# Background Tasks - Detailed Technical Design

## Overview

This document provides a detailed technical design for the background task system in Boards. The system handles asynchronous AI generation jobs (images, videos, audio, text) with progress tracking, reliability features, and credit management.

## Architecture Components

### 1. Queue System

**Technology Choice: RQ (Redis Queue)**
- **Primary**: RQ for simplicity and Python integration
- **Alternative**: Dramatiq for advanced features (if needed later)
- **Storage**: Redis for queue persistence and pub/sub

```python
import os

# Configuration
QUEUE_CONFIG = {
    "redis_url": os.getenv("BOARDS_REDIS_URL", "redis://redis:6379"),
    "default_queue": "boards-jobs",
    "high_priority_queue": "boards-priority",
    "low_priority_queue": "boards-bulk",
    "failed_queue": "boards-failed"
}
```

### 2. Job Flow Architecture

```
Client Request → API Validation → Job Enqueue → Worker Processing → Result Storage
     ↓               ↓              ↓              ↓                ↓
 Auth Check    Credit Reserve   Queue Mgmt    Provider API     Finalization
     ↓               ↓              ↓              ↓                ↓
 Input Valid.  Transaction Log   Redis Pub     Progress Pub    Credit Settle
```

### 3. Core Components

#### 3.1 Job Manager (`jobs/manager.py`)

**Responsibilities:**
- Job creation and validation
- Queue selection and enqueuing
- Job status management
- Credit reservation/finalization

```python
class JobManager:
    """Manages job lifecycle and coordination."""
    
    async def submit_job(self, job_request: JobRequest) -> str:
        """Submit a new job for processing."""
        # 1. Validate request
        # 2. Reserve credits
        # 3. Create generation record
        # 4. Enqueue job
        # 5. Return job ID
        
    async def cancel_job(self, job_id: str, user_id: str) -> bool:
        """Cancel a running job."""
        # 1. Check ownership
        # 2. Send cancellation signal
        # 3. Update status
        # 4. Refund credits
        
    async def get_job_status(self, job_id: str) -> JobStatus:
        """Get current job status and progress."""
```

#### 3.2 Worker System (`workers/`)

**Core Worker Structure:**
```python
class GenerationWorker:
    """Base class for AI generation workers."""
    
    def __init__(self, provider_manager: ProviderManager):
        self.provider_manager = provider_manager
        self.progress_publisher = ProgressPublisher()
        
    async def execute(self, job: GenerationJob):
        """Execute a generation job."""
        try:
            # 1. Load job context
            await self._load_context(job)
            
            # 2. Initialize provider
            provider = await self._get_provider(job.provider_name)
            
            # 3. Submit to provider
            external_job = await provider.submit(job.params)
            
            # 4. Update with external job ID
            await self._update_external_job_id(job.id, external_job.id)
            
            # 5. Poll for progress/completion
            await self._monitor_progress(job, external_job)
            
        except Exception as e:
            await self._handle_error(job, e)
            raise
```

**Worker Design Note:**
Since each provider has a consistent API across media types, we use a single `GenerationWorker` that delegates to provider-specific implementations rather than specialized workers per media type. The provider abstraction handles the differences between image, video, audio, and text generation.

#### 3.3 Progress Tracking System

**Progress Publisher (`progress/publisher.py`):**
```python
class ProgressPublisher:
    """Publishes job progress to clients via SSE."""
    
    async def publish_progress(self, job_id: str, progress: ProgressUpdate):
        """Publish progress update to Redis pub/sub."""
        channel = f"job:{job_id}:progress"
        await self.redis.publish(channel, progress.json())
        
        # Also update database
        await self._update_database_progress(job_id, progress)

class ProgressUpdate(BaseModel):
    job_id: str
    status: JobStatus
    progress: float  # 0.0 to 1.0
    phase: str      # "queued", "initializing", "processing", "finalizing"
    message: Optional[str]
    estimated_completion: Optional[datetime]
    artifacts: List[ArtifactInfo] = []
```

**SSE Endpoint (`api/endpoints/sse.py`):**
```python
@router.get("/jobs/{job_id}/progress")
async def job_progress_stream(job_id: str, request: Request):
    """Server-sent events for job progress."""
    async def generate():
        async with redis.pubsub() as pubsub:
            await pubsub.subscribe(f"job:{job_id}:progress")
            async for message in pubsub.listen():
                if await request.is_disconnected():
                    break
                yield f"data: {message['data']}\n\n"
    
    return StreamingResponse(generate(), media_type="text/plain")
```

#### 3.4 Provider Integration (`providers/`)

**Provider Interface:**
```python
class BaseProvider(ABC):
    """Abstract base for AI generation providers."""
    
    @abstractmethod
    async def submit_job(self, params: GenerationParams) -> ExternalJob:
        """Submit job to external provider."""
        
    @abstractmethod 
    async def get_job_status(self, external_job_id: str) -> ExternalJobStatus:
        """Get job status from provider."""
        
    @abstractmethod
    async def cancel_job(self, external_job_id: str) -> bool:
        """Cancel job with provider."""
        
    @abstractmethod
    async def download_artifacts(self, external_job_id: str) -> List[ArtifactUrl]:
        """Download generated artifacts."""
```

**Concrete Providers:**
- `ReplicateProvider` - Replicate API integration
- `FalProvider` - Fal.ai API integration  
- `OpenAIProvider` - DALL-E, GPT models
- `AnthropicProvider` - Claude models
- `StabilityProvider` - Stability AI models

#### 3.5 Credit Management Integration

**Credit Operations:**
```python
class CreditManager:
    """Manages credit transactions for jobs."""
    
    async def reserve_credits(self, user_id: str, job_cost: Decimal) -> str:
        """Reserve credits for a job."""
        # 1. Check available balance
        # 2. Create RESERVE transaction
        # 3. Return transaction ID
        
    async def finalize_credits(self, transaction_id: str, actual_cost: Decimal):
        """Finalize credit usage after job completion."""
        # 1. Create FINALIZE transaction
        # 2. Refund difference if actual < reserved
        
    async def refund_credits(self, transaction_id: str, reason: str):
        """Refund credits for failed/cancelled jobs."""
        # 1. Create REFUND transaction
        # 2. Restore user balance
```

### 4. Database Integration

#### 4.1 Enhanced Generations Table

The existing `generations` table supports job tracking:

```sql
-- Key fields for background jobs
external_job_id VARCHAR(255),     -- Provider's job ID
status generation_status_enum NOT NULL,  -- ENUM: 'pending', 'processing', 'completed', 'failed', 'cancelled'
progress DECIMAL(5,2),            -- 0.00 to 100.00
error_message TEXT,               -- Error details if failed
started_at TIMESTAMP WITH TIME ZONE,
completed_at TIMESTAMP WITH TIME ZONE

-- Create enum type for job status
CREATE TYPE generation_status_enum AS ENUM (
    'pending', 'processing', 'completed', 'failed', 'cancelled'
);
```

#### 4.2 Job Queue State Table

Additional table for queue-specific metadata:

```sql
CREATE TABLE job_queue_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    generation_id UUID NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
    queue_name VARCHAR(100) NOT NULL,
    priority INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    worker_id VARCHAR(255),
    cancellation_token VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 5. Error Handling & Reliability

#### 5.1 Retry Strategy

```python
from typing import List, Literal
from pydantic import BaseSettings

# Configurable retry settings - can be overridden via environment or config file
class RetryConfig(BaseSettings):
    max_retries: int = 3
    backoff_base: float = 2.0     # Exponential backoff: 2^attempt seconds
    backoff_max: int = 300        # Maximum 5 minutes
    jitter: bool = True           # Add randomness to prevent thundering herd
    retry_exceptions: List[str] = [
        "ProviderTimeoutError",
        "ProviderRateLimitError", 
        "ProviderTemporaryError"
    ]
    
    class Config:
        env_prefix = "BOARDS_RETRY_"
        # Allows setting via BOARDS_RETRY_MAX_RETRIES=5, etc.
```

#### 5.2 Circuit Breaker

```python
class ProviderCircuitBreaker:
    """Circuit breaker pattern for provider reliability."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state: Literal["closed", "open", "half-open"] = "closed"
```

#### 5.3 Dead Letter Queue

Failed jobs after max retries go to a dead letter queue for manual inspection:

```python
async def handle_job_failure(job: GenerationJob, error: Exception):
    """Handle final job failure."""
    # 1. Update generation record with error
    # 2. Refund credits
    # 3. Move to dead letter queue
    # 4. Send notification (if configured)
```

### 6. Security Considerations

#### 6.1 Credential Management

```python
class ProviderCredentialManager:
    """Secure credential management for providers."""
    
    async def get_credentials(self, tenant_id: str, provider_name: str) -> Dict:
        """Get encrypted provider credentials."""
        # 1. Load from secure storage (env vars, vault, etc.)
        # 2. Decrypt if necessary
        # 3. Return scoped credentials
        
    async def rotate_credentials(self, tenant_id: str, provider_name: str):
        """Rotate provider API keys."""
```

#### 6.2 Input Validation & Sanitization

```python
class JobValidator:
    """Validates and sanitizes job inputs."""
    
    async def validate_generation_params(self, params: GenerationParams) -> ValidationResult:
        """Validate generation parameters."""
        # 1. Check required fields
        # 2. Validate ranges and constraints
        # 3. Sanitize text inputs
        # 4. Check content policy compliance
        
    async def sanitize_prompt(self, prompt: str) -> str:
        """Sanitize user prompts for safety."""
        # 1. Remove potentially harmful content
        # 2. Apply content filters
        # 3. Redact sensitive information
```

#### 6.3 Audit Logging

```python
class JobAuditLogger:
    """Audit logging for job operations."""
    
    async def log_job_submitted(self, job_id: str, user_id: str, params: dict):
        """Log job submission with redacted sensitive data."""
        
    async def log_job_completed(self, job_id: str, status: str, artifacts: List):
        """Log job completion."""
        
    async def log_job_cancelled(self, job_id: str, user_id: str, reason: str):
        """Log job cancellation."""
```

### 7. Monitoring & Observability

#### 7.1 Metrics Collection

```python
# Key metrics to track
METRICS = {
    "job_submission_rate": "Counter",
    "job_completion_rate": "Counter", 
    "job_failure_rate": "Counter",
    "queue_depth": "Gauge",
    "worker_utilization": "Gauge",
    "job_duration": "Histogram",
    "credit_usage": "Counter",
    "provider_response_time": "Histogram"
}
```

#### 7.2 Health Checks

```python
@router.get("/health/jobs")
async def jobs_health_check():
    """Health check for job system."""
    return {
        "queue_connection": await check_redis_connection(),
        "active_workers": await get_active_worker_count(),
        "queue_depths": await get_queue_depths(),
        "provider_status": await check_provider_health()
    }
```

### 8. Configuration & Deployment

#### 8.1 Environment Configuration

```python
import os
from pydantic import BaseSettings, Field, validator

# Additional settings for background tasks
class BackgroundTaskSettings(BaseSettings):
    # Queue settings  
    redis_url: str = Field(default_factory=lambda: os.getenv("BOARDS_REDIS_URL", "redis://redis:6379"))
    
    @validator('redis_url', pre=True)
    def validate_redis_url(cls, v):
        if not v or v.startswith('redis://localhost'):
            raise ValueError('Redis URL must not use localhost for production deployments')
        return v
    job_queue_name: str = "boards-jobs"
    max_concurrent_jobs: int = 10
    job_timeout: int = 3600  # 1 hour
    
    # Retry settings
    max_retries: int = 3
    retry_backoff_base: float = 2.0
    retry_backoff_max: int = 300
    
    # Worker settings
    worker_count: int = 4
    worker_max_jobs: int = 1
    worker_heartbeat_interval: int = 30
    
    # Provider settings
    provider_timeout: int = 300
    provider_rate_limit_per_minute: int = 60
    
    # Monitoring
    metrics_enabled: bool = True
    audit_logging_enabled: bool = True
```

#### 8.2 Docker Compose Integration

```yaml
# Additional services in docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "127.0.0.1:6379:6379"  # Bind to localhost only
    volumes:
      - redis_data:/data
    command: redis-server --requirepass ${REDIS_PASSWORD:-boards_dev_redis}
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD:-boards_dev_redis}
      
  worker:
    build: .
    command: python -m boards.workers.main
    depends_on:
      - redis
      - postgres
    environment:
      - BOARDS_REDIS_URL=redis://:${REDIS_PASSWORD:-boards_dev_redis}@redis:6379
      - BOARDS_DATABASE_URL=postgresql://boards:boards_dev@postgres/boards_dev
    deploy:
      replicas: 4
      
volumes:
  redis_data:
```

### 9. API Endpoints

#### 9.1 Job Submission

```python
@router.post("/api/generations", response_model=GenerationResponse)
async def submit_generation(
    request: GenerationRequest,
    current_user: User = Depends(get_current_user)
) -> GenerationResponse:
    """Submit a new generation job."""
    # Implementation handles validation, credit check, and job enqueue
```

#### 9.2 Job Management

```python
@router.get("/api/generations/{generation_id}")
async def get_generation_status(generation_id: str) -> GenerationStatus:
    """Get generation status and progress."""

@router.post("/api/generations/{generation_id}/cancel")
async def cancel_generation(generation_id: str) -> CancellationResponse:
    """Cancel a running generation."""

@router.get("/api/generations/{generation_id}/progress")
async def generation_progress_stream(generation_id: str) -> StreamingResponse:
    """SSE stream for real-time progress updates."""
```

### 10. Implementation Phases

#### Phase 1: Core Infrastructure
- [ ] Job manager and basic queue setup
- [ ] Database schema updates
- [ ] Progress tracking system
- [ ] Basic worker framework

#### Phase 2: Provider Integration
- [ ] Provider abstraction layer
- [ ] Replicate provider implementation
- [ ] Fal.ai provider implementation
- [ ] Error handling and retries

#### Phase 3: Advanced Features
- [ ] Circuit breaker implementation
- [ ] Advanced monitoring and metrics
- [ ] Job prioritization
- [ ] Bulk job operations

#### Phase 4: Production Readiness
- [ ] Security hardening
- [ ] Performance optimization
- [ ] Comprehensive testing
- [ ] Documentation and deployment guides

## File Structure

```
packages/backend/src/boards/
├── jobs/
│   ├── __init__.py
│   ├── manager.py          # JobManager class
│   ├── models.py           # Job-related Pydantic models
│   └── exceptions.py       # Job-specific exceptions
├── workers/
│   ├── __init__.py
│   ├── main.py            # Worker entry point
│   ├── base.py            # BaseWorker class
│   └── generation.py      # GenerationWorker (handles all media types)
├── providers/
│   ├── __init__.py
│   ├── base.py            # BaseProvider abstract class
│   ├── replicate.py       # ReplicateProvider
│   ├── fal.py             # FalProvider
│   ├── openai.py          # OpenAIProvider
│   └── credentials.py     # ProviderCredentialManager
├── progress/
│   ├── __init__.py
│   ├── publisher.py       # ProgressPublisher
│   └── models.py          # Progress-related models
├── credits/
│   ├── __init__.py
│   ├── manager.py         # CreditManager
│   └── models.py          # Credit transaction models
└── api/endpoints/
    ├── jobs.py            # Job management endpoints
    ├── sse.py             # Server-sent events
    └── webhooks.py        # Provider webhooks
```

This detailed design provides a comprehensive foundation for implementing the background task system while maintaining flexibility for future enhancements and provider integrations.
# Generators: Detailed Design

## Overview

This document presents a detailed design for the Boards generators system, enabling users to integrate with any AI generation service through a unified, type-safe, and developer-friendly architecture.

## Core Requirements

1. **Minimal Generator Code**: Generator creation should require only Pydantic schema definitions
2. **Type Safety**: Full-stack type safety from Python → GraphQL → TypeScript → UI  
3. **Artifact Resolution**: Declarative specification of artifact dependencies between generations
4. **Direct SDK Usage**: Generators use provider SDKs directly with no abstraction layer

## Architecture Principles

### 1. Pydantic-First Generators
- **Generators** define input/output schemas as Pydantic models
- Automatic JSON Schema generation for frontend type generation
- Built-in validation and serialization

### 2. Direct SDK Integration
- Generators import and use provider SDKs directly
- No wrapper layers or generic REST clients
- Full access to provider-specific features and authentication

### 3. Declarative Artifact Resolution
- Input fields can reference other Generation artifacts by type
- Automatic file resolution and preparation
- Type-safe drag/drop UI generation

## System Components

### Artifact Types

```python
# Artifact Types for Input/Output Schemas
class AudioArtifact(BaseModel):
    generation_id: str
    storage_url: str
    duration: Optional[float] = None
    format: str

class VideoArtifact(BaseModel):
    generation_id: str
    storage_url: str
    duration: Optional[float] = None
    width: int
    height: int
    format: str

class ImageArtifact(BaseModel):
    generation_id: str
    storage_url: str
    width: int
    height: int
    format: str
```

### Base Generator Interface

```python
class BaseGenerator(ABC):
    """Defines generation inputs/outputs and handles generation logic"""
    name: str
    artifact_type: str  # 'image', 'video', 'audio', 'text', 'lora'
    description: str
    
    @abstractmethod
    def get_input_schema(self) -> Type[BaseModel]
    
    @abstractmethod
    async def generate(self, inputs: BaseModel) -> BaseModel
    
    @abstractmethod
    async def estimate_cost(self, inputs: BaseModel) -> float
```

### Example Generator Implementation

```python
# Example: Lipsync Generator
class ReplicateLipsyncInput(BaseModel):
    audio_source: AudioArtifact  # Drag/drop slot for audio
    video_source: VideoArtifact  # Drag/drop slot for video
    prompt: Optional[str] = None

class ReplicateLipsyncOutput(BaseModel):
    video: VideoArtifact

class ReplicateLipsyncGenerator(BaseGenerator):
    name = "replicate-lipsync"
    artifact_type = "video"
    description = "Sync lips in video to audio"

    def get_input_schema(self) -> Type[ReplicateLipsyncInput]:
        return ReplicateLipsyncInput

    async def generate(self, inputs: ReplicateLipsyncInput) -> ReplicateLipsyncOutput:
        # Import SDK directly
        import replicate

        # System automatically resolves artifacts to file paths
        audio_file = await resolve_artifact(inputs.audio_source)
        video_file = await resolve_artifact(inputs.video_source)

        # Use SDK directly - no wrapper layer
        result = await replicate.async_run(
            "replicate/lipsync-model",
            input={
                "audio": audio_file,
                "video": video_file
            }
        )

        # Store output and create artifact
        video_artifact = await store_video_result(result)
        return ReplicateLipsyncOutput(video=video_artifact)

    async def estimate_cost(self, inputs: ReplicateLipsyncInput) -> float:
        # Simple cost estimation logic
        return 0.05  # $0.05 per generation
```

## Configuration System

### Environment Variables Only

```bash
# .env - Simple environment-based configuration
REPLICATE_API_TOKEN=r8_your_token_here
FAL_KEY=your_fal_key_here  
OPENAI_API_KEY=sk-your_openai_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here

# Optional: Storage configuration
BOARDS_STORAGE_BACKEND=s3  # or local, gcs, etc.
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
```

**Benefits:**
- No YAML configuration needed at all
- Standard environment variable approach
- Each generator handles its own SDK authentication
- Simple setup process

## Generator Registry

### Simple Discovery System

```python
class GeneratorRegistry:
    def __init__(self):
        self._generators: Dict[str, BaseGenerator] = {}
    
    def register(self, generator: BaseGenerator) -> None:
        """Register a generator instance"""
        self._generators[generator.name] = generator
    
    def get(self, name: str) -> Optional[BaseGenerator]:
        """Get generator by name"""
        return self._generators.get(name)
    
    def list_all(self) -> List[BaseGenerator]:
        """List all registered generators"""
        return list(self._generators.values())
    
    def list_by_artifact_type(self, artifact_type: str) -> List[BaseGenerator]:
        """List generators that produce specific artifact types"""
        return [g for g in self._generators.values() 
                if g.artifact_type == artifact_type]

# Global registry instance
registry = GeneratorRegistry()

# Generators register themselves on import
registry.register(ReplicateLipsyncGenerator())
registry.register(ReplicateFluxProGenerator())
registry.register(OpenAIDallE3Generator())
```

## Directory Structure

```
packages/backend/src/boards/
├── generators/
│   ├── __init__.py              # Registry and base exports  
│   ├── base.py                  # BaseGenerator abstract class
│   ├── registry.py              # Generator discovery and management
│   ├── artifacts.py             # Artifact type definitions
│   ├── resolution.py            # Artifact resolution utilities
│   └── implementations/         # Generator implementations
│       ├── __init__.py          # Registers all generators on import
│       ├── image/               # Image generators
│       │   ├── flux_pro.py
│       │   ├── dalle3.py
│       │   └── qwen_image.py
│       ├── video/               # Video generators
│       │   ├── lipsync.py
│       │   └── upscale.py
│       └── audio/               # Audio generators
│           └── whisper.py
│
├── storage/                     # Storage system integration
│   └── ...                     # (existing pluggable storage)
│
└── database/                    # Database models for generations
    └── ...                     # Generation, Board models, etc.
```

## Type Safety & Frontend Integration

### Pydantic → TypeScript Pipeline

1. **Generator defines Pydantic schema**:
```python
class LipsyncInput(BaseModel):
    audio_source: AudioArtifact
    video_source: VideoArtifact
    prompt: Optional[str] = None
```

2. **JSON Schema generation**:
```python
@app.get("/api/generators/{name}/input-schema")
async def get_input_schema(name: str):
    generator = registry.get_generator(name)
    return generator.get_input_schema().model_json_schema()
```

3. **Frontend gets TypeScript types** (via user's tooling):
```typescript
interface LipsyncInput {
    audio_source: AudioArtifact;  // Drag/drop knows: audio only
    video_source: VideoArtifact;  // Drag/drop knows: video only  
    prompt?: string;              // Text input field
}
```

4. **UI auto-generates** from schema:
   - Artifact fields → drag/drop zones with type validation
   - String fields → text inputs
   - Enums → select dropdowns
   - Optional fields → collapsible sections

## Adding New Generators

### Simple Process for Developers

1. **Create Pydantic input/output schemas**:
```python
class MyGeneratorInput(BaseModel):
    prompt: str
    image_input: Optional[ImageArtifact] = None
    
class MyGeneratorOutput(BaseModel):
    result: ImageArtifact
```

2. **Implement generator class**:
```python
class MyGenerator(BaseGenerator):
    name = "my-generator"
    provider = "replicate"
    artifact_type = "image"
    description = "My custom generator"
    
    def get_input_schema(self) -> Type[MyGeneratorInput]:
        return MyGeneratorInput
        
    async def generate(self, inputs: MyGeneratorInput) -> MyGeneratorOutput:
        # Use provider SDK + artifact resolution
        # Return structured output
```

3. **Register with system** (happens automatically via discovery or manual registration)

4. **Frontend automatically gets**:
   - TypeScript types for the input schema
   - Drag/drop UI for artifact inputs
   - Form fields for primitive inputs

## Key Benefits

### For Developers
- **Minimal Code**: Only Pydantic schemas + simple generation logic
- **Type Safety**: Full-stack type safety from Python to TypeScript
- **Direct SDKs**: Use any provider SDK directly with no wrappers
- **Auto UI**: Frontend generation forms created automatically
- **No Configuration**: Just environment variables, no YAML needed

### For Users  
- **Simple Setup**: Just set environment variables for API keys
- **Drag/Drop UX**: Type-safe artifact connections between generators
- **Provider Agnostic**: Use any combination of services (Replicate, OpenAI, Fal, etc.)
- **Extensible**: Easy to add custom generators

### For the System
- **Storage Integration**: Automatic artifact storage and retrieval  
- **Database Integration**: Generation history and metadata tracking
- **Billing Integration**: Cost estimation and credit tracking
- **GraphQL API**: Structured data access for frontend

## Success Criteria

1. **Generator Creation**: Adding a new generator requires < 50 lines of Python code
2. **Type Safety**: Zero runtime type errors between frontend/backend  
3. **Performance**: Artifact resolution adds < 100ms overhead per generation
4. **Developer Experience**: New developers can add generators in < 30 minutes

This simplified design focuses on the core value: making it trivial to add new AI generation capabilities while maintaining full type safety and excellent developer experience.

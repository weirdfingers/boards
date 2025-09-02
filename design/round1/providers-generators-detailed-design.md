# Providers and Generators: Detailed Design

## Overview

This document presents a detailed design for the Boards providers and generators system, enabling users to integrate with any AI generation service through a unified, extensible, and agentic-friendly architecture.

## Core Requirements

1. **User Choice**: Users select which providers and generators their system uses
2. **Agentic Extensibility**: AI agents can add new generators with minimal prompting by referencing documentation
3. **Minimal Generator Code**: Generator-specific implementation should be as small as possible
4. **Well-Documented Process**: Creating new providers must be thoroughly documented

## Architecture Principles

### 1. Separation of Concerns
- **Provider**: Handles authentication, API communication, and service-specific logic
- **Generator**: Defines input/output schemas and orchestrates the generation process
- **Registry**: Manages discovery, registration, and lifecycle of providers/generators

### 2. Declarative Configuration
- YAML/JSON configuration files describe providers and generators
- Minimal code required for standard REST API integrations
- Configuration-driven approach enables agentic tools to add new integrations

### 3. Plugin-based Architecture
- Dynamic discovery and loading of providers/generators
- Support for both built-in and user-defined implementations
- Hot-swappable configurations for development

## System Components

### Core Abstractions

```python
# Base Provider Interface
class BaseProvider(ABC):
    """Abstract base for all providers"""
    name: str
    description: str
    auth_type: str  # 'api_key', 'oauth', 'bearer_token', 'custom'
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> bool
    
    @abstractmethod
    async def validate_credentials(self) -> bool
    
    @abstractmethod
    def get_supported_generators(self) -> List[str]

# Base Generator Interface  
class BaseGenerator(ABC):
    """Abstract base for all generators"""
    name: str
    provider: str
    artifact_type: str  # 'image', 'video', 'audio', 'text', 'lora'
    description: str
    
    @abstractmethod
    def get_input_schema(self) -> Type[BaseModel]
    
    @abstractmethod
    def get_output_schema(self) -> Type[BaseModel]
    
    @abstractmethod
    async def generate(
        self, 
        inputs: BaseModel, 
        progress_callback: Optional[Callable] = None
    ) -> BaseModel
    
    @abstractmethod
    async def estimate_cost(self, inputs: BaseModel) -> float
```

### Registry System

```python
class ProviderRegistry:
    """Central registry for provider discovery and management"""
    
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._generators: Dict[str, BaseGenerator] = {}
    
    def register_provider(self, provider: BaseProvider) -> None
    def register_generator(self, generator: BaseGenerator) -> None
    def get_provider(self, name: str) -> Optional[BaseProvider]
    def get_generator(self, name: str) -> Optional[BaseGenerator]
    def list_providers(self) -> List[str]
    def list_generators(self, artifact_type: str = None) -> List[str]
    
    async def load_from_config(self, config_path: str) -> None
    async def validate_all_providers(self) -> Dict[str, bool]
```

## Configuration System

### Provider Configuration

```yaml
# providers.yaml
providers:
  replicate:
    type: rest_api
    description: "Replicate.com API access"
    auth:
      type: api_key
      header: "Authorization"
      prefix: "Bearer "
    endpoints:
      base_url: "https://api.replicate.com/v1"
      models: "/collections/text-to-image/models"
    generators:
      - flux-1-1-pro
      - sdxl
      
  fal_ai:
    type: rest_api  
    description: "Fal.ai API access"
    auth:
      type: api_key
      header: "Authorization"  
      prefix: "Key "
    endpoints:
      base_url: "https://fal.run"
    generators:
      - qwen-image
      - flux-general
      
  openai:
    type: rest_api
    description: "OpenAI API access"
    auth:
      type: api_key
      header: "Authorization"
      prefix: "Bearer "
    endpoints:
      base_url: "https://api.openai.com/v1"
    generators:
      - dall-e-3
      - whisper
```

### Generator Configuration

```yaml
# generators.yaml
generators:
  flux-1-1-pro:
    provider: replicate
    artifact_type: image
    description: "FLUX.1.1 [pro] by Black Forest Labs"
    api_spec:
      endpoint: "/models/black-forest-labs/flux-1.1-pro/predictions"
      method: POST
      input_schema:
        type: object
        properties:
          prompt:
            type: string
            description: "Text prompt for image generation"
            required: true
          aspect_ratio:
            type: string
            enum: ["1:1", "16:9", "21:9", "2:3", "3:2", "4:5", "5:4", "9:16", "9:21"]
            default: "1:1"
          safety_tolerance:
            type: integer
            minimum: 1
            maximum: 5
            default: 2
      output_mapping:
        storage_url: "output[0]"
        metadata:
          model_version: "version"
          seed: "seed"
          
  qwen-image:
    provider: fal_ai
    artifact_type: image
    description: "Qwen image generation via fal.ai"
    api_spec:
      endpoint: "/fal-ai/qwen-image"
      method: POST
      input_schema:
        type: object
        properties:
          prompt:
            type: string
            description: "Image description prompt"
            required: true
          image_size:
            type: string
            enum: ["square", "portrait", "landscape"]
            default: "square"
      output_mapping:
        storage_url: "images[0].url"
        metadata:
          inference_time: "timings.inference"
```

## REST Spec Generator

A key innovation is the `RestSpecGenerator` - a generic generator that can execute any REST API based on YAML configuration:

```python
class RestSpecGenerator(BaseGenerator):
    """Generic generator that executes REST APIs based on YAML specifications"""
    
    def __init__(self, config: Dict[str, Any], provider: BaseProvider):
        self.config = config
        self.provider = provider
        self.name = config['name']
        self.artifact_type = config['artifact_type']
        self.api_spec = config['api_spec']
        
    def get_input_schema(self) -> Type[BaseModel]:
        """Dynamically create Pydantic model from OpenAPI-style schema"""
        return create_model_from_schema(self.api_spec['input_schema'])
    
    async def generate(self, inputs: BaseModel, progress_callback=None) -> BaseModel:
        """Execute the REST API call as specified in configuration"""
        
        # Build request
        url = f"{self.provider.base_url}{self.api_spec['endpoint']}"
        payload = inputs.dict()
        headers = await self.provider.get_auth_headers()
        
        # Execute request
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=self.api_spec['method'],
                url=url,
                json=payload,
                headers=headers
            )
            
        # Handle response
        result_data = response.json()
        
        # Map output using JSONPath expressions
        output_data = {}
        for key, path in self.api_spec['output_mapping'].items():
            output_data[key] = extract_jsonpath(result_data, path)
            
        return GenerationOutput(**output_data)
```

## Directory Structure

```
packages/backend/src/boards/
├── providers/
│   ├── __init__.py              # Registry exports
│   ├── base.py                  # BaseProvider abstract class
│   ├── registry.py              # ProviderRegistry implementation
│   ├── rest_provider.py         # Generic REST API provider
│   ├── config_loader.py         # YAML configuration loading
│   └── builtin/                 # Built-in provider implementations
│       ├── __init__.py
│       ├── replicate.py         # Custom Replicate provider (if needed)
│       ├── openai.py            # Custom OpenAI provider (if needed)
│       └── fal.py               # Custom Fal.ai provider (if needed)
│
├── generators/
│   ├── __init__.py              # Registry exports  
│   ├── base.py                  # BaseGenerator abstract class
│   ├── registry.py              # GeneratorRegistry implementation
│   ├── rest_spec_generator.py   # Generic REST API executor
│   ├── schema_utils.py          # Dynamic Pydantic model creation
│   └── builtin/                 # Custom generator implementations
│       ├── __init__.py
│       └── comfyui_generator.py # Example custom generator
│
└── config/
    ├── providers.yaml           # Provider configurations
    ├── generators.yaml          # Generator configurations
    └── examples/                # Example configurations
        ├── replicate-flux.yaml
        ├── fal-qwen.yaml
        └── openai-dalle.yaml
```

## Agentic Integration Strategy

### 1. Documentation Structure

Create comprehensive documentation that enables AI agents to add new integrations:

```markdown
# ADDING_A_GENERATOR.md

## Quick Start for AI Agents

To add a new generator, follow these steps:

1. **Identify the API**: Find the API documentation (e.g., https://replicate.com/black-forest-labs/flux-1.1-pro/api)

2. **Create generator entry**: Add to `config/generators.yaml`:
   ```yaml
   generators:
     your-generator-name:
       provider: provider-name
       artifact_type: image|video|audio|text
       description: "Brief description"
       api_spec:
         endpoint: "/path/to/endpoint"
         method: POST|GET|PUT
         input_schema:
           # OpenAPI 3.0 schema definition
         output_mapping:
           # JSONPath mappings
   ```

3. **Test the integration**: Run `boards test-generator your-generator-name`

### API Documentation Templates

The system includes templates for common API patterns that agents can reference:

- `templates/rest-api-generator.yaml` - Standard REST API pattern
- `templates/replicate-style-generator.yaml` - Replicate.com API pattern  
- `templates/polling-generator.yaml` - APIs that require polling for results
```

### 2. Generator Templates

```yaml
# templates/rest-api-generator.yaml
generators:
  template-generator:
    provider: PROVIDER_NAME
    artifact_type: ARTIFACT_TYPE  # image, video, audio, text
    description: "DESCRIPTION"
    api_spec:
      endpoint: "API_ENDPOINT_PATH"
      method: POST
      input_schema:
        type: object
        properties:
          prompt:
            type: string
            description: "Main generation prompt"
            required: true
          # ADD_ADDITIONAL_PARAMETERS_HERE
      output_mapping:
        storage_url: "OUTPUT_PATH_TO_MEDIA_URL"
        metadata:
          # MAP_ADDITIONAL_METADATA_HERE
```

### 3. Self-Documenting Schema

The system automatically generates documentation from configurations:

```python
@app.get("/api/generators/{generator_name}/schema")
async def get_generator_schema(generator_name: str):
    """Return OpenAPI schema for a generator's inputs"""
    generator = registry.get_generator(generator_name)
    return generator.get_input_schema().schema()

@app.get("/api/generators")
async def list_generators():
    """Return all available generators with their descriptions"""
    return [
        {
            "name": gen.name,
            "provider": gen.provider,
            "artifact_type": gen.artifact_type,
            "description": gen.description,
            "input_schema": gen.get_input_schema().schema()
        }
        for gen in registry.list_all_generators()
    ]
```

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)
- [x] Implement base classes and registry system
- [x] Create configuration loading system
- [x] Implement RestSpecGenerator
- [x] Create basic provider implementations (Replicate, Fal.ai, OpenAI)

### Phase 2: Integration & Testing (Week 3)
- [ ] Integrate with existing GraphQL schema
- [ ] Add provider/generator management to admin interface
- [ ] Implement comprehensive test suite
- [ ] Create CLI tools for testing integrations

### Phase 3: Documentation & Examples (Week 4)
- [ ] Write comprehensive documentation for adding providers/generators
- [ ] Create example integrations for popular services
- [ ] Develop agentic integration guides
- [ ] Create video tutorials

### Phase 4: Advanced Features (Week 5-6)
- [ ] Implement cost estimation and credit tracking
- [ ] Add support for streaming/progress callbacks
- [ ] Implement caching for repeated generations
- [ ] Add support for batch operations

## Security Considerations

### API Key Management
- Never store API keys in configuration files
- Use environment variables or secure key management services
- Implement key rotation capabilities
- Support multiple authentication methods per provider

### Input Validation
- Validate all inputs against provider-specific schemas
- Implement rate limiting and quota management
- Sanitize user inputs to prevent injection attacks
- Log all generation requests for audit purposes

### Output Handling
- Validate generated content before storage
- Implement content filtering and moderation
- Support different storage backends for sensitive content
- Maintain audit trail of all generation activities

## Monitoring & Observability

### Metrics Collection
- Track generation success/failure rates per provider
- Monitor API response times and error rates
- Collect cost and usage statistics
- Track user adoption of different generators

### Logging Strategy
- Structured logging with correlation IDs
- Separate logs for business logic vs. technical issues
- Log level configuration per provider
- Integration with centralized logging systems

## Migration & Compatibility

### Backward Compatibility
- Maintain compatibility with existing generation jobs
- Support gradual migration from hardcoded integrations
- Version configuration schemas appropriately
- Provide migration tools for existing data

### Future Extensibility
- Design for additional artifact types (3D models, animations)
- Support for complex multi-step workflows
- Integration with local/on-premise generation services
- Support for custom preprocessing/postprocessing pipelines

## Success Criteria

1. **Developer Experience**: Adding a new REST API generator takes < 15 minutes
2. **AI Agent Compatibility**: Agents can successfully add new generators using only documentation
3. **Performance**: No significant overhead compared to hardcoded integrations
4. **Reliability**: 99.9% uptime for core registry and execution systems
5. **Adoption**: 80% of new generators use the configuration-based approach within 3 months

This design provides a robust, extensible foundation for the Boards providers and generators system while maintaining the flexibility and ease-of-use required for rapid AI-driven development.
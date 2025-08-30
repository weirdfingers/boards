---
sidebar_position: 1
---

# Providers Overview

Boards supports multiple AI providers through a pluggable architecture. This allows you to integrate with various AI services for content generation.

## Supported Providers

### Image Generation

- **Replicate** - Wide variety of image models
- **Fal.ai** - Fast inference for popular models  
- **Stability AI** - Official Stable Diffusion API
- **OpenAI DALL·E** - GPT-powered image generation

### Text Generation  

- **OpenAI** - GPT-4, GPT-3.5, and other models
- **Anthropic Claude** - Constitutional AI models
- **Replicate** - Open source language models

### Video Generation

- **Replicate** - Video generation models
- **Runway** - Creative video tools
- **Stability AI** - Stable Video Diffusion

### Audio Generation

- **Replicate** - Music and audio models
- **ElevenLabs** - Voice synthesis
- **OpenAI** - Audio generation and transcription

## Provider Architecture

Each provider implements a common interface:

```python
from boards.providers.base import BaseProvider

class MyProvider(BaseProvider):
    name = "my_provider"
    supported_types = ["image", "text"]
    
    async def generate(self, request: GenerationRequest):
        # Implementation
        pass
```

## Configuration

Providers are configured through environment variables:

```bash
# Replicate
BOARDS_REPLICATE_API_TOKEN=your_token

# OpenAI  
BOARDS_OPENAI_API_KEY=your_key

# Fal.ai
BOARDS_FAL_API_KEY=your_key
```

## Next Steps

- **[Replicate Integration](./replicate)** - Set up Replicate provider
- **[OpenAI Integration](./openai)** - Configure OpenAI models
- **[Custom Providers](./custom-providers)** - Build your own provider
"""
Built-in generator implementations for the Boards system.

This package contains example generators that demonstrate how to integrate
various AI services using their native SDKs.

Generators are organized by provider (Replicate, Fal, OpenAI, etc.).

Import this module to automatically register all built-in generators:
    import boards.generators.implementations
"""

# Import all provider modules to make them available
from . import fal, openai, replicate

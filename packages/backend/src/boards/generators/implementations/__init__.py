"""
Built-in generator implementations for the Boards system.

This package contains example generators that demonstrate how to integrate
various AI services using their native SDKs.

Import this module to automatically register all built-in generators:
    import boards.generators.implementations
"""

# Import all generator modules to trigger registration
from . import audio, image, video

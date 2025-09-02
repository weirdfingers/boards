"""
Boards Backend SDK
Open-source creative toolkit for AI-generated content
"""

__version__ = "0.1.0"

from .config import settings

# Register built-in provider types at import time
try:
    from .providers.registry import provider_registry
    from .providers.builtin.replicate import ReplicateProvider
    from .providers.builtin.fal import FalProvider

    provider_registry.register_type("replicate", ReplicateProvider)
    provider_registry.register_type("fal", FalProvider)
except Exception:
    # Safe import guard to avoid hard failure in environments without provider modules
    pass

__all__ = ["settings", "__version__"]
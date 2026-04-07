"""Exceptions for the artifact plugin system."""


class PluginExecutionError(Exception):
    """Raised when a plugin fails and should fail the generation."""

    def __init__(self, plugin_name: str, error_message: str | None = None):
        self.plugin_name = plugin_name
        self.error_message = error_message or "Unknown error"
        super().__init__(f"Plugin '{plugin_name}' failed: {self.error_message}")


class PluginTimeoutError(PluginExecutionError):
    """Raised when a plugin exceeds its execution timeout."""

    def __init__(self, plugin_name: str, timeout_seconds: float):
        self.timeout_seconds = timeout_seconds
        super().__init__(
            plugin_name=plugin_name,
            error_message=f"Execution timed out after {timeout_seconds}s",
        )


class PluginLoadError(Exception):
    """Raised when a plugin fails to load from configuration."""

    def __init__(self, message: str):
        super().__init__(message)

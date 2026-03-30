# Artifact Plugins: Detailed Design

## Overview

Artifact Plugins provide a hook for executing custom code after a generator produces an artifact but before the artifact is uploaded to remote storage. This enables post-processing operations that require access to the local file data, such as embedding C2PA provenance metadata, watermarking, format conversion, or content analysis.

## Motivation

### Key Use Case: C2PA Metadata

The primary motivation is enabling C2PA (Coalition for Content Provenance and Authenticity) metadata embedding. C2PA requires:

1. **Local file access**: Cryptographic signing requires direct file manipulation
2. **Post-generation timing**: Metadata must be embedded after the artifact is created
3. **Pre-upload execution**: The signed file must be what gets uploaded to storage

### Additional Use Cases

- **Watermarking**: Visible or invisible watermarks for brand protection
- **Format conversion**: Converting artifacts to alternative formats
- **Content analysis**: Running safety checks, quality scoring, or classification
- **Metadata enrichment**: Adding EXIF, IPTC, or custom metadata
- **Manifest repository**: Writing provenance records to external systems

## Architecture Principles

### 1. Independence from Generators

Plugins are configured separately from generators and run on **all artifacts** produced by any generator. This ensures:

- Consistent behavior across all generated content
- Simpler configuration (no per-generator plugin setup)
- Easier auditing and compliance

### 2. Synchronous Execution

Plugins run synchronously in the worker process, blocking artifact upload until all plugins complete. This guarantees:

- Plugin modifications are included in the uploaded artifact
- Clear error handling (plugin failure can fail the generation)
- Predictable ordering of operations

### 3. Ordered Pipeline

Multiple plugins execute in the order specified in configuration, allowing:

- Chained transformations (e.g., watermark → sign)
- Dependencies between plugins (e.g., analysis → conditional signing)

## System Components

### Plugin Base Interface

```python
from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel
from pathlib import Path

class PluginResult(BaseModel):
    """Result returned by a plugin after execution."""
    success: bool
    # If provided, replaces the artifact file path (for plugins that create new files)
    output_file_path: Optional[Path] = None
    # If success=False and fail_generation=True, this message is stored in the generation record
    error_message: Optional[str] = None
    # Whether a plugin failure should fail the entire generation
    fail_generation: bool = True
    # Optional metadata to attach to the artifact record
    metadata: Optional[dict] = None


class PluginContext(BaseModel):
    """Context provided to plugins during execution."""
    # Local file path to the artifact (read/write access)
    file_path: Path

    # Artifact metadata
    artifact_type: str  # 'image', 'video', 'audio', 'text'
    mime_type: str
    file_size_bytes: int
    # Type-specific metadata (e.g., width/height for images, duration for video/audio)
    artifact_metadata: dict

    # Generation metadata
    generation_id: str
    generator_name: str
    generator_inputs: dict  # The inputs passed to the generator (includes prompt, etc.)

    # Board context
    board_id: str
    board_title: str

    # User/tenant context
    tenant_id: str
    user_id: str

    # Full generation record (for advanced use cases)
    generation_record: dict

    class Config:
        arbitrary_types_allowed = True


class BaseArtifactPlugin(ABC):
    """Base class for artifact plugins."""

    # Unique identifier for the plugin
    name: str

    # Human-readable description
    description: str

    # Artifact types this plugin applies to (empty = all types)
    supported_artifact_types: list[str] = []

    @abstractmethod
    async def execute(self, context: PluginContext) -> PluginResult:
        """
        Execute the plugin on an artifact.

        Args:
            context: Full context about the artifact and generation

        Returns:
            PluginResult indicating success/failure and optional modifications
        """
        pass

    def supports_artifact_type(self, artifact_type: str) -> bool:
        """Check if this plugin supports the given artifact type."""
        if not self.supported_artifact_types:
            return True  # Empty list means all types
        return artifact_type in self.supported_artifact_types
```

### Example Plugin Implementations

#### C2PA Signing Plugin

```python
from c2pa import Builder, SigningAlg
from pathlib import Path

class C2PASigningPlugin(BaseArtifactPlugin):
    """Embeds C2PA provenance metadata into artifacts."""

    name = "c2pa-signing"
    description = "Signs artifacts with C2PA Content Credentials"
    supported_artifact_types = ["image", "video"]  # C2PA supports these

    def __init__(
        self,
        signing_key_path: str,
        certificate_path: str,
        claim_generator: str = "Boards/1.0",
        include_ingredients: bool = True,
    ):
        self.signing_key_path = Path(signing_key_path)
        self.certificate_path = Path(certificate_path)
        self.claim_generator = claim_generator
        self.include_ingredients = include_ingredients

    async def execute(self, context: PluginContext) -> PluginResult:
        try:
            # Build C2PA manifest
            builder = Builder()
            builder.set_claim_generator(self.claim_generator)

            # Add creation action
            builder.add_action("c2pa.created", {
                "softwareAgent": context.generator_name,
                "parameters": {
                    "prompt": context.generator_inputs.get("prompt", ""),
                }
            })

            # Sign and embed in-place
            builder.sign_file(
                source=context.file_path,
                dest=context.file_path,  # In-place modification
                signing_key=self.signing_key_path.read_bytes(),
                certificate=self.certificate_path.read_bytes(),
                algorithm=SigningAlg.ES256,
            )

            return PluginResult(success=True)

        except Exception as e:
            return PluginResult(
                success=False,
                error_message=f"C2PA signing failed: {str(e)}",
                fail_generation=True,  # C2PA failure should fail the generation
            )


class WatermarkPlugin(BaseArtifactPlugin):
    """Adds a visible watermark to images."""

    name = "watermark"
    description = "Adds visible watermark to images"
    supported_artifact_types = ["image"]

    def __init__(
        self,
        watermark_image_path: str,
        position: str = "bottom-right",
        opacity: float = 0.5,
    ):
        self.watermark_image_path = Path(watermark_image_path)
        self.position = position
        self.opacity = opacity

    async def execute(self, context: PluginContext) -> PluginResult:
        try:
            from PIL import Image

            # Load artifact and watermark
            artifact = Image.open(context.file_path)
            watermark = Image.open(self.watermark_image_path)

            # Apply watermark (simplified)
            # ... watermark application logic ...

            # Save in-place
            artifact.save(context.file_path)

            return PluginResult(success=True)

        except Exception as e:
            return PluginResult(
                success=False,
                error_message=f"Watermarking failed: {str(e)}",
                fail_generation=False,  # Watermark failure is non-critical
            )


class ContentAnalysisPlugin(BaseArtifactPlugin):
    """Analyzes content and attaches metadata without modifying the file."""

    name = "content-analysis"
    description = "Runs content analysis and attaches metadata"
    supported_artifact_types = []  # All types

    async def execute(self, context: PluginContext) -> PluginResult:
        # Run analysis (e.g., NSFW detection, quality scoring)
        analysis_result = await self._analyze(context.file_path, context.artifact_type)

        return PluginResult(
            success=True,
            metadata={
                "content_analysis": analysis_result,
                "analyzed_at": datetime.utcnow().isoformat(),
            }
        )
```

### Plugin Registry

```python
class ArtifactPluginRegistry:
    """Manages registered artifact plugins."""

    def __init__(self):
        self._plugins: list[BaseArtifactPlugin] = []

    def register(self, plugin: BaseArtifactPlugin) -> None:
        """Register a plugin instance."""
        # Check for duplicate names
        if any(p.name == plugin.name for p in self._plugins):
            raise ValueError(f"Plugin with name '{plugin.name}' already registered")
        self._plugins.append(plugin)

    def get_plugins_for_artifact(self, artifact_type: str) -> list[BaseArtifactPlugin]:
        """Get ordered list of plugins that apply to the given artifact type."""
        return [p for p in self._plugins if p.supports_artifact_type(artifact_type)]

    def list_all(self) -> list[BaseArtifactPlugin]:
        """List all registered plugins in order."""
        return list(self._plugins)


# Global registry instance
plugin_registry = ArtifactPluginRegistry()
```

### Plugin Executor

```python
class ArtifactPluginExecutor:
    """Executes plugins on artifacts in the worker context."""

    def __init__(self, registry: ArtifactPluginRegistry):
        self.registry = registry

    async def execute_plugins(
        self,
        file_path: Path,
        context: PluginContext,
    ) -> tuple[Path, list[PluginResult]]:
        """
        Execute all applicable plugins on an artifact.

        Args:
            file_path: Path to the artifact file
            context: Plugin execution context

        Returns:
            Tuple of (final_file_path, list_of_results)

        Raises:
            PluginExecutionError: If a plugin fails with fail_generation=True
        """
        plugins = self.registry.get_plugins_for_artifact(context.artifact_type)
        results: list[PluginResult] = []
        current_path = file_path

        for plugin in plugins:
            # Update context with current file path
            context.file_path = current_path

            log.info(
                "executing_artifact_plugin",
                plugin_name=plugin.name,
                generation_id=context.generation_id,
                artifact_type=context.artifact_type,
            )

            try:
                result = await plugin.execute(context)
                results.append(result)

                if not result.success:
                    log.warning(
                        "plugin_execution_failed",
                        plugin_name=plugin.name,
                        error_message=result.error_message,
                        fail_generation=result.fail_generation,
                    )

                    if result.fail_generation:
                        raise PluginExecutionError(
                            plugin_name=plugin.name,
                            error_message=result.error_message,
                        )

                # Update path if plugin produced a new file
                if result.output_file_path:
                    current_path = result.output_file_path

            except Exception as e:
                if isinstance(e, PluginExecutionError):
                    raise
                # Unexpected error - treat as critical
                raise PluginExecutionError(
                    plugin_name=plugin.name,
                    error_message=f"Unexpected error: {str(e)}",
                ) from e

        return current_path, results


class PluginExecutionError(Exception):
    """Raised when a plugin fails and should fail the generation."""

    def __init__(self, plugin_name: str, error_message: str):
        self.plugin_name = plugin_name
        self.error_message = error_message
        super().__init__(f"Plugin '{plugin_name}' failed: {error_message}")
```

## Configuration

### Configuration File: `plugins.yaml`

Plugins are configured in a separate file from generators, following the same patterns:

```yaml
# plugins.yaml
strict_mode: true  # Fail startup if any plugin fails to load

plugins:
  # Class path (preferred)
  - class: "boards.plugins.c2pa.C2PASigningPlugin"
    enabled: true
    options:
      signing_key_path: "/etc/boards/c2pa-signing-key.pem"
      certificate_path: "/etc/boards/c2pa-certificate.pem"
      claim_generator: "Boards/1.0"
      include_ingredients: true

  # Watermark plugin (runs after C2PA so watermark is included in signature)
  - class: "boards.plugins.watermark.WatermarkPlugin"
    enabled: true
    options:
      watermark_image_path: "/etc/boards/watermark.png"
      position: "bottom-right"
      opacity: 0.3

  # Content analysis (non-modifying, runs last)
  - class: "boards.plugins.analysis.ContentAnalysisPlugin"
    enabled: true
    options:
      safety_threshold: 0.8

  # Entry point from external package
  - entrypoint: "myorg.custom-plugin"
    enabled: false
    options:
      custom_setting: "value"
```

### Configuration Schema

```yaml
# Top-level keys
strict_mode: bool  # Default: true. Fail startup on plugin load errors.

plugins:
  # Each plugin declaration supports these mutually exclusive forms:

  # 1. Class path (preferred)
  - class: "fully.qualified.ClassName"
    enabled: bool  # Default: true
    options: {}    # Passed as kwargs to constructor

  # 2. Entry point (external packages)
  - entrypoint: "package.plugin-name"
    enabled: bool
    options: {}

  # 3. Import (back-compat, module registers itself)
  - import: "package.module"
    enabled: bool
```

### Environment Configuration

```bash
# Point to plugins configuration
BOARDS_PLUGINS_CONFIG_PATH=/etc/boards/plugins.yaml

# Or use default location: ./plugins.yaml in working directory
```

### Plugin Entry Points

External packages expose plugins via Python entry points:

```toml
# pyproject.toml
[project.entry-points."boards.plugins"]
c2pa-signing = "boards.plugins.c2pa:C2PASigningPlugin"
myorg.custom = "myorg_boards.plugins:CustomPlugin"
```

## Worker Integration

### Execution Flow

```
Generator.generate()
    ↓
Artifact created (local temp file)
    ↓
Build PluginContext
    ↓
PluginExecutor.execute_plugins()
    ↓ (for each plugin in order)
    ├─→ Plugin.execute(context)
    │       ↓
    │   PluginResult
    │       ↓
    ├─→ If fail_generation=True and success=False → Fail generation
    ├─→ If output_file_path provided → Update current path
    └─→ Continue to next plugin
    ↓
Upload final artifact to storage
    ↓
Update generation record with plugin metadata
```

### Worker Code Integration

```python
# In GenerationWorker.execute()

async def execute(self, job: GenerationJob):
    """Execute a generation job."""
    try:
        context = await self._build_context(job)
        generator = self.registry.get(job.generator_name)

        # 1. Run generator
        output = await generator.generate(job.typed_inputs, context)

        # 2. For each artifact produced, run plugins
        for artifact_info in output.artifacts:
            plugin_context = await self._build_plugin_context(
                job=job,
                artifact_info=artifact_info,
                generator_name=generator.name,
                generator_inputs=job.typed_inputs,
            )

            try:
                final_path, plugin_results = await self.plugin_executor.execute_plugins(
                    file_path=artifact_info.local_path,
                    context=plugin_context,
                )

                # Update artifact path if plugins modified it
                artifact_info.local_path = final_path

                # Collect plugin metadata for storage
                artifact_info.plugin_metadata = self._collect_plugin_metadata(plugin_results)

            except PluginExecutionError as e:
                # Plugin requested generation failure
                await self._handle_plugin_failure(job, e)
                raise

        # 3. Upload artifacts to storage (now with plugin modifications)
        await self._upload_artifacts(output.artifacts)

        # 4. Finalize
        await self._finalize_success(job.id, output)

    except Exception as e:
        await self._handle_error(job, e)
        raise
```

## Database Schema

### Plugin Execution Tracking

```sql
-- Add plugin execution results to artifacts table
ALTER TABLE artifacts ADD COLUMN plugin_results JSONB;

-- Example plugin_results structure:
-- {
--   "executions": [
--     {
--       "plugin_name": "c2pa-signing",
--       "success": true,
--       "executed_at": "2026-01-16T10:30:00Z",
--       "metadata": { ... }
--     },
--     {
--       "plugin_name": "watermark",
--       "success": true,
--       "executed_at": "2026-01-16T10:30:01Z"
--     }
--   ]
-- }
```

### Generation Error Messages

The existing `error_message` field on the `generations` table is used to store plugin failure messages:

```python
# When a plugin fails with fail_generation=True
generation.status = "failed"
generation.error_message = f"Plugin '{plugin_name}' failed: {error_message}"
```

## Directory Structure

```
packages/backend/src/boards/
├── plugins/
│   ├── __init__.py              # Registry and base exports
│   ├── base.py                  # BaseArtifactPlugin, PluginContext, PluginResult
│   ├── registry.py              # ArtifactPluginRegistry
│   ├── executor.py              # ArtifactPluginExecutor
│   ├── loader.py                # Configuration loader (mirrors generator loader)
│   ├── exceptions.py            # PluginExecutionError, etc.
│   └── implementations/         # Built-in plugin implementations
│       ├── __init__.py
│       ├── c2pa.py              # C2PASigningPlugin
│       ├── watermark.py         # WatermarkPlugin
│       └── analysis.py          # ContentAnalysisPlugin
├── generators/
│   └── ...                      # Existing generator code
└── workers/
    └── generation.py            # Updated to call plugin executor
```

## Error Handling

### Plugin Failure Modes

| Scenario | `fail_generation` | Result |
|----------|-------------------|--------|
| C2PA signing fails | `True` | Generation marked as failed, error stored |
| Watermark fails | `False` | Generation succeeds, warning logged |
| Plugin raises exception | N/A | Treated as `fail_generation=True` |
| Plugin times out | N/A | Treated as critical failure |

### Timeout Configuration

```python
class PluginTimeoutConfig(BaseSettings):
    # Per-plugin execution timeout (seconds)
    plugin_timeout: int = 60

    # Total time allowed for all plugins on one artifact
    total_plugins_timeout: int = 300

    class Config:
        env_prefix = "BOARDS_PLUGIN_"
```

## Testing Strategy

### Unit Tests

- Plugin base class behavior
- Registry registration and ordering
- Context building
- Result handling (success, failure, file replacement)

### Integration Tests

- Full worker flow with plugins enabled
- Plugin ordering verification
- Error propagation to generation record
- File path updates through plugin chain

### Plugin-Specific Tests

- C2PA: Verify manifest is embedded and valid
- Watermark: Verify visual output
- Analysis: Verify metadata attachment

## Implementation Phases

### Phase 1: Core Infrastructure

- [ ] `BaseArtifactPlugin` abstract class
- [ ] `PluginContext` and `PluginResult` models
- [ ] `ArtifactPluginRegistry` with ordered registration
- [ ] `ArtifactPluginExecutor` with error handling
- [ ] Configuration loader for `plugins.yaml`
- [ ] Worker integration point

### Phase 2: Built-in Plugins

- [ ] C2PA signing plugin (using `c2pa-python`)
- [ ] Basic watermark plugin
- [ ] Content analysis plugin skeleton

### Phase 3: Advanced Features

- [ ] Plugin metrics and observability
- [ ] Async plugin execution (optional, for non-blocking plugins)
- [ ] Plugin dependency declaration
- [ ] Conditional plugin execution (e.g., only on certain boards)

### Phase 4: Documentation & Ecosystem

- [ ] Plugin development guide
- [ ] Entry point documentation for external packages
- [ ] Example plugins repository

## Security Considerations

### Plugin Privileges

Plugins run with full worker privileges. This is acceptable because:

1. Plugins are configured by system administrators, not end users
2. Plugin code comes from trusted sources (installed packages)
3. Workers already have broad system access

### Signing Key Security

For C2PA signing:

1. Private keys should be stored securely (file permissions, secrets manager)
2. Keys should not be logged or included in error messages
3. Consider HSM integration for production deployments

### Input Validation

Plugins should validate:

1. File path exists and is readable/writable
2. Artifact type matches expected types
3. Options are within valid ranges

## Observability

### Structured Logging

```python
log.info(
    "plugin_execution_complete",
    plugin_name=plugin.name,
    generation_id=context.generation_id,
    artifact_type=context.artifact_type,
    success=result.success,
    duration_ms=elapsed_ms,
)
```

### Metrics

```python
PLUGIN_METRICS = {
    "plugin_execution_count": "Counter",      # By plugin name, artifact type
    "plugin_execution_duration": "Histogram", # By plugin name
    "plugin_failure_count": "Counter",        # By plugin name, failure type
}
```

## Open Questions

1. **Conditional execution**: Should plugins be able to declare conditions (e.g., "only run on images over 1MB")? Or is `supported_artifact_types` sufficient?

2. **Plugin ordering dependencies**: Should plugins be able to declare "run after X" relationships, or is config-file ordering sufficient?

3. **Parallel execution**: For non-modifying plugins (like analysis), could they run in parallel? Is this worth the complexity?

4. **Manifest repository**: Should there be first-class support for writing to external manifest repositories, or is this just another plugin output?

---

**Document Version:** 1.0
**Created:** January 2026
**Status:** Draft

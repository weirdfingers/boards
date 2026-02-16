---
id: at-hyb6
status: closed
deps: [at-31t4]
links: []
created: 2026-02-14T16:25:39Z
type: task
priority: 0
assignee: cdiddy77
parent: at-3pzv
tags: [backend, ai, fal]
---
# Implement OutfitGenerator

Implement the `OutfitGenerator` composite generator class in `packages/backend`. This generator orchestrates sequential Kolors Virtual Try-On calls to apply multiple garments onto a model photo. See at-31t4 for the full pipeline design.

## Details

**Location:** `packages/backend/src/boards/generators/implementations/fal/image/outfit_generator.py`
**Generator name:** `outfit-generator`
**Artifact type:** `image`

### Input Schema

```python
class OutfitGeneratorInput(BaseModel):
    model_image: ImageArtifact              # Required
    inside_top_image: ImageArtifact | None   # Optional
    outside_top_image: ImageArtifact | None  # Optional
    bottoms_image: ImageArtifact | None      # Optional
    shoes_image: ImageArtifact | None        # Optional
    socks_image: ImageArtifact | None        # Optional
    hat_image: ImageArtifact | None          # Optional
```

Validation: at least one garment slot must be non-None.

### Internal Flow

1. Resolve all input artifacts
2. Build ordered garment list from non-None slots in layering order: Socks → Inside Top → Bottoms → Outside Top → Shoes → Hat
3. Set `current_image = model_image`
4. For each garment: upload `current_image` + garment to Fal, call Kolors, set `current_image` = result
5. Store final image as generation output

### Progress Reporting

Report per-step progress: `"Applying {slot_name} ({i}/{total})..."`

### Cost Estimation

`$0.05 * number_of_garments`

### Error Handling

If any intermediate Kolors call fails, the entire generation fails. No partial results saved.

### Registration

Add to `packages/backend/baseline-config/generators.yaml`.

## Acceptance Criteria

- [ ] `OutfitGenerator` class implemented following at-31t4 design
- [ ] Registered in `generators.yaml`
- [ ] Unit tests with mocked Kolors calls (single garment, multiple garments, validation)
- [ ] Live test with real test images validates sequential approach quality
- [ ] Multi-step progress reporting works correctly

---
id: at-dui6
status: closed
deps: [at-091e]
links: []
created: 2026-02-14T16:25:44Z
type: task
priority: 1
assignee: cdiddy77
parent: at-o0ik
tags: [backend, frontend, ai]
---
# Implement background removal on upload

When users add new images via camera, photo library, or paste, automatically run Bria Background Removal (`fal-bria-background-remove` generator) before storing the item in the wardrobe. Existing board items are already processed and should not be re-run through background removal.

## Details

### Flow

1. User adds an image via any input method (camera, file picker, paste)
2. Image is uploaded as a generation artifact
3. A Bria Background Removal generation is triggered automatically
4. The background-removed result is what gets stored/displayed in the wardrobe
5. The original (with background) can be discarded or kept as lineage

### Scope

This applies to **clothing item uploads only** (not model photos). The model photo should keep its background since Kolors needs a full human image with context.

### Design Decision

Background removal happens at **upload time**, not at generation time. By the time the OutfitGenerator runs, all garment images should already have clean transparent backgrounds.

### Open Question

Should model photos also get background removal, or should they be left as-is? (Current assumption: leave model photos as-is.)

## Acceptance Criteria

- [ ] New clothing item uploads automatically trigger Bria background removal
- [ ] Model photo uploads are NOT background-removed
- [ ] User sees processing indicator during background removal
- [ ] Background-removed image is stored and displayed in wardrobe
- [ ] Selecting existing board items does NOT re-trigger background removal

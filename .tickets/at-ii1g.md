---
id: at-ii1g
status: open
deps: [at-hyb6, at-xmtg]
links: []
created: 2026-02-02T07:03:08Z
type: task
priority: 0
assignee: cdiddy77
parent: at-o0ik
tags: [features, core]
---
# Implement outfit generation flow

Frontend flow for triggering and displaying outfit generation results. Uses the `outfit-generator` backend generator (at-hyb6) and the outfit selection state (at-xmtg).

## Details

### Triggering Generation

When the user taps "Generate Outfit", the frontend should:

1. Read current selections from outfit selection state
2. Map selections to `OutfitGeneratorInput` fields:
   - `model_image` → model slot selection (generation ID)
   - `inside_top_image` → inside top slot selection (or null)
   - `outside_top_image` → outside top slot selection (or null)
   - `bottoms_image` → bottoms slot selection (or null)
   - `shoes_image` → shoes slot selection (or null)
   - `socks_image` → socks slot selection (or null)
   - `hat_image` → hat slot selection (or null)
3. Call `createGeneration` with generator name `"outfit-generator"` and the mapped input params

### Validation (pre-submit)

- Model must be selected
- At least one garment slot must be filled
- Disable generate button otherwise

### Progress Display

The outfit generator reports multi-step progress (`"Applying inside top (1/3)..."` etc.). The UI should:
- Show which garment step is currently being processed
- Display step count (e.g., "Step 2 of 3")
- Estimated time: ~15-30 seconds per garment

### Result Display

- Show full-screen generated outfit image (post-generation state from UX-DESIGN.md)
- Provide Share and Download action buttons
- Offer Regenerate option
- Back navigation to return to outfit builder

### Tagging

Save the generated outfit with the `"outfit"` tag.

## Acceptance Criteria

- [ ] Generation triggered with correct generator name and input params
- [ ] Multi-step progress displayed to user (per-garment steps)
- [ ] Result image displayed full-screen with action buttons
- [ ] Generated outfit tagged with "outfit"
- [ ] Error states handled (generation failure, timeout)
- [ ] Regenerate creates a new generation with same selections

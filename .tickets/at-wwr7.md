---
id: at-wwr7
status: closed
deps: [at-hgpu]
links: []
created: 2026-02-02T07:01:19Z
type: task
priority: 1
assignee: cdiddy77
parent: at-q31v
tags: [frontend, ui, component]
---
# Create GenerateButton component

Build generate button with green gradient background matching mockups. Integrates with outfit selection state (at-xmtg) for enable/disable logic.

## Details

### Disabled Logic

Button is disabled unless outfit selection state `isValid()` returns true:
- Model must be selected
- At least one garment slot must be filled

### Visual States

- **Disabled**: Gray background, no interaction
- **Enabled**: Green gradient (#7FA67A), sparkle icon, "Generate Outfit" text
- **Generating**: Loading spinner with multi-step progress text
- **Error**: Red background, retry option

### Progress Display (Generating State)

The outfit generator reports per-garment progress. During generation, show:
- Current step description (e.g., "Applying bottoms...")
- Step counter (e.g., "Step 2 of 3")
- Time estimate: ~15-30 seconds per item selected

### Time Estimate

Display "~15-30s per item" beneath the button (expectation setting). With multiple items, total time scales linearly.

## Acceptance Criteria

- [ ] Button styling matches mockups (green gradient, sparkle icon)
- [ ] Disabled when model or all garments are empty
- [ ] Enabled when model + at least one garment selected
- [ ] Loading state shows multi-step progress (which garment is being applied)
- [ ] Time estimate reflects number of selected items

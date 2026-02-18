---
id: at-vgk6
status: closed
deps: [at-e1fa, at-dui6]
links: []
created: 2026-02-02T07:02:06Z
type: task
priority: 1
assignee: cdiddy77
parent: at-q31v
tags: [frontend, input]
---
# Implement paste functionality

Implement clipboard paste for images based on UploadArtifact.tsx pattern. Support pasting screenshots from clipboard. Extract images and add to wardrobe with appropriate tag.

## Details

### Flow

1. User taps "Paste" button in SelectionDrawer input methods bar (or pastes into a focused input)
2. Image is extracted from clipboard
3. Image is uploaded as a generation artifact with the appropriate slot tag
4. Background removal is triggered automatically (handled by at-dui6) for clothing items
5. Processed image appears in the wardrobe grid and is auto-selected

### Use Case

Primary use case: user screenshots a clothing item from a shopping app or website, then pastes it directly into Angie-Tryon.

## Acceptance Criteria

- [ ] Can paste images from clipboard
- [ ] Pasted images uploaded to wardrobe with correct slot tag
- [ ] Background removal triggered for clothing items (via at-dui6)
- [ ] Handles non-image clipboard content gracefully (show error/ignore)
- [ ] Works across major browsers (Chrome, Safari, Firefox)

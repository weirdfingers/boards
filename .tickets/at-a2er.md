---
id: at-a2er
status: closed
deps: [at-e1fa, at-dui6]
links: []
created: 2026-02-02T07:02:16Z
type: task
priority: 1
assignee: cdiddy77
parent: at-q31v
tags: [frontend, input, mobile]
---
# Implement camera capture

Use browser camera API for direct photo capture on mobile. Process captured image and add to wardrobe. Support both front and back cameras.

## Details

### Flow

1. User taps "Camera" button in SelectionDrawer input methods bar
2. Browser camera opens (request permission if needed)
3. User captures photo
4. Image is uploaded as a generation artifact with the appropriate slot tag
5. Background removal is triggered automatically (handled by at-dui6) for clothing items
6. Processed image appears in the wardrobe grid and is auto-selected

### Camera Options

- Support front and back cameras
- Default to back camera for clothing photos, front for model photos

## Acceptance Criteria

- [ ] Camera opens on mobile with permission request
- [ ] Photo capture works (front and back cameras)
- [ ] Captured images uploaded to wardrobe with correct slot tag
- [ ] Background removal triggered for clothing items (via at-dui6)
- [ ] Works gracefully on desktop (fallback or disable)

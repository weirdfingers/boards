---
id: at-0pyp
status: open
deps: [at-e1fa, at-dui6]
links: []
created: 2026-02-14T16:25:48Z
type: task
priority: 1
assignee: cdiddy77
parent: at-q31v
tags: [frontend, input]
---
# Implement photo library upload

Implement the "Photos" input method in the SelectionDrawer. Opens the native file picker to allow users to select images from their device and add them to the wardrobe.

## Details

### Behavior

1. User taps "Photos" button in the SelectionDrawer input method bar
2. Native file picker opens (supports image types: JPEG, PNG, WebP)
3. User selects one or more images
4. Each image is uploaded as a generation artifact with the appropriate slot tag
5. Background removal is triggered automatically (handled by at-dui6)
6. Processed images appear in the wardrobe grid

### Mobile vs Desktop

- **Mobile**: Opens native photo picker (camera roll)
- **Desktop**: Opens standard file dialog with drag-and-drop support

### Multiple Selection

Support selecting multiple files at once. Each file is processed independently.

## Acceptance Criteria

- [ ] File picker opens and accepts image files
- [ ] Selected images uploaded to wardrobe with correct slot tag
- [ ] Multiple file selection works
- [ ] Upload progress indicator shown
- [ ] Works on both mobile and desktop

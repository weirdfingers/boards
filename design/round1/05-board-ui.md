# Board Concept & UX Notes

> The toolkit **does not ship UI components by default**. It ships **hooks** that power any UI.
> Example apps demonstrate a board grid built with shadcn or plain HTML.

## Concepts
- **Board**: named collection of artifacts, collaborators, and drafts.
- **Cell**: visualization of an artifact or an in-progress job.
- **Composer**: context area where inputs are assembled (prompt, images, masks, LoRAs).

## Hooks driving the UI
- `useBoards()`, `useBoard(boardId)`, `useBoardMembers(boardId)`
- `useArtifacts(boardId, filters)`, `useArtifact(artifactId)`
- `useGeneration()` for submit/progress/cancel; `useCredits()`

## Input Affordances
- Images + prompt, image + mask (inpainting), multi-image for video, audio prompts.
- Hooks provide schemas + validation for inputs; UIs implement drawing/masking as they wish.

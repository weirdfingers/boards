# Frontend Hooks API (Draft)

> The toolkit focuses on **hooks**, not components. Hooks encapsulate data access, auth, and generation APIs.

## Conventions
- All hooks are framework-agnostic React hooks (work in Next.js, Vite, etc.).
- Data fetching uses swr-like semantics; auth is provider-pluggable.

## Auth
```ts
const { user, status, signIn, signOut, getToken } = useAuth();
```

## Boards & Artifacts
```ts
const { boards, createBoard } = useBoards();
const { board, members, addMember, removeMember } = useBoard(boardId);
const { artifacts, uploadInput, download } = useArtifacts(boardId, { type: 'image' });
```

## Generation
```ts
const { submit, progress, result, cancel, error } = useGeneration();
await submit({
  provider: 'replicate',
  model: 'flux-v1',
  inputs: { prompt, image, mask, loras: [loraId] },
  boardId
});
```

## Credits
```ts
const { balance, reserve, finalize, refund, history } = useCredits();
```

## LoRAs
```ts
const { loras, trainLora, applyToInputs } = useLoras();
```

## Extensibility
- Hooks accept an optional client config to swap transport (GraphQL/REST), base URLs, and auth token sources.

# Create Basic Template Structure

## Description

Create a minimal Next.js template that serves as a lightweight alternative to the full Baseboards application. This "basic" template should provide a starting point for developers who want to build custom applications using the Boards toolkit without the full feature set of Baseboards.

The basic template should:
- Use Next.js 14+ with App Router
- Include minimal page.tsx demonstrating Boards hooks (`useBoards`, `useCreateBoard`)
- Use shadcn/ui for basic UI components (Button, Card)
- Include Tailwind CSS configuration
- Have @weirdfingers/boards as a dependency (published package, not workspace)
- Be small in size (< 50KB when compressed)
- Include essential configuration files
- Provide a simple example of board listing and creation

This template will be packaged and published to GitHub Releases in later tickets.

## Dependencies

None

## Files to Create/Modify

Create entire directory structure at `/packages/cli-launcher/basic-template/`:

```
basic-template/
├── web/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   └── globals.css
│   │   └── components/
│   │       └── ui/
│   │           ├── button.tsx
│   │           └── card.tsx
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── components.json (shadcn config)
│   ├── postcss.config.js
│   └── .env.example
├── config/
│   ├── generators.yaml
│   └── storage_config.yaml (must use /app/data/storage for base_path)
├── extensions/
│   ├── generators/
│   │   └── README.md (instructions for adding custom generators)
│   └── plugins/
│       └── README.md (instructions for adding plugins)
├── data/
│   └── storage/.gitkeep
├── docker/
│   └── .env.example
├── compose.yaml (placeholder, will be copied from template-sources)
├── compose.web.yaml (placeholder, will be copied from template-sources)
├── Dockerfile.web (placeholder, will be copied from template-sources)
├── .gitignore
└── README.md
```

## Testing

### Installation Test
```bash
cd packages/cli-launcher/basic-template/web
pnpm install

# Verify all dependencies resolve
pnpm list @weirdfingers/boards
```

### Build Test
```bash
cd packages/cli-launcher/basic-template/web
pnpm build

# Verify TypeScript compiles successfully
# Verify Next.js build succeeds
```

### Development Test
```bash
# Mock the backend API (or point to running instance)
cd packages/cli-launcher/basic-template/web
echo 'NEXT_PUBLIC_API_URL=http://localhost:8800' > .env
echo 'NEXT_PUBLIC_GRAPHQL_URL=http://localhost:8800/graphql' >> .env

pnpm dev

# Verify app runs at http://localhost:3000
# Verify page renders without errors
```

### Hooks Test
```typescript
// Verify that Boards hooks are correctly imported and used in page.tsx
import { useBoards, useCreateBoard } from "@weirdfingers/boards";

// Verify TypeScript types work
const { boards, loading, error } = useBoards();
```

### Size Test
```bash
# Create tarball and check size
cd packages/cli-launcher
tar -czf basic-test.tar.gz basic-template/
ls -lh basic-test.tar.gz

# Should be under 50KB
```

## Acceptance Criteria

- [ ] basic-template directory created at correct path
- [ ] package.json includes @weirdfingers/boards dependency (not workspace:*)
- [ ] page.tsx demonstrates useBoards and useCreateBoard hooks
- [ ] layout.tsx includes BoardsProvider wrapper
- [ ] Basic shadcn components included (Button, Card at minimum)
- [ ] Tailwind CSS properly configured
- [ ] TypeScript compiles without errors
- [ ] pnpm install succeeds
- [ ] pnpm dev starts development server successfully
- [ ] pnpm build succeeds
- [ ] App renders board list UI
- [ ] Create board button exists and is wired to useCreateBoard
- [ ] README.md explains the template purpose
- [ ] Config files (generators.yaml, storage_config.yaml) included
  - [ ] storage_config.yaml uses `/app/data/storage` as base_path (Docker volume mount path)
- [ ] extensions/ directory structure created:
  - [ ] extensions/generators/README.md with instructions for custom generators
  - [ ] extensions/plugins/README.md with instructions for plugins (PR #231)
  - [ ] READMEs link to https://boards-docs.weirdfingers.com/docs/generators/configuration
- [ ] data/storage/.gitkeep created (ensures directory exists)
- [ ] .gitignore includes data/storage/* pattern
- [ ] .env.example files included with proper variables
- [ ] Compressed size under 50KB (excluding READMEs which add minimal size)
- [ ] No unnecessary dependencies or bloat

# Boards

Open-source creative toolkit for AI-generated content (images, video, audio, text).

## Quick Start

### Prerequisites
- Node.js 20+
- Python 3.9+
- pnpm 9+
- Docker (for local services)

### Setup

```bash
# Install dependencies
make install

# Start local services (PostgreSQL, Redis)
make docker-up

# Start development servers
make dev
```

## Project Structure

```
boards/
├── packages/
│   ├── backend-sdk/      # Python SDK for backend
│   └── frontend-hooks/   # React hooks library
├── apps/
│   └── example-nextjs/   # Example Next.js app
└── design/              # Architecture documents
```

## Development

```bash
# Run tests
make test

# Run linters
make lint

# Build all packages
make build

# Clean workspace
make clean
```

## License

MIT

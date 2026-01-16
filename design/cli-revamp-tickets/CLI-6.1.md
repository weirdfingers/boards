# Update CLI README

## Description

Update the CLI launcher's README file to document all the new commands, flags, and functionality introduced in the revamp. This includes the new template system, app-dev mode, and templates command.

The README should be the primary reference for CLI users and provide clear examples of common workflows.

## Dependencies

All previous phases (CLI should be feature-complete)

## Files to Create/Modify

- Modify `/packages/cli-launcher/README.md`

## Testing

### Completeness Test
```bash
# Verify all commands documented
grep -E "(up|down|logs|status|clean|templates|doctor)" packages/cli-launcher/README.md

# Should find all commands
```

### Example Validation Test
```bash
# Run examples from README to verify they work
# Copy-paste each example command and verify it executes correctly
```

### Link Verification Test
```bash
# Check all links in README are valid
# Manual review or use link checker tool
```

## Acceptance Criteria

### Overview Section

- [ ] Brief introduction to CLI
- [ ] Key features highlighted:
  - [ ] Multiple template options
  - [ ] Docker-based backend
  - [ ] Local development mode (--app-dev)
  - [ ] Template caching
- [ ] Installation instructions

### Installation

- [ ] npm install command:
  ```bash
  npx @weirdfingers/baseboards@latest up my-project
  ```

- [ ] Prerequisites listed:
  - [ ] Docker Desktop
  - [ ] Node.js 20+ (for --app-dev mode only)

### Quick Start

- [ ] Basic usage example:
  ```bash
  # Start with full-featured template
  npx @weirdfingers/baseboards up my-app --template baseboards

  # Minimal starter
  npx @weirdfingers/baseboards up my-app --template basic

  # Local frontend development
  npx @weirdfingers/baseboards up my-app --template basic --app-dev
  ```

### Commands Reference

- [ ] **up** command:
  - [ ] Description
  - [ ] All flags documented:
    - `--template <name>` - Template selection
    - `--app-dev` - Local frontend development
    - `--backend-version <v>` - Backend image version
    - `--attach` - Attach to logs
    - `--ports <string>` - Custom ports
    - `--fresh` - Delete existing volumes
  - [ ] Examples for each flag combination

- [ ] **down** command:
  - [ ] Description
  - [ ] Flags: `--volumes`
  - [ ] Example

- [ ] **logs** command:
  - [ ] Description
  - [ ] Flags: `-f`, `--since`, `--tail`
  - [ ] Examples with service filtering

- [ ] **status** command:
  - [ ] Description
  - [ ] Example output

- [ ] **clean** command:
  - [ ] Description
  - [ ] Flags: `--hard`
  - [ ] Warning about data loss

- [ ] **templates** command:  **(NEW)**
  - [ ] Description
  - [ ] Flags: `--refresh`, `--version`
  - [ ] Example output

- [ ] **doctor** command:
  - [ ] Description
  - [ ] Example output

### Template System

- [ ] Section explaining templates:
  - [ ] What templates are
  - [ ] Available templates (baseboards, basic)
  - [ ] How to choose between them
  - [ ] Template caching explanation

- [ ] Template comparison table:
  | Template | Size | Description | Best For |
  |----------|------|-------------|----------|
  | baseboards | ~12 MB | Full application | Quick start, demos |
  | basic | ~45 KB | Minimal starter | Custom apps, learning |

### Development Modes

- [ ] **Docker Mode** (default):
  - [ ] All services in Docker
  - [ ] Hot reload for frontend
  - [ ] Best for: Quick testing

- [ ] **App-Dev Mode** (`--app-dev`):
  - [ ] Backend in Docker, frontend local
  - [ ] Native dev server
  - [ ] Best for: Active frontend development
  - [ ] Prerequisites: Node.js, package manager

### Common Workflows

- [ ] Starting a new project
- [ ] Stopping and starting
- [ ] Viewing logs
- [ ] Cleaning up
- [ ] Using custom ports
- [ ] Local development workflow

### Troubleshooting

- [ ] Common issues and solutions:
  - [ ] Port conflicts
  - [ ] Docker not running
  - [ ] Template download failures
  - [ ] Permission errors
- [ ] Link to GitHub issues
- [ ] Link to full documentation

### Configuration

- [ ] Environment variables reference
- [ ] Config file locations
- [ ] Port configuration
- [ ] Backend version pinning

### Advanced Usage

- [ ] Custom backend versions
- [ ] Template caching management
- [ ] Offline usage (cached templates)
- [ ] CI/CD usage (non-interactive)

### Quality

- [ ] Clear, concise writing
- [ ] Code examples formatted properly
- [ ] Consistent formatting throughout
- [ ] Table of contents for easy navigation
- [ ] No broken links
- [ ] Examples are tested and work
- [ ] Markdown properly formatted

### Removal of Old Content

- [ ] Remove references to `--prod` flag
- [ ] Remove references to `--dev` flag
- [ ] Remove outdated workflow examples
- [ ] Remove references to bundled templates

### Links

- [ ] Link to main documentation site
- [ ] Link to template source code
- [ ] Link to GitHub repository
- [ ] Link to issues page
- [ ] Link to releases page

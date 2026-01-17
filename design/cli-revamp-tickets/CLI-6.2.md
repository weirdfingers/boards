# Update Main Documentation Site

## Description

Update the documentation website ([apps/docs](apps/docs)) to reflect all the CLI revamp changes. This includes updating the CLI documentation pages, adding migration guides, and updating any examples that reference the CLI.

The docs site is the primary source of truth for users, so it must be comprehensive and accurate.

**Critical files requiring immediate attention:**
- `/apps/docs/docs/baseboards/overview.md` - Contains outdated architecture, wrong ports (8088 vs 8800), removed flags (--prod, --dev), and references to removed compose.dev.yaml
- `/apps/docs/docs/installation/installing-baseboards.md` - Wrong API port throughout (8088 vs 8800), uses old `update` command instead of `upgrade`, missing template and app-dev mode documentation

These files are user-facing quick start documentation and must be updated to prevent user confusion.

## Dependencies

- CLI-6.1 (CLI README should be complete for reference)

## Files to Create/Modify

- Modify `/apps/docs/docs/cli/*.md` (all CLI documentation pages)
- Create `/apps/docs/docs/migration-v0.8.md` (new migration guide)
- **Modify `/apps/docs/docs/baseboards/overview.md`** (critical - outdated architecture and commands)
- **Modify `/apps/docs/docs/installation/installing-baseboards.md`** (critical - wrong ports and commands)
- Update any other pages that reference CLI usage

## Testing

### Build Test
```bash
cd apps/docs
pnpm build

# Should build without errors
# Check for broken links in output
```

### Local Preview Test
```bash
cd apps/docs
pnpm start

# Navigate to CLI docs
# Verify all pages load
# Verify all links work
# Verify examples are correct
```

### Link Verification Test
```bash
# Use docusaurus link checker or manual review
# Verify no broken internal/external links
```

## Acceptance Criteria

### Critical File Updates

#### `/apps/docs/docs/baseboards/overview.md`

- [ ] **Architecture section**:
  - [ ] Update to reflect pre-built Docker images (not local builds)
  - [ ] Add template system explanation
  - [ ] Update service descriptions to match new architecture
  - [ ] Add diagram showing default mode vs app-dev mode
  - [ ] Remove references to local backend builds

- [ ] **Services section**:
  - [ ] Fix API port from 8088 to 8800
  - [ ] Update web service description to mention production build
  - [ ] Add note about pre-built backend images
  - [ ] Update worker description to clarify image usage

- [ ] **Configuration section**:
  - [ ] Update environment variables examples
  - [ ] Add section on template selection
  - [ ] Add section on development modes (default vs --app-dev)
  - [ ] Update storage configuration paths to match Docker volumes

- [ ] **CLI Commands section**:
  - [ ] Remove `--prod` flag from all examples
  - [ ] Remove `--dev` flag from all examples
  - [ ] Add `--template` flag examples
  - [ ] Add `--app-dev` flag examples
  - [ ] Replace `baseboards update` with `baseboards upgrade`
  - [ ] Add `baseboards templates` command
  - [ ] Update port examples to use 8800 (not 8088)

- [ ] **Remove outdated references**:
  - [ ] Remove references to `compose.dev.yaml` (merged into base)
  - [ ] Remove references to hot-reload in default mode
  - [ ] Update "Production Deployment" section for new architecture

#### `/apps/docs/docs/installation/installing-baseboards.md`

- [ ] **"What You'll Get" section**:
  - [ ] Fix GraphQL API port from 8088 to 8800
  - [ ] Add note about pre-built Docker images

- [ ] **System Requirements**:
  - [ ] Update ports from 8088 to 8800
  - [ ] Add note about template download bandwidth

- [ ] **Installation section**:
  - [ ] Update step descriptions to mention template selection
  - [ ] Add interactive template selection flow example
  - [ ] Update success message to show correct port (8800)

- [ ] **Configuration section**:
  - [ ] Fix API port in all examples (8088 → 8800)
  - [ ] Add section on template options
  - [ ] Add section on --app-dev mode for frontend development

- [ ] **"Using Baseboards" section**:
  - [ ] Replace `baseboards update` with `baseboards upgrade`
  - [ ] Add examples for new upgrade command with flags (--dry-run, --version)

- [ ] **Troubleshooting section**:
  - [ ] Update port numbers in all examples (8088 → 8800)
  - [ ] Add troubleshooting for template download issues
  - [ ] Add troubleshooting for Docker image pull issues

### CLI Documentation Pages

- [ ] **Getting Started** page:
  - [ ] Updated installation instructions
  - [ ] Quick start with new templates
  - [ ] Prerequisites clearly listed
  - [ ] First-time user flow

- [ ] **Commands Reference** page:
  - [ ] All commands documented (up, down, logs, status, clean, templates, doctor)
  - [ ] New flags documented (--template, --app-dev)
  - [ ] Removed flags noted as deprecated (--prod, --dev)
  - [ ] Examples for each command
  - [ ] Return value/exit codes documented

- [ ] **Templates Guide** page (new or updated):
  - [ ] What are templates?
  - [ ] Available templates (baseboards, basic)
  - [ ] How to choose
  - [ ] Template structure overview
  - [ ] Custom templates (future)

- [ ] **Development Modes** page (new or updated):
  - [ ] Docker mode (default)
  - [ ] App-dev mode (--app-dev)
  - [ ] Comparison table
  - [ ] When to use each
  - [ ] Switching between modes

- [ ] **Configuration** page:
  - [ ] Environment variables
  - [ ] Port configuration
  - [ ] Backend version pinning
  - [ ] Template caching
  - [ ] Config file locations

- [ ] **Troubleshooting** page:
  - [ ] Common issues
  - [ ] Template download problems
  - [ ] Docker issues
  - [ ] Port conflicts
  - [ ] Permission errors
  - [ ] Cache management

### Migration Guide

- [ ] Create **Migration from v0.7.0 to v0.8.0** page:
  - [ ] Breaking changes summary:
    - [ ] --prod flag removed (single mode now)
    - [ ] --dev flag removed (no hot-reload by default, use --app-dev for frontend)
    - [ ] Backend runs from pre-built Docker image (not local build)
    - [ ] Templates downloaded from GitHub Releases (not bundled)
    - [ ] New project structure with extensions/ directory
    - [ ] API port standardized to 8800 (was inconsistently 8088 in docs)
    - [ ] `baseboards update` command replaced with `baseboards upgrade`
    - [ ] New `--template` flag for template selection
    - [ ] New `--app-dev` flag for local frontend development
    - [ ] compose.dev.yaml merged into compose.yaml
  - [ ] Step-by-step migration:
    1. Back up configuration files (api/.env, config/, extensions/)
    2. Back up generated media (data/storage/)
    3. Stop and clean old scaffold (baseboards down --volumes)
    4. Update CLI (npx @weirdfingers/baseboards@latest)
    5. Re-scaffold with new CLI (baseboards up --template baseboards)
    6. Restore configuration files
    7. Verify services start correctly
    8. Test generators with API keys
  - [ ] What changed and why (link to design doc)
  - [ ] Benefits of upgrading (faster startup, better templates, upgrade support)
  - [ ] Breaking changes impact assessment (data preserved, config preserved, custom code must be re-applied)

### Examples and Tutorials

- [ ] Update all code examples that use CLI
- [ ] Update screenshots (if any)
- [ ] Update tutorial pages
- [ ] Verify example projects still work

### API Documentation

- [ ] Update any API docs that reference CLI
- [ ] Update environment variable docs
- [ ] Update deployment guides (if affected)

### Navigation

- [ ] Add new pages to sidebar
- [ ] Update breadcrumbs
- [ ] Update search index
- [ ] Verify page ordering makes sense

### Content Quality

- [ ] Clear, beginner-friendly writing
- [ ] Technical accuracy
- [ ] Code examples tested
- [ ] Consistent terminology
- [ ] Proper markdown formatting
- [ ] Syntax highlighting correct
- [ ] Images/diagrams clear (if any)

### SEO and Metadata

- [ ] Page titles descriptive
- [ ] Meta descriptions added
- [ ] Keywords appropriate
- [ ] Canonical URLs set

### Cross-Links

- [ ] Link between related pages
- [ ] Link to GitHub repository
- [ ] Link to npm package
- [ ] Link to Docker images
- [ ] Link to issue tracker

### Removal of Old Content

- [ ] Archive or remove v0.7.0 specific docs
- [ ] Update version numbers throughout
- [ ] Remove references to removed features
- [ ] Update comparison tables

### Accessibility

- [ ] Alt text for images
- [ ] Proper heading hierarchy
- [ ] Code examples have labels
- [ ] Links descriptive

### Version Selector

- [ ] Ensure version dropdown works (if applicable)
- [ ] Latest version is v0.8.0
- [ ] Old versions archived properly

### Search

- [ ] Verify search finds new pages
- [ ] Verify search terms work
- [ ] Test common queries

### Mobile Responsive

- [ ] Docs render well on mobile
- [ ] Code examples scrollable
- [ ] Navigation usable

### Quality Checks

- [ ] No broken links
- [ ] No typos (spell check)
- [ ] No placeholder text
- [ ] No TODO comments
- [ ] Builds without warnings

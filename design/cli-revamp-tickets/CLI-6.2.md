# Update Main Documentation Site

## Description

Update the documentation website ([apps/docs](apps/docs)) to reflect all the CLI revamp changes. This includes updating the CLI documentation pages, adding migration guides, and updating any examples that reference the CLI.

The docs site is the primary source of truth for users, so it must be comprehensive and accurate.

## Dependencies

- CLI-6.1 (CLI README should be complete for reference)

## Files to Create/Modify

- Modify `/apps/docs/docs/cli/*.md` (all CLI documentation pages)
- Create `/apps/docs/docs/migration-v0.8.md` (new migration guide)
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
    - [ ] --prod flag removed
    - [ ] --dev flag removed (now default)
    - [ ] Backend runs from Docker image
    - [ ] Templates downloaded from releases
    - [ ] New project structure
  - [ ] Step-by-step migration:
    1. Back up configuration files
    2. Stop and clean old scaffold
    3. Re-scaffold with new CLI
    4. Restore configuration
  - [ ] What changed and why
  - [ ] Benefits of upgrading
  - [ ] Breaking changes impact assessment

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

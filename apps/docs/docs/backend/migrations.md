---
sidebar_position: 2
---

# Database Migrations

Boards uses a **SQL DDL-first migration system** where SQL schema files are the single source of truth, and SQLAlchemy models are automatically generated.

## Migration Philosophy

Traditional ORMs often lead to **schema drift** where the database schema and ORM models become out of sync. Boards solves this with:

1. **SQL DDL files** as the authoritative schema definition
2. **Auto-generated SQLAlchemy models** from the actual database
3. **Auto-generated migration scripts** by diffing schemas
4. **Version-controlled schema history** for reproducibility

## Quick Workflow

```bash
# 1. Edit schema files
vim migrations/schemas/002_add_feature.sql

# 2. Generate migration scripts  
python scripts/generate_migration.py --name add_feature

# 3. Apply migration
psql boards_dev < migrations/generated/*_add_feature_up.sql

# 4. Regenerate models
python scripts/generate_models.py
```

## Detailed Workflow

### Step 1: Edit Schema Files

Schema files in `migrations/schemas/` are processed alphabetically:

```sql
-- migrations/schemas/002_add_user_preferences.sql
-- Add user preferences and notification settings

CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    theme VARCHAR(20) DEFAULT 'light' CHECK (theme IN ('light', 'dark')),
    timezone VARCHAR(50) DEFAULT 'UTC',
    email_notifications BOOLEAN DEFAULT TRUE,
    push_notifications BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- Indexes for performance
CREATE INDEX idx_user_preferences_user ON user_preferences(user_id);
CREATE INDEX idx_user_preferences_theme ON user_preferences(theme);

-- Trigger for updated_at
CREATE TRIGGER update_user_preferences_updated_at 
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add new column to existing table
ALTER TABLE boards ADD COLUMN view_count INTEGER DEFAULT 0;
CREATE INDEX idx_boards_view_count ON boards(view_count);
```

### Step 2: Generate Migration Scripts

The migration generator compares your current database with the target schema:

```bash
python scripts/generate_migration.py --name add_user_preferences
```

This creates two files:
- `migrations/generated/20240830_143022_add_user_preferences_up.sql` - Apply changes
- `migrations/generated/20240830_143022_add_user_preferences_down.sql` - Rollback changes

### Step 3: Review Generated Migration

Always review the generated migration before applying:

```bash
# Review the UP migration
cat migrations/generated/*add_user_preferences_up.sql

# Review the DOWN migration (for rollback)
cat migrations/generated/*add_user_preferences_down.sql
```

### Step 4: Apply Migration

Apply the migration to your database:

```bash
# Apply to development database
psql boards_dev < migrations/generated/*add_user_preferences_up.sql

# Verify the changes
psql boards_dev -c "\dt user_preferences"
```

### Step 5: Regenerate SQLAlchemy Models

Update the Python models to match the new schema:

```bash
python scripts/generate_models.py
```

This updates `src/boards/database/models.py` with the new table definitions.

## Migration Patterns

### Adding a New Table

```sql
-- 003_add_analytics.sql
CREATE TABLE page_views (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    page_path VARCHAR(255) NOT NULL,
    viewed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_page_views_tenant ON page_views(tenant_id);
CREATE INDEX idx_page_views_user ON page_views(user_id);
CREATE INDEX idx_page_views_path ON page_views(page_path);
CREATE INDEX idx_page_views_date ON page_views(viewed_at);
```

### Adding Columns to Existing Tables

```sql
-- 004_add_board_features.sql
ALTER TABLE boards ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;
ALTER TABLE boards ADD COLUMN archived_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE boards ADD COLUMN tags TEXT[] DEFAULT '{}';

-- Add indexes
CREATE INDEX idx_boards_archived ON boards(is_archived);
CREATE INDEX idx_boards_archived_at ON boards(archived_at);
CREATE INDEX idx_boards_tags ON boards USING GIN(tags);

-- Add constraint
ALTER TABLE boards ADD CONSTRAINT check_archived_date 
    CHECK (is_archived = FALSE OR archived_at IS NOT NULL);
```

### Creating Indexes

```sql
-- 005_optimize_queries.sql
-- Composite index for board member queries
CREATE INDEX idx_board_members_board_role ON board_members(board_id, role);

-- Partial index for active generations
CREATE INDEX idx_generations_active ON generations(board_id, created_at) 
    WHERE status IN ('pending', 'processing');

-- Text search index
CREATE INDEX idx_boards_title_search ON boards USING gin(to_tsvector('english', title));
```

### Modifying Column Types

```sql
-- 006_extend_varchar_limits.sql
ALTER TABLE users ALTER COLUMN display_name TYPE VARCHAR(500);
ALTER TABLE boards ALTER COLUMN title TYPE VARCHAR(500);
ALTER TABLE generations ALTER COLUMN generator_name TYPE VARCHAR(200);
```

## Rollback Procedures

### Using DOWN Migration

```bash
# Apply the rollback migration
psql boards_dev < migrations/generated/*add_user_preferences_down.sql

# Regenerate models to reflect rollback
python scripts/generate_models.py
```

### Database Restore

```bash
# If you have a backup
dropdb boards_dev
createdb boards_dev
psql boards_dev < backup.sql
```

## Production Deployment

### Pre-deployment Checklist

- [ ] Migration tested on development database
- [ ] Migration tested on staging with production-like data
- [ ] Backup created before deployment
- [ ] Rollback plan prepared
- [ ] Performance impact assessed

### Zero-downtime Migrations

For large tables, consider these strategies:

```sql
-- Step 1: Add nullable column
ALTER TABLE large_table ADD COLUMN new_column VARCHAR(255);

-- Step 2: Backfill data (in application code)
-- Step 3: Add NOT NULL constraint
ALTER TABLE large_table ALTER COLUMN new_column SET NOT NULL;
```

```sql
-- Non-blocking index creation
CREATE INDEX CONCURRENTLY idx_large_table_new_column ON large_table(new_column);
```

## Best Practices

### ✅ DO:
- Test migrations on development/staging first
- Use descriptive migration names
- Include proper indexes and constraints
- Document complex changes
- Create backups before production migrations
- Use transactions for complex migrations

### ❌ DON'T:
- Apply migrations directly to production without testing
- Create migrations that can't be rolled back
- Forget to regenerate models after schema changes
- Skip index creation for new columns
- Make breaking changes without a migration strategy

## Troubleshooting

### Migration fails with constraint violation

```bash
# Check existing data
psql boards_dev -c "SELECT COUNT(*) FROM users WHERE email IS NULL;"

# Fix data first, then retry migration
psql boards_dev -c "UPDATE users SET email = 'unknown@example.com' WHERE email IS NULL;"
```

### Generated models are incorrect

```bash
# Clear and regenerate
rm src/boards/database/models.py
python scripts/generate_models.py
```

### Schema conflicts

```bash
# Compare schemas manually
pg_dump boards_dev --schema-only > current_schema.sql
# Apply DDL files to temp database and compare
```

## File Structure

```
packages/backend/
├── migrations/
│   ├── schemas/              # DDL source files (edit these)
│   │   ├── 001_initial_schema.sql
│   │   ├── 002_add_user_preferences.sql
│   │   └── 003_add_analytics.sql
│   ├── generated/            # Generated migration scripts (don't edit)
│   │   ├── 20240830_143022_add_user_preferences_up.sql
│   │   ├── 20240830_143022_add_user_preferences_down.sql
│   │   └── ...
│   └── migration_runner.py   # Migration application tool
├── scripts/
│   ├── generate_models.py    # DDL → SQLAlchemy models
│   └── generate_migration.py # Schema diff → migration scripts
└── src/boards/database/
    └── models.py             # Generated SQLAlchemy models (don't edit)
```

Remember: The schema files in `migrations/schemas/` are your source of truth. Everything else is generated!
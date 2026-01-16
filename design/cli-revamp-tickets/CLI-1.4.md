# Verify Image Works with Current Setup

## Description

Test that the published Docker image works as a drop-in replacement for the current local build setup. This validates that the image can be used in existing compose files and the CLI workflow without breaking changes.

This is the final validation step for Phase 1 before we can proceed to Phase 3 (updating compose files to use the pre-built image). We need to ensure:
- Image can be pulled from both registries
- Image works with current environment variable configuration
- Database migrations run successfully
- Worker starts and processes jobs
- Health checks pass
- No regressions compared to local build

This ticket doesn't modify any code - it's purely validation and testing.

## Dependencies

- CLI-1.1 (Dockerfile must exist and work)
- CLI-1.2 (Image must be published)
- CLI-1.3 (Credentials must be configured)

## Files to Create/Modify

None (testing only)

## Testing

### Pull Image Test
```bash
# Pull from GHCR
docker pull ghcr.io/weirdfingers/boards-backend:0.7.0

# Pull from Docker Hub
docker pull weirdfingers/boards-backend:0.7.0

# Verify both pulls succeed
docker images | grep boards-backend
```

### Local Compose Test
Create a test compose file using the published image:
```yaml
# test-compose.yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: boards
      POSTGRES_PASSWORD: boards_dev
      POSTGRES_DB: boards_dev
    ports:
      - "5433:5432"

  cache:
    image: redis:7

  api:
    image: ghcr.io/weirdfingers/boards-backend:0.7.0
    command: ["uvicorn", "boards.api.app:app", "--host", "0.0.0.0", "--port", "8800", "--reload"]
    environment:
      BOARDS_DATABASE_URL: postgresql://boards:boards_dev@db:5432/boards_dev
      BOARDS_REDIS_URL: redis://cache:6379/0
      BOARDS_API_PORT: 8800
      BOARDS_JWT_SECRET: test-secret-key-32-chars-long
    depends_on:
      - db
      - cache
    ports:
      - "8800:8800"

  worker:
    image: ghcr.io/weirdfingers/boards-backend:0.7.0
    command: ["dramatiq-gevent", "boards.workers.actors:broker", "--processes", "1", "--threads", "50"]
    environment:
      BOARDS_DATABASE_URL: postgresql://boards:boards_dev@db:5432/boards_dev
      BOARDS_REDIS_URL: redis://cache:6379/0
    depends_on:
      - db
      - cache
```

```bash
# Start services
docker compose -f test-compose.yaml up -d

# Wait for services to be healthy
sleep 10

# Check all services are running
docker compose -f test-compose.yaml ps
```

### Migrations Test
```bash
# Run migrations using the image
docker compose -f test-compose.yaml exec api \
  alembic upgrade head

# Verify migrations ran successfully
docker compose -f test-compose.yaml exec api \
  alembic current
```

### API Health Check Test
```bash
# Test health endpoint
curl http://localhost:8800/health

# Should return 200 OK
# Expected response: {"status":"ok"}
```

### Worker Test
```bash
# Verify worker process is running
docker compose -f test-compose.yaml exec worker pgrep -f dramatiq

# Check worker logs for startup messages
docker compose -f test-compose.yaml logs worker | grep -i "worker"
```

### Environment Variables Test
Verify all expected environment variables work:
```bash
# Test API can connect to database
docker compose -f test-compose.yaml exec api python -c "
from boards.database import get_db_session
session = next(get_db_session())
print('Database connection successful')
"

# Test worker can connect to Redis
docker compose -f test-compose.yaml exec worker python -c "
import redis
r = redis.from_url('redis://cache:6379/0')
r.ping()
print('Redis connection successful')
"
```

### Config Mounts Test
Test that external config files can be mounted:
```bash
# Create test config
mkdir -p test-config
echo "generators: []" > test-config/generators.yaml

# Update compose to mount config
# Add to api service:
#   volumes:
#     - ./test-config:/app/config:ro

# Restart and verify config is accessible
docker compose -f test-compose.yaml restart api
docker compose -f test-compose.yaml exec api ls -la /app/config/generators.yaml
```

### Cleanup
```bash
# Stop and remove test containers
docker compose -f test-compose.yaml down -v
```

## Acceptance Criteria

- [ ] Image pulls successfully from GHCR
- [ ] Image pulls successfully from Docker Hub
- [ ] Both amd64 and arm64 architectures available (verify with `docker manifest inspect`)
- [ ] API service starts successfully using the image
- [ ] Worker service starts successfully using the image
- [ ] Database migrations run without errors
- [ ] API health check endpoint returns 200 OK
- [ ] Worker process runs and can be verified with pgrep
- [ ] API can connect to PostgreSQL database
- [ ] Worker can connect to Redis cache
- [ ] Environment variables are correctly parsed
- [ ] External config files can be mounted to /app/config
- [ ] No regressions compared to local build behavior
- [ ] All current CLI scaffolded projects would work with this image
- [ ] Image size is reasonable (document actual size in ticket comments)

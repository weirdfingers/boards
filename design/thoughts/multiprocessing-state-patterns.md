# Managing Module-Level State in Multiprocessing

**Author:** Design Notes
**Date:** October 24, 2025
**Status:** Best Practices

## The Problem

When using multiprocessing in Python (as Dramatiq does for workers), each process gets its own **independent copy** of module-level variables. They start with empty/initial state and don't share memory with the parent process or other worker processes.

This is fundamentally different from multithreading, where threads share the same memory space.

### Common Symptom

```python
# In parent process or main thread
registry = GeneratorRegistry()
load_generators_from_config()  # Registers 10 generators
print(len(registry))  # → 10

# In worker process (spawned by Dramatiq)
print(len(registry))  # → 0 (empty!)
```

**Why?** The worker process is a fresh Python interpreter that imports the modules from scratch. Module-level initialization code may or may not run depending on how it's structured.

## Multiprocessing vs Multithreading

| Aspect | Multithreading | Multiprocessing |
|--------|---------------|-----------------|
| **Memory** | Shared (same process) | Isolated (separate processes) |
| **State sharing** | Automatic | Must be explicit |
| **Race conditions** | ❌ Major risk - requires locks everywhere | ✅ Impossible by default (isolated state) |
| **Debugging** | 🔥 Heisenbugs, non-deterministic | ✅ Deterministic, isolated failures |
| **Python GIL** | ❌ Limits parallelism | ✅ True parallelism |
| **Performance** | Fast (no IPC overhead) | Slower (serialization) |
| **Common bugs** | Data races, deadlocks, corrupted state | Forgot to initialize, state not shared |

**Bottom line:** Multiprocessing's "confusion tax" (state isolation) is far better than multithreading's "race condition tax" (data corruption and non-deterministic bugs).

## Pattern 1: Module-Level Lazy Initialization ⭐

**Best for:** Simple registries, caches, connection pools that need one-time setup.

### Implementation

```python
# In actors.py (worker module)
from ..generators.loader import load_generators_from_config
from ..generators.registry import registry as generator_registry

# This runs once when each worker process imports the module
load_generators_from_config()
logger.info(
    "Generators loaded",
    count=len(generator_registry),
    generators=generator_registry.list_names(),
)

@actor
async def process_generation(generation_id: str) -> None:
    # Registry is already populated
    generator = generator_registry.get(name)
    await generator.generate(...)
```

### How It Works

- Module-level code runs **once per process** at import time
- Worker processes import the module when they start
- Each process gets its own initialized registry
- No per-job overhead

### Pros

✅ Simple and explicit
✅ No overhead per job
✅ Works with fork and spawn process models
✅ Easy to understand

### Cons

❌ Easy to forget in new modules
❌ No enforcement mechanism
❌ Not obvious to new developers
❌ Can't control initialization order across modules

### Example in Boards

We initially used this pattern in `boards/workers/actors.py` before migrating to middleware (Pattern 2).

---

## Pattern 2: Framework Middleware/Lifecycle Hooks ⭐⭐⭐

**Best for:** When your framework provides initialization hooks (Dramatiq, Celery, etc.).

### Implementation

```python
# In workers/middleware.py
from dramatiq.middleware import Middleware
from ..generators.loader import load_generators_from_config
from ..generators.registry import registry as generator_registry

class GeneratorLoaderMiddleware(Middleware):
    """Load generators when worker process starts."""

    def before_worker_boot(self, broker, worker):
        """Called once per worker process at startup."""
        logger.info("Loading generators in worker process")
        load_generators_from_config()
        logger.info(
            "Generators loaded",
            count=len(generator_registry),
            generators=generator_registry.list_names(),
        )

# In actors.py
broker = RedisBroker(url=settings.redis_url)
broker.add_middleware(AsyncIO())
broker.add_middleware(GeneratorLoaderMiddleware())  # ← Explicit initialization
```

### How It Works

- Framework calls middleware hooks at specific lifecycle points
- `before_worker_boot` runs once per worker process, before processing any jobs
- Middleware is registered explicitly in broker setup
- Centralized initialization logic

### Pros

✅ **Explicit lifecycle management** - clear when/where initialization happens
✅ **Self-documenting** - middleware list shows initialization steps
✅ **Framework-integrated** - uses proper lifecycle hooks
✅ **Discoverable** - easy for new developers to find
✅ **Centralized** - one place to add worker initialization
✅ **Testable** - can test middleware in isolation

### Cons

❌ Slightly more boilerplate
❌ Requires understanding framework's middleware API
❌ Framework-specific (not portable)

### Example in Boards

This is our **current pattern** for generator loading in `boards/workers/middleware.py`. This pattern is superior to Pattern 1 for production systems.

---

## Pattern 3: Lazy Initialization with Getters

**Best for:** When you want initialization to happen on first use, not at import time.

### Implementation

```python
# In registry.py
class GeneratorRegistry:
    _instance: GeneratorRegistry | None = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _ensure_loaded(self):
        """Load generators on first access."""
        if not self._initialized:
            from .loader import load_generators_from_config
            load_generators_from_config()
            self._initialized = True

    def get(self, name: str):
        self._ensure_loaded()
        return self._generators.get(name)

    def list_all(self):
        self._ensure_loaded()
        return list(self._generators.values())

# Usage in actors
@actor
async def process_generation(generation_id: str) -> None:
    # First call triggers initialization
    generator = generator_registry.get(name)
```

### How It Works

- Registry checks if loaded on every access
- First access triggers initialization
- Subsequent accesses use cached state
- Initialization is deferred until needed

### Pros

✅ No explicit initialization needed
✅ Happens automatically in each process
✅ Works across all process spawn methods
✅ Can't forget to initialize

### Cons

❌ Small overhead on every access (check if initialized)
❌ Makes initialization timing unpredictable
❌ Harder to debug (hidden initialization)
❌ Can't control when initialization happens
❌ Error handling is awkward (errors happen on first use)

### When to Use

- Configuration objects that are read-only after loading
- Caches that can be built on-demand
- Cases where you can't control import order

---

## Pattern 4: Dependency Injection (Most Testable)

**Best for:** Maximizing testability and making dependencies explicit.

### Implementation

```python
# In executors.py (business logic, not actors)
async def execute_generation(
    generation_id: str,
    registry: GeneratorRegistry,  # ← Explicit dependency
    db_session: AsyncSession,
    progress_publisher: ProgressPublisher,
) -> None:
    """Pure function with explicit dependencies."""
    generator = registry.get(generator_name)
    # ... do work ...

# In workers/actors.py
_registry: GeneratorRegistry | None = None

def _get_registry() -> GeneratorRegistry:
    """Get or initialize registry (module-level singleton)."""
    global _registry
    if _registry is None:
        load_generators_from_config()
        _registry = registry
    return _registry

@actor
async def process_generation(generation_id: str) -> None:
    """Actor is thin wrapper that handles initialization."""
    reg = _get_registry()
    async with get_async_session() as db:
        publisher = ProgressPublisher()
        await execute_generation(generation_id, reg, db, publisher)
```

### How It Works

- Business logic receives dependencies as parameters (pure functions)
- Actors/entry points handle initialization and dependency wiring
- Core logic has no global state or imports
- Tests can inject mocks easily

### Pros

✅ **Extremely testable** - can inject mocks without patching
✅ **Clear dependencies** - function signature shows what's needed
✅ **Reusable logic** - same function works in different contexts
✅ **No hidden coupling** - all dependencies explicit
✅ **Easy to refactor** - change initialization without touching logic

### Cons

❌ More boilerplate (passing parameters)
❌ More indirection (separation of concerns)
❌ Actors become thin wrappers
❌ Can feel over-engineered for simple cases

### When to Use

- Complex business logic that needs thorough testing
- Code that will be reused in multiple contexts (CLI, API, workers)
- Teams with strong testing culture
- Long-term maintainability is critical

---

## Pattern Comparison Summary

| Pattern | Setup Complexity | Testability | Discoverability | Production-Ready |
|---------|-----------------|-------------|-----------------|------------------|
| **Module-level lazy** | ⭐ Simple | ⭐⭐ Medium | ⭐ Hidden | ⭐⭐ Good |
| **Middleware hooks** | ⭐⭐ Medium | ⭐⭐⭐ Good | ⭐⭐⭐ Explicit | ⭐⭐⭐ Excellent |
| **Lazy getters** | ⭐⭐ Medium | ⭐⭐ Medium | ⭐ Hidden | ⭐⭐ Good |
| **Dependency injection** | ⭐⭐⭐ Complex | ⭐⭐⭐ Excellent | ⭐⭐⭐ Explicit | ⭐⭐⭐ Excellent |

## Recommendations for Boards

### Current Implementation (October 2024)

We use **Pattern 2: Middleware Hooks** for generator loading:

```python
# workers/middleware.py
class GeneratorLoaderMiddleware(Middleware):
    def before_worker_boot(self, broker, worker):
        load_generators_from_config()

# workers/actors.py
broker.add_middleware(GeneratorLoaderMiddleware())
```

This is the **recommended pattern** for our use case because:

1. ✅ **Explicit** - middleware list documents all initialization
2. ✅ **Framework-native** - uses Dramatiq's proper lifecycle hooks
3. ✅ **Discoverable** - new developers can see the middleware setup
4. ✅ **Centralized** - one place for all worker initialization
5. ✅ **No overhead** - initialization happens once per worker at startup

### Future Considerations

If we need more testability or want to reuse generation logic outside workers (e.g., in a CLI tool), consider migrating to **Pattern 4: Dependency Injection**:

- Extract `execute_generation()` as a pure function
- Keep actors as thin wrappers that wire dependencies
- Makes testing much easier without Dramatiq mocks

### Anti-Patterns to Avoid

❌ **Don't initialize in CLI parent process** - worker processes won't see it
❌ **Don't use threading locks** - not needed with multiprocessing
❌ **Don't use shared memory** - complex, error-prone, usually unnecessary
❌ **Don't rely on module import side effects** - use explicit initialization

## Process Spawn Methods

Python's multiprocessing has different spawn methods:

### Fork (Linux default, deprecated on macOS)

- **How it works:** Copies parent process memory (copy-on-write)
- **Module state:** Inherited from parent
- **Pros:** Fast, memory-efficient
- **Cons:** Can corrupt file descriptors, SSL connections, database pools
- **macOS:** Deprecated in Python 3.8+, will be removed

### Spawn (macOS/Windows default)

- **How it works:** Fresh Python interpreter
- **Module state:** Starts empty, must be initialized
- **Pros:** Clean state, no corruption issues
- **Cons:** Slower startup, higher memory usage
- **Pattern requirement:** MUST use explicit initialization

### Recommendation

**Always use spawn mode** or write code that works with spawn (like Patterns 2-4). This ensures:

1. ✅ Works on all platforms (macOS, Linux, Windows)
2. ✅ No subtle bugs from inherited state
3. ✅ Future-proof (fork is being deprecated)
4. ✅ Clean worker processes

To enforce spawn mode:

```python
# In cli.py
import multiprocessing as mp
mp.set_start_method('spawn', force=True)
```

However, our current approach (Pattern 2 with middleware) works with **any** spawn method, which is ideal.

## Real-World Examples in Boards

### Example 1: Redis Connection Pool

Our `RedisPoolManager` is a singleton that initializes per-process:

```python
# redis_pool.py
class RedisPoolManager:
    _instance: RedisPoolManager | None = None
    _pool: ConnectionPool | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

This works because:
- Each process gets its own connection pool (good - connections aren't shared)
- Initialization happens on first use in each process
- No shared state between processes

### Example 2: Generator Registry (Current)

We load generators via middleware (Pattern 2):

```python
# workers/middleware.py
class GeneratorLoaderMiddleware(Middleware):
    def before_worker_boot(self, broker, worker):
        load_generators_from_config()

# workers/actors.py
broker.add_middleware(GeneratorLoaderMiddleware())
```

This ensures:
- Generators loaded once per worker at startup
- Explicit initialization visible in middleware list
- Framework-managed lifecycle

### Example 3: SQLAlchemy Sessions

We use context managers for sessions (good pattern):

```python
@actor
async def process_generation(generation_id: str):
    async with get_async_session() as session:
        # Session is per-job, not shared
        gen = await jobs_repo.get_generation(session, generation_id)
```

This is correct because:
- Sessions are per-job, not module-level
- No shared state
- Proper cleanup via context manager

## Debugging Tips

### How to Detect the Problem

**Symptom:** Code works in main process but fails in workers

```python
# In main process
print(len(registry))  # → 10 generators

# In worker process
print(len(registry))  # → 0 generators (bug!)
```

**How to debug:**

1. Add logging at module import time:
   ```python
   logger.info("Module imported", pid=os.getpid())
   ```

2. Log state at key points:
   ```python
   logger.info("Registry state", count=len(registry), pid=os.getpid())
   ```

3. Check if PIDs are different (confirms multiprocessing)

### Common Mistakes

❌ **Initializing only in parent:**
```python
# cli.py
load_generators_from_config()  # ← Only loads in parent!
dramatiq_main()  # Workers won't have generators
```

❌ **Assuming fork copies state:**
```python
# Assumes fork will copy parent's registry
# Breaks on macOS/Windows with spawn!
```

✅ **Correct: Initialize in each worker:**
```python
# Via middleware (Pattern 2)
class GeneratorLoaderMiddleware(Middleware):
    def before_worker_boot(self, broker, worker):
        load_generators_from_config()  # ← Runs in each worker
```

## Conclusion

For Boards workers:

1. **Use Pattern 2 (Middleware)** for framework-managed initialization ✅
2. **Avoid module-level implicit initialization** - hard to discover
3. **Consider Pattern 4 (DI)** if testability becomes a priority
4. **Always test with spawn mode** - ensures cross-platform compatibility
5. **Remember:** Multiprocessing isolation is a feature, not a bug!

The key insight: **Multiprocessing's "confusion tax" (state not shared) is infinitely better than multithreading's "race condition tax" (data corruption).**

## References

- [Python multiprocessing documentation](https://docs.python.org/3/library/multiprocessing.html)
- [Dramatiq middleware guide](https://dramatiq.io/advanced.html)
- [Dramatiq GitHub Issue #350: Worker startup hooks](https://github.com/Bogdanp/dramatiq/issues/350)
- Internal: `boards/workers/middleware.py` (our implementation)

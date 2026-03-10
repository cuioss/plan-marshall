# Java Concurrency Patterns (21+)

Modern concurrency for Java 21+. Prefer immutability and higher-level constructs over low-level synchronization.

## Guiding Principle: Avoid Shared Mutable State

The safest concurrent code has no shared mutable state. Prefer — in order:

1. **Immutable objects** (records, `List.of()`, `final` fields)
2. **Confinement** (thread-local or scoped values)
3. **Higher-level concurrency utilities** (`java.util.concurrent`)
4. **Explicit locks** (`ReentrantLock`, `StampedLock`)
5. **`synchronized`** — last resort, avoid in virtual thread code

## Do Not Use: `volatile` and Double-Checked Locking

Double-checked locking is a legacy pattern. Modern JVMs optimize uncontended synchronization, removing the performance argument. The pattern is error-prone and unnecessary.

```java
// Bad - volatile + double-checked locking
private volatile ExpensiveResource resource;
public ExpensiveResource getResource() {
    if (resource == null) {
        synchronized (this) {
            if (resource == null) {
                resource = createExpensiveResource();
            }
        }
    }
    return resource;
}

// Good - initialization-on-demand holder (lazy, thread-safe, zero overhead)
private static class ResourceHolder {
    static final ExpensiveResource INSTANCE = createExpensiveResource();
}
public static ExpensiveResource getResource() {
    return ResourceHolder.INSTANCE;
}

// Good - enum singleton (simplest for singletons)
public enum ResourceSingleton {
    INSTANCE;
    private final ExpensiveResource resource = createExpensiveResource();
    public ExpensiveResource getResource() { return resource; }
}

// Good - AtomicReference for instance-level lazy init
private final AtomicReference<ExpensiveResource> resource = new AtomicReference<>();
public ExpensiveResource getResource() {
    return resource.updateAndGet(r -> r != null ? r : createExpensiveResource());
}
```

**When `volatile` is still acceptable**: Single flag variables for shutdown signals (`volatile boolean running`). For anything else, use `AtomicBoolean` or higher-level constructs.

## Immutability as Concurrency Strategy

Records are inherently thread-safe — their fields are `final` and set at construction:

```java
// Thread-safe by design — no synchronization needed
public record HttpResult(int statusCode, String body, Map<String, String> headers) {
    public HttpResult {
        headers = Map.copyOf(headers); // Defensive copy of mutable input
    }
}
```

**Rules for thread-safe records**:
- Wrap mutable collection parameters with `List.copyOf()`, `Set.copyOf()`, `Map.copyOf()` in compact constructors
- Ensure nested objects are themselves immutable
- Never expose mutable internal state through accessors

## Lock Selection Guide

| Need | Use | Why |
|------|-----|-----|
| Simple mutual exclusion | `ReentrantLock` | Does not pin virtual threads |
| Read-heavy, write-rare | `StampedLock` (optimistic read) | Lock-free reads in common case |
| Atomic field updates | `AtomicReference`, `AtomicInteger`, etc. | No lock contention |
| Bulk atomic operations | `LongAdder`, `LongAccumulator` | Sharded counters, better than `AtomicLong` under contention |
| Virtual thread code | `ReentrantLock` only | `synchronized` pins the carrier thread |

```java
// StampedLock - optimistic read pattern
private final StampedLock lock = new StampedLock();
private double x, y;

public double distanceFromOrigin() {
    long stamp = lock.tryOptimisticRead();
    double currentX = x, currentY = y;
    if (!lock.validate(stamp)) {
        stamp = lock.readLock();
        try { currentX = x; currentY = y; }
        finally { lock.unlockRead(stamp); }
    }
    return Math.sqrt(currentX * currentX + currentY * currentY);
}

// LongAdder - high-contention counter
private final LongAdder requestCount = new LongAdder();
public void onRequest() { requestCount.increment(); }
public long getCount() { return requestCount.sum(); }
```

## Virtual Threads

Use for I/O-bound work with high concurrency. Never pool them.

```java
// Good - virtual thread per task
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    List<Future<Response>> futures = urls.stream()
        .map(url -> executor.submit(() -> httpClient.send(url)))
        .toList();
}
```

**Critical rules**:
- Replace `synchronized` with `ReentrantLock` in any code called from virtual threads
- Do not pool virtual threads — they are cheap to create
- Do not use `ThreadLocal` — use `ScopedValue` or pass context explicitly
- Virtual threads do not benefit CPU-bound work — use platform thread pools for computation

## Scoped Values (Replaces ThreadLocal)

`ScopedValue` (final in JDK 25, preview in 21-24) is the modern replacement for `ThreadLocal` in request-scoped contexts:

```java
// Good - ScopedValue for request context
private static final ScopedValue<UserContext> CURRENT_USER = ScopedValue.newInstance();

public void handleRequest(Request request) {
    var userCtx = authenticate(request);
    ScopedValue.runWhere(CURRENT_USER, userCtx, () -> {
        processRequest(request); // All code in this scope sees CURRENT_USER
    });
}

// Reading the scoped value
public void processRequest(Request request) {
    UserContext user = CURRENT_USER.get(); // Available in this scope
}
```

**ScopedValue vs ThreadLocal**:

| Aspect | `ThreadLocal` | `ScopedValue` |
|--------|---------------|---------------|
| Mutability | Mutable — any code can `set()` | Immutable within scope |
| Cleanup | Manual `remove()` required | Automatic at scope exit |
| Virtual threads | Memory cost per thread | Efficient — shared across child scopes |
| Inheritance | Copies all parent thread-locals | Inherited by structured concurrency children |

**When ThreadLocal is still appropriate**: Mutable per-thread caches (e.g., `SimpleDateFormat`, reusable buffers) on platform threads.

## Concurrent Collections

Choose the right concurrent collection for the access pattern:

| Pattern | Use | Avoid |
|---------|-----|-------|
| Concurrent map | `ConcurrentHashMap` | `Collections.synchronizedMap()` |
| Producer-consumer | `LinkedBlockingQueue` | Manual wait/notify |
| Concurrent set | `ConcurrentHashMap.newKeySet()` | `Collections.synchronizedSet()` |
| Copy-on-write (read-heavy) | `CopyOnWriteArrayList` | `synchronizedList` with rare writes |
| Sorted concurrent | `ConcurrentSkipListMap` | Synchronized `TreeMap` |

```java
// ConcurrentHashMap - compute patterns (atomic read-modify-write)
ConcurrentHashMap<String, LongAdder> metrics = new ConcurrentHashMap<>();
metrics.computeIfAbsent("requests", k -> new LongAdder()).increment();

// Bad - check-then-act is not atomic
if (!map.containsKey(key)) {
    map.put(key, value); // Race condition
}

// Good - atomic compute
map.computeIfAbsent(key, k -> createValue());
```

## Common Pitfalls

### 1. Non-Atomic Check-Then-Act

```java
// Bad - race between check and act
if (counter.get() < MAX) {
    counter.incrementAndGet(); // May exceed MAX
}

// Good - atomic compare-and-set loop
counter.getAndUpdate(c -> c < MAX ? c + 1 : c);
```

### 2. Publishing Mutable Objects

```java
// Bad - exposing internal mutable state
public List<String> getItems() { return items; }

// Good - defensive copy or unmodifiable view
public List<String> getItems() { return List.copyOf(items); }
```

### 3. Forgetting InterruptedException Handling

```java
// Bad - swallowing interrupt
try { Thread.sleep(1000); }
catch (InterruptedException e) { /* ignored */ }

// Good - restore interrupt status
try { Thread.sleep(1000); }
catch (InterruptedException e) {
    Thread.currentThread().interrupt();
    throw new RuntimeException("Interrupted", e);
}
```

### 4. synchronized in Virtual Thread Code

```java
// Bad - pins carrier thread
synchronized (lock) { database.query(sql); }

// Good - virtual-thread-safe
private final ReentrantLock lock = new ReentrantLock();
lock.lock();
try { database.query(sql); }
finally { lock.unlock(); }
```

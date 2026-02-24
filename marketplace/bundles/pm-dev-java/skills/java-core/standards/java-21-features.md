# Java 21 Features and Patterns

Features introduced in Java 21. Use these in all Java 21+ projects.

## Pattern Matching in Switch

```java
String describe(Object obj) {
    return switch (obj) {
        case String str -> "String of length " + str.length();
        case Integer i -> "Integer: " + i;
        case null -> "null value";
        default -> "Unknown type: " + obj.getClass();
    };
}
```

## Record Patterns

Deconstruct records directly in pattern matching — avoids accessor calls:

```java
public record Point(int x, int y) {}
public record Line(Point start, Point end) {}

// Deconstruct record in switch
String describe(Object obj) {
    return switch (obj) {
        case Point(int x, int y) -> "Point at (%d, %d)".formatted(x, y);
        case Line(Point(int x1, int y1), Point(int x2, int y2)) ->
            "Line from (%d,%d) to (%d,%d)".formatted(x1, y1, x2, y2);
        default -> "Unknown shape";
    };
}

// Deconstruct in instanceof
if (obj instanceof Point(int x, int y)) {
    return Math.sqrt(x * x + y * y);
}
```

## Sequenced Collections

`SequencedCollection`, `SequencedSet`, and `SequencedMap` provide uniform access to first/last elements and reverse views:

```java
// First/last element access (replaces verbose workarounds)
SequencedCollection<String> names = new LinkedHashSet<>(List.of("Alice", "Bob", "Charlie"));
String first = names.getFirst();   // "Alice"
String last = names.getLast();     // "Charlie"

// Reverse view
SequencedCollection<String> reversed = names.reversed();

// SequencedMap — ordered map with first/last entry access
SequencedMap<String, Integer> scores = new LinkedHashMap<>();
scores.put("Alice", 95);
scores.put("Bob", 87);
Map.Entry<String, Integer> firstEntry = scores.firstEntry();
Map.Entry<String, Integer> lastEntry = scores.lastEntry();
```

**Interface hierarchy**: `SequencedCollection` extends `Collection`, `SequencedSet` extends `SequencedCollection` and `Set`, `SequencedMap` extends `Map`. Existing classes (`LinkedHashSet`, `LinkedHashMap`, `TreeSet`, `TreeMap`, `ArrayList`) implement the appropriate sequenced interface.

## Virtual Threads

Virtual threads are lightweight threads managed by the JVM. Use for I/O-bound workloads with high concurrency:

```java
// Good - virtual thread per task for I/O-bound work
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    List<Future<String>> futures = urls.stream()
        .map(url -> executor.submit(() -> fetchContent(url)))
        .toList();
    List<String> results = futures.stream()
        .map(f -> { try { return f.get(); } catch (Exception e) { throw new RuntimeException(e); } })
        .toList();
}

// Good - simple virtual thread for one-off tasks
Thread.ofVirtual().start(() -> sendNotification(event));
```

### When to Use Virtual Threads vs Platform Threads

| Workload | Use | Reason |
|----------|-----|--------|
| I/O-bound (HTTP calls, DB queries, file I/O) | Virtual threads | Scales to millions of concurrent tasks |
| CPU-bound (computation, data processing) | Platform threads / parallel streams | Virtual threads add no benefit for CPU work |
| Short-lived tasks with high concurrency | Virtual threads | Minimal overhead per thread |

### Virtual Thread Caveats

- Avoid `synchronized` blocks in virtual thread code — they pin the carrier thread. Use `ReentrantLock` instead:

```java
// Bad - pins carrier thread when virtual thread blocks inside synchronized
private final Object lock = new Object();
synchronized (lock) { blockingOperation(); }

// Good - ReentrantLock does not pin
private final ReentrantLock lock = new ReentrantLock();
lock.lock();
try { blockingOperation(); } finally { lock.unlock(); }
```

- Avoid ThreadLocal with virtual threads — memory cost multiplies with millions of threads. Prefer passing context explicitly or using `ScopedValue` (preview).
- Do not pool virtual threads — they are cheap to create. Using `Executors.newFixedThreadPool()` with virtual threads defeats the purpose.

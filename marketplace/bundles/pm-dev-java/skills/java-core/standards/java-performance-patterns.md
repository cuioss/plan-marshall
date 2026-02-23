# Java Performance Patterns

## Overview

Performance issues often hide in "obviously correct" code that works fine in development but degrades under production load. This document covers common performance anti-patterns and their solutions.

## String Handling in Hot Paths

### String Concatenation in Loops

String concatenation with `+` creates new String objects on each operation. In hot paths, this causes allocation storms and GC pressure.

```java
// ❌ Bad - creates objects on every iteration
for (String item : items) {
    log.info("Processing " + item + " from " + source + " at " + timestamp);
}

// ✅ Good - use parameterized logging
for (String item : items) {
    log.info("Processing {} from {} at {}", item, source, timestamp);
}

// ❌ Bad - string concatenation in loop
String result = "";
for (String part : parts) {
    result += part + ",";  // Creates new String each iteration
}

// ✅ Good - use StringBuilder for building strings
StringBuilder result = new StringBuilder();
for (String part : parts) {
    if (!result.isEmpty()) {
        result.append(",");
    }
    result.append(part);
}

// ✅ Better - use String.join() or Collectors.joining()
String result = String.join(",", parts);

// Or with streams
String result = parts.stream()
    .collect(Collectors.joining(","));
```

### Pre-size StringBuilder

When the approximate size is known, pre-size StringBuilder to avoid resizing:

```java
// ❌ Bad - default capacity (16), may resize multiple times
StringBuilder sb = new StringBuilder();

// ✅ Good - pre-sized based on expected content
StringBuilder sb = new StringBuilder(expectedLength);

// Example: building CSV with known columns
int estimatedSize = rows.size() * averageRowLength;
StringBuilder csv = new StringBuilder(estimatedSize);
```

## Autoboxing and Primitive Types

### Avoid Boxing in Tight Loops

Autoboxing between primitives and wrapper types creates temporary objects:

```java
// ❌ Bad - autoboxing on every iteration (creates 1M objects)
Long sum = 0L;
for (int i = 0; i < 1_000_000; i++) {
    sum += i;  // Unboxes sum, adds i, boxes result
}

// ✅ Good - use primitive (12x faster)
long sum = 0L;
for (int i = 0; i < 1_000_000; i++) {
    sum += i;
}

// ❌ Bad - Map with primitive keys causes boxing
Map<Integer, String> cache = new HashMap<>();
for (int i = 0; i < 10000; i++) {
    cache.put(i, process(i));  // Boxes i on every put
}

// ✅ Good - use primitive collections (Eclipse Collections, Trove, etc.)
IntObjectMap<String> cache = new IntObjectHashMap<>();
for (int i = 0; i < 10000; i++) {
    cache.put(i, process(i));  // No boxing
}
```

### Prefer Primitive Streams

Use primitive-specialized streams to avoid boxing:

```java
// ❌ Bad - boxes each integer
int sum = numbers.stream()
    .mapToInt(Integer::intValue)
    .sum();

// ✅ Good - use IntStream directly
int sum = IntStream.range(0, 1000).sum();

// ✅ Good - use primitive stream operations
OptionalDouble average = measurements.stream()
    .mapToDouble(Measurement::getValue)
    .average();
```

## Collection Initialization

### Specify Initial Capacity

Collections resize when they exceed load factor, causing allocation and rehashing:

```java
// ❌ Bad - default 16 buckets, resizes at 75% load
Map<String, User> userCache = new HashMap<>();

// ✅ Good - size based on expected entries
// Formula: expectedSize / loadFactor + 1
int expectedUsers = 1000;
Map<String, User> userCache = new HashMap<>(expectedUsers * 4 / 3 + 1);

// ❌ Bad - ArrayList resizes multiple times
List<String> results = new ArrayList<>();
for (int i = 0; i < 10000; i++) {
    results.add(process(i));
}

// ✅ Good - pre-sized ArrayList
List<String> results = new ArrayList<>(10000);
for (int i = 0; i < 10000; i++) {
    results.add(process(i));
}

// ✅ Better - use Stream.collect when size is known
List<String> results = IntStream.range(0, 10000)
    .mapToObj(this::process)
    .toList();
```

### Choose Appropriate Collection Types

Select collections based on access patterns:

```java
// ✅ Good - HashSet for O(1) contains checks
Set<String> allowedRoles = new HashSet<>(List.of("ADMIN", "USER", "GUEST"));
if (allowedRoles.contains(role)) { ... }

// ❌ Bad - List.contains() is O(n)
List<String> allowedRoles = List.of("ADMIN", "USER", "GUEST");
if (allowedRoles.contains(role)) { ... }  // Linear scan

// ✅ Good - LinkedHashMap for LRU cache behavior
Map<String, Object> cache = new LinkedHashMap<>(capacity, 0.75f, true) {
    @Override
    protected boolean removeEldestEntry(Map.Entry<String, Object> eldest) {
        return size() > capacity;
    }
};

// ✅ Good - EnumSet/EnumMap for enum keys
Set<DayOfWeek> workDays = EnumSet.of(MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY);
Map<Status, Handler> handlers = new EnumMap<>(Status.class);
```

## Hot Path Optimization

### Understanding CPU Cache Lines

Modern CPUs optimize for data locality and predictable access patterns. Streams and Optional can create scattered heap allocations that cause cache misses:

```java
// ❌ Bad - stream + Optional on hot path (scattered allocations, cache unfriendly)
BigDecimal totalAmount(List<Order> orders) {
    return orders.stream()
        .filter(Order::isActive)
        .map(o -> Optional.ofNullable(o.getAmount())
            .orElse(BigDecimal.ZERO))
        .reduce(BigDecimal.ZERO, BigDecimal::add);
}

// ✅ Good - simple loop (predictable access, cache friendly)
BigDecimal totalAmount(List<Order> orders) {
    BigDecimal sum = BigDecimal.ZERO;
    for (int i = 0; i < orders.size(); i++) {
        Order order = orders.get(i);
        if (!order.isActive()) {
            continue;
        }
        BigDecimal amount = order.getAmount();
        if (amount == null) {
            continue;
        }
        sum = sum.add(amount);
    }
    return sum;
}
```

**Why the simple loop wins on hot paths:**

- No lambda objects created per iteration
- No Optional wrapper allocations
- No stream infrastructure overhead
- Sequential memory access (better cache prefetching)
- Predictable branch patterns (better branch prediction)

### When to Use Streams vs Simple Loops

**Use streams when:**

- Code runs once per request (not per item in large collections)
- Processing configuration or setup code
- Readability matters more than microseconds
- Non-critical paths where clarity beats raw speed

**Use simple loops when:**

- Code runs for every item in large collections
- The method appears in profiler hot spots
- Processing high-volume message streams
- Every allocation matters (low-latency systems)

```java
// ✅ Stream OK - runs once per request, readability wins
List<UserDto> activeUsers = users.stream()
    .filter(User::isActive)
    .map(this::toDto)
    .toList();

// ✅ Simple loop - hot path, runs thousands of times per request
long countActive(List<Order> orders) {
    int count = 0;
    for (Order order : orders) {
        if (order.isActive()) {
            count++;
        }
    }
    return count;
}
```

### Avoid Optional.ofNullable in Streams

Creating Optional inside stream operations adds allocation overhead:

```java
// ❌ Bad - creates Optional for every element
BigDecimal total = items.stream()
    .map(item -> Optional.ofNullable(item.getValue())
        .orElse(BigDecimal.ZERO))
    .reduce(BigDecimal.ZERO, BigDecimal::add);

// ✅ Good - use Objects.requireNonNullElse or filter
BigDecimal total = items.stream()
    .map(Item::getValue)
    .filter(Objects::nonNull)
    .reduce(BigDecimal.ZERO, BigDecimal::add);

// ✅ Better on hot paths - simple loop
BigDecimal total = BigDecimal.ZERO;
for (Item item : items) {
    BigDecimal value = item.getValue();
    if (value != null) {
        total = total.add(value);
    }
}
```

### Index-Based Iteration for ArrayList

For ArrayList specifically, index-based iteration can be faster than enhanced for-loop:

```java
// ✅ Good for ArrayList - index access is O(1)
for (int i = 0; i < list.size(); i++) {
    process(list.get(i));
}

// Also good - enhanced for-loop uses iterator
for (Item item : list) {
    process(item);
}

// ❌ Bad for LinkedList - index access is O(n)
// Use iterator instead for LinkedList
```

## Stream Performance

### Avoid Stream Creation in Loops

Creating streams has overhead; avoid in tight loops:

```java
// ❌ Bad - creates stream on each iteration (O(n*m) stream creations)
for (Order order : orders) {
    Optional<Product> product = products.stream()
        .filter(p -> p.getId().equals(order.getProductId()))
        .findFirst();
}

// ✅ Good - build lookup map once, O(1) lookups
Map<String, Product> productMap = products.stream()
    .collect(Collectors.toMap(Product::getId, Function.identity()));

for (Order order : orders) {
    Product product = productMap.get(order.getProductId());
}

// ❌ Bad - nested stream operations
list.forEach(item -> otherList.stream()
    .filter(other -> matches(item, other))
    .forEach(this::process));

// ✅ Good - use classic loops for O(n²) operations when needed
for (Item item : list) {
    for (Other other : otherList) {
        if (matches(item, other)) {
            process(other);
        }
    }
}
```

### Consider Parallel Streams Carefully

Parallel streams have overhead; use only for CPU-intensive operations on large datasets:

```java
// ❌ Bad - parallel for small collection or I/O operations
List<Result> results = smallList.parallelStream()
    .map(this::fetchFromNetwork)  // I/O bound, not CPU bound
    .toList();

// ✅ Good - parallel for CPU-intensive with large data
List<BigDecimal> results = largeDataset.parallelStream()
    .map(this::complexCalculation)  // CPU intensive
    .toList();

// ✅ Good - stay sequential for most operations
List<String> names = users.stream()
    .filter(User::isActive)
    .map(User::getName)
    .toList();
```

## Optional Usage

### Use orElseGet for Expensive Defaults

`orElse()` evaluates eagerly; `orElseGet()` evaluates lazily:

```java
// ❌ Bad - database call happens EVERY time, even when value exists
String name = user.getName()
    .orElse(database.lookupDefaultName(userId));  // Always called!

// ✅ Good - lambda only invoked when Optional is empty
String name = user.getName()
    .orElseGet(() -> database.lookupDefaultName(userId));

// ❌ Bad - constructs object even when not needed
Config config = configOptional.orElse(new ExpensiveConfig());

// ✅ Good - only constructs when needed
Config config = configOptional.orElseGet(ExpensiveConfig::new);

// ✅ OK - cheap constant value, orElse is fine
String value = optional.orElse("");
String defaultValue = optional.orElse(DEFAULT_VALUE);
```

## Thread Safety Patterns

### Lazy Initialization

Use proper patterns to avoid contention:

```java
// ❌ Bad - synchronized on every access
public synchronized ExpensiveResource getResource() {
    if (resource == null) {
        resource = createExpensiveResource();
    }
    return resource;
}

// ✅ Good - initialization-on-demand holder idiom
public class ResourceHolder {
    private static class Holder {
        static final ExpensiveResource INSTANCE = createExpensiveResource();
    }

    public static ExpensiveResource getResource() {
        return Holder.INSTANCE;  // Lazy, thread-safe, no synchronization
    }
}

// ✅ Good - double-checked locking with volatile
public class LazyResource {
    private volatile ExpensiveResource resource;

    public ExpensiveResource getResource() {
        ExpensiveResource result = resource;
        if (result == null) {
            synchronized (this) {
                result = resource;
                if (result == null) {
                    resource = result = createExpensiveResource();
                }
            }
        }
        return result;
    }
}
```

### ThreadLocal Cleanup

Always clean up ThreadLocal in pooled thread environments:

```java
// ❌ Bad - memory leak in thread pools
private static final ThreadLocal<UserContext> context = new ThreadLocal<>();

public void processRequest(Request request) {
    context.set(createContext(request));
    try {
        handleRequest(request);
    } finally {
        // Missing cleanup! Thread returns to pool with stale data
    }
}

// ✅ Good - always remove in finally
private static final ThreadLocal<UserContext> context = new ThreadLocal<>();

public void processRequest(Request request) {
    context.set(createContext(request));
    try {
        handleRequest(request);
    } finally {
        context.remove();  // Critical for thread pools
    }
}

// ✅ Better - use try-with-resources pattern
public class ScopedContext implements AutoCloseable {
    private static final ThreadLocal<UserContext> CONTEXT = new ThreadLocal<>();

    public ScopedContext(UserContext ctx) {
        CONTEXT.set(ctx);
    }

    public static UserContext current() {
        return CONTEXT.get();
    }

    @Override
    public void close() {
        CONTEXT.remove();
    }
}

// Usage
try (var scope = new ScopedContext(context)) {
    handleRequest(request);
}  // Automatically cleaned up
```

## Exception Handling Performance

### Avoid Silent Exception Swallowing

Silent catches prevent JIT optimization and hide issues:

```java
// ❌ Bad - JVM wastes time on unused stack traces
try {
    processData(data);
} catch (Exception ignored) {
    // Silent failure blocks JIT optimizations
}

// ❌ Bad - swallows and returns default
public Optional<Config> loadConfig() {
    try {
        return Optional.of(parser.parse(configFile));
    } catch (IOException e) {
        return Optional.empty();  // No logging, no visibility
    }
}

// ✅ Good - log and handle appropriately
public Optional<Config> loadConfig() {
    try {
        return Optional.of(parser.parse(configFile));
    } catch (IOException e) {
        log.warn("Failed to load config from {}, using defaults", configFile, e);
        return Optional.empty();
    }
}

// ✅ Good - catch specific exceptions, propagate when appropriate
public Config loadConfig() throws ConfigurationException {
    try {
        return parser.parse(configFile);
    } catch (IOException e) {
        throw new ConfigurationException("Failed to load: " + configFile, e);
    }
}
```

### Avoid Exceptions for Flow Control

Exceptions are expensive; don't use them for expected conditions:

```java
// ❌ Bad - using exception for flow control
public boolean isValidNumber(String str) {
    try {
        Integer.parseInt(str);
        return true;
    } catch (NumberFormatException e) {
        return false;
    }
}

// ✅ Good - check conditions directly
public boolean isValidNumber(String str) {
    if (str == null || str.isEmpty()) {
        return false;
    }
    for (char c : str.toCharArray()) {
        if (!Character.isDigit(c)) {
            return false;
        }
    }
    return true;
}

// ✅ Good - use Optional-returning methods
public Optional<Integer> parseNumber(String str) {
    try {
        return Optional.of(Integer.parseInt(str));
    } catch (NumberFormatException e) {
        return Optional.empty();
    }
}
```

## Logging Performance

### Use Async Logging for High Throughput

Synchronous logging blocks threads on I/O:

```java
// ❌ Problem - synchronous disk I/O on every log call
// (Configure in logback.xml, not code)

// ✅ Solution - use async appenders in logback.xml
// <appender name="ASYNC" class="ch.qos.logback.classic.AsyncAppender">
//     <appender-ref ref="FILE"/>
//     <queueSize>1024</queueSize>
//     <discardingThreshold>0</discardingThreshold>
// </appender>
```

### Use Parameterized Logging

Avoid string concatenation in log statements:

```java
// ❌ Bad - string concatenation happens even if DEBUG disabled
log.debug("Processing user " + userId + " with roles " + roles);

// ✅ Good - parameterized logging, no concatenation if level disabled
log.debug("Processing user {} with roles {}", userId, roles);

// ❌ Bad - expensive toString() called even if level disabled
log.debug("User details: {}", user.toVerboseString());

// ✅ Good - use supplier for expensive operations
log.debug("User details: {}", () -> user.toVerboseString());

// Or check level explicitly for very expensive operations
if (log.isDebugEnabled()) {
    log.debug("User details: {}", user.toVerboseString());
}
```

## Database Access Patterns

### Avoid N+1 Query Problems

Fetch related data efficiently:

```java
// ❌ Bad - N+1 queries
List<User> users = userRepository.findAll();
for (User user : users) {
    List<Order> orders = orderRepository.findByUserId(user.getId());  // N queries!
    process(user, orders);
}

// ✅ Good - batch fetch with JOIN or IN clause
List<User> users = userRepository.findAllWithOrders();  // Single query with JOIN

// Or fetch in batches
Map<Long, List<Order>> ordersByUser = orderRepository
    .findByUserIdIn(userIds)
    .stream()
    .collect(Collectors.groupingBy(Order::getUserId));
```

### Use Connection Pooling Properly

Configure pools based on workload:

```java
// ✅ Good - appropriate pool sizing
// Pool size = number of CPU cores × 2 (for I/O-bound)
// Or follow database vendor recommendations

// ✅ Good - validate connections on borrow
HikariConfig config = new HikariConfig();
config.setMaximumPoolSize(10);
config.setConnectionTimeout(30000);
config.setValidationTimeout(5000);
config.setIdleTimeout(600000);
```

## Quality Checklist

- [ ] No string concatenation in hot paths (use parameterized logging, StringBuilder)
- [ ] Primitives used instead of wrappers in tight loops
- [ ] Collections initialized with appropriate capacity
- [ ] No stream creation inside loops (use lookup maps)
- [ ] Simple loops used on hot paths instead of streams (profiler-guided)
- [ ] No Optional.ofNullable inside stream operations
- [ ] orElseGet used for expensive Optional defaults
- [ ] Proper lazy initialization patterns (holder idiom or double-checked locking)
- [ ] ThreadLocal cleaned up in finally blocks
- [ ] No silent exception swallowing
- [ ] Async logging configured for high-throughput paths
- [ ] Parameterized logging used (no string concatenation)
- [ ] N+1 query patterns eliminated

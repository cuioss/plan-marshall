# Java Performance Patterns

Performance issues often hide in "obviously correct" code that works fine in development but degrades under production load.

## String Handling in Hot Paths

String concatenation with `+` creates new String objects on each operation. In loops, this causes allocation storms.

```java
// Bad - string concatenation in loop
String result = "";
for (String part : parts) {
    result += part + ",";
}

// Good - String.join() or Collectors.joining()
String result = String.join(",", parts);

// Good - StringBuilder for complex building
StringBuilder result = new StringBuilder(estimatedLength);
for (String part : parts) {
    if (!result.isEmpty()) result.append(",");
    result.append(part);
}
```

Use parameterized logging instead of concatenation:

```java
// Bad - concatenation happens even if DEBUG disabled
log.debug("Processing " + item + " from " + source);

// Good - no concatenation if level disabled
log.debug("Processing {} from {}", item, source);
```

## Autoboxing and Primitive Types

Autoboxing between primitives and wrappers creates temporary objects:

```java
// Bad - autoboxing on every iteration
Long sum = 0L;
for (int i = 0; i < 1_000_000; i++) {
    sum += i;  // Unboxes, adds, boxes
}

// Good - use primitive
long sum = 0L;
for (int i = 0; i < 1_000_000; i++) {
    sum += i;
}
```

Use primitive-specialized streams:

```java
// Good - IntStream directly, no boxing
int sum = IntStream.range(0, 1000).sum();

OptionalDouble average = measurements.stream()
    .mapToDouble(Measurement::getValue)
    .average();
```

## Collection Initialization

Collections resize when they exceed load factor. Pre-size when size is known:

```java
// Bad - default capacity, resizes multiple times
Map<String, User> userCache = new HashMap<>();

// Good - pre-sized (expectedSize / loadFactor + 1)
Map<String, User> userCache = new HashMap<>(expectedUsers * 4 / 3 + 1);

// Good - pre-sized ArrayList
List<String> results = new ArrayList<>(10000);
```

Choose appropriate collection types for access patterns:

```java
// Good - HashSet for O(1) contains
Set<String> allowedRoles = new HashSet<>(List.of("ADMIN", "USER", "GUEST"));

// Bad - List.contains() is O(n)
List<String> allowedRoles = List.of("ADMIN", "USER", "GUEST");

// Good - EnumSet/EnumMap for enum keys
Set<DayOfWeek> workDays = EnumSet.of(MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY);
Map<Status, Handler> handlers = new EnumMap<>(Status.class);
```

## Hot Path Optimization

### Streams vs Simple Loops

Streams add overhead (lambda objects, Optional wrappers, infrastructure). On hot paths, prefer simple loops:

```java
// Bad on hot path - scattered allocations, cache unfriendly
BigDecimal totalAmount(List<Order> orders) {
    return orders.stream()
        .filter(Order::isActive)
        .map(o -> Optional.ofNullable(o.getAmount())
            .orElse(BigDecimal.ZERO))
        .reduce(BigDecimal.ZERO, BigDecimal::add);
}

// Good on hot path - predictable access, cache friendly
BigDecimal totalAmount(List<Order> orders) {
    BigDecimal sum = BigDecimal.ZERO;
    for (int i = 0; i < orders.size(); i++) {
        Order order = orders.get(i);
        if (!order.isActive()) continue;
        BigDecimal amount = order.getAmount();
        if (amount != null) sum = sum.add(amount);
    }
    return sum;
}
```

**Use streams when**: code runs once per request, readability matters more than microseconds.
**Use simple loops when**: code runs per item in large collections, method appears in profiler hot spots.

### Avoid Optional.ofNullable in Streams

```java
// Bad - creates Optional for every element
items.stream()
    .map(item -> Optional.ofNullable(item.getValue()).orElse(BigDecimal.ZERO))
    .reduce(BigDecimal.ZERO, BigDecimal::add);

// Good - filter nulls directly
items.stream()
    .map(Item::getValue)
    .filter(Objects::nonNull)
    .reduce(BigDecimal.ZERO, BigDecimal::add);
```

### Avoid Stream Creation in Loops

```java
// Bad - creates stream on each iteration (O(n*m) stream creations)
for (Order order : orders) {
    Optional<Product> product = products.stream()
        .filter(p -> p.getId().equals(order.getProductId()))
        .findFirst();
}

// Good - build lookup map once, O(1) lookups
Map<String, Product> productMap = products.stream()
    .collect(Collectors.toMap(Product::getId, Function.identity()));
for (Order order : orders) {
    Product product = productMap.get(order.getProductId());
}
```

### Parallel Streams

Use only for CPU-intensive operations on large datasets. Never for I/O-bound or small collections:

```java
// Bad - parallel for small collection or I/O
smallList.parallelStream().map(this::fetchFromNetwork).toList();

// Good - parallel for CPU-intensive with large data
largeDataset.parallelStream().map(this::complexCalculation).toList();
```

## Optional Usage

`orElse()` evaluates eagerly; `orElseGet()` evaluates lazily:

```java
// Bad - database call happens EVERY time, even when value exists
String name = user.getName().orElse(database.lookupDefaultName(userId));

// Good - lambda only invoked when Optional is empty
String name = user.getName().orElseGet(() -> database.lookupDefaultName(userId));

// OK - cheap constant, orElse is fine
String value = optional.orElse("");
```

## Thread Safety Patterns

### Lazy Initialization

```java
// Bad - synchronized on every access
public synchronized ExpensiveResource getResource() {
    if (resource == null) resource = createExpensiveResource();
    return resource;
}

// Good - initialization-on-demand holder idiom
public class ResourceHolder {
    private static class Holder {
        static final ExpensiveResource INSTANCE = createExpensiveResource();
    }
    public static ExpensiveResource getResource() {
        return Holder.INSTANCE;  // Lazy, thread-safe, no synchronization
    }
}
```

### ThreadLocal Cleanup

Always clean up ThreadLocal in pooled thread environments:

```java
// Good - always remove in finally
private static final ThreadLocal<UserContext> context = new ThreadLocal<>();

public void processRequest(Request request) {
    context.set(createContext(request));
    try {
        handleRequest(request);
    } finally {
        context.remove();  // Critical for thread pools
    }
}

// Better - try-with-resources pattern
public class ScopedContext implements AutoCloseable {
    private static final ThreadLocal<UserContext> CONTEXT = new ThreadLocal<>();

    public ScopedContext(UserContext ctx) { CONTEXT.set(ctx); }
    public static UserContext current() { return CONTEXT.get(); }
    @Override public void close() { CONTEXT.remove(); }
}
```

## Exception Handling Performance

### Avoid Silent Exception Swallowing

Silent catches prevent JIT optimization and hide issues:

```java
// Bad - no visibility into failures
try {
    return Optional.of(parser.parse(configFile));
} catch (IOException e) {
    return Optional.empty();  // No logging
}

// Good - log and handle
try {
    return Optional.of(parser.parse(configFile));
} catch (IOException e) {
    log.warn("Failed to load config from {}, using defaults", configFile, e);
    return Optional.empty();
}
```

### Avoid Exceptions for Flow Control

Exceptions are expensive; don't use them for expected conditions:

```java
// Bad - exception for flow control
public boolean isValidNumber(String str) {
    try { Integer.parseInt(str); return true; }
    catch (NumberFormatException e) { return false; }
}

// Good - check directly
public boolean isValidNumber(String str) {
    if (str == null || str.isEmpty()) return false;
    for (char c : str.toCharArray()) {
        if (!Character.isDigit(c)) return false;
    }
    return true;
}
```

## Logging Performance

```java
// Bad - concatenation even if DEBUG disabled
log.debug("Processing user " + userId + " with roles " + roles);

// Good - parameterized
log.debug("Processing user {} with roles {}", userId, roles);

// Good - supplier for expensive toString()
log.debug("User details: {}", () -> user.toVerboseString());
```

Configure async appenders in logback.xml for high-throughput paths.

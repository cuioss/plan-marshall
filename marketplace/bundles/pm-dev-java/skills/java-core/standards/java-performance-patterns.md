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

Always clean up ThreadLocal in pooled thread environments. Avoid ThreadLocal with virtual threads (use explicit parameter passing instead):

```java
// Good for platform threads - always remove in finally
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

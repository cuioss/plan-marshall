# Java 25 Features and Patterns

Features finalized in Java 25 (LTS, September 2025). Use these in all Java 25+ projects.

## Scoped Values (JEP 506)

Thread-safe, immutable alternative to `ThreadLocal`. Preferred for all new code, especially with virtual threads:

```java
// Declare as static final
private static final ScopedValue<User> CURRENT_USER = ScopedValue.newInstance();

// Bind within a scope — automatically cleaned up
public void handleRequest(Request request) {
    var user = authenticate(request);
    ScopedValue.where(CURRENT_USER, user)
        .run(() -> processRequest(request));
    // CURRENT_USER.get() throws NoSuchElementException here
}

// Read deeper in the call stack
void processRequest(Request request) {
    User user = CURRENT_USER.get();
    String name = CURRENT_USER.orElse(defaultUser); // fallback must be non-null
}
```

### When to Use

| Scenario | Use |
|----------|-----|
| Request-scoped context (user, tenant, trace ID) | `ScopedValue` |
| Mutable per-thread state | `ThreadLocal` (rare) |
| Virtual thread context passing | `ScopedValue` (always) |

### Rules

- Declare as `static final` fields
- Values are immutable within scope — no `set()` method
- `orElse(null)` throws `NullPointerException` (changed in JDK 25)
- Prefer over `ThreadLocal` in all new code
- No manual cleanup needed — scope is bounded

## Flexible Constructor Bodies (JEP 513)

Statements are allowed before `super()` or `this()` calls — eliminates auxiliary static methods:

```java
// Validate before superclass construction
public class PositiveBigInteger extends BigInteger {
    public PositiveBigInteger(long value) {
        if (value <= 0) throw new IllegalArgumentException("Must be positive");
        super(Long.toString(value));
    }
}

// Compute arguments for super()
public class Square extends Rectangle {
    public Square(Color color, int area) {
        if (area < 0) throw new IllegalArgumentException("Negative area");
        double side = Math.sqrt(area);
        super(color, side, side);
    }
}
```

### Rules

- Use for parameter validation and argument computation before `super()`
- Cannot read instance fields before `super()` — compiler enforces this
- Cannot use `this` reference before `super()`
- Replaces the static-helper-method workaround pattern

## Module Import Declarations (JEP 511)

Import all exported packages of a module with a single statement:

```java
import module java.base;   // All java.base exports (collections, streams, I/O, etc.)
import module java.sql;    // All java.sql exports + transitive dependencies

// Use types without individual imports
Map<Character, List<String>> grouped = Stream.of(values)
    .collect(Collectors.groupingBy(s -> Character.toUpperCase(s.charAt(0))));
```

### Resolving Ambiguities

When two modules export the same type name, use an explicit import to resolve:

```java
import module java.base;
import module java.sql;
import java.util.Date;      // Explicit import wins over module imports

Date date = new Date();      // Uses java.util.Date
```

### Rules

- Use to reduce import clutter when using many types from a module
- Explicit single-type imports take precedence over module imports
- Transitive dependencies are included automatically
- Works with all modules, not just `java.base`

## Compact Source Files and Instance Main Methods (JEP 512)

Simplified entry points for small programs, scripts, and prototypes:

```java
// Minimal program — no class declaration needed
void main() {
    IO.println("Hello, World!");
}

// With helper methods
void main() {
    IO.println(greet("world"));
}

String greet(String name) {
    return "Hello " + name + "!";
}
```

### The IO Class

`java.lang.IO` provides simple console I/O without imports:

```java
void main() {
    String name = IO.readln("Enter name: ");
    IO.println("Hello, " + name);
}
```

### Rules

- Use for prototypes, scripts, demos, and educational code
- NOT for production application entry points — use `public static void main(String[])` there
- `java.base` is automatically imported in compact source files
- `IO` is in `java.lang` — always accessible without imports

## Key Derivation Function API (JEP 510)

Standard API for cryptographic key derivation via `javax.crypto.KDF`:

```java
import javax.crypto.KDF;
import javax.crypto.SecretKey;
import javax.crypto.spec.HKDFParameterSpec;

KDF hkdf = KDF.getInstance("HKDF-SHA256");

// Extract-then-expand (RFC 5869)
var params = HKDFParameterSpec.ofExtract()
    .addIKM(inputKeyMaterial)
    .addSalt(salt)
    .thenExpand(info, 32);  // context info + output length in bytes

SecretKey aesKey = hkdf.deriveKey("AES", params);

// Or derive raw bytes
byte[] rawBytes = hkdf.deriveData(params);
```

### Rules

- Use `deriveKey()` for `SecretKey` objects, `deriveData()` for raw bytes
- KDF instances are reusable across multiple derivations
- Supported algorithms: HKDF-SHA256, HKDF-SHA384, HKDF-SHA512
- Replaces third-party HKDF implementations

## JVM Performance Improvements

### Compact Object Headers (JEP 519)

Reduces object headers from 12 bytes to 8 bytes — 10-20% heap reduction:

```bash
java -XX:+UseCompactObjectHeaders MyApp
```

Opt-in flag. Most beneficial for applications with many small objects.

### AOT Cache (JEP 514 + JEP 515)

Simplified AOT compilation — single command replaces the previous two-step process:

```bash
# Create AOT cache (runs app, records profile, builds cache)
java -XX:AOTCacheOutput=app.aot -cp app.jar com.example.Main

# Use the cache for faster startup
java -XX:AOTCache=app.aot -cp app.jar com.example.Main
```

JEP 515 additionally caches method profiling data, eliminating JIT warmup for hot methods (up to 19% faster startup).

### Generational Shenandoah (JEP 521)

Low-pause GC with generational support for improved throughput:

```bash
java -XX:+UseShenandoahGC -XX:ShenandoahGCMode=generational MyApp
```

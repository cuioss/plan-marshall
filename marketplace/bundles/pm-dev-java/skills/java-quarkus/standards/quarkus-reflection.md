# Quarkus Reflection Registration Standards

## Purpose

Standards for registering classes for reflection in Quarkus applications and extensions, ensuring optimal native image compilation and runtime performance.

## Overview

Quarkus uses ahead-of-time (AOT) compilation to build fast native executables through closed-world analysis, which eliminates unused code paths. This optimization can break functionality relying on runtime reflection, making explicit reflection registration crucial for native image compilation success.

## Registration Approaches

### @RegisterForReflection Annotation

Application-level reflection registration using annotations directly on classes or configuration classes.

#### When to Use

* Simple application-level reflection needs
* Registering your own classes
* Third-party classes with minimal complexity
* Quick and declarative approach
* Classes that users directly interact with

#### Usage Patterns

```java
// Direct class registration
@RegisterForReflection
public class MyClass {
    // Implementation
}

// Third-party class registration
@RegisterForReflection(targets = {
    ThirdPartyClass.class,
    AnotherThirdPartyClass.class
})
public class ReflectionConfiguration {
}

// Private class registration using class names
@RegisterForReflection(classNames = {"com.example.PrivateClass"})
public class ReflectionConfig {
}
```

### ReflectiveClassBuildItem in BuildStep

Deployment-time reflection registration using Quarkus extension processors.

#### When to Use

* Building Quarkus extensions
* Programmatic registration based on conditions
* Bulk registration of classes
* Fine-grained control over reflection scope
* Dynamic discovery using Jandex

#### Usage Patterns

```java
@BuildStep
ReflectiveClassBuildItem basicReflection() {
    // Constructor reflection only
    return new ReflectiveClassBuildItem(false, false, "com.example.DemoClass");
}

@BuildStep
ReflectiveClassBuildItem fullReflection() {
    return ReflectiveClassBuildItem.builder(MyClass.class)
        .methods(true)
        .fields(true)
        .constructors(true)
        .build();
}

// Dynamic registration using Jandex
@BuildStep
void registerImplementations(CombinedIndexBuildItem combinedIndex,
                             BuildProducer<ReflectiveClassBuildItem> reflectiveClasses) {
    DotName interfaceName = DotName.createSimple(MyInterface.class.getName());
    for (ClassInfo implClass : combinedIndex.getIndex().getAllKnownImplementors(interfaceName)) {
        reflectiveClasses.produce(new ReflectiveClassBuildItem(true, true, implClass.name().toString()));
    }
}
```

### AdditionalBeanBuildItem for CDI Beans

**CRITICAL**: For CDI beans, use `AdditionalBeanBuildItem` instead of reflection registration.

#### When to Use

* Registering CDI beans that need explicit discovery
* Ensuring beans are not removed by aggressive bean removal
* Type-safe bean registration in extensions

#### Usage Pattern

```java
@BuildStep
public AdditionalBeanBuildItem additionalBeans() {
    return AdditionalBeanBuildItem.builder()
            .addBeanClasses(
                    TokenValidatorProducer.class,
                    BearerTokenProducer.class,
                    IssuerConfigResolver.class,
                    ParserConfigResolver.class
            )
            .setUnremovable()
            .build();
}
```

**IMPORTANT**: When using `AdditionalBeanBuildItem`, remove `@RegisterForReflection` annotations from the bean classes to avoid conflicts and redundancy.

## Hybrid Strategy Guidelines

### Recommended Boundaries

#### Use @RegisterForReflection For

* Application-level endpoints and controllers
* Simple DTOs and record classes
* Integration test classes
* User-facing configuration classes

#### Use ReflectiveClassBuildItem For

* Core library classes (validation, parsing, etc.)
* Complex dependency chains
* Classes requiring conditional registration
* Third-party library integration
* Dynamic class discovery and registration

### Strategy Implementation

```java
// Application level - annotation approach
@RegisterForReflection(targets = {
    JwtClaims.class,
    CustomUserPrincipal.class
})
public class JwtReflectionConfig {
}

// Extension level - processor approach
@BuildStep
void registerCryptoClasses(BuildProducer<ReflectiveClassBuildItem> reflectiveClasses) {
    // Register crypto algorithm classes based on configuration
    List<String> enabledAlgorithms = getEnabledAlgorithms();
    for (String algorithm : enabledAlgorithms) {
        String className = "com.auth0.jwt.algorithms." + algorithm + "Algorithm";
        reflectiveClasses.produce(new ReflectiveClassBuildItem(true, false, className));
    }
}
```

## Performance Optimization

**Important**: Both `@RegisterForReflection` and `ReflectiveClassBuildItem` have identical runtime performance. The performance considerations below affect native image size and build time, not runtime reflection performance.

### Selective Registration

Only register classes that are actually accessed via reflection:

```java
// Optimal - specific reflection needs
ReflectiveClassBuildItem.builder(MyClass.class)
    .constructors(true)  // Only if constructors are called via reflection
    .methods(false)      // Only if methods are called via reflection
    .fields(false)       // Only if fields are accessed via reflection
    .build();
```

### Avoid Over-Registration

Over-registration increases native image size and build time without providing runtime performance benefits:

```java
// Avoid - excessive registration (increases image size)
@RegisterForReflection(targets = {
    // Don't register entire packages or class hierarchies
    com.example.package1.Class1.class,
    com.example.package1.Class2.class,
    // ... hundreds of classes
})

// Prefer - selective registration (smaller image size)
@RegisterForReflection(targets = {
    // Only classes actually used via reflection
    com.example.SpecificClass.class
})

// Or use conditional registration for even better optimization
@BuildStep
void registerConditionally(BuildProducer<ReflectiveClassBuildItem> producer) {
    if (featureEnabled()) {
        producer.produce(new ReflectiveClassBuildItem(ConditionalClass.class));
    }
}
```

## Type Safety Best Practices

### Prefer Class-Based Registration

```java
// Preferred - type-safe registration
ReflectiveClassBuildItem.builder(RestEasyServletObjectsResolver.class)
    .methods(true)
    .build();

// Avoid - string-based registration (error-prone)
ReflectiveClassBuildItem.builder("de.cuioss.jwt.quarkus.servlet.RestEasyServletObjectsResolver")
    .methods(true)
    .build();
```

### Handle Deployment-Time Accessibility

```java
// Use string registration only when class is not accessible at deployment time
@BuildStep
public ReflectiveClassBuildItem registerRuntimeOnlyClasses() {
    return ReflectiveClassBuildItem.builder(
            // Runtime-only classes that can't be referenced directly
            "io.vertx.core.impl.VertxInternal",
            "io.netty.channel.epoll.EpollEventLoop")
            .methods(true)
            .build();
}
```

## Organizational Standards

### Logical Grouping

Group related classes together in separate build steps:

```java
@BuildStep
public ReflectiveClassBuildItem registerValidationClasses() {
    return ReflectiveClassBuildItem.builder(
            // Core validation components
            TokenValidator.class,
            IssuerConfig.class,
            ParserConfig.class)
            .methods(true)
            .fields(true)
            .constructors(true)
            .build();
}

@BuildStep
public ReflectiveClassBuildItem registerDomainClasses() {
    return ReflectiveClassBuildItem.builder(
            // Domain model classes
            AccessTokenContent.class,
            IdTokenContent.class,
            ClaimValue.class)
            .methods(true)
            .fields(true)
            .constructors(true)
            .build();
}
```

### Documentation Requirements

Document reflection registration strategy:

```java
/**
 * Reflection registration strategy:
 * - @RegisterForReflection: Application-level classes (endpoints, DTOs)
 * - ReflectiveClassBuildItem: Core infrastructure and third-party integration
 * - Avoid duplicates between annotation and processor approaches
 */
public class ReflectionProcessor {
    // Implementation
}
```

## Common Patterns

### Interface-Based Registration

```java
@BuildStep
void registerServiceImplementations(CombinedIndexBuildItem combinedIndex,
                                   BuildProducer<ReflectiveClassBuildItem> reflectiveClasses) {
    // Register all implementations of a service interface
    DotName serviceName = DotName.createSimple(MyService.class.getName());
    for (ClassInfo implClass : combinedIndex.getIndex().getAllKnownImplementors(serviceName)) {
        reflectiveClasses.produce(new ReflectiveClassBuildItem(true, true, implClass.name().toString()));
    }
}
```

### Annotation-Based Discovery

```java
@BuildStep
void registerAnnotatedClasses(CombinedIndexBuildItem combinedIndex,
                              BuildProducer<ReflectiveClassBuildItem> reflectiveClasses) {
    // Register classes with specific annotations
    DotName annotationName = DotName.createSimple(MyAnnotation.class.getName());
    for (AnnotationInstance annotation : combinedIndex.getIndex().getAnnotations(annotationName)) {
        if (annotation.target().kind() == AnnotationTarget.Kind.CLASS) {
            reflectiveClasses.produce(new ReflectiveClassBuildItem(true, true,
                annotation.target().asClass().name().toString()));
        }
    }
}
```

### Conditional Registration

```java
@BuildStep
void registerConditionalClasses(BuildProducer<ReflectiveClassBuildItem> reflectiveClasses,
                                CombinedIndexBuildItem combinedIndex) {
    // Only register if specific conditions are met
    if (combinedIndex.getIndex().getClassByName(DotName.createSimple("io.vertx.core.Vertx")) != null) {
        reflectiveClasses.produce(new ReflectiveClassBuildItem(true, false,
            "io.vertx.core.impl.VertxInternal"));
    }
}
```

## Anti-Patterns to Avoid

### Redundant Registration

```java
// AVOID - Double registration
@RegisterForReflection
public class MyClass {
    // Class already registered via annotation
}

@BuildStep
public ReflectiveClassBuildItem registerMyClass() {
    // DON'T register the same class again
    return new ReflectiveClassBuildItem(true, true, MyClass.class.getName());
}
```

### CDI Bean Reflection Conflicts

```java
// AVOID - CDI bean with reflection annotation
@ApplicationScoped
@RegisterForReflection(methods = false, fields = false)
public class TokenValidatorProducer {
    // This class should use AdditionalBeanBuildItem instead
}

@BuildStep
public AdditionalBeanBuildItem additionalBeans() {
    return AdditionalBeanBuildItem.builder()
            .addBeanClasses(TokenValidatorProducer.class) // Conflicts with annotation above
            .build();
}

// CORRECT - CDI bean without reflection annotation
@ApplicationScoped  // Remove @RegisterForReflection annotation
public class TokenValidatorProducer {
    // CDI bean registered via AdditionalBeanBuildItem only
}

@BuildStep
public AdditionalBeanBuildItem additionalBeans() {
    return AdditionalBeanBuildItem.builder()
            .addBeanClasses(TokenValidatorProducer.class) // Type-safe CDI registration
            .setUnremovable()
            .build();
}
```

### Excessive String Usage

```java
// AVOID - String-based registration when class is available
@BuildStep
public ReflectiveClassBuildItem registerAvailableClasses() {
    return ReflectiveClassBuildItem.builder(
            // Don't use strings for accessible classes
            "de.cuioss.jwt.validation.TokenValidator")
            .build();
}

// PREFER - Type-safe registration
@BuildStep
public ReflectiveClassBuildItem registerAvailableClasses() {
    return ReflectiveClassBuildItem.builder(TokenValidator.class)
            .build();
}
```

## Quarkus Auto-Registration

### Classes That Are Automatically Registered

Modern Quarkus (3.x+) automatically registers many classes for reflection through its build-time analysis.

#### CDI Beans

**Rule**: CDI beans with scope annotations are automatically analyzed and registered by Quarkus.

```java
// NO @RegisterForReflection needed - CDI scope annotation is sufficient
@ApplicationScoped
public class MyService {
    // Quarkus automatically registers this for reflection
}

@RequestScoped
public class MyRequestBean {
    // Also automatically registered
}
```

**Rationale**: Quarkus's CDI integration performs build-time bean discovery and ensures all CDI beans are accessible for dependency injection and proxy generation.

#### MicroProfile Health Checks

**Rule**: Health check implementations are automatically discovered through their annotations.

```java
// NO @RegisterForReflection needed
@Liveness
public class DatabaseHealthCheck implements HealthCheck {
    @Override
    public HealthCheckResponse call() {
        return HealthCheckResponse.up("database");
    }
}
```

#### CDI Qualifiers and Stereotypes

**Rule**: CDI qualifier annotations do not need reflection registration.

```java
// NO @RegisterForReflection needed
@Qualifier
@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.FIELD, ElementType.METHOD})
public @interface CustomQualifier {
}
```

**Rationale**: Qualifiers are metadata annotations processed entirely at build time.

### Classes That Require Explicit Registration

#### Data Transfer Objects (DTOs) and Records

**Rule**: Classes used in JSON serialization/deserialization or REST responses require explicit registration.

```java
// @RegisterForReflection IS required
@RegisterForReflection
public class UserDTO {
    private String username;
    private String email;
    // Getters/setters accessed via reflection by JSON-B/Jackson
}

// For records
@RegisterForReflection
public record ErrorResponse(int code, String message) {
}
```

#### Enums in REST/JSON Context

**Rule**: Enums used in serialization contexts need minimal reflection registration.

```java
// Minimal registration for enum constants
@RegisterForReflection(methods = false, fields = false)
public enum Status {
    ACTIVE, INACTIVE, PENDING
}
```

#### Interceptors

**Rule**: CDI interceptors need reflection for proxy generation.

```java
@Interceptor
@Priority(Interceptor.Priority.APPLICATION)
@RegisterForReflection  // Required for proxy generation
public class SecurityInterceptor {
    @AroundInvoke
    public Object intercept(InvocationContext ctx) throws Exception {
        // Interceptor logic
    }
}
```

#### JAX-RS Filters and Interceptors

**Rule**: JAX-RS filters require reflection for the JAX-RS runtime.

```java
@Provider
@RegisterForReflection  // Required for JAX-RS instantiation
public class RequestLoggingFilter implements ContainerRequestFilter {
    @Override
    public void filter(ContainerRequestContext ctx) {
        // Filter logic
    }
}
```

#### InterceptorBinding Annotations with @Nonbinding

**Rule**: InterceptorBinding annotations with `@Nonbinding` members need method reflection.

```java
@InterceptorBinding
@Retention(RetentionPolicy.RUNTIME)
@RegisterForReflection(methods = true, fields = false)  // methods=true required
public @interface Secured {
    @Nonbinding  // This member is accessed via reflection
    String[] roles() default {};
}
```

### Decision Matrix

| Class Type | Needs @RegisterForReflection? | Reason |
|---|---|---|
| CDI Bean (@ApplicationScoped, etc.) | ❌ No | Auto-registered by CDI extension |
| Health Check (@Liveness, @Readiness) | ❌ No | Auto-discovered by health extension |
| CDI Qualifier (@Qualifier) | ❌ No | Build-time metadata only |
| DTO/POJO for JSON | ✅ Yes | JSON processors use reflection |
| Enum in REST context | ✅ Yes (minimal) | Enum constants accessed via reflection |
| @Interceptor | ✅ Yes | Proxy generation requires reflection |
| JAX-RS @Provider | ✅ Yes | JAX-RS runtime instantiation |
| @InterceptorBinding with @Nonbinding | ✅ Yes (methods=true) | Runtime parameter access |

### Common Pitfalls

#### Pitfall 1: Double Registration

```java
// WRONG - Redundant registration
@ApplicationScoped
@RegisterForReflection  // ❌ Not needed - CDI handles this
public class MyService {
}
```

**Impact**: Unnecessary metadata in native image, potential configuration conflicts.

**Solution**: Remove `@RegisterForReflection` from all CDI beans.

#### Pitfall 2: Missing Registration for DTOs

```java
// WRONG - Missing registration
public class UserDTO {  // ❌ Will fail in native image if used in REST
    private String name;
}
```

**Impact**: Native image build succeeds but runtime reflection fails with `ClassNotFoundException`.

**Solution**: Add `@RegisterForReflection` to all DTOs used in REST/JSON contexts.

#### Pitfall 3: Incorrect Scope for Enums

```java
// INEFFICIENT - Too much reflection
@RegisterForReflection  // ❌ Registers methods/fields unnecessarily
public enum Status {
    ACTIVE, INACTIVE
}
```

**Solution**: Use minimal scope: `@RegisterForReflection(methods = false, fields = false)`

## Testing and Validation

### Native Image Testing

Always test reflection registration with native image compilation:

```bash
# Build native image
./mvnw clean package -Pnative

# Run native image tests
./mvnw verify -Pnative
```

### Runtime Verification

Verify reflection works at runtime:

```java
@Test
public void testReflectionRegistration() {
    // Verify classes can be instantiated via reflection
    Class<?> clazz = Class.forName("com.example.MyReflectiveClass");
    Object instance = clazz.getDeclaredConstructor().newInstance();
    assertThat(instance).isNotNull();
}
```

## References

* [Quarkus Native Application Tips](https://quarkus.io/guides/writing-native-applications-tips)
* [Quarkus Extension Development Guide](https://quarkus.io/guides/writing-extensions)
* [GraalVM Native Image Reflection Documentation](https://github.com/oracle/graal/blob/master/docs/reference-manual/native-image/Reflection.md)
* [Quarkus CDI Reference Guide](https://quarkus.io/guides/cdi-reference)

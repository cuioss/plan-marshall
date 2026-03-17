# Quarkus Reflection Registration Standards

Standards for registering classes for reflection in Quarkus native image compilation. Quarkus uses ahead-of-time (AOT) compilation with closed-world analysis, which eliminates unused code paths — making explicit reflection registration crucial.

## Registration Approaches

### @RegisterForReflection (Application Level)

For application classes, DTOs, and simple third-party class registration:

```java
// Direct class registration
@RegisterForReflection
public class MyDTO {
    private String name;
}

// Third-party class registration
@RegisterForReflection(targets = {
    ThirdPartyClass.class,
    AnotherThirdPartyClass.class
})
public class ReflectionConfiguration { }

// Private/inaccessible classes (string-based only when necessary)
@RegisterForReflection(classNames = {"com.example.PrivateClass"})
public class ReflectionConfig { }
```

### ReflectiveClassBuildItem (Extension Level)

For Quarkus extensions, conditional registration, and fine-grained control:

```java
@BuildStep
ReflectiveClassBuildItem registerWithScope() {
    return ReflectiveClassBuildItem.builder(MyClass.class)
        .constructors(true)   // Only if called via reflection
        .methods(false)       // Only if accessed via reflection
        .fields(false)        // Only if accessed via reflection
        .build();
}

// Dynamic registration using Jandex index
@BuildStep
void registerImplementations(CombinedIndexBuildItem combinedIndex,
                             BuildProducer<ReflectiveClassBuildItem> reflectiveClasses) {
    DotName interfaceName = DotName.createSimple(MyService.class.getName());
    for (ClassInfo impl : combinedIndex.getIndex().getAllKnownImplementors(interfaceName)) {
        reflectiveClasses.produce(new ReflectiveClassBuildItem(true, true, impl.name().toString()));
    }
}
```

### AdditionalBeanBuildItem (CDI Beans)

For CDI beans in extensions — use instead of reflection registration:

```java
@BuildStep
public AdditionalBeanBuildItem additionalBeans() {
    return AdditionalBeanBuildItem.builder()
            .addBeanClasses(
                    TokenValidatorProducer.class,
                    BearerTokenProducer.class)
            .setUnremovable()
            .build();
}
```

When using `AdditionalBeanBuildItem`, remove any `@RegisterForReflection` from the bean classes to avoid conflicts.

## When to Use Which Approach

| Approach | Use For |
|----------|---------|
| `@RegisterForReflection` | Application DTOs, records, simple third-party classes |
| `ReflectiveClassBuildItem` | Extensions, conditional/bulk registration, Jandex discovery |
| `AdditionalBeanBuildItem` | CDI beans in extensions |

## Decision Matrix — What Needs Registration?

| Class Type | Needs `@RegisterForReflection`? | Reason |
|---|---|---|
| CDI Bean (`@ApplicationScoped`, etc.) | No | Auto-registered by CDI extension |
| Health Check (`@Liveness`, `@Readiness`) | No | Auto-discovered by health extension |
| CDI Qualifier (`@Qualifier`) | No | Build-time metadata only |
| DTO/POJO for JSON | **Yes** | JSON processors use reflection |
| Record in REST context | **Yes** | JSON processors use reflection |
| Enum in REST context | **Yes** (minimal: `methods=false, fields=false`) | Enum constants accessed via reflection |
| `@Interceptor` | **Yes** | Proxy generation requires reflection |
| JAX-RS `@Provider` | **Yes** | JAX-RS runtime instantiation |
| `@InterceptorBinding` with `@Nonbinding` | **Yes** (`methods=true`) | Runtime parameter access |

## Type Safety

Always prefer class-based over string-based registration:

```java
// Preferred
ReflectiveClassBuildItem.builder(MyClass.class)

// Only when class is not accessible at deployment time
ReflectiveClassBuildItem.builder("io.vertx.core.impl.VertxInternal")
```

## Performance Guidelines

Both `@RegisterForReflection` and `ReflectiveClassBuildItem` have identical runtime performance. Over-registration only affects native image size and build time.

- **Narrow the scope**: Set `methods`, `fields`, `constructors` to only what is actually accessed via reflection
- **Don't register entire packages**: Register only specific classes that need it
- **Use conditional registration** in extensions when features may be disabled

## Anti-Patterns

```java
// ❌ Redundant — CDI beans don't need reflection registration
@ApplicationScoped
@RegisterForReflection
public class MyService { }

// ❌ Double registration — annotation + BuildStep for same class
@RegisterForReflection
public class MyClass { }
// plus ReflectiveClassBuildItem for MyClass in a @BuildStep

// ❌ CDI bean registered via both AdditionalBeanBuildItem and @RegisterForReflection
@ApplicationScoped
@RegisterForReflection
public class TokenProducer { }  // Remove @RegisterForReflection
```

## References

* [Quarkus Native Application Tips](https://quarkus.io/guides/writing-native-applications-tips)
* [Quarkus Extension Development Guide](https://quarkus.io/guides/writing-extensions)
* [GraalVM Native Image Reflection](https://github.com/oracle/graal/blob/master/docs/reference-manual/native-image/Reflection.md)
* [Quarkus CDI Reference Guide](https://quarkus.io/guides/cdi-reference)

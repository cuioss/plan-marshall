# Weld Testing: AutoWeld and Bean Registration

Standards for CDI unit testing with `weld-junit5` using auto-discovery and explicit bean registration.

## Required Imports

```java
import org.jboss.weld.junit5.EnableWeld;
import org.jboss.weld.junit5.auto.EnableAutoWeld;
import org.jboss.weld.junit5.auto.AddBeanClasses;
import org.jboss.weld.junit5.auto.AddPackages;
import org.jboss.weld.junit5.auto.ActivateScopes;
import org.jboss.weld.junit5.auto.ExcludeBeanClasses;
import jakarta.inject.Inject;
```

## @EnableAutoWeld (Preferred)

Use `@EnableAutoWeld` for automatic bean discovery. It scans the test class for injected types and registers them automatically.

```java
@EnableAutoWeld
class MyServiceTest {

    @Inject
    MyService underTest;

    @Inject
    DependencyBean dependency;

    @Test
    void shouldProcessInput() {
        var result = underTest.process("input");
        assertNotNull(result);
    }
}
```

**How auto-discovery works**: The extension inspects `@Inject` fields and constructor parameters, then adds the concrete types as beans to the Weld container. No `beans.xml` needed.

## @AddBeanClasses (Explicit Registration)

Use `@AddBeanClasses` when auto-discovery is insufficient — e.g., for producer methods, interceptors, or beans not directly injected.

```java
@EnableAutoWeld
@AddBeanClasses({ConfigProducer.class, LoggingInterceptor.class})
class MyServiceTest {

    @Inject
    MyService underTest;

    @Test
    void shouldUseProducedConfig() {
        assertNotNull(underTest.getConfig());
    }
}
```

## @AddPackages (Package-Level Registration)

Use `@AddPackages` to register all beans from a package. Useful when a service depends on many beans from the same package.

```java
@EnableAutoWeld
@AddPackages(MyService.class)
class MyServiceTest {

    @Inject
    MyService underTest;
}
```

This registers all CDI beans in the package containing `MyService`.

## @ActivateScopes

Activate CDI scopes required by beans under test:

```java
@EnableAutoWeld
@ActivateScopes({RequestScoped.class, SessionScoped.class})
class ScopedServiceTest {

    @Inject
    RequestScopedBean requestBean;

    @Test
    void shouldWorkInRequestScope() {
        assertNotNull(requestBean.getData());
    }
}
```

## @ExcludeBeanClasses

Exclude specific beans from auto-discovery to replace them with test doubles:

```java
@EnableAutoWeld
@ExcludeBeanClasses(ExternalClient.class)
@AddBeanClasses(MockExternalClient.class)
class ServiceWithMockTest {

    @Inject
    MyService underTest;

    @Test
    void shouldUseMockClient() {
        // MockExternalClient is injected instead of ExternalClient
    }
}
```

## @EnableWeld (Manual Configuration)

Use `@EnableWeld` with `WeldInitiator` for full manual control. Prefer `@EnableAutoWeld` unless you need explicit container configuration.

```java
@EnableWeld
class ManualConfigTest {

    @WeldSetup
    WeldInitiator weld = WeldInitiator.from(MyService.class, DependencyBean.class)
            .activate(RequestScoped.class)
            .build();

    @Inject
    MyService underTest;

    @Test
    void shouldWork() {
        assertNotNull(underTest);
    }
}
```

## Rules

1. **Prefer @EnableAutoWeld** over @EnableWeld for simpler test setup
2. **Use @AddBeanClasses** for beans not discovered automatically (producers, interceptors, decorators)
3. **Use @ExcludeBeanClasses + @AddBeanClasses** to swap implementations with test doubles
4. **Activate scopes explicitly** — Weld testing does not activate scopes by default
5. **One test class per service** — follow junit-core 1:1 mapping rule
6. **Use constructor injection** in production code — makes auto-discovery reliable
7. **Avoid beans.xml in test resources** — use annotations for explicit, readable configuration

## Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| `UnsatisfiedResolutionException` | Bean not discovered | Add via `@AddBeanClasses` |
| `ContextNotActiveException` | Missing scope activation | Add `@ActivateScopes` |
| `AmbiguousResolutionException` | Multiple implementations | Use `@ExcludeBeanClasses` to narrow |
| Test passes alone, fails in suite | Shared static state | Ensure beans are `@Dependent` or properly scoped |

## References

- [weld-testing GitHub](https://github.com/weld/weld-testing)
- [Weld JUnit 5 Auto README](https://github.com/weld/weld-testing/blob/master/junit5/README.md)

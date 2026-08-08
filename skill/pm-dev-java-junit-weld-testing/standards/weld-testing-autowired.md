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
5. **At least one test class per service** — split at ~200 lines
6. **Use constructor injection** in production code — makes auto-discovery reliable
7. **Avoid beans.xml in test resources** — use annotations for explicit, readable configuration

## Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| `UnsatisfiedResolutionException` | Bean not discovered | Add via `@AddBeanClasses` |
| `ContextNotActiveException` | Missing scope activation | Add `@ActivateScopes` |
| `AmbiguousResolutionException` | Multiple implementations | Use `@ExcludeBeanClasses` to narrow |
| Test passes alone, fails in suite | Shared static state | Ensure beans are `@Dependent` or properly scoped |

## Advanced Patterns

### Testing with Producers

When a bean depends on a produced value (e.g., configuration), register the producer explicitly:

```java
@EnableAutoWeld
@AddBeanClasses(AppConfigProducer.class)
class ConfigDependentServiceTest {

    @Inject
    ConfigDependentService underTest;

    @Test
    void shouldUseProducedConfig() {
        // AppConfigProducer provides @Produces AppConfig
        assertNotNull(underTest.getConfig());
        assertEquals("expected-value", underTest.getConfig().getSetting());
    }
}
```

### Testing with Alternatives and Qualifiers

Use `@AddBeanClasses` with `@Alternative` beans to override production implementations:

```java
@Alternative
@Priority(1)
class StubNotificationService implements NotificationService {
    private final List<String> sentMessages = new ArrayList<>();

    @Override
    public void send(String message) {
        sentMessages.add(message);
    }

    public List<String> getSentMessages() {
        return sentMessages;
    }
}

@EnableAutoWeld
@AddBeanClasses(StubNotificationService.class)
class OrderServiceTest {

    @Inject
    OrderService underTest;

    @Inject
    StubNotificationService notifications;

    @Test
    void shouldNotifyOnOrderCompletion() {
        underTest.completeOrder("order-123");
        assertEquals(1, notifications.getSentMessages().size());
    }
}
```

### Testing Event Observers

Verify CDI events by registering a test observer:

```java
@ApplicationScoped
class TestEventCollector {
    private final List<OrderEvent> events = new ArrayList<>();

    void onOrder(@Observes OrderEvent event) {
        events.add(event);
    }

    public List<OrderEvent> getEvents() {
        return events;
    }
}

@EnableAutoWeld
@ActivateScopes(RequestScoped.class)
@AddBeanClasses(TestEventCollector.class)
class EventFiringServiceTest {

    @Inject
    EventFiringService underTest;

    @Inject
    TestEventCollector collector;

    @Test
    void shouldFireOrderEvent() {
        underTest.processOrder("order-456");
        assertEquals(1, collector.getEvents().size());
        assertEquals("order-456", collector.getEvents().get(0).getOrderId());
    }
}
```

### Nested Test Classes

Use `@Nested` with Weld annotations on the outer class — inner classes inherit the container:

```java
@EnableAutoWeld
@AddBeanClasses(ConfigProducer.class)
class UserServiceTest {

    @Inject
    UserService underTest;

    @Nested
    class WhenUserExists {
        @Test
        void shouldReturnUser() {
            var user = underTest.findById("known-id");
            assertTrue(user.isPresent());
        }
    }

    @Nested
    class WhenUserDoesNotExist {
        @Test
        void shouldReturnEmpty() {
            var user = underTest.findById("unknown-id");
            assertTrue(user.isEmpty());
        }
    }
}
```

### Combining with Mockito

For dependencies that are hard to instantiate in tests, combine Weld with Mockito:

```java
@EnableAutoWeld
@ExcludeBeanClasses(ExternalApiClient.class)
class ServiceWithExternalDependencyTest {

    @Produces
    @Default
    ExternalApiClient mockClient = Mockito.mock(ExternalApiClient.class);

    @Inject
    MyService underTest;

    @Test
    void shouldHandleExternalFailure() {
        when(mockClient.fetchData()).thenThrow(new RuntimeException("timeout"));
        var result = underTest.processWithFallback();
        assertEquals("fallback-value", result);
    }
}
```

The `@Produces` annotation makes the mock available to the CDI container. `@ExcludeBeanClasses` prevents the real implementation from conflicting.

## References

- [weld-testing GitHub](https://github.com/weld/weld-testing)
- [Weld JUnit 5 Auto README](https://github.com/weld/weld-testing/blob/master/junit5/README.md)

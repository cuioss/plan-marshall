# CDI Basics — Injection, Scopes, Producers

## Constructor Injection (Mandatory)

**REQUIRED**: Always use constructor injection instead of field injection.

### Single Constructor Rule

When a CDI bean has exactly **one constructor**, CDI automatically treats it as the injection point — no `@Inject` needed:

```java
@ApplicationScoped
public class OrderService {
    private final PaymentService paymentService;
    private final InventoryService inventoryService;

    // No @Inject needed - only one constructor
    public OrderService(PaymentService paymentService,
                       InventoryService inventoryService) {
        this.paymentService = paymentService;
        this.inventoryService = inventoryService;
    }
}
```

### Multiple Constructors Rule

When a CDI bean has **multiple constructors**, you **MUST** explicitly mark the injection constructor with `@Inject`:

```java
@ApplicationScoped
public class ConfigurableService {
    private final DatabaseService databaseService;
    private final String configValue;

    public ConfigurableService() {
        this.databaseService = null;
        this.configValue = "default";
    }

    @Inject  // REQUIRED - multiple constructors exist
    public ConfigurableService(DatabaseService databaseService,
                              @ConfigProperty(name = "app.config") String configValue) {
        this.databaseService = databaseService;
        this.configValue = configValue;
    }
}
```

### Anti-Patterns

```java
// ❌ Field Injection - FORBIDDEN
@Inject
private UserService userService;

// ❌ Setter Injection - FORBIDDEN
@Inject
public void setUserService(UserService userService) {
    this.userService = userService;
}
```

---

## CDI Scopes

| Scope | Lifecycle | Use Case |
|-------|-----------|----------|
| `@ApplicationScoped` | Single instance per application | Stateless services, most business logic |
| `@RequestScoped` | New instance per HTTP request | Request-specific data |
| `@SessionScoped` | New instance per HTTP session | User session data |
| `@Dependent` | New instance per injection | Helpers, utilities |
| `@Singleton` | Single instance (eager init) | Use sparingly, prefer `@ApplicationScoped` |

### Scope Mismatch Rule

**NEVER** inject a shorter-lived bean directly into a longer-lived bean. The longer-lived bean holds a proxy, but the underlying instance may already be destroyed:

```java
// ❌ WRONG - RequestScoped injected into ApplicationScoped
@ApplicationScoped
public class ReportService {
    private final HttpServletRequest request; // Stale after request ends

    public ReportService(HttpServletRequest request) {
        this.request = request;
    }
}

// ✅ CORRECT - Use Instance<T> for shorter-lived dependencies
@ApplicationScoped
public class ReportService {
    private final Instance<HttpServletRequest> request;

    public ReportService(Instance<HttpServletRequest> request) {
        this.request = request;
    }

    public String getCurrentUser() {
        return request.get().getUserPrincipal().getName();
    }
}
```

Use `Instance<T>` (not `Provider<T>`) — it is the CDI-native type and provides `isResolvable()`, `isAmbiguous()`, and `Iterable` support that `Provider<T>` lacks. `Provider<T>` is a `jakarta.inject` type with no CDI awareness.

---

## Optional Dependencies

Use `Instance<T>` when a dependency might not be available:

```java
@ApplicationScoped
public class NotificationService {
    private final EmailService emailService;
    private final Instance<SmsService> smsService;

    public NotificationService(EmailService emailService,
                             Instance<SmsService> smsService) {
        this.emailService = emailService;
        this.smsService = smsService;
    }

    public void sendNotification(String message) {
        emailService.send(message);
        if (smsService.isResolvable()) {
            smsService.get().send(message);
        }
    }
}
```

> **Quarkus note**: ArC also supports `@io.quarkus.arc.All List<SmsService>` as a type-safe alternative to iterating `Instance<T>` when collecting all implementations.

---

## Producer Methods

Never return null from producers — use the Null Object pattern:

```java
// ❌ ILLEGAL - will throw IllegalProductException
@Produces
@RequestScoped
public SomeService createService() {
    return null;  // CDI will throw exception at runtime
}

// ✅ CORRECT - Null Object pattern
@Produces
@RequestScoped
public NotificationService createNotificationService() {
    return notificationEnabled ?
           new EmailNotificationService() :
           new NoOpNotificationService();  // Never null
}
```

---

## Error Handling

| Problem | Exception | Solution |
|---------|-----------|----------|
| Missing dependency | `UnsatisfiedResolutionException` | Ensure dependency is a CDI bean with appropriate scope |
| Multiple implementations | `AmbiguousResolutionException` | Use `@Named` or custom qualifiers |
| Circular dependencies | `DeploymentException` | Refactor architecture or use `Instance<T>` for lazy init |
| Scope mismatch | Stale/null references at runtime | Use `Instance<T>` for shorter-lived dependencies |

```java
// Disambiguate with @Named
@ApplicationScoped
public class PaymentService {
    public PaymentService(@Named("primary") PaymentGateway gateway) {
        // Uses specifically qualified implementation
    }
}
```

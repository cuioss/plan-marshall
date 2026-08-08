# CDI Advanced — Events, Observers, Interceptors

## Events and Observers

CDI events provide loose coupling between producers and consumers. The container manages observer discovery and invocation.

### Firing Events

Inject `Event<T>` and fire payloads. Observers are resolved by the container at runtime:

```java
@ApplicationScoped
public class OrderService {
    private final Event<OrderCreated> orderCreatedEvent;

    public OrderService(Event<OrderCreated> orderCreatedEvent) {
        this.orderCreatedEvent = orderCreatedEvent;
    }

    public Order createOrder(OrderRequest request) {
        var order = processOrder(request);
        orderCreatedEvent.fire(new OrderCreated(order.getId(), order.getTotal()));
        return order;
    }
}
```

### Event Payload

Use immutable records as event payloads:

```java
public record OrderCreated(String orderId, BigDecimal total) { }
```

### Observing Events

Observer methods are automatically discovered by the container. Use `@Observes` for synchronous, `@ObservesAsync` for asynchronous processing:

```java
@ApplicationScoped
public class AuditLogger {

    public void onOrderCreated(@Observes OrderCreated event) {
        log.info("Order created: %s, total: %s", event.orderId(), event.total());
    }
}

@ApplicationScoped
public class InventoryUpdater {

    public void onOrderCreated(@ObservesAsync OrderCreated event) {
        reserveStock(event.orderId());
    }
}
```

For async observers, fire with `fireAsync()`:

```java
orderCreatedEvent.fireAsync(new OrderCreated(order.getId(), order.getTotal()));
```

> **Quarkus note**: ArC supports `fireAsync`/`@ObservesAsync`, but async observers are offloaded to a thread pool — they are not reactive-aware and cannot participate in reactive pipelines or managed transactions.

### Qualified Events

Use qualifiers to distinguish event channels:

```java
@Qualifier
@Retention(RUNTIME)
@Target({FIELD, PARAMETER})
public @interface Priority {
    enum Level { HIGH, LOW }
    Level value();
}

// Fire qualified event
@ApplicationScoped
public class AlertService {
    @Priority(Level.HIGH)
    private final Event<Alert> highPriorityAlerts;

    public AlertService(@Priority(Level.HIGH) Event<Alert> highPriorityAlerts) {
        this.highPriorityAlerts = highPriorityAlerts;
    }
}

// Observe only high-priority alerts
public void onHighPriority(@Observes @Priority(Level.HIGH) Alert alert) {
    escalate(alert);
}
```

---

## Interceptors

Interceptors implement cross-cutting concerns (logging, transactions, security) without modifying business logic.

### Define the Interceptor Binding

```java
@InterceptorBinding
@Retention(RUNTIME)
@Target({TYPE, METHOD})
public @interface Logged { }
```

### Implement the Interceptor

```java
@Logged
@Interceptor
@jakarta.annotation.Priority(Interceptor.Priority.APPLICATION)
public class LoggingInterceptor {

    @AroundInvoke
    public Object logInvocation(InvocationContext context) throws Exception {
        var method = context.getMethod().getName();
        log.info("Entering %s", method);
        try {
            return context.proceed();
        } finally {
            log.info("Exiting %s", method);
        }
    }
}
```

### Apply to Beans

Apply at class level (all methods) or method level:

```java
// All methods intercepted
@Logged
@ApplicationScoped
public class OrderService {
    public Order createOrder(OrderRequest request) { ... }
}

// Single method intercepted
@ApplicationScoped
public class PaymentService {
    @Logged
    public PaymentResult processPayment(Payment payment) { ... }
}
```

### Interceptor Ordering

Use `@jakarta.annotation.Priority` to control execution order (lower value = earlier):

```java
@Security
@Interceptor
@jakarta.annotation.Priority(Interceptor.Priority.PLATFORM_BEFORE + 100)
public class SecurityInterceptor { ... }

@Logged
@Interceptor
@jakarta.annotation.Priority(Interceptor.Priority.APPLICATION)
public class LoggingInterceptor { ... }

@Transactional
@Interceptor
@jakarta.annotation.Priority(Interceptor.Priority.APPLICATION + 100)
public class TransactionInterceptor { ... }
```

Execution order: Security (100) → Logging (2000) → Transaction (2100).

> **Quarkus note**: ArC supports interceptor self-invocation — calling an intercepted method from within the same bean triggers the interceptor. In standard CDI, self-invocations bypass interceptors.

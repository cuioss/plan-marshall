# Async Testing Patterns

Never use `Thread.sleep()`, `TimeUnit.sleep()`, or busy-wait loops in tests. They cause flaky tests (too short = intermittent failure, too long = slow suite).

## Awaitility

Use Awaitility for all async waiting. It polls a condition with configurable timeout and interval.

### Dependency

```xml
<dependency>
    <groupId>org.awaitility</groupId>
    <artifactId>awaitility</artifactId>
    <scope>test</scope>
</dependency>
```

### Basic Patterns

```java
import static org.awaitility.Awaitility.await;

// Wait for condition with timeout
await().atMost(Duration.ofSeconds(5))
    .untilAsserted(() -> assertEquals(Status.COMPLETED, service.getStatus()));

// Wait for value to match
await().atMost(Duration.ofSeconds(5))
    .until(service::getStatus, equalTo(Status.COMPLETED));

// Wait for collection to be populated
await().atMost(Duration.ofSeconds(10))
    .until(() -> repository.findAll().size(), greaterThan(0));
```

### Polling Configuration

```java
// Custom poll interval (default is 100ms)
await().atMost(Duration.ofSeconds(5))
    .pollInterval(Duration.ofMillis(200))
    .until(() -> messageQueue.isEmpty());

// With poll delay (initial wait before first poll)
await().atMost(Duration.ofSeconds(10))
    .pollDelay(Duration.ofSeconds(1))
    .until(() -> cache.isWarmed());
```

### Assertion Integration

```java
// Combine with JUnit 5 assertions
await().atMost(Duration.ofSeconds(5))
    .untilAsserted(() -> {
        var result = service.getResult();
        assertAll("Async result",
            () -> assertNotNull(result, "Result should be present"),
            () -> assertTrue(result.isSuccess(), "Result should be successful")
        );
    });
```

### Anti-Patterns

```java
// WRONG — Thread.sleep is flaky and slow
Thread.sleep(2000);
assertEquals(Status.COMPLETED, service.getStatus());

// WRONG — Busy-wait loop
while (service.getStatus() != Status.COMPLETED) {
    Thread.sleep(100);
}

// CORRECT — Awaitility with readable timeout
await().atMost(Duration.ofSeconds(5))
    .untilAsserted(() -> assertEquals(Status.COMPLETED, service.getStatus()));
```

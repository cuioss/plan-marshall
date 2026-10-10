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

### When the Wait Is the Subject

The rule above is about waiting for a condition. A test that proves a wall-clock property — a session is refused once its lifetime has passed, a token is refreshed near its expiry — has no condition to poll for before the time has elapsed: the elapsed time is what it asserts. Such a wait is legitimate, and it is not shortened to make the suite faster, nor is the lifetime under test changed for that purpose.

Three things keep such tests honest and affordable:

* **Bracket the boundary with a matched control.** Assert the positive side before the time has passed and the negative side after it, and run a control whose lifetime is long enough that the same age still passes. A test that only asserts the refusal cannot tell an expired session from a broken one.
* **Wait once per event, not once per test.** Tests that observe the same event share one wait — see `pm-dev-java:junit-integration` → `standards/integration-test-duration.md`.
* **Replace a sleep that only waits for a scheduler.** Where the wait exists to let a scheduled task run, drive the scheduler deterministically — run the queued task, or use a scheduler the test controls — instead of sleeping until it probably has.

### A Wait on a Signal Still Needs a Deadline

Replacing a fixed wait with a completion signal — a loop that runs until a future is done, a latch another thread counts down — removes the time bound together with the sleep. When the signal is given only on the success path, a failure leaves the loop running, and the test hangs where it should fail: the worker threads never end, and closing their executor blocks.

A test that waits on a signal keeps three things:

* **A deadline as backstop.** The loop also ends when a deadline has passed, set above every bounded wait in the test. The deadline is not the expected duration; it is what turns a hang into a failure.
* **The signal released in `finally`.** Whatever the main thread does after starting the workers runs in `try`; `finally` completes or cancels the signal and shuts the executor down, so an assertion failure reaches the report instead of waiting behind it.
* **A bounded read of the result.** `future.get(timeout, unit)`, not `join()` or a bare `get()`.

```java
var done = new CompletableFuture<Void>();
var deadline = System.nanoTime() + Duration.ofSeconds(60).toNanos();
var executor = Executors.newFixedThreadPool(observers);
try {
    for (int i = 0; i < observers; i++) {
        executor.submit(() -> {
            while (!done.isDone() && System.nanoTime() < deadline) {
                observed.add(subject.status());
            }
        });
    }
    subject.initialise().get(30, TimeUnit.SECONDS);
    assertEquals(Status.OK, subject.status());
} finally {
    done.complete(null);
    executor.shutdownNow();
}
```

Check the failure path of such a test once by making the awaited step fail: the test must end with that failure, not with a timeout of the build.

### Hold a Transient State Open to Observe It

An assertion that some thread saw an intermediate state — `LOADING` between `UNDEFINED` and `OK` — passes only when a sample happens to fall into the window. On a fast machine the window closes before the first sample, and the test fails now and then.

Do not drop the assertion and do not widen a sleep. Hold the window open: let the test double delay its answer behind a gate the test controls, wait until the state has been observed, then release the gate.

* The gate is opt-in and off by default, so other users of the test double are unaffected.
* Waiting at the gate is bounded and fails when it is not released.
* The test still asserts the final state and that no error state was observed.

Run the class many times in a row — twenty is a reasonable number — before calling it deterministic.

### Failure-Path Tests Should Not Pay Production Back-Off

A test of the failure path — the endpoint is down, the lookup fails — runs the production retry policy unless told otherwise, and then spends its time in back-off delays that prove nothing about the failure handling.

* **Pass a fast retry configuration into the unit under test.** Few attempts, millisecond delays. When the component offers no way to pass one on that path, that is a finding about the component: a path that ignores the configured policy and uses a built-in default does so in production too.
* **Use a closed local port, not an unresolvable host name.** A name that does not resolve costs a DNS lookup whose duration depends on the machine and the network. A connection to a loopback port nothing listens on is refused at once, on every machine.

A test whose subject is the back-off itself keeps its real delays — see "When the Wait Is the Subject" above.

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

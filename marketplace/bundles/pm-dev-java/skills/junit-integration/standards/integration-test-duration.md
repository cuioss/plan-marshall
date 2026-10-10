# Integration Test Lane Duration

How to shorten an integration-test lane without weakening what it proves. For Failsafe basics see `pm-dev-java:junit-integration` SKILL.md; for the Docker-based lane structure see `external-integration-testing.md`; for the unit-suite counterpart see `pm-dev-java:junit-core` → `standards/test-fork-policy.md`.

## The Constraint

Every measure here removes time that proves nothing. None of them may remove proof:

* No test is deleted or weakened unless another, named test asserts the same behaviour.
* No real wait is shortened and no lifetime or timeout value is changed to make a suite faster.
* No gating test moves to a lane that does not gate.

When a measure cannot be applied without breaking one of these, the measure is dropped, not the constraint.

## Measure First

Read the lane's log before changing anything. The time is usually not where the tests are:

| Where to look | What it shows |
|---------------|---------------|
| Surefire executions in the integration-test lane | A unit suite running a second time through `-am` (see SKILL.md) |
| The stack-start phase | An image build that runs a full build tool inside the container |
| Failsafe per-class times | Classes whose time is a wall-clock wait, not work |
| Tests inside one class with near-identical times | Several tests each waiting for the same event |

Take the baseline from several runs and compare medians. A single run before against a single run after cannot separate the change from the runner's noise.

## Share One Wait Between Tests That Observe the Same Event

When several tests in one class each wait for the same event — a token expiring, a session timing out — and then assert a different consequence of it, the event can be awaited once and its outcome shared.

```java
class TokenRefreshIT extends BaseIntegrationTest {

    private static RefreshObservation observation;
    private static Throwable observationFailure;

    @BeforeAll
    static void observeRefreshOnce() {
        try {
            observation = RefreshObservation.awaitOne();
        } catch (Throwable failure) {
            observationFailure = failure;
        }
    }

    private static RefreshObservation observation() {
        if (observationFailure != null) {
            throw new AssertionError("the shared refresh observation failed", observationFailure);
        }
        return observation;
    }

    @Test
    void refreshRotatesTheAccessToken() {
        assertNotEquals(observation().tokenBefore(), observation().tokenAfter());
    }

    @Test
    void refreshKeepsTheSession() {
        assertEquals(observation().sessionBefore(), observation().sessionAfter());
    }
}
```

The failure is kept and rethrown by every reader on purpose: the wait is attempted once, and every test that reads it fails with the same cause instead of one test failing and the others waiting again.

State the trade in the class Javadoc, because it is real:

* The suite now observes one event per run where it observed several. Independent samples are traded for time.
* Tests that share a wait fail together. One broken observation reads as several failures with one cause.

Do not share a wait between tests that need the event under different preconditions. Those are different events.

## Run Wall-Clock-Bound Classes Concurrently

A class whose duration is a wait — it sleeps through a lifetime the system under test enforces — costs no CPU while it waits. Several such classes can run side by side. Declare the membership by JUnit tag and give the tagged classes their own Failsafe execution:

```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-failsafe-plugin</artifactId>
    <executions>
        <execution>
            <id>default</id>
            <goals>
                <goal>integration-test</goal>
                <goal>verify</goal>
            </goals>
            <configuration>
                <excludedGroups>sleep-bound</excludedGroups>
            </configuration>
        </execution>
        <execution>
            <id>sleep-bound-concurrent</id>
            <goals>
                <goal>integration-test</goal>
                <goal>verify</goal>
            </goals>
            <configuration>
                <groups>sleep-bound</groups>
                <forkCount>3</forkCount>
                <reuseForks>false</reuseForks>
            </configuration>
        </execution>
    </executions>
</plugin>
```

Two details decide whether this configuration is correct:

* **The two executions must partition the classes.** The first excludes exactly the tag the second selects. A guard test that reads the POM and the test sources, and fails when a class is selected by no execution or by two, keeps that true — see `pm-dev-java:junit-core` → `standards/test-fork-policy.md` for the guard pattern.
* **The first execution must reuse the id the parent POM's `pluginManagement` declares.** Executions merge by id. Under a different id the inherited execution stays beside the two new ones and runs every class a second time.

### The Alternative: One JVM, Classes Opted In

Where only one or two classes are wall-clock-bound, the same overlap is available without a second execution. Failsafe keeps one reused fork, JUnit's parallel execution is switched on with a sequential default, and the wall-clock-bound class opts in:

```properties
# src/test/resources/junit-platform.properties
junit.jupiter.execution.parallel.enabled=true
junit.jupiter.execution.parallel.mode.default=same_thread
junit.jupiter.execution.parallel.mode.classes.default=same_thread
junit.jupiter.execution.parallel.config.strategy=fixed
junit.jupiter.execution.parallel.config.fixed.parallelism=2
```

```java
@Execution(ExecutionMode.CONCURRENT)
class SessionExpiryIT extends BaseIntegrationTest { }
```

Every other class stays sequential because of the two `same_thread` defaults; the opted-in class runs beside whichever class is current while it waits.

What differs from the tagged execution:

* **The classes share a JVM.** Static state is shared as well — a static HTTP-client configuration, a static base URI. The opted-in class passes what it needs per request and changes no static setting.
* **`@Execution(CONCURRENT)` on the class is inherited by its methods.** They may run concurrently with each other. Annotate the methods `SAME_THREAD` when they must not.
* **A class that must run last still can.** Give it the highest `@Order`, select `ClassOrderer$OrderAnnotation`, and keep it `SAME_THREAD`. Set the orderer through Failsafe's `configurationParameters` when a `junit-platform.properties` from a dependency could otherwise decide.

The table below applies unchanged; "tagged" then reads "opted in".

### Which Class May Carry the Tag

A class may run concurrently when every one of its assertions still holds while another tagged class runs beside it. The limit is shared state, not CPU. Check each candidate against each of these:

| Shared state | Question |
|--------------|----------|
| Identity-provider users | Does it log in as a user another tagged class also uses, or can another class end that user's sessions? Give each concurrent class its own user. |
| Application instances | Which instances does it drive, and does it change anything there that another class reads? |
| Containers, networks, ports | Does it create a container name, a network or a host port that another class also creates? |
| Log files | Does it attribute a log record to its own request by counting records before and after? A record that carries no request, session or user identity can have been caused by a concurrent class and still satisfy the count. |
| Shared containers | Does it reconnect, restart or reconfigure a container other classes send requests through? |
| Timing margins | Are its margins tight enough that CPU contention from a neighbour breaks them? |

A class that fails any row stays in the sequential execution. Record the reason next to the Failsafe configuration, per class, so the next reader does not tag it again.

### When a Tagged Class Turns Out Flaky

A class that fails, or is flaky, only when it runs concurrently loses the tag. The test is not changed to make it pass concurrently: a test adjusted until it tolerates its neighbours has usually been made to assert less.

The same applies inside one class. Two legs that each log in against a freshly started identity provider can fail when started in the same instant although each passes alone; running them one after the other is then the correct state, not a missed optimisation.

## Keep Fixture Image Builds Out of the Lane

A fixture image whose Dockerfile runs a full build of its own — a build stage that resolves dependencies and packages a jar — pays that build on every lane run, outside the reactor's cache. Build the fixture's artifact in the reactor and let the Dockerfile copy it. See `pm-dev-oci:oci-standards` → `standards/image-building.md`, "Test-Fixture Images".

## Verify

* The failsafe test count across all executions equals the count before the change, and every tagged class reports the same number of tests as before.
* Classes named as sequential ran in the sequential execution.
* The lane is green on more than one consecutive run; a concurrency defect rarely shows on the first.
* The duration claim compares medians, or says plainly that it rests on a single run.

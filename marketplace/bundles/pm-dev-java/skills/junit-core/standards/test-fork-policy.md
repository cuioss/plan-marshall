# Test Fork Policy

How many JVMs a unit suite starts is a build-time decision with a large effect on duration and none on what the tests prove. This standard covers the surefire fork policy for a module's unit suite. For the Failsafe counterpart see `pm-dev-java:junit-integration` → `standards/integration-test-duration.md`.

## The Cost of One JVM Per Class

`reuseForks=false` starts a JVM for every test class. It is the safe default — no class can observe another's leftovers — and on a module with many classes it is most of the suite's duration: JVM start, class loading and framework boot are paid once per class, whatever the class tests.

`reuseForks=true` runs the classes in one JVM. It is fast and it makes every piece of JVM-wide state a shared resource.

Neither is right for a whole module. Most classes need no isolation; some cannot do without it.

## Declare the Group on the Class

Split the suite into executions and select each by JUnit tag. A class that carries no tag runs in the reused JVM; a class that needs its own JVM says so:

```java
@Tag("isolated-fork")
class DefaultTrustStoreReplacementTest { }
```

```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-surefire-plugin</artifactId>
    <executions>
        <execution>
            <id>default-test</id>
            <configuration>
                <excludedGroups>isolated-fork</excludedGroups>
                <forkCount>1</forkCount>
                <reuseForks>true</reuseForks>
            </configuration>
        </execution>
        <execution>
            <id>isolated-fork-tests</id>
            <goals>
                <goal>test</goal>
            </goals>
            <configuration>
                <groups>isolated-fork</groups>
                <forkCount>1</forkCount>
                <reuseForks>false</reuseForks>
            </configuration>
        </execution>
    </executions>
</plugin>
```

Three properties make this configuration correct:

* **The executions partition the tags.** `default-test` excludes exactly the tags the other executions select, so no class runs twice and none is left out.
* **`default-test` is surefire's own execution id.** Configuring it changes the built-in execution; any other id adds an execution beside it, and the untagged classes run twice.
* **The coverage report runs after the last execution.** Every execution appends to the same coverage data file. Where the report goal binds to the same phase as surefire, declare the surefire plugin before the coverage plugin so the report sees all of them.

A framework that boots an application per class — and keeps it running between classes of one JVM — earns a group of its own: one reused JVM for those classes only. See `pm-dev-java:java-quarkus` → `standards/quarkus-testing.md` for the Quarkus case.

## What Needs Its Own JVM

A class needs isolation when it changes something the JVM keeps after the class ends:

| JVM-wide state | Example |
|----------------|---------|
| Security defaults | Replacing the default trust store or the default `SSLContext` |
| System properties | Setting one and relying on a static initializer elsewhere to read it |
| Logger configuration | Setting a named logger's level, which stays set for whatever runs next |
| Static singletons and caches | A registry populated by one class and read by another |
| Event loops and thread pools | A class that creates its own reactive runtime instance |
| Fixed resources | A port, a file name or a registry name derived from a constant |

The list cannot be completed from reading the code. A class named in advance as "needs isolation" is a starting point; the real set is found by running the suite in the reused JVM and seeing what fails. Expect it to be several times larger than the list written beforehand.

Order dependence shows as a failure that appears in the reused JVM, disappears when the class runs alone, and may not appear on every run. Run the split suite several times in a row before trusting it.

## Tag It, Do Not Change the Test

A class that fails, or is flaky, only when it shares a JVM belongs in the isolated group. Tag it and leave the test as it is. A test rewritten until it tolerates a shared JVM has usually been made to assert less, and the tag costs one JVM start.

The inverse also holds: removing the leak at its source — a helper that hands out a distinct port per call instead of a fixed one, a fixture that restores what it changed — is a legitimate change, because it alters the fixture and not the assertion.

## Guard the Partition With a Test

The configuration is correct only while every class is in exactly one group, and nothing in the build checks that. A contract test, written in the project that declares the executions, does:

* It reads the surefire executions from the module's POM and the tags from the test sources.
* It fails when a tag is selected by no execution or by more than one.
* It fails when a class that structurally needs a group — one that carries the framework's boot annotation, or uses a fixture known to change JVM-wide state — does not carry the tag.

The guard is what turns the split from a convention into a property of the build. Without it, a new class that changes JVM-wide state lands untagged in the reused JVM and breaks an unrelated class on some later run.

When the executions are declared in a parent POM, every child module inherits them, including modules that have no class in one of the groups. Two consequences:

* An execution that selects a tag no class in the module carries runs zero tests and passes. That is correct, and it still starts a JVM.
* One guard in one module can read the test sources of every module below the parent. It then runs only when that module is built; a build limited to a sibling does not run it. Say so where the guard is declared, so nobody takes a sibling-only build for a guarded one.

## A `-Dtest` Selection Meets Two Executions

`-Dtest=SomeTest` is applied to every execution. The selected class belongs to one group, so the other execution matches nothing, and surefire fails a selection that matches nothing: `No tests matching pattern "SomeTest" were executed`. Every focused run then fails in the execution the class is not in.

Do not answer that with `<failIfNoSpecifiedTests>false</failIfNoSpecifiedTests>` in the POM. It makes the focused run pass, and it makes a mistyped `-Dtest` pass as well — zero tests run, build green. A value set in the POM also outranks `-Dsurefire.failIfNoSpecifiedTests` on the command line, so the strict behaviour cannot be asked for per run.

Collapse the split for a focused run instead. A profile activated by the `test` property removes the tag filter from the built-in execution and skips the others, so the selection runs in one execution with surefire's strict default:

```xml
<profile>
    <id>focused-test-selection</id>
    <activation>
        <property>
            <name>test</name>
        </property>
    </activation>
    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-surefire-plugin</artifactId>
                <executions>
                    <execution>
                        <id>default-test</id>
                        <configuration>
                            <excludedGroups combine.self="override" />
                        </configuration>
                    </execution>
                    <execution>
                        <id>isolated-fork-tests</id>
                        <configuration>
                            <skip>true</skip>
                        </configuration>
                    </execution>
                </executions>
            </plugin>
        </plugins>
    </build>
</profile>
```

Declare the profile where the executions are declared — under `pluginManagement` when they live there.

What this costs: a focused run puts the selected classes into one JVM, whatever their group. A class that needs isolation is not isolated in a focused run, and a selection that mixes groups shares a JVM. That affects hand-started runs only; a build without `-Dtest` keeps the split.

Have the guard fail when the POM sets `failIfNoSpecifiedTests` again, so the lenient setting cannot come back unnoticed.

## Verify

* The summed test count of all executions equals the count before the split, plus the guard's own tests.
* Per-class coverage is unchanged — compared on clean coverage data, see `coverage-analysis-pattern.md`.
* The suite is green on several consecutive runs.
* A build wrapper's summary may report only the last execution's count; read the per-execution numbers from the build log.
* Focused runs behave as intended: a build without `-Dtest` runs every execution; a class from each group passes when selected alone; a name that matches no class fails the build.

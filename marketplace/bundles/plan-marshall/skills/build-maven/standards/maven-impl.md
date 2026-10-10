# Maven Implementation Standards

Maven-specific standards for build execution, output parsing, and issue handling. For shared standards (timeouts, warnings, log files), see `extension-api/standards/build-systems-common.md`.

---

## Build Command Construction

### Base Command

All Maven builds use the Maven Wrapper from the project root:

```bash
./mvnw {goals} {options}
```

### Common Goals

| Goal | Purpose |
|------|---------|
| `clean` | Remove build artifacts and generated files |
| `install` | Build and install artifact to local repository |
| `clean install` | Fresh build with artifact installation |
| `verify` | Full build without installation |
| `test` | Compile and run tests only |
| `package` | Build without integration tests |
| `package -Dnative` | Native image build |
| `-Ppre-commit verify` | Pre-commit quality checks |
| `-Pcoverage verify` | Coverage analysis build |

### Log File Handling

Maven uses the `-l` flag for log file output capture. The build script handles log file creation automatically. When running manually, pre-create the log file before executing with `clean` (the `clean` phase deletes `target/` before Maven can create the log file).

---

## Module Targeting

### Single Module Build

Use `-pl` (project list) to build specific modules:

```bash
./mvnw clean install -pl module-name
```

For nested modules: `-pl parent/child-module`

### Building with Dependencies

| Flag | Purpose | Example |
|------|---------|---------|
| `-pl` | Build specific modules | `-pl module-a,module-b` |
| `-am` | Build required dependencies | `-pl module-a -am` |
| `-amd` | Build dependent modules | `-pl module-a -amd` |

### Resume From Module

Use `-rf` to restart a failed build:

```bash
./mvnw clean install -rf :module-name
```

### Test ladder for reactor test artifacts

Discovery emits `module-tests` = `test -pl {module} -am` and `test-compile` = `test-compile -pl {module} -am` for a module with tests. A module that consumes a reactor sibling's test artifact gets the `package`-phase ladder instead:

| Canonical | Command |
|-----------|---------|
| `module-tests` | `package -pl {module} -am` |
| `test-compile` | `package -pl {module} -am -DskipTests` |

Every other canonical of that module, and every module without such a dependency, keeps its usual command.

**Why the `test` phase is not enough.** `-am` builds the upstream reactor modules only up to the requested phase, and a classified or `test-jar` artifact is attached from `package` on. Before `package`, Maven 3.9 resolves a reactor sibling's artifact from the sibling's output directory instead. Measured on Maven 3.9.16 against a two-module reactor:

- A dependency declared `<type>test-jar</type>` resolves at `test-compile -pl b -am`: Maven falls back to the sibling's `target/test-classes`.
- A dependency declared with a custom classifier and the default `jar` type — a sibling producing its test classes through the `test-jar` goal with `<classifier>generators</classifier>` — fails at both `test-compile -pl b -am` and `test -pl b -am` (`package a does not exist`): Maven falls back to the sibling's `target/classes`, which lacks the test classes. `package -pl b -am -DskipTests` succeeds.

**Detection rule.** POM-only, no Maven run: a non-pom, non-root module whose own POM declares, under `/project/dependencies/dependency`, a dependency on another module of the same reactor with `<type>test-jar</type>` or any non-empty `<classifier>`. Reactor membership matches the dependency's `groupId:artifactId` against the coordinates of every POM discovery parsed (a child without `<groupId>` takes its parent's). `${project.groupId}` is interpolated to the declaring module's groupId and `${project.parent.groupId}` to its parent's. A classified dependency on an artifact outside the reactor keeps the usual command. `<type>test-jar</type>` is included although Maven 3.9 resolves it at `test`: a false positive costs one extra `package` phase, a false negative is a broken build, and the output-directory fallback is version-specific Maven behaviour.

**Documented limits.** A dependency inherited from a parent POM, declared only inside a profile or `dependencyManagement`, or whose coordinates use any other property is not detected; such a module keeps the usual command.

**Cost.** The module and its upstream reactor modules additionally run their `prepare-package` / `package` bindings (jar, test-jar, source and attach plugins, Quarkus augmentation in a Quarkus module). Failsafe and every `verify`-bound check are not run, so `module-tests` still means the unit tests of the module and its upstream modules.

**Rejected alternatives.**

| Alternative | Why rejected |
|-------------|--------------|
| `verify -pl {module} -am` | Runs Failsafe integration tests and every `verify`-bound gate (such as JaCoCo checks), changing what `module-tests` means and costs |
| `install -DskipTests` followed by `test -pl {module}` | Two commands where the canonical is one string, and it writes to the shared local repository |

**Module metadata.** Discovery records the qualifying dependencies in the Maven-specific module field `metadata.reactor_test_artifacts`: a sorted list of `groupId:artifactId:classifier-or-type` strings (the classifier when declared, otherwise `test-jar`). The key is omitted when the module consumes no reactor test artifact. The profile-enrich overlay in `manage-architecture` reads the same field, so the Maven-resolved profile commands never revert the ladder to the `test`-phase form.

---

## Quality Profiles

### Pre-Commit Profile

```bash
./mvnw -Ppre-commit verify
```

Includes: Compilation with warnings, unit tests, code quality checks, JavaDoc validation.

### Coverage Profile

```bash
./mvnw -Pcoverage verify
```

Includes: All pre-commit checks, JaCoCo coverage, threshold verification.

### Integration Tests Profile

```bash
./mvnw -Pintegration-tests verify
```

Runs in-process integration tests (*IT.java, *ITCase.java) using Failsafe, Weld, or embedded servers.

### E2E Tests Profile

```bash
./mvnw -Pe2e verify
```

Runs end-to-end / acceptance tests against a deployed application (browser, HTTP client).

### Extension Defaults

Profile behavior is configurable via extension defaults in `run-configuration.json`:

| Key | Format | Example |
|-----|--------|---------|
| `build.maven.profiles.skip` | Comma-separated profile names | `itest,native,jfr` |
| `build.maven.profiles.map.canonical` | `profile:canonical,...` pairs | `pre-commit:quality-gate,coverage:coverage` |

---

## CI/CD Standards

```bash
export MAVEN_OPTS="-Xmx2g -XX:MaxMetaspaceSize=512m"
export CI=true
./mvnw --batch-mode --no-transfer-progress clean install
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `-l` log file missing with `clean` | Pre-create the log file before running Maven (clean deletes target/) |
| Memory issues | Adjust `MAVEN_OPTS` (`-Xmx2g -XX:MaxMetaspaceSize=512m`) |
| Dependency resolution | Check repositories in `pom.xml` or `settings.xml` |
| Version conflicts | Use `dependency:tree` and `dependency:analyze` |
| Slow builds | Enable parallel builds (`-T 1C`) |

### Diagnostic Commands

```bash
./mvnw --version
./mvnw dependency:tree
./mvnw dependency:analyze
./mvnw help:effective-pom
./mvnw help:all-profiles
```

See `build-api-reference.md` for shared build documentation.

**Notation**: `plan-marshall:build-maven:maven`

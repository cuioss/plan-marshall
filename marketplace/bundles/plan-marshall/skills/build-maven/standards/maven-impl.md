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

# Build Log Test Data

Test fixtures derived from real build executions and research for testing parser consolidation.

## Research Sources

- [Maven Logging Options | Baeldung](https://www.baeldung.com/maven-logging)
- [Maven Surefire Plugin - Error Summary](https://maven.apache.org/surefire/maven-surefire-plugin/newerrorsummary.html)
- [Gradle Command-Line Interface](https://docs.gradle.org/current/userguide/command_line_interface.html)
- [Gradle Logging and Output](https://docs.gradle.org/current/userguide/logging.html)
- [TypeScript tsc CLI Options](https://www.typescriptlang.org/docs/handbook/compiler-options.html)
- [TAP Version 13 Specification](https://testanything.org/tap-version-13-specification.html)
- [ESLint Command Line Interface](https://eslint.org/docs/latest/use/command-line-interface)
- [npm Common Errors](https://docs.npmjs.com/common-errors/)

## Source Projects for Real Logs

| Project | Build System | Location |
|---------|--------------|----------|
| mrlonis-spring-boot-monorepo | Gradle | `/Users/oliver/git/other-test-projects/mrlonis-spring-boot-monorepo` |
| sample-monorepo | npm/TypeScript | `/Users/oliver/git/other-test-projects/sample-monorepo` |
| cui-http | Maven | `/Users/oliver/git/cui-http` |

## Test Files

### Gradle

| File | Type | Key Patterns |
|------|------|--------------|
| `gradle-success-real.log` | Success | `BUILD SUCCESSFUL`, `> Task :name`, task statuses |
| `gradle-failure-real.log` | Compile error | `error:`, source line with `^` caret, `symbol:`, `location:` |
| `gradle-test-failure-real.log` | Test failure | `FAILED`, `AssertionFailedError`, `X tests completed, X failed` |

### Maven

| File | Type | Key Patterns |
|------|------|--------------|
| `maven-success-real.log` | Success | `BUILD SUCCESS`, `[INFO]`, `Tests run: X, Failures: 0` |
| `maven-failure-real.log` | Compile + test | `[ERROR]`, `COMPILATION ERROR`, `BUILD FAILURE` |

### npm/TypeScript/Node.js

| File | Type | Key Patterns |
|------|------|--------------|
| `npm-tap-test-real.log` | TAP success | `TAP version 13`, `ok N`, `# tests N` |
| `npm-tap-test-failure-real.log` | TAP failure | `not ok N`, YAML diagnostics |
| `npm-typescript-error-real.log` | TS compile | `error TSNNNN:`, `file.ts(line,col)` |
| `npm-jest-test-failure.log` | Jest failure | `FAIL`, `expect().toBe()`, `Test Suites:` |
| `npm-eslint-errors.log` | Lint errors | `error`, `warning`, rule IDs, `✖ N problems` |
| `npm-dependency-error.log` | ERESOLVE | `npm ERR! code ERESOLVE`, peer dependency conflicts |
| `npm-404-error.log` | Registry 404 | `npm ERR! code E404`, package not found |

## Pattern Reference (Verified by Research)

### Issue Location Formats

| System | Format | Example |
|--------|--------|---------|
| Maven | `[ERROR] /path/File.java:[line,col] message` | `[ERROR] /src/Main.java:[45,20] cannot find symbol` |
| Maven (multi-line) | `[ERROR]   symbol:` / `[ERROR]   location:` | `[ERROR]   symbol:   class Logger` |
| Gradle/javac | `/path/File.java:line: error: message` + source + `^` | `/src/Main.java:45: error: cannot find symbol` |
| TypeScript | `file.ts(line,col): error TSNNNN: message` | `src/app.ts(15,3): error TS2741: Property missing` |
| ESLint | `line:col  severity  message  rule-id` | `5:10  error  'x' is unused  no-unused-vars` |

### Build Status Markers

| System | Success | Failure |
|--------|---------|---------|
| Maven | `BUILD SUCCESS` | `BUILD FAILURE` |
| Gradle | `BUILD SUCCESSFUL in Xm Xs` | `BUILD FAILED in Xs` |
| npm | Exit code 0 | `npm ERR!` prefix lines |

### Test Summary Formats

| System | Format | Example |
|--------|--------|---------|
| Maven Surefire | `Tests run: N, Failures: N, Errors: N, Skipped: N` | `Tests run: 13, Failures: 2, Errors: 0, Skipped: 0` |
| Maven (with time) | `Tests run: N, ..., Time elapsed: X.XXX sec` | `Tests run: 19, ..., Time elapsed: 0.009 s` |
| Gradle | `N tests completed, N failed` | `5 tests completed, 2 failed` |
| TAP | `# tests N` / `# pass N` / `# fail N` | `# tests 5` / `# pass 3` / `# fail 2` |
| Jest | `Tests: N passed, N failed, N total` | `Tests: 5 passed, 2 failed, 7 total` |
| Jest (suites) | `Test Suites: N passed, N failed, N total` | `Test Suites: 1 passed, 2 failed, 3 total` |

### Error Severity Indicators

| System | Error | Warning |
|--------|-------|---------|
| Maven | `[ERROR]` | `[WARNING]` |
| Gradle | `: error:` | `: warning:` |
| TypeScript | `error TSNNNN:` | (uses error for all) |
| ESLint | `error` (severity 2) | `warning` (severity 1) |
| npm | `npm ERR!` | `npm WARN` |

### Task/Phase Status (Gradle)

| Status | Meaning |
|--------|---------|
| (none) | Task executed normally |
| `UP-TO-DATE` | Outputs unchanged, skipped |
| `FROM-CACHE` | Retrieved from build cache |
| `NO-SOURCE` | No input files found |
| `SKIPPED` | Task skipped (conditional) |
| `FAILED` | Task execution failed |

## Usage

These files are used by:
- `test/pm-dev-java/build-operations/` - Maven/Gradle parse tests
- `test/pm-dev-frontend/build-operations/` - npm parse tests
- Future consolidated `build_format.py` tests

# Build Log Parsing Design

This document defines the parsing architecture for build system outputs (Maven, Gradle, npm).

## Design Decision: Separate Parsers, Unified Output

Parsing is build-system-specific. Output formatting is shared.

**Rationale:** The input formats are structurally incompatible, but consumers expect consistent output.

## Input Format Analysis

### Compilation Error Formats

**Maven:**
```
[ERROR] /path/File.java:[45,20] cannot find symbol
[ERROR]   symbol:   class Logger
[ERROR]   location: class com.example.Service
```
- Bracket prefix `[ERROR]`
- Position in `[line,col]` format
- Multi-line with indented continuation

**Gradle (javac):**
```
/path/File.java:45: error: cannot find symbol
    private Logger logger = LoggerFactory.getLogger(...);
            ^
  symbol:   class Logger
  location: class com.example.Service
```
- No prefix
- Position as `path:line:` with `error:` keyword after
- Source line + caret on following lines

**TypeScript:**
```
packages/ui/Button.tsx(15,3): error TS2741: Property missing
```
- No prefix
- Position as `path(line,col)` with parentheses
- Error code `TSNNNN`

### Required Regex Patterns

```python
MAVEN_ERROR = r'\[ERROR\]\s+(/[^:]+):\[(\d+),(\d+)\]\s+(.+)'
GRADLE_ERROR = r'^(/[^:]+):(\d+):\s*(error|warning):\s*(.+)'
TS_ERROR = r'^([^(]+)\((\d+),(\d+)\):\s*error\s+(TS\d+):\s*(.+)'
```

These patterns share no common structure. A unified regex would require:
- Format detection logic
- Multiple pattern branches
- Edge case handling for overlaps

This adds complexity without benefit.

### Test Summary Formats

| System | Format | Example |
|--------|--------|---------|
| Maven | Key-value pairs | `Tests run: 51, Failures: 2, Errors: 0, Skipped: 0` |
| Gradle | Prose | `5 tests completed, 2 failed` |
| Jest | Two-tier | `Test Suites: 2 failed, 1 passed, 3 total` |
| TAP | Hash-prefixed lines | `# tests 5` / `# pass 3` / `# fail 2` |

Semantic differences:
- Maven distinguishes "Errors" (exceptions) from "Failures" (assertions)
- Gradle collapses these into "failed"
- Jest adds suite-level aggregation
- TAP uses separate lines per metric

### Build Status Markers

| System | Success | Failure |
|--------|---------|---------|
| Maven | `BUILD SUCCESS` | `BUILD FAILURE` |
| Gradle | `BUILD SUCCESSFUL in Xs` | `BUILD FAILED in Xs` |
| npm | Exit code 0 | `npm ERR!` lines |

## npm Architecture Difference

Maven and Gradle are build systems with unified logging frameworks. All plugin output passes through `[INFO]`/`[ERROR]`/`[WARNING]`.

npm is a script runner. It executes arbitrary commands:
- `tsc` → TypeScript format
- `jest` → Jest format
- `eslint` → ESLint format
- `webpack` → Webpack format

Each tool has independent output format. There is no "npm build output" to parse.

```
Maven/Gradle:
┌─────────────────────────────────┐
│         BUILD SYSTEM            │
│  ┌─────────────────────────┐   │
│  │  UNIFIED LOG FRAMEWORK  │   │
│  │  [INFO] [ERROR] [WARN]  │   │
│  └─────────────────────────┘   │
└─────────────────────────────────┘

npm:
┌─────────────────────────────────┐
│        SCRIPT RUNNER            │
│  ┌─────┐ ┌─────┐ ┌─────┐      │
│  │ tsc │ │jest │ │eslint│      │
│  └──┬──┘ └──┬──┘ └──┬──┘      │
│     ↓       ↓       ↓          │
│  [TS fmt] [Jest] [ESLint]      │
│  DIFFERENT FORMATS              │
└─────────────────────────────────┘
```

## Parsing Architecture

### Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BUILD PIPELINE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐    ┌─────────────────┐    ┌──────────────┐    ┌─────────┐ │
│  │   Parser    │───▶│ filter_warnings │───▶│ *_result()   │───▶│ format  │ │
│  │             │    │                 │    │              │    │         │ │
│  │ parse_log() │    │ build_parse.py  │    │ build_result │    │ build_  │ │
│  │ returns:    │    │                 │    │ .py          │    │ format  │ │
│  │ list[Issue] │    │                 │    │              │    │ .py     │ │
│  │ UnitTestSummary │    │                 │    │              │    │         │ │
│  └─────────────┘    └─────────────────┘    └──────────────┘    └─────────┘ │
│                                                                              │
│  SINGLE TYPE: Issue/UnitTestSummary dataclasses throughout pipeline              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### What Remains Separate

| Component | Location | Reason |
|-----------|----------|--------|
| `parse_log()` implementation | `*_cmd_parse.py` | Incompatible regex patterns |
| Regex patterns | `*_cmd_parse.py` | Different formats and semantics |

### What Is Shared

| Component | Location | Reason |
|-----------|----------|--------|
| `BuildParser` protocol | `build_parse.py` | Unified parser contract |
| `Issue`, `UnitTestSummary` | `build_parse.py` | Single type throughout pipeline |
| `filter_warnings()` | `build_parse.py` | Logic identical, input varies |
| `format_toon()`, `format_json()` | `build_format.py` | Consumers expect consistent output |
| `create_log_file()` | `build_result.py` | Standard location `.plan/temp/build-output/` |

## Parser Contract

All parsers implement the `BuildParser` protocol defined in `build_parse.py`.

### BuildParser Protocol

```python
from typing import Protocol
from pathlib import Path

class BuildParser(Protocol):
    """Protocol for build log parsers.

    All parsers must implement parse_log() with this signature.
    Structural typing - no inheritance required.
    """

    def parse_log(self, log_file: str | Path) -> tuple[list[Issue], UnitTestSummary | None, str]:
        """Parse build log file.

        Args:
            log_file: Path to the log file (from build_result.create_log_file())

        Returns:
            Tuple of (issues, test_summary, build_status):
            - issues: list[Issue] - all errors and warnings found
            - test_summary: UnitTestSummary | None - test counts if tests ran
            - build_status: "SUCCESS" | "FAILURE"

        Raises:
            FileNotFoundError: If log file doesn't exist
        """
        ...
```

### Parser Implementation Example

```python
# maven_cmd_parse.py
from pathlib import Path
from build_parse import Issue, UnitTestSummary, SEVERITY_ERROR, SEVERITY_WARNING

def parse_log(log_file: str | Path) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse Maven build log file."""
    content = Path(log_file).read_text(encoding='utf-8', errors='replace')

    issues = _extract_issues(content)
    test_summary = _extract_test_summary(content)
    build_status = _detect_build_status(content)

    return issues, test_summary, build_status
```

## Output Contract

All parsers produce `Issue` and `UnitTestSummary` dataclasses defined in `build_parse.py`.

### Issue

```python
@dataclass
class Issue:
    file: str | None
    line: int | None
    message: str
    severity: str              # "error" | "warning"
    category: str | None       # "compilation", "test_failure", "lint"
    stack_trace: str | None    # For test failures
    accepted: bool             # For warning filtering (structured mode)
```

### UnitTestSummary

```python
@dataclass
class UnitTestSummary:
    passed: int
    failed: int
    skipped: int
    total: int
```

Both classes provide `to_dict()` methods for serialization.

### TOON Output Format

All build systems output tab-separated format:

```
status	success
exit_code	0
duration_seconds	45
log_file	.plan/temp/build-output/default/maven-2026-01-06-143000.log
command	./mvnw clean verify
```

## Anti-Patterns

Do not create:
- `UnifiedBuildParser` - formats are incompatible
- `AbstractBuildSystem` - unnecessary abstraction
- Common error extraction - patterns don't overlap
- Pluggable format detection - adds complexity without benefit

## Maven/Gradle Similarity

These systems appear similar (both compile Java, run JUnit) but output formats differ:

| Aspect | Maven | Gradle |
|--------|-------|--------|
| Log prefix | `[INFO]`, `[ERROR]` | None |
| Error location | `path:[line,col]` | `path:line: error:` |
| Source context | None | Source line + caret |
| Test summary | `Tests run: N, Failures: N, Errors: N` | `N tests completed, N failed` |

Shared parsing would require format detection + two complete pattern sets = two parsers pretending to be one.

## Implementation Files

```
extension-api/scripts/
├── build_result.py      # Log file creation, result constants
├── build_parse.py       # Warning filtering, issue partitioning
└── build_format.py      # TOON/JSON output formatting (shared)

pm-dev-java/.../scripts/
├── maven_cmd_parse.py   # Maven-specific patterns
├── maven_cmd_run.py     # Maven execution + output
├── gradle_cmd_parse.py  # Gradle-specific patterns
└── gradle_cmd_run.py    # Gradle execution + output

pm-dev-frontend/.../scripts/
└── npm_cmd_run.py       # npm tool detection + per-tool parsing
```

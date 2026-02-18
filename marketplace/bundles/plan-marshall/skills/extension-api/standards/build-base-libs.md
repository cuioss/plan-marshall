# Build Base Libraries

Complete specification for shared base libraries in the extension-api.

## Purpose

The extension-api provides shared infrastructure for domain bundle extensions (pm-dev-java, pm-dev-frontend). These libraries centralize:

- **Extension system**: Abstract base class, discovery, loading
- **Module discovery**: Finding descriptors, building paths
- **Execution support**: Log file creation, result dict construction
- **Issue parsing**: Shared data structures, warning filtering

## Library Summary

### Core Libraries

| Library | Location | Responsibility |
|---------|----------|----------------|
| `extension_base.py` | extension-api/scripts | Abstract base class, canonical commands, profile patterns |
| `extension.py` | extension-api/scripts | Extension discovery, loading, aggregation |
| `build_discover.py` | extension-api/scripts | Module discovery, path building, README detection |
| `build_result.py` | extension-api/scripts | Log file creation, result dict construction |
| `build_parse.py` | extension-api/scripts | Issue structures, warning filtering, test summaries |
| `build_format.py` | extension-api/scripts | TOON and JSON output formatting |

### External Dependencies

| Library | Location | Responsibility |
|---------|----------|----------------|
| `toon_parser.py` | toon-usage/scripts | TOON serialization |
| `run_config.py` | run-config/scripts | Timeout get/set, adaptive learning |

**Output formatting**: Use `toon_parser.serialize_toon()` for TOON output, `json.dumps(data, indent=2)` for JSON.

**Not in base libraries** (build-system-specific):
- Wrapper detection (`./mvnw`, `./gradlew`, npm/npx)
- Command flag construction (`-l`, `-P`, `--workspace`)
- Log level marker parsing (`[INFO]`, `[WARNING]`, `[ERROR]`)
- Stack trace extraction and association
- Error/warning regex patterns (compilation errors, test failures)
- Log output format handling
- Descriptor content parsing (pom.xml, package.json, build.gradle)
- Source/test directory conventions (src/main/java vs src/)
- Package discovery (Java packages vs npm exports)
- Dependency extraction

---

## Libraries

### 1. extension_base.py - Abstract Base Class

Defines the extension contract that all domain bundles must implement.

**Location**: `plan-marshall/skills/extension-api/scripts/extension_base.py`

**Responsibility**:
- Define canonical command constants and metadata
- Profile classification patterns (derived from command aliases)
- Abstract methods extensions must implement
- Default implementations for optional methods

#### Canonical Command Constants

Exports command constants (`CMD_COMPILE`, `CMD_MODULE_TESTS`, etc.), the `CANONICAL_COMMANDS` metadata dict, and `PROFILE_PATTERNS` for profile classification.

See [canonical-commands.md](canonical-commands.md) for the complete command vocabulary and definitions.

#### Abstract Base Class

```python
class ExtensionBase(ABC):
    """Abstract base class for domain bundle extensions."""

    # Required - must be implemented
    @abstractmethod
    def get_skill_domains(self) -> dict: ...

    # Module discovery - primary API
    def discover_modules(self, project_root: str) -> list: ...

    # Configuration callback
    def config_defaults(self, project_root: str) -> None: ...

    # Workflow extension methods
    def provides_triage(self) -> str | None: ...
    def provides_outline_skill(self) -> str | None: ...
```

### 2. extension.py - Extension Discovery

Single source of truth for discovering and loading extension.py files from domain bundles.

**Location**: `plan-marshall/skills/extension-api/scripts/extension.py`

**Responsibility**:
- Find extension.py files in bundles (source and cache structures)
- Load extension modules and instantiate Extension classes
- Inject `extension_base` into sys.modules for import
- Aggregate data from multiple extensions

#### API

```python
def get_plugin_cache_path() -> Path:
    """Get plugin cache path from environment or default."""

def get_marketplace_bundles_path() -> Path:
    """Get path to marketplace bundles directory (source or cache)."""

def load_extension_module(extension_path: Path, bundle_name: str):
    """Load an extension.py module and instantiate the Extension class."""

def find_extension_path(bundle_dir: Path) -> Path | None:
    """Find extension.py path in a bundle directory."""

def discover_all_extensions() -> list:
    """Discover all extension.py files in bundles (no applicability check)."""

def discover_extensions(project_root: Path) -> list:
    """Discover applicable extensions for a project."""

# Primary API
def discover_project_modules(project_root: Path) -> dict:
    """Single entry point: discover modules, merge hybrids, return merged structure."""

# Aggregation functions
def get_build_systems_from_extensions(extensions: list, project_root: Path = None) -> list:
def get_skill_domains_from_extensions(extensions: list) -> list:
def get_workflow_extensions_from_extensions(extensions: list) -> dict:
```

### 3. build_discover.py - Module Discovery

Shared utilities for discovering project modules and building paths.

**Location**: `plan-marshall/skills/extension-api/scripts/build_discover.py`

**Responsibility**:
- Find descriptor files recursively (pom.xml, package.json, build.gradle)
- Build standardized module path structures
- Detect README files in various formats

#### Constants

```python
README_PATTERNS = ["README.md", "README.adoc", "README.txt", "README"]
EXCLUDE_DIRS = {".git", "node_modules", "target", "build", "__pycache__"}
```

#### Data Classes

```python
@dataclass
class ModulePaths:
    """Path structure for a module."""
    module: str      # Relative path from project root
    descriptor: str  # Path to build descriptor
    readme: str | None  # Path to README if exists

@dataclass
class ModuleBase:
    """Base module information before extension-specific enrichment."""
    name: str
    paths: ModulePaths

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
```

#### API

```python
def discover_descriptors(
    project_root: str,
    descriptor_name: str,
    exclude_dirs: set = EXCLUDE_DIRS
) -> list[Path]:
    """Recursively find all descriptor files.

    Args:
        project_root: Absolute path to project root
        descriptor_name: File name to find (e.g., "pom.xml")
        exclude_dirs: Directory names to skip

    Returns:
        List of paths to descriptors, sorted by depth (root first)
    """

def build_module_base(project_root: str, descriptor_path: str) -> ModuleBase:
    """Build base module info from a descriptor path.

    Args:
        project_root: Absolute path to project root
        descriptor_path: Absolute path to descriptor file

    Returns:
        ModuleBase with name and paths populated
    """

def find_readme(module_path: str) -> str | None:
    """Find README file in a module directory.

    Args:
        module_path: Absolute path to module directory

    Returns:
        Relative path to README or None if not found
    """
```

### 4. build_result.py - Result Construction

Shared utilities for log file management and result dict construction.

**Location**: `plan-marshall/skills/extension-api/scripts/build_result.py`

**Responsibility**:
- Define `DirectCommandResult` TypedDict for `{build_system}_execute.py` implementations
- Create timestamped log files in standard locations
- Build consistent result dicts for success/error/timeout
- Validate result structure

#### DirectCommandResult TypedDict

Standard return structure for `{build_system}_execute.py` implementations:

```python
from build_result import DirectCommandResult

def execute_direct(...) -> DirectCommandResult:
    """Return type for direct command execution."""
    ...
```

**Required fields**:

| Field | Type | Description |
|-------|------|-------------|
| `status` | `Literal["success", "error", "timeout"]` | Execution outcome |
| `exit_code` | `int` | Process exit code (-1 for timeout/failure) |
| `duration_seconds` | `int` | Actual execution time |
| `log_file` | `str` | Path to captured output (R1 requirement) |
| `command` | `str` | Full command executed |

**Optional fields** (build-system specific):

| Field | Type | Description |
|-------|------|-------------|
| `timeout_used_seconds` | `int` | Timeout that was applied |
| `wrapper` | `str` | Maven/Gradle: wrapper path used |
| `command_type` | `str` | npm: "npm" or "npx" |
| `error` | `str` | Error message (on error/timeout only) |

#### Constants

```python
LOG_BASE_DIR = ".plan/temp/build-output"
TIMESTAMP_FORMAT = "%Y-%m-%d-%H%M%S"

# Status values
STATUS_SUCCESS = "success"
STATUS_ERROR = "error"
STATUS_TIMEOUT = "timeout"

# Error type identifiers
ERROR_BUILD_FAILED = "build_failed"
ERROR_TIMEOUT = "timeout"
ERROR_EXECUTION_FAILED = "execution_failed"
ERROR_WRAPPER_NOT_FOUND = "wrapper_not_found"
ERROR_LOG_FILE_FAILED = "log_file_failed"
```

#### API

```python
def create_log_file(
    build_system: str,
    scope: str = "default",
    project_dir: str = "."
) -> str | None:
    """Create a timestamped log file for build output.

    Args:
        build_system: Build system name (maven, gradle, npm)
        scope: Module scope or "default" for root
        project_dir: Project root directory

    Returns:
        Absolute path to log file, or None if creation failed

    Creates: .plan/temp/build-output/{scope}/{build_system}-{timestamp}.log
    """

def success_result(
    duration_seconds: int,
    log_file: str,
    command: str,
    **extra
) -> dict:
    """Build success result dict.

    Returns: {status, exit_code, duration_seconds, log_file, command, **extra}
    """

def error_result(
    error: str,
    exit_code: int,
    duration_seconds: int,
    log_file: str,
    command: str,
    **extra
) -> dict:
    """Build error result dict.

    Returns: {status, error, exit_code, duration_seconds, log_file, command, **extra}
    """

def timeout_result(
    timeout_used_seconds: int,
    duration_seconds: int,
    log_file: str,
    command: str,
    **extra
) -> dict:
    """Build timeout result dict.

    Returns: {status, error, exit_code, timeout_used_seconds, duration_seconds, log_file, command, **extra}
    """

def validate_result(result: dict) -> tuple[bool, list]:
    """Validate result dict has required fields.

    Returns: (is_valid, list_of_missing_fields)
    """
```

### 5. build_parse.py - Issue Parsing

Shared data structures for build issues and warning filtering.

**Location**: `plan-marshall/skills/extension-api/scripts/build_parse.py`

**Responsibility**:
- Define Issue and UnitTestSummary data structures
- Filter warnings based on acceptable patterns
- Support actionable/structured/errors modes

#### Constants

```python
SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
```

#### Data Classes

```python
@dataclass
class Issue:
    """Represents a build issue (error or warning)."""
    file: str | None
    line: int | None
    message: str
    severity: str  # SEVERITY_ERROR or SEVERITY_WARNING
    category: str | None = None  # e.g., "compilation", "test_failure"
    stack_trace: str | None = None
    accepted: bool = False  # For structured mode

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""

@dataclass
class UnitTestSummary:
    """Summary of test execution results."""
    passed: int
    failed: int
    skipped: int
    total: int

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
```

#### API

```python
def load_acceptable_warnings(project_dir: str, build_system: str) -> list[str]:
    """Load acceptable warning patterns from run-configuration.json.

    Args:
        project_dir: Project root directory
        build_system: Build system key (maven, gradle, npm)

    Returns:
        List of acceptable warning patterns
    """

def is_warning_accepted(warning: Issue, patterns: list[str]) -> bool:
    """Check if a warning matches an acceptable pattern.

    Supports:
    - Substring matching
    - Regex matching (patterns starting with ^)
    """

def filter_warnings(
    warnings: list[Issue],
    patterns: list[str],
    mode: str = "actionable"
) -> list[Issue]:
    """Filter warnings based on mode.

    Modes:
    - actionable: Remove accepted warnings
    - structured: Keep all, set accepted=True on matching
    - errors: Return empty list (no warnings)
    """

def partition_issues(issues: list[Issue]) -> tuple[list[Issue], list[Issue]]:
    """Partition issues into (errors, warnings) by severity."""
```

### 6. build_format.py - Output Formatting

Shared utilities for formatting build results in TOON and JSON formats.

**Location**: `plan-marshall/skills/extension-api/scripts/build_format.py`

**Responsibility**:
- Format result dicts as TOON output (tab-separated key-value pairs)
- Format result dicts as JSON output
- Handle Issue and UnitTestSummary dataclass serialization

#### API

```python
def format_toon(result: dict) -> str:
    """Format result dict as TOON output.

    Produces tab-separated key-value pairs for scalar fields,
    followed by structured sections for errors, warnings, and tests.

    Args:
        result: Result dict from build_result.*_result() functions.
            May contain Issue objects (with to_dict()) or plain dicts.

    Returns:
        TOON-formatted string with tab separators.

    Example output (success):
        status	success
        exit_code	0
        duration_seconds	45
        log_file	.plan/temp/build-output/default/maven-2026-01-06-143000.log
        command	./mvnw clean verify

    Example output (error with issues):
        status	error
        exit_code	1
        ...
        error	build_failed

        errors[2]{file,line,message,category}:
        src/Main.java	15	cannot find symbol	compilation
        src/Test.java	42	test failed	test_failure

        warnings[1]{file,line,message}:
        pom.xml	-	deprecated version	deprecation

        tests:
          passed: 10
          failed: 2
          skipped: 1
    """

def format_json(result: dict, indent: int = 2) -> str:
    """Format result dict as JSON output.

    Converts any Issue or UnitTestSummary objects to dicts before serialization.

    Args:
        result: Result dict from build_result.*_result() functions.
        indent: JSON indentation level (default 2).

    Returns:
        JSON-formatted string.
    """
```

---

## Integration Pattern

### Layer Separation

```
┌─────────────────────────────────────────────────────────────────┐
│                      Domain Extensions                           │
│  pm-dev-java/extension.py         pm-dev-frontend/extension.py  │
│  - Descriptor parsing (pom.xml)   - Descriptor parsing (pkg)    │
│  - Source dir conventions         - Source dir conventions      │
│  - Metadata extraction            - Metadata extraction         │
│  pm-dev-java/maven_execute.py     pm-dev-frontend/npm_execute.py    │
│  - Wrapper detection (./mvnw)     - npm/npx detection           │
│  - Maven flags (-l, -P, -pl)      - Workspace flags (--workspace)│
│  - Module targeting               - Package targeting            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 extension-api Base Libraries                     │
│                                                                  │
│  extension_base.py  - Abstract base class, canonical commands   │
│  extension.py       - Extension discovery, loading, aggregation │
│  build_discover.py  - Module discovery, path building           │
│  build_result.py    - Log file creation, result construction    │
│  build_parse.py     - Issue structures, warning filtering       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   External Dependencies                          │
│  toon_parser.py (toon-usage)    - TOON serialization            │
│  run_config.py (run-config)     - Timeout get/set               │
└─────────────────────────────────────────────────────────────────┘
```

The `module` parameter (Maven) or `package` parameter (npm) scopes builds to specific project modules. Log files are organized by module scope.

## Import Resolution

Base libraries live in `extension-api/scripts/` and are imported by domain extensions.

### From Domain Extensions

```python
# pm-dev-java/skills/plan-marshall-plugin/scripts/extension.py

import sys
from pathlib import Path

# Add extension-api scripts to path
SCRIPT_DIR = Path(__file__).parent
BUNDLES_DIR = SCRIPT_DIR.parent.parent.parent.parent
EXTENSION_API_DIR = BUNDLES_DIR / "plan-marshall" / "skills" / "extension-api" / "scripts"
sys.path.insert(0, str(EXTENSION_API_DIR))

# Now import base libraries
from extension_base import ExtensionBase, CMD_MODULE_TESTS, CMD_VERIFY
```

## Testing Requirements

Tests for extension-api libraries are in `test/plan-marshall/extension-api/`:

```
test/plan-marshall/extension-api/
├── test_extension_base.py
├── test_extension.py
├── test_build_discover.py
├── test_build_result.py
└── test_build_parse.py
```

Key test scenarios:
1. **extension_base**: Canonical command constants, profile pattern vocabulary
2. **extension**: Bundle discovery, extension loading, aggregation functions
3. **build_discover**: Descriptor discovery, deep nesting, README detection, module base construction
4. **build_result**: Log file path generation, directory creation, result dict construction
5. **build_parse**: Issue dataclass, warning filtering modes, acceptable pattern matching

Note: `toon_parser.py` has its own tests in `test/plan-marshall/toon-usage/`.

## Compliance

Implementations must:

- [ ] Inherit from `ExtensionBase` for domain extensions
- [ ] Use canonical command constants from `extension_base`
- [ ] Use `extension.py` for discovery and aggregation
- [ ] Use `project-structure` skill for persistence and lookup operations

## Related Specifications

- [architecture-overview.md](architecture-overview.md) - System flow and data dependencies
- [build-execution.md](build-execution.md) - Execution API contract
- [build-return.md](build-return.md) - Return value structure
- [build-project-structure.md](build-project-structure.md) - Module discovery
- [extension-contract.md](extension-contract.md) - Extension API

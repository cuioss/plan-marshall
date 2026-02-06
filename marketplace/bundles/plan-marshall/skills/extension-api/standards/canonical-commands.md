# Canonical Command Vocabulary

Defines the standard command names that extensions return in `discover_modules()` output.

## Purpose

Canonical commands provide a **build-system-agnostic vocabulary** for common development operations. Extensions map these canonical names to build-system-specific invocations.

## Canonical Commands

| Canonical Name | Phase | Required | Description |
|----------------|-------|----------|-------------|
| `clean` | clean | No | Remove build artifacts and generated files |
| `compile` | build | No | Compile production sources only |
| `test-compile` | build | No | Compile production and test sources |
| `module-tests` | test | **Yes** | Unit tests for the module |
| `integration-tests` | test | No | Integration tests (containers, external services) |
| `coverage` | test | No | Test execution with coverage measurement |
| `benchmark` | test | No | Benchmark/performance tests |
| `quality-gate` | quality | **Yes** | Static analysis, linting, formatting checks |
| `verify` | verify | **Yes** | Full verification (compile + test + quality) |
| `install` | deploy | No | Install artifact to local repository |
| `clean-install` | deploy | No | Clean and install artifact to local repository |
| `package` | deploy | No | Create deployable artifact |

**Note**: `clean` is a separate command. Other commands do NOT include clean goal. Use `clean-install` for combined clean + install workflows.

## Command Resolution Logic

Extensions resolve which commands to include based on module characteristics. This section defines the resolution rules.

### Resolution Categories

Commands fall into three categories based on when they are included:

| Category | Commands | Condition |
|----------|----------|-----------|
| **Always (all)** | `clean`, `quality-gate` | All modules including pom |
| **Always (non-pom)** | `verify`, `install`, `clean-install`, `package` | Non-pom modules only |
| **Source-conditional** | `compile` | Only if `paths.sources` is non-empty |
| **Test-conditional** | `test-compile`, `module-tests` | Only if `paths.tests` is non-empty |
| **Profile-based** | `integration-tests`, `coverage`, `performance` | Only if corresponding profile detected |

### Resolution Rules

#### 1. Always-Available Commands

All modules (including pom) receive:
- `clean` - Remove build artifacts
- `quality-gate` - Static analysis and linting

Non-pom modules also receive:
- `verify` - Full verification (compile + test + quality)
- `install` - Install to local repository
- `clean-install` - Clean and install combined
- `package` - Create deployable artifact

**Profile enhancement**: If a profile maps to a canonical command, enhance that command:
```
quality-gate + pre-commit profile → "verify -Ppre-commit"
```

**Note**: Profile commands do NOT include clean goal. Run `clean` separately if needed.

#### 2. Source-Conditional Commands

Only include if `stats.source_files > 0` or `paths.sources` is non-empty:
- `compile` - Compile production sources

#### 3. Test-Conditional Commands

Only include if `stats.test_files > 0` or `paths.tests` is non-empty:
- `test-compile` - Compile test sources
- `module-tests` - Run unit tests

**Rationale**: Modules without test sources should not have `module-tests` (avoids misleading "no tests to run" results).

#### 4. Profile-Based Commands

Only include if corresponding profile/configuration is detected:
- `integration-tests` - Requires integration test profile
- `coverage` - Requires coverage tooling (JaCoCo, Istanbul, etc.)
- `benchmark` - Requires benchmark configuration (JMH, etc.)

### Aggregator Modules (pom-only)

Modules with `metadata.packaging == "pom"` only receive:
- `quality-gate` - Can still run linting/formatting checks

They do **not** receive: `compile`, `test-compile`, `module-tests`, `verify`, `install`, `package`

### Resolution Flow

```
discover_modules():
    for each module:
        commands = {}

        # 1. Always: clean and quality-gate (all modules)
        commands["clean"] = template.clean
        commands["quality-gate"] = template.quality_gate

        # 2. Non-pom modules get verify, install, clean-install, package
        if packaging != "pom":
            commands["verify"] = template.verify
            commands["install"] = template.install
            commands["clean-install"] = template.clean_install
            commands["package"] = template.package

        # 3. Source-conditional
        if has_sources(module):
            commands["compile"] = template.compile

        # 4. Test-conditional
        if has_tests(module):
            commands["test-compile"] = template.test_compile
            commands["module-tests"] = template.module_tests

        # 5. Profile-based enhancements (internal classification)
        for profile in detected_profiles:
            canonical = _classify_profile(profile.id)  # Internal function
            if canonical == "quality-gate":
                commands["quality-gate"] = enhance_with_profile(...)
            elif canonical in ["integration-tests", "coverage", "performance"]:
                commands[canonical] = build_profile_command(...)

        return {... "commands": commands}
```

### Extension Implementation

Extensions return resolved `commands` in `discover_modules()`. Each command is **complete and self-contained** with all routing embedded in `--command-args`:

```python
def discover_modules(self, project_root: str) -> list:
    # Extensions generate complete commands per module
    # All routing (module, profile, workspace) is embedded in --command-args
    # Note: Commands do NOT include clean goal (run clean separately)
    return [{
        "metadata": {"packaging": "jar", "profiles": [...]},
        "commands": {
            "clean": "python3 ... --command-args \"clean -pl my-module\"",
            "module-tests": "python3 ... --command-args \"test -pl my-module\"",
            "verify": "python3 ... --command-args \"verify -pl my-module\"",
            "clean-install": "python3 ... --command-args \"clean install -pl my-module\"",
            "quality-gate": "python3 ... --command-args \"verify -Ppre-commit -pl my-module\""
        },
        ...
    }]
```

## Implementation in Extensions

Profile classification and command generation are handled **internally** by each extension's `discover_modules()` implementation. The `PROFILE_PATTERNS` constant from `extension_base.py` provides the mapping vocabulary for classifying profile IDs to canonical command names.

### Command String Format

Commands embed **all routing** in the `--command-args` parameter:

| Build System | Routing Mechanism | Example `--command-args` |
|--------------|-------------------|-------------------------|
| Maven | `-pl module` flag | `"verify -Ppre-commit -pl oauth-sheriff-core"` |
| Gradle | `:module:task` prefix | `":api-genshin-impact:build"` |
| npm (workspace) | `--workspace=path` flag | `"test --workspace=packages/app"` |
| npm (prefix) | `--prefix path` flag | `"--prefix nifi-cuioss-ui test"` |

**Key principle**: No placeholders, no runtime composition. Commands are generated **once** during discovery with all routing embedded.

## Required Commands

Required commands depend on module type and content:

| Module Type | Required Commands |
|-------------|-------------------|
| **Standard module** (jar, war, etc.) | `quality-gate`, `verify` |
| **Standard module with tests** | `quality-gate`, `verify`, `module-tests` |
| **Aggregator module** (pom) | `quality-gate` only |

**Validation rules**:
- `quality-gate` - Required for all modules
- `verify` - Required for non-pom modules
- `module-tests` - Required only if `stats.test_files > 0`

The orchestrator validates that required commands exist in the `commands` field returned by `discover_modules()`.

## Phase Descriptions

| Phase | Purpose |
|-------|---------|
| **build** | Compile source code |
| **test** | Execute tests |
| **quality** | Static analysis, formatting |
| **verify** | Complete validation |
| **deploy** | Create/install artifacts |

## Extension-Specific Commands

Extensions may define additional commands beyond the canonical set. These are valid within their build system scope but are not part of the canonical vocabulary.

Extensions document their additional commands in their own skill documentation.

## Related Specifications

- [extension-contract.md](extension-contract.md) - Extension API contract
- [build-execution.md](build-execution.md) - Build command execution
- [build-project-structure.md](build-project-structure.md) - Module discovery and metadata

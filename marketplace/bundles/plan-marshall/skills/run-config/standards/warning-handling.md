# Warning Handling

Manage acceptable warnings that should be filtered from build output.

## Purpose

Build scripts use this configuration to distinguish actionable warnings from known/accepted ones. Patterns stored here are used to filter build output in `--mode actionable`.

---

## Warning Categories

| Category | Description |
|----------|-------------|
| `transitive_dependency` | Dependency management warnings about transitive dependencies |
| `plugin_compatibility` | Maven/Gradle plugin version compatibility warnings |
| `platform_specific` | Platform-specific warnings (e.g., Windows vs Unix paths) |

---

## Operations

### Add Warning Pattern

Add a pattern to the acceptable warnings list:

```bash
python3 .plan/execute-script.py plan-marshall:run-config:run_config warning add \
  --category transitive_dependency \
  --pattern "uses transitive dependency"
```

**Options:**
- `--category` - Warning category (required)
- `--pattern` - Pattern to match in warning messages (required)
- `--build-system` - Build system (default: maven)
- `--project-dir` - Project directory (default: current)

**Output (JSON):**
```json
{
  "success": true,
  "action": "added",
  "category": "transitive_dependency",
  "pattern": "uses transitive dependency",
  "build_system": "maven"
}
```

### List Warning Patterns

List all acceptable warning patterns:

```bash
# List all categories
python3 .plan/execute-script.py plan-marshall:run-config:run_config warning list

# List specific category
python3 .plan/execute-script.py plan-marshall:run-config:run_config warning list \
  --category transitive_dependency
```

**Output (JSON):**
```json
{
  "success": true,
  "build_system": "maven",
  "categories": {
    "transitive_dependency": ["pattern1", "pattern2"],
    "plugin_compatibility": [],
    "platform_specific": []
  }
}
```

### Remove Warning Pattern

Remove a pattern from the acceptable warnings list:

```bash
python3 .plan/execute-script.py plan-marshall:run-config:run_config warning remove \
  --category transitive_dependency \
  --pattern "uses transitive dependency"
```

**Output (JSON):**
```json
{
  "success": true,
  "action": "removed",
  "category": "transitive_dependency",
  "pattern": "uses transitive dependency",
  "build_system": "maven"
}
```

---

## Usage in Build Scripts

Build scripts with `--mode actionable` filter warnings matching patterns in `acceptable_warnings`:

```bash
# Run build with actionable mode (default) - filters accepted warnings
python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run \
  --targets "clean verify" --mode actionable

# Run with structured mode - shows all warnings with [accepted] markers
python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run \
  --targets "clean verify" --mode structured
```

---

## Storage

Warning patterns are stored in `run-configuration.json`:

```json
{
  "maven": {
    "acceptable_warnings": {
      "transitive_dependency": ["pattern1", "pattern2"],
      "plugin_compatibility": [],
      "platform_specific": []
    }
  }
}
```

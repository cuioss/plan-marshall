# Config Callback Contract

Extension callback mechanism for configuring project-specific defaults during initialization.

## Purpose

Provides a hook for extensions to set project-specific configuration defaults in `marshal.json` before other components access them. This enables:

- Domain-specific defaults (e.g., profiles to ignore in coverage)
- Project-aware configuration without hardcoding
- User-overridable settings (callback only writes if values don't exist)

---

## Lifecycle Position

The callback is invoked by `marshall-steward` during initialization:

```
1. Script initialization (.plan/execute-script.py)
2. Extension discovery and loading
3. ➤ config_defaults() callback for each extension
4. Plugin access and workflow execution
```

**Timing**: After extensions are loaded but before any workflow logic accesses configuration.

---

## Method Signature

```python
def config_defaults(self, project_root: str) -> None:
    """Configure project-specific defaults in marshal.json.

    Called during initialization to set up domain-specific configuration
    values. Implementations MUST respect existing user-defined values.

    Args:
        project_root: Absolute path to project root directory.

    Returns:
        None (void method)

    Contract:
        - MUST only write values if they don't already exist
        - MUST NOT override user-defined configuration
        - SHOULD use direct import from _config_core module
        - MAY skip silently if no defaults are needed
    """
    pass  # Default no-op implementation
```

---

## Implementation Pattern

### Write-Once Semantics

The critical contract: **only write if the key doesn't exist**. This ensures user-defined configurations are never overwritten.

The `extension-defaults set-default` command implements this automatically - it only writes if the key doesn't exist, eliminating the need for check-then-set patterns.

### Using plan-marshall-config Commands

All configuration operations use the `plan-marshall-config` script API. The script handles file location internally - no file paths needed.

**Recommended pattern** - Direct import for simplicity and performance:

```python
from _config_core import ext_defaults_set_default

def config_defaults(self, project_root: str) -> None:
    """Configure extension defaults."""
    # set_default returns True if set, False if key already existed
    ext_defaults_set_default("my_bundle.my_setting", "default_value", project_root)
```

**Alternative** - CLI via subprocess (when import path unavailable):

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config ext-defaults set-default \
  --key "my_bundle.my_setting" --value "default_value"
```

Values are stored in the isolated `extension_defaults` section of `marshal.json`.

### Available plan-marshall-config Operations

| Operation | Description |
|-----------|-------------|
| `ext-defaults set-default` | Set value only if key doesn't exist (write-once) |
| `ext-defaults get/set/list/remove` | Generic key-value operations in `extension_defaults` |

---

## Example: Generic Extension Defaults

Extensions can store arbitrary configuration using direct import:

```python
from _config_core import ext_defaults_set_default

class Extension(ExtensionBase):
    """Example extension with generic defaults."""

    def config_defaults(self, project_root: str) -> None:
        """Configure extension-specific defaults."""
        # Store comma-separated values
        ext_defaults_set_default("my_bundle.skip_profiles", "itest,native", project_root)

        # Store simple string values
        ext_defaults_set_default("my_bundle.default_mode", "strict", project_root)
```

**Effect**: Values are stored in `extension_defaults` section and can be retrieved with `ext_defaults_get()`.

---

## Example: Profile Skip List and Mappings

Profile configuration uses extension defaults with specific key patterns:

```python
from _config_core import ext_defaults_set_default

class Extension(ExtensionBase):
    """CUI Java extension for pm-dev-java-cui bundle."""

    def config_defaults(self, project_root: str) -> None:
        """Configure CUI-specific profile settings."""
        # Store profiles to skip (comma-separated)
        ext_defaults_set_default("build.maven.profiles.skip", "itest,native", project_root)

        # Store profile-to-canonical mappings (comma-separated profile:canonical pairs)
        ext_defaults_set_default("build.maven.profiles.map.canonical", "pre-commit:quality-gate", project_root)
```

**Effect**: When `discover_modules` runs, it checks extension defaults for skip lists and profile mappings before auto-classifying profiles.

---

## Configuration Operations

Extensions should use plan-marshall-config operations:

| Operation | Use Case |
|-----------|----------|
| `ext-defaults set-default` | Generic extension defaults (write-once) |
| `ext-defaults set` | Generic extension config (overwrites) |
| `ext-defaults set --key build.maven.profiles.skip` | Exclude profiles from discovery |
| `ext-defaults set --key build.maven.profiles.map.canonical` | Map profiles to canonical commands |

---

## Design Rationale

### Why Not Hardcoded?

Hardcoded defaults in extension logic work, but config-callback provides:

1. **User Override** - Users can always set their own values in `marshal.json`
2. **Transparency** - Configuration is visible and editable, not hidden in code
3. **Project Specificity** - Different projects using the same extension may need different values

### Why Write-Once?

The write-once contract ensures:

1. **User Intent** - If a user set a value, they meant it
2. **Idempotency** - Running initialization multiple times is safe
3. **No Surprises** - Configuration never changes unexpectedly

---

## Validation

Extensions with `config_defaults()` implementations should be validated:

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:validate extension \
    --extension path/to/extension.py
```

Validation checks:
- Method signature matches contract
- Uses write-once semantics (doesn't unconditionally overwrite)
- Configuration keys follow naming conventions

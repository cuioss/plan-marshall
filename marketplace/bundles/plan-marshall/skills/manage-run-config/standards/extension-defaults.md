# Extension Defaults

Generic key-value storage for extension-set configuration defaults.

## Purpose

Values are stored in the isolated `extension_defaults` section and follow write-once semantics (only written if key doesn't exist). This enables extensions to set project-specific defaults during initialization without overriding user configuration.

---

## When to Use

Extensions use this API in their `config_defaults()` callback to set project-specific defaults during initialization.

For the Python API and callback implementation patterns, see [extension-api:config-callback.md](../../extension-api/standards/config-callback.md).

---

## CLI Operations

### Set Configuration Value

Set a configuration value (overwrites if exists):

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config extension-defaults set \
  --key "my_extension.setting" --value "value"
```

**Value types supported**: strings, numbers, booleans, JSON objects/arrays

```bash
# String value
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config extension-defaults set \
  --key "feature.enabled" --value "true"

# JSON object
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config extension-defaults set \
  --key "feature.settings" --value '{"timeout": 30, "retries": 3}'
```

**Output (JSON)**:
```json
{
  "success": true,
  "action": "added",
  "key": "my_extension.setting",
  "value": "value"
}
```

### Set Default Value (Write-Once)

Set a value only if the key doesn't exist. This is the primary API for extension callbacks:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config extension-defaults set-default \
  --key "my_extension.setting" --value "default_value"
```

**Output when key doesn't exist**:
```json
{
  "success": true,
  "action": "added",
  "key": "my_extension.setting",
  "value": "default_value"
}
```

**Output when key already exists**:
```json
{
  "success": true,
  "action": "skipped",
  "key": "my_extension.setting",
  "reason": "key already exists"
}
```

### Get Configuration Value

Retrieve a configuration value:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config extension-defaults get \
  --key "my_extension.setting"
```

**Output (key exists)**:
```json
{
  "success": true,
  "key": "my_extension.setting",
  "exists": true,
  "value": "value"
}
```

**Output (key doesn't exist)**:
```json
{
  "success": true,
  "key": "my_extension.setting",
  "exists": false
}
```

### List All Configuration

List all extension defaults:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config extension-defaults list
```

**Output**:
```json
{
  "success": true,
  "count": 2,
  "keys": ["my_extension.setting", "feature.enabled"],
  "values": {
    "my_extension.setting": "value",
    "feature.enabled": true
  }
}
```

### Remove Configuration

Remove a configuration key:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config extension-defaults remove \
  --key "my_extension.setting"
```

---

## Python API

For direct import in extension code (preferred over subprocess):

```python
from run_config import ext_defaults_get, ext_defaults_set, ext_defaults_set_default, ext_defaults_list

# Get value (returns None if not found)
value = ext_defaults_get("my_bundle.setting", project_root)

# Set value (always overwrites)
ext_defaults_set("my_bundle.setting", ["a", "b"], project_root)

# Set default (returns True if set, False if key existed)
was_set = ext_defaults_set_default("my_bundle.setting", ["a", "b"], project_root)

# List all defaults
all_defaults = ext_defaults_list(project_root)
```

---

## Storage

Extension defaults are stored in `run-configuration.json`:

```json
{
  "extension_defaults": {
    "my_extension.setting": "value",
    "feature.enabled": true
  }
}
```

This section is isolated from user-visible configuration to prevent conflicts.

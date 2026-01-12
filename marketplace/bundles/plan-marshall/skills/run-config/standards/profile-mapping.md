# Profile Mapping

Manage profile-to-canonical mappings for build profiles that can't be auto-classified.

## Purpose

When `build_env persist` detects profiles it can't auto-classify, user decisions stored here are applied before command generation. Profiles mapped to 'skip' are excluded from command generation.

---

## Valid Canonicals

| Canonical | Description |
|-----------|-------------|
| `integration-tests` | Integration test profile |
| `coverage` | Code coverage profile |
| `benchmark` | Performance/benchmark profile |
| `quality-gate` | Quality checks profile |
| `skip` | Exclude from command generation |

---

## When to Use

When `build_env persist` reports unmapped profiles:

```
unmapped_profiles[3]{module,profile_id}:
default	jfr
benchmark-core	analyze-jfr
benchmark-core	quick

hint: Use 'run_config profile-mapping set --profile-id <id> --canonical <canonical|skip>'
```

---

## Operations

### Set Profile Mapping

Map a profile to a canonical command or skip it:

```bash
# Map 'jfr' profile to benchmark canonical
python3 .plan/execute-script.py plan-marshall:run-config:run_config profile-mapping set \
  --profile-id jfr --canonical benchmark

# Skip 'quick' profile (internal shortcut, not a standard command)
python3 .plan/execute-script.py plan-marshall:run-config:run_config profile-mapping set \
  --profile-id quick --canonical skip
```

### Get Profile Mapping

```bash
python3 .plan/execute-script.py plan-marshall:run-config:run_config profile-mapping get \
  --profile-id jfr
```

**Output (JSON)**:
```json
{
  "success": true,
  "profile_id": "jfr",
  "mapped": true,
  "canonical": "benchmark"
}
```

### List All Profile Mappings

```bash
# List all mappings
python3 .plan/execute-script.py plan-marshall:run-config:run_config profile-mapping list

# Filter by canonical
python3 .plan/execute-script.py plan-marshall:run-config:run_config profile-mapping list \
  --canonical skip
```

### Remove Profile Mapping

```bash
python3 .plan/execute-script.py plan-marshall:run-config:run_config profile-mapping remove \
  --profile-id jfr
```

### Batch Set Multiple Mappings

```bash
python3 .plan/execute-script.py plan-marshall:run-config:run_config profile-mapping batch-set \
  --mappings-json '{"jfr": "benchmark", "quick": "skip", "analyze-jfr": "skip"}'
```

---

## Complete Workflow

```bash
# 1. Run persist to detect unmapped profiles
python3 .plan/execute-script.py plan-marshall:extension-api:build_env persist

# 2. Set mappings for reported unmapped profiles
python3 .plan/execute-script.py plan-marshall:run-config:run_config profile-mapping batch-set \
  --mappings-json '{"jfr": "skip", "quick": "skip", "analyze-jfr": "skip"}'

# 3. Re-run persist - mappings will be applied
python3 .plan/execute-script.py plan-marshall:extension-api:build_env persist
```

---

## Storage

Profile mappings are stored in `run-configuration.json`:

```json
{
  "profile_mappings": {
    "jfr": "benchmark",
    "quick": "skip"
  }
}
```

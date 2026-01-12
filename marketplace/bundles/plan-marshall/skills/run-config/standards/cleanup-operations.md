# Cleanup Operations

Clean temporary files, logs, archived plans, and memory based on retention settings.

## Purpose

Manage `.plan/` directory storage by removing old files according to configurable retention periods.

---

## Default Retention

| Category | Default Retention |
|----------|-------------------|
| Logs | 1 day |
| Archived plans | 5 days |
| Memory | 5 days |
| Temp files | Always cleaned |

---

## Operations

### Dry Run (Preview)

Preview what would be deleted without making changes:

```bash
python3 .plan/execute-script.py plan-marshall:run-config:cleanup run --dry-run
```

### Run Cleanup

Execute cleanup with default retention:

```bash
python3 .plan/execute-script.py plan-marshall:run-config:cleanup run
```

### Custom Retention

Override retention periods:

```bash
python3 .plan/execute-script.py plan-marshall:run-config:cleanup run \
    --logs-days 1 \
    --archived-days 5 \
    --memory-days 5
```

---

## Output

**TOON format:**

```toon
status: success
operation: cleanup
dry_run: false

deleted[4]{category,count,size_bytes}:
logs	12	45678
archived_plans	3	12345
memory	5	8901
temp	28	56789
```

---

## Cleaned Directories

| Directory | Content |
|-----------|---------|
| `.plan/logs/` | Execution logs |
| `.plan/archived/` | Archived plan files |
| `.plan/memory/` | Memory/context files |
| `.plan/temp/` | Temporary files (always cleaned) |

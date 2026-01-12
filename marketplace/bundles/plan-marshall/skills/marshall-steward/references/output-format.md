# Output Format Standards

All operations return TOON format for structured parsing.

---

## Success Format

```toon
status: success
operation: {operation_name}
data:
  key: value
  nested:
    key: value
```

---

## Error Format

```toon
status: error
error: {error_type}
message: {error_message}
recovery: {suggested_action}
```

---

## Warning Format

```toon
status: warning
operation: {operation_name}
issues:
  - {issue_1}
  - {issue_2}
fixes_available: true
```

---

## Common Operations

### Wizard Complete
```toon
status: success
operation: wizard_complete
gitignore: configured
executor:
  path: .plan/execute-script.py
  script_count: 45
```

### Health Check
```toon
status: success
operation: health_check
executor:
  valid: true
  script_count: 47
overall: HEALTHY
```

### Maintenance
```toon
status: success
operation: maintenance
executor_regenerated: true
cleanup:
  files_deleted: 15
  bytes_freed: 12288
```

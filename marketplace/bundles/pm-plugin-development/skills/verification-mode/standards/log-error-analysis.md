# Log Error Analysis Standard

Post-workflow scan of the **global** script execution log to catch errors that failed before reaching plan-scoped logging.

## Purpose

Scripts that fail due to missing or incorrect `--plan-id` / `--trace-plan-id` parameters cannot log to a plan-specific log file. These errors end up in the global log only. Step 6 of verification mode catches these.

## Detection

Scan the global script execution log:

```bash
grep '\[ERROR\]' .plan/logs/script-execution-$(date +%Y-%m-%d).log 2>/dev/null || echo "No errors"
```

## Common Causes

| Pattern | Likely Cause |
|---------|--------------|
| `required: --plan-id` | Script called without plan-id parameter |
| `required: --trace-plan-id` | Agent script called without trace-plan-id |
| `plan not found` | Invalid plan-id value |
| `unknown notation` | Incorrect script notation in calling component |

## Analysis

For each ERROR entry found, use the existing analysis process from `failure-analysis.md`:

1. **Identify the notation** from the log entry
2. **Trace origin** - which component (agent/skill/command) made the call
3. **Determine if** `--plan-id` or `--trace-plan-id` was required but missing
4. **Propose fix** to the calling component

## Typical Fix

Most global log errors require adding the correct plan parameter to the calling component's script invocation:

- Commands/Skills: Use `--plan-id {plan_id}`
- Agents: Use `--trace-plan-id {plan_id}`

## Related Standards

- `failure-analysis.md` - Full failure analysis process

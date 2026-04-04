# Shared: Update Project Documentation

Check if project docs need required content and apply fixes.

---

## Step 1: Run check-docs

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine-mode check-docs
```

## Step 2: Interpret output

- `status: ok` → No action needed, continue.
- `status: needs_update` → Apply fixes below for each missing marker listed in the output.

## Step 3: Apply fixes (if needed)

The output lists missing content markers by key. For each:

| Key | Target File | Content to Append |
|-----|-------------|-------------------|
| `plan_temp` | Listed file (typically CLAUDE.md) | `- Use .plan/temp/ for ALL temporary files (covered by Write(.plan/**) permission - avoids permission prompts)` |
| `file_ops` | CLAUDE.md | `- Never use Bash for file operations (find, grep, cat, ls) — use Glob, Read, Grep tools instead` |

Append the content to an appropriate section (e.g., "Development Notes") in the target file. If no such section exists, create one.

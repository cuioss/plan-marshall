# Shared: Update Project Documentation

Check if project docs need required content and apply fixes.

---

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine-mode check-docs
```

**Output (TOON)**:
```toon
status	ok
missing_count	0
```

Or if updates needed:
```toon
status	needs_update
missing_count	2
plan_temp	CLAUDE.md
file_ops	CLAUDE.md
```

If `status` is `needs_update`, add missing content to each listed file:

**For `plan_temp`** — add to each file listed:
```
- Use `.plan/temp/` for ALL temporary files (covered by `Write(.plan/**)` permission - avoids permission prompts)
```

**For `file_ops`** — add to CLAUDE.md (e.g. in a "Development Notes" or equivalent section):
```
- Never use Bash for file operations (find, grep, cat, ls) — use Glob, Read, Grep tools instead
```

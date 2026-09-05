# Safe Fixes Guide

Detailed guide for applying safe fixes automatically without user confirmation. See `fix-catalog.md` for safe fix types and their detection patterns.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `doctor-marketplace` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

## Safe Fix Principles

Safe fixes are mechanical transformations that:
- Don't lose information
- Don't change component behavior
- Have deterministic outcomes
- Are always correct to apply

## Applying Safe Fixes

### General Process

1. **Create Backup**: Always backup before modifying
2. **Apply Fix**: Use appropriate strategy for fix type
3. **Validate Result**: Ensure fix was applied correctly
4. **Track Changes**: Record what was changed

### Using the doctor-marketplace fix subcommand

`_fix.py` is unregistered and registers no executor notation of its own. The
safe-fix pass documented here does not run it: `doctor-marketplace fix` reaches
`_cmd_apply.py` directly. Scope by bundle / type / name, with `--dry-run` to
preview:

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace fix \
  --bundles {bundle} --name {component_name} --dry-run
```

Drop `--dry-run` to apply. Each applied fix reports its type, the file it touched,
and the changes it made.

## Batch Application

When applying multiple safe fixes to same file:

```python
# Optimal order
fixes = sorted(fixes, key=lambda f: FIX_PRIORITY.get(f['type'], 99))

for fix in fixes:
    result = apply_single_fix(fix, bundle_dir, templates)
    if not result['success']:
        # Log error, continue with next fix
        continue
```

**Priority Order** (see fix-catalog.md for full list):
1. missing-frontmatter (required for others)
2. invalid-yaml
3. missing-*-field (name, description, user-invocable, tools)
4. array-syntax-tools
5. agent-skill-tool-visibility
6. trailing-whitespace
7. improper-indentation

## Error Recovery

### Backup Restoration

If fix fails mid-application:
```bash
# Backup is at original_file.md.fix-backup
cp file.md.fix-backup file.md
```

`apply_single_fix` does this automatically on error, so the `cp` above is a
manual fallback rather than the normal procedure.

### Validation After Fix

After each fix, validate:
- File is still readable
- YAML is valid (if frontmatter fix)
- No content was accidentally removed

## Tracking Applied Fixes

Maintain tracking JSON:

```json
{
  "bundle": "bundle-name",
  "timestamp": "2025-11-21T10:00:00Z",
  "fixes_applied": [
    {
      "type": "missing-frontmatter",
      "file": "agents/my-agent.md",
      "success": true,
      "backup": "agents/my-agent.md.fix-backup"
    }
  ],
  "summary": {
    "total": 5,
    "successful": 5,
    "failed": 0
  }
}
```

## Simplification Safe Fix (SIMPLICITY_SIGNATURE_DOCSTRING)

The `SIMPLICITY_*` rule cluster enforces the "minimum viable code" posture (`plan-marshall:ref-code-quality` `standards/code-organization.md` § `#minimum-viable-code`). Of the five rules, exactly **one** is a safe auto-apply fix:

- **SIMPLICITY_SIGNATURE_DOCSTRING** — delete a function docstring whose first paragraph only restates `Args:`/`Returns:` with no intent content. The handler (`_cmd_apply.py::apply_signature_docstring_fix`) re-parses the file, finds every signature-restating docstring, and deletes its source lines bottom-up. Deleting a pure-structural docstring changes no behaviour and no signature, so it satisfies all four Safe Fix Principles above.

The other four `SIMPLICITY_*` rules (`SIMPLICITY_UNUSED_PARAMETER`, `SIMPLICITY_BACKWARD_COMPAT_REEXPORT`, `SIMPLICITY_DEFENSIVE_CATCHALL`, `SIMPLICITY_THIN_WRAPPER`) are **NOT** auto-apply — each resolution changes a signature or rewrites call sites, which is a judgement call. They are surfaced for human review (confirm-before-apply); see `risky-fixes-guide.md` § Simplification rules.

## Common Pitfalls

1. **Applying to Wrong Component Type**: Check path for `/agents/`, `/commands/`, `/skills/`
2. **Overwriting Existing Content**: Check for field before adding
3. **Breaking YAML Structure**: Validate YAML after insertion
4. **Empty File Handling**: Check file has content before fixing

## See Also

- `fix-catalog.md` - Fix type reference with detection and fix strategies
- `verification-guide.md` - Verify fixes worked

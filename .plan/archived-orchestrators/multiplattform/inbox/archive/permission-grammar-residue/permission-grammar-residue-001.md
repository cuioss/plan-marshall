envelope_version=1
sender_type=plan
sender_id=permission-grammar-residue
epic=multiplattform
kind=landing
created=2026-09-08T15:35:00Z

```landing-facts
schema=landing-facts/1
plan_id=permission-grammar-residue
epic=multiplattform
pr=#1452
merge_state=merged
deliverables_total=2
deliverables_done=2
total_tokens=unknown
steps=step-4-implement:done,step-5-build-gate:done,step-6-verifier:clear,step-7-pr:done,step-8-merge:done,step-9-self-check:done
```

## Summary

Closed the last two coupling-inventory rows in multiplattform §B (rows 5 and 6) — the permission-DSL residue in a general script, unowned after WS-01 closed and PLAN-14 narrowed its row.

- **D1** — `permission_fix.py`'s permission-DSL residue honestly declines on a non-Claude target: the eight DSL-rendering direct subcommands (`apply-fixes`, `consolidate`, `ensure-wildcards`, `generate-wildcards`, `ensure-executor`, `cleanup-scripts`, `migrate-executor`, `apply-project-step-permissions`) resolve the active target at the subcommand boundary and return an honest `no-op` on non-Claude instead of emitting Claude grammar (`Bash(...)`/`Skill(...)`/`SlashCommand(...)`). `remove-redundant` propagates the third state rather than swallowing it.
- **D2** — `permission_doctor.py`'s direct-script `detect-*` route stops reporting a false zero: `detect-redundant`, `detect-suspicious`, `detect-missing-project-step-permissions` return the ADR-019 could-not-evaluate third state (`skipped`) on a non-Claude target instead of walking empty allow lists. The documented `platform_runtime permission analyze` path was already honest; the direct route is now too.
- Shared seam: `permission_common.is_claude_target()` added so both scripts resolve target identity through one point.

## Residue

- CodeRabbit findings from the initial review were both fixed (SKILL.md de-enumerated; `remove-redundant --scope both` returns `skipped` with a regression test). The account-level CodeRabbit quota prevented a fresh re-review of the post-fix head; `obtained` satisfied condition 6 (a `coderabbitai` body present, every finding handled).
- Pre-existing, out-of-scope: `cmd_add`/`cmd_remove`/`cmd_ensure` in `permission_fix.py` raise an unhandled `RuntimeError` on a non-Claude target via `permission_settings_path` (characterized survivor; not DSL-emitting, not in this plan's done-when).
- D2's direct-route enforcement is now complete; the three standards documents' provenance declaration remains PLAN-14's and was not reopened.
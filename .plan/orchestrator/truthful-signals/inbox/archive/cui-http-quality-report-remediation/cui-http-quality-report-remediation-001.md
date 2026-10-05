envelope_version=1
sender_type=orchestrator
sender_id=cui-http-quality-report-remediation
epic=truthful-signals
kind=finding
created=2026-10-03T06:50:06Z

# Finding: steward `gitignore_setup` never un-ignores the git-tracked orchestrator ledger

**Origin:** cui-http, relocation of `quality-report-remediation` epic (2026-10-02), cuioss/cui-http PR #253.

## Observed

`orchestration-model.md` § Directory Layout states the epic tree under `.plan/orchestrator/{slug}/` (and `.plan/archived-orchestrators/{slug}/`) is **git-tracked**, with only `logs/` staying git-ignored. The managed `.gitignore` block that `marshall-steward:gitignore_setup` writes is:

```
.plan/*
!.plan/marshal.json
!.plan/project-architecture/
!.plan/plugin-doctor.yml
.plan/local/worktrees/
```

`.plan/*` swallows `.plan/orchestrator/` and `.plan/archived-orchestrators/`; no negation is emitted. `gitignore_setup --dry-run` on cui-http reported `entries_added: 0` — the gap is invisible to the steward. Verified against current plan-marshall source (`marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/gitignore_setup.py`, HEAD 5753130cb): the managed constants contain no orchestrator entry.

## Consequence

- `git -C {store_checkout} add` of any ledger file is silently a no-op (ignored path), so the "ledger travels with the clone" contract is false on every steward-configured repo until the operator hand-edits `.gitignore`.
- With `orchestrator.use_worktree` on, `git status` in the ledger worktree shows nothing — new ledger state is indistinguishable from "nothing changed" (a could-not-look reported as clean).
- The orchestrator persona may not edit `.gitignore` (outside the epic tree), so the orchestrator cannot self-remedy; cui-http needed an operator decision to hand-patch it.

## Workaround applied in cui-http

```
# Orchestrator ledger (git-tracked epic trees; logs stay local)
!.plan/orchestrator/
!.plan/archived-orchestrators/
.plan/orchestrator/*/logs/
.plan/archived-orchestrators/*/logs/
```

## Suggested remedy

- `gitignore_setup` emits the four lines above as managed rules (and includes them in `_MANAGED_RULE_LINES` consolidation), so `upgrade` back-fills existing repos.
- A steward health check (or `orchestrator resolve-path` / `scaffold`) detects the store root being git-ignored (`git check-ignore`) and reports it rather than letting ledger adds no-op.

## Related observation (same session)

The relocation from the retired `.plan/local/orchestrator/{slug}/` into the tracked store has no verb: it was a manual `cp -a` + `migrate-layout`. A predecessor closed epic under `.plan/local/archived-orchestrators/` shared the active slug and had to be hand-renamed to the dated-snapshot form (`{slug}-26-09-03`). A `migrate-layout`/`relocate` companion that moves legacy local trees (and resolves slug collisions to the dated-snapshot name) would remove the manual step.

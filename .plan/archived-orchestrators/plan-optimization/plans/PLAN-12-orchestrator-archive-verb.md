# PLAN-12: orchestrator-archive-verb

epic: plan-optimization
workstream: WS-06

> Staged plan spec. Operator-requested 2026-07-18. Adds a NEW convention (no archive verb exists
> today) — `close` currently freezes the epic tree in place as the audit record. Re-ground all
> citations at outline.

## Objective

Add an optional `archive` step to the orchestrator epic lifecycle that physically relocates a CLOSED
epic tree from the active store root `.plan/local/orchestrator/{slug}/` to
`.plan/local/archived-orchestrators/{slug}/`, mirroring the plan lifecycle's
`.plan/local/archived-plans/`. Today `close` freezes in place ("close freezes, never deletes; the
tree remains on disk as the audit record" — `orchestration-model.md`), which is intentional and
stays the default; `archive` is a separate, opt-in post-close move for store-root tidiness.

## Deliverables

### D1 — `archive` verb + `orchestrator.py archive` subcommand

- New `orchestrator.py archive --slug SLUG` subcommand that relocates the epic tree to
  `.plan/local/archived-orchestrators/{slug}/`, main-anchored via the same resolver family used for
  the store root (`get_store_dir` / `resolve_main_anchored_path`) so it works from any worktree cwd.
- New `archive` verb on the `marshall-orchestrator` skill: router entry + `workflow/archive.md`, and
  a Canonical-invocations block for the new subcommand (the plugin-doctor `manage-invocation-invalid`
  / `missing-canonical-block` analyzer reads it).
- **Precondition:** only a `phase=closed` epic may be archived (mirrors plans archiving a done plan).
  Refuse (or warn-and-require-confirm) on a non-closed epic. **Acceptance:** archiving a closed epic
  moves the tree to `archived-orchestrators/{slug}/`; archiving a non-closed epic is refused with an
  actionable message. Idempotent re-run is safe.

### D2 — lifecycle standard + discovery/resume fallback

- Update `persona-marshall-orchestrator/standards/orchestration-model.md`: document the lifecycle as
  `close` (freeze in place) → optional `archive` (relocate), and add `archived-orchestrators/` to the
  layout contract. Keep the "close freezes, never deletes" wording — archive is the additive move,
  not a change to close.
- **Discovery/status/resume fallback:** ensure `status` / `resume` / the on-query store scan still
  resolve an archived epic from `archived-orchestrators/` (analogous to the archived-plan status
  fallback), so archiving doesn't orphan the audit record from the verbs. **Acceptance:**
  `status --slug` and `resume --slug` on an archived epic resolve from the archived location.

> **Outline must decide (do NOT pre-answer):** (1) retention — plans get a 5-day archived-plans
> retention cleanup; epics are the durable audit record, so archived-orchestrators likely has NO
> auto-cleanup (confirm). (2) Whether `close` gains an optional `--archive` flag that chains the move,
> or archive stays a strictly separate verb. (3) Exact fallback read-path for status/resume/scan.

## Out of scope / do NOT expand
- Changing `close` to delete or auto-move by default (close stays freeze-in-place).
- Plan-lifecycle archiving (already exists).

## Expected Surface

- `marshall-orchestrator/scripts/orchestrator.py` (new `archive` subcommand)
- `marshall-orchestrator/SKILL.md` (verb table + Canonical invocations) + new `workflow/archive.md`
- `persona-marshall-orchestrator/standards/orchestration-model.md` (lifecycle + layout)
- possibly `manage-status` orchestrator-store read fallback + `tools-file-ops` `get_store_dir`
- tests: archive-closed (move), refuse-non-closed, status/resume fallback from archived tree

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none in flight — disjoint from PLAN-10 (github) and PLAN-11 (manifest/aspect).
  Startable concurrently.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-12-orchestrator-archive-verb.md"
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-12.md is recorded}

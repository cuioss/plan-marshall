# PLAN-TRUTH-187: steward `gitignore_setup` never un-ignores the git-tracked orchestrator ledger

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-TRUTH-187-gitignore-setup-never-un-ignores-the-tracked-orchestrator-ledger.md` and is queued as one row file, `queue/PLAN-TRUTH-187.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Provenance

Staged 2026-10-05 from inbox message `cui-http-quality-report-remediation-001.md`
(cui-http relocation of the `quality-report-remediation` epic, PR cuioss/cui-http#253).
Corroborated by this orchestrator against plan-marshall HEAD before staging
(see Claim Labels). No staged or live spec in any epic mentions `gitignore_setup`.

## Objective

The steward's managed `.gitignore` block (`gitignore_setup`) ignores `.plan/*` with
exceptions for `marshal.json` and `project-architecture/` only, so the git-tracked
orchestrator ledger (`.plan/orchestrator/`, `.plan/archived-orchestrators/`) stays
ignored on every steward-configured repo: ledger `git add`s silently no-op and the
"ledger travels with the clone" contract is false until an operator hand-edits
`.gitignore`. Ship the managed-rule fix plus an ignored-store detector, so the
gap is closed for new repos, back-filled on upgrade, and loudly reported instead
of silently green.

## Deliverables

Two deliverables, both verified by unit tests through the real writer path
(managed-block emit + consolidate + upgrade back-fill), not by editing a fixture
`.gitignore` by hand.

**D1 — `gitignore_setup` emits the orchestrator negations as managed rules.**
The four lines from the cui-http workaround land in the writer and in
`_MANAGED_RULE_LINES` consolidation, so `upgrade` back-fills existing repos:
`!.plan/orchestrator/`, `!.plan/archived-orchestrators/`,
`.plan/orchestrator/*/logs/`, `.plan/archived-orchestrators/*/logs/` (re-ignore
order matters — the `*/logs/` lines stay after the negations).

**D2 — an ignored store root is reported, never silently no-op.**
A steward health check (or `resolve-path`/`scaffold`) detects the store root
being git-ignored (`git check-ignore`) and reports it, so a ledger `add` can
never again no-op invisibly. Exact wiring (healthcheck vs setup-time probe) is
the plan's verify-at-outline call; the detection helper lives beside the writer.

## Claim Labels

- OBSERVED: the managed writer carries no orchestrator entry — read at `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/gitignore_setup.py` § `GITIGNORE_*` constants (`:82-86`) and `_MANAGED_RULE_LINES` (`:94-112`).
  - verdict: corroborated | checked_at: 14d624bd93a751204eb38a5d849cd32f4ea28493 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Writer constants :82-86 and _MANAGED_RULE_LINES :94-112 carry no orchestrator entry at HEAD.
- OBSERVED: `.plan/*` swallows both ledger homes with no negation emitted — the constants above plus this repo's own hand-maintained negations at `.gitignore:49-59` (outside the managed block), which exist precisely because the writer never emitted them.
  - verdict: corroborated | checked_at: 14d624bd93a751204eb38a5d849cd32f4ea28493 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Repo .gitignore:49-59 hand-maintained negations outside the managed block; writer emits none.
- HYPOTHESIS: the D2 detection helper belongs beside the writer and is surfaced through the steward healthcheck — confirm at `marshall-steward/references/menu-healthcheck.md` and the healthcheck seam (verify-at-outline).
  - verdict: unverifiable | checked_at: 14d624bd93a751204eb38a5d849cd32f4ea28493 | by: truthful-signals/cleanup | rescoped: n/a | evidence: D2 wiring (healthcheck vs setup-time probe) is the plan's verify-at-outline call.
- Verify-first clause: the consolidation pass must keep recognizing old blocks after the new rules land (SHIM(A/B) pattern) — confirm against `consolidate_managed_blocks` before scoping D1's back-fill.
  - verdict: unverifiable | checked_at: 14d624bd93a751204eb38a5d849cd32f4ea28493 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Consolidation SHIM behavior under new rules is the plan's verify-at-outline call.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/gitignore_setup.py` — writer, consolidation, detection helper (D1, D2)
- OBSERVED: `test/plan-marshall/marshall-steward/` — writer/consolidation/back-fill controls (D1, D2)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none among live rows (shipped PLAN-TRUTH-168 touched `upgrade.py` Stage-2 and `sync-defaults`, not the gitignore writer; different files).
- Adjacent to: `marshall-steward/references/upgrade-flow.md` — the back-fill rides the existing upgrade path, no flow change.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-187-gitignore-setup-never-un-ignores-the-tracked-orchestrator-ledger.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

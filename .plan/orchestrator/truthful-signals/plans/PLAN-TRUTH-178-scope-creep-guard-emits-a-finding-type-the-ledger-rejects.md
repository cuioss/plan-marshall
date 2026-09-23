# PLAN-TRUTH-178: The scope-creep guard emits a finding type the ledger rejects, so it can never persist

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-22 from a paste-mode bug report (observed across three firings on API-Sheriff
`plan-28-closeout-residual-hardening`, residuals 9/11/28 vs threshold 5). Every mechanism claim
below was re-grounded against this repo's code at HEAD before staging — the report's incidentals
that did not survive are marked refuted, not carried.

## Objective

**The scope-creep guard fires and nothing persists.** `scope_creep_check` passes
`finding_type='scope_creep_warning'` to the findings store, but that string is not a member of the
store's 14-type taxonomy — so every over-threshold firing ends in `finding_persist_failed` and the
guard's verdict never becomes a finding. A guard that cannot record is a guard that cannot be
triaged, counted, or audited; its verdicts exist only in the check's own error payload.

## Deliverables

Three deliverables. D0 owns a choice with consequences; D1 pins it; D2 stops the recurrence.

**D0 — Close the type gap one way or the other.** Either admit `scope_creep_warning` to
`FINDING_TYPES` (with the store-file, triage-surface, and promotion-routing consequences a new
member carries — `arch-constraint` is the worked precedent, see the taxonomy comment), or remap the
emission to an existing member and document why that member is the honest one. ⛔ Do not do both:
a remapped emission beside a newly admitted type is two overlapping vocabularies for one signal.

**D1 — Matched control, both directions.** An over-threshold residual persists a finding that reads
back from the store with its type, title, and detail intact; an at-threshold residual still emits
nothing and still exits 0. The control fails at HEAD (persist rejected) and passes after the fix.

**D2 — Audit every other hardcoded `finding_type` call site for taxonomy membership.** One sweep:
every literal `finding_type=` / `--type` in marketplace scripts must name a member of
`FINDING_TYPES`, or be filed as its own defect with this spec's evidence attached. Publish the
swept population and its size — this defect was found three times live before anyone checked the
enum.

## Claim Labels

- OBSERVED: `scope_creep_check.py:180` passes `finding_type='scope_creep_warning'` to
  `add_qgate_finding` (in-process primitive, `scope_creep_check.py:55,176-185) — re-verify at
  outline that the call site still hardcodes the string.
  - Corroborated 2026-09-22 at HEAD (`1bd5c6a3`) by the staging session; re-ground at outline per standing rule.
- OBSERVED: `FINDING_TYPES` (`tools-file-ops/scripts/constants.py:96-121`, 14-type taxonomy) has no
  `scope_creep_warning` member; `add_qgate_finding` returns an error status for unlisted types
  (`_findings_core.py` validation), which `_emit_finding` surfaces as a failure descriptor and
  `cmd_check` exits as `finding_persist_failed` — re-verify at outline.
  - Corroborated 2026-09-22 at HEAD by the staging session; re-ground at outline per standing rule.
- OBSERVED (report provenance, mechanism corrected): the report's "CLI `qgate add --type` exits 1"
  and "`check` reports `finding_emitted: true`" describe a pre-fail-loud revision. At HEAD the call
  is in-process and the failure is loud (`finding_persist_failed` with the rejected content inline,
  exit 1) — never silent prose, never a false `finding_emitted: true`. The root type gap is
  unaffected by the correction.
  - Corroborated-with-correction 2026-09-22 at HEAD by the staging session.
- ⚠ HYPOTHESIS: no other hardcoded producer type is outside the taxonomy — ⛔ asserted by nobody;
  D2 owns the sweep (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py` — the emitting call site (D0, D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py` — the `FINDING_TYPES` taxonomy (D0)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/` — the qgate-add path and its type validation (D0, D1)
- HYPOTHESIS: `test/plan-marshall/phase-5-execute/` and `test/plan-marshall/manage-findings/` — D1's controls (verify-at-outline)
- HYPOTHESIS: every other literal producer type site D2's sweep finds (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Shares `phase-5-execute/**` with PLAN-TRUTH-147 and `manage-findings/**` with a dozen staged
  specs — sequence, never pair (N=1 makes this automatic, recorded so a future scope change keeps it).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-178-scope-creep-guard-emits-a-finding-type-the-ledger-rejects.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

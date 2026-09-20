# PLAN-TRUTH-068: `change_type` is one word for two different scopes, and the narrower one narrows the plan

epic: truthful-signals
workstream: WS-01

> Staged 2026-08-08 at the pre-restart reconciliation, from `daemon-baseline-interpreter-is-unregistrable-002`
> (PR #1122's run). **This gives routed cluster C14 an owner** — it had been recorded as an unowned lead
> for want of a first-party instance. It now has one, with a named root cause.

## Objective

`change_type` is meaningful at two different scopes — a **plan's** settled classification and a
**deliverable's** local kind — and one word carries both. `manage-execution-manifest compose` takes
`--change-type` as a required caller-supplied flag and **never reconciles it against
`status.metadata.change_type`**, so a caller that forwards the *first deliverable's* value silently
narrows phase-5 verification **for the whole plan**. This plan separates the two scopes and makes
compose refuse, rather than accept, a value that contradicts the plan's own settled classification.

## Deliverables

1. **D0 — GATE (mutates nothing): derive both scopes and every producer/consumer of each.** Which sites
   mean *plan* `change_type` and which mean *deliverable* `change_type`, in both directions. ⛔ **The
   two-scope split is the finding; do not assume the deliverable scope is the accidental one** until the
   sweep says so.
2. **D1 — compose reconciles against `status.metadata.change_type`.** A `--change-type` that
   contradicts the plan's settled classification is **refused with both values named**, never silently
   accepted. ⚠ Decide explicitly whether the flag should remain caller-supplied at all once a settled
   value exists — a required flag duplicating a stored fact is a lost-update shape.
3. **D2 — name the two scopes apart** wherever both appear, so a caller cannot pass one where the other
   is meant. A rename is preferred to a comment.
4. **D3 — the narrowing decision records which scope it used.** The run's own logs disagreed with
   themselves and nothing noticed; the decision must carry its input.
5. **D4 — tests, each verified to FAIL pre-fix.** (a) The live shape: a plan settled `bug_fix` whose
   caller passes a deliverable's `verification` is refused. (b) A matching pair passes. (c) A control:
   a plan with no settled classification still composes. (d) The narrowing decision names its scope.

Five deliverables — well under the raised cap of 12.

## Claim Labels

- **OBSERVED (filer, first-party on PR #1122's run; NOT re-derived by this orchestrator)**: compose was
  called with `--change-type verification` while `status.metadata.change_type` was `bug_fix`;
  `decision.log` `eafc53` records *"Detected: bug_fix (confidence 85) … Overrides prior heuristic value
  feature"*; `architecture-refresh` read the settled value back correctly at finalize
  (*"Tier 1 skipped - change_type = bug_fix"*). ⇒ **Only the compose call disagreed**, which is what
  makes this a scope confusion rather than a detection failure.
- **HYPOTHESIS (the filer says "likely", and so do we)**: the `verification` value came from
  **Deliverable 1** — `decision.log` `241d24` records D0 being given its own owner *"as Deliverable 1,
  change_type verification, verification profile, zero affected_files"*. ⛔ **Confirm the forwarding
  path by symbol at D0**; a plausible provenance is not a proven one, and the remedy differs if the
  value came from somewhere else.
- **HYPOTHESIS**: cluster **C14** (5 corpus instances, *change_type and plan scoping under-report risk*)
  is the same defect at population scale — confirm/refute by re-deriving those 5 instances against this
  root cause (verify-at-outline). If they are not the same, C14 returns to being an unowned lead and
  this plan stays scoped to the compose reconciliation.
- **Verify-first clause**: re-read `compose`'s `--change-type` handling and
  `status.metadata.change_type` at HEAD before scoping. **#1122 landed after the observation**, so
  confirm the path still exists.

## Expected Surface

- **HYPOTHESIS**: `plan-marshall:manage-execution-manifest` — `compose`, the `--change-type` flag
  (verify-at-outline)
- **HYPOTHESIS**: `plan-marshall:phase-4-plan` — the caller that forwards the value (verify-at-outline)
- **HYPOTHESIS**: `manage-status` — `status.metadata.change_type` as the settled store (read side)

## Dependencies and Sequencing

- ⚠ **Adjacent to `PLAN-TRUTH-014`** (manage-execution-manifest, which absorbed `-021`) — **same
  component, and 014 is AT the 12 cap**, which is why this is a separate plan rather than a merge.
  ⛔ **SERIALIZE against 014; do not pair them** — both touch compose.
- ⚠ Adjacent to `PLAN-TRUTH-045`: 045 owns the manifest **cross-check** that failed to notice this
  narrowing (M3's bare-vs-canonical skip). **Different site, same run, complementary** — 045 makes the
  check able to fire, this makes the narrowing correct. **Cite, do not merge.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-068-change-type-is-one-word-for-two-different-scopes.md"
```

## Write-Boundary

Touches only its own repository source and tests. Creates and edits NO file under
`.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.

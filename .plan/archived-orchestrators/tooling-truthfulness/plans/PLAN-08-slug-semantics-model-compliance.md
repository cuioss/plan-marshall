# PLAN-08: Queue slug semantics are validated, and the bypass pattern gets a mechanism

epic: tooling-truthfulness
workstream: WS-02

> Staged plan spec — one shippable unit of work. SELF-SUFFICIENT.

## Epic Constraints (bind every deliverable)

- **ADR-019 binds reflexively:** every guard is red-first, with matched controls; every
  indeterminate state stays indeterminate, never a checked negative.
- **Confirm the Expected Surface against the tree as the first action.** ⛔ A surface expansion
  updates this section IN THE SAME ACT.
- **No prose-only rules.** Per this epic's own bar (PLAN-05 verify-first clause): a mechanism
  or nothing. A wording that cannot fail before it lands is exactly the vacuous pin this epic
  exists to remove.

## Objective

During `model-provisioning` decompose, every plan row's `slug` was filled with the epic slug.
All writes returned success; `resume-summary` renders verbatim and `corpus enumerate` joins by
`PLAN-NN-` prefix, so every structural check agreed with a semantically wrong ledger — caught
only by human reading (see inbox `model-provisioning-001.md`, archived). The queue-write path
validates id grammar and status vocabulary (PLAN-01) but nothing about slug semantics.

In parallel, the third Muse-plan-lifecycle bypass on record (two tooling-truthfulness
occurrences plus the `model-provisioning` PLAN-01 design-without-a-plan) shows the same shape:
cost-benefit shortcut, self-reported on challenge. Operator direction: this plan also finds a
way to instrument Muse compliance — a mechanism, not a fourth wording, and scoped to what this
epic can enforce (gates and instruments, not model behavior itself).

## Deliverables

1. **D1 — slug semantics stated at the decompose Step 5 write site.** The `{id, slug,
   workstream, …}` placeholder never states `slug` is the plan's own short slug. Add the
   one-line semantic (plan-short-slug, unique within the queue, never the epic slug) where the
   write happens.
   *Done when:* the Step 5 text states the semantic; a reader with only that section cannot
   plausibly fill the epic slug.
2. **D2 — duplicate-slug lint on the queue-write path.** Reject (or flag, per the existing
   rejection vocabulary) a row whose `slug` duplicates another row's or equals the epic slug.
   Red-first, mirroring the PLAN-01 `PLAN_ROW_FIELDS`/`invalid_field` pattern.
   *Done when:* the rejected case fails before the fix and passes after, with a matched
   control (distinct slugs admit cleanly); no previously-valid write newly refuses.
3. **D3 — `resume-summary` self-validation detector for N rows sharing one slug.** Beside the
   existing detectors, so a future mis-fill is reported rather than rendered into agreement.
   Red-first.
   *Done when:* the detector fires on a shared-slug queue and stays silent on a clean one.
4. **D4 — Muse-compliance instrumentation analysis with a mechanism.** Analyze the three
   recorded bypasses for the enforcement point each needed (what gate, at what seam, would
   have refused or redirected it), and implement the mechanism where it touches this epic's
   machinery; where the enforcement point lives outside it (plan-lifecycle core), deliver a
   specified, red-first-testable proposal routed to its owner rather than a wording.
   *Done when:* every occurrence maps to a named enforcement point; each in-epic point ships
   as a gate with red-first guards; each out-of-epic point ships as a specified proposal with
   an owner — zero prose-only rules.

## Claim Labels

- OBSERVED: `model-provisioning` decompose filled all four plan-row slugs with the epic slug;
  all writes succeeded; caught only by human reading — per archived inbox
  `model-provisioning-001.md` and that epic's 2026-09-13 decision log.
- OBSERVED: the queue-write path checks id grammar and status vocabulary but not slug
  semantics (uniqueness, slug≠epic-slug) — read at `orchestrator.py` `cmd_queue`.
- OBSERVED: `resume-summary` renders `{id}-{slug}` verbatim and `corpus enumerate` joins by
  `PLAN-NN-` prefix, so both agree with a slug-wrong ledger — per prior drains in this epic.
- HYPOTHESIS: the three bypasses share enforceable seams addressable by mechanism, not only
  by wording — confirm/refute by D4's analysis mapping each occurrence to its seam
  (verify-at-outline). ⛔ If D4's only available output IS a wording, that refutes the
  deliverable — loop back and re-scope rather than shipping prose.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — D2, D3
- OBSERVED: `test/plan-marshall/plan-orchestrator/**` — the red-first guards
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/decompose.md` — D1
- HYPOTHESIS: D4 mechanism surface — TBD at outline; the analysis declares its surface in the
  SAME ACT it proposes the mechanism (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none in this epic. Docs-disjoint with running PLAN-07 (orchestrator machinery
  vs user docs) — pairable at the gate's verdict, never assumed.
- Adjacent to: `model-provisioning` (where the defect bit) — no edits there; the evidence
  stays a reference.
- Feeds: the retired Watch — this plan's landing closes the recurrence record.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/tooling-truthfulness/plans/PLAN-08-slug-semantics-model-compliance.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO file under
`.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.

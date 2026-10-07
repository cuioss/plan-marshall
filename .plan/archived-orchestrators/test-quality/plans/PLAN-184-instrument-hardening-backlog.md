# PLAN-184: Instrument-Hardening Backlog

epic: test-quality
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-184-instrument-hardening-backlog.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never
> launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
>
> ⛔ **Scope is exactly the five instrument-hardening items below (D1–D5).**
> Each was verified live during staging; every population figure is a LEAD and
> is re-derived before sizing. Deliberately excluded: the B3 severity flip
> (RUNNING PLAN-182 owns it), any module-budget carve or slice work, new
> detector scope beyond D1, and all `.plan/orchestrator/` ledger writes.

## Execution Contract

The executing plan complies strictly with the plan-marshall process and rules: it
runs the phased lifecycle through its managing skills, treats this spec as the binding
brief, verifies every HYPOTHESIS and verify-first clause against the implementing
source before scoping on it, honors the Write-Boundary below, and reports back through
its PR and its inbox message. Standing operator instruction for this epic (opencode): process compliance is mandatory, not advisory.

## Objective

Harden the instruments the campaign exposed as soft — one new detector rule,
two pipeline defects, one trust-boundary fence, and two deferred review
hardenings — so the next campaign runs on instruments that fail closed.
Done when each D-row's Done criterion reads clean at the merge HEAD and no
item below still names an open defect.

## Deliverables

1. **D1 — Timeout-marker detector rule (new scope).** From drained finding
   `module-budget-campaign-completion-010` (fix #1645 verified merged
   `1b4c1ba0`): author a `test-conventions` rule requiring whole-marketplace
   scan tests to carry `@pytest.mark.timeout(N)` above the suite default with
   a comment naming the contention. Detection seam: AST check for a
   whole-tree-scan call with no enclosing per-test timeout marker; must NOT
   recommend raising the suite default (`timeout = 300` stays coupled to the
   `slow_live` budget).
   *Done when:* the rule ships with a failing-before/passing-after control
   (the two #1645 tests as positive controls) and the doctor suite is green.
2. **D2 — Lessons-housekeeping stale field doc.** `finalize-step-lessons-
   housekeeping` SKILL.md still documents retired `manage-references get
   --field modified_files` (field_retired). ⚠️ The full defect report was
   claimed-filed but verified absent tree-wide — re-derive the defect from
   the skill source at dispatch (do not adopt this paragraph as the defect).
   *Done when:* the SKILL.md documents only live fields, with a negative
   control proving the retired field path is gone.
3. **D3 — Surfacer contract-drift blind spot (3rd instance).** The
   self-review surfacer only surfaces changed files, so contract drift whose
   doc side did not change is structurally invisible to its own
   contract-drift check — the class check 5 exists to catch, now with three
   real instances. ⚠️ Same verify-first caveat as D2: re-derive from the
   surfacer source (`_self_review_patterns.py`, `_self_review_detectors.py`).
   *Done when:* the blind-spot class carries a failing-before/passing-after
   control or is closed by construction with the control to prove it.
4. **D4 — `--files-out` plan-state fence.** `--files-out` refuses
   `references.json` but would still overwrite `status.json` or another plan
   file — the guarantee was kept narrow rather than widened silently.
   Extend the fence to the plan directory (deny plan-state paths beyond the
   caller-named output file) without breaking the legitimate
   `derive_gate_bundles --files-file` hand-off.
   *Done when:* a probe writing outside the caller-named file is refused,
   and the sanctioned hand-off still passes.
5. **D5 — Two declined-but-valid CodeRabbit hardenings + review logging.**
   From the slice-1 record: EXCLUDED_DIR_NAMES tomllib derivation +
   `relative_to` rework, and the `_declares_a_test` pytest-exact predicate +
   testdata positive control — both valid as future hardening, neither a
   merge blocker then. Implement both now. Per-PR review logging throughout:
   Tier M `skip-bot-review` label; log label y/n, CodeRabbit skipped y/n,
   Sourcery present y/n + dispositions; every arrived Sourcery comment
   triaged/handled before merge.
   *Done when:* both hardenings land with controls and the D5 log lines are
   in the landing message.

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/` (rules + references) — D1 new detector (WS-03 production scope)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` (lesson-housekeeping skill + gate scripts) — D2 doc fix + D4 fence (WS-03 production scope)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/` — D3 blind spot (WS-03 production scope)
- OBSERVED: `test/_shared/_shared_harness_fixtures.py` + `test/plan-marshall/script-shared/test_conftest_loader_contract.py` — D5 hardenings (test scope)

## Dependencies and Sequencing

- Depends on: PLAN-183 landing (shipped #1602 — the D2/D3 instruments);
  #1645 (merged — D1 positive controls); the slice-1 record (D5 hardening
  texts); `landings/PLAN-182-slice-2.md` (D2/D3 gist preservation).
- Overlaps with: PLAN-182 (RUNNING) owns the module-budget campaign and the
  B3 flip — **this row sequences behind the running plan** (N=1 default);
  the surfaces are disjoint by charter (WS-03 instruments vs WS-04 budget
  carves), so concurrent emission is available on operator word only. Emit
  into a free slot or on operator order.
- Pairs with: none — terminal backlog closure; when D1–D5 read clean, the
  instrument backlog is zero.
- Findings 006–010 (process findings): NOT staged here — process-compliance
  scope, owned by that epic.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-184-instrument-hardening-backlog.md"
```

## Write-Boundary

The plan implementing this spec touches only the scoped sources above. Only
WS-03-chartered production edits under `marketplace/bundles/**` plus the
explicitly named test scopes are admitted — anything outside the Expected
Surface is a scope escalation requiring a spec amendment first. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger
write — and reports its outcome through its PR and its inbox message. The
report carries a complete `landing-facts` block; narrative-only landings cost
a hand-recovery drain every time. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

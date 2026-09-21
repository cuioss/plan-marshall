# Landing Analysis: PLAN-PRQ-02 — Retrospective aspects publish a verdict over a population they never read

epic: post-run-quality
workstream: WS-01
pr: #1550

> Landing record for one shipped plan. Lives at `landings/PLAN-PRQ-02.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Verified against the staged spec (`plans/PLAN-PRQ-02-retrospective-aspects-publish-a-verdict-over-a-population-they-never-read.md`)
and the plan's own landing message (`inbox/retrospective-aspects-publish-verdict-009.md`,
`landing-facts/1`: `deliverables_total=5`, `deliverables_done=5`, merged squash via merge queue).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D0 — derive aspect population, classify all 17 registered aspects | shipped-as-specified | landing-facts `deliverables_done: 5/5`; no contradicting inbox finding |
| D1 — `check-manifest-consistency` stops deriving footprint from a `base_ref` diff | shipped-as-specified | no contradicting inbox finding |
| D2 — `build_time` publishes its population or omits the figure | shipped-modified, correctly | corroborated first-party by this same plan's own retrospective (inbox `-005.md`): the honest-`unavailable`-sentinel half of D2 works exactly as specified, but the message also demonstrates D2 was "necessary but not sufficient" (a downstream writer gap remains, explicitly owned by `PLAN-PRQ-08` D0, not a D2 defect) |
| D3 — `extract-chat-signal` obeys the serialization rule its own sibling contract states | **shipped-incomplete — fix landed at the wrong hop** | inbox `-001.md` (root-cause-corrected by this orchestrator, see `PLAN-PRQ-12`): D3's consumer-side `BlockScalar` wrap is confirmed correct at HEAD, but the value it wraps was already truncated to 69 of 725,532 bytes one hop upstream, in `platform-runtime/_chat_signal_reducer.py`, which D3 did not touch. The symptom D3 was built to fix recurred byte-for-byte on the very next run that exercised it. Follow-up staged as `PLAN-PRQ-12`. |
| D4 — dispatch audit states the strength of its own coverage claim, plus controls | shipped-as-specified | no contradicting inbox finding |

**Net**: 4/5 deliverables land clean; D3 shipped a real, correctly-implemented fix that does not close the
defect it targets, because the defect's true root cause sits one layer upstream of D3's own Expected
Surface. This is not a fidelity failure against the SPEC (D3 did what it said) — it is the spec's own
root-cause diagnosis proving incomplete, caught only by this plan's own retrospective running against its
own output.

## Metrics and Anomalies

- Tokens: 18,653,683 total (`total_tokens`, `landing-facts/1`)
- Duration: 128,684s wall (~35.7h) / ~4h45m worked, per the plan's own report
- Anomalies (from `-009.md` Residue):
  - `pre-submission-self-review` fired 21 times (17 loop-backs, 4 done across re-firings); `finalize-step-simplify`
    fired 27 times; `project:finalize-step-plugin-doctor` fired 20 times. Finalize alone consumed ~13.5M of
    the 18.65M total (a 14× overrun against the plan's `single_module+bug_fix` error anchor).
  - `project:finalize-step-review-retrospective`'s review-vs-gate delta was `excluded`
    (`gate_tree_unsubstantiated`): the self-review loop-back churn left three different `reviewed_commit_sha`
    values across the PR's findings, so no single reviewed-head could be substantiated against the gate's
    certified tree.
  - This plan's own opt-in retrospective aspect filed 8 candidate-lessons to this epic's inbox (`-001`
    through `-008`), 4 of which are defects in `plan-retrospective` itself — found by the aspect running
    against its own plan.

## Routing and Merge Behavior

- Review: automated review ran; no blocking findings recorded at landing.
- CI/merge: squash merge via the platform merge queue, CI green. Archived to
  `.plan/archived-plans/2026-09-21-retrospective-aspects-publish-verdict` (per the operator's landing
  report).

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-PRQ-02 --status shipped`
- [x] row `pr` stamped → `1550`
- [x] row `landing` stamped → `landings/PLAN-PRQ-02.md`
- [x] row `plan_marshall_plan_id` stamped → `retrospective-aspects-publish-verdict`
- [x] epic.md Decisions reconciled (2026-09-21 entry, alongside the ledger-relocation entry)
- [x] follow-up spec staged: `PLAN-PRQ-12` (D3's upstream root-cause fix + tier-gate delivery-integrity gate)
- [x] `PLAN-PRQ-09` D3 widened with two more render-gap shapes (inbox `-003`, `-004`)
- [x] `PLAN-PRQ-08` D0 gained two corroborating-evidence citations (inbox `-005`, `-006`)
- [x] `PLAN-PRQ-09` D4 gained one corroborating-evidence citation (inbox `-007` action #3)
- [ ] Open Defect recorded for inbox `-007` actions #1/#2 (plan-efficiency ratios script, scope-creep
      reconciliation via `manage-references`) — message itself frames these lower-priority; unowned, no
      spec staged
- [ ] lesson promoted from inbox `-008` (argparse-rejection recurrence anti-pattern)
- [ ] all 9 inbox messages archived
- [ ] resume_anchor updated
- [ ] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`

## Follow-Ups

- Root-cause fix for the TOON block-scalar corruption one hop upstream of D3 (inbox `-001`, `-002`) → staged
  as `PLAN-PRQ-12`.
- Two more report-render-gap shapes, same family as `PLAN-PRQ-09` D3's original member (inbox `-003`,
  `-004`) → folded into `PLAN-PRQ-09` D3 (widened, not a new deliverable — the spec was already at the
  6-deliverable split-guard threshold).
- Build-ledger writer gap (inbox `-005`) and `record-dispatch-boundary` missing 4 token component fields
  (inbox `-006`) → both corroborating citations into `PLAN-PRQ-08` D0 / its `truthful-signals`
  PLAN-TRUTH-160 ownership note; no new spec.
- LLM-to-script opportunities (inbox `-007`): action #3 (per-deliverable recall) → confirming citation into
  `PLAN-PRQ-09` D4. Actions #1/#2 (plan-efficiency-ratios script, scope-creep via `manage-references`) →
  recorded as a new unowned Open Defect in epic.md; message itself frames these lower-priority.
- Argparse-rejection recurrence anti-pattern (inbox `-008`) → promoted to the lessons corpus, component
  `plan-marshall:persona-plan-marshall-agent`, category `anti-pattern`.

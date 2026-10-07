# PLAN-06: A pin that cannot fail is not a pin

epic: tooling-truthfulness
workstream: WS-05

> Staged plan spec — one shippable unit of work. SELF-SUFFICIENT.

## Epic Constraints (bind every deliverable)

- **ADR-019 binds reflexively**, and here it binds twice: the subject is tests that cannot distinguish pass from vacuum, and the fix must itself be shown to fail before it lands.
- **Confirm the Expected Surface against the tree as the first action.** ⛔ A surface expansion updates this section IN THE SAME ACT.

## Objective

`test_script_performs_no_settings_io` asserts that certain strings are absent from its own module's
source text. It sets no target, drives no project and touches no filesystem — so it breaks on an
innocent rename and passes for any bypass not spelled with those literals. It fails in BOTH
directions, which is the defining property of a pin that pins nothing. `inspect.getsource` appears
across EIGHT test files, and whether the other seven are legitimate uses is unknown.

⛔ **SURVEY FIRST, FIX SECOND.** The deliverable count is DERIVED from what the survey finds, not
declared here. A plan that pre-commits to fixing eight sites before knowing how many are defects
would manufacture work — which is the same failure as a test that manufactures assurance.

## Deliverables

1. **D1 — survey every `inspect.getsource` use and classify it.** Eight files at last count; re-derive, the figure is a lead. Each use is one of: a **vacuous pin** (asserts on source text where behaviour was the stated property), a **legitimate use** (source inspection genuinely IS the subject — a docstring contract, a generated-code check), or **indeterminate**.
   *Done when:* every use carries a classification with its reason, and the counts ride with the population they were computed over. ⛔ An indeterminate classification is a legitimate outcome and is NOT rounded into either other class.
2. **D2 — replace the confirmed vacuous pins with behavioural ones.** `test_script_performs_no_settings_io` is confirmed: its done-condition asked for a test that sets `runtime.target` to a non-Claude value and asserts no `.claude/settings*.json` is written. Ship that test, plus whatever D1's survey confirms.
   *Done when:* each replaced pin drives the real code path and asserts on the observable outcome; each is mutation-verified red before the fix; and each carries a matched control so a change that makes it always-pass is caught. ⛔ **The deliverable count for this item is derived from D1** — state it in the PR body and re-evaluate the scope-bloat guard against the derived count.

## Claim Labels

- OBSERVED: `test_script_performs_no_settings_io` is at `test/plan-marshall/workflow-permission-web/test_permission_web.py`:169 and calls `inspect.getsource` at :181 — read directly 2026-09-10.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: test/plan-marshall/workflow-permission-web/test_permission_web.py:169 defines test_script_performs_no_settings_io and :181 calls inspect.getsource(mod) - exact match to the claim
- OBSERVED: `inspect.getsource` resolves to 16 hits across 8 test files via `architecture search --content` — measured 2026-09-10. ⚠️ **The 8 is a file count, not a defect count.** Eight files is the population to survey, not the work list.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: inspect.getsource resolves across the 8 named test trees (automatic-review, phase-6-finalize, plan-retrospective, platform-runtime, script-shared, workflow-integration-github, workflow-permission-web, plugin-doctor) - file-count claim corroborated; defect-count is D1's survey
- HYPOTHESIS: the other seven files' uses are a mix rather than uniformly vacuous — confirm/refute by D1's survey (verify-at-outline). ⛔ Do not assume the class; PLAN-14's is the only confirmed instance.
  - verdict: unverifiable | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: whether the other seven files' inspect.getsource uses are a mix is D1's survey outcome, not settleable from a source read at HEAD - the survey classifies each use
- Verify-first clause: **if the survey finds a broad class, handing it to the sibling `test-quality` epic is the CORRECT outcome, not a failure of this plan.** That epic already owns anti-vacuity work (#1430, #1443) and has the instruments. Report the finding, stage nothing here, and say so.
  - verdict: unverifiable | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: whether the survey finds a broad class warranting hand-off to the test-quality epic is D1's finding, not source-settleable at HEAD

## Expected Surface

- OBSERVED: `test/plan-marshall/workflow-permission-web/test_permission_web.py` — D2's confirmed instance
- HYPOTHESIS: `test/plan-marshall/automatic-review/` — carries `inspect.getsource` (verify-at-outline; D1's survey decides whether it is touched)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/` — same
- HYPOTHESIS: `test/plan-marshall/plan-retrospective/` — same
- HYPOTHESIS: `test/plan-marshall/platform-runtime/` — same
- HYPOTHESIS: `test/plan-marshall/script-shared/` — same
- HYPOTHESIS: `test/plan-marshall/workflow-integration-github/` — same
- HYPOTHESIS: `test/pm-plugin-development/plugin-doctor/` — same

⚠️ **The seven directories above are declared as SEPARATE entries deliberately.** They were first
written as a comma-joined list inside one prose bullet, and the parser resolved NONE of them — the
spec claimed 2 paths while the plan would sweep 9. That is the under-declaration class this epic
exists to close, produced while staging this epic. Caught by reading `corpus surfaces` rather than
the spec text, which is the only instrument that would have caught it. ⛔ **D1's survey decides which
are actually touched; the surface is narrowed or widened in the SAME ACT when it does.**
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-permission-web/scripts/permission_web.py` — only if D2's behavioural test needs a seam the script does not expose (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: **nothing in this epic** — no other member touches `test/` outside the orchestrator's own tests. ⚠️ But it DOES overlap the sibling `test-quality` epic's territory; re-derive that epic's live plan set before launch.
- Adjacent to: the orchestrator's own tests (`test/plan-marshall/plan-orchestrator/**`), which PLAN-01, PLAN-04 and PLAN-05 edit. ⛔ If D1's survey reaches that directory, sequence against whichever of those is live.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/tooling-truthfulness/plans/PLAN-06-test-falsifiability-survey.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO file under
`.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.

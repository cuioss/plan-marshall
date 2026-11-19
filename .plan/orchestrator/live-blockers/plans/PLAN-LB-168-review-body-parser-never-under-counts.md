# PLAN-LB-168: The review-body parser never answers fewer findings than the body declares — four under-count paths of PLAN-LB-162 stop or count instead

epic: live-blockers
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> Staged on the operator's word. Source: `landings/PLAN-LB-162.md`, layer-3 findings L3-1 to L3-4 (four majors, read by one leaf and re-read by the orchestrator at the merge commit), and the Open Defect "Residual under-count paths of the PLAN-LB-162 parser" in `epic.md`.
> Shares one file, `runbook_lane.py`, with PLAN-LB-167 in different functions: a single shared file sequences nothing.

## Objective

PLAN-LB-162 taught the review gate to read every counted section of a review body, including the CAUTION-shape block. Its landing ended `budget-exhausted` on an unconfirmed fifth round, and four hand-traced inputs show the reading can still answer FEWER findings than the body declares, which is the one direction the gate's own contract forbids: a declared finding that mints nothing lets the gate answer `all_handled`. Before the change, three of the four shapes stopped the gate as `undecidable_read`.

This plan closes the four paths so each one either counts the declared findings or stops as `undecidable_read` with a named cause, never reads fewer. How often a real CodeRabbit body takes one of these shapes is not shown; the fix does not depend on it, because an under-count is the unsafe direction whatever the frequency.

## Deliverables

1. A bold heading that declares a positive count and owns no `<details>` block no longer mints nothing. Today `bold_headings` keeps only headings that own a block (`runbook_lane.py` lines 2776-2779), by design, so a heading mentioned in prose does not mint a finding, and a test pins the drop. The outline settles how a counted heading whose rows are plain markdown, or that is followed directly by a section or a file-list block, is told from a heading that is only mentioned in prose, and the gate either counts it or stops as `undecidable_read` naming the heading; it never answers `all_handled` over a count it dropped. The pinning test is rewritten to the new rule with its reason stated.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:runbook-lane
   - Persona: implementer
2. A counted, unrecognised wrapper no longer swallows a recognised section nested inside it. `<details><summary>Review (1)</summary><details><summary>Nitpick comments (10)</summary>…</details></details>` reads the outer title as an `unclassified` heading (PLAN-LB-162's rule for a counted unknown title), the inner recognised section becomes content, and the outer count of 1 wins over the 10 nitpicks; the same body stopped as `undecidable_read` before PLAN-LB-162. A wrapper that contains a recognised section is read through, not as a finding section of its own, or the body stops; the `_enclosing_sections` docstring already states that a wrapper must not drop findings.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:runbook-lane
   - Persona: implementer
3. One stray `**` earlier in the body no longer shifts the heading pairing. `_BOLD_SPAN_RE` (`\*\*(?P<title>[^*]+?)\*\*`) is run with `finditer` over the whole body, so `x **kwargs y **⚠️ Outside diff range comments (1)**` pairs the first two markers and the real heading's opening marker is consumed; the backtick filter pairs backticks the same way. A `**kwargs` in a Python review is a plausible stray. The heading is read, or the body stops as `undecidable_read`, whatever an unpaired marker earlier in the body does.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:runbook-lane
   - Persona: implementer
4. An unclosed `<code>` or `<dd>` is bounded by its own block at every depth. `_inside_prose` starts its scan at `stack[-1]`, the innermost block still open at the heading (lines 2421-2442), which for `<details><summary>Walkthrough</summary><details><summary>Nitpick comments (1)</summary><dd>see <code>a.py </dd></details> **Outside diff range comments (1)** <details><summary>Major · b.py</summary>fix</details></details>` is the outer wrapper, so the inner block's unclosed `<code>` leaves the code depth at 1 and the heading is read as prose and its finding lost. The PLAN-LB-162 landing says an unclosed `<code>` or `<dd>` ends with its own block; the code holds that only at the top level.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:runbook-lane
   - Persona: implementer
5. Tests pin D1 to D4, written against the unfixed tree first, one case per path with the exact input above (the four inputs are hand-built and labelled as such), each asserting the declared count is counted or the stop is raised and named, plus the controls that hold at `main` `46d3308ea`: the captured #1983 and #1984 shapes still read as the PLAN-LB-162 tests state, a heading mentioned in prose still mints nothing, and an uncounted title is still ignored. Where the repository holds a captured full CodeRabbit body, one test runs the parser over it unchanged, so the fix is also shown on a real body and not on constructed ones alone.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-dev-python:pytest-testing
   - Persona: module-tester

## Standing Constraints

- The direction never changes: a body that declares N findings yields N findings or a stop, never fewer. Where a fix cannot decide, it stops with a named `undecidable_read` cause.
- The eight-title allow-list, the `unclassified` rule for a counted unknown title and the `minor` kind of PLAN-LB-162 are unchanged; a heading mentioned in prose still mints nothing.
- The fix does not enlarge `_body_findings`: it is already about 180 lines with four nested closures. A new helper or a simplification is welcome where it keeps the four fixes readable; a fifth interleaved heading model is not.
- Order inside the plan: deliverables 1 to 4, then deliverable 5 written against the unfixed tree.
- No `SKILL.md` edit: PLAN-LB-167 owns the lane skill's document. The verdict-list wording gap recorded in `landings/PLAN-LB-162.md` is a minor and stays out of this plan.
- No file outside the runbook lane's script and its review-gate test is touched. No change under `.plan/orchestrator/` other than the plan's own inbox message.
- Scope-bloat note: five deliverables; the four fixes share one function and one test module, so splitting them would only create merge conflicts. The rationale is recorded as an epic decision.

## Claim Labels

- OBSERVED (re-read at the merge commit `4c9449a73` on 2026-11-19, the same tree as `main` `46d3308ea` for this file): `runbook_lane.py` lines 2776-2779 (`bold_headings = [… if owned_blocks.get(candidate[0])]`), lines 2720-2726 with 2489-2492 (`containers` assigns every summary to the nearest summary whose `heading_at` is not `None`), lines 2760-2767 with `_BOLD_SPAN_RE` at line 2225 (`finditer` over the whole body), and lines 2421-2442 (`region_start = stack[-1]`) are as described in Deliverables.
- OBSERVED (leaf reading of the tests, not re-read): a test at `test_runbook_lane_review_gate.py:1173` pins the drop of a bold heading that owns no block, and the PLAN-LB-162 tests cover the unclosed `<code>` only at the top level.
- OBSERVED: the four inputs are hand-traced from the code, not run; each is a constructed shape. How often a real CodeRabbit body takes one is NOT shown (landing, layer 3 not shown by reading, L3-9).
- HYPOTHESIS: `_heading_section` returns `unclassified` for a counted unknown title, which makes the outer wrapper of D2 a heading. It was not re-read in the analysis; confirm at `runbook_lane.py` § `_heading_section` (verify-at-outline).
- HYPOTHESIS: the line numbers above are unchanged at the tip of `main` when the plan starts, after PLAN-LB-164, 165 and 167 may have merged; re-read each at outline (verify-at-outline).
- Verify-first clause: the outline settles (a) how D1 tells a counted heading with plain-markdown rows from a heading only mentioned in prose, and what it does for each; (b) which of D2's two fixes (read the wrapper through, or stop) keeps the existing nested-container tests green; (c) whether D3 is fixed by pairing per line or paragraph, by a tokenizer, or by a parity stop, and which of those keeps a legitimate `**bold**` heading and a backtick span working; (d) whether the repository holds a captured full CodeRabbit body for the real-body test; (e) the stop causes it names, so the verdict reasons stay a closed list. A refutation of (a) or (c) loops back to re-scope.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py`
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane_review_gate.py`

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-LB-167 in `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py`, one file, in different functions. PLAN-LB-167 also declares the lane skill document, the Sonar skill and their tests, none of which this plan touches.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py`, which PLAN-LB-162 edited for the refusal wording and which this plan leaves untouched.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-168-review-body-parser-never-under-counts.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox message.

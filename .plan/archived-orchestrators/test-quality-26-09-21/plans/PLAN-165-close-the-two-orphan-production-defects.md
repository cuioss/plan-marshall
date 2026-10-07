# PLAN-165: Close the Two Orphan Production Defects

epic: test-quality
workstream: WS-03

> Staged plan spec. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

> **Split from PLAN-145 at cleanup.** Both defects live in WS-03's tree and both were routed to PLAN-090
> and left undone, but neither has anything to do with parser seams — bundling them delayed the seams
> PLAN-150 is blocked on. See the epic's `## Decisions`.

## Objective

Two production defects in `marketplace/bundles/**` were each found by a landed reduction plan, routed to
PLAN-090, and left undone: an import arrangement PLAN-040 reported as a circular import behind a
bottom-of-file lint suppression, and a script at 52.6% coverage that is the sole reason a landed plan's verification condition did not
hold. Neither is test debt and neither belongs to a reduction slice, so both have sat unowned since. Close
them.

## Deliverables

1. **D1 — Adjudicate the `github_ops` import arrangement, then act on the verdict.**
   ⛔ **RE-SCOPED AT CLEANUP — the original premise did not survive re-grounding.** It read as one accidental
   cycle to break. At HEAD it is a **uniform, documented pattern across three module pairs**:
   `github_ops.py` bottom-imports `_github_ci` (`:1849`), `_github_issue` (`:1858`) and `_github_pr`
   (`:1868`), each behind `# noqa: E402 — bottom import: primitives must be defined first`, and **all three**
   siblings import `github_ops` at module scope (`:22`, `:16`, `:56`). ⚠️ **These line numbers were
   re-grounded at HEAD `9853a7ab` and are current as of that sha; the previous set (`:1754`/`:1762`/`:1772`
   and `:26`) had drifted. Re-derive them rather than quoting them** — this spec has now had its
   references go stale once. The `_github_ci` and `_github_issue`
   preambles state the reason outright: the handler modules reach every monkeypatch-sensitive primitive by
   **attribute access on the imported module at call time** — *"never `from github_ops import <name>`, which
   would defeat a test's `monkeypatch.setattr(github_ops, '<name>', ...)`"*. PLAN-090's decline now reads as
   **correct on the merits**, not as work skipped.
   So the deliverable is to **decide, with evidence, whether the pattern stands** — and the plan is closed
   either way:
   * **If it stands** — record the decision where the next reader meets it. The suppression comments say
     *"primitives must be defined first"*, which explains the ordering and not the cycle; make them say why
     the cycle is intended, and report D1 **closed by decision**, not by change.
   * **If it does not** — the fix is **all three pairs**, not one.
   ⛔ **Do not fix `_github_pr` alone.** The arrangement is uniform; fixing one pair leaves the identical
   shape in two siblings and the bottom-import block still in place, while making the tree look repaired.
   ⛔ **Any change MUST preserve `monkeypatch.setattr(github_ops, …)` interception.** That is the documented
   reason the imports are shaped this way. A refactor that quietly breaks test interception is worse than
   the arrangement it replaces, and it breaks silently — the tests keep passing while they stop patching.
   ⛔ **A cycle broken by re-ordering imports is not broken.** The check is that neither module imports the
   other at module scope, not that the linter stopped complaining.
   *Done when:* the adjudication is recorded with the preamble rationale quoted and either accepted or
   refuted on the merits; **if refuted**, no pair imports the other at module scope, all three bottom
   imports and their suppressions are gone, interception is demonstrated still working, and the affected
   tests pass in **default and reverse** directory order; **if accepted**, the rationale is written where
   the suppression is, and the report says D1 closed by decision.

2. **D2 — Raise `credentials.py` coverage.** It sits at **52.6%** and is the stated sole cause of
   PLAN-090's own verification condition 2 falling (83.40% → 83.34%).
   ⚠️ **Measure it first and report the measured baseline rather than adopting the lead.** That figure
   could not be re-derived during ingestion — no coverage artifact existed in the clone — so it is an
   **unverifiable** claim, not a verified one.
   ⛔ **Cover branches, not lines.** A test that imports the module and asserts nothing raises the number
   and closes nothing; the deliverable is that the credential-handling paths are exercised.
   *Done when:* the file's coverage is reported before and after with the command that produced it; the
   whole-project aggregate is reported at both ends; and any branch left uncovered is named with why.

3. **D3 — Give `test_configure.py`'s hardcoded auth type one definition.** Folded in from PLAN-155's
   landing (2026-09-09), where CodeRabbit raised it on PR #1455 and it was **deferred rather than
   rejected** — PLAN-155's Expected Surface excluded `marketplace/bundles/**`, and this plan already
   owns `credentials.py`. `test/plan-marshall/manage-providers/test_configure.py:250` hardcodes a
   configure-specific auth type that production does not expose, so the value has two definitions that
   drift independently. The remedy is a **named constant in `credentials.py`** the test imports.
   ⚠️ **The shared shape across all three deferred nitpicks is *a test mirroring a production set that
   production does not expose*** — the other two (`platform_runtime.py`'s operation registry,
   `permission_fix.py`'s parser construction) fall OUTSIDE this plan's declared surface and stay with
   WS-03 / WS-04. Do not widen into them. Lesson `2026-09-08-21-001`.
   ⛔ **Verify the constant is actually consumed**, not merely defined — a constant the test does not
   import leaves both definitions standing and closes nothing.
   *Done when:* the constant exists in `credentials.py`, `test_configure.py` imports it, no literal of
   that value remains in the test, and the reverse-order run is clean.

4. **D4 — Report the measured deltas.** The import-cycle before and after with the import statements
   quoted; the reverse-order result; the coverage figures for `credentials.py` and for the project; the
   auth-type constant's definition and consumption sites; and the collected test count before and after.
   *Done when:* the report carries every figure with the command that produced it.

## Claim Labels

- OBSERVED: the cycle is confirmed present at HEAD — and it is **three cycles, not one**. `github_ops.py`
  carries `from _github_ci import` (`:1754`), `from _github_issue import` (`:1762`) and `from _github_pr
  import` (`:1772`), each `# noqa: E402 — bottom import: primitives must be defined first`; `_github_ci.py:22`,
  `_github_issue.py:16` and `_github_pr.py:26` each carry `import github_ops`
  - verdict: contradicted | checked_at: 9853a7ab | by: test-quality/cleanup | rescoped: yes | evidence: the three-cycle STRUCTURE is confirmed intact at HEAD 9853a7ab but every line reference has drifted. github_ops.py bottom-imports are now at :1849 (_github_ci), :1858 (_github_issue) and :1868 (_github_pr), not the claimed :1754/:1762/:1772 - a uniform +95 shift; each still carries the noqa E402 bottom-import comment. On the other side _github_ci.py:22 and _github_issue.py:16 still match exactly, but _github_pr.py carries import github_ops at :56, not the claimed :26. Re-scoped on all six line numbers; the defect itself is unchanged and still present.
- OBSERVED — **the claim that re-scoped D1**: the module-scope `import github_ops` is **deliberate and
  documented**. `_github_ci.py:6-14` and `_github_issue.py:5-12` state that every monkeypatch-sensitive
  primitive is reached by attribute access on the imported module at call time — *"never `from github_ops
  import <name>`, which would defeat a test's `monkeypatch.setattr(github_ops, '<name>', ...)`"*. The
  arrangement is an entry-module/handler-module split with a stated testability rationale, uniform across
  three pairs — ⛔ **not an accident to be repaired without first refuting the rationale**
  - verdict: corroborated | checked_at: 9853a7ab | by: test-quality/cleanup | rescoped: n/a | evidence: confirmed present at HEAD 9853a7ab and INSIDE both claimed ranges: the testability rationale sits at _github_ci.py:13-14 (claimed :6-14) and _github_issue.py:10 (claimed :5-12), both carrying the operative sentence - never from github_ops import <name>, which would defeat a test's monkeypatch.setattr(github_ops, ...). Unlike claim 0's line references this claim's ranges still bound their subject. The rationale therefore still stands unrefuted, and D1's re-scoping onto adjudicate-then-act remains correct.
- OBSERVED: PLAN-090 checked the cycle and **explicitly declined** it as outside its deliverable set —
  read at `.plan/orchestrator/test-quality/archive/090-harness-and-rule-gaps/report-01.md` § Residue, which records it as *open and
  unowned*
  - verdict: corroborated | checked_at: 9853a7ab | by: test-quality/cleanup | rescoped: n/a | evidence: re-confirmed at HEAD 9853a7ab: archive/090-harness-and-rule-gaps/report-01.md is present and carries its Residue section, recording the cycle as explicitly declined by PLAN-090 and left open and unowned. This claim reads a FROZEN archive report rather than live source, so it is stable by construction - it cannot drift the way claim 0's line references did. Re-stamped to record that it was re-checked at this HEAD, not assumed.
- HYPOTHESIS: `credentials.py` is at **52.6%** and is the sole cause of PLAN-090's aggregate coverage fall
  — confirm/refute by running coverage over that module and the project (verify-at-outline).
  ⛔ **An UNVERIFIABLE figure at ingestion, not an unverified one**: no coverage artifact existed to read,
  and running a build is outside the orchestrator's boundary. **D2 measures before it acts.**
  - verdict: unverifiable | checked_at: 9853a7ab | by: test-quality/cleanup | rescoped: n/a | evidence: UNCHANGED and unchanged for the same reason: the 52.6% coverage figure still cannot be re-derived in a read-only pass. No coverage artifact exists in the tree and running one is a build, which is outside the orchestrator boundary. This is an UNVERIFIABLE claim, not an unverified one, and the claim itself says so - it is a verify-at-outline HYPOTHESIS and D2 is written to measure before it acts. Re-stamped at HEAD rather than left at bf1b7ed6 so the record shows the question was re-asked and is still unanswerable from here, not that it was forgotten.
- OBSERVED: PLAN-090 shipped a `build_parser()` seam and a `main()` on `credentials.py` (`:29`, `:153`),
  so the module has a CLI surface a coverage test can drive. ⛔ **Not this plan's to change** — PLAN-145
  owns the seam work
  - verdict: corroborated | checked_at: 9853a7ab | by: test-quality/cleanup | rescoped: n/a | evidence: re-measured at HEAD 9853a7ab: credentials.py carries def build_parser() at line 29 and def main() at line 153, BOTH exactly as claimed and unmoved since bf1b7ed6. The CLI surface a coverage test can drive is present, so D2's approach is unblocked. Note this is the one PLAN-165 claim whose line references did NOT drift, which is why it is worth stating explicitly rather than folding into a general everything-holds sentence.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py` — D1
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — D1
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_ci.py` — D1.
  ⚠️ **Added at cleanup** — it carries the identical shape and the rationale D1 must adjudicate
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_issue.py` — D1.
  ⚠️ **Added at cleanup**, same reason
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-providers/scripts/credentials.py` — D2
- OBSERVED: `test/plan-marshall/workflow-integration-github/` — D1's own tests. ⚠️ **PLAN-040's slice**;
  this plan writes only the tests its own production change requires
- OBSERVED: `test/plan-marshall/manage-providers/` — D2's coverage tests. ⚠️ **PLAN-060's slice**; same
  bound

## Dependencies and Sequencing

- Depends on: PLAN-090 (landed). Nothing blocks it, and nothing is blocked on it — which is why it was
  split out of PLAN-145 rather than left to delay the seams.
- ⛔ **Must not run concurrently with**: PLAN-145, PLAN-160, PLAN-105 (§ D3 and § D7) — all in WS-03's
  exclusive tree — or PLAN-120 if its checker lands under `marketplace/bundles/**`.
- ⚠️ **Its test half sits in two reduction slices** (`workflow-integration-github/` is PLAN-040's,
  `manage-providers/` is PLAN-060's). Confirm no campaign run or sweep is holding either before writing.
- **May run concurrently with**: PLAN-110, PLAN-150, PLAN-155 — subject to the caution above.

## Out of Scope

- **Publishing a parser seam.** PLAN-145's.
- **Any other `manage-providers` or `workflow-integration-github` production change** not required by D1
  or D2. Two defects were routed here because they were orphaned, not because this is a general
  maintenance plan for those skills.
- **Refactoring `github_ops.py` beyond breaking the cycle.** The file is large; making it smaller is a
  different plan with a different argument.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-165-close-the-two-orphan-production-defects.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

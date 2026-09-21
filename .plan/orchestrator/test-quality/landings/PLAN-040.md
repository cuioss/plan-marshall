# Landing Analysis: PLAN-040 — Delivery Pipeline Test Reduction

epic: test-quality
workstream: WS-02
pr: not recorded in the archived report (one run)

> Landing record for one shipped plan. Written after verifying claims against ground truth at HEAD
> `2cd1a19c` by a dispatched read-only `execution-context-level-3` leaf.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — strip history from docstrings and comments (**B3**) | **shipped-as-specified against its done-when; partial against its own prose, and it says so** | Rule-shaped re-derivation is clean: bare `deliverable D\d+` → 0; `PR #\d+` → 3, **all string-literal test data** (fixture titles), exactly the exemption the report names; `TASK-\d{3}` → 1, also a literal filename. The report **explicitly discloses** 92 further citations in shapes the rule's regexes do not match. This honest partial is the model the sibling plans should have followed |
| D2 — one fixture corpus and one driver per module (**B4**) | **not started** | `monkeypatch.setattr` : `@pytest.fixture` = **941 : 49**, a ratio of ~19.2:1 — consistent with an unconverted slice |
| D3 — collapse the duplicated subprocess/in-process assertion layer (**B9**) | **not performed at all** | **124** `run_script(` call sites remain, **none paired** with a subsuming in-process test. `test_github.py` and `test_gitlab.py` each still carry 3 call sites. The report initially called this partial and **self-corrected**: the work actually done was **B5** parametrization, which its own out-of-scope sanctioned but which is not D3. Only the call-site *count* fell (31→3, 28→3), not the execution count — no collapse occurred |
| D4 — split every module over the 400-line budget | **not done, correctly ordered last** | **57** modules over budget at HEAD (report: 55). The campaign has not reached this slice |
| D5 — normalise preambles (**B7**) and namespaces (**B6**) | **shipped-partial, done-when explicitly NOT met** | Preamble half: 42 → 24 doctor findings; **11** files still carry `spec_from_file_location` and **7** the deep `Path` chain — nonzero, so the done-when fails exactly as reported. `parse_ns` half **not started**: **387** `Namespace(` sites against **3** slice-scoped `parse_ns` calls |
| D6 — report the measured deltas | **shipped-as-specified** | All seven figures present with commands; `run_script` count re-derives **exactly** (124) |

## Metrics and Anomalies

- Slice: 66,229 lines reported → **67,498** at HEAD.
- The retired percentage line floor: **0.581%** achieved against a **25%** floor — a floor demanding
  ~91% of every comment and docstring in the slice.
- **Anomaly — the cold read caught the floor doing damage.** Four of ten rewritten docstrings were found
  to have lost the *why* a maintainer needs, **every one because the rewrite chased the number**. This is
  the single strongest piece of evidence behind the epic's decision to retire the line floors, and it is
  this plan's most valuable output.

## Routing and Merge Behavior

- Review: not recoverable from the archived artifacts beyond the report's own findings table.
- CI/merge: landed.

## Reconciliation Actions

- [x] row `status` → `landed`
- [x] row `landing` stamped → `landings/PLAN-040.md`
- [x] Open Defect opened — the 92 citations' **remediation** is unowned
- [x] Open Defect opened — `github_ops` ↔ `_github_pr` circular import
- [x] Open Defect opened — `fixtures/ci-wait/README.md` standards violation

## Follow-Ups

- ⛔ **The 92 citations were routed to PLAN-090, and PLAN-090 could not have fixed them.** PLAN-090's D4
  widened the *detection* regexes in `marketplace/bundles/**`; its out-of-scope forbids editing `test/**`.
  So *"the rule can now see it"* landed and *"it is fixed"* did not. **The README's one-line ownership
  assignment does not preserve that distinction** — and this is the same defect that later re-opened
  PLAN-050's and PLAN-060's clean prose counts. Staged as **PLAN-130**.
- ⛔ **`github_ops` ↔ `_github_pr` circular import is confirmed present at HEAD** —
  `github_ops.py:1772` imports from `_github_pr` at the bottom of the file with an `E402` suppression,
  and `_github_pr.py:26` imports `github_ops`. PLAN-090 checked it and **explicitly declined** it as
  outside its deliverable set. **Unowned.** This is a production defect, not test debt. Recorded in the
  epic's `## Open Defects`.
- ⛔ **`test/plan-marshall/phase-6-finalize/fixtures/ci-wait/README.md`** carries a plan slug (twice), a
  lesson id, two TASK ids, a Q-Gate id and an `Authored 2026-05-24` line — a direct `CLAUDE.md`
  § Documentation Standards violation ("No timestamps", "Current state only"). Confirmed verbatim at
  HEAD. **Unowned.** Folded into **PLAN-130**.
- **D3 (124 unpaired `run_script` sites) and D5's `parse_ns` half (387 sites) have no scheduled owner.**
  Recorded in the epic's `## Open Defects`.

## Note on a Correct Self-Correction

D3's report initially claimed *partial* and then corrected itself to *not performed at all*, on the
ground that its gating survey licensed no collapse. That correction is worth preserving: the survey ran,
returned "no collapse warranted", and the run reported the honest answer rather than banking the
parametrization work it did instead as D3 credit.

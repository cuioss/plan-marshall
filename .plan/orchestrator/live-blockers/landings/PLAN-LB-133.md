# Landing Analysis: PLAN-LB-133 — the criteria gate is recorded, the re-freeze decision is reachable, and `superseded_by` must name a deliverable

epic: live-blockers
workstream: WS-03
pr: #1953 (merge commit `4959c5530`, one parent `b09bf3197`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (actual code, artifacts, PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Corroborated against git: the merge is a merge-queue squash with one parent (`b09bf3197`, the PLAN-LB-134 squash, read with git before the leaf prompt named it); fifteen changed paths (nine production, six test), read with `git diff --name-only`. The facts block (`pr=#1953`, `merge_state=merged`, `deliverables 4/4`) agrees with git. `total_tokens=unknown` is an unobserved fact, not a defect. `self-review:budget-exhausted` is a lane state: three rounds and an operator-authorised fix round, with one finding (F3, self-reference) recorded as spec-literal.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — `criteria_gate` is recorded; the dead drop-reason read is removed | shipped-as-specified, one gap | the note is set or popped before `write_status` in the one commit (`_cmd_lifecycle.py:1825-1834`, leaf) and on the production `cmd_archive` completion (`:2059-2070`, leaf); the metadata read is gone from `_criteria_snapshot.py:1803-1833` (re-read at `:1830-1833`: the reason is now derived from `scope_estimate` and the manifest). It is a metadata key, not a status field. Gap: the spec said the note is "shown by the finalize output", and only the transition payload carries it; `cmd_archive` writes metadata only, and no document names `criteria_gate`. |
| D2 — a re-freeze decision has a documented path, and the decision is recorded | shipped-as-specified | `light-lane.md:280-283` branches on `refreeze_requires_decision`; the `refreeze-authorize` question has the declared envelope shape (`:321`); `planning.md:322-332` prints, asks once, authorises then re-dispatches exactly once, stops on refusal or a second prompt; `functional-review.md:93` records the PLAN-LB-70 D3e decision. The verbs and flags the documents name are real (leaf read the three `--help` outputs and `_criteria_snapshot.py:1300-1309, 563-587`). |
| D3 — `superseded_by` must name an existing deliverable | shipped, but the rule is weaker than its purpose | `superseded_by_names_deliverable` (`_criteria_snapshot.py:1836-1867`, re-read): the value must OPEN with `D<n>` or `deliverable <n>` and the number must be one of the outline's own; the validator and `open_criteria` share the rule over their own populations. **Nothing compares the cited number with the deliverable's own** (see Layer 3). |
| D4 — the documents state what the gate does | shipped-as-specified | `triage.md:68` lists five closing states and matches `open_criteria` (leaf); the `review_support` row lists all six verbs and the three private modules (leaf). The D4 doc test is weak: two of its assertions were already true before the change (`triage.md:53-54`). |

**Surface drift.** The report says it touched two files outside the Expected Surface (`review-rubric.md`, `planning.md`) and two test files, each forced by a deliverable. The re-read path list shows more: `test_lb74_criterion_matching_d2.py` (modified), `test_criteria_gate_documentation_d4.py`, `test_functional_review_decision_records.py` and `test_superseded_by_names_deliverable_d3.py` (all new) are outside the spec's list beyond the one new test its last bullet licenses. Four Expected Surface tests were not touched (`test_criteria_integrity_d1.py`, `test_criteria_integrity_d2.py`, `test_review_support.py`, `test_lb77_authorize_guard_d2.py`) and the report does not say so. "Skills: none named" is consistent with the diff.

## Three-Layer Analysis

One read-only leaf (`execution-context-level-3`) read the landing with the lane's seven claims passed one by one; the orchestrator re-read the points marked re-read. **By reading, no build, no test run, no write.**

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is the depth the dispatch rule exists for, and the three landings drained together must not share a context.
- **Verdict:** no blocker. Layer 3: one major (self-supersede), minors and watches.
- **Leaf process note:** the leaf used read-only `git grep` three times against the instruction and one `python3 -I -c` that ran a copy of the shipped regex; it disclosed both. The facts that rest on `git grep` alone are the line numbers in `light-lane.md` (282, 321), `planning.md` (233, 323, 327) and `triage.md` (53, 54, 68).

Re-read: `_criteria_snapshot.py:1830-1871` and the diff of `test_lb74_criterion_matching_d2.py`; a `git diff -G` for the control test the lane names. **Not re-read** (unverified leads): `_cmd_lifecycle.py:1825-2070`, `_review_support_validate.py:444-450`, the three `--help` outputs, `light-lane.md`, `planning.md`, `triage.md`, the `review_support` row, the test bodies, every job log and test count, the review histories, and the PLAN-LB-70 source of D3e.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | The spec's D1 says the note is shown by the finalize output; only the transition payload carries it. | checked (leaf) | refutes (partly) | `_cmd_lifecycle.py:1849-1850` against `:2059-2070` |
| L1-2 | D3 asks that `superseded_by` name an existing deliverable; the rule shipped accepts the deliverable's OWN number and a cycle. | checked (re-read) | refutes the purpose | `_criteria_snapshot.py:1854-1867` |

**Layer 1 verdict:** findings — 2 (1 major, 1 minor)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `_cmd_lifecycle.py:1825-1834, 2059-2070` | real `cmd_transition` and `cmd_archive`, stubs only the findings assertion and logging (leaf) | none | checked (leaf) |
| D2 | `light-lane.md`, `planning.md` | doc substring tests; they do not pin the question id or the "exactly once" and "stop" rules (leaf) | none | checked |
| D3 | `_criteria_snapshot.py:1836-1867`, `_review_support_validate.py:444-450` | real `write_snapshot`, `run_author_verdict`, `run_validate`, `open_criteria`; no case for self-reference, cycles or a capital-D "Deliverable 2" (leaf) | one control fixture edited to a self-citation (below) | checked |
| D4 | `triage.md:68` | weak: two assertions were already true (leaf) | none | checked |

- **L2-1 (minor):** the report's surface-drift disclosure undercounts (above).
- **L2-2 (minor, re-read):** the report calls the D3 "holds" control unchanged. The test it names, `test_superseded_deliverable_criteria_do_not_block`, is in no changed file (a `git diff -G` finds no mention), so that statement is true. A different test, `test_a_superseded_deliverables_rows_are_not_reported_unmatched` in `test_lb74_criterion_matching_d2.py`, had its `superseded_by` rewritten from free text to `'D1'` on deliverable 1, a self-citation; the report does not mention that edit, and the fixture now rests on self-reference being accepted. (The leaf named the wrong test as the edited one; the edit itself is real.)

**Layer 2 verdict:** findings — 2 (minor)

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `_criteria_snapshot.py:1854-1867`; `_review_support_validate.py:444-450` (leaf) | deliverable 1 `{verdict: superseded, superseded_by: "D1"}`, or D1 superseded by D2 while D2 is superseded by D1 | the validator passes, `author-verdict` seals, `open_criteria` returns `open_count: 0` and the completion gate passes, with no evidence. The tree checks that guard `met` do not apply. The new rule forces a reviewer retiring a deliverable by operator decision, with no successor, to name some deliverable, so naming itself is the easy workaround. Not a regression (the base closed on any free text), but the D3 hardening is bypassable by one token | **major** |
| L3-2 | `_criteria_snapshot.py` `_DELIVERABLE_REFERENCE` (leaf, run on a copy) | `Deliverable 2` (capital D), `Deliverable D2`, backticked `` `D2` ``, `**D2**`, `(D2)`, `D#2` | rejected as "names no deliverable of the outline"; recoverable through the validator, but `author-verdict` without `validate` leaves the criteria open as `ungraded` with no hint of the cause, and the message misdescribes it | minor |
| L3-3 | `_criteria_snapshot.py:1847-1852` | a citation naming a deliverable added to the outline after the freeze (or removed from it) | the validator and `open_criteria` disagree by design (different populations); one closes, the other errors | watch |
| L3-4 | `planning.md:322-332` | the re-dispatch's return | the branch does not say to apply the `status: success` handling to it, so a reader could stop after the re-dispatch; it also re-runs the whole light lane, including the domain-narrow pass (idempotence not verified) | minor / watch |
| L3-5 | status record | a plan completed with a dropped review then rolled back | the `criteria_gate` note survives until the next completion; nothing reads the key and the gate recomputes | watch |

**Layer 3 verdict:** findings — 1 (major), 2 (minor), 3 (watch)

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| spec Expected Surface | touched paths within the surface | deviates | four test paths and two documents outside it, partly explained (above) |
| spec standing | a fixture answer is one the real verb can give | conforms | D1 and D3 drive the real functions (leaf) |
| CLAUDE.md § Documentation Standards | current state only | not shown | the documents were not read line by line |
| lane rules | files read with the file tools | the lane admits `ls`, `grep` and `wc -l` through Bash (report § 7) | not checkable here |

## Metrics and Anomalies

- Tokens: `unknown`; out of scope. `landing-check` is run per message in the next step of this pass and recorded in the decision log.
- Anomalies: CodeRabbit refused on quota seven times across nine triggers before the ninth secured a review of the merge head; the operator chose to keep the 90-minute cadence. This is the cost PLAN-LB-142 removes, and it is the strongest single piece of evidence for it. One environment-dependent collection error in a first full `module-tests` run (xdist racing a target-tree generator), not reproduced.

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited) reviewed `80d1a0b86` and the merge head `96de7f247`; three body findings, one fixed (the matcher accepted a token inside prose), two answered with reasons (self-reference as the operator's recorded decision; a nitpick whose variant re-runs the same path, which the leaf agrees with). Sourcery (optional) refused on quota. Review numbers re-read with `runbook_lane review-gate --pr-number 1953`: `unresolved_review_threads` 0 (agrees) and `review_body_findings_total` 3 (agrees: inline-1, inline-2, nitpick-1); `review_body_findings_handled` is **not re-verified** (no progress file was passed, so the verb reports 0).
- CI/merge: merge queue, squash with one parent (git); CI claims not re-read.
- Sonar: `n/a`.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-133 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-133 --field pr --value 1953`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-133 --field landing --value landings/PLAN-LB-133.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-133 --field plan_marshall_plan_id --value rb-lb-133-criteria-gate-reach`
- [x] epic.md narrative reconciled against the queue rows
- [x] defect/watch opened or retired
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

(Each box is ticked only after the call it names has returned.)

## Follow-Ups

- No blocker. **One major, reported to the operator and NOT staged: the self-supersede and cyclic supersede bypass** (Open Defects). The fix is small (compare the cited number with the deliverable's own, and reject a cycle) and sits in the same functions PLAN-LB-133 changed.
- **Watch:** L3-2 to L3-5 and the surface-drift undercount.
- **Sequencing:** PLAN-LB-139 (`functional-review.md`, shared one file with this plan) is now admissible.

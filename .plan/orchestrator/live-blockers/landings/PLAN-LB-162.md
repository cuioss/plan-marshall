# Landing Analysis: PLAN-LB-162 — The review gate never stops on a section name it has not seen, reads the CAUTION-shape block, and carries an operator selection to later heads

epic: live-blockers
workstream: WS-05
pr: #2019 (https://github.com/cuioss/plan-marshall/pull/2019)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth — a landing message is a lead, never a fact. Source message: `rb-lb-162-review-gate-unknown-sections-caution-block-later-heads-001.md` (`kind: landing`, drained from the inbox).

## Deliverable Fidelity vs Spec

PR #2019 `merged` through the CI abstraction; merge commit `4c9449a7361f4e08d0b3e1ec9a68bcd503ffabfc` (squash, first parent `60e6a5c46`), on `origin/main`, read with git. The diff is four files, 1212 insertions and 93 deletions: `SKILL.md`, `runbook_lane.py`, `github_re_review.py` and `test_runbook_lane_review_gate.py`.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — an unrecognised counted title mints `unclassified` findings; `minor comments` is its own kind; allow-list unchanged | shipped-as-specified | the leaf reads `unclassified-N` minted per reviewer through the same ledger, `minor` in the findings table, the eight-title allow-list unchanged and an uncounted title still ignored; the tests fail at base (`undecidable_read`). Not re-read line by line. |
| D2 — the CAUTION-shape block is read | shipped-modified | re-read: a bold heading is read only when it OWNS a block (`runbook_lane.py:2776-2779`, `bold_headings = [… if owned_blocks.get(candidate[0])]`), which the code comment at `:2750-2754` states as the intent (a heading mentioned in prose must not mint a finding). The captured #1983 and #1984 shapes read as the spec states (leaf reading of the tests). The reading has fail-open paths the spec did not exclude: see L3-1 to L3-4. |
| D3 — the reach of an operator selection is stated in `SKILL.md` section 7 | shipped-as-specified | the merged text states the rule from `git -C {worktree} diff --name-only --no-renames {selected_head} {merge_head}` and adds no lane-side check, as the spec allows (leaf reading); the PR body's three-dot form is stale against it. |
| D4 — the PLAN-LB-152 minors | shipped-as-specified (a, b, c); dropped with a recorded reason (d) | (a) the `github_re_review.py` header now says "every refusal the refusal test reaches"; (b) a read with no `complete` key has its own detail; (c) the reason pin covers every verdict paragraph. The (d) reason lives in the PR body (re-read through the CI abstraction: the #1992 thread has `reviewThreads.comments: 0`). |
| D5 — tests pin D1 to D4 | shipped-modified | all new fixtures are inline in `test_runbook_lane_review_gate.py`; `_github_pr_fixtures.py` is untouched, and the PR body says why (the runbook-lane test tree does not have the other directory on `sys.path`). |

**Surface delta** (declared 5, realized 4): declared and touched: `runbook_lane.py`, `SKILL.md`, `github_re_review.py`, `test_runbook_lane_review_gate.py`. Declared and untouched: `test/plan-marshall/workflow-integration-github/_github_pr_fixtures.py`. Realized and undeclared: none (diff stat, re-read). The spec is shipped, so no correction is owed to it.

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, resolved from `orchestrator.analyze`). The orchestrator re-read the points marked "re-read" at their lines in the merge commit; every other point is the leaf's reading and is an unverified lead. The reading is by reading, no build, no test run, no write.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is the depth the dispatch rule exists for, and this landing's read must not share context with the other two landings of the drain. The leaf also reported two rule slips of its own (a `git grep`, and `--output` passed to `git show`); both are read-class, wrote nothing in the repository, and are recorded here.
- **Verdict:** layer 1 findings (one minor); layer 2 findings (minor); **layer 3 findings — four major**; not shown by reading on layers 2 and 3.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | D3 is internally inconsistent: the reach paragraph says a selection such as "merge without reviewer X" covers later no-new-logic heads, and the residual paragraph says a head whose `review-gate` read is not clean "inherits nothing — ask". For a selection over a review-gate gap every later head stays not clean, so the rule is empty for its own example; the same paragraph concedes `.md` is product logic here yet classifies it as no new logic | checked (leaf reading, not re-read) | refutes | `SKILL.md:975-991` of the merge |
| L1-2 | The spec's OBSERVED labels and the premise that the CAUTION block is reachable hold | checked (leaf reading) | confirms | `runbook_lane.py:2131` |
| L1-3 | Whether the two restated rulings match the 2026-10-23 and 2026-10-25 ledger entries | not_shown_by_reading | none | needs the ledger, which the leaf may not open |

**Layer 1 verdict:** findings — 1 (L1-1, minor); not shown by reading — 1

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `runbook_lane.py:2131` and `_body_findings` | the `unclassified` and `minor` tests fail at base (leaf reading; the landing gives the logs) | none | checked |
| D2 | `runbook_lane.py:2760-2807` (re-read) | `test_the_captured_1983_…`, `test_the_captured_1984_…`; the leaf notes the "captured" #1983 fixture omits the nested suggested-fix `<details>`, the part most likely to carry stray `**` and backticks, so real-body behaviour stays unproven | none | checked |
| D3 | `SKILL.md` section 7 | the text-pin test | a new "Enqueue and settle" head re-read paragraph that no deliverable names (leaf reading; inside the allowed surface) | checked |
| D4 | the three corrections | tests added for (a), (b), (c) | the verdict list in `SKILL.md` names the new more-than-enumerable stop but not the new "block … is never closed" `undecidable_read` cause (leaf reading, minor) | checked |
| D5 | the test module | — | the landing's touched-surface list is borne out by the diff stat (re-read); the narrative's "five rounds rewrote ownership" and "written against the unfixed tree first" are process claims a reading cannot settle | not_shown_by_reading |

**Layer 2 verdict:** findings — 2 (minor); not shown by reading — 1

### Layer 3 — Correct

The landing itself reports `self-review: budget-exhausted`: the fifth round's fixes have fixtures that fail against the previous code, but no sixth round confirmed them. The four majors below sit on exactly those paths. All four are under-counts, the direction the spec's own Standing Constraint says the gate must never take.

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `runbook_lane.py:2776-2779` (re-read) | a bold heading naming a findings section with a positive count, owning no `<details>` block: `> [!CAUTION] > **⚠️ Outside diff range comments (1)** > <rows as plain markdown>`, or the heading directly followed by a section or a file-list block | `bold_headings` keeps only headings with an owned block, so the declared finding mints nothing and the gate can answer `all_handled`; a test pins this drop (leaf reading of the test at `:1173`). The drop is deliberate (to ignore a heading mentioned in prose, `:2750-2754`), and the only stop is an adjacent unclosed block (`:2770-2772`) | major |
| L3-2 | `runbook_lane.py:2720-2726`, `:2489-2492` (re-read) | `<details><summary>Review (1)</summary><details><summary>Nitpick comments (10)</summary>…</details></details>`: a counted, unrecognised outer title wrapping a recognised section | `containers` assigns every summary to the nearest summary whose `heading_at` is not `None`, and an unrecognised counted title is `unclassified` (D1's rule; `_heading_section` itself was not re-read), so it is a heading; the inner recognised section becomes content and the outer declared 1 wins over the 10 nitpicks. Before this change the same body stopped as `undecidable_read`, so a stop became an under-count. The `_enclosing_sections` docstring (`:2452-2465`) says a wrapper must not drop findings | major |
| L3-3 | `runbook_lane.py:2760-2767`, `_BOLD_SPAN_RE` at `:2225`, `_BACKTICK_SPAN_RE` at `:2240` (re-read) | a stray `**` earlier in the body: `x **kwargs y **⚠️ Outside diff range comments (1)** <details>…` | `\*\*(?P<title>[^*]+?)\*\*` is run over the whole body with `finditer`, so the first match is `**kwargs y **` and the real heading's opening marker is consumed; the heading is never matched. The backtick filter pairs backticks the same way. A `**kwargs` in a Python review is a plausible stray; the #1983 zero-findings failure comes back | major |
| L3-4 | `runbook_lane.py:2421-2442` (re-read) | `<details><summary>Walkthrough</summary><details><summary>Nitpick comments (1)</summary><dd>see <code>a.py </dd></details> **Outside diff range comments (1)** <details><summary>Major · b.py</summary>fix</details></details>` | `_inside_prose` starts the scan at `stack[-1]`, the innermost block still open at the heading (`:2433-2434`), which here is the outer wrapper; the inner block's unclosed `<code>` leaves `depth['code'] == 1` and the heading is read as prose, so the outside-diff finding is lost. The landing says an unclosed `<code>`/`<dd>` ends with its own block; the code bounds it by the wrapper, so the claim holds only at the top level (the pinning test covers only that, leaf reading) | major |
| L3-5 | `runbook_lane.py:2295`, `:2378` (leaf reading) | two sibling blocks under one bold heading, the second never closed | the stop fires only when the heading owns nothing, so the count is 1 instead of 2 with no stop | minor |
| L3-6 | `runbook_lane.py:2848`, `:2902`, `:2577` (leaf reading) | `**Actionable comments posted: 99999999**`, or a count of more than 4300 digits | the enumeration cap covers one section only, the inline status line is uncapped, and `int()` on a huge count raises a `ValueError` nothing catches | minor |
| L3-7 | `runbook_lane.py:2230`, `:2748` (leaf reading) | reading the comments | one says an unclosed region "runs to the end of the body, the fail-safe direction", which for bold headings hides headings; the other says a bold heading "ends the span of the summary section above it", which `_span_end` explicitly does not do | minor |
| L3-8 | `runbook_lane.py:2764` (leaf reading) | a large body | the backtick scan reruns per bold match and `_inside_prose` and `_owned_blocks` rescan per candidate | not_shown_by_reading |

**Layer 3 not shown by reading:** L3-9: how the regexes behave on full real CodeRabbit bodies (pairing parity, nested suggested-fix and AI-prompt blocks) — only a run against captured full bodies shows it. L3-1 to L3-4 are traced by hand from the code and the stated inputs are constructed, so how often a real body takes any of those shapes is not shown.

**Layer 3 verdict:** findings — 7 (4 major, 3 minor); not shown by reading — 2 (L3-8, L3-9)

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| ref-code-quality | complexity thresholds / SRP | deviates | `_body_findings` is about 180 lines with four nested closures and three interleaved heading models (leaf reading; the span at `:2679-2857` re-read in part) |
| python-core | readable data structures over positional tuples | deviates | four-tuples read as `candidate[1]`, `candidate[2]` (`:2771`) (re-read) |
| ref-code-quality | no duplication | deviates | the tag-strip `re.sub(r'<[^>]+>', ' ', …)` repeated in five helpers (leaf reading) |
| CLAUDE.md § Documentation Standards | current state only | deviates | docstrings narrate past behaviour (leaf reading) |
| pytest-testing | fixture provenance labelled | conforms | the hand-built `Minor comments` fixture labels itself (leaf reading) |
| spec Standing Constraints | no file outside the review gate and the runbook lane | conforms | the four-file diff stat (re-read) |

## Metrics and Anomalies

- Tokens: `unknown`; out of scope under the ruling of 2026-10-23, so no defect.
- Duration: not stated. Self-review ran five rounds (the 4th and 5th on the operator's word) and ended `budget-exhausted`; the landing counts 28 findings across them.
- Anomalies: the lane reports two shell file operations refused by the guard (`cp` and `rm` on the base tree) and three read-class shell reads (`wc`, `grep`, `tail`); `.plan/temp/guard.log` was not re-read here. CodeRabbit was refused on quota twice, with 90-minute waits, per the landing.
- Model: `deepseek-v4.1-flash/high`.

## Routing and Merge Behavior

- Review: the landing claims 0 unresolved threads, 19 body findings, 19 handled. `runbook_lane review-gate --pr-number 2019` returns `unresolved_review_threads: 0` and `review_body_findings_total: 19`, both agreeing. `review_body_findings_handled: 19` is **not re-verified**: the progress file carries 14 `finding:` lines (twelve thread lines, one line covering body positions `inline-1` to `inline-12` and one for `inline-13`) and two lane gate lines, `13/13` at `912f8e867` and `19/19` at `d4d725a48`; the six findings beyond the thirteenth are asserted only by the lane's own gate line.
- CI/merge: merged (`4c9449a73`); CodeRabbit's required review is on record, with every finding handled, so no re-trigger was owed for the last two heads (per the landing).
- Sonar: `sonar_open_new_issues: n/a`; Sonar is not enabled for this project.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-162 --status shipped`
- [x] row `pr` stamped — `2019`
- [x] row `landing` stamped — `landings/PLAN-LB-162.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-162-review-gate-unknown-sections-caution-block-later-heads` (from the sender)
- [x] epic.md narrative reconciled: the CAUTION-shape defect and the PLAN-LB-152 minors marked shipped; the selection-reach entries closed by D3; the four majors opened as one Open Defect and reported to the operator
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **L3-1 to L3-4 (major, REPORTED TO THE OPERATOR, NOT STAGED).** Four hand-traced fail-open paths in the review-body parser. Staging a fix plan needs the operator's word. One plan in the `runbook-lane` skill would cover all four, since they share one function, and the standing rule (as few plans as possible, grouped by module) applies.
- **L1-1, L3-5 to L3-8, the SKILL.md verdict-list gap.** Minor; recorded here and not staged.
- **Residue the landing lists** (five sibling test-module docstrings; three documentation enumerations outside the surface that still omit `minor` and `unclassified`; an enforce-in-code candidate for the selection-reach rule; a title for an `unclassified` row): recorded here, not staged, outside the focus rule.

# Landing Analysis: PLAN-LB-168 — The review-body parser never answers fewer findings than the body declares

epic: live-blockers
workstream: WS-05
pr: #2030 (https://github.com/cuioss/plan-marshall/pull/2030)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (the merged code, the PR state through the CI abstraction, the lane's own progress file). The landing message is a lead, not a fact. Merge commit `8939de0565e089bc0db3de3edb4a6c3940de4634` (parent `c35f23c12`, which is PLAN-LB-167's merge), squash, two files, 756+/65-. Landing message: `rb-lb-168-review-body-parser-never-under-counts-001.md` (runbook lane, harness `opencode`, model `deepseek-v4.1-flash/high`, effort `high`). `landing-check`: `complete: false`, `missing_keys` = `total_tokens` only; per the standing ruling of 2026-10-23 that is no defect. `deliverables_done=5` of `deliverables_total=5`.

## Deliverable Fidelity vs Spec

The plan exists for one property, stated in its Standing Constraints: a body that declares N findings yields N findings or a named stop, never fewer. The merged code closes the four spec inputs. It also ships two under-counts the lane names and accepts, and the layer-3 read found a third that D4's rewrite introduced. All three read fewer than declared with no stop, and each could have stopped.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 a counted bold heading that owns no block no longer mints nothing | shipped-modified: the plain-markdown-row, before-a-section and before-a-file-list shapes are counted; a counted heading over a prose row that starts with a letter still mints 0 with no stop (residual 1) | `runbook_lane.py:2944-2964` (re-read); the lane's own named residual |
| D2 a counted unrecognised wrapper no longer swallows a recognised section inside it | shipped-modified: `Review (1)` around `Nitpick comments (10)` now reads 10; `Review (5)` around one `Nitpick comments (1)` reads 1 with no stop (residual 2) | `runbook_lane.py:3279-3314`, `:3430-3461` (re-read) |
| D3 one stray `**` no longer shifts the heading pairing | shipped-as-specified for the spec's two inputs (a stray `**`, a stray backtick); minor pairing gaps remain (L3-5, L3-6) | `_bold_spans` `:2875-2920`, `_quoted_in_a_code_span` `:2923-2936` (leaf reading) |
| D4 an unclosed `<code>` or `<dd>` is bounded by its own block at every depth | shipped-modified: the nested case is fixed, and the rewrite opens a new under-count at the top level (L3-1) | `runbook_lane.py:2824-2860` against the parent's `_inside_prose` (both re-read) |
| D5 tests pin D1 to D4, written against the unfixed tree first, plus the controls and a real-body test where one exists | shipped-modified: eight path tests plus guards; no test pins either named residual or the new top-level path; the real-body clause is not satisfiable, and the lane says so | leaf reading, `test_runbook_lane_review_gate.py:1180-1201`, `:2171-2578`; the lane's progress file |

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`); the orchestrator re-read the load-bearing points below at the merge commit. The working tree of the main checkout holds both files byte-identical to `8939de056` (the leaf's `git diff --stat`). The reading is **by reading, no build, no test run, no write**.

- **Dispatch:** one read-only leaf for this landing — reason: the landing is a 375-line change to a parser that reads third-party review text; testing the spec's one direction against it means tracing adversarial inputs through the merged code, which is the depth the Dispatch Decision Rule exists for, and one landing's read does not share context with another's.
- **Verdict:** layer 1 findings (1 minor); layer 2 findings (1 major, 5 minors); layer 3 findings (3 majors, 7 minors). The three layer-3 majors are each a silent under-count, the direction the plan exists to close.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | The spec's "a mention mints nothing" and "never fewer" overlap only because the parser reads the flattened display form, where a newline is a space; a named stop satisfies both at once, so they do not conflict. The spec's "four nested closures" is five | checked | confirms | `runbook_lane.py:3721-3731`, `:3836` (flattening), `:3900-3902` (the raw snapshot is still in hand); leaf reading |

**Layer 1 verdict:** findings — 1 minor (L1-1)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `runbook_lane.py:2944-2964`, `:3223-3224`, `:3382-3389` | the three D1 path tests; the pinning test `test_a_bold_heading_with_no_block_of_its_own_owns_nothing` keeps the old rule's name and its assertion holds under both rules, so it pins nothing that changed; its input is residual 1 itself | the lane's "rewritten to the new rule, reason stated" is borne out only as a docstring (`:1180-1201`, re-read) | checked (minor, L2-2) |
| D2 | `runbook_lane.py:3307-3314`, `:3430-3461` | the wrapper read-through and the two wrapper stops; no test pins `Review (5)` around one section | the lane's "errs toward fewer … documented as the accepted residual" is a named under-count (re-read at `:3279-3288`) | checked (major, L3-3) |
| D3 | `_bold_spans`, `_quoted_in_a_code_span` | the stray-marker and stray-backtick tests plus guards | none | checked |
| D4 | `runbook_lane.py:2824-2860` | `test_an_unclosed_code_in_a_nested_block_…`; none for the top-level case | the rewrite changed behaviour for a top-level `<code>` (L3-1) | checked (major) |
| D5 | the new tests run `test_runbook_lane_review_gate.py:2171-2578` (leaf) | not tautological: only the data fetch is patched, the flatten and the parser are real (leaf) | no captured FULL CodeRabbit body exists in the checkout; the lane records the conditional clause as "not met as written, by absence" and runs the captured #1983 body unchanged | checked |

Findings: L2-1 (major) **`_body_findings` grew from 179 lines (`c35f23c12`) to 287 (`runbook_lane.py:3238-3524`)** against the spec's Standing Constraint that the fix does not enlarge it and that a fifth interleaved heading model is not welcome; the wrapper model is woven into it at `:3307-3314`, `:3322` and `:3430-3461`, and `declared_headings` (`:3382-3389`) is a further heading source beside the summary headings, the bold headings and the inline supplement (`:3517-3523`); the marker pairing, the quotation test and the mention test are separate helpers (leaf: `_is_punctuation` 5, `_bold_spans` 46, `_quoted_in_a_code_span` 14, `_heading_is_mentioned_in_prose` 21, `_enclosing_block_span` 20, `_inside_non_finding_block` 13, `_inline_status_count` 25 lines, and a rewritten `_inside_prose` of 37). L2-2 (minor) the pinning test (above). L2-3 (minor) no test pins residual 2 or the top-level `<code>` path. L2-4 (minor) `runbook-lane/SKILL.md:192` still says a counted unknown title contributes its count as `unclassified` findings, "never a stop" (re-read), which is now false for a counted wrapper; and `:211-213` lists the `undecidable_read` causes without the wrapper causes (re-read). The spec forbade a `SKILL.md` edit, so the drift is owed to a plan that owns that file. L2-5 (minor) the new docstring at `runbook_lane.py:3290-3292` calls the enumeration cap "the one remaining stop", which is false beside the two wrapper stops. L2-6 (info) the PR body's gate evidence is at `f7af5215b`, before the review-round commits; the lane's progress file records the final-head gates (`module-tests` 436 green and CI `verify / verify` green at `0a19dbbc7`), re-read.

**Layer 2 verdict:** findings — 1 major (L2-1), 5 minors

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `runbook_lane.py:2840`, `:2858-2860` (re-read) against the parent's `_inside_prose` (re-read, `c35f23c12`: `region_start = token.end()` after every closed top-level block) | an unclosed `<code>` (or one written inside backticks) in the top-level text, then a closed block, then a counted bold heading: `Wrap it in <code> tags. <details><summary>🧹 Nitpick comments (1)</summary> a </details> **⚠️ Outside diff range comments (1)** <details><summary>Major · b.py</summary> fix </details>` (leaf's input, hand-traced, not run) | the rewrite makes the top-level prose scope `{}` never pop and every block inherit it, so the heading reads as prose and its finding is dropped: the parent reads 2, the merged code 1, no stop. A NEW silent under-count, opened by D4's own fix; untested | major |
| L3-2 | `runbook_lane.py:2944-2964` (re-read) | `**⚠️ Outside diff range comments (1)**` followed by a prose row that starts with a letter (`Line 12: rename …`, `src/a.py:12 …`) | the heading reads as a mention and mints 0; the gate demands nothing for it and can answer `all_handled`. The lane names this residual. A stop (a named `undecidable_read`) satisfies "a mention mints nothing" and "never fewer" at once, so the spec did not force the choice; the raw text the gate holds (`:3900-3902`) separates a heading on its own line from one inside a sentence | major |
| L3-3 | `runbook_lane.py:3279-3288`, `:3310-3314`, `:3437-3461` (re-read) | `Review (5)` around one `Nitpick comments (1)` section | the wrapper is transparent and its gap empty (`continue`, `:3461`), so the body reads 1 against 5 declared and answers `all_handled` once that one is disposed of. The lane gives its reason: a stop "refused every body this shape appears in"; that holds only for a stop with no condition. A stop only when the wrapper's count exceeds the sum of the enclosed counts keeps `Review (1)` around 10 readable and stops `Review (5)` around 1 | major |
| L3-4 | `runbook_lane.py:2953` | `**Nitpick comments (2)**, which I fixed`; a counted heading in a table cell or a blockquote | a punctuation-led continuation or a markup-led one mints its count, against "a mention mints nothing", in the permitted over-count direction; documented at `:2953-2955` | minor |
| L3-5 | `runbook_lane.py:2908` | a heading glued to a letter on its left while an earlier `**` opener is unpaired, or a closer followed by an emoji | the heading is lost with no stop (contrived) | minor |
| L3-6 | `runbook_lane.py:2933` | a backtick pairing by `finditer` whose mis-paired span holds exactly the heading | the heading is dropped as a quotation (contrived) | minor |
| L3-7 | `runbook_lane.py:2989-3001` (`_inside_non_finding_block`, first `<summary>` anywhere in the innermost block, `:2776`) | a summary-less block holding a counted heading and a nested `Files selected…` block | the heading is silenced | minor |
| L3-8 | `runbook_lane.py:3449-3460` | a counted wrapper around an uncounted group holding a section | a false stop: the group's `<summary>` text stays in the gap | minor |
| L3-9 | `runbook_lane.py:3136`, `:3564` (leaf); no guard at `:3875` | a digit run of more than 4300 characters in a count | `int()` raises `ValueError` on CPython 3.11+, a traceback and not a named stop; existed before | minor |
| L3-10 | `runbook_lane.py:3501`, `:3518` | many headings each declaring just under the cap | the cap (`_MAX_ENUMERATED_FINDINGS = 1000`, `:2667`) is per heading and per supplement, not on the total, and the new blockless headings add another way to declare large counts | minor |

Not shown by reading: the cost of `_inside_prose` and `_quoted_in_a_code_span` per bold span (O(spans × body) plus a sort per span) on a 100 KB body; whether the `int()` path is reachable on the deployed Python. Handled correctly, by reading: `***x***`, the `>` quote prefix, a `**` pair across a line break (the flatten removes it), a status-line count beside inline sections (the max rule at `:3517`), and the captured #1983 and #1984 shapes (the controls test). Existing, not this plan's: a count of 0 reads 0, several numbers in one title never match a label, `__x__` and `*x*` are never markers.

**Layer 3 verdict:** findings — 3 majors (L3-1, L3-2, L3-3), 7 minors (L3-4 to L3-10); 1 not shown by reading

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| spec | never fewer than declared; where a fix cannot decide it stops with a named `undecidable_read` | deviates | `runbook_lane.py:2840`, `:2964`, `:3461` |
| spec | the fix does not enlarge `_body_findings`; no fifth interleaved heading model | deviates | `runbook_lane.py:3238-3524` (179 to 287 lines), `:3307-3461` |
| spec | no `SKILL.md` edit; no file outside the lane script and its review-gate test | conforms | the diff holds exactly the two Expected Surface files |
| spec | the eight-title allow-list, the `unclassified` rule and the `minor` kind unchanged | conforms | leaf reading (no change to the allow-list) |
| spec | the verdict reasons stay a closed list | conforms | the reason values are unchanged; three new `detail` strings (`:3445-3448`, `:3457-3460`, `:3519-3522`) are added, and the documents list none of them (L2-4) |
| ref-code-quality / python-core | no swallowed `except`; a malformed body stops, not a traceback | deviates | `runbook_lane.py:3564`, `:3875` (existing path, kept) |
| CLAUDE.md Commit Trailer | exactly the plan-marshall trailer and nothing else by way of attribution | deviates | the squash message also carries `Co-authored-by: cuioss oliver …`; the leaf finds the same line on #2027 and #2028, so GitHub's squash adds it on every merge, not this plan |

Points re-read by the orchestrator at the merge commit: `runbook_lane.py:2820-2860`, `:2938-2964`, `:3276-3318`, `:3426-3466`; the parent's `_inside_prose` (`c35f23c12:2806-2845`); `test_runbook_lane_review_gate.py:1176-1203`; `runbook-lane/SKILL.md:188-215`; the squash message and the body of PR #2030. Not re-read, recorded as unverified leads: the helper sizes and line counts, the test counts and the claim that each new test would be red at the unfixed tree, the `_bold_spans` pairing details (L3-5, L3-6), `:2989-3001`, `:3136`, `:3564`, `:3875`, `:3501`, `:3518`, the `declared_headings` source at `:3382-3389`, and every `not_shown_by_reading` point.

The leaf's own slips: it was granted neither Grep nor Glob and used `git ls-files`, `git log -S` and `git log -L` (history reads, not `git grep`) and no shell `grep`, `find` or `cat`; it read the workflow document from the worktree and skipped the dispatcher's logging and `resolve-workflow` steps under the read-only instruction; it opened two persisted tool-result files under `~/.claude/projects` (its own command output) and no `.plan/` path.

## Metrics and Anomalies

- Tokens: `unknown`, an unobserved fact, no defect.
- Duration: the squash commit is dated 2026-11-19 20:57:10 +0000; the landing message was filed at 21:20:36Z.
- Anomalies: (1) the lane waited out a CodeRabbit rate limit (a refusal at 17:47, a 90-minute wait without triggering, a re-trigger at 19:48, a review at 20:00) and Sourcery refused on a budget (14 h); neither is a defect. (2) The lane's merge brought `c35f23c12` into its branch by a merge commit (`0a19dbbc7`), not a rebase; the leaf's `git diff c35f23c12 8939de056` holds hunks only at the imports and in the review-gate parser, so no PLAN-LB-167 function was touched. (3) The lane self-reports one shell file operation (`cat` of a background command's output file); no guard refusal was recorded. (4) `harness=opencode`, `model=deepseek-v4.1-flash/high`, as for the other lanes of this pass, recorded as a fact with no conclusion drawn. (5) The merge ran with the lane's `executor-skew: not_applicable` and `spec_source: ledger_worktree`.

## Routing and Merge Behavior

- Review: the landing claims 4 review-body findings, 4 handled, 0 unresolved threads; coderabbit required (`quota_limited`, `review_complete_after_handling`; a review at `f7af5215b` with four findings fixed in `258013c85` and three threads resolved), sourcery optional (refused on a budget). Re-read by `runbook_lane review-gate --pr-number 2030`: `unresolved_review_threads` 0 and `review_body_findings_total` 4 (coderabbit `outside-diff-1`, `inline-1`, `inline-2`, `inline-3`) both agree with the landing. `review_body_findings_handled`: the gate's own read is `0` (`body_findings_undisposed`); the number is re-verified from the lane's progress file, which holds four `finding:` lines naming exactly those four ids, each with the commit `258013c85`, so 4 agrees. No false claim.
- **PR body and squash message are this plan's own.** The body of PR #2030 and the squash message of `8939de056` describe the parser change and match the two files changed. PR #2030 was numbered after PLAN-LB-169's #2029; whether that bears on the PR-body hypothesis recorded for #2028 is not shown, and #2030's own body is correct.
- CI/merge: PR `#2030`, state `merged`, merge commit `8939de056`, base `main`, `review_decision: none`; the lane reports `settle merged` (merge-group run `44613888114` success), cleanup done. Builds reported: `module-tests` and `quality-gate` six times each, one `verify` that hit the daemon's supervisory bound (1705 s) and was replaced by the split form, all `daemon_longpoll`; none re-run here.
- Collision with PLAN-LB-171 (running; same file `runbook_lane.py`): this merge touches only the imports and the review-gate parser, so a conflict with PLAN-LB-171's Sonar hunks could arise only in `main`'s argparse block, which this merge does not touch. No unpredicted collision, so no declared surface needs correcting.
- Sonar: `n/a` and `step.sonar-roundtrip.open_issue_rules` `n/a`, the lane's `sonar: not_configured`; compared as the claim it is.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-168 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-168 --field pr --value 2030`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-168 --field landing --value landings/PLAN-LB-168.md`
- [x] row `plan_marshall_plan_id` stamped — value `rb-lb-168-review-body-parser-never-under-counts`, taken from the sender
- [x] epic.md narrative reconciled: the Open Defect "Residual under-count paths of the PLAN-LB-162 parser" is marked SHIPPED IN PART and stays open for the three silent paths; the minors go to the Watch
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **Three silent under-counts remain in the plan's own subject (L3-1, L3-2, L3-3).** One is new (the top-level `<code>` rewrite), two are accepted by the lane as named residuals. Each could stop with a named `undecidable_read` instead. Reported to the operator at once; a fix plan is staged only on the operator's word. The three share one function family in `runbook_lane.py` and one test module, the surface PLAN-LB-168 already used, so they would not split.
- **The stale documents (L2-4, L2-5)** are owed to whichever plan next edits `runbook-lane/SKILL.md`; PLAN-LB-171 does, and its deliverable 4 can carry the two lines if the operator wants them there.
- The minors (L1-1, L2-2, L2-3, L2-6, L3-4 to L3-10) go to the BACKLOG Watch of `epic.md` under the focus rule.

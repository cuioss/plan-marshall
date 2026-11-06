# Landing Analysis: PLAN-LB-105 — the review gate grades what the branch really did and every criterion the outline wrote

epic: live-blockers
workstream: WS-03
pr: #1913

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-105.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Merge commit `ce29d4b1f314fd00465e758eb48b918507811c8c`, a squash commit with ONE parent, `60aa555e5` (read by the leaf; my prompt named `144ccdbfc` as the parent, which is the lane's base and not the squash parent — an error of mine the leaf corrected), read through the `ci` abstraction as `pr_state: merged`. Landing message `rb-lb-105-review-gate-grading-truth-001.md` (runbook lane; harness opencode, model `deepseek-v4.1-flash/high`). `landing-check` reports `complete: false`, missing `total_tokens` only (the known gap; `unknown` is an unobserved fact and not a zero; out of scope under the focus rule). The diff touches 25 files: 13 under `marketplace/bundles/plan-marshall/skills/` and 12 under `test/plan-marshall/`. The lane reports 3 of 4 deliverables done (D1's literal merge-base Done-when "not met as written") and `self-review: budget-exhausted`.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — a moved, renamed or split test is not a lost assertion; the pre-image is the merge base; every plan is graded | shipped-modified | Renames detected (`_review_support_integrity.py:141-154`), pre-image at the merge base (`:172-185,213-222,376`), identity per test (`:238-299`), `use_worktree: false` graded against the main checkout (`:307-327`). The lane's "not met as written" for the literal fixture is right: the spec's own claim L185 says the changed set is the three-dot diff, so an untouched file is never read (L1-2). The "moved test is not a lost assertion" holds only for whole-file moves and splits (L3-2) and the set-based comparison hides a loss in one shape (L3-1). |
| D2 — a removal decided on is decided once | shipped-modified | `accepted_test_removals`, declared removals parsed (`_plan_parsing.py:811-835`), the close records identities (`_cmd_loop_back.py:425-458`), `validate` raises no row for an accepted removal (`review_support.py:243-274`). Keyed by identity plus count as the spec asked, except a declaration without a count, which accepts any count (L2-1). |
| D3 — a resolved finding observed again has one visible outcome | shipped-as-specified, on a false premise | `add_qgate_finding` re-arms `taken_into_account` on an identical re-file and names `not_reopened` (`_findings_core.py:1607-1660`); Branch B reads `QGATE_PERSIST_OK` (leaf). The spec's premise that `taken_into_account` is only the review's own disposition is false (L1-1), and the re-arm has no rule, source or phase filter (L3-4). |
| D4 — the parser keeps every criterion and reports what it could not read | shipped-as-specified | `parse_success_criteria` (`_criteria_snapshot.py:777-824`), `unparsed_criteria`, `criteria_by_deliverable`, `parser_extended` classification (`:1257-1282`). The migration rule as the spec wrote it cannot tell an old snapshot from an author's append (L1-3); the lane narrowed it with a replay of the retired parser (`:855-879`). |
| not a deliverable | added-unplanned | `landing-check` `surface_delta`: `expansion_detected`, 18 declared, 25 realized, 3 added, 3 missing. Added: `manage-findings/SKILL.md`, `_review_support_validate.py`, `workflow/code-review.md`, all explained by D3 and D4. Declared and untouched: `_references_core.py` (the evidence root was built in `_review_support_integrity.py`), `manage-solution-outline.py` (per-deliverable output built in `_criteria_snapshot.py`), `test_weakened_test_d4.py` (tests went to the new `test_lb105_test_integrity_d1.py`). The message makes no claim about drift. |

## Three-Layer Analysis

The landing was read on three layers — the spec, the deliverable trace, and the merged code — by one read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`), and the orchestrator re-read the points recorded as `re-read` below at their `file:line` in the merged tree. The reading is by reading, no build, no test run, no write. The leaf had no Grep in its tool set and used `architecture search --content`; it used no shell grep. It reports the basis of its read correctly as `git diff 60aa555e5 ce29d4b1f`.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code across 25 files is depth work, and this landing's read must not share context with any other.
- **Verdict:** layer 1 findings (one major, three minor); layer 2 findings (one major, minor and info); layer 3 findings (five major, minor, info), no blocker.
- **Orchestrator re-read:** the rows marked "re-read" were read again at the cited lines. Rows marked "lead" or "not re-read" are unverified leads.

### Layer 1 — Specified

| Finding | Claim | Verdict | Evidence (file:line) |
|---------|-------|---------|----------------------|
| L1-1 (major) | The D3 premise is false at the base. The spec treats `taken_into_account` as the review's own supersession and protects only an operator-`accepted` record. But the triage workflow records an operator "Hold" as `taken_into_account` (`workflow/triage.md:327`, `:391`), and `manage-findings/SKILL.md:262` repeats the premise ("not an operator decision"). D2 "decided once" and D3 agree only for `accepted`. re-read | checked | `plans/PLAN-LB-105-…md:109-122`; `triage.md:327,391`; `manage-findings/SKILL.md:262` |
| L1-2 | The D1 Done-when "origin/main gains an assertion in a file the branch never touches → no row" cannot fail at the base: the spec's own Claim Label says the changed set is the three-dot diff, which never lists an untouched file. The lane is right; the clause is a spec defect of mine. The replacement control is a file the branch also edits. re-read (spec); the test at `test_lb105_test_integrity_d1.py:187` and the replacement at `:417` not re-read | checked | `plans/PLAN-LB-105-…md:70-71,185`; `_review_support_integrity.py:141` |
| L1-3 | D4's migration rule ("a frozen criterion that is a prefix of a newly parsed one is `parser_extended`, not drift") has no discriminator: the snapshot schema is unchanged, so an old-parser snapshot and an author's append have the same shape, against the Standing Constraint "more precise, never more permissive". The spec asks for no discriminator, so a full fix cannot follow from it. re-read | checked | `plans/PLAN-LB-105-…md:144-148,171` |
| L1-4 | The D3 Done-when pins `--reopen` against a `taken_into_account` record to "not reopened", while a plain re-add re-arms that record: the opt-in flag re-arms LESS than leaving it off. The semantics are inverted for that resolution by the spec's own wording. re-read | checked | `plans/PLAN-LB-105-…md:118-122,130`; `_findings_core.py:1615,1630` |

**Layer 1 verdict:** findings — 4 (one major).

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `_review_support_integrity.py:141-154,213-222,238-299,307-327,376` | `test_lb105_test_integrity_d1.py:137,153,168` (leaf: fail at the base) | L2-2 | checked (tests not re-read) |
| D2 | `_cmd_loop_back.py:425-458`, `review_support.py:243-274`, `_plan_parsing.py:811-835` | `test_lb105_accepted_removals_d2.py` (leaf) | L2-1 | checked (tests not re-read) |
| D3 | `_findings_core.py:1607-1660` | `test_lb105_reobservation_d3.py` (leaf) | none | checked (tests not re-read) |
| D4 | `_criteria_snapshot.py:777-824,855-879,1236-1294` | `test_lb105_criteria_parser_d4.py` (leaf) | L2-5 | checked (tests not re-read) |

- **L2-1 (major, re-read):** a declaration without a count accepts the identity for ANY count, and the check runs over every entry of the removed set, drops included, in every file (`review_support.py:258-274`, the code's own docstring says so at `:261-264`). The spec keys the accepted set by identity PLUS count (L84-85); the count is optional at `_plan_parsing.py:821-823`. So a `**Tests to remove:**` bullet naming `test_x` also licenses weakening any test named `test_x` anywhere. The operator-close entries require exact equality (`:272`), so a smaller accepted count does not hide a larger later removal.
- **L2-2 (minor, re-read):** the spec says the evidence root is "recorded at outline" (L61). The implementation decides it at validate time and reports it only as the payload field `evidence_root` (`_review_support_integrity.py:537`).
- **L2-3 (minor, leaf, not re-read):** the existing test `test_qgate_resolve_by_rule.py` and the parametrization in `test_qgate_resolution_survives_reemission.py` were inverted (the lane discloses it); the rename is a test-function rename that this branch's own gate would report as a named-test loss (the lane notes it).
- **L2-4 (minor, re-read):** the lane's "an author's append is a blocking `rewritten`" holds only for a same-line append; a continuation-line or sub-bullet append is `parser_extended`, advisory (`_criteria_snapshot.py:1265-1273`).
- **L2-5 (minor, partly re-read):** the one-parser constraint: `parse_success_criteria` is the live parser, but `_retired_criteria` keeps a replay of the retired parser beside it (`:855-879`); the replay is not faithful (with no bullet yet it skips prose and keeps scanning, where the retired regex matched nothing), so it can admit texts the old parser never froze.
- **L2-6 (info, re-read):** the lane claims that hold: renames are detected (`_review_support_integrity.py:141-154`), the pre-image is the merge base (`:172-185,213-222,376`), a close records an identity only for a finding whose title carries the weakened-test prefix (`_cmd_loop_back.py:425-427`; this is the fix for the CodeRabbit merge-risk note on `a8614295e`), `rejected` and `accepted` records stay put on a re-file (`_findings_core.py:1630-1660`).
- **L2-7 (info):** the answer to the Watch of the `quality-report` drain ("read this landing for the base anchor"): the changed set was already a three-dot diff at the base (spec Claim Label L185); the defect was the pre-image read at the base tip, and it is now read at the merge base. When no merge base can be computed the pre-image falls back to the tip (L3-9), a near-dead path. So a branch that lags a moved `main` no longer reads the base's later assertions as removed.
- Red-at-base runs, the mutation log `python-2026-11-05-112249.log` and every per-head test run are `not_shown_by_reading`.

**Layer 2 verdict:** findings — 7 (one major, rest minor and info).

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 (re-read) | `_review_support_integrity.py:411-430,467-471,490-493` | A deleted test file with a top-level `test_x` (2 assertions), a modified unrelated file that already has `test_x` with 2 or more, and 2 assertions added anywhere in the changed set | The surviving test is counted from the after-counts POOLED over every after-file, before-counts per file, so the same-named test in another file absorbs the loss and the set-total guard is neutralized by the additions: no row. The base reported the deleted file as a full loss, so the gate is more permissive than before. Top-level pytest names and bare JS `it` names collide often. No test covers a cross-file collision. (Effect inferred from the code; not run.) | major |
| L3-2 (re-read) | `_review_support_integrity.py:461-473`; `review_support.py:249`; docs `functional-review.md:301,303`, `review-rubric.md:41` | A test function moved from a surviving file to another file, or a split that keeps the original and extracts tests | `removed = max(file_loss, identity_loss)` reports a modified path whenever its own file total drops: a fourth loss case beside the three the docstring and § 3e name ("exactly three cases"). The row has `removed_tests=[]`, so `review_support.py:249` never accepts it and the close reports it as unaccounted (`_cmd_loop_back.py:451-457`). D1's "a moved test is not a lost assertion" holds only for whole-file moves. The fixture at `test_lb105_test_integrity_d1.py:153` deletes the original, so this shape is untested (leaf). | major |
| L3-3 (code re-read, reach not re-read) | `_review_support_integrity.py:119-130,324-327` | `use_worktree: false`, with the main checkout on `main` or on another session's branch, or dirty | The evidence root is the checkout's working directory with no check that its HEAD is the plan's branch and no dirty-tree guard. On `main` the three-dot diff is empty: success with zero rows, a pass. A dirty checkout feeds unrelated uncommitted text into the after-image. Whether finalize can run with a mismatched HEAD was not read. | major |
| L3-4 (code re-read, reach not re-read) | `_findings_core.py:1615,1641-1642`; `triage.md:327,391` | An identical re-file of a record resolved `taken_into_account` | The re-arm has no rule, source or phase filter, so it applies to every Q-Gate record, including one an operator chose to "Hold" in triage (those paths record `taken_into_account`). The code comment at `:1641-1642` ("an unchanged re-emission never re-arms a gate the reviewer had cleared") now contradicts `:1615`. Whether triage's Hold records live in the Q-Gate store where this path applies was not read; `rejected` and `accepted` stay put. | major |
| L3-5 (leaf; code paths partly re-read) | `review_support.py:249`; `_findings_core.py:1630-1660` | A row with no identity (`removed_tests=[]`: the file-total-only row, the set-total row, a `test_filtered` row) | It can never be accepted. After an operator close its Q-Gate record is `accepted`; the next head's identical re-file returns `kept`, the record is not pending, yet `validate` raises the row again as blocking: the deadlock D3 set out to remove. Whether an operator close without `--accept` is a working exit was not read. | major, not shown by reading |
| L3-6 (re-read) | `_cmd_loop_back.py:441-458,444` | An accepted `weakened_test` finding | The identities come from a FRESH test-integrity run at close time over the working tree, not from the row the operator saw, so a removal made after the validate is accepted unseen; `by_path` keeps the LAST row per path, so a `test_filtered` or set-total row overwrites the row that carries `removed_tests`, which records no identity and raises the row again (fails closed, defeats "decided once"). Whether the close pins HEAD to the validated head was not read. | minor |
| L3-7 (re-read) | `_review_support_integrity.py:114,181,190,372-376` | A git call exceeding 60 s in `merge_base` or `_show` | `subprocess.TimeoutExpired` is raised outside the `try` that covers only `changed_statuses`, so `validate` crashes with a traceback instead of returning `test_integrity_not_run`. | minor |
| L3-8 (re-read) | `_review_support_integrity.py:141-153,188-191` | A path `git diff --name-status` quotes (non-ASCII, `core.quotePath`) | `_show` returns `None` for ANY non-zero exit and reads it as "did not exist", so a deleted test's pre-image is dropped and its loss counted nowhere. The base had the same quoting issue with `--name-only`. (Effect inferred; not run.) | minor |
| L3-9 (re-read) | `_review_support_integrity.py:218-221,376` | No merge base resolvable | Falls back to the base TIP, the tree D1 removes, with no flag in the payload; the docstring presents it as intended. The three-dot diff at `:141` fails first in that case, so the path is near-dead, yet not fail-closed. | minor |
| L3-10 (re-read) | `_review_support_integrity.py:492-504` | A set-total loss | The row is attributed to the file with the most assertions BEFORE the change, carries `removed_tests=[]` (never acceptable) and can share a path with a per-path row, feeding the `by_path` overwrite (L3-6). | minor |
| L3-11 (re-read) | `_review_support_integrity.py:270-282` | A column-0 comment or dedented string inside a class body; two nested classes of the same name | The class scope stack pops on any non-blank line at or below the class indent, so following methods lose their `Class::` prefix (a false "named test disappears"); only the innermost class name is kept, so `A.Inner::m` and `B.Inner::m` collide. | minor |
| L3-12 (re-read) | `_review_support_integrity.py:605-617` | An indented JS `it.skip(` header | The marker goes to the next span whose offset is at or after it; an indented header's span offset is the line start, below the marker, so the marker is attributed to the NEXT test and an added skip on a test whose neighbour is already skipped is missed. Not a regression (the base missed it). The fixture at `:537` uses column 0 only (leaf). | minor |
| L3-13 (re-read) | `_review_support_integrity.py:194-210` | A removal committed (so in the PR) and restored only in the uncommitted working tree | The after-image reads the working tree first, so the removal is graded as not removed; the docstring calls this "the fail-closed direction", true only for further uncommitted removals. Same behaviour as the base. | minor |
| L3-14 (lead; `:802-824` re-read, end regex not read) | `_criteria_snapshot.py:807` | An indented bold-field continuation (`  **Given:** x`) or a `- ` line inside a fenced block | The block ends at the first line matching the bold-field regex (the regex was not read, so whether it matches an indented line is open), silently dropping later criteria, not listing them as `unparsed`, against `:786-789`. | minor |
| L3-15 (re-read) | `_criteria_snapshot.py:868-879` | An empty `retired` list and a prose line before the first bullet | The replay skips the prose and keeps scanning where the old regex matched nothing, so it can yield texts the old parser never froze (widens `parser_extended`). | minor |
| L3-16 (re-read) | `review-rubric.md:41,42`; `functional-review.md:301,303`; `review_support.py:272` | — | The documents say both sources key the accepted set "by identity plus the number of removed assertions" (a declaration's count is optional); a loss is reported "in exactly three cases" (the code has a fourth); a row without identity is "a file with neither a test-function nor a class header" (set-total and file-total rows also have none); § 3e's first sentence says relaxed assertions are covered and a later one says they are not; the `parser_extended` definition omits the retired-parser restriction. | minor |
| L3-17 (re-read) | `review-rubric.md:42`; `_criteria_snapshot.py:791-793`; `_review_support_integrity.py:99-101,160,176-179,422-425`; `_plan_parsing.py:812` | — | Transitional wording and history in current-state text ("now reads … used to truncate", "It replaces a regex", "no longer suppressed", a plan id in a code comment), against the Documentation Standards. `_review_support_validate.py:467,476` carry the same (leaf, not re-read). | minor |
| L3-18 (lead) | `review_support.py:153-159` vs `_review_support_integrity.py:119-130` | — | `main_checkout_root` and the two `_evidence_root` functions are duplicated across two modules (the lane discloses the second). | info |

**Layer 3 not shown by reading:** L3-5 (the deadlock rests on paths not read), L3-3 and L3-4 (the trigger's reach), and every runtime property (the pairing across a real git history, the fresh recompute at close, the timeouts).

**Layer 3 verdict:** findings — 18 (five major, twelve minor, one info), no blocker.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| Spec Standing Constraints | The gate gets more precise, never more permissive | deviates | L3-1 (`:411-430`, re-read), L2-1 (`review_support.py:272`, re-read), L3-4 (`_findings_core.py:1615`, re-read), L2-4 (`_criteria_snapshot.py:1273`, re-read) |
| Spec Standing Constraints | One identity scheme for a test | conforms | `_function_assertion_counts` and its spans are the one source (`:238-299`, re-read); declared identities are free text, never validated against the scheme (leaf, not re-read) |
| Spec Standing Constraints | One success-criteria parser | deviates | `_retired_criteria` keeps a replay of the retired parser beside the live one (`_criteria_snapshot.py:855-879`, re-read) |
| Spec Standing Constraints | No automatic re-freeze of any snapshot | conforms | `criteria_drift` writes nothing (`:1236-1294`, re-read); the authorization gate in front of the snapshot write was not read |
| Spec Standing Constraints | Protected keys | conforms | leaf (`ACCEPTED_TEST_REMOVALS_KEY` in the tuple; test at `test_lb105_accepted_removals_d2.py:393-411`; not re-read) |
| Spec Standing Constraints | Decisions go to scripts, not prose; non-Python fixtures | conforms | leaf (not re-read) |
| CLAUDE.md § Documentation Standards | Current state only, no transitional information | deviates | L3-17 (re-read) |
| CLAUDE.md § Documentation Standards | No duplication, cross-reference | deviates | L3-18 and the rule restated in three homes (leaf, `main_checkout_root` re-read in two places) |
| CLAUDE.md § Documentation Standards | No timestamps or version history | conforms | changed doc lines read by the leaf; not re-read |
| plugin-script-architecture | TOON output / exit 0 with a named error | deviates | L3-7 (re-read) |
| plugin-script-architecture | kebab-case flags, `allow_abbrev=False` | conforms | no new flag (leaf) |

## Metrics and Anomalies

- Tokens: `unknown` (not measured by the harness; recorded as unobserved).
- Duration: not reported.
- Anomalies: the build server was down for the plan worktree at setup and came back during the run; every build was `in_process_fallback` until about 14:13, then `daemon_longpoll` for the last runs (`verify` 1111 s at `292a0d4d6`, 898 s at `3a313068c`), no launch-fault retries (lane message, not corroborated against the daemon journal). Self-review used its three rounds plus one operator-authorized round; no round reported "nothing open", recorded as `budget-exhausted`. Lane rule breaks as the lane discloses them: three shell file reads (`tail -n 25`, `grep -c` twice). Corroboration against the session database was not done.

## Routing and Merge Behavior

- Review (read through the `ci` abstraction): CodeRabbit reviewed `2acd3328e` at 12:29 (eight actionable comments, one nitpick on the strength of the partition test) and `a8614295e` at 13:47 (one actionable comment; its merge-risk note names accepting an unrelated finding, which the lane fixed in `292a0d4d6`, and the guard at `_cmd_loop_back.py:425-427` is that fix). A third CodeRabbit review at 12:57 was not read. All nine review threads are resolved (the CI layer reports nine threads, none unresolved). Later triggers were refused with "Review rate limited" (12:57, 14:33, 14:58) or "Already reviewed" (12:31, 13:48), so the final head `3a313068c` has no bot review. Sourcery refused on the 150,000-character limit.
- Standing review authorization was applied by the lane (a qualifying CodeRabbit review on `a8614295e`, a re-trigger after the last push, refusal recorded); consistent with the PR comments read.
- CI/merge: green on every head per the lane; merged through the merge queue as a squash (`ce29d4b1f`). No collision recorded with a running plan.
- Sonar: `n/a` at both facts; the project has no Sonar, nothing to compare.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-105 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-105 --field pr --value 1913`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-105 --field landing --value landings/PLAN-LB-105.md`
- [x] row `plan_marshall_plan_id` stamped — `lb-105-review-gate-grading-truth` (the sender's `{plan}`)
- [x] epic.md narrative reconciled (Queue annotations entry, Open Defects for the layer-3 majors and the spec premise, Watch for the unread points)
- [x] resume anchor updated; `queue-view.md` regenerated

## Follow-Ups

- **Layer-3 defects reported to the operator in the same turn, nothing staged.** Five majors (L3-1 to L3-5) and the layer-1 and layer-2 majors (L1-1, L2-1) sit on the gate this plan was staged to make truthful; a fix plan only on the operator's word.
- **Spec edit owed (my spec's fault):** L1-1 (the Hold premise), L1-2, L1-3 and L1-4. The shipped spec is not rewritten.
- **Parked PLAN-LB-75** shares `review_support.py` (D1) and `_criteria_snapshot.py` (D4) with this landing: re-ground it against the line moves and against L3-2 and L3-5 before it runs.
- **Not staged, under the focus rule:** the documentation contradictions and transitional wording (L3-16, L3-17) unless folded into a fix plan; the duplication (L3-18).
- **Owed, operator-run:** none for this landing beyond the standing harness sync.

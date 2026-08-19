# Verification — 030-merge-gate-cannot-tell-a-required-check-from-a-decorative-one

**Verified against:** commit `ac06e4f`; adversarially re-reviewed at `9afba956` (34 commits later — `git diff ac06e4f..9afba956` is empty for `SKILL.md` and `_github_pr.py`, so every reference below still resolves)   **Landed as:** PR #1137, squash commit `991f3e5f`   **Verdict:** partially-implemented

## Method

What was actually done, in order:

- Read `plan.md` and `report-01.md` in full.
- The clone arrived shallow (50 commits), so `991f3e5f` was not present. Ran `git fetch --deepen 400`
  (history now 760 commits) and located the landing with `git log --oneline --all --grep '#1137'`.
- Read the landed diff: `git show --stat 991f3e5f` and `git show 991f3e5f -- .claude/skills/cloud-plan-lane/SKILL.md`.
  Saved the landed file body (`git show 991f3e5f:.claude/skills/cloud-plan-lane/SKILL.md`) to scratch for
  point-in-time greps.
- Opened the current tree's `.claude/skills/cloud-plan-lane/SKILL.md` (1597 lines) at every site the plan
  and report name: § Step 4 "Commit and push" (l. 330–360), § Step 5 build gate (l. 507–509), § Step 8
  merge gate conditions 1–4 (l. 1195–1290), § Step 8 "Record nothing" (l. 1373–1377), § Step 9
  contract-check table (l. 1407–1408), and the § Cloud session affordances table (l. 50–80).
- **Tree-wide sweeps** (each re-run at the moment of the claim): `checks are green` / `all checks green`;
  `license` and case-insensitive `cla`; `git add -A`; `--squash`; `outside this plan` / `nowhere else under`;
  `cloud-plan-lane` references across `*.md`/`*.adoc`/`*.py`.
- **Live GitHub re-derivation** via the MCP server, not trusting the report's restatements:
  `pull_request_read get_status` on #1112 (head `25a6c4ba…`, `license/cla` = **pending**) and on #1137;
  `pull_request_read get` on #1117 (head `0abb1953…`, `merged: true`, `merged_at 2026-08-08T16:57:13Z`) and
  on #1137 (`merged: true`, 3 changed files, +324/−5, 5 commits, branch
  `claude/merge-gate-check-distinction-56ktpn`); `get_comments` (4) and `get_review_comments`
  (`totalCount: 0`) on #1137; `get_commits` on #1137 (all five authored `Claude <noreply@anthropic.com>`).
- **Authorship claim executed against git**, not read: `git log origin/claude/harness-rule-gaps-541rjw
  --format='%an <%ae> | %cn <%ce>'` → `Claude <noreply@anthropic.com>` for both cloud commits.
- **Provenance of every post-landing edit inside condition 1** established with `git log -S` so later
  plans' text is not credited or debited to this one (`#1147`, `#1177`, and — added in adversarial review —
  `#1190` / `ea1ac4b7`, which inserted the `mergeable_state`-vs-`mergeStateStatus` blockquote now at
  `SKILL.md:1218-1224`. The `git log -S` enumeration in the first pass was string-scoped and therefore
  incomplete; the complete list is `git log --oneline 991f3e5f..HEAD -- .claude/skills/cloud-plan-lane/SKILL.md`
  narrowed to commits whose hunks fall in 1200–1252).
- Read the adjacent production code the D3 claim bears on:
  `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
  (`cmd_pr_auto_merge` l. 1592–1644, `cmd_pr_merge_queue` l. 1890–1920) and
  `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py` l. 968–980.
- Verified the reviewer-population derivation by opening
  `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{coderabbit,sourcery,pr-agent}.md`
  and reading each `author_login`.
- **No mutation check was performed and none was applicable:** the plan's entire surface is prose in one
  `SKILL.md`. There is no guard, function, or test to break. In its place I performed the plan's own
  verification instrument myself — an isolated read of the shipped condition 1 (l. 1200–1252) answering
  the plan's two questions.
- **No test run:** the landed diff contains no `*.py` and adds no test, so there is nothing to collect.
- **No file was modified.** `git status --porcelain` shows three files carrying `# MUTATION` markers
  (`reconcile_daemon.py`, `_config_core.py`, `_config_defaults.py`) that were **not** made by this
  verification — they appeared mid-session and belong to a concurrent agent sharing this working tree.
  They are untouched and reported, not reverted.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: derive required-context set from the ruleset | required set recorded with its API surface; CLA membership stated as read | Partly | No — reinterpreted | Conclusion sound | No positive set recorded | `report-01.md` § D0. Re-derived: `pull_request_read get_status` #1112 → `license/cla` `state: pending` at head `25a6c4ba…`; `pull_request_read get` #1117 → `merged: true`, head `0abb1953…`. Both match the report exactly. No enumerated required set exists in report or tree. |
| D1 | Step 8 condition 1 asks about required-ness | names the ruleset as source; disclose vs block; names no individual check | Yes | Yes | Yes, with one shipped omission (later fixed) | Yes | `SKILL.md:1200-1252`. `grep -oi "cla[a-z]*"` on the **landed** file → only `claude/CLAUDE/claim/clared/claring/clarification`; `grep -i license` on the landed file → 0 hits (at HEAD it returns `SKILL.md:975` "licenses"/"licenses" — later, unrelated prose, not a check name). Tree-wide `checks are green` → only `SKILL.md:1201` (the negated contrast) and `ci_verify.py:645` (a different lane). |
| D2 | Record CLA root cause as an operator proposal | the proposal is recorded; no authorship change | Yes | Yes | Yes | Yes | `report-01.md` § What have we learned #1 and § D2. Claim executed: `git log origin/claude/harness-rule-gaps-541rjw --format='%an <%ae>'` → `Claude <noreply@anthropic.com>`; `get_commits` on #1137 → all 5 commits same author. Landed diff contains no authorship/CI change. |
| D3 | Correct the documented merge command | the § Step 8 command is the one that works, with a one-line reason | No — dropped | Yes (drop is disclosed) | Drop trigger was not met; premise still unsettled | n/a | `SKILL.md:1290` still `gh pr merge {N} --squash --auto`; `SKILL.md:70` maps the same form to `enable_pr_auto_merge`/`SQUASH`. `report-01.md` § D3 records the drop and § Residue carries it forward. |
| D4 | Warn about lockfile churn; stage explicitly | hazard and staging rule stated where a run commits | Yes | Yes | Yes | Yes | `SKILL.md:339-345` (§ Step 4 "Commit and push") and `SKILL.md:507-509` (§ Step 5). `grep -n "git add" SKILL.md` → only those two prohibitions; no `git add -A` command example survives to contradict the rule. |
| D5 | Reword the Step-9 Bridge row | wording matches intent; no longer contradicts a legitimate deliverable | Yes | Yes | Yes | Yes | `SKILL.md:1408` (Bridge row) and `SKILL.md:1373-1377` (§ Step 8 "Record nothing", the declared consistency alignment). `grep -rn "nowhere else under"` across `*.md` → the old over-broad form survives in no contract text. |

### Why the verdict is `partially-implemented`

**Corrected in adversarial review** (it read `implemented-with-gaps` in the first pass). The rows do not
support that verdict: D0's `Implemented?` is **Partly** with its literal Done-when unmet, and D3's is
**No — dropped** on a trigger that was never met (below). Four of six deliverables landed clean; one gate
deliverable landed partially and one did not land at all. A plan with an unimplemented deliverable is
`partially-implemented`. Nothing else in the assessment changes — the deviations are disclosed in
`report-01.md`, not concealed, and D1's substance shipped correct.

### D0 — the STOP condition was reinterpreted, not obeyed

The plan's D0 carries an explicit ⛔ STOP: *"If the required set cannot be derived programmatically,
**halt and report that**."* The run established that the ruleset-config surface is unreachable (MCP exposes
no branch-protection tool; direct `api.github.com` returns `403`), and then **did not halt** — it substituted
a different derivation (merge-queue admission implies required contexts satisfied) that yields only a
*negative* fact about one context. That inference is sound and I re-derived both of its inputs live
(#1112 `license/cla` pending at `25a6c4ba…`; #1117 `merged: true` at `0abb1953…`), and the STOP's stated
*purpose* — do not write a hand-maintained list of required checks into the contract — was honoured: no such
list exists anywhere in `SKILL.md`. But D0's literal Done-when, *"the required set is recorded in the report
with the API surface it came from"*, is **not met**: neither `report-01.md` nor the tree names a single
required context as derived. The report discloses this as finding #2 and escalates it (§ What have we
learned #2), so it is a disclosed deviation rather than a concealed one — and a later plan (#1147,
`SKILL.md:56`) wrote the unreachability into the contract, which closes the forward-looking half.

### D1 — shipped correct, but its state enumeration was incomplete at landing

The rule as landed (`git show 991f3e5f`) defined exactly two `mergeStateStatus` values: `BLOCKED` (a required
context unsatisfied — failing, pending, or absent) and `UNSTABLE` (required all passed, only non-required
outstanding). It did **not** define `clean` — the ordinary fully-green state. A reader applying the shipped
text literally had no enumerated state in which arming was authorised on a fully-green PR. `git log -S 'both
report the required'` shows this was closed later by **#1177** (`chore(cloud-plan-lane): document the clean
mergeStateStatus in the merge gate`), which added the `clean` clause now at `SKILL.md:1229-1232`. Per the
supersession rule this is **not an open gap** — but it is a real defect this plan shipped, and it is recorded
here because the plan's own cold-read verification did not catch it: the cold read asked only about a pending
non-required check and an absent required context, never about the ordinary green case.

Everything the plan required of D1 is present and correct at HEAD. Read in isolation, `SKILL.md:1237-1243`
answers the plan's two questions correctly: an absent required context is "**not** satisfied … Absence never
reads as success"; a non-required context pending/failed/absent "**does not block** … but **is disclosed**".
Required-ness is attributed to the ruleset (`SKILL.md:1203-1208`) and no individual check is named anywhere
in the file.

### D3 — dropped on a rule the run could not actually apply, and the tree now contradicts the drop's premise

D3's ⛔ rule was: run **the documented form** against this PR; *"if it succeeds here, this deliverable is
refuted and drops."* The documented form is a `gh` command and the cloud session has no `gh` CLI, so the
documented form was never run. The run tested a **different** surface (MCP `enable_pr_auto_merge` with
`mergeMethod: SQUASH`), found it armed without error, and dropped D3. That is one defensible reading of the
rule, honestly caveated in the report (the MCP result reported an empty `method`, so it is unknown whether
`SQUASH` was accepted or normalised) — but the drop trigger the plan wrote was *success of the documented
form*, and inability-to-test is not that.

The tree supplies evidence the run lacked, and — **corrected in adversarial review** — it points **both
ways**, not one way.

`_github_pr.py:1911` (`cmd_pr_merge_queue`) does build `['pr', 'merge', identifier, '--auto']` with **no**
strategy flag, under a comment stating "Neither `--strategy` nor `--delete-branch` is forwarded: the merge
queue's own branch-protection configuration dictates the merge method." That much stands, and note the same
comment attributes outright *rejection* only to `--delete-branch`.

⛔ **The first pass's reading of the sibling path was wrong.** It described `_github_pr.py:1631` as "the
non-queue auto-merge path" and claimed "the two are separated by an explicit queue-configured discriminator".
Executed, not read: `cmd_pr_auto_merge` (`_github_pr.py:1592`) is **one** verb that runs on both kinds of
base. It calls `_resolve_base_queue_state` *before* the `gh` call, forwards `f'--{args.strategy}'`
unconditionally at line 1631, and consults the discriminator only *after* a zero exit, to label the outcome
`enqueued` vs `enabled`. Driven with the probe forced to `MERGE_QUEUE_ELIGIBLE_CONFIGURED` and
`strategy='squash'`, it emits `['pr', 'merge', '42', '--auto', '--squash']` and returns
`{'status': 'success', ..., 'disposition': 'enqueued'}` —
`test/plan-marshall/workflow-integration-github/test_github_ops_pr_merge.py:1349` asserts exactly that
configuration, with `strategy='squash'` as the namespace default (l. 1320), and
`tools-integration-ci/standards/leaf-command-reference.md:39` documents `--strategy {merge|squash|rebase}`
for the verb with no queue caveat.

So this repository's own `ci pr auto-merge` verb issues **the documented form** against a queue-gated `main`
and treats a non-zero exit as an error — which would be broken if `gh` rejected the flag there. The tree
therefore does not corroborate D3's premise; it contradicts it as often as it supports it. What remains true
is narrower and is what G1 now carries: `SKILL.md:1290` and `SKILL.md:70` document a form whose behaviour on
this base **nobody has observed**, and this plan's residue has been open on that question since #1137.

## Report accuracy

Every figure and identifier in `report-01.md` was re-derived. **No contradictions found**, having checked:

- **PR and branch identity** — `pull_request_read get` #1137: branch `claude/merge-gate-check-distinction-56ktpn`,
  `merged: true`, `merged_by: cuioss-oliver`. Matches the report's header exactly.
- **Diff shape** — report: "touches only `SKILL.md`, this plan's directory, and the plan-file rename — no
  `*.py`." `git show --stat 991f3e5f`: exactly 3 paths (`SKILL.md`, the `030-….md → 030-…/plan.md` rename,
  `report-01.md`), 324 insertions / 5 deletions. The API agrees (`changed_files: 3`, `additions: 324`,
  `deletions: 5`). Confirmed.
- **Commit SHAs** — `f834942` and `2ff57ec` both exist on the PR (`get_commits`), with the commit messages
  the report attributes to them. `commits: 5`, matching the report's account (directory establishment,
  two source-touching commits, two report commits).
- **D0's two source PRs** — #1112 head `25a6c4ba…` with `license/cla` `state: pending`, description
  "Contributor License Agreement is not signed yet."; #1117 head `0abb1953…`, `merged: true`,
  `merged_at 2026-08-08T16:57:13Z`. Both exactly as reported, including the SHA prefixes.
- **The "no longer recoverable" caveat** — the report says `mergeable_state` now reads `unknown` on both.
  Confirmed: #1117 returns `"mergeable_state":"unknown"`.
- **Comment counts** — report: "0 inline review threads; 4 conversation comments (2× CLA request, CodeRabbit
  skip-by-label, cuioss-review-bot 'no major issues')." `get_review_comments` → `totalCount: 0`.
  `get_comments` → exactly 4, and their authors/bodies are exactly the four named. Confirmed.
- **Reviewer population M = 3** — derived as the report says it was, from the `author_login` in each registry
  doc: `coderabbit.md:36` → `coderabbitai`, `sourcery.md:29` → `sourcery-ai`, `pr-agent.md:58` →
  `cuioss-review-bot`. Three files, three logins. Coverage 1-of-3 is consistent with the four comment bodies.
- **The authorship claim (D2)** — executed, not read: every one of #1137's five commits, and both cloud
  commits on an unrelated `claude/*` branch, carry author `Claude <noreply@anthropic.com>`.
- **The grep claim** — report: greps of the whole `SKILL.md` for `cla`/`license` "return only CLAUDE.md /
  Claude / .claude/ / claim / declared". Re-run against the landed file: the match set is
  `claude, CLAUDE, Claude, claimed, claim, clared, claring, clarification` and `license` returns nothing.
  The report's enumeration omits `clarification`; the substantive claim — no `license/cla` in the rule — holds.
- **Mitigation block** — the report's later-added note claims #2, #3 and #4 are closed by plan `450`/#1147
  and #1143 while #1 stays open. Verified in the tree: `SKILL.md:56` (ruleset-config unreachable row),
  `SKILL.md:70` (`gh`↔MCP mapping), `SKILL.md:1293` (one-way-door rule, landed as `838858c1` / #1143).
  Nothing in the tree fixes the authorship issue, so #1 is correctly still open.

Two figures could not be re-derived and are listed under "What could NOT be verified" rather than counted
as accurate.

## Out-of-scope compliance

Clean. The landed diff is three paths and nothing else — one `SKILL.md`, the plan-file rename into its own
directory, and the run report. No undeclared collateral change.

Each declared boundary held:

- **"Do not write `license/cla` is not a hard gate into the contract"** — `grep -i license` over the
  **landed** `SKILL.md` returns zero hits. **Corrected in adversarial review:** at HEAD it returns one line,
  `SKILL.md:975` ("What either exit licenses is stopping *this loop*; it licenses no claim…"), which is later
  prose from the Step 6 loop and not a check name. `grep -oi "cla[a-z]*"` at HEAD returns no `cla` token that
  is not part of `Claude`/`claim`/`declar*`/`clarification`/`class*`/`clause`/`clamps`. Broadened at HEAD to
  the actual check names in play (`verify / conclusion`, `dependency-review`, `codecov`, `sonar`,
  `coderabbit`, `sourcery`, `cuioss-review-bot`): the merge-gate **rule** (l. 1200–1252) names none of them;
  the hits are at l. 150/386/1185/1354 (§ Step 2 and CI-cancellation prose) and l. 1270–1271 (condition 4's
  worked example of a coverage disclosure). No individual check is named in any rule.
- **"Do not change commit authorship or sign a CLA"** — the diff touches no commit-template, workflow, or CI
  file; all five commits still author as `Claude <noreply@anthropic.com>`.
- **The `skip-bot-review` draft-open race** — untouched; nothing in the diff concerns labels or PR-creation
  ordering.
- **`doc/plans/cloud-bridge.md`** — not in the diff; `git show --stat` lists it nowhere.

The one edit beyond a deliverable's literal scope — the § Step 8 "Record nothing" alignment in `2ff57ec` —
was **declared** in the report (§ D5 and findings row 1) with its motivation (a verification-sub-agent finding
that the same over-broad phrasing left the contract self-contradictory) and is genuinely within D5's stated
Done-when. It is disclosed collateral, not silent collateral.

## Residue carried forward

| Residue as declared in report-01.md | Status in today's tree |
|---|---|
| **D3 doc edit deferred** — needs a `gh`-capable session or operator confirmation before the documented command changes | **Still open.** `SKILL.md:1290` is unchanged (`gh pr merge {N} --squash --auto`), and `SKILL.md:70` restates the same form in the MCP mapping. `git log -S 'squash --auto'` shows the only later touch was #1147 adding the mapping row — the command itself has never been revisited. New tree evidence bearing on it is recorded above and filed as G1. |
| **Operator ratification invited for What-have-we-learned #1–#3** | **#2 and #3 closed** by #1147 — `SKILL.md:56` records the ruleset-config API as unreachable and directs the reader to `mergeStateStatus`; `SKILL.md:66-76` supplies the `gh`↔MCP mapping. **#1 (cloud-run authorship / permanent `license/cla` red) still open** — nothing in the tree changes commit authorship, and every cloud branch commit still authors as `Claude <noreply@anthropic.com>`. |
| **What-have-we-learned #4** (arming auto-merge queues immediately; only closing dequeues) | **Closed** by `838858c1` / #1143 — `SKILL.md:1293-1308` carries the one-way-door rule and the close/reopen recovery. |

## What could NOT be verified

- **The build-gate figures.** "31 plugin-doctor rules at 0 findings", "mypy no issues found in 382 source
  files", "ruff All checks passed!" — these are properties of the tree at `2ff57ec`, and the tree has moved
  on by ~150 commits. Re-running `./pw quality-gate` at HEAD would measure a different tree and prove nothing
  about the claim. Not verified; not counted as accurate either.
- **Whether `gh pr merge {N} --squash --auto` is actually rejected on this merge-queue repository.** No `gh`
  CLI is present in this session either (`which gh` → exit 1), so the same instrument the run lacked is still
  missing. **Corrected in adversarial review:** the production-code evidence in `_github_pr.py` is not
  one-sided. `cmd_pr_merge_queue` omits the strategy flag on the queue path, but `cmd_pr_auto_merge` forwards
  it on that same path — executed, it emits `['pr', 'merge', '42', '--auto', '--squash']` and reports
  `disposition: enqueued`. Neither settles whether `gh` errors. This is the single largest open question in
  the file (G1).
- **The independent cold read the report describes.** A sub-agent's transcript is not in the tree. I
  performed an equivalent isolated read myself and it returned the plan's two required answers, but I cannot
  confirm the run's own cold read happened as described.
- **The point-in-time `mergeable_state: unstable` on #1137 at head `2ff57ec`.** Both that head and the PR
  are now historical; the API returns `unknown` for a merged PR. The report itself flags this as
  point-in-time, so it is a limitation of the surface, not a discrepancy.
- **Wall-clock and token figures.** The report states tokens are unavailable and derives wall-clock from
  git/PR timestamps; the timestamps I can check (PR created 14:29:46Z, merged 14:59:40Z) agree, but "run
  start ≈ 14:04 UTC" rests on a first branch operation whose branch has since been deleted.

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Working tree at `9afba956` (34 commits past the `ac06e4f` this document was written against;
`git diff --stat ac06e4f..HEAD -- .claude/skills/cloud-plan-lane/SKILL.md _github_pr.py` is **empty**, so every
line reference in this document still resolves). Re-verified:

- **Every line number cited.** `SKILL.md` is 1597 lines. Confirmed exactly: 56 (Ruleset-config row), 70
  (`gh`↔MCP merge row), 150 (`verify / conclusion` named required), 339–345 + 507–509 (D4), 1200–1252
  (condition 1), 1203–1208 (ruleset attribution), 1218–1224 (the MCP-field blockquote), 1229–1232 (`clean`),
  1237–1243 (required/non-required bullets), 1245–1252 (the `BLOCKED` intersection), 1290 (`--squash --auto`),
  1373–1377 (Record nothing), 1407–1408 (Step-9 rows), 1530 (the condition-4 report obligation).
- **The landing.** `git show --stat 991f3e5f` → 3 paths, 324 insertions / 5 deletions — re-derived, matches.
- **The D1-omission and provenance claims.** `git log -S 'both report the required'` → `3a5e2ca0` (#1177);
  `git log -S 'never from whichever pending status is loudest'` → `a3eb36bb` (#1147); `git log -S 'squash --auto'`
  → `47ace158` (#1098) and `a3eb36bb` only. `git show 991f3e5f` confirms the landed text defined only `BLOCKED`
  and `UNSTABLE`. **One provenance miss found:** `ea1ac4b7` (#1190) also edited inside condition 1 — corrected
  in § Method.
- **Live GitHub, re-run not re-read.** `pull_request_read get_status` #1112 → head `25a6c4ba8886…`,
  `license/cla` `pending` ("Contributor License Agreement is not signed yet."). Same on #1117 → head
  `0abb195360148b83…`, `license/cla` `pending`; `get` #1117 → `merged: true`,
  `merged_at 2026-08-08T16:57:13Z`, base `main`, `merged_by: cuioss-oliver`. **Both of D0's inputs are
  therefore re-derived live, not accepted** — each PR landed with `license/cla` still pending on its head, so
  the CLA is not a required context on `main`. `get_comments` #1137 → exactly 4, authors `cla-assistant[bot]`
  ×2, `coderabbitai[bot]` (skip-by-label), `cuioss-review-bot[bot]` ("No major issues detected"). Every
  claim holds verbatim.
- **The reviewer population.** `coderabbit.md:36` → `coderabbitai`, `sourcery.md:29` → `sourcery-ai`,
  `pr-agent.md:58` → `cuioss-review-bot`. Three files, M = 3. Holds.
- **The sweeps, re-run BROADER than the originals.** `license` at HEAD (not only on the landed file);
  `cla[a-z]*` at HEAD; the actual check names in play (`verify / conclusion`, `dependency-review`, `codecov`,
  `sonar`, `coderabbit`, `sourcery`, `cuioss-review-bot`); `checks are green|all checks green|all green|
  everything is green|all checks pass` tree-wide; `green` across all of `SKILL.md` (35 hits, each read);
  `nowhere else under|outside this plan` across `*.md`/`*.adoc`; `required context` across `SKILL.md`.
  Two over-claims found (below); the substantive "no individual check in the rule" claim survives every one.
- **A function was RUN, not read.** `cmd_pr_auto_merge` and `cmd_pr_merge_queue` were driven with `run_gh`
  stubbed and `_resolve_base_queue_state` forced to `MERGE_QUEUE_ELIGIBLE_CONFIGURED`, to see what argv each
  actually emits on a queue-gated base. This refuted the mechanism clause the D3 assessment and G1 rested on.

**Not re-checked**, and why: the build-gate figures (31 rules / 382 files / ruff) — same reason as before, the
tree has moved; the wall-clock and token figures; the run's own cold-read transcript (not in the tree); the
point-in-time `mergeable_state: unstable` on #1137 (the API now returns `unknown` for both merged PRs, as
this document already flags); the D4/D5 sweeps were re-run at HEAD but their *landed-diff* forms were not
re-greped separately. No mutation was applied — the surface is
prose, there is no guard to break; `git status --porcelain` showed only two other plans' doc files dirty
(another agent's), and no source file was touched by this review.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| Verdict | `implemented-with-gaps` | **Corrected → `partially-implemented`** | The document's own rows read D0 `Partly` (literal Done-when unmet) and D3 `No — dropped`. A plan with an unimplemented deliverable is partially-implemented. New § "Why the verdict is `partially-implemented`". |
| G1 | "This repository's own production enqueue path does the opposite … the sibling non-queue path at `_github_pr.py:1631` does forward `f'--{args.strategy}'`, and the two are selected by an explicit queue-configured discriminator" | **Rationale refuted; gap rewritten and re-severitied `medium` → `low`** | Executed: with the base probe forced to `MERGE_QUEUE_ELIGIBLE_CONFIGURED` and `strategy='squash'`, `cmd_pr_auto_merge` emits `['pr','merge','42','--auto','--squash']` and returns `disposition: enqueued`. 1631 is **not** a non-queue path — `cmd_pr_auto_merge` runs on both bases and forwards the flag unconditionally; the discriminator only labels the outcome. Corroborated by `test_github_ops_pr_merge.py:1349` and `leaf-command-reference.md:39`. The tree contradicts D3's premise as much as it supports it. |
| G2 | Condition 1 tells the run to compute (required ∩ non-green) while declaring the left operand unobtainable | **Upheld, Fix rewritten** | Contradiction confirmed at `SKILL.md:1245` vs `SKILL.md:1205-1208`/`:56`; `get_status` on #1112 returns per-context `state` and no required flag; the MCP server exposes no branch-protection tool. The original **Fix** proposed intersecting with "checks that carry a required-looking identity … (`verify / conclusion`)" — that collides with D1's Done-when ("names no individual check") and D0's STOP. Replaced with an explicit "required set not enumerable → name no blocker" branch. |
| G3 | "No positive required-context set is recorded in `report-01.md`, in `SKILL.md`, or anywhere else in the tree" | **Premise refuted; gap rewritten, severity `low` retained** | `SKILL.md:150`: a PR "produces the required `verify / conclusion` check". `CLAUDE.md:21`: "the required `verify / conclusion` check still reports green". The contract names the required context twice — 1050 lines before the section that consumes it, and unlinked from it. G3 now carries that narrower, true claim. |
| G4 | *(new)* | **Added** | D1 shipped "a non-required context … **is disclosed** to the operator" (`SKILL.md:1241-1243`) with no artifact anywhere: the Step-9 "8 Merge gate" row (`SKILL.md:1407`) requires only "Conditions 1–3 met and auto-merge armed", and the § Report template (`SKILL.md:1456-1562`) has no merge-gate section — its required sections are Skills loaded / Deliverables / Build gate / Findings / Reviewer participation / Cost / Contract check / What have we learned / Residue. Condition 4's sibling disclosure **does** have one, at `SKILL.md:1530`. Severity `medium`. |
| D1 row | "`grep -i license` → 0 hits" | **Re-derived; qualified** | True on the landed file; at HEAD it returns `SKILL.md:975` ("licenses"/"licenses"), later unrelated Step-6 prose. Substantive claim unaffected. |
| Out-of-scope row | "`grep -i license` over the landed **and current** `SKILL.md` returns zero hits" | **Refuted as stated; corrected** | Same hit at `SKILL.md:975`. Broadened the sweep to real check names; the merge-gate rule names none. |
| Method sweep | "Tree-wide `checks are green` → only `SKILL.md:1201` and `ci_verify.py:645`" | **Incomplete; noted** | `SKILL.md:1201` says "all checks green", not "checks are green". The literal phrase also occurs at `SKILL.md:57` ("arming auto-merge while the required checks are green") — correctly scoped to *required*, so benign, but the sweep as reported was not exhaustive. |
| Method provenance | "(`#1147`, `#1177` identified)" | **Incomplete; corrected** | `ea1ac4b7` (#1190) inserted `SKILL.md:1218-1224`, inside condition 1. |
| D0 / D2 / D4 / D5 rows | clean or disclosed-deviation passes | **Upheld** | D0's two inputs re-derived live (#1112). D2: all five #1137 commits author `Claude <noreply@anthropic.com>`. D4: `grep -n "git add"` → only l. 339/340/509, all prohibitions, no surviving `git add -A` example. D5: `SKILL.md:1408` + `:1373-1377` carry the reworded form; the over-broad phrasing survives only in other plans' **run reports**, never in contract text (`doc/plans/README.md`, `cloud-bridge.md` both clean). |
| Report accuracy §, PR/diff/comment/SHA figures | "no contradictions found" | **Upheld on the subset re-derived** | 3 paths / +324 / −5; 4 comments with the exact four authors; #1112 head and status verbatim. |

**Documents corrected.** *verification.md:* verdict `implemented-with-gaps` → `partially-implemented` with a
new § explaining why; § D3 rewritten to remove the refuted "non-queue path / discriminator" mechanism and
carry the executed result instead; the D3 row's `Correct?` cell restated ("Drop trigger was not met; premise
still unsettled"); the two `grep -i license` claims qualified to landed-vs-HEAD; the condition-1 provenance
list extended with #1190; the "could NOT be verified" `gh` bullet corrected to say the production-code
evidence is two-sided. *gaps.md:* open items 3 → 4; G1 rewritten and re-severitied to `low`; G2's Fix replaced
with a boundary-respecting one; G3 rewritten around the refuted premise; **G4 added**; a new
§ "Refuted during adversarial review" records R1 and R2 rather than dropping them silently.

**Residual doubt — what a third reviewer should look at first.**

1. **G1 is still unresolved and cannot be resolved from this session.** Somebody with a `gh` CLI must run
   `gh pr merge {N} --squash --auto` once against a `main`-based PR. Both readings of the tree are now
   documented; only that command settles it.
2. **Is G4 `medium` or `high`?** The Step-9 self-check is the contract's own guard, and it reports
   "8 Merge gate: done" for a run that disclosed nothing. That is close to "a guard that passes against the
   defect it names"; I filed `medium` because the row does not purport to check the disclosure at all — it
   omits it. A reviewer who reads that as a passing guard should raise it.
3. **Whether G2 and G3 are one defect or two.** They are two sites (`SKILL.md:1245-1252` and `SKILL.md:56`)
   of one underlying fact — "required contexts" has no resolvable referent on the cloud path. I kept them
   separate under the per-instance rule; a reviewer who merges them is not wrong.
4. **D0's inference itself, not its inputs.** Both inputs are now re-derived live (#1112 and #1117 each
   `merged: true` with `license/cla` `pending` on the head). What is *not* independently established is the
   premise that carries them — "a merge queue never admits a PR whose required contexts are unsatisfied."
   That is GitHub's documented behaviour, not something this tree or these two PRs prove; a reviewer who
   wants D0 airtight has to source it.

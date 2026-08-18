# Verification — 030-merge-gate-cannot-tell-a-required-check-from-a-decorative-one

**Verified against:** commit `ac06e4f` (HEAD)   **Landed as:** PR #1137, squash commit `991f3e5f`   **Verdict:** implemented-with-gaps

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
  plans' text is not credited or debited to this one (`#1147`, `#1177` identified).
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
| D1 | Step 8 condition 1 asks about required-ness | names the ruleset as source; disclose vs block; names no individual check | Yes | Yes | Yes, with one shipped omission (later fixed) | Yes | `SKILL.md:1200-1252`. `grep -oi "cla[a-z]*"` on the landed file → only `claude/CLAUDE/claim/clared/claring/clarification`; `grep -i license` → 0 hits. Tree-wide `checks are green` → only `SKILL.md:1201` (the negated contrast) and `ci_verify.py:645` (a different lane). |
| D2 | Record CLA root cause as an operator proposal | the proposal is recorded; no authorship change | Yes | Yes | Yes | Yes | `report-01.md` § What have we learned #1 and § D2. Claim executed: `git log origin/claude/harness-rule-gaps-541rjw --format='%an <%ae>'` → `Claude <noreply@anthropic.com>`; `get_commits` on #1137 → all 5 commits same author. Landed diff contains no authorship/CI change. |
| D3 | Correct the documented merge command | the § Step 8 command is the one that works, with a one-line reason | No — dropped | Yes (drop is disclosed) | Drop was authorised, premise now contradicted | n/a | `SKILL.md:1290` still `gh pr merge {N} --squash --auto`; `SKILL.md:70` maps the same form to `enable_pr_auto_merge`/`SQUASH`. `report-01.md` § D3 records the drop and § Residue carries it forward. |
| D4 | Warn about lockfile churn; stage explicitly | hazard and staging rule stated where a run commits | Yes | Yes | Yes | Yes | `SKILL.md:339-345` (§ Step 4 "Commit and push") and `SKILL.md:507-509` (§ Step 5). `grep -n "git add" SKILL.md` → only those two prohibitions; no `git add -A` command example survives to contradict the rule. |
| D5 | Reword the Step-9 Bridge row | wording matches intent; no longer contradicts a legitimate deliverable | Yes | Yes | Yes | Yes | `SKILL.md:1408` (Bridge row) and `SKILL.md:1373-1377` (§ Step 8 "Record nothing", the declared consistency alignment). `grep -rn "nowhere else under"` across `*.md` → the old over-broad form survives in no contract text. |

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

The tree now supplies evidence the run lacked, and it points the other way.
`_github_pr.py:1911` — the repository's own merge-queue enqueue path — builds `['pr', 'merge', identifier,
'--auto']` with **no** strategy flag, under a comment stating "Neither `--strategy` nor `--delete-branch` is
forwarded: the merge queue's own branch-protection configuration dictates the merge method." The non-queue
auto-merge path at `_github_pr.py:1631` does forward one (`f'--{args.strategy}'`, default `merge`), and the
two are separated by an explicit queue-configured discriminator. So this repository's production code treats
a strategy flag as *not applicable on a queue-gated base* — which is D3's premise. It does not by itself
establish that `gh` **rejects** the flag (the comment names rejection only for `--delete-branch`), so the
plan's stronger OBSERVED wording is still unconfirmed. Either way, `SKILL.md:1290` and `SKILL.md:70` still
document the `--squash` form for a repository whose own enqueue code omits it. Carried forward as G1.

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

- **"Do not write `license/cla` is not a hard gate into the contract"** — `grep -i license` over the landed
  and current `SKILL.md` returns zero hits; `grep -oi "cla[a-z]*"` returns no `cla` token that is not part of
  `Claude`/`claim`/`declar*`/`clarification`. No individual check is named in any rule.
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
  CLI is present in this session either, so the same instrument the run lacked is still missing. The
  production-code evidence in `_github_pr.py` is strong but indirect: it shows the strategy flag is
  deliberately *not forwarded* on the queue path, not that `gh` errors on it.
- **The independent cold read the report describes.** A sub-agent's transcript is not in the tree. I
  performed an equivalent isolated read myself and it returned the plan's two required answers, but I cannot
  confirm the run's own cold read happened as described.
- **The point-in-time `mergeable_state: unstable` on #1137 at head `2ff57ec`.** Both that head and the PR
  are now historical; the API returns `unknown` for a merged PR. The report itself flags this as
  point-in-time, so it is a limitation of the surface, not a discrepancy.
- **Wall-clock and token figures.** The report states tokens are unavailable and derives wall-clock from
  git/PR timestamps; the timestamps I can check (PR created 14:29:46Z, merged 14:59:40Z) agree, but "run
  start ≈ 14:04 UTC" rests on a first branch operation whose branch has since been deleted.

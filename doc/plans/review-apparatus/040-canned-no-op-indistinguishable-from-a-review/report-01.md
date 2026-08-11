# Run report — 040-canned-no-op-indistinguishable-from-a-review (run 01)

**Date (UTC):** 2026-08-11    **Branch:** `claude/canned-no-op-review-32oz84`    **PR:** [#1165](https://github.com/cuioss/plan-marshall/pull/1165)    **Outcome:** completed (landing delegated to the merge queue via armed auto-merge)

## Skills loaded

- `cloud-plan-lane` (working contract, loaded first)
- `plan-marshall:ref-code-quality` (+ `standards/error-handling.md` — the "branch on producer status before folding its payload" rule the plan's Notes cite)
- `pm-plugin-development:plugin-script-architecture`
- `pm-dev-python:python-core`
- `pm-dev-python:pytest-testing`
- `plan-marshall:persona-implementer`

All obtainable by bundle path; none skipped.

## Claim re-derivation (D0 gate — mutates nothing)

Every claim re-derived against the clone (the plan warns the corpus rows are past runs, not the tree):

| Claim | Label | Verdict from the tree |
|---|---|---|
| `display_detail` renders "no reviewer produced content" identically to a clean review | OBSERVED | **CONFIRMED** — `automatic-review/SKILL.md` Branch A composes `"{N} comment(s) found (unified triage pending)"`; with the default-empty `required_bots`, `participation_complete` is vacuously true, so Branch A fires with `N=0` whether reviewers reviewed-clean or never produced content. |
| The refusal taxonomy exists but does not reach `display_detail` | OBSERVED | **CONFIRMED** — `bot_states` (with the refusal states) is read by the guard but never interpolated into the Branch A `--display-detail`. |
| A binary `== 'awaitable_window'` test collapses a three-valued `rate_limit_class` | OBSERVED | **CONFIRMED** — `review_completeness.py:310`: `awaitable = rate_limit_class(bot) == 'awaitable_window'` → `unknown` collapses into `STATE_REFUSED_HARD`. |
| All three registry docs declare `rate_limit_class` | OBSERVED | **CONFIRMED** — coderabbit=`awaitable_window`, sourcery=`hard_quota`, pr-agent=`unknown`. All three values live; pr-agent's `unknown` is the one the binary test mis-renders. |
| The refusal pre-filter leaks within a single bot | OBSERVED | Not re-derived to a wired change — see "Out of this plan (split)". `_is_refusal_notice` enumerates known shapes; the positive-restatement remedy is a Notes "candidate remedy, not yet applied", not a D-deliverable. |
| The review-retrospective surface has no row for "enabled, invoked, refused" | OBSERVED | **CONFIRMED** — `review_retrospective.aggregate()` builds `reviewers[]` purely from the finding records (`per_reviewer` keyed by observed `author`); reviewed-clean, never-ran, and refused all render identically by having **no row**. |
| A diff-size refusal threshold of 150,000 characters | HYPOTHESIS | **NOT re-derivable** — Sourcery's size `refusal_patterns` entry is deliberately number-free (`"your pull request is larger than the review limit of"`). Per the plan, **do not pin a test to 150,000**. |
| One vocabulary change serves both consumers | HYPOTHESIS | **Splits** on the cause axis — see below. The `unknown`-collapse fix and the display distribution serve both; the quota-vs-size **cause member** is a material widening and is split out. |
| Share of past absences that were size vs quota | UNDERIVED | Partition is **derivable from the tree**: Sourcery declares a per-PR **size** notice and a weekly **quota** notice as distinct `refusal_patterns`, so the taxonomy CAN partition by cause. The plan does not require a historical rate (that data is git-ignored / absent); D0's HALT does not trigger because the partition exists in the registry. |

## Scoping decision (recorded per the split threshold)

The plan says: "if D1's derivation widens the change materially, split rather than absorbing." The
quota-vs-diff-size **cause** distinction, if wired as a new taxonomy member (`refused_size` vs
`refused_quota`), requires threading "which refusal pattern matched → cause" through
`_github_pr._is_refusal_notice`, `github_pr.py fetch_findings`, and `review_completeness.py` — a
material multi-file widening. It is **not needed** for D2 (deficit) or D3 (display distribution),
both of which read finding counts and the existing states. Decision: **document** the partition-by-cause
(D0) as derivable from `refusal_patterns`, wire only the `unknown`-collapse fix (D1), and **split out**
the wired cause-member. Recorded here as the split the threshold calls for.

## Deliverables

- **D0 — counting-rule contract + partition-by-cause (docs, mutates nothing).** Commit `058d761`.
  Added to `bot-participation-contract.md` (the single source of truth): the **counting rule** (filed
  pr-comment findings per reviewer — never a raw comment count; the reviewed-at-all predicate =
  `participated` ∪ `participated_but_empty`; the required / optional / enabled-roster populations, each
  published), and the **partition-by-cause** (refusals split by awaitability via `rate_limit_class`
  AND by cause — quota vs diff-size — carried by `refusal_patterns`; Sourcery declares both a size and a
  quota notice, so the partition is derivable from the tree and git → D0's HALT does not trigger). The
  invariant "do not report a participation rate over a corpus pooled across causes" is stated.

- **D1 — reviewer-state vocabulary (`refused_unknown` + consolidation).** Commits `11df4da`,
  `058d761`, `3ab4e76`. `review_completeness.py`: added `STATE_REFUSED_UNKNOWN` + `_refusal_state()`
  (one-to-one over the three-valued `rate_limit_class`), replacing the binary `== 'awaitable_window'`
  test that folded `unknown` into `refused_hard`; added to `_UNPROVEN_STATES`. Vocabulary agreed once in
  `bot-participation-contract.md` (nine-member taxonomy). **Split (per the threshold):** the *wired*
  quota-vs-diff-size cause member is a material multi-file widening, not needed for D2/D3 — documented as
  derivable, wiring deferred to a follow-up plan.

- **D2 — deficit signal.** Commit `11df4da`. `assess_deficit()` + a `deficit` subcommand. Fires only
  against a real baseline; `unassessable` when every other reviewer refused; never on `0 : 0`. Carries
  `gates_merge: false` / `proves: reviewer_quality_only` — an observability signal, never a merge
  verdict. Finding count is the filed pr-comment count per reviewer.

- **D3 — `display_detail` carries the reviewer-state distribution (both surfaces).** Commits `11df4da`
  (surface 1), `9f37480` (surface 2). Surface 1: `compose_review_state_summary()` +
  `review_state_summary` field; automatic-review Branch A interpolates it so `0 comment(s) found — 3
  refused` and `0 comment(s) found — 3 empty` no longer render identically. Surface 2:
  `review_retrospective.aggregate()` emits a row per **enabled** reviewer (roster ∪ observed), each
  carrying `participation: measured | unmeasurable`, closing the vacuous-set (no-row) defect.

- **D4 — tests, each proven to FAIL pre-fix.** Commits `11df4da`, `9f37480`. The two tests that codified
  the old `unknown → refused_hard` collapse were flipped to the new behaviour (they failed pre-fix —
  observed: `2 failed` before the code change). The new deficit tests cover the five corpus rows: (a)
  two deficit rows report a deficit; (b) the `0 : 0`-with-baseline row is `clean`; (c) the two
  baseline-less rows are `unassessable`. `test_required_count_alone_cannot_distinguish_the_rows` pins
  that `required_count == 0` is identical across all five rows while the verdict differs — the naive
  detector's blind spot. The 150,000-char threshold is **not** pinned to a number (the registry pattern
  is deliberately number-free). New/changed functions did not exist pre-fix, so their tests
  AttributeError against pre-fix code.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (`review_completeness.py`,
`review_retrospective.py`, and their two test files), so the gate triggered `./pw verify`. Result:
**`=== verify: SUCCESS ===`** — 18979 passed, 14 skipped. `./pw quality-gate`: `status: pass`,
`total_issues: 0`, mypy `Success: no issues found in 391 source files`, ruff `All checks passed!`. The
first `./pw verify` surfaced 4 collection errors from a sibling drift-guard
(`test_bot_participation_contract.py` pins the taxonomy member count); fixed in `3ab4e76` and the
re-run is green.

## Findings

### From the pre-PR verification sub-agent (Step 6, general-purpose, read-only)

Verdict: D0–D3 met and (where warranted) tested; both mandated cold reads PASS; the D1 cause-member
split is legitimate and leaves no "Done when" unmet. It found **eight documentation-drift instances**
the `refused_unknown` member (eight→nine taxonomy) introduced but the diff did not chase down. Each is
a now-false taxonomy statement — the exact misleading-signal defect this epic exists to remove — so all
were **fixed** (commit `607fa10`), then confirmed clean by full-tree greps.

- **[fixed]** `review_completeness.py:160` — the module-level constant-block comment still said "Eight
  members … NOT a ninth member", contradicting the same file's updated docstring. (HIGH — inside a
  changed file, in a hunk the diff never opened; my own beyond-diff sweep missed it.)
- **[fixed]** `workflow-pr-doctor/standards/automated-review-lifecycle.md:54` — "exactly one of eight"
  + enumeration missing `refused_unknown`. (HIGH, different bundle.)
- **[fixed]** `tools-integration-ci/standards/pr-review-operations.md:248` — "seven members" (also
  pre-existing drift: omitted `declined`) → "nine non-participation members"; and `:256` refused row
  two-way → three-way.
- **[fixed]** five two-way "refused_awaitable / refused_hard" classification descriptions
  (`workflow-integration-github/SKILL.md:137`, `github_pr.py:801` & `:984`, `_github_pr.py:177`,
  `test_github_pr.py:971`) → three-way.

Cold reads (recorded per the plan's Verification section):
- **D3 strings — PASS.** `"0 comment(s) found — 3 refused …"` reads as *not reviewed*; `"… — 3 empty …"`
  reads as *reviewed and clean*. The two conclusions differ, so the surface does its job.
- **D2 deficit — PASS.** A `verdict: deficit` report shows `gates_merge: false` / `proves:
  reviewer_quality_only` on adjacent lines; a naive operator concludes it does NOT block a merge.

Not independently re-run by the sub-agent (read-only): the "fail pre-fix" clause. Recorded from the
authoring run — the two flipped collapse-tests were observed `2 failed` against the pre-change code
before the fix landed (§ Deliverables D4), and the new-symbol tests necessarily error pre-fix.

No `re-dispatch` of the sub-agent: every finding was mechanical count-drift of one class, all fixed,
and two full-tree greps (`eight[- ]member…`, `refused_awaitable / refused_hard` without
`refused_unknown`) return clean — a cheaper, exhaustive re-verification of the exact finding class.

### From CI / PR review

- **CI green.** Required `verify / conclusion` = **success** on head `7ecd755`; `verify / verify`,
  `dependency-review`, `review / review`, `verify / gate`, `generate-check` all success. `Sourcery
  review` and `auto-merge` check-runs `skipped`. `mergeStateStatus: unstable` (all required contexts
  passed; only non-required remain), never `blocked`.
- **No actionable review comments.** Inline review-thread surface: empty. The conversation/review
  surface carried only non-feedback: two refusals (CodeRabbit, Sourcery), one clean review (PR-Agent),
  and a CLA-assistant status badge. Per the bot-participation contract and the plan's own thesis, a
  refusal notice and a clean Guide are participation artifacts, not code feedback — disposed of as
  accepted without a fix task and without a reply (being frugal about GitHub replies). Nothing required
  a fix or a thread reply.
- **Non-required status disclosed:** `cla-assistant` shows `not_signed`. It is **not** a required
  context (the PR is `unstable`, not `blocked`), the PR author is the repository owner
  (`cuioss-oliver`), and the badge is the "signed already but pending" transient. It does not gate the
  merge; recorded here rather than acted on.

## Reviewer participation

Population derived from the registry `author_login` of each
`automatic-review/standards/{bot_kind}.md` doc (never transcribed): `coderabbitai` (coderabbit),
`sourcery-ai` (sourcery), `cuioss-review-bot` (pr-agent) — the same set `.github/workflows/pr-agent.yml`
names.

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Published its `## PR Reviewer Guide 🔍` (its declared `issue_comment` shape) against head `7ecd755` — a clean result: "PR contains tests", "No security concerns identified", "No major issues detected". A `participated_but_empty`-shaped review. |
| `coderabbitai` | `rate-limited` | Published only "⚠ Review limit reached … Next review available in: 5 minutes" — an awaitable-window refusal in place of a review. It engaged but did not review this diff. |
| `sourcery-ai` | `rate-limited` | Published only "you have reached your weekly rate limit of 500000 diff characters" — a hard-quota (weekly) refusal in place of a review. |

**Coverage: 1 of 3.** The § Step 8 review-coverage shortfall disclosure fired: "Review coverage 1 of 3
— `cuioss-review-bot` reviewed (clean); `coderabbitai` rate-limited (awaitable window, ~5 min);
`sourcery-ai` rate-limited (weekly quota)." Rate limits are routine and outside our control, so per the
contract this is a **disclosure, not a block** — the merge is not held for them.

⭐ This run is itself an instance of the very defect the plan fixes: two reviewers produced only
refusals and one reviewed-and-found-nothing, which the old `display_detail` and retrospective would
have rendered indistinguishably from "reviewed clean". After this change the states are distinct
(`reviewed` vs `rate-limited`), and the disclosure above states the shortfall in words.

## Cost

- **Tokens:** not available to the agent in this session — the harness does not expose a token count
  to the run, stated plainly rather than estimated.
- **Wall-clock:** ~25 min of active session work from branch push (first commit `1bb595e`) to
  auto-merge arming, plus ~13 min of CI wall-clock for the `verify` job (started 15:08:52, `verify /
  conclusion` at 15:22:20) that overlapped the review-cycle wait.
- **Population:** this single Claude Code cloud session's wall-clock, as one interactive session. ⛔
  **NOT comparable** to a plan-marshall `metrics.toon` total — that counts the orchestrator-plus-agent
  dispatch tree under plan-marshall's per-task billing boundary, which this session does not share.
  No token figure is presented, so no false parity is implied.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — six skills, all by bundle path (named in § Skills loaded). |
| 2 Branch | Done — harness-assigned `claude/canned-no-op-review-32oz84` kept as-is; present on `origin` (pushed before any edit). GitHub access path: **GitHub MCP server** (the cloud path). |
| 3 Plan directory | Done — `doc/plans/review-apparatus/040-canned-no-op-indistinguishable-from-a-review/plan.md` exists and opens with the first-instruction block (verified present at Step 3). |
| 4 Implement | Done — commits carry the `Co-Authored-By: Claude` trailer; all five deliverables addressed. |
| 4 Per-commit gate | Done — every `*.py`-touching commit was preceded by a `./pw quality-gate` with `total_issues: 0` and empty `errors[]`. |
| 4 Pushed | Done — no unpushed commit remains (each commit pushed immediately). |
| 5 Build gate | Done — `*.py` changed → `./pw verify` run; `=== verify: SUCCESS ===` (18979 passed) after the drift-guard fix. |
| 6 Verification sub-agent | Done — findings and dispositions in § Findings; eight doc-drift instances found and fixed, both cold reads PASS. |
| 7 PR cycle | Done — PR #1165; both comment surfaces read; every comment dispositioned (all non-actionable — refusals / clean review / CLA status). |
| 8 Merge gate | Conditions 1–3 met; auto-merge armed (SQUASH). Session could not self-wake to watch the queue (self-wake tools approval-gated — § What have we learned), so the `MERGED` confirmation is delegated to the orchestrator's collect — **completed, not partial** (§ Step 8). |
| 8 Bridge | No status/bookkeeping write outside this plan's own directory; the report carries the PR number and per-deliverable outcome. |
| 9 This check | Recorded here. |
| 9 What have we learned | Below. |

No `/sync-plugin-cache` is owed — it is a machine-local build step a cloud run never performs or records (§ Scope and precedence).

## What have we learned (Step 9)

**Evidence from this run:** both self-wake tools (`subscribe_pr_activity`, `send_later`) returned
`MCP error -32003: requires approval`. Notably, re-calling `subscribe_pr_activity` **after** the
operator selected "approve autonomous watch" in an `AskUserQuestion` still returned the same error —
the chip answer is not the harness permission grant, so the subscription could not be established that
way. The run nonetheless completed the review cycle by **manual GitHub-MCP polling** (`pull_request_read`
is not gated): CI finished during the operator exchange, a re-poll saw it green, both comment surfaces
were read, and auto-merge was armed.

**Proposed contract change (presented to the operator, not self-approved):** § Step 8 / § Cloud session
affordances frame the gated-self-wake case as "arm-and-hand-off". This run shows a second viable path
when the operator is reachable or the session stays active: **drive the review cycle by manual
`pull_request_read` polling** rather than requiring a subscription — read both comment surfaces and the
check-runs on demand, then arm. Worth a one-line note in § Step 8 that manual MCP polling is the
in-session fallback when the self-wake tools are approval-gated. Per Step 9 this would ship as a
**separate `chore/` PR** touching only the skill, not in this plan's PR. Operator decision pending; if
declined, recorded as "no change".

## Residue

- **Landing delegated.** Auto-merge is armed (SQUASH); the merge queue lands the PR once required
  checks pass on the final head. The squash merge SHA does not exist yet and is read from the PR merge
  event by the orchestrator's collect, not embedded here.
- **Split-out (follow-up plan):** the *wired* quota-vs-diff-size refusal **cause** member
  (`refused_size` / `refused_quota`), deferred as a material widening. The partition is documented as
  derivable from `refusal_patterns`; only the wiring is deferred.
- **Contract-change proposal pending operator decision** (§ What have we learned): a one-line § Step 8
  note that manual `pull_request_read` polling is the in-session fallback when self-wake is
  approval-gated. Ships as a separate `chore/` PR if accepted.
- **CodeRabbit's window reopens in ~5 min.** Not awaited — rate limits are disclosed, not blocked. If
  richer coverage is wanted, `@coderabbitai review` could be posted after the reset; deliberately not
  done here.

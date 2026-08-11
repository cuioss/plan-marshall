# Run report — 040-canned-no-op-indistinguishable-from-a-review (run 01)

**Date (UTC):** 2026-08-11    **Branch:** `claude/canned-no-op-review-32oz84`    **PR:** _pending_    **Outcome:** in-progress

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

_pending_

## Reviewer participation

_pending_

## Cost

_pending_

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

- Split-out: the wired quota-vs-diff-size refusal **cause** member (`refused_size` / `refused_quota`),
  deferred as a material widening. The partition is documented as derivable; the wiring is a
  follow-up plan.

# Landing — PLAN-PR-015 `barrier-override-not-head-bound`

epic: review-apparatus · analysed 2026-08-02 · **PR #1077 MERGED** at `2026-08-02T12:39:52Z`
(verified via `ci pr view`, NOT from the landing message) · 2/2 deliverables · 18 inbox messages

## What landed

The `#1067` shape: the pre-merge review barrier's `ask`-mode "Merge anyway (record reason)" override
was free text in `decision.log`, bound to nothing, so a later barrier evaluation at a *different*
HEAD could recall it and merge a tree the operator never saw.

- **One persisted record + one predicate** — `manage-status merge-authorization` (`grant` / `check`)
  over `status.metadata.merge_authorizations`. `grant` persists `{head, granted_over, reason,
  granted_at}`; a re-grant at a new HEAD overwrites (the overwrite IS the sanctioned re-seek — no
  revoke verb). `check` takes **no `--kind`** and returns per-record `valid`/`lapsed` plus
  `authorized_kinds[]` / `lapsed_kinds[]` / `any_authorized`. Empty store → `any_authorized: false`;
  `absent` is never collapsed into `valid`.
- **Derived population + end-to-end regression** — the roster test parses `branch-cleanup.md`'s
  `## Merge-Authorization Roster` with the shared `parse_roster_rows`: no hardcoded membership, no
  cardinality literal, non-emptiness asserted FIRST. The e2e test pins the #1067 shape (grant at
  docs-only HEAD A → advance to HEAD B carrying production commits → refuse; re-grant → admit).

The escape hatch was **bound, not removed**. Normative rule now stated in the barrier doc: the ONLY
admissible evidence that an operator authorized proceeding past a reported gap is a
`merge-authorization check` verdict at the CURRENT HEAD — a `decision`-log entry, *including one this
plan wrote on an earlier pass*, is NEVER admissible authorization evidence.

## ⭐⭐ The D1 derivation — the spec's hypothesis was wrong in two directions

The spec assumed no existing merge-gate authorization mechanism lapses on HEAD change. D1 found
**six** mechanisms, not one:

| Mechanism | Was it HEAD-bound? |
|---|---|
| `barrier-ask-override` | no (free-text log) → now `grant`+checked |
| `pre-merge-consent` | no (re-rebase between consent and merge) → now `grant`+checked |
| `red-ci-override` | no (WARNING log only) → now `grant`+checked |
| `rereview-timeout-override` | no (named `{head_sha}` in the log, persisted nothing) → now `grant`+checked |
| `automatic-review-force-done` | ⭐ **ALREADY bound** via `head_dependent: true` — the counterexample |
| `final_merge_without_asking` | OUT OF CLASS — standing config, authorizes a *policy* not a tree |

⭐ Three of the four unbound mechanisms **were never in the plan's framing at all**. Building on the
hypothesis unchallenged would have meant "fixing" a mechanism that was already correct.

**Convergence answer** (the request's consolidation question): this plan and PLAN-PR-013 converge on a
single predicate *location* (the pre-merge barrier is the last gate before merge routing) but NOT on a
single *record* — PR-013 governs a bot's participation credit, this governs an operator's
authorization. **The consolidation shipped is the single check site, not a merged record.**

## ⛔ Four blocking defects, all found by the plan's own self-review, all in the fail-closed guard

Round 1 (`9e1caf`) found the **new check reintroduced the exact fail-open shape the plan exists to
remove**: correctly HEAD-bound and **kind-agnostic**, so a `pre-merge-consent` granted seconds earlier
at the same HEAD over a *different gap* satisfied the review barrier. Then `37dad6` — the UNKNOWN
branches, which may never merge, could still **mint a durable grant**; the refusal was enforced on the
routing and not on the credential issuance. Then `454e1b` — a **fail-open `--kind` matcher inside a
guard built to fail closed** (admitted on no-match).

⭐ Zero of the four came from review bots. See § below for why that is not a coincidence on this PR.

## ⛔ The landing message preceded the merge by 59 MINUTES

Message written `11:40:51Z`; merge `12:39:52Z`. PLAN-PR-014's gap was **13 minutes**.

⭐ **PLAN-PR-010 now has n=2 with a measured spread, and the spread is the finding**: the gap is not a
small race, it *scales* with whatever runs between `lessons-capture` (order 60) and `branch-cleanup`
(order 70). A fix that assumes a narrow window is mis-specified.

⭐ Corroborated independently here: messages `-002..-007` were written 11:41–11:43 (pre-merge,
`lessons-capture`), messages `-008..-018` at 13:17–13:22 (**post-merge**, `plan-retrospective`, order
995). The two batches straddle the merge, which is direct evidence for the ordering model.

## ⛔ The plan shipped a review-barrier hardening with no substantive review of the hardening

- **coderabbit** REFUSED — `awaitable_window`
- **sourcery** REFUSED — `hard_quota`
- **pr-agent** participated with a no-issues guide

`automatic-review` recorded "1 comment(s) found"; `review-retrospective` recorded "1 reviewer compared,
0 actionable comments"; the step chain stayed green. The operator read it correctly, **explicitly
accepted the gap, and merged** — the right disposition, and exactly why it must be recorded.

⭐ **The asymmetry worth pinning** (msg `-017`): `review_completeness` returned **green** while the
barrier's own WARNING at 11:31:36 told the truth in terms. *The check that passed and the sentence that
told the truth disagreed, and only the prose was right.*

⭐ Two independent refusal causes with the same effect — `awaitable_window` and `hard_quota`. **The
composite is invisible from any single bot's status**: a per-bot refusal-rate view cannot show it, only
a per-PR participation count can. Feeds PLAN-PR-006.

⚠ This is the **second recorded instance in this epic** of a detected refusal reported alongside a
clean review step (first: #1026).

## ⭐⭐ VERIFIED defect — an edit-in-place bot's `reviewed_commit_sha` never advances

Msg `-018`, and **I confirmed it against the implementing source rather than accepting the claim**:

- `github_pr.py:783-785` — the `(bot_kind, comment_id)` dedup `continue`s.
- `github_pr.py:824` — `reviewed_commit_sha` is passed **only** into `add_finding`, below that `continue`.
- `_findings_core.py:290-291` — written at record creation; **there is no update path in the codebase**.
- `automatic-review/SKILL.md:245` asserts the opposite in as many words: *"this re-stamps every
  finding's `reviewed_commit_sha` to the new HEAD … updated implicitly by that fresh `fetch_findings`
  run; no separate update call is needed."*

pr-agent edits ONE persistent comment, so its `comment_id` is stable ⇒ for pr-agent the documented
re-stamp **has never once happened**. Observed live on #1077 (`ae6c5615…` → `a2855290…`, sha frozen at
`ae6c5615…`, `count_skipped_duplicate: 1`).

⚠ **I part-refute the message's stated consequence.** It says the check "would compare the new HEAD
against a SHA two generations stale". The direction matters: since the frozen sha can never equal the
live HEAD, the `head_sha == reviewed_commit_sha` skip at `SKILL.md:236` can **never be satisfied**, so
trigger B re-fires on every advance regardless of whether the bot already re-reviewed. **This is
fail-CLOSED (redundant re-review), not a missed review** — materially less severe than the message
implies, and it changes how PLAN-PR-013 should scope it.

⚠ Gated by `re_review_on_loopback` (default `false`); it fired on #1077 because this repo enables it.

⭐⭐ **THREE independent paths reached this same mechanism**: msg `-018` (first-party, observed),
`truthful-signals-010`'s `lane-router-…-007` (dedup drops the edited comment), and our own
`review-apparatus-011` (movement credits participation). The sibling's synthesis — *the edit is
DROPPED from findings while the movement it caused CREDITS participation* — was filed as HYPOTHESIS;
**the dedup half is now OBSERVED and source-confirmed.** The movement half remains unverified.

## Positive observations (recorded so the ledger is not failure-only)

- The freshness gate went stale purely from finalize-internal commits and was honoured by **re-running
  verify**, not force-overridden — the documented `push.md` re-stale reconciliation path worked.
- **Shared-file sequencing held.** `branch-cleanup.md` is shared with PR-008/009/013/014; sequenced,
  never paired. The early baseline rebase onto `origin/main` was a real (non-noop) replay.
- A simplify pass silently dropped a mypy annotation, caught **only** because `pre-push-quality-gate`
  declares `head_dependent: true` and re-fired after the settle commits. Without the HEAD comparison a
  stale `done` would have been trusted and a typing regression would have shipped behind a green
  finalize. (Delegated — msg `-007`.)

## Feeds

- **PLAN-PR-013** — gains the source-confirmed `reviewed_commit_sha` freeze, **with the corrected
  fail-closed direction above**. Check first whether #1071's timestamp path already supersedes the SHA
  read.
- **PLAN-PR-006** — the two-refusal-causes-one-effect composite; a per-PR participation count is the
  only view that shows it.
- **PLAN-PR-010** — n=2, and the *spread* (13 min vs 59 min) is the new evidence.
- **PLAN-PR-008** — `awaitable_window` + `hard_quota` co-occurrence is its deadlock surface.

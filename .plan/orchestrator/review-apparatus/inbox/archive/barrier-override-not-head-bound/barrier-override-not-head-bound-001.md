envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=review-apparatus
kind=landing
created=2026-08-02T11:40:51Z

## What landed

**PLAN `barrier-override-not-head-bound` — "A barrier override is not bound to the HEAD it was granted against"** — PR **#1077**, `fix(phase-6-finalize): bind pre-merge barrier override to the HEAD it was granted against`.

The `#1067` shape: the pre-merge review barrier's `ask`-mode "Merge anyway (record reason)"
override was recorded as free text in `decision.log`, bound to nothing, so a later barrier
evaluation at a *different* HEAD could recall it and merge a tree the operator never saw.

Shipped in two deliverables:

1. **One persisted record + one predicate.** New `manage-status merge-authorization`
   subcommand (`grant` / `check`) over `status.metadata.merge_authorizations`, in a
   `_cmd_merge_authorization.py` sibling of `_cmd_mark_step.py`. `grant` persists
   `{head, granted_over, reason, granted_at}` per kind; a re-grant at a new HEAD overwrites
   (the overwrite IS the sanctioned re-seek — no revoke verb). `check` takes **no `--kind`**
   — the barrier's question is "is there a valid authorization for the gap I am reporting" —
   and returns every record with a per-record `valid`/`lapsed` verdict plus
   `authorized_kinds[]`, `lapsed_kinds[]`, `any_authorized`. Empty store → `any_authorized:
   false`; `absent` is never collapsed into `valid`.
   Wired into `branch-cleanup.md` (roster + three grant sites + ONE barrier check site) and
   `branch-cleanup-rereview.md` (two trigger-A grants), with a cross-reference from
   `automatic-review/SKILL.md`.
2. **Derived population + end-to-end regression.** `test_merge_authorization_roster.py`
   derives the authorization population by parsing `branch-cleanup.md`'s
   `## Merge-Authorization Roster` with the shared `parse_roster_rows` — no hardcoded
   membership, no cardinality literal, non-emptiness asserted FIRST, per-member mutation
   guard. `test_pre_merge_barrier.py` pins the #1067 shape end-to-end (grant at docs-only
   HEAD A → advance to HEAD B carrying production commits → `check --head B` refuses;
   re-grant at B → admits).

Normative rules now stated in the barrier doc in as many words: **the ONLY admissible
evidence that an operator authorized proceeding past a reported gap is a
`merge-authorization check` verdict at the CURRENT HEAD; a `decision`-log entry — including
one this plan wrote on an earlier pass — is NEVER admissible authorization evidence.** The
escape hatch was **bound, not removed**, and no existing WARNING decision-log line was
deleted or made quieter.

## The D1 derivation the epic should keep

The spec's own **hypothesis was partly wrong**, and D1's enumeration is the durable artifact:
there are **six** merge-gate authorization mechanisms, not one, and one of them was *already*
HEAD-bound:

- `barrier-ask-override` — was NOT bound (free-text log only) → now `grant`+checked
- `pre-merge-consent` — was NOT bound (release-before-wait / re-acquire can re-rebase between
  consent and merge) → now `grant`+checked
- `red-ci-override` — was NOT bound (WARNING log only) → now `grant`+checked
- `rereview-timeout-override` — was NOT bound (named `{head_sha}` in the log, persisted
  nothing) → now `grant`+checked
- `automatic-review-force-done` — **ALREADY HEAD-bound** via `head_dependent: true` +
  `--head-at-completion`. Recorded, not re-fixed. This is the counterexample to the spec's
  hypothesis that no existing mechanism lapses on HEAD change.
- `final_merge_without_asking` — OUT OF CLASS: standing config, authorizes a *policy* rather
  than a specific tree.

**Convergence answer for the epic (the request's consolidation question):** this plan and
PLAN-PR-013 DO converge on a single predicate *location* — the pre-merge barrier is the last
gate before merge routing — but NOT on a single *record*. PR-013 governs a bot's
participation credit (re-derived from the provider by Predicate 2); this plan governs an
operator's authorization (a persisted grant). The consolidation shipped is the single check
site, not a merged record.

## Residue the epic should track

1. **⛔ The green review step on #1077 is NOT evidence of substantive review.** Both
   substantive bots REFUSED: coderabbit `awaitable_window`, sourcery `hard_quota`. Only
   pr-agent participated, with a no-issues guide. `review-retrospective` recorded
   "1 reviewer compared, 0 actionable comments". The operator explicitly accepted the gap and
   chose to merge. **This plan therefore shipped a review-barrier hardening with no
   substantive external review of the hardening itself.** A post-merge PR revisit on #1077 is
   owed — a late review here is a recurrence, not an incident.
2. **This plan structurally cannot self-verify its own fix.** It changes a finalize-time
   component (`default:branch-cleanup`) and adds a new `manage-status` verb; its own finalize
   runs before `sync-plugin-cache` makes the change live. The evidence of correctness is
   deliverable 2's pre-fix-failing regression tests, never the green finalize. (Same class as
   PLAN-10's finalize-ordering defect.)
3. **Four blocking defects were caught by the plan's own pre-submission self-review**, across
   three rounds — the first of which reintroduced the exact fail-open shape the plan exists to
   remove. Filed as separate `candidate-lesson` messages alongside this landing.
4. **A simplify-pass edit silently dropped a mypy annotation**, caught only because the
   head-dependent quality gate re-fired after the settle commits. Filed as a
   `candidate-lesson`.
5. **The freshness gate went stale purely from finalize-internal commits** advancing the tree
   hash past the last build entry. It was honoured by RE-RUNNING verify, not force-overridden
   — the documented `push.md` § "Finalize-internal re-stale reconciliation" path behaved
   correctly. No action owed; recorded as a positive observation.
6. **Shared-file sequencing held.** `branch-cleanup.md` is shared with PR-008, PR-009, PR-013,
   PR-014 — sequenced, never paired, per the request. The early baseline rebase onto
   `origin/main` was a real (non-noop) replay.

envelope_version=1
sender_type=plan
sender_id=participation-credit-anchored-to-merge-candidate
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T21:18:30Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=participation-credit-anchored-to-merge-candidate
source_pr=1349

# branch-cleanup records done without checking either footprint-persistence write landed

## Context

`branch-cleanup.md` prescribes two writes into `references.json`, each with its own
section and its own stated purpose:

- § "Capture the realized footprint (before removing the worktree)" calls
  `manage-references capture-footprint` and is described as "the PRIMARY
  footprint-recovery mechanism (the merge-commit tier below is only a fallback)".
- § "Record the landing commit SHA (the footprint resolver's fallback seam)" records
  `merge_commit_sha` on the `switch-and-pull` success path.

This plan's `references.json` carries NEITHER key. It holds only `affected_files`,
`branch`, `base_branch`, `scope_estimate`, `domains`, `track` and `plan_creation_sha`.
Meanwhile the step recorded `outcome: done` with
`display_detail: "#1349 squash-merged via merge queue, worktree and refs removed"`.

The consequence is total for every post-merge coverage check. `_footprint_resolver.py`
walks four tiers — live worktree diff, `realized_footprint`, `merge_commit_sha`, legacy
`modified_files` — and all four failed:

- tier 1: the worktree was removed by this same step;
- tier 2: `realized_footprint` absent;
- tier 3: `merge_commit_sha` absent;
- tier 4: the legacy key is `modified_files`, and `references.json` carries
  `affected_files`, which is a different key holding the DECLARED set.

So `check-artifact-consistency` returned `inconclusive` on both
`affected_files_recall` and `affected_files_exact_match`, `analyze-logs` emitted
`ARTIFACT_COVERAGE_UNMEASURABLE`, and `check-routing-decisions` could only evaluate its
mis-prune predicates because this retrospective hand-supplied a `--diff-file`.

The footprint was never actually unavailable. The landing commit is `8025b2210`, and
`git diff 8025b2210^ 8025b2210` returns exactly 10 files — the same 10 that
`references.affected_files` already holds. The information existed throughout; no tier
had a path to it.

## Root cause

Two independent misses compound, and neither is observable:

1. Both writes are non-fatal by design. The capture's error branch is explicitly
   documented as "non-fatal here — log it and proceed", which is the right disposition
   for cleanup safety. But non-fatal is currently implemented as *unreported*: nothing
   downstream of the step records whether the key landed, so a skipped or failed write
   is indistinguishable from a successful one at every later read.
2. The step's recorded facts (`action`, `upstream_commit_count`, `merge_mechanism`,
   `merge_state`, `work_performed`) do not include footprint persistence, so the
   `done` outcome and its confident `display_detail` assert the worktree removal —
   the operation the capture is supposed to precede — while asserting nothing about
   the capture itself.

The resolver's own docstring anticipates exactly this run's shape and gets it wrong in
the safe direction: it says `merge_commit_sha` "is recorded by `default:branch-cleanup`
only on the synchronous merge path; on the async merge-queue path it is absent and
tier 2 is the resolution." This plan took the merge-queue path (`use_merge_queue: true`),
so tier 2 was the designated resolution — and tier 2 was empty too. The documented
fallback chain has no member that covers the merge-queue path.

## Proposed action

Three changes, smallest first:

1. **Make the miss observable.** After the two write sites, re-read `references.json`
   and record `footprint_persisted: true|false` (and `landing_sha_persisted`) as
   step facts in `records_facts`. This costs one read and converts a silent loss into
   an observable one without changing any failure disposition.
2. **Give the resolver a tier that does not depend on a write.** The plan records the
   PR number; the landing commit is derivable from it. A tier keyed on the PR number,
   or on `git log --grep "(#{pr})"` against the base branch, would have resolved this
   run's footprint exactly.
3. **Fix the legacy-key mismatch or document it.** Tier 4 reads `modified_files` while
   every live plan writes `affected_files`. Tier 4 is declared a shim for pre-ledger
   archives, so this may be correct as written — but it means the resolver holds a key
   that names the declared set and never consults it, which reads as a fallback and is
   not one.

## Evidence

- aspect: artifact_consistency — `affected_files_recall` / `affected_files_exact_match`
  both `inconclusive`; `footprint_resolved: false`, `declared: 8`.
- aspect: log_analysis — finding `ARTIFACT_COVERAGE_UNMEASURABLE: ... This is an
  unmeasured check, not a clean one.`
- artifact: `references.json` — carries `affected_files` (10 entries) and
  `plan_creation_sha`; carries neither `realized_footprint` nor `merge_commit_sha`.
- artifact: `status.json` — `branch-cleanup: outcome: done`.
- source: `plan-retrospective/scripts/_footprint_resolver.py` module docstring,
  tiers 1-5, and `resolve_merge_commit_footprint` / `read_legacy_footprint`.
- corroboration: `git show --no-patch --format="%H %P" 8025b2210` → single parent;
  `git diff 8025b2210^ 8025b2210` → the 10 realized files.

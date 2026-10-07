envelope_version=1
sender_type=plan
sender_id=correct-review-scores-as-maximally-wrong
epic=review-apparatus
kind=landing
created=2026-08-02T12:57:49Z

## What landed

Plan `correct-review-scores-as-maximally-wrong` — PR **#1078**, merging.

The run hardened the `automatic-review` participation/quality surface so that a review
score cannot read as clean when the underlying evidence is absent or contentless:

- **D1 contentless-review classification** — the `contentless_review_markers` predicate that
  identifies boilerplate-only bot output was repaired (see candidate-lesson 001). Iteration-2
  FIND confirmed the pre-fix drop originated in the predicate itself, not in dedup
  (`count_skipped_duplicate: 0`).
- **Participation evidence sidecar (TASK-4)** — `_has_update_movement` no longer reads its
  first-presence evidence out of the findings store, because the D1 contentless drop removes
  the comment from exactly that store. An observation sidecar now carries the evidence
  independently of the findings-store lifecycle (see candidate-lesson 002).
- **`automatic-review` argparse surface** — the shipped CLI now takes
  `--required-bots` / `--optional-bots` / `--participated-bots` / `--in-progress-bots` /
  `--refused-bots` and returns `participation_complete` / `unproven_bots` / `bot_states`.

## Review coverage on this PR — absent, not clean

This is epic-relevant residue, not a footnote:

- **coderabbit**: refused (awaitable window).
- **sourcery**: refused (hard quota).
- **pr-agent**: the only bot that saw the diff; its sole output was boilerplate that this very
  plan now classifies as noise.

The operator explicitly chose to proceed on pr-agent alone. The merge is therefore backed by
**one** reviewer whose only contribution this plan reclassifies as contentless. Any downstream
reading of "#1078 passed automated review" should be read as *one bot participated, zero
actionable review comments were produced* — not as *three bots reviewed and found nothing*.

## Self-review record

Four pre-submission self-review passes were configured. Passes 1, 2, and 3 **each found a
genuine defect** (a 3-for-3 hit rate — the ceiling was doing real work, not padding). The
4th pass was waived by the operator at the `max_iterations` ceiling, so the run terminated on
a budget boundary rather than on a clean pass. The clean-pass evidence this run has is
therefore *absent*, not *positive*.

## Residue the epic should track

1. **Unfixed doc-contract divergence** in `automatic-review/SKILL.md` — worth an epic item.
   Filed as candidate-lesson 005 with the exact drifted flag/field names.
2. **Leaf finding-persistence gap** — `pre-submission-self-review` pass 3 returned a finding in
   its TOON but never persisted it to the qgate store. Filed as candidate-lesson 006.
3. **Review-bot coverage** — two of three bots refused on this PR. The refusal causes
   (awaitable window, hard quota) are exactly the reliability surface this epic owns.

## Signals at finalize

`signal_qgate_pending_count=3`, `signal_automated_review_count=1`,
`signal_script_failure_clusters_count=0`.

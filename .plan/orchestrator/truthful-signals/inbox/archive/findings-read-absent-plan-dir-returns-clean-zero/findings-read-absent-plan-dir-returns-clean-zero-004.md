envelope_version=1
sender_type=plan
sender_id=findings-read-absent-plan-dir-returns-clean-zero
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T14:08:32Z

component=plan-marshall:manage-lessons
category=bug
disposition=new
severity=high
source_plan=findings-read-absent-plan-dir-returns-clean-zero
source_pr=1369

# A housekeeping step reported 12 lessons kept; one of them is now absent from the corpus under --status all, with no tombstone

## The evidence, in order

1. **2026-08-29T22:11:13Z** — this plan's `project:finalize-step-lessons-housekeeping` logged, to
   `decision.log`:

   > `(project:finalize-step-lessons-housekeeping) retained 2026-08-27-16-001: github_re_review head_sha_verified SHA-in-URL; 5cb0acac3 touches github_pr.py store refusal only, github_ops.py absent from the diff`

2. The step's recorded `display_detail` in `status.json` is
   **`"0 rm, 0 promo, 0 adapt, 12 keep (main_anchored corpus)"`** — zero removals, twelve kept.

3. **2026-08-30T14:0xZ**, from this retrospective:

   - `manage-lessons list` → `total: 11, filtered: 11` — `2026-08-27-16-001` absent.
   - `manage-lessons list --status all` → `total: 11, filtered: 11` — still absent. `--status all`
     includes `superseded` **and** `removed`, so this is not a lifecycle transition.
   - `manage-lessons get --lesson-id 2026-08-27-16-001` → `status: error, error: not_found`.

The lesson the step explicitly named as *retained* is gone, it is gone from the audit-inclusive
listing, and no tombstone surfaced for it. The step's own count (12) exceeds the corpus (11) by
exactly one — the missing lesson.

## What I can and cannot claim

I can claim: the lesson was present and named retained at 22:11:13Z on 08-29, and is unrecoverable
at 14:00Z on 08-30. The disappearance window is bounded by those two instants.

I **cannot** claim this run destroyed it. This retrospective made no mutating lessons call, and I
have not established which process removed it. Reporting a cause I did not observe would be the
same error this epic exists to remove.

## Why it is nonetheless high severity

Three properties compound:

- **Silent.** No tombstone, so `.tombstones/` — the mechanism whose entire purpose is to outlive
  the lesson it retired — has no record. A retirement without a tombstone is unauditable by design.
- **Self-certifying.** The step reported `0 rm` and `12 keep` and returned `outcome: done`. Its
  count was computed from a corpus that no longer matches it. Nothing reconciles the two.
- **Load-bearing content.** `2026-08-27-16-001` recorded that `github_re_review`'s
  `head_sha_verified` is blind to a SHA appearing inside a commit **URL** — and this dispatch's own
  brief states that defect was **CONFIRMED LIVE in this run**. So the corpus lost a lesson that had
  just been re-confirmed as live, on the day it was re-confirmed.

## The re-confirmed content, re-filed here because its lesson no longer exists

`github_re_review`'s `head_sha_verified` check treats a SHA occurring anywhere in the compared text
as a match, including a SHA embedded in a commit URL. A re-review can therefore be reported as
verified against the intended HEAD when it verified against a URL string that merely contains that
HEAD. The dispatch brief for this retrospective asked for *reinforcement* of `2026-08-27-16-001`
rather than a duplicate; reinforcement is impossible against a lesson that does not exist, so the
content is carried here instead.

## Remedy (for the epic to scope)

1. **Make the count derivable.** `finalize-step-lessons-housekeeping` should report the corpus size
   it observed *after* its own pass, not the count it intended to keep. A retention count that is
   never re-read against the store cannot detect its own divergence — the same shape this plan
   closed for the findings store.
2. **Close the tombstone-less deletion path.** Whatever removed this lesson bypassed the tombstone
   write. `remove` is documented as writing one unconditionally, so either a non-`remove` path
   deletes lesson files, or `remove` can fail after unlinking and before writing. Both are worth
   finding.
3. **Add a corpus-integrity check** that reads the lessons directory and the tombstone directory
   and reports ids present in neither — a lesson referenced by a prior run's log with no file and no
   tombstone is exactly the state observed here, and nothing currently detects it.

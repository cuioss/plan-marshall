envelope_version=1
sender_type=plan
sender_id=the-foreign-gate-population-and-branch-f-recovery
epic=review-apparatus
kind=candidate-lesson
created=2026-09-13T08:19:59Z

component=plan-marshall:automatic-review
category=improvement

# Three of five CodeRabbit inline findings were defects in the fix for its own previous finding

On PR #1473 CodeRabbit filed five inline findings across four review rounds. Three of
them were not defects in the plan's own work at all — they were defects in code that the
*previous round's remediation* had just introduced. The reviewer's actionable yield was
concentrated in re-checking its own remediations, not in the original diff.

## The three chains

| Round N finding | Round N+1 finding on the fix for it |
|---|---|
| `7c8de7` (Major) — `terminal_call_sites` merges every `mark-step-done` block in a label segment, so a sibling block's fact masks a missing `cleanup_owed` | `f9c945` (Major) — the fix (`c678e94d`) closed only the two-blocks-in-ONE-segment case; two *separate* `F2` segments still overwrite, because `_BRANCH_LABEL.finditer` yields two matches with the same `group(1)` |
| `ece98f` (round-1 nitpick) — the `('affected_files', 'mutation_scope', 'survey_scope')` key tuple is hand-copied at two consumers | `558161` (Major) — the fix introduced a shared `DECLARATION_FIELDS` constant whose own docstring requires it to be edited in step with `_DECLARATION_HEADINGS`, and nothing held it to that |
| `4634b3` (Minor) — `_DOCUMENTED` is a hand-maintained two-document list; derive the population from `_SKILLS` | `cfaa6b` (Minor) — the fix's new whole-tree `_documented_check_invocations()` caught `OSError` / `UnicodeDecodeError` and continued, so an unreadable document silently left the derived population |

Each remediation was itself good work — every one landed with a mutation control aimed at
the channel it closed — and each one still opened a new latent masking channel of the same
archetype it had just closed.

## Why this is a practice observation, not just a defect list

The re-review barrier is what caught all three. Had the run merged on the review that was
current when the last remediation was pushed, three Major/Minor defects introduced *by the
remediations* would have shipped, and the PR's review record would have read clean.
Concretely: **a review that predates the last remediation commit has not reviewed the
change that is about to merge**, and for this PR that gap was 60% of the reviewer's inline
yield. The barrier is not ceremony; on this run it was the majority of the value.

Corollary for cost reasoning: each extra round costs a full review-quota window (see the
sibling candidate on the three ~90-minute waits this PR paid). The observation above is the
counterweight — the rounds that look like pure overhead are where the findings were.

## Adjacent corpus entries for the orchestrator to dedup against

- `2026-09-04-08-013` — "Completeness was asserted again inside the fix for three
  asserted-completeness defects". Same recurrence archetype, observed on the self-review
  side. This candidate adds the *reviewer-cycle* half: the external reviewer is where the
  recurrence was caught, and only because review re-fired after each remediation.
- `2026-08-27-16-004` — "12 of 19 bot findings are one archetype the in-run self-review had
  already passed". Complementary, not duplicate: that one is about overlap with self-review,
  this one about a fix-of-a-fix chain.

Source: plan `the-foreign-gate-population-and-branch-f-recovery`, PR #1473 (merged
`38af136ede5c7d6ea531a38d59a67ece1bf3ade2`). Findings survive in that plan's archived
findings store under the hash ids above.

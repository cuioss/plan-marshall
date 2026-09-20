envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:28:25Z

# Candidate lesson: publishing an indeterminacy count is not enforcing it — the admission rule ignored `candidates_indeterminate`

## Signal source

PR #1539 CodeRabbit review-body finding `15ddea`, outside-diff item 1, against `plan-orchestrator/workflow/orchestrate.md:77-106`. Rated Major. Allocated TASK-025.

## Observation

The `next` admission rule's disjointness predicate consumed two signals: the candidate's declarative surface, and the **absence** of a `file_overlap_matches[]` row. It never consumed `candidates_indeterminate`.

So a declarative plan with no overlap row could be **emitted as admissible while another candidate was never comparable at all**. The cross-check implementation *published* the indeterminacy count faithfully; nothing *read* it. The bot's phrasing of the gap is the useful part: *"The cross-check implementation only publishes this count; the `next` admission rule is the enforcement point."*

A sibling finding in the same run (`4f4183`) is the producer-side twin: `candidates_indeterminate` was documented as counting only reads-with-no-comparable-surface, but was computed over `CANDIDATE_NON_CONTRIBUTING_STATES` (indeterminate + unreadable), so a 3-unreadable / 0-indeterminate corpus reported `candidates_indeterminate: 3` — asserting three reads that never happened.

## Corrective rule

1. **A published caveat count has no effect until a decision point consumes it.** Emitting `*_indeterminate`, `*_unreadable`, `*_skipped` alongside a verdict is necessary but not sufficient; the gate that acts on the verdict must branch on the caveat, or the caveat is decoration.
2. **When adding an indeterminacy count to a producer, name its enforcement point in the same change.** Otherwise the count's presence makes the system *look* honest while behaving exactly as it did before.
3. **An absence-of-evidence predicate ("no overlap row was found") must be paired with a determinacy predicate ("and every candidate was comparable").** The first alone cannot distinguish "no conflict" from "not checked" — the same confident-zero shape this epic exists to close.

## Why this is a strong epic-level candidate

The two halves together (a count computed over the wrong population, and a gate that ignores the count) show the failure is not a single oversight but a missing convention: the codebase has no established pattern binding a caveat count to its enforcement site, so each new instrument re-invents — or omits — the binding.

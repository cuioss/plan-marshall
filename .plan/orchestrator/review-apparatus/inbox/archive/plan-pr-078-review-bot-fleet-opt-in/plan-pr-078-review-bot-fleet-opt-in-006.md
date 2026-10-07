envelope_version=1
sender_type=plan
sender_id=plan-pr-078-review-bot-fleet-opt-in
epic=review-apparatus
kind=candidate-lesson
created=2026-10-06T22:21:57Z

component=plan-marshall:manage-references
category=improvement

# Give foreign-repository paths their own class in the declared footprint

## Context

Plan `plan-pr-078-review-bot-fleet-opt-in` was a fleet rollout: 9 of its 10 deliverables edited other repositories and one edited plan-marshall. Its declared footprint holds 64 modification-intent paths, 50 of them absolute paths under other checkouts (`/Users/oliver/git/{repo}/...`). The realized footprint the shared resolver recovers is the host diff, 14 files. Three retrospective checks compared the two and reported failure: artifact-consistency `affected_files_recall` failed at 22 percent against a 70 percent bar, manifest rule M6 failed on 50 declared-but-unrealized paths, and outline-vs-shipped reported 56 of 70 `CERTAIN_INCLUDE` paths as `include_unrealised`. Much of the work those paths describe did ship - 9 plan-authored foreign PRs merged (7 opt-in PRs, the org npm-guard PR, the coderabbit comment fix) - and is recorded only in free-text `[OUTCOME]` lines.

## Root cause

The footprint model has one population, "files this plan will modify", and one evidence source, the host worktree diff. A path outside the host repository can be declared but can never be realized, so every declared-vs-realized comparison counts it as a miss by construction. The same gap showed up earlier in the lifecycle: phase 4 had no documented handling for the four foreign modules and resolved them through a non-blocking "profile unresolved" path with four Q-Gate findings closed as `taken_into_account`; the lessons consult at outline matched nothing because no foreign path maps to a component.

## Proposed action

- Record foreign-repository paths under their own key in the declared footprint (a third class beside modification-intent and read-intent), keyed by repository.
- Have the declared-vs-realized consumers (`affected_files_recall`, manifest rule M6, outline-vs-shipped `include_unrealised`) exclude that class from their denominators and publish its size beside the count, so a zero or a low ratio stays attributable.
- Give foreign work a structured realization record - one row per repository with PR number and merge state - so a retrospective can grade it instead of reading `[OUTCOME]` prose.
- Document the foreign-module path in `phase-4-plan` so it is not re-derived per plan.

## Evidence

- aspect: artifact-consistency - `affected_files_recall` fail, "Recall 22% below 70% threshold", declared 64, found 14
- aspect: manifest-decisions - `declared_vs_realized_set` fail, 50 declared-but-unrealized, 0 realized-but-undeclared; every culprit path is outside the host repository
- aspect: outline-vs-shipped - `include_unrealised` 56 of 70; `touched_but_unassessed` 0 of 14; `exclude_violated` 0 of 11
- aspect: request_result_alignment - file coverage not applicable to 9 of 10 deliverables; graded on task status plus merged foreign PRs instead
- aspect: logging_gap_analysis - 2 of 2 change-qualified tasks emitted `[ARTIFACT]` lines; the 9 foreign-only tasks are outside the eligible set, so no artifact line records any foreign PR
- phase-4 hand-back: "The workflow document should say how foreign modules are handled"

envelope_version=1
sender_type=plan
sender_id=build-gates-test-suite-confidence-ci-workflow-lint
epic=truthful-signals
kind=candidate-lesson
created=2026-08-25T14:58:44Z

# Deleting interior prose re-points pronouns — deletion is not a safe rewrite

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern
confidence=high
source=plan-retrospective
source_plan=build-gates-test-suite-confidence-ci-workflow-lint

## Context

Round 2 of this plan's self-review adopted an explicit convergent-resolution heuristic, stated in the findings themselves: resolve by DELETION rather than rewrite, because "a rewrite authors the next round's finding". The heuristic was adopted precisely to escape the self-seeding that round 1's rewrites had caused.

It caused round 3 in one hop. Round 2's deletions removed the sentences sitting BETWEEN a subject and a later pronoun:

- `build-api-reference.md` — deleting the two intervening sentences moved the antecedent of "the value published" from `run` to `parse`. Daemon routing exists only on the `run` verb, so the surviving sentence became false (`c33703`).
- `_build_format.py` — the same deletion pattern moved the antecedent of "It is emitted ONLY when the count was measured" from the `tests_run` whitelist entry to parse's `metrics.tests_run`. `cmd_parse_common` publishes that key unconditionally, so the surviving sentence became false (`57f8a4`).

Both damaged sentences were individually untouched by the diff.

## Root cause

Deletion is treated as strictly safer than rewriting because it removes claims rather than authoring them. That reasoning holds for the deleted text and fails for its neighbours: prose is not a set of independent claims but a referential chain, and removing a link re-binds every pronoun downstream of it. The failure is invisible to the review that would catch it, because the review reads the diff, and the newly-false text is exactly the text the diff does not contain.

## Proposed action

Two changes, both cheap:

1. **Qualify the heuristic where it is stated.** "Resolve by deletion" must carry the caveat that deleting interior text obliges a re-read of the surviving neighbours for antecedent drift — it is not the safe default the current phrasing implies.
2. **Add the deleted-neighbourhood re-read to the round's own checklist.** After any deletion of interior prose, re-read the surviving sentences immediately before and after the deletion point AS THEY NOW STAND (not as the diff shows them) and check every pronoun and every definite reference against its new nearest antecedent.

This generalizes past self-review: the same failure applies to any doc edit that removes a paragraph from the middle of a section.

## Evidence

- qgate finding `c33703` — "Round 2's deletion removed the two sentences that sat between the parse-verb sentence and the daemon-routed sentence, moving the latter's antecedent from 'run' to 'parse'"
- qgate finding `57f8a4` — "Same root cause and same class as c33703, in the sibling file"
- Round 2's own findings (`383a70`, `a61ed7`, `31de1f`, `a228e0`) each prescribe deletion over rewrite, citing re-seeding as the reason to prefer it
- aspect: chat_history_analysis — the settle band consumed the raised loop-back budget (ceiling 3 -> 8, 6 iterations spent)

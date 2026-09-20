envelope_version=1
sender_type=plan
sender_id=review-packs-become-published-artifacts
epic=review-apparatus
kind=candidate-lesson
created=2026-09-03T22:43:44Z

# Argparse rejections cluster on flag names transferred from a sibling verb

component: plan-marshall:script-shared
category: improvement
confidence: high

## Context

Nine distinct script notations failed during this plan. A substantial share are argparse exit-2 rejections in one recognisable shape: the caller used a flag or verb that is real and correct on a SIBLING surface, but not on the one it invoked.

Observed instances:

- `automatic-review:review_completeness --pr-number`
- `manage-status get-phase-steps`
- `manage-execution-manifest read --phase`
- `manage-findings qgate list --status` (canonical: `--resolution`)
- `manage-architecture:architecture search --path-glob` (canonical: `find --pattern` for a path glob, `search --content --pattern` for a body match)

This lessons-capture dispatch reproduced the shape a sixth time before finishing, issuing `manage-findings list --format json` — a flag that exists on other scripts in the corpus and not on that verb.

## Root cause

This is NOT the verb-paraphrase signature already filed in this inbox for `manage-solution-outline` (candidate 004), where the skill's own description wording generated an unregistered verb out of nothing. Here the invented token is a REAL token borrowed across a boundary: `--status` / `--resolution` and `--pattern` / `--path-glob` name the same concept under different spellings on adjacent verbs, and `--phase` is declared on some verbs of a script and not on others. The vocabulary is inconsistent across siblings, so a caller who has correctly learned one verb's surface predicts the next one wrong.

The rejection messages are good — `manage-findings` printed its full accepted flag set on rejection — so the cost is one wasted call per occurrence. But it recurred across five separate notations in a single plan, plus once more inside this step's own dispatch, which makes it structural rather than incidental.

## Proposed action

Audit the flag vocabulary across sibling verbs of the same script and across scripts sharing a concept, and converge the spellings. The `argument-naming` standard already owns `--resolution` and the typed-ID flags; extend the same treatment to the `--pattern` family and to per-verb `--phase` presence.

Where convergence would break a caller, register the sibling's spelling as an argparse alias — the carve-out already granted to the accepted read-verb aliases (`manage-lessons read`, `manage-tasks get`, `manage-status get`).

Publish, per verb, the accepted flag set adjacent to the canonical-invocation block, so a caller can read the surface without a `--help` round trip.

## Evidence

- `signal_script_failure_clusters_count: 9` distinct notations this run
- The five instances above, each a real token on a neighbouring surface
- One further instance produced by this step's own dispatch — direct evidence that the pressure survives the current guidance
- `agent-behavior-rules` already names `--resolution`-vs-`--status` as recurrence signature 5, and it recurred anyway, which argues the remedy belongs on the script surface rather than in further caller-side exhortation

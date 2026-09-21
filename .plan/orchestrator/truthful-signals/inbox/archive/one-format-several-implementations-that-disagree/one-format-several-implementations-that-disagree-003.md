envelope_version=1
sender_type=plan
sender_id=one-format-several-implementations-that-disagree
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T18:41:48Z

category=anti-pattern
component=plan-marshall:plan-retrospective
title=A failing coverage gate whose denominator is contaminated

## Observed

`check-artifact-consistency` reported, in this plan's own retrospective:

```text
affected_files_recall,fail,Recall 57% below 70% threshold
  declared: 30
  found: 17
  recall_pct: 56.7
```

A confident red gate with a crisp number. Reading the `missing[]` list it publishes
alongside, **six of the ten "missing declared files" are not files**:

```text
- Best practice — A review-bot finding already satisfied in the current tree is dispositioned
- Best practice — Review-bot style nits on test fixtures in this module are routinely declined under
- Insight — Q-Gate findings are a standing consideration in this project: expect them to be folded
- Insight — This project records improvement findings and anti-pattern findings against the corpus
- No tips, insights or best practices recorded for this module.
- Tip — Whole-tree coverage is an orchestrator-tier build the harness kills; scope local coverage to
```

These are **lessons-consult narrative bullets** from the solution outline, parsed
as declared-file entries. They inflate the denominator from ~24 to 30 and drag the
ratio from roughly 71% (above threshold) to 56.7% (below it).

The genuinely missing files are four, not ten — three GitHub/GitLab provider
scripts and one test — and that is a real, much smaller scope observation worth
its own look.

## Why this is the epic's own archetype

`truthful-signals` exists for signals that are confident about something they have
not established. This one is sharper than most because it fails **loudly**: a red
gate invites action, and the action it invites (go find 13 missing files) is partly
chasing prose bullets that were never files. A silent wrong number invites nothing;
a loud wrong number spends someone's afternoon.

Note also that the same parser drives `affected_files_exact_match`, whose
`outline_only[13]` list carries the same six prose entries — so the contamination
reaches two checks from one parse.

## The generalisable rule

**A ratio is only as trustworthy as the membership predicate that built its
denominator.** When a gate reports a failing percentage, the first question is not
"which items are missing" but "is every item in the denominator actually of the
kind being counted". Publishing the population — which this check does, and which
is what made the defect visible in one read — is the property that makes the
question answerable at all. That publication requirement is already project
doctrine for set-guarding detectors; this case shows it earning its keep on the
denominator side rather than the numerator side.

## How to apply

Fix the declared-file parser to exclude lessons-consult bullets (they are
recognisable: they open with `Tip — `, `Insight — `, `Best practice — `, or the
literal no-lessons sentence). Until then, read a failing `affected_files_recall`
against its own `missing[]` list before acting on the number.

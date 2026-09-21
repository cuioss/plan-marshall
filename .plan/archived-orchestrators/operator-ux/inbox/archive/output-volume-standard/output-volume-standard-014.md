envelope_version=1
sender_type=plan
sender_id=output-volume-standard
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T16:08:58Z

component=plan-marshall:manage-plan-documents
category=anti-pattern

# Verb-paraphrase rejection on manage-plan-documents inside the wait-region triage envelope

## Observation

During the wait-region unified triage step, a call to `plan-marshall:manage-plan-documents:manage-plan-documents` was rejected with exit 2:

```
failure_kind=argparse_rejection
detail=Use a registered verb for `plan-marshall:manage-plan-documents:manage-plan-documents`: ['list-types', 'request']
```

The script's whole top-level surface is two verbs. `request` is a NOUN carrying its own sub-verbs (`request read --plan-id X --section Y`), so the natural-reading shape — a top-level `read` — does not exist. This is recurrence signature 1 (verb-paraphrase) from the standing "Never invent script subcommands" rule: the invented verb reads correctly in workflow prose and is absent from the argparse `choices`.

## Recommended rule

The rule already exists and was violated anyway, so the remedy is structural rather than exhortative. Two candidates:

1. `manage-plan-documents` has an unusually small and unusually noun-shaped surface (two verbs, one of which is a noun with sub-verbs). Every consuming workflow that documents a read against it should carry the full `request read --plan-id {plan_id} --section {section}` form inline, not a paraphrase — the `lessons-capture` workflow body already does this and explicitly warns that "`manage-plan-documents`' only top-level choices are `{list-types, request}`". The warning exists because the mistake recurs; check whether the OTHER consumers carry it.
2. The rejection message is already good (it enumerates the registered verbs). Consider having it also name the noun's sub-verbs when the invented token matches a sub-verb of a registered noun, so the caller is handed the fix rather than the enumeration.

## Evidence

- Plan: `output-volume-standard` (epic `operator-ux`)
- Work log 2026-09-03T09:58:50Z, inside `execution-context.wait-region-unified-triage`
- One of 4 distinct failing script notations on this run

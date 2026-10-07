envelope_version=1
sender_type=plan
sender_id=freshness-gate-says-fresh-unexamined-tree
epic=truthful-signals
kind=candidate-lesson
created=2026-09-06T17:33:33Z

# Candidate lesson: four argparse rejections in one finalize run, all on CORRECT verbs with the wrong flag SET

## Proposed component

`plan-marshall:script-shared` (the cross-surface argparse-discipline home), with consumer-side
remedies owed by `plan-marshall:tools-integration-ci`,
`plan-marshall:workflow-integration-github`, and `plan-marshall:workflow-integration-git`.

Category: `anti-pattern`.

## Observation

A single `6-finalize` run produced four distinct argparse rejections. Not one of them was an
invented verb — every verb name was correct and every call reached the right subparser. All four
failed on the **flag set**, and they failed in **both directions**:

| Call as issued | Fault direction | Live declaration (verified via `--help` at HEAD) |
|---|---|---|
| `ci pr prepare-comment --pr-number N` | supplied a flag the verb does not declare | `--plan-id` (REQUIRED), `--for {reply,thread-reply}`, `--slot` — and nothing else |
| `github_re_review re-review` without `--push-time` | omitted a REQUIRED flag | `--pr-number`, `--bot-kind`, `--head-sha`, `--push-time` all required |
| `git-workflow switch-and-pull` without `--base` | omitted a REQUIRED flag | `--base` required; `--plan-id` / `--project-dir` optional |
| `git-workflow prune-local-and-remote-ref --branch X` | supplied a plausible synonym for a declared flag | the declared name is `--head`, not `--branch` |

Each is a disagreement between what a workflow doc (or the caller's model of a sibling verb)
prescribes and what the live parser declares.

## Why the existing guards did not catch this class

Three guards already exist near this space, and each one misses these four:

1. **`persona-plan-marshall-agent` § "Never invent script subcommands — recurrence signatures"**
   is framed around inventing a *verb*. Its five signatures cover verb-paraphrase, `--plan-id` /
   `--project-dir` placement on two surfaces, a doubled bundle prefix, and — signature 5 — a
   missing required `--phase` plus `--resolution`-vs-`--status`. Signature 5 is the only one
   pointing at the omission direction, and it is scoped to the *findings* verbs by name. Nothing
   states the general class: **a correct verb can be rejected for its flag set alone, in either
   direction.**

2. **Lesson `2026-09-04-08-014`** ("Argparse rejections cluster on flag names transferred from a
   sibling verb") captures the *transfer* mechanism. It reaches rows 1 and 4 above. It does not
   reach rows 2 and 3 at all — a required flag the caller never knew existed is not a name
   transferred from anywhere.

3. **Lesson `2026-09-03-23-005`** ("The router-flag placement hint fires only when the flag
   exists, staying silent on the undeclared case") is the closest structural match to rows 1 and
   4: the helpful placement hint is exactly what does NOT fire when the flag is undeclared, so
   those two rejections arrived as a bare `unrecognized arguments` with no remedy attached.

The gap is therefore real and it is a *class* gap, not four unrelated incidents.

## Why the recurrence count is the signal

Four rejections in one run, across three different bundles, is not caller carelessness that a
sharper reminder fixes. It is evidence that the **doc-to-parser agreement is unverified for flag
sets**, while it IS verified for verb names: the `ARGUMENT_NAMING_*` plugin-doctor cluster and
`manage-invocation-invalid` derive their accept-set from a live `--help` walk, but the observed
failures show the flag-level half of that surface is not closing these cases in practice.

## Suggested direction (for the orchestrator to judge, not a decided remedy)

- State the class explicitly wherever the verb-invention rule already lives: a rejection can come
  from the flag set on a perfectly correct verb, and it has two directions — **undeclared flag
  supplied** and **required flag omitted**. The self-audit move is the same for both: read the
  verb's own `--help` (or its Canonical-invocations block) and diff the flag set in *both*
  directions before issuing the call, rather than checking only that the verb name exists.
- Consider extending the placement-hint mechanism so the **undeclared** case also emits a remedy
  (lesson `2026-09-03-23-005` already names this hole); rows 1 and 4 would both have been
  self-correcting had it fired.
- Consider whether the finalize workflow docs that prescribe these four calls carry flag sets that
  still match the live parsers — the four rejections are the observable end of that question, and
  a doc sweep is cheaper than a fifth incident.

## Provenance

Signal source: `signal_script_failure_clusters_count` for plan
`freshness-gate-says-fresh-unexamined-tree`. Each live declaration in the table above was
re-verified against HEAD by invoking the verb's own `--help` during this step; none is quoted from
a doc.

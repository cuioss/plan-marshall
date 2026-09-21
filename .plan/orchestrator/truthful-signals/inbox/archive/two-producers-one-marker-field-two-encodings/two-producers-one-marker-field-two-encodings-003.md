envelope_version=1
sender_type=plan
sender_id=two-producers-one-marker-field-two-encodings
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T04:55:35Z

component=plan-marshall:finalize-step-review-retrospective
category=bug
confidence=high
source_plan=two-producers-one-marker-field-two-encodings
source_pr=1125
suggested_epic=review-apparatus
delegation_note=PR/review-shaped — belongs to review-apparatus under the standing three-way routing rule. Emitted here because a dispatched leaf writes only to the epic it was dispatched under; forward via the inbox channel rather than a direct edit.

# Self-review findings are queried at 5-execute but filed at 6-finalize, so absence is inferred from the wrong phase

## Context

`review-retrospective.md` closes with a structural claim about the review pipeline:

> **This retrospective could not substantiate that figure** — the findings store holds
> no `bug`, `improvement`, or `anti-pattern` records for this plan, and `qgate list
> --phase 5-execute` returns zero.
>
> ... **self-review output leaves no trace in the findings store, so it is invisible
> to this retrospective by construction.** ... A review comparison that cannot see the
> cheapest reviewer in the pipeline is comparing an incomplete field.

The claim is false, and the evidence cited is a non-observation. The self-review
findings exist. `qgate list --phase 6-finalize` returns two records:

- `a7d905` — "contract_drift: single-read-site claim omits the generated-executor
  duplicate", `source: qgate`, `component:
  pm-plugin-development:ext-self-review-plan-marshall`, resolution `fixed`
- `e26682` — "contract_drift: existence-only test is blind to the template read site",
  same source and component, resolution `fixed`

Both carry full detail and a resolution narrative. Both are exactly the "real defects
found by self-review" the step reported it could not substantiate.

## Root cause

`pre-submission-self-review` is a **phase-6-finalize** step. Its Q-Gate findings are
therefore written to `artifacts/findings/qgate-6-finalize.jsonl`. The retrospective
queried `--phase 5-execute`, which is where execution-time findings live.

`qgate-5-execute.jsonl` does not exist for this plan at all — the artifact manifest
lists `qgate-2-refine`, `qgate-3-outline`, `qgate-4-plan` and `qgate-6-finalize`, and
no 5-execute file. So the zero was not a measurement over an empty population; it was
a read of a file that is not there. A could-not-look was rendered as a
proved-absent, and then generalised into a claim about the pipeline's construction.

The one-line remedy the step already had available: `manage-findings list --plan-id X
--include-qgate` merges pending Q-Gate findings across **every** phase, which is the
read surface that makes a phase guess unnecessary.

## Proposed action

- Query self-review findings at the phase that produces them (`6-finalize`), or
  better, drop the phase guess entirely and use `list --include-qgate`, which spans
  all phases by design.
- Filter by the producing component (`pm-plugin-development:ext-self-review-*`) rather
  than by finding type. The step looked for `bug`/`improvement`/`anti-pattern` in the
  per-plan store; self-review files Q-Gate findings, which is a different store and a
  different verb.
- Do not derive a structural claim ("by construction") from a single empty read.
  Where a query returns zero, report whether the queried population existed. A zero
  from a non-existent phase file and a zero from an empty phase file are different
  facts and only one of them supports a conclusion.

## Evidence

- artifact: `review-retrospective.md` § "Comparator: the plan's own pre-submission
  self-review" — the claim, and the `qgate list --phase 5-execute` zero it rests on
- first-party: `manage-findings qgate list --phase 6-finalize` returns
  `total_count: 2` — findings `a7d905` and `e26682`, both `source: qgate`, both
  `component: pm-plugin-development:ext-self-review-plan-marshall`
- first-party: `manage-findings qgate list --phase 5-execute` returns
  `total_count: 0`
- artifact manifest: `artifacts/findings/` contains `qgate-2-refine.jsonl`,
  `qgate-3-outline.jsonl`, `qgate-4-plan.jsonl`, `qgate-6-finalize.jsonl` — there is
  no `qgate-5-execute.jsonl`
- `status.metadata.phase_steps["6-finalize"]["pre-submission-self-review"]` —
  outcome `done`, confirming the step ran in phase 6, not phase 5
- `manage-findings` SKILL.md § "Unified read surface (--include-qgate)" — the
  all-phase read the step could have used instead

envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:53:20Z

component=plan-marshall:manage-status
category=bug
proposed_title=A lane-routing plan self-sealed: the scorer counted its own spec's boilerplate citation as the only target path

# A lane-routing plan self-sealed: the scorer counted its own spec's boilerplate citation as the only target path

## What happened

The plan `lane-router-reads-the-wrong-body` exists to fix the scope-estimate/planning-lane scorer. At its own `phase-1-init`, that same scorer ran on that same plan's request and produced:

```text
distinct_path_count = 1
```

The one counted path was `persona-marshall-orchestrator/standards/orchestration-model.md` — the **plan-spec template's boilerplate citation**, not a target of the work. Every real target (`_cmd_planning_lane.py`, `manage-status.py`, `manage-status/SKILL.md`, `phase-1-init/SKILL.md`) was missed.

Downstream verdict: `planning_lane=light`, `execution_profile=minimal`. A light-lane, minimal-profile run on a plan whose deliverable was a multi-file scorer rewrite plus a 311-line new regression suite.

Only a **manual operator escalation to `deep`** prevented that route. `status.json` records `lane_escalated: true, escalation_trigger: premise`.

## Why it matters (the archetype)

This is the **self-sealing defect**: a component whose defect is *in the detector* will, by construction, fail to detect the work that fixes it. The confident output (`planning_lane: light` with a clean count) hides the caveat that the count was computed over the wrong text. Same shape as the spec's Seventh Instance.

It is also the recurring **volume-read-as-coverage** inversion in miniature: `distinct_path_count=1` is a *count of what the parser found*, never a *count of what the request targets*, and nothing in the pipeline distinguishes the two.

## The rule

- A plan that targets a routing/scoring/detection component MUST NOT accept that component's own verdict about itself. Treat the self-run output as **untrusted** and route the lane decision by explicit operator judgement or by a counterfactual computed outside the component under repair.
- More generally: whenever a plan's deliverable is component X, any signal produced by X about that plan is evidence of X's defect, not evidence about the plan.
- A path-counting heuristic must distinguish **cited** paths (references, templates, boilerplate, prior-art links) from **targeted** paths. A citation is not a target. Without that distinction the count is unfalsifiable in exactly the cases that matter.

## Detection

Look for a plan whose `metadata.lane_escalated == true` with `escalation_trigger: premise` — that is the fingerprint of a human catching a router that was about to under-route. Every such record is a near-miss the router should have caught itself.

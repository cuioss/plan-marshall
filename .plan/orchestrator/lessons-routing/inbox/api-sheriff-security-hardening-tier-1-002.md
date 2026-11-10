envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-security-hardening-tier-1
epic=lessons-routing
kind=candidate-lesson
created=2026-11-09T11:45:56Z

component=plan-marshall:phase-6-finalize
category=bug
title=Finalize docs name verbs the scripts do not register (review_completeness roster, manage-logging signal-scan) and an explicit off lane reported as binding is not applied under the full posture

# Finalize docs name verbs the scripts do not register, and an explicit `off` lane reported as binding is not applied

Source: API-Sheriff epic `security-hardening-tier-1`, inbox messages `plan-sec-03-pending-authorization-store-fairness-001.md` and `-005.md` (plan `plan-sec-03-pending-authorization-store-fairness`, PR cuioss/API-Sheriff#581, 2026-11-09). Clustered here because all three are the same class: a documented control or verb that the scripts do not carry out.

## Observations

1. **`review_completeness roster` is documented but not registered.** The dispatched review agents followed their workflow docs and called `review_completeness roster` for the required/optional review-bot roster. argparse rejected it (exit 2). The agents improvised a fallback the doc does not sanction: they read `required_bots` / `optional_bots` from `manage-execution-manifest step-params get --phase 6-finalize --step-id automatic-review`, which held the correct values.
2. **`manage-logging signal-scan` is documented but not registered.** `workflow/lessons-capture.md` says the script-failure-cluster count "is computed by `manage-logging signal-scan --plan-id {plan_id}`". The executor rejects it with `unknown_verb` (accepted: `decision, read, script, separator, work`). The only route left is `manage-logging read --type work`, which returned 7106 entries (1.2 MB) for this plan. Nothing narrows it by marker or phase: `--phase` is accepted but did not filter the work log.
3. **An explicit `off` lane is reported as binding but not applied.** The manifest carried `lane_requested: off` for `adr-propose` and `lessons-capture`. `lanes preview --plan-id` reported both as `declared=off effective=off binds=true` ("explicit 'off' override opts this prunable element out"). Yet both stayed in the composed `phase_6.steps`, because `execution_profile: full` short-circuits lane resolution. The dispatcher has no documented rule for which signal wins.

## Why it matters

- A documented verb that argparse rejects is the verb-paraphrase / doc-drift class. Every dispatch pays a failed call and then improvises, and the "never invent script subcommands" rule is undermined when the doc itself is the source of the invented verb.
- A signal gate whose documented computation cannot run forces every finalize run to improvise the count or skip it.
- An override reported as binding but not applied is a declared-but-not-in-force control: neither surface tells the operator whether the step will run.

## Suggested correction (from the reporting plan)

- Implement `review_completeness roster`, or remove it from the review workflow docs and name `step-params get` as the sanctioned roster read.
- Register `manage-logging signal-scan`, or correct the doc to the actual computation. Either way, give `read` a working marker/phase filter.
- Bring the documented invocations into the `manage-invocation-invalid` plugin-doctor accept-set check, so a documented-but-unregistered verb fails the quality gate.
- Apply an explicit `off` on a prunable element under the `full` posture too, or have `lanes preview` report `binds=false` with the reason "full posture keeps every candidate". State in `phase-6-finalize/SKILL.md` how the dispatcher treats a scheduled step whose effective lane is `off`.

envelope_version=1
sender_type=plan
sender_id=a-refusal-is-recorded-as-a-refusal-the-record
epic=review-apparatus
kind=candidate-lesson
created=2026-08-31T08:18:11Z

component=plan-marshall:plan-retrospective
category=bug
title=script-failure-analysis reads only stderr, so an executor rejection whose note is on stdout reads as no note at all

# script-failure-analysis reads only stderr, so an executor rejection whose note is on stdout reads as no note at all

## Context

`script-failure-analysis.py` publishes exactly one evidence field per failure signature: `stderr_excerpt`. For plan `a-refusal-is-recorded-as-a-refusal-the-record` it recorded 17 failures across 10 signatures, and **8 of the 10 carry an empty `stderr_excerpt`**. The two that carry a populated one — `architecture search` (`invented_flag`) and `ci pr` (`invented_flag`) — are the two where the *target script's own argparse* rejected the call and wrote usage to stderr.

The empty eight are not silent. They are the executor-layer rejections, and the executor emits a rich corrective envelope for them — on **stdout**.

## The evidence is a matched pair observed in this very step

This candidate was produced by the `lessons-capture` step of the same plan, which reproduced the class live. A deliberate wrong-flag call (`manage-files list --subdir work`) returned exit 2 with:

```text
status: error
error: invalid_invocation
notation: plan-marshall:manage-files:manage-files
reason: unknown_flag
rejected: --subdir
accepted: dir, plan-id
message: Use `--dir` for `plan-marshall:manage-files:manage-files list` — declared: ['dir', 'plan-id']
```

`script-execution.log` recorded that call as:

```text
[2026-08-31T08:12:56Z] [ERROR] [66ea25] plan-marshall:manage-files:manage-files list (0.00s)
  exit_code: 2
  args: list --plan-id ... --subdir work
  stdout: status: error error: invalid_invocation ... message: Use `--dir` ... declared: ['dir', 'plan-id']
```

A `stdout:` continuation line carrying the accepted-flag list, and **no `stderr:` line at all**. An analyzer whose only evidence field is `stderr_excerpt` is blind to that whole channel by construction — so for every executor-layer rejection it reports empty, and empty is read as "nothing was emitted".

## Why this is a defect and not a cosmetic gap

The empty field was consumed as positive evidence. This plan's candidate-lesson message `-007` states, of the 7× `manage-solution-outline read` rejection:

> "The `manage-solution-outline read` failures carry an **empty** `stderr_excerpt`, so the caller got no such steer."

That inference does not hold. The steer may well have been emitted, on the channel the field cannot see — and the executor's `invalid_invocation` envelope names the accepted flag set, which is exactly the steer `-007` concludes was absent. `manage-solution-outline read --plan-id {plan_id}` was re-run during this step and returns `status: success`, so the accepted form exists and the rejections were a wrong flag against a live verb. Whether the caller got no note, or got one and re-issued anyway, is **not established** by the recorded evidence — and those two have opposite remedies (add a corrective note vs. make the emitted note reach the caller).

The archetype is the epic's own: an absent read presented as a measured zero. An empty `stderr_excerpt` today means *either* "no diagnostic" *or* "diagnostic on the channel I do not read", and nothing in the fragment distinguishes them.

## Proposed action

1. Have `script-failure-analysis.py` parse the `stdout:` continuation of `[ERROR]` entries in `script-execution.log`, not only `stderr:`.
2. Publish a `diagnostic_channel` discriminator per signature — `stderr` / `stdout_envelope` / `none` — so "no corrective note was emitted" becomes a **measured** verdict instead of the default reading of an unread field. Rename or pair the field accordingly (`diagnostic_excerpt` + `diagnostic_channel`).
3. When the channel is `stdout_envelope`, surface the envelope's `accepted` / `message` values on the row: those name the fix, and a repeated signature whose corrective note WAS emitted is a materially different (and more interesting) defect than one where it was not.
4. Re-read message `-007` against the corrected evidence before acting on it — its observable (7 rejections of one form, the largest repeated failure in the plan) stands; its stated cause does not.

## Evidence

- artifact: `work/fragment-script-failure-analysis.toon` — `total_failures: 17`, `unique_failures: 10`; 8 of 10 rows carry `stderr_excerpt: ""`
- log: `script-execution.log` `[2026-08-31T08:12:56Z] [ERROR] [66ea25]` — a `stdout:` continuation carrying the `invalid_invocation` envelope, no `stderr:` line
- source: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/script-failure-analysis.py` — `stderr_excerpt` is the only evidence field emitted
- live re-run: `manage-solution-outline read --plan-id a-refusal-is-recorded-as-a-refusal-the-record` returns `status: success`, so the verb accepts a form the 7 rejected calls did not use
- prior message: this epic's inbox `-007`, whose causal clause this candidate qualifies

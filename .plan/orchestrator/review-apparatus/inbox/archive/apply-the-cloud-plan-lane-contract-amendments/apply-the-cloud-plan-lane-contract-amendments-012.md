envelope_version=1
sender_type=plan
sender_id=apply-the-cloud-plan-lane-contract-amendments
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T06:29:21Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-09-05

# The argparse loss concentrates in the read-only reporting steps, not in the work

## Observation

Distributing this run's eighteen argparse rejections over the timeline shows they are not spread
across the plan — they cluster hard in the **post-run-review band**, in steps that write no
source and exist only to read and report.

| Band | Window (UTC) | Rejections | Notations involved |
|---|---|---:|---|
| outline + plan | 12:19 – 12:39 | 3 | `manage-config` ×2, `manage-solution-outline` |
| execute / CI checks | 13:48 | 2 | `ci` ×2 |
| pre-submission-self-review | 15:13 | 1 | `architecture` |
| automatic-review | 21:41 | 1 | `github_pr` |
| **`finalize-step-review-retrospective`** | 02:19 – 02:22 | **4** | `manage-execution-manifest`, `manage-status` ×2, `ci` |
| **`plan-retrospective`** | 06:09 – 06:10 | **3** | `manage-findings` ×2, `manage-solution-outline` |
| **metrics / qgate wrap-up** | 06:22 – 06:23 | **4** | `manage-metrics` ×2, `manage-findings` ×2 |

**11 of 18 rejections (61%) fall after 02:19**, inside the two post-run-review steps and the
metrics wrap-up that follows them. The eight tasks of actual implementation work
(TASK-001…TASK-008, 13:12–00:15) produced **zero** rejections between them.

## Why the reporting steps are the hot spot

A reporting step's job is to fan out across surfaces it does not otherwise touch. In one window
`finalize-step-review-retrospective` called `manage-execution-manifest`, `manage-status` (twice),
and `ci` — four notations, four rejections, in 3 minutes 49 seconds. `plan-retrospective` and the
metrics wrap-up did the same across `manage-findings`, `manage-solution-outline`, and
`manage-metrics`. An implementor step calls two or three scripts repeatedly and learns their
surfaces; a reporting step calls eight scripts once each and has learned none of them.

That is a structural property of the role, not a property of these two step bodies.

## Proposed corrective action

Aim the remedy where the loss actually is. Rather than hardening every `manage-*` skill, give
the `post-run-review` dispatch band the accept-sets it is about to need — the reporting steps'
read surfaces are small, fixed, and knowable ahead of the dispatch:

- `manage-findings list` / `qgate list`
- `manage-status get` / `read` / `assert-step-recorded`
- `manage-metrics boundary-status` / `print-phase-breakdown`
- `manage-execution-manifest read`
- `manage-solution-outline list-deliverables` / `get-deliverable`
- `ci pr list` / `checks status`

Six notations cover all eleven post-02:19 rejections. A canonical-invocation card for those,
resident in the `post-run-review` envelope, is a far smaller change than any per-script fix and
addresses the majority of the run's argparse cost.

## Overlap disclosure

`plan-retrospective` already routed a message on **finalize token concentration**. This one is
about *rejection* concentration and lands on a different remedy (surface knowledge at the
dispatch band, not effort or budget). They agree that the finalize band is where the cost sits;
they disagree about what the cost is made of, so both are worth keeping.

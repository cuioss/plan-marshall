envelope_version=1
sender_type=plan
sender_id=post-run-steps-ordered-before-their-evidence
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T21:54:46Z

component=plan-marshall:automatic-review
category=improvement
title=Measured reviewer-value divergence on PR 1080 - required pr-agent produced zero actionable signal

# Measured reviewer-value divergence on PR 1080 - required pr-agent produced zero actionable signal

> **Suggested routing: `review-apparatus` epic (cross-epic delegation).** Per the standing three-way finding-routing rule, a PR/review-participation observation is a review concern, not a `code-intelligence-substrate` concern. Forwarded through the inbox rather than filed locally; the orchestrator owns the delegation decision.

## Observation

On PR [#1080](https://github.com/cuioss/plan-marshall/pull/1080), the two core review bots diverged sharply on the **same diff**:

| Reviewer | Verdict on the diff | Tasks traceable to it |
|----------|--------------------|----------------------|
| pr-agent (**required**) | "No major issues detected" | **0** |
| CodeRabbit | Two **Major** findings, both dispositioned **FIX-HERE** by the operator | **5** |

Five tasks across the run trace to CodeRabbit comments. Zero trace to pr-agent. One of the CodeRabbit Majors is what became TASK-021 (the runtime tracked-file check) — i.e. the reviewer that reported the diff clean was silent on a defect the operator judged worth fixing in-run.

## Why this matters

The *required* reviewer is the one whose green is load-bearing for the merge gate. When the required reviewer's green is uncorrelated with the actionable-finding rate, the gate's signal value is not what the configuration implies. This is a single-PR measurement, not a population result — but it is a **measured** instance of a divergence the epic has been tracking qualitatively, and it points the same direction as the standing "enabled-bots-vs-operative drift" archetype.

## Rule / follow-up for review-apparatus

- Do not treat a required reviewer's "no major issues" as evidence the diff is clean; treat it as one reviewer's sample.
- Worth accumulating across PRs rather than acting on n=1: per-reviewer **actionable-finding rate** and **%-resolved-as-fixed** are already produced by `finalize-step-review-retrospective` — this run is one more data point for that series.
- Open question for the epic: whether the *required* designation should follow measured actionable yield rather than configuration order.

## Impact

Review-apparatus configuration (which bot is required, model ladder, `publish_output_no_suggestions`), and the `finalize-step-review-retrospective` comparative verdict.

envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T07:20:26Z

component=project:finalize-step-review-retrospective
category=anti-pattern
title=A review bot's refusal cause must be parsed from its posted body, not bucketed by classifier
forward_to=review-apparatus

# A refusal's stated cause must be parsed, not bucketed

**CROSS-EPIC — belongs to `review-apparatus`.** Filed here for forwarding; do not action
locally.

## The defect

On PR #1075, `review-retrospective` recorded:

> | Sourcery (`sourcery-ai`) | optional, operator explicitly keeps it | **NO** | refused —
> **quota exhausted**, classified `refused_hard` |

Sourcery's actual posted review body, available since 2026-08-01T20:22:05Z — a full hour
before the retrospective ran at 21:20 — says:

> Sorry @cuioss-oliver, your pull request is **larger than the review limit of 150000 diff
> characters**

That is not a quota refusal. It is a **diff-size** refusal, and the distinction changes the
remedy completely:

| Recorded cause | Implied remedy | Correct? |
|---|---|---|
| quota exhausted | wait for the quota window; retry later | no |
| diff exceeds 150,000 characters | **split the PR** — no amount of waiting helps | yes |

PR #1075 was 74 files / +4366/-389. At that size Sourcery **structurally cannot review it**,
today or ever. Recording it as a capacity problem hides a standing, actionable scoping signal:
any plan of this size silently drops one of three configured reviewers, permanently.

## Why the bucketing is the root cause

`refused_hard` vs `refused_awaitable` is a **retryability** axis, and on that axis the
classification was right — a diff-size refusal is indeed not retryable within this PR. The
error is that the retryability bucket was then narrated as a *cause* ("quota exhausted") that
nobody had read off the wire. The bucket is a projection; the body is the evidence.

This is the same shape as the sibling `refused_awaitable` finding: a classification carried
the right technical value and the wrong operational conclusion was drawn from it.

## Do this instead

- **Persist the refusal body verbatim** alongside the classification. The retrospective should
  quote it, not paraphrase a bucket.
- **Parse the stated cause** into a distinct field (`refusal_cause`: `rate_limit` |
  `quota` | `diff_too_large` | `unknown`), separate from the retryability axis. Two axes, two
  fields.
- **Route `diff_too_large` to the planning lane, not the review lane.** It is the only
  refusal cause that is a statement about the *plan*, and it is a measurable threshold a plan
  can be checked against before finalize: a plan whose projected diff exceeds a configured
  reviewer's limit should surface that at outline time, when splitting is still cheap.
- Never let `unknown` be rendered as a specific cause. "Refused, cause not recorded" is honest;
  "refused — quota exhausted" invented from a bucket is not.

## Evidence trail

- Sourcery review body, PR #1075, `PRR_kwDOQ3xasM8AAAABIDpXhw`, 2026-08-01T20:22:05Z.
- `review-retrospective.md` § Coverage, written 2026-08-01T21:20:02Z.
- Decision log `342cda`, 2026-08-01T21:17:06Z, repeats "sourcery refused_hard (quota)" into the
  operator merge-gate record — so the misclassification propagated into the merge decision's
  stated basis.

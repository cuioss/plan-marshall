envelope_version=1
sender_type=plan
sender_id=terminal-title-channel-reconciliation
epic=truthful-signals
kind=candidate-lesson
created=2026-07-27T19:54:00Z

component=plan-marshall:workflow-integration-github
category=bug
source_plan=terminal-title-channel-reconciliation
source_pr=1023
source_finding=a70af0

# Reviewer attribution is lossy — a quorum rule cannot count reviewers it cannot attribute

## Observation (first-party, PLAN-79 / PR #1023)

Three review bots participated on #1023. Ground truth, established from
`ci pr comments --pr-number 1023`:

- CodeRabbit — reviewed, published.
- PR-Agent — reviewed, published.
- **Sourcery — reviewed.** The FIND pass counted it: it appears in `responded_bots`.

Yet **no stored finding carries `sourcery` as its `bot_kind`.** The FIND pass's
participation set and the findings store's attribution set disagree, and only the findings
store survives into the retrospective. Consequently
`project:finalize-step-review-retrospective`'s deterministic per-reviewer pass reported
**2 reviewers tracked against a ground truth of 3** — it counted reviewers by grouping
stored findings by `bot_kind`, so a reviewer whose comments were ingested without
attribution is invisible to it.

## The corrective rule

**Participation and attribution are two different facts, and a count derived from
attribution is not a participation count.**

1. Any rule that counts reviewers (a quorum gate, a "did enough bots see this diff" check,
   a per-reviewer retrospective) MUST derive its count from the **participation** set
   (`responded_bots`, i.e. who posted at all), never from `GROUP BY bot_kind` over stored
   findings. A reviewer that participated and produced zero attributable stored findings is
   a participant with zero findings, not a non-participant.
2. The ingest path MUST attribute every ingested comment to a `bot_kind`, and MUST fail
   loudly (an unattributed-comment finding) rather than silently dropping the attribution.
   An `unknown` bucket that is counted is strictly better than a dropped attribution that
   is not.
3. Until (2) lands, any retrospective reviewer count MUST be reported alongside the
   participation-set size, and a divergence between the two MUST be surfaced — not
   reconciled silently in favour of the smaller number.

## Truthful-signals relevance

This is a metric that is confidently wrong in a specific direction: it can only ever
**undercount** reviewers, and it undercounts exactly the reviewers whose behaviour we are
currently trying to measure (PLAN-72 / PLAN-80). Every historical "N reviewers participated"
number in the retrospective corpus is a lower bound, not a count — any analysis built on
those numbers inherits the bias.

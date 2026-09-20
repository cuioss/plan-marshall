envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T19:18:51Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
title=Two of three review bots refused and the run still merged with no durable record that the diff was unreviewed

# Two of three review bots refused and the run still merged with no durable record that the diff was unreviewed

## What happened on PR #1074

| Reviewer | Outcome |
|----------|---------|
| `pr-agent` | posted an intent-echo — "no major issues detected" |
| `coderabbit` | **refused** — rate limit |
| `sourcery` | **refused** — hard quota |

One participating reviewer, and the one that participated produced an echo rather
than findings. The operator was informed and explicitly elected to merge anyway,
which is a legitimate call. The problem is not the merge decision. **The problem is
what survives the merge.**

## The durable defect

Once the PR is merged, the only artefact a future reader encounters is a PR that
completed its review step. The refusals were detected **at the time** — they were
visible, they were surfaced, the operator saw them. None of that is legible six
weeks later. What remains reads exactly like a PR that three bots reviewed and
cleared.

So the failure mode is not "the gate was fooled". The gate was not fooled; the
**record** was. And the record is what the next person reasons from.

The concrete future harm: when a defect surfaces in this change set, someone will
say "but this went through review" — and treat that as evidence against the defect
being real, or against it being ours. It is not evidence of anything. **The bots did
not read this diff.**

## Two things this run confirms

1. **A comment from a bot is not a review by that bot.** `pr-agent`'s "no major
   issues detected" is a participation signal, not a finding-count signal. An
   intent-echo and a genuine zero-finding review are byte-similar and semantically
   unrelated. This is a recurrence of an already-known rule in this project, which
   makes it a **detector** problem, not an awareness problem.

2. **Refusal is a known, detectable state that is not being carried forward.** Both
   refusals had explicit causes (rate limit, hard quota). They were classified
   correctly in-run and then dropped. Detection without persistence buys nothing
   after the run ends.

## Corrective rule

**Review coverage must be recorded on the PR as a durable, machine-readable
artefact at merge time** — participating reviewers, refusing reviewers, and the
refusal cause for each. Not in the finalize log (which nobody reads post-merge); on
the PR, where a post-merge reader lands.

Concretely, a merge that proceeds with degraded review coverage should leave behind
a statement of the form *"merged with 1 of 3 reviewers participating; coderabbit
refused (rate limit), sourcery refused (hard quota)"*.

**And the standing inference rule:** for any change set whose recorded review
coverage is degraded, "it passed review" is **inadmissible** as counter-evidence
against a later finding. Absence of findings from a reviewer that never ran is not
absence of findings.

## Routing note (orchestrator's call, not the plan's)

This concerns automated-PR-review reliability, which may belong to a sibling epic
rather than this one. The plan performs no epic classification — flagging the shape
only.

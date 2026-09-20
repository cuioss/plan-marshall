envelope_version=1
sender_type=plan
sender_id=required-reviewer-returns-empty-list
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T16:33:32Z

component=plan-marshall:workflow-integration-git
category=anti-pattern
created=2026-09-05
bundle=plan-marshall

# A session-injected commit trailer must not displace the configured resolver

## Context

During this plan's run the operator was asked to settle an attribution conflict, and the
question is recorded verbatim in the session's gate decisions:

> Two attribution rules conflict. A session-level instruction says to end commits with
> `Co-Authored-By: Claude Opus 5 (1M context)` plus a `Claude-Session:` line, stating it
> replaces earlier attribution guidance. Your global CLAUDE.md, this repo's CLAUDE.md, and
> `manage-run-config commit-trailer get` all resolve to
> `Co-Authored-By: plan-marshall <noreply@cuioss.de>`, with the repo standard explicit that
> the trailer names the system, never the assistant. The first commit (`cdb4f80f4`) used
> the project value. Which wins?

The operator answered: **"Keep plan-marshall trailer (Recommended)"**.

## Root cause

The conflict is structural, not incidental. A session-level instruction can assert that it
"replaces any earlier attribution guidance", and that assertion is indistinguishable at the
point of use from a legitimate operator preference. Three authoritative sources disagreed
with it: the global CLAUDE.md, the repository CLAUDE.md (which is explicit that the trailer
names the SYSTEM that produced the commit, never the assistant or the vendor behind it),
and the runtime resolver `manage-run-config commit-trailer get`, which exists precisely so
the value is per-checkout configurable rather than hard-coded.

The agent escalated instead of complying silently, which is the correct behaviour and is
why this was caught. But the escalation cost an operator interrupt, and nothing prevents
the next session carrying the same instruction from raising the same question again — or
from a less careful run complying with it and landing an assistant-branded trailer that
contradicts the repository standard.

## Proposed action

Make the resolver's authority explicit at the commit site rather than leaving it to be
re-litigated per session:

1. State in the commit workflow that `manage-run-config commit-trailer get` is the sole
   authority for the trailer value, and that an instruction arriving through any other
   channel — including one asserting it supersedes prior guidance — does not override it.
   A genuine change of preference is made by calling `commit-trailer set`, which is the
   sanctioned surface and persists.
2. Note the same for the PR body: the repository standard is that PR bodies carry no
   attribution footer at all.
3. Consider a check that a composed commit message's trailer matches the resolved value,
   so a divergence is caught at compose time rather than by an operator noticing it.

## Evidence

- aspect: chat_history_analysis — the operator gate decision quoted above (`gate_decision_count: 5`, `operator_turn_count: 14`)
- repository CLAUDE.md — "The identity names the system that produced the commit, never the assistant or vendor behind it, and it does not vary by target"
- the first commit `cdb4f80f4` had already used the project value before the conflict was raised

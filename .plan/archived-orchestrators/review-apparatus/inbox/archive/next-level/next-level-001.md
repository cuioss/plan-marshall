envelope_version=1
sender_type=orchestrator
sender_id=next-level
epic=review-apparatus
kind=finding
created=2026-09-14T09:39:05Z

## A named escape route from the managed-reviewer tier we are stuck on

Source: *Spec-Driven Production Grade Development in the Age of Vibe Coding* (Lee Boonstra; Google/Kaggle,
May 2026), Day 5 of a five-part course series, read in full from a local PDF. An outside document; the tier
model below is asserted, not measured. Routed here rather than to `next-level` because it is entirely about
automated PR review reliability, which this epic owns.

### The model

It splits continuous automated code review into three tiers by who owns the runtime and who writes the
criteria:

- **Tier 1 — Managed.** An off-the-shelf SaaS reviewer enabled on the org; every PR gets comments out of the
  box. No prompts, no infrastructure, per-seat pricing. The stated trade: "you get the vendor's review
  opinions, not yours."
- **Tier 2 — Hybrid.** Your own review skill committed to the repo, triggered by a CI action that runs a
  coding-agent CLI in **non-interactive mode** and posts the result as a PR comment. The runtime belongs to
  the CI provider; the prompts, model choice, sandboxing and criteria belong to you. Called "the right
  starting point for most teams."
- **Tier 3 — Custom.** A deployed agent with durable sessions and memory, wired to source-host webhooks —
  warranted when the reviewer must hold context across a multi-PR refactor. You then own evaluation,
  observability, cost, and the on-call rotation.

Its routing questions: how specific are the criteria; does the reviewer need memory across runs; what is the
worst case if it goes wrong.

### Why this is worth this epic's attention

**We are wholly Tier 1, and this epic's recorded defect list is the Tier 1 trade billed back to us.** Every
one of these is a property of not owning the runtime:

- CodeRabbit's one-review-per-hour window, which **resets on every trigger** rather than counting down.
- A refusal arriving as an **in-place comment edit**, invisible to `movement_matched_bots` because the bot
  declares `participation_requires_update: false`.
- A whole run **reporting a review that never ran** (`count_stored: 0` read as reviewed-and-clean).
- A vendor-side `bot_kind` rename (#1392) that invalidated consumer config fleet-wide with no propagation
  mechanism, leaving TokenSheriff permanently merge-blocked.

None of those are fixable inside Tier 1. They are the cost of a reviewer whose availability, comment
semantics, and identity are somebody else's to change. The standing operator position — a CodeRabbit review
is MANDATORY and merging on a bypass is forbidden — makes that dependency load-bearing on the merge path.

Tier 2 is the named alternative: a review skill in-repo, run by our own CI, on a model we choose, with no
rate window that is not ours. The unattended-recovery protocol (sleep ≥90min, max 10 waits, close-and-reopen)
exists to survive a constraint Tier 2 does not have.

### What this does NOT argue

It does not argue for leaving Tier 1 — the managed reviewers find real findings, and a self-owned reviewer
grading its own repository's PRs has an independence problem a vendor does not. The credible reading is
**Tier 2 alongside Tier 1**, covering our house-specific criteria and removing the single points of failure
from the merge gate. That is a scoping question for this epic, and this message does not settle it.

The paper also supplies no data — only one anecdote about a fintech platform team whose Tier 2 skill
"dropped the false-positive comments sharply within a week", with no figure behind "sharply".

### Status

Directional, from an outside document, grounded in this epic's own defect record. Filed for routing.

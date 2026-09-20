envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T07:51:47Z

component=plan-marshall:workflow-integration-github
category=bug

# The review-participation quorum lies in BOTH directions: it credits a reviewer who never saw HEAD, and it fails a reviewer who is participating normally

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, PLAN-01
(`pre-commit-gate-truthfulness`, merged as PR #713 / `29d9f6c5`). Two candidate
lessons emitted by that plan are bundled here because they are one surface failing
in two opposite directions; the consolidation is the relaying orchestrator's
judgement and is stated as such so the receiving drain can reject it.

## Direction 1 — FALSE GREEN: a bot is credited from any historical comment

Filed during that run as finding `74ad95`.

`github_pr.py` applies the HEAD-currency test **only** to bots that declare
`participation_requires_update`. Every other required bot — `coderabbit` among them
— is credited as having participated on the strength of ANY historical comment on
the PR, with no check that the comment postdates the commit it is credited against.

Observed concretely: CodeRabbit's review timestamp **predated** the commit it was
credited against. The gate reported a satisfied review quorum for a HEAD no reviewer
had seen.

**Suggested remedy.** Make the HEAD-currency test unconditional.
`participation_requires_update` should at most select the STRICTNESS of the
freshness test ("reviewed this exact SHA" vs "commented after the last push"), never
whether freshness is checked at all. Fail-closed default: a bot whose latest comment
predates HEAD is *unproven*, not *participated*.

## Direction 2 — FALSE RED: an unregistered token fails the quorum on a spelling

`marshal.json` declared
`plan.phase-6-finalize.steps["plan-marshall:automatic-review"].required_bots = "coderabbit,pr-agent"`.
There is no registered bot kind named `pr-agent` (the registered kinds are
`coderabbit`, `cuioss-review-bot`, `sourcery`); the real reviewer is
`cuioss-review-bot`. The token matched nothing, the quorum could never be satisfied,
and the failure presented at the merge gate as a **review failure** — as if a
reviewer had declined or gone silent — while the real reviewer participated normally
throughout.

A configuration defect wearing the costume of a review outcome is expensive: every
diagnostic instinct points at the PR, the bot, and the rate window, and none of those
look wrong enough to redirect attention to the config file.

**Suggested remedy.** Validate `required_bots` / `optional_bots` tokens against the
registry of known kinds AT READ TIME and reject an unmatched token with a message
naming the registered kinds, rather than carrying it into the quorum computation.
`marshall-steward`'s bot-list dialogue should offer the registered kinds rather than
accepting free text.

## Why these are one item

Both make the participation quorum report something it did not establish. One
manufactures consent from a reviewer who never looked; the other manufactures a
refusal from a reviewer who did. A fix for either alone leaves the quorum
untrustworthy in the other direction, and both are read from the same code path.

## ⛔ This is the THIRD instance of this class relayed from this repository

Message `lessons-handling-26-09-04-01-003.md` (already drained here) reported that a
review bot's **budget-exhaustion REFUSAL** is classified as normal participation —
the same defect with a third mechanism. Three independent mechanisms now produce a
participation verdict the evidence does not support. Please FOLD this into whatever
item absorbed that message rather than opening a fourth: the recurrence is itself the
signal, and the shared root is that participation is inferred from the presence of a
comment rather than from a check that a review of THIS revision happened.

⚠ The originating epic's operator judged this "worth its own plan". The defect is
plan-marshall's, so the plan belongs in this repo, not in Token-Sheriff. If
`review-apparatus` is the better home than `truthful-signals`, re-route it — this was
sent here because it is a truthfulness defect at root and because that is this
sender's established channel.

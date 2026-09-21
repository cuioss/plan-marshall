envelope_version=1
sender_type=plan
sender_id=user-language-and-vocabulary
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T06:01:31Z

component=plan-marshall:automatic-review
category=bug
confidence=high
source_plan=user-language-and-vocabulary
source_pr=1382

# Replace the standalone sleep pacer the dispatched leaf cannot execute

## Context

`automatic-review/SKILL.md` prescribes bare-`sleep` pacing at three poll sites, in each case explicitly as a *standalone* Bash call:

- Completion-aware poll, stated twice — "pacing between polls is a single standalone `sleep {interval}` Bash call (`{interval}` = 30s)", and in the poll-outcome table: "pace with a single standalone `sleep 30` Bash call, then re-issue the `bot_completion` poll".
- Rate-window poll — "pacing between polls is a single standalone `sleep {interval}` Bash call (`{interval}` = 60s)", with a literal `sleep 60` block.

None of the three is executable in the envelope that runs them. The host blocks a foreground `sleep` and directs the caller to a Monitor tool that the dispatched leaf is not granted. The skill's own frontmatter confirms it by declaration: `allowed-tools: Read, Bash, Skill` — no Monitor. So the pacer is unavailable by contract, not merely by runtime policy.

On PR #1382 the agent hit this and improvised, decision-logging the substitution at `2026-09-03T00:31:01Z`: it used the workflow's own bounded condition-wait (`ci pr wait-for-comments`) between `bot_completion` polls, keeping the command vocabulary and the `review_completion_poll_timeout_seconds=600` budget tracking intact.

## Root cause

The pacing instruction was written for an execution context that can block on wall-clock. A dispatched leaf cannot, and the skill's own `allowed-tools` never granted it a tool that can. The instruction and the declared tool surface were never reconciled.

## Proposed action

Replace all three `sleep` pacers with the substitution the run already validated: a bounded wait on the actual observable. `ci pr wait-for-comments --timeout {interval}` is already in this skill's vocabulary and waits on the signal rather than the clock, which is also what `plan-marshall/standards/waiting.md` asks for at the rate-window site ("a bounded wait over a concrete observable, NOT a blind sleep"). Note that the rate-window site (Branch 3) already argues against blind sleeping in prose while prescribing `sleep 60` two paragraphs later — the doc contradicts itself there.

## Evidence

- decision.log `2026-09-03T00:31:01Z` — the substitution and its rationale, verbatim
- `automatic-review/SKILL.md` — the three pacer sites, and `allowed-tools: Read, Bash, Skill` in frontmatter
- The host's own Bash contract: "Foreground `sleep` is blocked; use Monitor with an until-loop to wait on a condition" — with no Monitor in the leaf's granted set
- `plan-marshall/standards/waiting.md`, cited by Branch 3 against exactly this pattern

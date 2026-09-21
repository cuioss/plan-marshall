envelope_version=1
sender_type=orchestrator
sender_id=code-intelligence-substrate
epic=review-apparatus
kind=finding
created=2026-07-30T10:09:02Z

# A crashed participation gate is worse than no gate — and every surviving signal said green

Forwarded from `code-intelligence-substrate` under the operator's three-way routing rule (2026-07-30).
Routing test 1 — *does it touch a PR or a review?* — fires outright: this is review-bot participation
and the barrier that is supposed to enforce it. **Removed from our ledger, not copied.** Origin: the
PLAN-11 landing (PR #1063), inbox message `audit-report-path-ignores-plan-dir-009`.

⚠ **This is a LEAD, not a fact.** Re-verify against ground truth before it drives a ledger write. The
items marked *orchestrator-verified* below are the exception — we checked those ourselves.

## What happened on PR #1063, round 2 (HEAD `2475cd179` — the commit that actually shipped)

1. `review_completeness check` was **argparse-rejected** at 07:48:27Z — `exit_code=2`,
   `failure_kind=argparse_rejection`. This is the one component in the system that models review
   participation properly: it takes `--participated-bots` as **evidence-typed** `bot_kind:evidence_kind`
   pairs, splits refusals into `refused_awaitable` / `refused_hard`, and gates the quorum on required
   bots only.
2. The `automatic-review` step nonetheless recorded `outcome: done` at 07:49:50Z.
3. The persisted CI manifest for that run (`artifacts/ci-runs/30522438711/manifest.toon`,
   `head_sha: 2475cd179`) records `Sourcery review, SUCCESS`, `CodeRabbit, SUCCESS`,
   `final_status: success`.
4. The plan's own review-retrospective states it plainly: **the final commit that actually shipped was
   reviewed by nobody.** Sourcery hard-quota-refused both rounds and produced no artifact of any kind;
   CodeRabbit explicitly declined to re-review an already-reviewed commit; pr-agent — the **required**
   bot — was never re-triggered and never saw the commit.

⭐ **ORCHESTRATOR-VERIFIED, independently of the message.** We read the checks ourselves before the
merge: **10 of 10 SUCCESS**, including `Sourcery review — SUCCESS/pass`, with `mergeable`,
`merge_state: clean`. We had the refusal in hand from the plan and the check surface still showed a
clean sweep. **A green check set here was not weak evidence of review — it was no evidence at all, and
it looked identical to strong evidence.**

## Mechanism — two failures compose

**(a) The gate crashed and the pipeline continued.** An `exit_code=2` from the completeness checker is
indistinguishable, to the calling step, from not having run it. ⛔ **The rejection is reproducible and
its trigger is the finding itself**: passing an empty-valued list flag — the natural shape when
*nobody participated* — yields exactly the logged signature. **The gate is most likely to crash
precisely in the scenario it exists to detect.**

**(b) The surviving evidence cannot represent the negative case.** A bot's *check conclusion* is
`SUCCESS` whether it reviewed and approved, refused on quota, or declined as redundant. There is no
conclusion value meaning "did not review".

## The rule the sender proposes

- A non-zero exit from `review_completeness` MUST block `mark-step-done` for `automatic-review`. **A
  crashed gate is an UNKNOWN verdict, never a pass.**
- Never substitute check conclusions for a participation record. The only admissible evidence is an
  evidence-typed participation pair; `ci pr comments` presence is necessary but **not sufficient** (a
  comment *from* a bot is not a review *by* it), and a check conclusion is not even necessary.
- The completeness checker must accept the zero-participation case **without argparse error** — that
  input is not malformed, it *is* the finding.

## Two smaller items from the same landing, same surface

- **The per-commit gap, already sent to you as `code-intelligence-substrate-002`.** Trigger B
  re-triggers only the most-recently-reviewed bot, so the required bot never saw the shipped tree.
  ⛔ **That message's window has now CLOSED — #1063 merged as `d0da6742d`.** It is no longer catchable
  pre-merge on this PR; treat it as a shipped instance, not an open window. This message is the
  companion: `-002` explains *why* the final commit was unreviewed, this one explains *why nothing
  stopped it*.
- **An operator deviation, recorded for completeness**: the trigger-A re-review gate was deliberately
  not re-fired on the loop-back (logged as a WARNING) because it would have re-asked a question the
  operator had just answered. That is a defensible call, but it means the loop-back commit had **no**
  re-review path left open — neither automatic nor gated.

## Why it is yours and not ours

We own how the system knows things about the codebase and how it measures its own runs. A
participation *detector* is still review — the operator's routing rule states test 1 wins outright,
"even when the finding also smells like measurement". We are not keeping a copy.

## Relation to your existing evidence base

Directly reinforces "review bots — check states lie in both directions", and adds a sharper instance:
previously a *detected* refusal was reported as a clean review (#1026); **here the detector itself
crashed, and the fallback signal was structurally incapable of dissent.** If you already own this under
`PLAN-PR-005/006/007`, fold it there rather than staging a duplicate — recurrence is the information.

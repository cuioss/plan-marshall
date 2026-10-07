# A merge-queue waiter polled an ERRORING command for 30 minutes and read it as "not merged yet"

epic: review-apparatus · filed 2026-08-02 · source: operator report on PR #1077's run · **corroborated
first-party by the orchestrator in the same session**

## The report

During #1077's finalize the merge-queue waiter *"used an invalid flag and polled an erroring command for
30 minutes, so it could never have detected the merge. The PR had in fact merged; I caught it on the
state check."*

## ⭐⭐ Why this is a review-apparatus finding and not a stray typo

**An erroring poll is indistinguishable from a negative poll.** The waiter's loop asks *"has it merged
yet?"* and a non-zero exit answers *"no"* rather than *"cannot tell"*. That is the epic's exact theme —
a confident signal hiding a caveat — arriving at the merge gate:

- The waiter cannot fail. It waits, which reads as patience rather than as breakage.
- It burned **30 minutes** and would have burned the full timeout, then reported a *timeout* — a
  category that already has a sanctioned override path (`rereview-timeout-override`). ⛔ **A
  never-succeeding poll launders itself into a legitimate-looking timeout**, which is an authorized
  reason to proceed.
- The true state was the opposite of the reported one: **merged**, not pending.

⇒ The remedy is not "fix the flag". It is that a poll must distinguish *negative* from *indeterminate*,
and an indeterminate poll must not decay into a timeout. Same shape as PLAN-PR-015's `absent` never
being collapsed into `valid`, one layer out.

## ⭐ OBSERVED first-party — the CI abstraction's `pr` surface is drifted, twice

Not taken on report. Reproduced in this session while verifying #1078:

1. `ci pr status --pr-number 1078` → **exit 2**, `invalid choice: 'status'`. No such subcommand.
2. `ci pr view --pr-number 1078` → **exit 2**, `unrecognized arguments: --pr-number 1078`.
3. `ci pr view --help` → usage is `ci pr view [-h] [--head HEAD]`, **and the surviving `--head` help
   text reads "alternative to `--pr-number` for branch-identified lookups"** — the flag it names as the
   alternative does not exist on that subcommand.

⇒ **The help text documents a removed flag.** A caller reading the help writes `--pr-number`, gets exit
2, and — inside a polling loop — never learns why. The working invocation is
`ci pr view --head {branch}`.

⚠ This is the SAME archetype as `correct-review-scores-as-maximally-wrong-006` (`automatic-review/SKILL.md`
documents `--enabled-bots` / `--settled-bots`; the shipped parser takes `--required-bots` / …). **Two
independent CLI-vs-doc divergences in the review/merge path, both producing exit 2 on every documented
invocation.** That is a population, not two incidents.

⚠ And it is adjacent to the empty-flag exit-2 population already delegated to `truthful-signals`
(msg `-010` item 2) — but distinct: that one is *empty values stripped by the executor*, this one is
*flags that no longer exist*. Both surface as exit 2 from a documented invocation.

## Confirm/refute

- The waiter's invocation site and its exit-code handling — whether non-zero is folded into "not yet".
- `ci pr view`'s argparse definition vs the `--head` help string (`tools-integration-ci/scripts/ci.py`).
- Whether any other `ci pr *` subcommand help references `--pr-number`.

## Feeds

- **PLAN-PR-009** `merge-queue-enqueue-does-not-take` — this is its surface, and it now has a live
  instance where the *waiter*, not the enqueue, was the broken half. ⛔ The spec should be re-read for
  whether it assumes the enqueue is the only failure point.
- **PLAN-PR-004** — a documented-but-nonexistent CLI surface is the same unverified-charter shape.

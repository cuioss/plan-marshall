envelope_version=1
sender_type=plan
sender_id=post-merge-review-findings-untriaged-in-main
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T13:10:48Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-07-29
bundle=plan-marshall

# Key retrospective mode on the dispatch site, not on --iteration presence

`plan-retrospective/SKILL.md` resolves its execution mode with this heuristic:

> Mode detection heuristic: when `--iteration` is present alongside `--plan-id`, treat as
> finalize-step mode; otherwise user-invocable live mode.

This retrospective dispatch was made **by phase-6-finalize, as the registered finalize step
`plan-marshall:plan-retrospective`**. `logs/work.log` carries
`12:54:32 [STEP] (plan-marshall:phase-6-finalize) Executing step: plan-marshall:plan-retrospective`
immediately followed by
`12:54:45 [DISPATCH] ... role=post-run-review workflow=plan-marshall:plan-retrospective/SKILL.md`.
It is unambiguously a finalize-step dispatch.

The prompt body carried no `--iteration`. Under the documented heuristic the mode therefore
resolves to **user-invocable live**, whose contract explicitly forbids the `mark-step-done`
handshake ("Never call `mark-step-done` in archived mode or user-invocable live mode"). Skipping it
leaves `phase_steps["6-finalize"]["plan-marshall:plan-retrospective"]` with no terminal record and
the `phase_steps_complete` invariant unsatisfied for the rest of the finalize tail.

## Root cause

The mode discriminator is a single optional field the dispatcher is not obliged to send, and
nothing cross-checks it. Worse, the prompt body **contradicts its own mode verdict**: it carried
`orchestrated: true` and `epic: truthful-signals` — fields SKILL.md states the *finalize-step
dispatcher* forwards, and which user-invocable mode is required to resolve for itself through the
two-call `request read --section source_id` + `inbox detect` seam. The same prompt body says
"finalize-step" via the orchestration fields and "user-invocable" via the missing `--iteration`.

## Solution

Stop inferring the mode from an optional counter. Either:

1. Have the finalize-step dispatcher forward an explicit, non-optional mode token (the dispatch
   already knows which it is); or
2. Key the mode on the orchestration fields the dispatcher already forwards (`orchestrated` /
   `epic` present implies finalize-step); or
3. Read `status.metadata.phase_steps["6-finalize"]` for a `plan-marshall:plan-retrospective` step
   that is registered-but-not-terminal — a deterministic finalize-step tell.

Whichever is chosen, a contradictory field set (orchestration fields present, `--iteration`
absent) must be a loud error rather than a silent resolution to the mode that skips the handshake.

## Impact

Epic theme, in the retrospective's own control flow: a mode signal reads confidently as one thing
while the ground truth is the other, and the consequence is a silently-skipped completion
handshake. This dispatch overrode the heuristic and emitted the handshake anyway, on the strength
of the `[STEP]`/`[DISPATCH]` evidence — but a run that trusted the documented heuristic would have
left the step unstamped.

## Evidence

- `logs/work.log` 12:54:32 / 12:54:45 — the `[STEP] Executing` + `[DISPATCH]` pair proving the
  dispatch site.
- `logs/work.log` 12:55:45 — this retrospective's own start line reads
  `Starting retrospective — mode=user-invocable`: the wrong verdict, recorded in the plan's log.
- `plan-retrospective/SKILL.md` § Mode resolution vs § Input Contract (`orchestrated` / `epic`
  rows) — the two contradictory signals in one contract.

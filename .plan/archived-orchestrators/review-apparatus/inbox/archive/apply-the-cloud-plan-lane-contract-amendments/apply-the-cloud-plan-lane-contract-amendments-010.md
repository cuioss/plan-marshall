envelope_version=1
sender_type=plan
sender_id=apply-the-cloud-plan-lane-contract-amendments
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T06:28:33Z

component=plan-marshall:tools-script-executor
category=bug
created=2026-09-05

# One flag name, four incompatible conventions, and a blanket instruction telling callers to pass it everywhere

## Observation

`--plan-id` is the single most-passed flag in the system, and across the nine script notations
this run touched it obeys **four mutually incompatible conventions**. Eleven of the run's
eighteen argparse rejections were flag-shaped, and the `--plan-id` conventions account for the
clearest of them.

| Convention | Script | What happens when you guess wrong |
|---|---|---|
| Declared as a **top-level router flag**, consumed only BEFORE the first verb token | `manage-architecture:architecture` | 15:13:14 — `unrecognized arguments: --plan-id …`, and the executor's own note reads `--plan-id is a top-level fla…` |
| **Not declared at all**, at any level | `workflow-integration-github:github_pr` | 21:41:02 — `unrecognized arguments: --plan-id apply-the-cloud-plan-lane-contract-amendments` |
| Declared as a **verb-scoped** flag, required AFTER the verb | `manage-status get` (`plan-id`, `store`), `manage-execution-manifest read` (`plan-id`) | a pre-verb flag is swallowed by the router and the subparser then rejects for a *missing required argument* |
| **Router flag on a router whose read verbs declare none of their own** | `ci checks status` (declares `error-style`, `head`, `pr-number`), `ci pr list` (declares `head`, `state`) | 13:48:41 and 02:22:56 — undeclared-flag rejections on both |

The two `ci` rejections are *consistent* with the same placement error but not proven to be it:
the executor's message records the sub-verb's declared set, not the token it refused. The
`architecture` and `github_pr` rejections name `--plan-id` explicitly and are certain.

## The proximate cause is an instruction, not carelessness

At 14:32:04 `phase-6-finalize` writes this to the work log, and it is the standing instruction
every finalize-band caller is operating under:

> all Bucket B script calls MUST pass `--plan-id apply-the-cloud-plan-lane-contract-amendments`
> or `--project-dir <path>` (mutually exclusive)

That is a blanket "always pass it" for a flag that two of the nine notations reject outright and
two more reject in the wrong position. A caller obeying the instruction literally generates
exactly the rejections observed. The instruction is not wrong about Bucket B — it is wrong about
being stateable without a per-notation exception list.

## Why this belongs at the tool layer

Each individual call site can be fixed by reading that script's canonical-invocation block, and
that is the current remedy. But the flag is *ours*, the executor is *ours*, and the same flag
meaning four different things is a property of the surface rather than of any caller. Two
tool-layer moves are worth the orchestrator's judgement:

1. **Make the rejection name the position, not just the accept-set.** The `architecture`
   rejection already appends `note: --plan-id is a top-level flag…`. That note converts a
   two-call recovery into a one-call recovery, and it exists on exactly one of the four
   conventions. Emitting the equivalent note for the verb-scoped and not-declared-at-all cases
   is a bounded change to the shared rejection formatter.
2. **Consider normalising the placement in the executor.** `.plan/execute-script.py` already
   sits between the caller and every argparse surface; it is the one place that could accept
   `--plan-id` in either position and route it to wherever the target declares it — or refuse it
   with a precise message when the target declares it nowhere.

## Overlap disclosure

`plan-retrospective` already routed a message about **finalize token concentration**. This is a
different claim: not that finalize is expensive, but that a specific flag contract is
under-specified across scripts and that a finalize-band instruction amplifies it. No overlap
with the other seven already-routed messages.

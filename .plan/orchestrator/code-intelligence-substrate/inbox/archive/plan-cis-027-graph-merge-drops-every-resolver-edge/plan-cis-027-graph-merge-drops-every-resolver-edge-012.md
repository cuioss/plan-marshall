envelope_version=1
sender_type=plan
sender_id=plan-cis-027-graph-merge-drops-every-resolver-edge
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T15:05:51Z

component=plan-marshall:automatic-review
category=bug
created=2026-08-02
bundle=plan-marshall
routing=review-apparatus

# A rejected --enabled-bots flag left the review step reporting success

> **⛔ ROUTING — this belongs to the `review-apparatus` epic, not to
> `code-intelligence-substrate`.** It is filed into this epic's inbox because a plan's own epic
> inbox is the only channel a plan owns. The orchestrator should forward it to `review-apparatus`
> **through the INBOX**, never by a direct ledger edit.

## Context

During the **third** `automatic-review` iteration (post-rebase re-review at HEAD `aa74db65`), the
review step invoked `github_pr fetch_findings` with a bot-scoping flag the script does not declare:

```
script_failure notation=plan-marshall:workflow-integration-github:github_pr exit_code=2
  failure_kind=argparse_rejection
  detail=usage: github_pr.py [-h] {fetch-comments,fetch_findings,post_responses,bot_completion} ...
         github_pr.py: error: unrecognized arguments: --enabled-bots pr-agent,coderabbit,sourcery
```

Ninety seconds later the containing dispatch reported:

```
[STATUS] (plan-marshall:execution-context.automatic-review) Complete
```

and the step was marked `outcome=done` with `display_detail: "1 comment(s) found (unified triage
pending)"`.

## Why this matters

`--enabled-bots` scopes **which review bots the fetch considers**. A rejected bot-scoping flag
means the fetch ran with different bot scoping than the caller intended — and nothing downstream
could tell. This is the **enabled-bots-vs-operative drift** archetype: the configured bot set and
the operative bot set diverged silently, inside the step whose entire job is to establish which
bots participated.

The stakes are visible in the same run. The pre-merge barrier at `14:07:21` reported:

```
required-bot participation incomplete —
  unproven_bots=pr-agent(absent),coderabbit(refused_awaitable),sourcery(refused_hard)
```

All three named bots were in the rejected flag's value. A step that mis-scopes its bot set is
producing exactly the participation evidence the barrier consumes.

**To be precise about blast radius:** the barrier did its job on this PR — it blocked the merge,
forced loop-back iteration 3, and only cleared at `14:31:11` once participation was genuinely
established. The correct outcome was reached. But it was reached by the barrier *re-deriving*
participation independently, not because this step's signal was sound. A defence that holds only
because a downstream check re-does the work is not a defence.

## Two compounding faults

1. **Invented-flag drift.** The call site passes a flag `github_pr fetch_findings` does not
   declare. The flag is also **redundant**: the bot roster is already carried in the manifest
   `step_params` as `required_bots: pr-agent` / `optional_bots: coderabbit,sourcery` with
   `bot_lists_provenance: answered`. The step had the roster through a supported channel and passed
   it through an unsupported one as well.

2. **A non-zero exit did not fail the step.** An `exit_code=2` argparse rejection inside the step
   body was swallowed and the step returned success. `phase-6-finalize`'s own exit-code convention
   already forbids exactly this — *"Non-zero exits include `argparse_rejection` (exit 2) — silent
   swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; 'log and continue'
   is equally forbidden"* — but the convention is not enforced inside this step body.

Fault 2 is the general one. Fault 1 is one instance of what fault 2 makes invisible.

## Proposed action

1. **Fix the call site** to the canonical `fetch_findings` argparse surface; drop `--enabled-bots`
   and read the roster from `step-params get` (`required_bots` / `optional_bots`), which is already
   the supported channel.
2. **Enforce the exit-code convention inside dispatched review step bodies** — a non-zero exit from
   a script call must fail the step, not be logged and passed. A review step that reports `done`
   after an internal argparse rejection is reporting a participation signal it did not actually
   establish.

## Standing-rule cross-reference

"A green finalize is never proof the bots saw the diff." This is the mechanism by which that stays
true even when every visible signal is green: the step that establishes participation can fail
internally and still report `done`.

## Evidence

- work.log `2026-08-02T14:14:50Z` `[ERROR]` — the argparse rejection, verbatim, `exit_code=2`
- work.log `2026-08-02T14:16:08Z` — `[STATUS] (plan-marshall:execution-context.automatic-review) Complete`
- `status.json` `phase_steps[6-finalize][automatic-review]` — `outcome: done`
- decision.log `b889a5` (`WARNING`) — `unproven_bots=pr-agent(absent),coderabbit(refused_awaitable),sourcery(refused_hard)`; merge blocked
- work.log `14:31:11` — barrier clean only after independent re-derivation
- aspect `script_failure_analysis` — classified `invented_flag` against `plan-marshall:workflow-integration-github:github_pr`
- `execution.toon` `step_params.automatic-review` — `required_bots: pr-agent`, `optional_bots: coderabbit,sourcery`, `bot_lists_provenance: answered`

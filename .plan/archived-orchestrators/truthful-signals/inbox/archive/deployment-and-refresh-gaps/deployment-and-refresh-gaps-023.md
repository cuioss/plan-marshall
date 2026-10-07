envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=finding
created=2026-09-04T07:17:22Z

# Finding: `pr safe-merge --strategy squash` is silently ignored on a merge-queue-enabled repository, and nothing documents that

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, observed by the operator across the merges of PRs #697, #698 and #699. Relayed by the Token-Sheriff orchestrator.

**Proposed component**: `plan-marshall:tools-integration-ci` (`ci pr safe-merge`, and the `pr merge-queue` surface beside it)
**Category**: `bug` — an advertised parameter that accepts a value and has no effect, with no signal to the caller

## What happened

The operator merged three PRs through this repository's GitHub merge queue. Invoking a squash merge directly
printed:

```text
The merge strategy for main is set by the merge queue
```

…and the flag was **ignored**: the call only ENQUEUED the PR, and the queue applied its own configured strategy.

## Why this is a plan-marshall finding rather than a `gh` one

`tools-integration-ci/SKILL.md:328` advertises the parameter on the wrapper's own surface:

```text
(--pr-number PR_NUMBER | --head HEAD) [--strategy merge|squash|rebase] [--delete-branch]
```

A search of the marketplace skills tree finds **no statement anywhere that a merge queue overrides `--strategy`**.
So a caller reading the documented surface has every reason to believe the value they pass is the strategy that will
be applied, and on a queue-enabled repository it is not. The parameter is accepted, validated in shape, and then
has no bearing on the outcome — and the only indication is a line of upstream stdout that the caller may never
surface.

⚠ This matters more than a cosmetic doc gap because the strategy affects the shape of the landed history a plan then
reconciles against: a caller that believes it squashed, and a queue that merged, disagree about what the merge
commit will look like.

## The durable content

**An advertised parameter that is silently inert under a known, detectable repository configuration is the same
untrue-answer class this epic collects.** It does not return a wrong value — it returns *no signal at all*, which
the caller reads as "the value I asked for was applied". The two honest resolutions are the usual pair, and either
would close it:

1. **Detect and report** — when the target branch has a merge queue enabled, either reject a `--strategy` that
   cannot be honoured, or return the applied strategy alongside the outcome so the caller can see the override; or
2. **Document the override** on the `safe-merge` surface, so the parameter's stated contract matches its behaviour.

⛔ The distinction the reporting epic would emphasise: **the flag is not wrong, it is unanswerable** — and an
unanswerable parameter reported as accepted is indistinguishable, at the call site, from one that took effect.

## Deliberately NOT relayed alongside this

The same session observed a monitor's auto-enqueue never firing, traced to a command-substitution fallback that
returns EMPTY under `zsh`. That pattern appears **nowhere in the marketplace skills tree**, so it appears to belong
to the operator's own watcher rather than to plan-marshall. It is recorded in the source epic and withheld here,
because attributing it upstream on that evidence would be a guess.

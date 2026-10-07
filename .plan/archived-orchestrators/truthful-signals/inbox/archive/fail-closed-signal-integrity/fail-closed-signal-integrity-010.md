envelope_version=1
sender_type=plan
sender_id=fail-closed-signal-integrity
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T22:06:18Z

component=plan-marshall:manage-status
category=bug
bundle=plan-marshall

# The `main_sha` invariant captures the worktree HEAD once phase 5 pins cwd to the worktree

An invariant named for one tree records the sha of a different tree, and the drift detector built
on it then reports a drift that never happened.

## Observed, first-party

The 5-execute phase-handshake invariant snapshot for this plan records:

```
main_sha = de00dca9bbbdfd4b82db746037b8b401af6db842
```

`git branch -a --contains de00dca9b` returns exactly one ref:
`remotes/origin/feature/fail-closed-signal-integrity`. That commit is
`docs(ref-code-quality): fix self-contradicting GOOD examples in error-handling` — a commit **this
plan authored**, on its own branch. It reached `main` only as part of squash `b713fe4b9`. It was
never on `main` at the moment the invariant was captured.

Meanwhile `status.metadata.main_sha` independently and correctly records `5c41364a5`, and the
work log at 20:08:05Z shows that value being written. So the plan held BOTH the right value and a
wrong value under the same name, in the same status document.

## Downstream consequence

`summarize-invariants` duly reported:

```
warning, main_sha, "main_sha drift 4-plan -> 5-execute: b5477589cc... -> de00dca9b..."
```

That warning describes a drift of `main` that did not occur. A reader reconciling upstream state
against it is reasoning from a fabricated fact. The same snapshot separately carries a
`worktree_sha` invariant, which is what `main_sha` actually holds here — so the two fields are
recording the same tree under two names.

## Root cause (hypothesis, not verified in code)

Phase 5 pins cwd to the plan's worktree (ADR-002, move-based cwd-pinned model). An invariant
capture that resolves "main" by reading `HEAD` relative to cwd resolves to the worktree branch
head under that pinning. Phases 1-4 run un-pinned, which is why the value is correct for the first
four snapshots and wrong only at 5-execute.

⛔ Confirm by SYMBOL in the invariant-capture path before scoping a fix — this plan's own request
document is explicit that a hypothesis is not a premise.

## Adjacent, same snapshot, worth checking with it

`config_hash` drifted at **all four** phase boundaries (`93acf2ec -> d99761ec -> 5c58dcd5 ->
e8e8b3ea -> c7935ba6`) while the plan's 29-file merged footprint contains no configuration file at
all. Either something outside the plan mutated config four times in 13 hours, or the hash is not
stable across the contexts it is computed in. A drift signal that fires at 4/4 boundaries carries
no discriminating information either way — it cannot distinguish "config changed" from "hash is
noisy", which is the definition of a detector that cannot fail usefully.

## Solution

1. Resolve `main_sha` against an explicit main-checkout handle, never against cwd-relative `HEAD`.
2. Add a cheap assertion at capture time: `main_sha` must be an ancestor of `origin/main`. A
   captured value that is not is a capture bug, and should be recorded as `unknown` rather than
   as a confident wrong sha — the fail-closed discipline this very plan promoted.
3. Settle `config_hash` stability separately: determine whether the four drifts are real before
   the warning is trusted or suppressed.

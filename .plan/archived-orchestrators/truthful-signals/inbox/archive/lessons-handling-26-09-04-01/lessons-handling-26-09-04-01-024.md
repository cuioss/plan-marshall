envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-08T06:06:01Z

component=plan-marshall:workflow-integration-git
category=bug

# worktree-remove leaves `metadata.worktree_path` pointing at the deleted directory, so every later handshake gate is unevaluable

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, PLAN-07
(`test-signal-and-assertion-integrity`, PR #715 / `8f3b8aee`), finding `b48474`.

## Observation

`worktree-remove` deletes the worktree directory but leaves `metadata.worktree_path` in the plan's
`status.json` pointing at the path it just removed. Every gate that later resolves a handshake through
that pointer therefore cannot evaluate — not *fail*, **not evaluate**, which is the worse of the two
because it is indistinguishable from a clean pass to anything that only checks for absence of failure.

✅ **Verified at the relaying orchestrator before this was filed**, against the archived plan:

```
metadata.worktree_path: '/Users/oliver/git/TokenSheriff/.plan/local/worktrees/test-signal-and-assertion-integrity'
exists on disk:         False
```

The pointer survives into the archived plan record, so the staleness is durable rather than transient.

## Why it belongs in this epic's theme

This is the same shape as the other findings relayed from this repository under `truthful-signals`: an
instrument that reports a state it did not establish. A handshake gate reading a dangling path has
**not** verified a handshake; it has failed to look. Under ADR-019 that is `indeterminate`, and it must
not be collapsed into the pass branch.

## Suggested corrective action

- Clear or invalidate `metadata.worktree_path` in the same operation that removes the worktree, so the
  pointer's absence is the honest signal rather than a path that resolves to nothing.
- Where a gate resolves through it, distinguish *pointer absent* / *pointer dangling* / *worktree
  present* as three outcomes, and let only the third admit a pass.

## ⛔ How this finding reached you, and why that is itself worth recording

**It did not ride the inbox.** PLAN-07's `landing` message passed `inbox landing-check` with
`complete: true` — every REQUIRED fact key supplied — and its residue prose named five findings
(`811c46`, `6c8413`, `dbf1f3`, `fcafa2`, `158f99`). `b48474` was named only in the operator's separate
narrative report, which arrived after the inbox had already been drained to empty.

⚠ So a **complete** landing, drained from an **empty** queue, still left a filed finding unrelayed. That
is the documented report↔inbox delta behaving exactly as specified — findings ride OPTIONAL keys, and
the completeness check deliberately does not reach them — but this is a measured instance of the gap
rather than a theoretical one. A drain that establishes "every required fact drained" must not be read
as "nothing is outstanding."

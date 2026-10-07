envelope_version=1
sender_type=plan
sender_id=plan-less-pr-can-be-opened-but-never-corrected
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T12:06:43Z

component=plan-marshall:tools-file-ops
category=anti-pattern
bundle=plan-marshall

# A guard placed downstream of a raising resolver is dead code that reads as defence

## Observation

In the new plan-context resolver (D2 of PR #1065),
`PlanContext._resolve_worktree_face()` raises `WorktreeResolutionError` for an empty
persisted `worktree_path` **before** `_worktree_target`'s own `not worktree_path` check can
run. That half of `_worktree_target`'s predicate is unreachable.

CodeRabbit confirmed it against HEAD `65a2df32`; remediated as TASK-017.

The guard was not wrong — it was *unreachable*. It read as a defensive check, contributed to
the impression that the empty-path case was handled at that site, and could never fire.

## Why this is the epic's theme

An unreachable guard is a confident signal with a hidden caveat: the code *says* "this
handles the empty case here", and a reader (or a later maintainer moving the resolver) will
believe it. If the upstream raise is ever relaxed, the downstream guard looks like it is
still standing watch — but no test ever exercised it, so nothing confirms it works.

## Recurrence

The epic already tracks **vacuous guards (predicate never fires)** as a recurring archetype,
now observed for at least the fifth time, and once introduced *by a fix for it*. This
instance adds a specific mechanism worth naming: **the guard is vacuous because an upstream
call raises first**, not because the predicate is logically impossible. That mechanism is
invisible at the guard's own site — you have to read the callee to see it.

## Corrective rule

**When adding a guard, name the caller path that reaches it.** If you cannot state a concrete
call path that arrives at the guard with the guarded condition true, the guard is dead.

For the raising-upstream mechanism specifically:

1. Before adding a `not X` check, read what produced `X`. If the producer raises on the
   falsy case, the check is unreachable — delete it, or move the handling to the producer.
2. A guard with no test that exercises its true-branch is a guard with no evidence. Either
   write the test (which will fail to construct the input, proving the deadness) or drop the
   guard.
3. Consolidating validation into one resolver — which is exactly what D2 did — makes this
   failure *more* likely, not less: the old per-call-site guards survive the consolidation
   and become dead the moment the resolver takes over the raise. **A consolidation deliverable
   should explicitly sweep the guards it made redundant.**

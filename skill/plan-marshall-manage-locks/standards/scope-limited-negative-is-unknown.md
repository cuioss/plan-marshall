# Scope-limited negative is `unknown`, not `absent`

The invariant, stated once, structurally:

> **An empty result from a scope that could not have observed the subject is
> `unknown`, not `absent`.**

A store resolver anchored by the uniform cwd rule
(`file_ops.get_base_dir()` / `get_worktree_root()`, ADR-002) enumerates only the
tree the caller is pinned to. From a session pinned to its OWN worktree it is
structurally BLIND to a subject living in a SIBLING worktree — the subject is
outside the scope the resolver could ever have observed. An empty or absent result
under such a scope therefore carries no information about the subject's existence:
it means *not-observed-from-this-scope*, never *does-not-exist*.

Reading that scope-limited negative as authoritative absence, and driving a
destructive or existence-proof decision on it, is the bug this invariant forbids —
the `#948` incident, where a live merge-lock holder in a sibling worktree read as
absent from a worktree-scoped enumeration and its lock was released while it was
still live in another session.

## Relationship to ADR-009 (a generalization, not a new principle)

This is the scope-limited-enumeration face of
[ADR-009](../../../../../../doc/adr/009-Status_reporting_fails_closed_with_an_explicit_unknown_state.adoc)
(`Status reporting fails closed with an explicit unknown state`), NOT a distinct
principle and NOT grounds for a new ADR. ADR-009 governs the version-staleness read:
when a status surface cannot substantiate the positive property it reports, it must
model the third, evidence-absent state as a first-class `unknown` verdict rather
than fold it into the positive. The same structure applies verbatim here — the
"evidence" is *observation coverage*, and a scope that could not have observed the
subject has no evidence of absence:

| ADR-009 (version staleness) | This invariant (scope-limited enumeration) |
|-----------------------------|--------------------------------------------|
| Unresolvable installed manifest → `marshal_status: unknown`, never a vacuous `fresh` | Subject outside the resolver's scope → `unknown`, never a vacuous `absent` |
| Fail-closed: absence-of-evidence is not evidence of freshness | Fail-closed: absence-from-an-unobserving-scope is not evidence of non-existence |
| Third verdict is first-class across producer + every consumer | Scope-qualifier / main-anchored verdict is first-class at every authority-bearing consumer |

Defaulting a scope-limited negative to `absent` is the exact analogue of ADR-009's
rejected "default the unresolvable case to `stale`" alternative: it conflates an
evidence gap with a positive finding and produces a wrong, sometimes destructive,
decision.

## The two sanctioned resolutions

An authority-bearing consumer that must act on a subject's existence honours the
invariant in one of two ways:

1. **Route the decision through a main-anchored verdict.** When the subject lives
   in a bounded, cross-session-shared namespace, resolve it against the MAIN
   checkout (via `marketplace_paths.resolve_main_anchored_path`) so the answer is
   the same regardless of the caller's pinned worktree. This is what
   `_locks_core.holder_staleness` does: it composes the main-anchored
   `holder_is_dead` / `holder_has_live_worktree` predicates into an explicit
   `fresh` / `stale` / `unknown` verdict, and `merge_lock release --require-stale`
   gates the destructive lock removal on a provably `stale` verdict — refusing
   fail-closed on `fresh` or `unknown`.

2. **Carry a scope-qualifier so the consumer cannot mistake scope for census.**
   When the enumeration is inherently cwd-scoped, surface the scope as a
   first-class field so a consumer knows whether an absence is authoritative. This
   is what `manage-status list` / `git-workflow worktree-list` do: they emit a
   `scope` field (`main` / `worktree_local` / `unknown`), and a `worktree_local`
   census is documented as BLIND to sibling worktrees, so an absent entry under it
   is `unknown`, not `absent`.

The enumeration of every CWD-keyed store-resolution site and its fix-or-justify
disposition against this invariant lives in
[cwd-keyed-store-resolution-audit.md](cwd-keyed-store-resolution-audit.md).

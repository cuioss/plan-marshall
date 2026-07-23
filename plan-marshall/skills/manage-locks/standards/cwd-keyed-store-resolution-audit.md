# CWD-keyed store-resolution audit

An enumeration of every CWD-keyed store-resolution site across the plan/worktree
enumeration surface, each carrying a fix-or-justify disposition against a single
failure shape:

- **The shape — scope-limited negative read as authoritative absence.** A store
  resolver anchored by the uniform cwd rule (`file_ops.get_base_dir()` /
  `get_worktree_root()`, ADR-002) enumerates only the tree the caller is pinned to.
  From a session pinned to its OWN worktree it is structurally BLIND to a subject
  living in a SIBLING worktree, so an empty/absent result is *not-observed-from-this-scope*,
  NOT proof of non-existence. When an authority-bearing consumer reads that
  scope-limited negative as authoritative absence and drives a destructive or
  existence-proof decision on it, a live subject is mistaken for a dead one — the
  #948 incident, where `steward-provisioning-fail-closed` was judged stale from a
  worktree-scoped view and its merge lock released while it was live in a sibling
  worktree's session.

The governing decision is ADR-009 (`Status reporting fails closed with an explicit
unknown state`), generalized here to the scope-limited-enumeration case: an empty
result from a scope that could not have observed the subject is `unknown`, not
`absent`. The structural encoding of that invariant is
[`scope-limited-negative-is-unknown.md`](scope-limited-negative-is-unknown.md).

This is an enumeration (not a sample): every CWD-keyed store-resolution site in the
surveyed universe appears below with a disposition.

## The shared resolver (the anchor)

Every site below resolves its store through the ONE uniform cwd-relative resolver,
so the fix belongs at the authority-bearing CONSUMERS, not the resolver.

### tools-file-ops/scripts/file_ops.py

| Site | Disposition |
|------|-------------|
| `get_base_dir()` / `get_worktree_root()` | **JUSTIFY (the resolver, correct by design).** The single uniform cwd-relative resolver (ADR-002): it MUST resolve cwd-relatively so phase-5+ callers pinned to a worktree operate on their own tree. It is not itself authority-bearing — it never reads an absence and never decides. Critically it does NOT return an empty sentinel on failure: an unresolvable base raises `RuntimeError`, so a consumer cannot silently receive `""`/`None` and mistake it for an empty store. The scope-blindness is a property of the callers that CENSUS across trees; the fix is a scope-qualifier at those callers. |
| `guard_worktree_cwd(plan_id)` | **JUSTIFY (fail-safe / not-applicable direction).** Returns `None` (assertion not applicable) when the worktree root cannot be resolved or the canonical worktree dir is absent — it never fires a false positive from an unresolvable scope. A negative here suppresses an assertion, it does not authorize a destructive act. |

## Surveyed sites

### manage-status/scripts/_status_query.py

| Site | Disposition |
|------|-------------|
| `cmd_list` (the plan census) | **FIX (D3).** Enumerates `get_plans_dir()` + each `get_worktree_root()` child cwd-relatively. From the MAIN checkout this is comprehensive (main + every sibling worktree); from a PINNED worktree the same resolvers anchor at that worktree's own `.plan/local`, so the census sees only the worktree's own moved-in plan and is BLIND to siblings — the #948 shape when a consumer reads an absent plan as authoritative absence. Fixed by surfacing a first-class `scope` field (`main` / `worktree_local` / `unknown`, from `_resolution_scope`) so a consumer cannot silently mistake a cwd-scoped census for a global one; an absent plan under `worktree_local` is `unknown`, and the consumer must route a destructive decision through a main-anchored verdict (e.g. `merge_lock check` staleness). |
| `cmd_list_orphans` (orphan-GC discovery) | **JUSTIFY (fail-safe direction).** Resolves `get_plans_dir()` cwd-relatively and collects directories with no `status.json`. Its authority-bearing consumer (planning.md Step 3b GC) acts on POSITIVE detections only — an empty/under-scoped result yields NO deletion, so scope-blindness can only UNDER-detect (miss an orphan), never mis-delete a live sibling. The one hazardous case (an unreadable dir) already fails closed via the `<unreadable>` sentinel that forces a prompt rather than a silent delete. The failure shape (empty-read → authoritative absence → destructive act) requires positive detection to reach the destructive branch and therefore does not apply. |

### workflow-integration-git/scripts/git-workflow.py

| Site | Disposition |
|------|-------------|
| `cmd_worktree_list` | **FIX (D3).** Reads the `manage-status list` census (above) and filters it — it INHERITS that census's cwd-scoped blindness. Fixed by propagating the `scope` field verbatim from the underlying list output onto its own return (single-sourced in `cmd_list._resolution_scope`, never re-derived; a malformed/scope-less output fails closed to `unknown`). A consumer must not read an empty `worktree_local` listing as proof that no other worktree exists. |
| `cmd_locate_plan_checkout` | **JUSTIFY (already main-aware).** Resolves by two paths in order — the canonical `manage-status get-worktree-path` channel, then a STRUCTURAL `get_worktree_root() / {plan_id}` filesystem probe — so a phase-5+ plan MOVED into its worktree (invisible to the cwd-relative census) is still located. It returns `not_found` only after both probes miss, and `not_found` is a location report, not a destructive authorization. |
| `_plan_dir_on_current_checkout` | **JUSTIFY (positive-presence probe).** A boolean presence check (`{root}/.plan/local/plans/{id}/status.json` is a file) feeding `cmd_locate_plan_checkout`. A `False` from a cwd-scoped root is disambiguated by the caller's second (structural worktree) probe before any conclusion is drawn; it never stands alone as authoritative absence. |

### manage-lessons/scripts/_lessons_io.py

| Site | Disposition |
|------|-------------|
| `get_lessons_dir()` | **JUSTIFY (already main-anchored).** Resolves the lessons store via `resolve_main_anchored_path(DIR_LESSONS)` — the single sanctioned main-anchored resolver, NOT the cwd-relative `get_base_dir`. It therefore resolves to the SAME store regardless of which worktree the caller is pinned to, so a cross-session read is never scope-blind. `guard_component_store_match` additionally fails closed when a component's store does not match the resolved repo, so a foreign store cannot be silently written. This is the already-sound exemplar the FIX sites are brought toward. |

### manage-locks/scripts/_locks_core.py + merge_lock.py

| Site | Disposition |
|------|-------------|
| `holder_is_dead` / `holder_has_live_worktree` / `holder_staleness` | **JUSTIFY (D1 — the main-anchored exemplar).** All three anchor their liveness paths at the MAIN checkout via `_main_plan_local_base` → `resolve_main_anchored_path`, never a cwd-scoped enumeration, so a holder is judged correctly regardless of the caller's pinned worktree. `holder_staleness` returns the explicit three-valued verdict (`fresh` / `stale` / `unknown`) that models the evidence-absent state as first-class (ADR-009), never collapsing an unresolvable base into `stale`. This is the verdict the FIX sites above route destructive decisions through. |
| `merge_lock run_check` / `run_release --require-stale` | **JUSTIFY (D1 — routes the destructive decision through the main-anchored verdict).** The manual-release recovery path no longer infers death from a cwd-scoped enumeration: `--require-stale` gates the destructive lock removal on `holder_staleness(holder) == 'stale'`, failing closed (`refused`, `holder_not_provably_dead`) on `fresh`/`unknown`, and `check` surfaces the same verdict for the recovery recipe to consult. The removal itself uses the observed-file eviction arbitration rather than a blind unlink. |

## Summary

- **Two authority-bearing census sites require a scope-qualifier fix:** `cmd_list`
  and `cmd_worktree_list` (D3), each now surfacing a `scope` field so a
  `worktree_local` census cannot be silently read as a global one.
- **The destructive decision that motivated the audit** — the manual merge-lock
  release — is routed through the main-anchored `holder_staleness` verdict (D1),
  the exemplar the census consumers defer to.
- Every other enumerated site either resolves main-anchored already
  (`get_lessons_dir`, the `_locks_core` predicates), acts on positive detection only
  so scope-blindness can merely under-detect (`cmd_list_orphans`,
  `_plan_dir_on_current_checkout`), is already dual-probe main-aware
  (`cmd_locate_plan_checkout`), or is the resolver itself which raises rather than
  returning an empty sentinel (`get_base_dir` / `get_worktree_root`) — each
  justified above.
- No deferred tail: the surveyed universe is fully dispositioned here, so no
  follow-up split is recorded.

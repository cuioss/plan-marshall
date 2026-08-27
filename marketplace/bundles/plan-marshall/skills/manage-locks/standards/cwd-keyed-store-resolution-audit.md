# CWD-keyed store-resolution audit

An enumeration of CWD-keyed store-resolution sites across the plan/worktree
enumeration surface, each carrying a fix-or-justify disposition against a single
failure shape. The population, and the criterion that bounds it, are derived in
§ "Population, and how it was derived" rather than asserted here.

- **The shape — a scope-limited read taken as authoritative.** A store resolver
  anchored by the uniform cwd rule (`file_ops.get_base_dir()` /
  `get_worktree_root()`, ADR-002) enumerates only the tree the caller is pinned to.
  From a session pinned to its OWN worktree it is structurally BLIND to a subject
  living in a SIBLING worktree — and equally blind to the fact that whatever it DID
  find is its own tree's copy rather than the one it was asked about. The shape has
  **two polarities, and a destructive consumer has existed for each**:
  - **Negative read as authoritative absence.** An empty/absent result is
    *not-observed-from-this-scope*, NOT proof of non-existence, so a live subject is
    mistaken for a dead one — the sibling-worktree case, where
    `steward-provisioning-fail-closed` was judged stale from a worktree-scoped view
    and its merge lock released while it was live in a sibling worktree's session.
  - **Positive read as authoritative presence.** A hit proves only that the subject
    exists *in the scope that was searched*, NOT that it exists where the consumer
    needs it to be. The move-back guard in `cmd_worktree_remove` is this polarity:
    cwd-pinned inside the worktree it was about to destroy, it found the plan
    directory in that very worktree and read the hit as proof the state had already
    landed back on main.

  Both polarities end the same way — an authority-bearing consumer drives a
  destructive or existence-proof decision on a reading its scope could not support.
  A disposition that clears only one polarity has not cleared the site.

The governing decision is ADR-009 (`Status reporting fails closed with an explicit
unknown state`), generalized here to the scope-limited-enumeration case: an empty
result from a scope that could not have observed the subject is `unknown`, not
`absent`. The structural encoding of that invariant is
[`scope-limited-negative-is-unknown.md`](scope-limited-negative-is-unknown.md).

## Population, and how it was derived

The universe this audit dispositions is the **plan/worktree enumeration surface**:
sites that resolve a store through the cwd-relative resolver and feed an
authority-bearing consumer that draws an existence conclusion from the result. That
criterion — not the word "every" — is what a later reader re-derives against.

**Method.** `architecture search --content` over the crawled file inventory, scoped
`--category script` so exactly one module attribution is read. Classifying a single
file's matches into definition / cross-reference / call site needs a `Read` of that
file as a second step, because `search` deliberately returns no line numbers and no
line bodies. Every figure below is therefore reproducible by the same two moves; no
number here is asserted from reading alone.

**⛔ Sum `match_count` over ONE attribution — never read the top-level `count`.**
`count` is a count of result ROWS, and this repository indexes each file under two
module attributions (`default`/`source` and `plan-marshall`/`script`), so an unscoped
sweep returns two rows per file. For `_plan_dir_on_current_checkout` the unscoped
sweep reports `count: 6` over `file_count: 3` — that 6 is 3 files x 2 attributions,
and it is **not** an occurrence count. The occurrence figure is the sum of the
per-row `match_count` (non-overlapping matches per file) over one attribution: 3 in
`git-workflow.py`, 4 in this audit, and 1 in `test_git_workflow_worktree.py` =
**8 occurrences over 3 distinct files**.

**6 and 8 are one sweep read two ways**, and the gap between them is the whole
hazard. `count` answers "how many attributed rows matched", `file_count` answers
"how many files contain this", and only the `match_count` sum answers "how many
occurrences" — three different questions whose answers sit close enough together to
be mistaken for each other, and which coincide outright often enough that a match
between them proves nothing.

**An agreement between `count` and a hand itemization is meaningless, not
reassuring.** Reading `count` as an occurrence count is one error; an itemization
that misses or double-counts an occurrence is a second; and the two cancel, so the
pair agrees while both figures are wrong. Agreement is therefore never evidence that
either was computed correctly. Verify the method rather than the coincidence: sum
`match_count` over one attribution, and read `file_count` for the file total.

**Why this audit is in its own population.** The sweep scans every inventoried file,
documentation included, so the 4 occurrences attributed to this audit are its own
prose: one in this section, one in the `git-workflow.py` table, and two in the
Summary. That is the
counted population behaving correctly, not contamination; but it does mean the
figure moves whenever this document is edited, which is exactly why the method is
published beside the number instead of the number alone. A reader who finds a
different total should re-run the sweep rather than assume either figure is wrong.

**Resolver-consumer population (derived).** `get_base_dir()` resolves in 15 distinct
script files and `get_worktree_root()` in 8; three files (`file_ops.py`,
`constants.py`, `_status_query.py`) carry both, so the union is **20 distinct script
files**. This audit dispositions the members of that union which meet the
enumeration-surface criterion above, plus the lessons and lock store resolvers that
reach the same failure shape without passing through either cwd resolver. The
residue — resolvers used to locate `.plan/` for a caller's own reads and writes,
which enumerate nothing and conclude nothing about existence — is **out of universe,
not a deferred tail**.

**Coverage.** Every sweep quoted here returned `unreadable: []`, `truncated: false`
and `elided: []`, so each enumeration is complete to the inventory's edge.
**Inventory-scope caveat:** the crawl does not walk `.plan/`, `.claude/**`,
`.github/**`, or anything a `.gitignore` rule excludes. A negative from these sweeps
is *"not in any inventoried file"* — never *"not in the tree"*.

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
| `cmd_list` (the plan census) | **FIX (D3).** Enumerates `get_plans_dir()` + each `get_worktree_root()` child cwd-relatively. From the MAIN checkout this is comprehensive (main + every sibling worktree); from a PINNED worktree the same resolvers anchor at that worktree's own `.plan/local`, so the census sees only the worktree's own moved-in plan and is BLIND to siblings — the sibling-worktree shape when a consumer reads an absent plan as authoritative absence. Fixed by surfacing a first-class `scope` field (`main` / `worktree_local` / `unknown`, from `_resolution_scope`) so a consumer cannot silently mistake a cwd-scoped census for a global one; an absent plan under `worktree_local` is `unknown`, and the consumer must route a destructive decision through a main-anchored verdict (e.g. `merge_lock check` staleness). |
| `cmd_list_orphans` (orphan-GC discovery) | **JUSTIFY (fail-safe direction).** Resolves `get_plans_dir()` cwd-relatively and collects directories with no `status.json`. Its authority-bearing consumer (planning.md Step 3b GC) acts on POSITIVE detections only — an empty/under-scoped result yields NO deletion, so scope-blindness can only UNDER-detect (miss an orphan), never mis-delete a live sibling. The one hazardous case (an unreadable dir) already fails closed via the `<unreadable>` sentinel that forces a prompt rather than a silent delete. The failure shape (empty-read → authoritative absence → destructive act) requires positive detection to reach the destructive branch and therefore does not apply. |

### workflow-integration-git/scripts/git-workflow.py

| Site | Disposition |
|------|-------------|
| `cmd_worktree_list` | **FIX (D3).** Reads the `manage-status list` census (above) and filters it — it INHERITS that census's cwd-scoped blindness. Fixed by propagating the `scope` field verbatim from the underlying list output onto its own return (single-sourced in `cmd_list._resolution_scope`, never re-derived; a malformed/scope-less output fails closed to `unknown`). A consumer must not read an empty `worktree_local` listing as proof that no other worktree exists. |
| `cmd_locate_plan_checkout` | **JUSTIFY (already main-aware).** Resolves by two paths in order — the canonical `manage-status get-worktree-path` channel, then a STRUCTURAL `get_worktree_root() / {plan_id}` filesystem probe — so a phase-5+ plan MOVED into its worktree (invisible to the cwd-relative census) is still located. It returns `not_found` only after both probes miss, and `not_found` is a location report, not a destructive authorization. |
| `_plan_dir_on_current_checkout` | **JUSTIFY — scoped to its one caller, and to BOTH polarities of its return.** A boolean presence check (`{root}/.plan/local/plans/{id}/status.json` is a file) resolved through the cwd walk-up. **Derived caller set: exactly one** — `cmd_locate_plan_checkout`. The derivation is the sweep in § "Population, and how it was derived": of the helper's 3 occurrences in `git-workflow.py`, a `Read` of that file classifies them as one definition, one `:func:` docstring cross-reference, and exactly one call. The count is what makes "one caller" a finding rather than a claim: naming a caller establishes that it calls, never that it is the only one that does. **The justification is scoped to that caller and does not travel with the helper, because neither polarity is safe standing alone.** A `False` is *not-observed-from-this-scope* and is disambiguated here by the caller's second (structural worktree) probe before any conclusion is drawn. A `True` is the mirror — authoritative *presence*, equally scope-limited: from a session pinned inside a worktree the probe finds that worktree's own plan dir and reports it as present on "the current checkout". In this caller that is harmless, because presence is reported as a location (`location: current`) and nothing is destroyed on the strength of it. In a destructive consumer it is not — see the `cmd_worktree_remove` row below, where exactly that `True` was read as proof the plan state had moved back to main. |
| `cmd_worktree_remove` (the move-back guard) | **FIXED (D1, D2) — the positive-polarity instance of this audit's failure shape.** Before destroying a worktree the guard must answer "has the plan directory landed back on **main**?". Asked through the cwd walk-up, it resolved through whichever checkout the caller happened to stand in, so a caller cwd-pinned inside the worktree being removed found the plan dir *in that worktree* and read the resulting `True` as "moved back" — authorizing destruction of the sole authoritative copy of the plan's state. Note the polarity: the destructive branch was reached by a scope-limited **positive**, not by an empty read. Fixed by asking a predicate anchored on the tree it protects — `_plan_dir_on_main_checkout` resolves via `marketplace_paths.main_checkout_root` (git's common dir, which points at main even from a linked worktree), so the verdict is cwd-independent. It **fails closed**: an unresolvable main root returns `False`, which is never evidence that the move-back happened. It accepts both main-resident shapes — the live record `integrate_into_main` moves back, and the date-prefixed archived record `manage-status archive` writes — so the structural-probe fallback that exists to reach an archived plan's worktree is not refused by the very guard that follows it. The refusal (`plan_dir_not_moved_back`) is not overridable by `--force`, which keeps its dirty-tree meaning only. A second, independent refusal (`cwd_inside_removal_target`) rests on a plain containment test rather than on the same predicate, so the two failure modes do not both ride on one probe. |

### manage-lessons/scripts/_lessons_io.py

| Site | Disposition |
|------|-------------|
| `get_lessons_dir()` | **JUSTIFY (the RESOLVER is already main-anchored — this claim covers the resolver only).** Resolves the lessons store via `resolve_main_anchored_path(DIR_LESSONS)` — the single sanctioned main-anchored resolver, NOT the cwd-relative `get_base_dir`. It therefore resolves to the SAME store regardless of which worktree the caller is pinned to, so a cross-session read through it is never scope-blind. `guard_component_store_match` additionally fails closed when a component's store does not match the resolved repo, so a foreign store cannot be silently written. **Scope of this row:** it dispositions the resolver, NOT the lesson path as a whole. This audit never surveyed the resolver's CONSUMERS, and that is where the could-not-look-reports-benign collapse actually lived — including one consumer (`manage-status/scripts/_cmd_lifecycle.py::_restore_lesson_from_plan_dir`) that bypassed this resolver entirely via `base_path('lessons-learned')`. Those consumers are enumerated and dispositioned in the sibling audit [`../../manage-lessons/standards/cwd-keyed-store-resolution-audit.md`](../../manage-lessons/standards/cwd-keyed-store-resolution-audit.md). |

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
- **The shape has a second polarity, and that is the one that cut.** The move-back
  guard in `cmd_worktree_remove` reached its destructive branch on a scope-limited
  `True` — authoritative *presence* — not on an empty read. It is fixed (D1, D2) by
  the main-anchored `_plan_dir_on_main_checkout`. `_plan_dir_on_current_checkout`
  MUST NOT be grouped with `cmd_list_orphans` on the strength of both "acting on
  positive detection": for `cmd_list_orphans` a positive detection is an observation
  of something really there, so scope-blindness can only under-detect; for the
  move-back guard a positive detection WAS the destructive authorization, so
  scope-blindness mis-authorized. Same phrase, opposite safety property — which is
  exactly why the grouping read as safe.
- Every remaining enumerated site either resolves main-anchored already
  (`get_lessons_dir`, the `_locks_core` predicates), acts on positive detection whose
  worst case is under-detection (`cmd_list_orphans`), is already dual-probe main-aware
  (`cmd_locate_plan_checkout`, the sole derived caller of
  `_plan_dir_on_current_checkout`), or is the resolver itself which raises rather than
  returning an empty sentinel (`get_base_dir` / `get_worktree_root`) — each
  justified above. For `get_lessons_dir` that justification is **scoped to the
  resolver**; its consumers are a separate surveyed universe with its own
  dispositions (next bullet).
- **The lesson path's CONSUMERS are surveyed elsewhere.** This audit's population
  is the plan/worktree enumeration surface, so it reached the lessons resolver but
  not the sites that consume it — and a consumer can carry the failure shape even
  when its resolver does not, either by collapsing an unreachable store into a
  benign zero or by bypassing the resolver outright. That population is derived
  from the store-path sweep (not from any roster) and dispositioned in
  [`../../manage-lessons/standards/cwd-keyed-store-resolution-audit.md`](../../manage-lessons/standards/cwd-keyed-store-resolution-audit.md).
- **Completeness here is derived, not asserted.** The population, the method, the
  field summed (`match_count`), the attribution it was summed over, the
  self-inclusion of this document, and the inventory-scope caveat are all published
  in § "Population, and how it was derived", so a later reader re-derives rather
  than trusts. Within the enumeration-surface criterion stated there, every site is
  dispositioned above; the resolver-consumer residue outside that criterion is named
  there as out of universe rather than left as an unstated tail. The lesson-store
  consumer surface is likewise not a deferred tail of this audit — it is a distinct
  population with its own complete enumeration in the sibling audit above.

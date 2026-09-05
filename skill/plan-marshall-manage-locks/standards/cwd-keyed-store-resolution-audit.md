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
`absent`. That generalization — and its structural encoding in
[`scope-limited-negative-is-unknown.md`](scope-limited-negative-is-unknown.md) —
states the **negative polarity only**, in its title and throughout. The positive
polarity is not covered there and must not be read out of it: a scope-limited hit is
likewise `unknown` presence, never authoritative presence, and it is governed by the
two-polarity statement above. The omitted side is the one that actually cut here —
the move-back guard reached its destructive branch on a scope-limited `True`, not on
an empty read — so a site checked only against that encoding has been checked
against half the invariant.

## Population, and how it was derived

The universe this audit dispositions is the **plan/worktree enumeration surface**:
sites that resolve a store through the cwd-relative resolver and feed an
authority-bearing consumer that draws an existence conclusion from the result. That
criterion — not the word "every" — is what a later reader re-derives against.

**Method.** `architecture search --content` over the crawled file inventory, scoped
`--category script`. The inventory indexes each file twice — once under the `default`
module with a generic category, once under its OWNING module with a specific one — so
`--category script` keeps only the owning-module row and each script file contributes
exactly one row. It bounds the CATEGORY, not the module: the surviving rows span every
bundle that owns a script, which is why a `pm-plugin-development` file appears in the
resolver-consumer sweeps below. Classifying a single
file's matches into definition / cross-reference / call site needs a second step,
because `search` deliberately returns no line numbers and no line bodies — and,
being a regex over bytes, it cannot distinguish a call from a comment at all.
Narrowing the pattern to a discriminating literal does **not** substitute for that
step: a parenthesised `get_base_dir(` matches a comment and a `def` line exactly as
it matches a call, so the narrowed figure is still textual. Where the criterion is
"is this a CALL", the classification is therefore made by parsing the candidate with
`ast`, as specified in § "Resolver-consumer population (derived)" below; where a
`Read` of a single file suffices, that `Read` is named. Every figure below is
reproducible by those moves; no number here is asserted from reading alone.

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

**Resolver-consumer population (derived).** The criterion is that a resolving caller
INVOKES the resolver — and **no text sweep can apply that criterion**.
`architecture search --content` is a regex over bytes, so a narrowed `get_base_dir(`
pattern matches a comment, a docstring and a `def` line exactly as it matches a call.
Narrowing to the parenthesis therefore does not separate the classes; it only makes a
textual figure look like a criterion-bearing one. The population is instead derived in
two stages: a text sweep bounds the CANDIDATES, then an AST pass CLASSIFIES them.

**Stage 1 — candidate set (text, superset by construction).** Two bare-name sweeps,
both `architecture search --content --literal --category script`:

| `--pattern` | `file_count` |
|-------------|--------------|
| `get_base_dir` | 17 |
| `get_worktree_root` | 8 |

Union: **22 distinct candidate files**. The bare name is used deliberately: a call
always contains it, so this set provably contains every call site. The parenthesised
form is not used at any stage — it excludes nothing a call can hide behind, while
admitting every comment that happens to write the parenthesis.

**Stage 2 — classification (AST, call-aware).** Parse each candidate with Python's
`ast` module and classify every occurrence of each target name:

| Class | AST shape | Counts as a call? |
|-------|-----------|-------------------|
| **call** | `ast.Call` whose `func` is `Name(id=target)` or `Attribute(attr=target)` | **yes — this is the population** |
| definition | `FunctionDef` / `AsyncFunctionDef` named target | no |
| import | `Import` / `ImportFrom` alias binding the name | no |
| reference | a non-`Store` `Name` / `Attribute` load that is not a call's `func` | no (reported — an indirect-call risk) |
| text-only residue | textual occurrences minus AST-visible ones: comments, docstrings, plain string literals | no — invisible to the AST by construction |

**Alias resolution is part of the method, not a refinement.** `from file_ops import
get_base_dir as X` binds the resolver to a local name that no longer contains the
target substring, so any classifier matching on the name alone — textual **or**
AST — under-counts callers by exactly the aliased sites. The pass therefore builds the
`asname → target` map first and then counts calls to the bound local name. Exactly one
such alias exists in the candidate set:
`tools-script-executor/scripts/generate_executor.py:150`
(`from file_ops import get_base_dir as _get_plan_base_dir`), and it **is** invoked, at
lines 168 and 172. That file is a genuine `get_base_dir` caller that every name-matching
derivation reports as a mention, and it is the single reason the figures below read
10 / 14 rather than 9 / 13. Its signature is a *negative* text-only residue: the AST sees
more occurrences than the text sweep does.

**Figures (derived).**

| Set | Files |
|-----|-------|
| `get_base_dir` callers | **10** |
| `get_worktree_root` callers | **6** |
| Callers of both (intersection) | **2** |
| **Union — the resolver-consumer population** | **14** |

The intersection is `tools-file-ops/scripts/file_ops.py` and
`manage-status/scripts/_status_query.py`, so the union is 10 + 6 − 2 = **14 distinct
script files**. The remaining **8 candidates are mention-only** and excluded:
`manage-execution-manifest/scripts/manage-execution-manifest.py`,
`manage-locks/scripts/_locks_core.py`,
`manage-locks/scripts/merge_lock.py`, `plan-doctor/scripts/plan_doctor.py`,
`tools-file-ops/scripts/constants.py`, `tools-integration-ci/scripts/ci_base.py`,
`workflow-integration-github/scripts/github_ops.py`, and
`pm-plugin-development/skills/plugin-doctor/scripts/_analyze_plan_path_in_scripts.py`.

**The definition site is excluded as a definition, and included on other evidence.**
`tools-file-ops/scripts/file_ops.py` holds the sole `def` of BOTH resolvers
(`get_worktree_root` at line 174, `get_base_dir` at line 369). A definition is not a
call, so neither `def` puts the file in the population. It is nonetheless a member,
on independent evidence: it separately *invokes* `get_base_dir` (lines 196, 431) and
`get_worktree_root` (line 234). The distinction matters because it is exactly the one a
textual criterion cannot draw.

**The counter-example that decides the method.**
`tools-file-ops/scripts/constants.py` matches both bare names *and* both parenthesised
forms, yet invokes neither. Its single `get_base_dir` occurrence is inside a comment at
line 251 — ``# module-scope `PLAN_BASE_DIR = get_base_dir()` would bind the base
directory at import time`` — which exists precisely to explain why this side-effect-free
constants module makes no such call. A parenthesis-narrowed textual criterion counts that
comment as an invocation and places the file in the intersection of both resolvers; the
file calls neither and is not in the population at all.

**Re-derivation.** Run the two Stage-1 sweeps for the candidate set, then apply the
Stage-2 table to each candidate with `ast.parse` — building the alias map before
counting calls, and treating the four non-call classes as exclusions. The classifier is
~40 lines of stdlib `ast` and is fully specified by the table above; a later reader
re-runs it rather than trusting these numbers, and a disagreement is resolved by
comparing classifications per file, not totals.

These figures are scoped `--category script`, so documentation is outside them and
**this document is not in its own resolver-consumer population**: editing this prose
cannot move any of them.

This audit dispositions the members of that union which meet the
enumeration-surface criterion above, plus the lessons and lock store resolvers that
reach the same failure shape without passing through either cwd resolver. The
residue — resolvers used to locate `.plan/` for a caller's own reads and writes,
which enumerate nothing and conclude nothing about existence — is **out of universe,
not a deferred tail**.

**Coverage.** Every sweep quoted here returned `unreadable: []`, `truncated: false`
and `elided: []`, so each enumeration is complete to the inventory's edge. The Stage-2
pass walked **453** `*.py` files under `marketplace/` — a strict superset of the
`*/skills/*/scripts/` tree the `--category script` sweeps bound — and found **no**
candidate outside those script directories, **no** parse error, and **no** non-call
reference, so there is no indirect-call residue beyond the one resolved alias.
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
| `_plan_dir_on_current_checkout` | **JUSTIFY — scoped to its one caller, and to BOTH polarities of its return.** A boolean presence check (`{root}/.plan/local/plans/{id}/status.json` is a file) resolved through the cwd walk-up. **Derived caller set: exactly one** — `cmd_locate_plan_checkout`. The derivation is the sweep in § "Population, and how it was derived": of the helper's 3 occurrences in `git-workflow.py`, the Stage-2 AST classification resolves them as one definition (line 2520), one call (line 2566), and one text-only residue — the `:func:` docstring cross-reference. Exactly one call, in exactly one file, by the same call-aware criterion the resolver-consumer population is derived under. The count is what makes "one caller" a finding rather than a claim: naming a caller establishes that it calls, never that it is the only one that does. **The justification is scoped to that caller and does not travel with the helper, because neither polarity is safe standing alone.** A `False` is *not-observed-from-this-scope* and is disambiguated here by the caller's second (structural worktree) probe before any conclusion is drawn. A `True` is the mirror — authoritative *presence*, equally scope-limited: from a session pinned inside a worktree the probe finds that worktree's own plan dir and reports it as present on "the current checkout". In this caller that is harmless, because presence is reported as a location (`location: current`) and nothing is destroyed on the strength of it. In a destructive consumer it is not — see the `cmd_worktree_remove` row below, where exactly that `True` was read as proof the plan state had moved back to main. |
| `cmd_worktree_remove` (the move-back guard) | **FIXED (D1, D2) — the positive-polarity instance of this audit's failure shape.** Before destroying a worktree the guard must answer "has the plan directory landed back on **main**?". Asked through the cwd walk-up, it resolved through whichever checkout the caller happened to stand in, so a caller cwd-pinned inside the worktree being removed found the plan dir *in that worktree* and read the resulting `True` as "moved back" — authorizing destruction of the sole authoritative copy of the plan's state. Note the polarity: the destructive branch was reached by a scope-limited **positive**, not by an empty read. Fixed by asking a predicate anchored on the tree it protects — `_plan_dir_on_main_checkout` resolves via `marketplace_paths.resolve_main_anchored_path`, the single sanctioned main-anchored resolver, so the verdict is cwd-independent. That resolver rather than a raw `main_checkout_root` walk, because it is the same call the plan dir's PRODUCER uses: `integrate_into_main` computes its move-back destination as `resolve_main_anchored_path('plans/{plan_id}')`, so guard and producer derive one path by one mechanism — and it honours the `PLAN_BASE_DIR` / `set_base_dir()` override, which a git-common-dir walk does not, so the two do not diverge whenever an override is active. It **fails closed**: an unresolvable main anchor returns `False`, which is never evidence that the move-back happened. It accepts both main-resident shapes — the live record `integrate_into_main` moves back, and the date-prefixed archived record `manage-status archive` writes — so the structural-probe fallback that exists to reach an archived plan's worktree is not refused by the very guard that follows it. The refusal (`plan_dir_not_moved_back`) is not overridable by `--force`, which keeps its dirty-tree meaning only. A second, independent refusal (`cwd_inside_removal_target`) rests on a plain containment test rather than on the same predicate, so the two failure modes do not both ride on one probe. |

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
- **Completeness here is derived, not asserted.** § "Population, and how it was
  derived" publishes each derivation in full rather than its number alone. For the
  occurrence figure: the field summed (`match_count`), the attribution it was summed
  over, and this document's self-inclusion. For the resolver-consumer population: the
  two bare-name sweeps that bound the 22 candidates, the AST classification table that
  separates a call from a definition, an import, a bare reference and a
  comment/docstring, the alias resolution without which the count is short by one, the
  8 mention-only files the criterion excludes, and the dual-carry subtraction behind
  the union. **A textual sweep cannot make this population.** A parenthesis-narrowed
  `file_count` is not an invocation figure: it counts the comment in
  `tools-file-ops/scripts/constants.py` as a call, placing a file that invokes neither
  resolver into the intersection of both. The inventory-scope caveat bounds
  the derivation, and a later reader therefore re-derives rather than trusts —
  resolving any disagreement by comparing per-file classifications rather than
  totals. Within the
  enumeration-surface criterion stated there, every site is
  dispositioned above; the resolver-consumer residue outside that criterion is named
  there as out of universe rather than left as an unstated tail. The lesson-store
  consumer surface is likewise not a deferred tail of this audit — it is a distinct
  population with its own complete enumeration in the sibling audit above.

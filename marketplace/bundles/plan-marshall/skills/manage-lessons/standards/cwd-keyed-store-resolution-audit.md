# CWD-keyed store-resolution audit (lessons store)

An enumeration of every site that resolves the **lessons-learned store**, each
carrying a fix-or-justify disposition against **both** failure directions.

The sibling audit in
[`manage-locks/standards/cwd-keyed-store-resolution-audit.md`](../../manage-locks/standards/cwd-keyed-store-resolution-audit.md)
surveys the plan/worktree enumeration surface and dispositions the lessons
*resolver* as already-sound. This audit surveys what that one did not: the
resolver's **consumers**, which is where the collapse actually lives.

## The two failure directions

A site is dispositioned against both, because closing one leaves the other open:

- **Direction A — could-not-look reports benign.** The site fails to reach the
  store (an unresolvable anchor, an absent directory) and returns the SAME
  answer it returns for a store it read and found empty. The caller cannot tell
  `stalled_count: 0` / `action: no_lesson_file` / `0 removed, 0 promoted` from
  "I never looked", so a stranded lesson reports as a clean corpus.
- **Direction B — looked in the wrong store.** The site resolves the store
  through a cwd-keyed resolver (`file_ops.base_path()` / `get_base_dir()`)
  rather than the main-anchored one, so a worktree-pinned caller reads or writes
  a *different*, ephemeral corpus. The answer is well-formed and confidently
  wrong, and on a write path the worktree's copy is discarded when the worktree
  goes away.

The governing decision is ADR-009 (*Status reporting fails closed with an
explicit unknown state*): a result from a scope that could not have observed the
subject is `unknown`, not `absent`. The lesson-path realization of that
invariant is the three-value discriminator
(`_lessons_io.STORE_RESOLUTIONS` = `main_anchored` / `override` / `unresolved`)
that every consumer below reports.

## Population derivation

The population predicate is **the store itself, not a roster of verbs**. This is
load-bearing: a roster-derived population is closed under the roster, so it
excludes by construction any resolver living outside it — which is exactly how
`manage-status/scripts/_cmd_lifecycle.py::_restore_lesson_from_plan_dir` stayed
invisible through the prior audit. That helper is in no `manage-lessons` verb
list and in no finalize-step roster, yet it carried all of Direction A, all of
Direction B, and destroyed the only copy of a colliding lesson.

The population is the union of three content sweeps over the full inventory,
minus incidental prose mentions that resolve nothing:

| # | Sweep | `files_scanned` | `unreadable` | `truncated` | `elided` | Distinct hits |
|---|-------|-----------------|--------------|-------------|----------|---------------|
| 1 | `architecture search --content --literal --pattern get_lessons_dir` | 4245 | 0 | false | (none) | 7 |
| 2 | `architecture search --content --literal --pattern DIR_LESSONS` | 4245 | 0 | false | (none) | 6 |
| 3 | `architecture search --content --literal --pattern lessons-learned` | 4245 | 0 | false | (none) | 69 |

Every sweep reports the complete-coverage conjunction (`unreadable: 0`,
`truncated: false`, `elided: []`), so a negative is trustworthy over the crawled
inventory and the derivation is not a sample.

Sweep 3 is the arm that catches a resolver bypassing both of the others — it is
what surfaces a bare `'lessons-learned'` literal handed to a cwd-keyed resolver,
the exact shape of `base_path('lessons-learned')`. Sweeps 1 and 2 alone would
have reported the lesson path clean.

**Resulting population size: 11 members derived from the sweeps**, plus **1
member added from the finalize-step roster** because it lives outside the
crawled inventory (see the coverage boundary below) — **12 members dispositioned
in total**.

**Derivation arms for a mechanical re-derivation.** A checker reproducing this
population over the marketplace script tree matches a file when it (a) calls a
canonical resolver — `get_lessons_dir` **or** `resolve_lesson_store`, (b)
imports the `DIR_LESSONS` constant, or (c) carries a bare `'lessons-learned'`
literal. Arm (a) must name **both** resolvers: the store handle is the migration
target, so a checker watching only `get_lessons_dir` would stop covering
precisely the consumers a migration just fixed.

**Inventory-coverage boundary (stated, not left implicit).** The sweeps cover the
crawled inventory only. Dotfile trees outside the allowlist are **not** searched,
so `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md` — a genuine
consumer of the corpus — cannot be derived from them. It is added from the
declared project-local finalize-step roster and dispositioned below. This
coverage gap is recorded rather than reported as a clean negative: a sweep whose
coverage is partial is partial.

## Dispositions

### script-shared/scripts/marketplace_paths.py

| Site | Direction | Disposition |
|------|-----------|-------------|
| `resolve_main_anchored_path(subpath)` | A, B | **JUSTIFY (the anchor, correct by design).** THE single sanctioned main-anchored exception resolver (ADR-002): test override first, then `git rev-parse --git-common-dir`, so it resolves to the MAIN checkout regardless of caller cwd. Direction B cannot originate here. For Direction A it does the right thing structurally — it RAISES `RuntimeError` when git cannot resolve rather than returning an empty sentinel, so a consumer cannot silently receive `None`/`""` and render it as an empty store. The fail-open was never in this function; it was in consumers that either bypassed it (Direction B) or caught its absence and reported it as a zero (Direction A). |

### tools-file-ops/scripts/constants.py

| Site | Direction | Disposition |
|------|-----------|-------------|
| `DIR_LESSONS = 'lessons-learned'` | — | **JUSTIFY (declaration, resolves nothing).** The single canonical spelling of the store's directory name. It is a constant, not a resolver: it performs no anchoring and can carry neither failure direction. It is in the population because naming the store through this constant is one of the three ways a real resolution site is found. |

### tools-file-ops/scripts/file_ops.py

| Site | Direction | Disposition |
|------|-----------|-------------|
| `base_path(subpath)` / `get_base_dir()` | B | **JUSTIFY (the cwd-keyed resolver — correct for its own contract).** The uniform cwd-relative resolver (ADR-002). It MUST resolve cwd-relatively so a phase-5+ caller pinned to a worktree operates on its own tree, and it raises rather than returning an empty sentinel. The Direction-B defect was never this function returning a wrong answer — it was a CALLER handing it a store that is main-anchored by design (`base_path('lessons-learned')`). The fix therefore belongs at that caller, and it landed there: a content sweep for `base_path('lessons-learned')` now returns **0 hits** across the full inventory. |

### manage-lessons/scripts/_lessons_io.py

| Site | Direction | Disposition |
|------|-----------|-------------|
| `resolve_lesson_store(subpath)` | A, B | **EXTENDED (the explicit store handle).** The named handle this audit's consumers are expressed in terms of. It returns the resolved path **together with** how it resolved over the closed `STORE_RESOLUTIONS` vocabulary, and it never raises — an unresolvable store comes back as `resolution: unresolved` with `path: None` so a caller must *report* the state rather than swallow an exception into a zero. This is the primitive that makes Direction A expressible at all. |
| `get_lessons_dir()` | A, B | **JUSTIFY (main-anchored, now expressed in terms of the handle).** Resolves via the main-anchored anchor, so Direction B cannot originate here. It keeps its bare-`Path` signature for the many callers that only need the location, and RAISES on an unresolvable store — a caller with no discriminator to report cannot silently proceed against a store it never reached. The prior audit's disposition of this function as sound is correct **for the resolver**; that claim never extended to its consumers, and the sibling audit's row has been narrowed accordingly. |
| `guard_component_store_match(...)` | B | **JUSTIFY (already fails closed).** Refuses to file a lesson whose bundle prefix the resolved store repo does not own, raising `WrongStoreError` rather than writing into a foreign store. A wrong-store write is refused, not silently performed. |

### manage-lessons/scripts/_lessons_query.py

| Site | Direction | Disposition |
|------|-----------|-------------|
| `cmd_restore_from_plan` | A, B | **FIX (D1).** The defect: `action: no_lesson_file` for a plan directory that does not exist — Direction A exactly, "I could not look" rendered as "I looked and it was empty". Now reports four outcomes over the closed `RESTORE_ACTIONS` vocabulary, modelled on `_orchestrator_inbox.cmd_inbox_list`'s three-state triple: `restored` (every carried file landed), `restore_incomplete` (the move aborted on a collision or traversal guard, with `restored_count` stating how many landed first — possibly none), `no_lesson_file` (the directory GENUINELY resolved and was scanned), and the non-benign `plan_dir_unresolved` returned as a structured `status: error`. `store_resolution` sub-discriminates an unreachable store from a resolved store that does not hold the named plan, closing Direction B on the same path. Every branch emits the full documented field set through `_restore_payload`. |
| `cmd_list_stalled` | A, B | **FIX (D1).** Carried Direction A twice over. Its `plans_root` non-existence early return was a bare `stalled_count: 0`; its population was additionally gated on `status.metadata.plan_source` matching a lesson-id regex, which excludes every `convert-to-plan`-carried plan (whose `plan_source` is unset) — so the verb reported a clean zero over a population that had already discarded the plans it exists to find. The population is now derived from the OBSERVABLE presence of a `lesson-*.md` file; the `plan_source` gate is removed outright; an absent plans root is the non-faulting `plans_root_state: missing`; an unresolvable store is a structured `store_unresolved` error reporting the resolution of the store that actually failed — never a sibling's resolved value — alongside `plans_root_state: unknown` and the `unresolved_store` name; a plan whose `status.json` cannot be read is surfaced in `unclassifiable_plans` instead of being silently skipped out of the population; and the inverse direction — a carried lesson id that ALREADY exists in the active corpus — is reported as its own separately-counted `duplicate_lessons` outcome. |
| `cmd_consult` / `cmd_list` / `cmd_get` / `cmd_set_body` / `cmd_set_title` | A | **JUSTIFY (read paths whose zero is not authority-bearing).** Each resolves through `get_lessons_dir()` (main-anchored) and reports a lesson set or a single lesson. None drives a destructive or existence-proof decision on an empty read: `cmd_consult` returns a surfaced set the outline author judges, `cmd_list` is a listing, and the three single-lesson verbs return an explicit `not_found` error rather than an empty success. An under-scoped read here can only under-surface, never authorize a deletion. |

### manage-lessons/scripts/manage-lessons.py

| Site | Direction | Disposition |
|------|-----------|-------------|
| The argparse registrations (`list-stalled`, `restore-from-plan` help strings) | A | **FIX (D1).** Not a resolver, but the verbs' **user-facing advertised contract**, which goes stale in lock-step with the handlers. The `list-stalled` help advertised a "lesson-**sourced**" population — naming the exact predicate the fix removes — and the `restore-from-plan` help advertised only the move-the-file-back outcome, with no mention of the unresolvable-store outcome. An advertised form that survives the fix is a stale contract that sends a reader to the wrong mental model, so both were rewritten in the same change. |
| The `get_lessons_dir()` call sites (`add`, `remove`, `supersede`, `convert-to-plan`, `cleanup-superseded`, `retire-quiet`, …) | A, B | **JUSTIFY (main-anchored write paths, fail-closed on absence).** All resolve through the main-anchored resolver, so Direction B is closed. None reads an absence as authority: the write verbs create the store when missing, and the mutate verbs (`remove`, `supersede`, `set-*`) return an explicit `not_found` error rather than treating an unreadable store as an empty one. |

### manage-lessons/scripts/_lessons_crud.py

| Site | Direction | Disposition |
|------|-----------|-------------|
| `set_body(lessons_dir, ...)` | — | **JUSTIFY (parameter-injected, resolves nothing).** Takes the already-resolved `lessons_dir` as its first parameter; its only mention of the resolver is a docstring naming where callers typically get it. Resolution is the caller's, so neither direction can originate here. |

### manage-status/scripts/_cmd_lifecycle.py

| Site | Direction | Disposition |
|------|-----------|-------------|
| `_restore_lesson_from_plan_dir` | A, B | **FIX (D1) — the site the roster-derived population missed, and the only one where the fail-open costs the corpus.** It carried BOTH directions and a third, sharper failure at once. (B) It resolved the destination with `base_path('lessons-learned')` — the cwd-keyed resolver, bypassing the main-anchored one entirely — so a worktree-pinned `delete-plan` restored into a store that is discarded with the worktree. (A) `if not plan_dir.exists(): return False, []` collapsed could-not-look into the same zero as a genuine absence. And a destination collision or traversal-shaped id was `continue`-skipped **silently**, immediately before the caller deleted the directory holding the only copy. Now resolves through `resolve_lesson_store()`, returns the `LessonCarryBack` record whose `action` shares every value it has in common with `RESTORE_ACTIONS` under the identical meaning (the two sets are not equal — `not_attempted` is producible only here, from the `--no-restore-lessons` opt-out), and reports every un-landed lesson in `skipped` with its reason. |
| `cmd_delete_plan` | A | **FIX (D1).** Surfaces the carry-back outcome on its payload (`lesson_carry_back_action`, `lesson_store_resolution`, `lessons_dir`, `restored_lesson_ids`, `skipped_lessons`) and **refuses to delete** the plan directory when any carried lesson did not land, returning `error: lesson_carry_back_incomplete`. The refusal is what makes a silently-skipped lesson impossible to lose: the directory holding the only copy survives the failure. |

### pm-plugin-development/skills/plugin-doctor/scripts/_analyze_plan_path_in_scripts.py

| Site | Direction | Disposition |
|------|-----------|-------------|
| The `'lessons-learned'` member of the Form-B subdirectory-name set | — | **JUSTIFY (detector token, resolves nothing).** The literal appears as one entry in the `.plan`-domain subdirectory list the `plan-path-in-scripts` rule matches against when detecting hand-rolled parent-walking path re-derivation. It resolves no store; it is the lint rule that flags Direction-B drift. Included as first-class evidence: this is a guard against the failure shape, not an instance of it. |

### marshall-orchestrator/workflow/lessons-handling.md

| Site | Direction | Disposition |
|------|-----------|-------------|
| The remote-lesson handling prose | A, B | **JUSTIFY (consulted, already fail-closed).** Reasons explicitly about the cwd-keyed hazard and deliberately routes remote-lesson removal around the store rather than resolving it from an arbitrary cwd. It states the constraint instead of tripping over it, so no change is owed. Recorded here because an already-sound site is evidence the survey reached it — not filler. |

### marshall-steward/references/menu-maintenance.md

| Site | Direction | Disposition |
|------|-----------|-------------|
| The cleanup-route pointer | — | **JUSTIFY (pure route pointer, carries no population predicate).** Names the store only to point at the cleanup route; it does not restate the population predicate and does not resolve anything, so it does not go stale with this change. (The predicate-bearing descriptor was in `marshall-steward/SKILL.md`'s Available-References row, which IS rewritten by D1.) |

### .claude/skills/finalize-step-lessons-housekeeping/SKILL.md

| Site | Direction | Disposition |
|------|-----------|-------------|
| Step 2 corpus read; Step 7 outcome report | A | **FIX (D1).** Added from the finalize-step roster, not from the sweeps — it lives outside the crawled inventory (see the coverage boundary above). Its Step 2 resolved the corpus implicitly, so *where the step ran* decided *what corpus it could see*, and Step 7 could emit `0 removed, 0 promoted, 0 adapted` without stating whether that reflected a genuinely clean corpus or an unavailable one. Step 2 now resolves through the explicit main-anchored store handle and both the report and the empty-corpus skip-clean exit name the substrate the counts were computed from. Splitting the step into a main-anchored classify pass and a pushable apply pass is deliberately **out of scope** and owned by `PLAN-CIS-034`. |

## Excluded from the population (prose-only, resolves nothing)

Sweep 3 matches the store's name wherever it is *mentioned*. The following
members mention it exclusively in a docstring, a narrative comment, or a
generated `.gitignore` comment string, and perform no resolution. They are named
here rather than dropped silently, so the subtraction from the union is
auditable:

- `manage-locks/scripts/merge_lock.py`, `manage-locks/scripts/build_queue.py` —
  docstring references to the main-anchored exception set.
- `manage-status/scripts/manage-status.py` — docstring reference to the
  `delete-plan` carry-back.
- `workflow-integration-git/scripts/git-workflow.py` — a narrative comment on
  which corpora stay main-anchored across the worktree move.
- `marshall-steward/scripts/gitignore_setup.py` — the store's name inside the
  emitted `.gitignore` header comment.
- `manage-locks/standards/cwd-keyed-store-resolution-audit.md` — the sibling
  audit. It *dispositions* the resolver rather than resolving anything; D1
  narrows its `get_lessons_dir()` row to the resolver and cross-links here.
- The ADRs, developer/user docs, skill bodies, templates, and test modules that
  name the store descriptively.

A member of this group that later gains a real resolution moves into the table
above; membership is decided by what the file DOES, never by whether the string
appears in it.

## Summary

- **Four of the twelve members carry a FIX disposition**, all of them consumers
  rather than resolvers: `manage-lessons/scripts/_lessons_query.py`
  (`cmd_restore_from_plan`, `cmd_list_stalled`),
  `manage-status/scripts/_cmd_lifecycle.py` (`_restore_lesson_from_plan_dir`,
  `cmd_delete_plan`), `manage-lessons/scripts/manage-lessons.py` (the two help
  strings that advertise the changed contracts), and
  `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md`. The remaining
  eight are JUSTIFY rows, with `_lessons_io.py` additionally EXTENDED by the new
  store handle.
- **The site the prior audit could not see** —
  `_cmd_lifecycle._restore_lesson_from_plan_dir` — is in this population only
  because the population predicate is the store-path sweep rather than a roster
  of `manage-lessons` verbs or finalize steps. A population that omits it is by
  construction roster-derived.
- **Direction B is closed at the last remaining caller**: a content sweep for
  `base_path('lessons-learned')` returns 0 hits over the full inventory.
- **Direction A is closed by a shared vocabulary**, not by four independent
  patches: `STORE_RESOLUTIONS` plus the per-verb discriminators
  (`RESTORE_ACTIONS`, `PLANS_ROOT_STATES`, `CARRY_BACK_ACTIONS`) mean every zero
  on the lesson path states which kind of zero it is.
- Every other enumerated member either IS the anchor and raises rather than
  returning an empty sentinel (`resolve_main_anchored_path`, `base_path`), is a
  declaration or a parameter-injected consumer that resolves nothing
  (`DIR_LESSONS`, `set_body`), is a read path whose empty result authorizes
  nothing (`cmd_list`, `cmd_consult`), is already fail-closed
  (`guard_component_store_match`, `lessons-handling.md`), or is the lint rule
  that detects the drift (`_analyze_plan_path_in_scripts.py`) — each justified
  above.
- **No deferred tail**: the surveyed universe is fully dispositioned here. The
  one bounded exclusion is recorded explicitly — the housekeeping step's
  classify/apply split, owned by `PLAN-CIS-034` — and it is a follow-up to a
  FIXED site, not an undispositioned member.

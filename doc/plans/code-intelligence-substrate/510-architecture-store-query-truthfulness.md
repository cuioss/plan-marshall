> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# The architecture store and its query surfaces report what they actually hold

**Epic:** code-intelligence-substrate
**Branch prefix:** `fix` — every deliverable corrects shipped behaviour or a shipped self-description
that is false; nothing here is a new capability.

## Problem

An audit of thirty-six landed plans in this epic found fifty-nine open defects in one contiguous
region: the architecture store, its concept model, and the query verbs an agent consults before it
decides anything — `info`, `find`, `search --content`, `which-module`, `module`, `capabilities`. The
defects share one shape. **A surface reports a verdict, a status, or a count that its own data does
not support, and every consumer is told to branch on it.** A guard that fails open is worse than no
guard, because callers stop checking; a count that names the wrong population is worse than no count,
because it is acted on.

Six of them are load-bearing, and each was reproduced by execution twice — once by the audit and once
by an independent adversarial re-review:

- **`architecture info` derives freshness from the wrong document.** `get_project_info`
  (`_cmd_client_query.py`, around the `derive_freshness(index_entry.get(GENERATION_FIELD), …)` call)
  reads the *root-index snapshot* rather than the concept document's own `generation` header. The
  index is written only by `api_discover`; the document is rewritten by every enrich verb — so the two
  separate on the first enrich after a discover. A document generated against a different tree is then
  reported `fresh`, and a module with **no concept document at all** is reported `fresh` *with a
  description*, because the row is built without consulting the (already loaded) empty document.
- **`capabilities` reports an impossible state.** `cmd_capabilities` emits `module_edges` as
  `status: not_derivable, producer_count: 0` beside `derived_count: 1` when every resolver is switched
  off but declared `internal_dependencies` edges still reach the `graph` response. The handler's own
  docstring enumerates that combination as impossible. An agent reading `not_derivable` skips
  `graph`/`path`/`neighbors`/`impact` on a project where those verbs return a real, non-empty edge set.
- **The `minimal` marker is copied onto a profile that is then populated.** `enrich_add_domain` does
  `merged = dict(existing)` and appends to `merged['defaults']`, carrying `minimal: true` across. Two
  supported CLI verbs in sequence — declare a profile minimal, then `enrich add-domain` / `enrich all`
  — persist a populated block still marked minimal, both returning `status: success` with no warning;
  `phase-4-plan` then reads "declared minimal" **before** any emptiness test and sets `task.skills =
  []`, discarding every resolved skill silently. The state did not exist before the plan that
  introduced `minimal`.
- **A shared suppression note counts deduplicated triples and calls them references.** The
  single-sourced Axis-C renderer in `extension_base.py` prints
  `f'{category}: {len(candidates)} reference(s) suppressed …'`, but `module-discovery.md` mandates that
  `component_refs` entries be deduplicated on the `(target_bundle, dep_type, resolved)` triple. On the
  live doc corpus the `unresolved-target` note read `1` where the audit re-derived eighteen references
  behind it, and the `self-edge` note read `1` where it re-derived five hundred and four. Every Axis-C
  resolver on the roster shares the renderer, so every one of them under-reports.
- **`main_*` invariant columns can still record the worktree.** `_assert_main_capture_read_main`
  compares `main_root.resolve() != worktree_path.resolve()` — plain equality — so a resolved path
  *inside* the worktree reads as a distinct tree and the refusal does not fire. Under a non-canonical
  `PLAN_BASE_DIR` from a worktree subdirectory the row persists with the worktree's value, which is
  the exact defect the owning plan existed to end.

Underneath the six sit twenty-five more of the same class in the same files (a migration that never
reaches disk, a description silently discarded on key collision, a `files_scanned` that counts scans
while its documentation calls it files, a `find` `count` that became a hybrid population, docstrings
asserting the crawl shells out to Maven when it is subprocess-free) and twenty-two smaller ones.

**Mechanism, in one sentence:** the store has a documented single writer
(`save_module_enriched`) and a documented single identity scheme (repo-relative package paths), and in
both cases a second path bypasses it — `api_discover` writes the raw dict, `merge_module_data` holds
the only migration and no writer calls it — so invariants stamped in one place silently do not apply
in the other, and the read surfaces built on top inherit the divergence and then report it as fact.

## Goal

Every verdict, status and count these surfaces emit is true of the data behind it, and where a number
cannot be made true it is renamed to the population it actually has. `info` derives freshness from the
concept document and says `unknown` when there is no document. `capabilities` cannot emit a state its
own contract calls impossible, and its three rows share one vocabulary. `find` and `search --content`
name their populations, and the claimed-path precedence that decides them is written where a caller
reads. A profile marked minimal is never also populated, and when the inventory resolves nothing the
condition reaches the command's structured output rather than only a log file. The remaining
architecture-core defects outside the store are closed at their sites, and every defect whose fix is a
genuine design decision is written up as a proposal for the operator instead of being decided by a run
that has no one to ask.

## Deliverables

Six deliverables, grouped by owning surface and shared mechanism rather than by severity. Each
sub-item names the file and the observable condition; each cites its gap entry as corroboration, not
as required reading — every fact needed to execute is restated here, because a landed cloud plan's
directory is deleted at collect and those files may be gone.

**⚠ Every count in this plan is a lead.** The tree has moved since the audit — the doc corpus alone
grew from 407 to 479 files *during* the audit, and `files_scanned` from 5409 to 5541. Re-derive any
number at the moment you claim it, and report the number you got, not the number written here.

---

### D1 — The concept-document store persists and reports what it actually holds

The store's freshness verdict, its provenance header, its root-index snapshot and its package-key
identity are four faces of one mechanism: a documented single writer that two paths bypass. Fix them
together, in `manage-architecture`'s scripts.

*Covers* `150-architecture-store-concept-model/gaps.md#G1`–`#G10`, `#G14`, `#G17`.

1. **Freshness from the document, not the snapshot** (`#G1`, high). In `get_project_info`
   (`_cmd_client_query.py`), compute the module row's `freshness` from the concept document's own
   `generation` header — the function already loads that document a few lines above, to read
   `purpose`, so this costs nothing on that path.
2. **`unknown` when there is no document** (`#G2`, high). In the same function, when the loaded
   enriched document is empty, force `freshness` to `FRESHNESS_UNKNOWN` and blank the `description` —
   both currently describe a document that is not on disk.
   ⛔ **A shipped test pins this defect as correct behaviour.**
   `test/plan-marshall/manage-architecture/test_concept_model.py::test_info_surfaces_freshness_from_index`
   seeds an index entry and **no** `enriched.json`, then asserts `fresh`. It must be rewritten to seed
   a document (so it still tests what its name says) — not deleted, and not "fixed" by weakening the
   new behaviour. Re-derive its line range; it will have moved.
3. **One writer** (`#G8`). `api_discover` (`_cmd_manage.py`) writes the concept document through a raw
   `_write_json` into its tmp-staging directory, bypassing `save_module_enriched`, which documents
   itself as "the single concept-document writer" and stamps both concept-model constructs. Extract
   the invariant-stamping into a helper that returns the document to write and let each caller place
   it — `save_module_enriched` resolves its own path from `project_dir`, so a naive redirect would
   break `discover --force`'s atomic tmp+swap.
4. **Back-fill `generation` honestly** (`#G7`). A preserved pre-field document survives `discover` with
   no `generation` and stays permanently `unknown` with nothing that will ever add one. Stamp
   `{'by': 'architecture', 'tree_sha': None}` — which `derive_freshness` already maps to `unknown` —
   through the helper from (3). ⛔ It must **not** stamp the current tree sha onto preserved content:
   that would convert an inert signal into a wrong one across the whole installed base.
5. **Keep the index snapshot true** (`#G6`). No enrich verb touches `_project.json`, so its
   `description` and `generation` are whatever the last `discover` left. Have `save_module_enriched`
   (or a small helper the enrich verbs call after it) write through the module's current
   `responsibility` and `generation`, tolerant of a missing `_project.json`. `enrich all` writes many
   modules per invocation — batch the index update rather than rewriting the file per module.
6. **Write the dotted→path `key_packages` migration back to disk** (`#G3`). `migrate_key_packages` is
   called from exactly one place, `merge_module_data`, which no writer calls — so the merged read shows
   paths while the persisted document keeps dotted keys indefinitely. Migrate in `api_discover`, where
   both the document and the crawled derived data are already in hand and where `type` is already
   back-filled on the same path; that avoids making every enrich verb depend on derived data being
   loadable. A module whose derived `packages` bridge is unavailable keeps its dotted key — the write
   must not fail.
7. **Route the one outside reader through the migration** (`#G4`).
   `manage-solution-outline.py`'s `_read_module_context` reads `enriched['key_packages'].keys()` via
   `load_module_enriched_or_empty`, which migrates `type` but not `key_packages`. It is the only
   production reader outside `manage-architecture`, and it feeds `phase-3-outline`'s module and package
   selection — so a legacy store gives that phase dotted names while `architecture module` gives paths
   for the same module. Apply `migrate_key_packages` with the derived `packages` map the function
   already holds. ⛔ Preserve the existing tolerance of a missing `derived.json`: `merge_module_data`
   raises `DataNotFoundError` there and the current code does not.
8. **Stop losing a description on key collision** (`#G5`). `migrate_key_packages` does
   `migrated[path] = value` unconditionally, so two dotted keys bridging to one path silently discard
   the first entry's curated description, and the discarded key never reaches the `unresolved` list, so
   the WARNING never fires. The function's own docstring promises "a named outcome, never a silent
   drop". Detect an already-present target key and report the collision through the existing
   `unresolved`/WARNING channel — that avoids changing the two-tuple return signature callers
   destructure; say in the WARNING text that it is a collision, not an unresolved key.
9. **Refuse a migrated key that does not resolve, and refuse the root** (`#G9`, `#G10`). The bridge
   `path` is adopted with no `package_key_resolves` check, so a deleted package directory yields a
   silently broken key reported as migrated — check before adopting and fall through to the existing
   `unresolved` branch. Separately, `package_key_resolves` allows `candidate == root`, so `.` and `./`
   are valid package keys and `enrich package --package .` attaches a description to the whole
   repository; reject the root explicitly. Check first whether any fixture or store relies on a
   root-level key.
10. **Two contract statements, decided here so the run does not have to** (`#G14`, `#G17`).
    (a) D4 of the source plan promised provenance records "at what point" a document was generated and
    `build_generation` records only `by` and `tree_sha`; a test asserts the exact key set, so adding a
    field turns it red, and a wall-clock field is the mtime-shaped evidence this project has ruled
    inadmissible. **Take the documentation arm:** state in `architecture-persistence.md` § the concept
    model that provenance deliberately records *who* and *against which tree* but not *when*, and why
    (a tree identifier, not an expiry, is what the freshness verdict must derive from). (b) The
    `CONCEPT_TYPES` vocabulary is enforced but no verb can write a non-`module` type, because the
    store's directory layout is keyed by module name and the key-space decision was deliberately
    deferred. **Take the documentation arm:** record in `architecture-persistence.md` that non-`module`
    types are currently reachable only through the Python API and name what a writer would first have
    to settle (where a `standard` concept document lives). Do **not** add a `--type` flag in this plan.

*Done when:*

- A test seeds an index entry whose `tree_sha` equals the current tree and a concept document whose
  `tree_sha` differs, calls `get_project_info`, and asserts the module row's `freshness` is `stale`.
- A test seeds an index entry carrying a current-tree `generation` and writes **no** `enriched.json`,
  and asserts the module row's `freshness` is `unknown`.
- Either `_write_json` no longer appears in `_cmd_manage.py` for `enriched.json`, or a test asserts
  that a document written by `api_discover` and one written by `save_module_enriched` carry an
  identical set of concept-model fields.
- A test seeds a document with no `generation`, runs `api_discover`, and asserts the on-disk document
  carries a `generation` whose freshness verdict is `unknown`.
- A test runs an enrich verb that changes `responsibility`, then reads `_project.json` and asserts the
  module's index entry carries the new description and the document's current `generation`, with no
  intervening `discover`.
- A test writes a document with a legacy dotted `key_packages` key, invokes `api_discover`, re-reads
  the file **from disk**, and asserts the key is the repo-relative path with no dotted key left.
- A test seeds a module whose `enriched.json` holds a dotted key and whose `derived.json` bridges it,
  invokes the outline architecture-context reader, and asserts the returned `key_packages` contains
  the path and not the dotted name — and a sibling test with `derived.json` absent still succeeds.
- A test passes two dotted keys whose derived entries share one `path` and asserts no curated
  description is lost — the collision is reported in the returned diagnostics.
- A test supplies a bridge whose `path` does not exist and asserts the dotted key comes back in
  `unresolved`; `package_key_resolves('.', root)` and `('./', root)` are both `False` while a real
  sub-path stays `True`.
- `architecture-persistence.md` states the "at what point" deviation and its reason, and states that
  non-`module` concept types are Python-API-only with the key-space question named.

---

### D2 — `capabilities` cannot emit a state its own contract calls impossible

One verb, one vocabulary, one memo. All sites in `manage-architecture`.

*Covers* `220-resolver-configuration/gaps.md#G1`, `#G2`, `#G10`;
`130-lsp-shaped-query-api/gaps.md#G1`, `#G2`, `#G3`, `#G9`;
`135-remove-lsp-query-facade/gaps.md#G2`, `#G15`.

1. **`not_derivable` must never co-occur with `derived_count > 0`** (`220/#G1`, high). Compute the
   `module_edges` `status` from the full producer population that actually reaches the response —
   dispatched resolvers **plus** the reserved `declared` and `sibling-cross-link` producers present in
   the graph result — while leaving `producer_count` resolver-scoped, which four docstrings and
   `test_capabilities.py` depend on.
   ⛔ **A shipped test asserts the defect.**
   `test/plan-marshall/manage-architecture/test_derivation_resolver_configuration.py::test_capabilities_reports_not_derivable_when_every_resolver_is_disabled`
   asserts `status == 'not_derivable'` for the all-disabled case, and its docstring states the
   generalisation this fix refutes. Its fixture seeds modules with **no** declared
   `internal_dependencies`, so the assertion stays true once the test is re-scoped to that
   precondition — **re-scope it and correct its docstring; do not delete it** — and add a sibling test
   for the declared-edge case.
   ⛔ Do not widen `resolver_count`. The feasibility/anti-vacuity guard in
   `test_feasibility_underivable_guard.py` derives "underivable" from `resolver_count > 0`; changing
   that population would flip a guard this plan is not touching.
2. **One status vocabulary across all three rows** (`135/#G2`). `content_search` emits
   `available`/`unavailable` while `module_edges` and `path_attribution` emit
   `derivable`/`not_derivable`, and the handler's own docstring already describes all three rows in the
   `derivable` vocabulary — so the code contradicts itself, not only the documents. Adopt
   `derivable`/`not_derivable` everywhere (a crawl that produced an inventory *is* a producer that
   ran). Grep the tree for consumers matching the literal `available` before landing.
3. **`content_search` must distinguish never-crawled from crawled-and-empty** (`130/#G1`). The entry
   carries only `status` and `modules_inventoried`, and the module loop swallows a missing descriptor
   (`except DataNotFoundError: continue`), so an empty envelope and an envelope of two crawled but
   file-less modules return byte-identical payloads. Add evidence in the shape the other two rows use —
   `modules_total` (or `modules_without_descriptor`) beside `modules_inventoried` — and emit
   `not_derivable` when no module descriptor could be read at all.
4. **Give `path_attribution` the `derived_count` its contract documents** (`130/#G9`). Three documents
   and the handler docstring state a three-state entry shape keyed on `derived_count`, and the
   `path_attribution` row never emits one, so an attributor that claimed nothing and one that claimed
   fifty are the same payload. The data is already computed: each attributor report carries
   `claim_count` (`extension-api/scripts/_path_attribution_merge.py`). Sum it, and document the field
   as *claims reported* rather than *paths attributed*, because two attributors claiming one path
   double-count.
5. **Make the "nothing is memoised" claim true** (`130/#G2`). `_PATH_CLAIM_CACHE` in
   `_architecture_core.py` memoises path-attribution discovery for the process lifetime, while
   `_cmd_client_handlers.py`, `client-api.md` and `doc/concepts/code-intelligence.adoc` all say
   "Nothing is memoised across calls" / "memoised across none". Two `cmd_capabilities` calls in one
   process with the attributor population changed between them both report the stale row. **Invalidate
   the attribution memo at the top of `cmd_capabilities` only** — the strong claim then becomes true.
   ⛔ Do not drop the memo for `resolve_module_for_path`'s per-path loop; the memo exists for that loop
   and removing it re-runs full extension discovery per path.
6. **Key the memo by project directory** (`130/#G3`). `cache_key = tuple(sorted(module_names))` omits
   `project_dir`, so two envelopes with identical module-name sets share one entry within a process.
   It is latent only because attributor discovery is currently process-global; key on
   `(project_dir, module_names)` and keep the existing `invalidate_crawl_cache` drop behaviour.
7. **Bring the documents to the code, in lock-step** (`220/#G2`, `220/#G10`, `135/#G15`, and the doc
   half of `130/#G1`). The render footer for the all-switched-off case prints "No edges were derived"
   two lines below an adjacency table containing a declared edge — qualify it ("no edges were derived
   *by a resolver*; any dependency shown above is declared"), symmetrically with the zero-registered
   branch, and move the two footer assertions that pin the current substrings. `_derivation_merge.py`'s
   docstring says the caller distinguishes the two anti-vacuity states "by the length of the returned
   report list"; the caller uses `count_dispatched`. ⛔ **Do not sweep that wording repo-wide** — the
   same sentence in `_path_attribution_merge.py` is *correct*, because Axis-D has no dispatch control
   and length genuinely is the discriminator there; ADR-014 exempts Axis-D explicitly. Finally,
   `_cmd_client_handlers.py`'s module docstring lists nineteen handlers while the file defines twenty
   (`cmd_capabilities` is missing), and `client-api.md`'s command-summary row already claims
   `capabilities` reports `derivable`/`not_derivable` for content search — which becomes true once (2)
   lands. Update the entry-shape table and every worked TOON payload in the same change.

*Done when:*

- A test seeds a project with a declared `internal_dependencies` edge, disables every discovered
  resolver through the `derivation_resolvers` binding, and asserts `cmd_capabilities`' `module_edges`
  record does not claim `not_derivable` while `derived_count > 0`; the handler docstring's state
  enumeration matches the states the code can emit.
- A test asserts all three `capabilities` entries emit the same two status values, and no document or
  docstring mentions a per-entry exception.
- A test seeds (a) an envelope with no descriptors and (b) an envelope with N crawled file-less
  modules, and asserts the two `content_search` entries differ.
- A test reads the payload keys of all three entries and asserts they are exactly the fields
  `client-api.md`'s entry-shape table names.
- A test calls `cmd_capabilities` twice in one process with the attributor population changed between
  the calls and asserts the second call reflects the change; a positive control clears the memo
  explicitly and gets the same answer.
- A test computes path attribution for two project dirs with identical module names and different
  expected outcomes in one process and gets two different answers.
- A test renders an overview for a project with a declared edge and every resolver disabled and asserts
  the footer does not state an unqualified "No edges were derived".
- No docstring in `_derivation_merge.py` says the report list's length is the anti-vacuity
  discriminator, and `_path_attribution_merge.py`'s equivalent sentence is **unchanged** (assert this
  by diff review, and say so in the report).
- `_cmd_client_handlers.py`'s module docstring names every `def cmd_*` the file defines — re-derive
  both numbers rather than trusting nineteen/twenty.

---

### D3 — Every count names its own population, and every self-description is true

The recurring shape across `find`, `search --content` and the shared Axis-C note: a number is computed
over one population and printed with the name of another.

*Covers* `120-documentation-surface-provider/gaps.md#G3`, `#G7`, `#G8`, `#G9`, `#G14`;
`130-lsp-shaped-query-api/gaps.md#G5`, `#G6`;
`300-freshness-gate-cannot-distinguish-test-authored-evidence/gaps.md#G3`, `#G5`.

1. **Carry reference multiplicity through the Axis-C schema** (`120/#G3`, high). The renderer in
   `script-shared/scripts/extension/extension_base.py` prints `len(candidates)` as
   "N reference(s) suppressed", and `extension-api/standards/module-discovery.md` mandates that
   `component_refs` be deduplicated on the `(target_bundle, dep_type, resolved)` triple — so the number
   is a triple count wearing a reference label, on every Axis-C resolver at once.
   ⛔ **Do not make the resolvers emit one entry per reference.** That violates the schema clause and
   turns `test/pm-documents/plan-marshall-plugin/test_doc_references.py::test_component_refs_deduped_on_triple`
   red. **Take the schema arm:** add an optional additive `occurrences` (int, default 1) to the
   `component_refs` element in `module-discovery.md`, populate it in each materializer, and have
   `_aggregate_notes` sum `occurrences` instead of counting candidates. The field must be optional with
   a documented default so a materializer that omits it still renders correctly, and the sample
   truncation (`NOTE_SAMPLE_LIMIT`) must still bound the sample. Re-derive which resolvers implement the
   element — the audit found four (`pm-documents`, `pm-plugin-development`, `pm-dev-python`,
   `pm-code-intelligence`) and that set is a lead. Update the illustrative numbers in
   `ext-point-derivation-resolver.md`, which this changes.
2. **`find` must name its hybrid population** (`120/#G7`). After the claimed-duplicate collapse, a
   claimed path contributes one row per file while an unclaimed path still contributes one row per
   attributing module, so `cmd_find`'s `count` is a mixture — measured live as `count: 1` for one file
   and `count: 2` for another. `cmd_search` already ships both `count` and `file_count`. Add
   `file_count: len({row['path'] for row in results})` to `cmd_find`'s payload.
3. **`files_scanned` must be a file count or be renamed** (`130/#G5`, `120/#G9`). It increments once per
   `(module, category, path)` row while `client-api.md` and `doc/user/code-search.adoc` describe it as
   "files actually opened and scanned"; it is the field the documented complete-coverage conjunction
   rests on and the number quoted to a caller behind a `count: 0`. Two changes, both measurable:
   (a) resolve ownership **before** the scan loop so a claimed path is read and regex-scanned once
   rather than once per attributing module; (b) count distinct paths, so the remaining unclaimed
   duplication cannot inflate it either.
   ⚠ **If (a) changes which module any test reports a hit under, keep the existing scan order, land (b)
   alone, and record (a) in the run report as a proposal with the failing test named.** Both call the
   same `resolve_path_attribution`, so a disagreement would be a finding, not a judgement call — this
   is a measurement the run makes, not a decision it takes.
   ⚠ The over-statement is **not** the doc-corpus doubling alone. The audit re-derived 5541 pre-collapse
   rows against 2907 distinct paths — 479 from the claimed-doc doubling and 2155 from pre-existing
   unclaimed marketplace duplication. Re-derive all four figures; they drifted during the audit itself.
4. **One `unreadable[]` entry per physical file** (`130/#G6`). A missing file listed in two modules'
   inventories yields the same `{path, reason}` twice, and `client-api.md` describes each entry as
   "a file that MIGHT contain a match nobody saw", so a caller counting entries over-reports the gap.
   De-duplicate on `(path, reason)`, or attribute explicitly as `{path, reason, modules[]}`.
   ⛔ ADR-014 requires the skip be reported, never suppressed — collapse repeats, never drop the path.
5. **Write the claimed-path precedence where a caller reads it** (`120/#G8`, `120/#G14`). The rule lives
   in `doc/concepts/code-intelligence.adoc`, in `pm-documents`' SKILL.md and in a docstring — but
   `client-api.md`, the document `CLAUDE.md` itself points readers at, uses the phrase "unclaimed
   cross-module duplicate" twice without ever defining the *claimed* case, and its § find is silent on
   duplication entirely. Add a paragraph to § find and a sentence to § search stating that an Axis-D
   ownership claim outranks the root crawl: a claimed path's duplicate rows collapse onto the owning
   module's single row, an unclaimed duplicate is untouched, and a single-rowed claimed path is never
   dropped. Extend the same paragraph with the consequence a caller currently cannot see: `module`
   names the **inventorying** module, the collapse picks the owner's row **only when the owner
   inventoried the path**, and `which-module` is the authoritative ownership answer — with `README.md`
   as the worked example (`which-module README.md` → `documentation`; `find --pattern README.md` → one
   row carrying `module: default`). ⛔ Do **not** rewrite the surviving row's module: `find` reports
   inventory rows, and rewriting one the owning module never inventoried would make `find --module
   documentation` and `find --pattern README.md` mutually inconsistent. Cross-reference
   `ext-point-path-attribution.md` rather than restating the mechanism.
6. **Correct the false crawl-cost claims at their source** (`300/#G5`, `300/#G3`). `crawl_all_modules`'
   docstring and the `_CRAWL_CACHE` comment in `_architecture_core.py` say the crawl "shells out to the
   build tools — e.g. Maven runs `help:all-profiles dependency:tree` per module" and speak of "O(N²)
   subprocess invocations". Two first-party surfaces say the opposite and instrumentation settled it in
   their favour: the crawl parses each `pom.xml` with stdlib XML and makes one child process, a `git`
   call. This docstring is the *authority* the other false copies quoted, so fixing the copies without
   it guarantees the next author re-derives the same error. Fix it, and fix
   `resolve_project_build_notations`' § Cost in `_cmd_client_query.py`, which is a *new* public API
   docstring written by copying it — state the real mechanism (build-file parsing, filesystem walk, one
   `git` invocation) and say explicitly that the function does not reach the lazy Maven enrich path.

*Done when:*

- A unit test supplies a category whose several references collapse to one triple and asserts the
  rendered note's number matches the population the schema documents; the live doc-corpus
  `unresolved-target` and `self-edge` notes report reference counts, re-derived and reported.
- `architecture find` returns `file_count` on every success response, and `client-api.md` § find states
  what `count` and `file_count` each mean.
- A test using a doubly-attributed fixture asserts `files_scanned` equals the distinct-file count; a
  whole-corpus `search --content` reports `files_scanned` equal to the distinct paths scanned
  (re-derive both figures and report them).
- The duplicate-attribution fixture with an unreadable file produces exactly one `unreadable` entry for
  that path, or one entry naming both modules.
- `client-api.md` § find and § search state the precedence, name `which-module` as the ownership
  authority with `README.md` as the example, and the word "unclaimed" no longer appears without the
  claimed case defined nearby. `test_doc_corpus_dedup.py::test_single_row_claimed_path_unchanged`
  carries a docstring naming the consequence.
- `_architecture_core.py` and `_cmd_client_query.py` agree about whether the crawl runs a build tool,
  and neither Cost section names a subprocess its function does not cause.

---

### D4 — The `skills_by_profile` three-state signal survives the write path and reaches the consumer

*Covers* `160-empty-skill-resolution-indistinguishable-from-minimal/gaps.md#G1`, `#G2`, `#G3`, `#G9`,
`#G13`, `#G14`.

1. **Clear `minimal` when enrichment populates a profile** (`#G2`, high). In `enrich_add_domain`
   (`_cmd_enrich.py`), `merged = dict(existing)` carries `minimal: true` across while entries are
   appended, and `_validate_skills_by_profile_structure` runs only in `enrich_skills_by_profile`, so
   nothing catches it. Drop the `minimal` key whenever at least one entry is appended to a profile, and
   have the validator flag `minimal: true` on a profile carrying any `defaults`/`optionals` as
   malformed. The reproduction is three supported steps and warns at none of them — treat any claim
   that this is "nonsensical input" as refuted by execution.
2. **Stop discarding the unresolved-profile condition on the registry fail-open** (`#G1`). When
   `resolve_bundles_root` raises, `_emit_skills_by_profile_staleness_warning` returns early and emits
   nothing, while its own module comment promises the missing/empty and unresolved-profile checks still
   fire "because they need no registry". ⚠ **Only the unresolved-profile signal is actually lost** — a
   falsy `skills_by_profile` takes a different branch and still emits. Restructure so
   `detect_stale_skills_by_profile` is always called, resolving the registry predicate defensively
   (fall back to `lambda _: True`, which disables only the stale-notation signal).
3. **Let the guard fire for an ABSENT profile** (`#G3`). Both writers skip a profile that resolves
   nothing (`if merged_defaults or merged_optionals:` and `if not new_entries: continue`), so enrichment
   never persists an empty block — and the guard walks only present keys, so the real-world "the
   inventory answered nothing" case produces no message at all.
   ⛔ **This sub-item is a stop-condition.** The expected-profile set must come from configuration —
   the active profiles in `marshal.json`, or the `architecture profiles` key set — never from a
   hard-coded list, because a hard-coded list is the defect class this epic exists to close. **If the
   expected-profile set cannot be derived from configuration in a fresh clone, do not build a fallback:
   stop this sub-item, land the rest of D4, and record in the run report exactly what could not be
   derived and where you looked.** Word the emitted condition so an absent profile is distinguishable
   from a present-but-empty one.
4. **Surface the condition in the command's output, not only a log file** (`#G9`). The condition is
   written through `log_entry(...)`, which appends to a log file under the plans store; the dict
   `get_module_info` returns carries no warnings field, so the TOON payload a consumer reads is
   unchanged — and the allocation-time consumer (`phase-4-plan`) reads the output, never the log. Attach
   the guard's messages to the returned payload as a `warnings[]` field, consistent with the enrich
   commands, keeping the log write. Presence-gate the field so a quiet read stays byte-identical.
5. **Do not skip a non-dict profile block silently** (`#G13`). `detect_stale_skills_by_profile` does
   `if not isinstance(profile_data, dict): continue`, deferring to a validator that never runs on the
   `enrich add-domain` / `enrich all` write paths — while the legacy list shape is still supported
   downstream, so `"module_testing": []` is a representable empty profile that produces nothing. Treat
   an empty list-shaped block as an empty profile (a list cannot carry `minimal`, so it is always
   unresolved) and emit a malformed-shape message for other non-dict values. Check the population of
   list-shaped profiles before landing.
6. **Reflect the distinction on the render surface** (`#G14`). `_count_profile_skills` in
   `_cmd_client_render.py` sums `defaults` + `optionals` and never reads `minimal`, and **both** its
   call sites — the overview section and the module deep-dive — print `- {profile}: 0 skills` for a
   declared-minimal profile and an undeclared-empty one alike, reproducing on the human-facing surface
   exactly the indistinguishability the machine-facing one lost.

*Done when:*

- Enriching a `{"defaults": [], "optionals": [], "minimal": true}` profile with a domain that supplies
  skills yields a block carrying the skills and **no** `minimal` key; a test asserts both the persisted
  shape and the validator warning for the hand-written contradictory pair.
- With `resolve_bundles_root` raising **and** a non-empty `skills_by_profile` carrying an
  undeclared-empty profile, the emitter logs the unresolved-profile condition and logs no
  stale-notation condition; a test asserts both halves. (Asserting the missing/empty case alone does
  not discriminate — it already passes today.)
- A module whose `skills_by_profile` contains only `implementation`, in a project whose active profiles
  include `module_testing`, surfaces the named condition for `module_testing`, while a declared-minimal
  or populated `module_testing` surfaces nothing — **or** the run reports the stop-condition above.
- `architecture module` output for a module with an undeclared-empty profile contains the named
  condition as a field and a declared-minimal profile's output does not, asserted by a test.
- `{"module_testing": []}` surfaces the named condition, asserted by a test.
- Both rendered surfaces distinguish the two zero-count states, with a test asserting each.

---

### D5 — Bounded sweep: the remaining architecture-core defects outside the store

Fourteen independent, mechanically-verifiable fixes. They share no mechanism with each other — they are
grouped because each is small, each has an observable condition, and splitting them into their own
plans would cost more review than it saves. Land them as separate commits so a reviewer can take them
one at a time.

*Covers* `020-corpus-residency-admission-control/gaps.md#G11`;
`040-generator-fails-open-and-its-fixtures-cannot-see-it/gaps.md#G10`, `#G15`;
`110-blocking-boundary-arms-on-a-call-not-a-state/gaps.md#G12`;
`190-frozen-manifest-diverges-from-live-config/gaps.md#G1`, `#G3`, `#G8`;
`290-auditor-detector-integrity/gaps.md#G7`;
`310-main-sha-records-the-pinned-cwd/gaps.md#G1`, `#G9`;
`350-outline-derived-set-closure-integrity/gaps.md#G7`, `#G10`, `#G14`, `#G16`.

1. **Close the base-dir-override hole in the main-scoped refusal** (`310/#G1`). In
   `_assert_main_capture_read_main` (`plan-marshall/scripts/_invariants.py`), replace the equality
   comparison with containment: refuse when the resolved `main_root` is at or under the resolved
   `worktree_path`. A genuine main checkout is an *ancestor* of the worktree, never a descendant, so the
   direction is safe. **Measured by the adversarial review:** with that single change applied, every
   previously-silent row in an eight-row sweep becomes a refusal, the module's tests stay green and the
   owning directory stayed green — re-derive both counts.
   ⛔ **Do NOT also make `_main_repo_root`'s override branch return `None` for a non-canonical base
   dir.** That was measured and **breaks the suite**: the autouse `_plan_base_dir_sandbox` fixture in
   `test/conftest.py` gives *every* test a flat `PLAN_BASE_DIR`, so all three `main_*` columns empty out
   and at least seven tests go red. It is a separate change with a sandbox migration attached and is
   **out of scope here** (see § Out of scope).
   ⚠ The bucket manifest carries this gap as `high`; its own entry and the adversarial review both rate
   it **medium**, with the reasoning written out (the defect is unreachable on the shipped default path,
   nothing under `marketplace/` writes `PLAN_BASE_DIR`, and the limitation is disclosed in three shipped
   surfaces). The adversarial review is the later evidence-bearing pass and wins. It is fixed here
   regardless, because the fix is one line and was measured safe.
2. **Give `TaskGraphInvalid` a handler at both handshake verbs** (`310/#G9`). The exception carries
   `cycle` and `dangling` and is declared in `capture_all`'s `Raises:`, but neither `cmd_capture` nor
   `cmd_verify` (`plan-marshall/scripts/_handshake_commands.py`) catches it, so a broken task graph
   escapes and renders as `error: internal_error`. Add the handler at both, returning a structured
   payload through a shared builder in the same shape the sibling refusals use.
   ⚠ Adding the code to `VERIFY_REFUSAL_ERRORS` — which lives in a **different skill**,
   `manage-status/scripts/_cmd_lifecycle.py`, not beside the handshake scripts — changes loop-back
   re-entry from "auto-override attempted" to "refused". Check that posture against the existing members
   first, and note that that set and `phase_handshake.py`'s strict-exit tuple already disagree in size:
   adding to one is not adding to the other.
3. **Distinguish "previous had no surfaces" from "previous unreadable"** (`040/#G15`).
   `read_previous_surfaces` in `tools-script-executor/scripts/generate_executor.py` returns `{}` on
   every failure mode — absent file, `OSError`, missing or unterminated `SCRIPT_SURFACES` block, parse
   error, non-dict — so Guard 5 (`if previous_surfaces and emitted_surface_count == 0:`) cannot fire on
   an unreadable previous executor and a surfaces-less executor gets written. Report the failure mode
   separately from the empty result and treat "exists but unreadable" as a refusal.
   ⚠ Keep an explicit escape for a legitimate change to the emitted surfaces-block format, or the first
   regeneration after such a change refuses.
4. **Reconcile the "UNCONDITIONALLY" stats-line contract** (`040/#G10`). The docstring says the
   surface-stats line "is emitted UNCONDITIONALLY on every real regeneration"; three `generate` paths
   return before the print (template not found, template-format skew, dry run) — measured for the dry
   run by grepping its output. **Take the docstring arm:** narrow it to every regeneration that reached
   the derivation, and say plainly that an earlier refusal emits no line and is identified by
   `status: error`.
5. **Separate the entry-guard set from the completion-guard predicate** (`110/#G12`). In
   `manage-status/scripts/_cmd_lifecycle.py`, one single-member frozenset keys two different questions —
   the phase being *completed* and the phase being *entered* — and the helper it dispatches to hardcodes
   `'6-finalize'` regardless. Introduce a distinct constant for the completion use, leaving
   `_BLOCKING_BOUNDARIES` to mean entry only, and update the reference doc that cites the old name.
6. **Make `reconcile` able to classify an external step as stale** (`190/#G1`). `cmd_reconcile`'s only
   oracle is `_check_step_loadable`, which short-circuits every `project:` / `bundle:skill` entry to
   `loadable: True`, so the stale branch is unreachable for them — and this repository schedules
   `project:` steps in phase 6. Feed `_check_step_resolvable(step_id, phase)`, which already exists and
   is used only by `compose`, into the same partition for external steps, keeping the partition rule
   unchanged (unresolvable **and** absent from the live candidate set → stale; unresolvable but still
   listed → broken). Built-in steps keep `_check_step_loadable`.
7. **Subject a backfilled step to the composer's narrowing, or state it is exempt** (`190/#G3`). The
   `backfill` comprehension applies three conditions where `compose` applies eight filters, so a step
   added to `marshal.json` after compose is written straight into `phase_6.steps` regardless of its lane
   tier — a `tier: full` step can be dispatched in a `minimal` posture. Apply the composer's narrowing
   to backfill candidates, and if any filter genuinely cannot apply at reconcile time, say which and why
   in `manage-execution-manifest/SKILL.md` beside the existing "never re-runs the decision matrix"
   promise.
8. **Stop `reconcile --apply` silently deleting a non-string step entry** (`190/#G8`). A non-string
   entry is filtered out of `frozen_steps`, never reaches `stale[]`, `broken[]` or the decision log, and
   vanishes on any `--apply` — while the sibling ordering function documents non-string entries as fixed
   pins it deliberately preserves. **Reject the manifest with `error: invalid_manifest` naming the
   offending index**, matching the verb's fail-loud posture. Check first that no fixture relies on the
   current silence.
9. **Reconcile the `[LOCK]` timeline's log root** (`290/#G7`). `_resolve_lock_log_path` in
   `manage-locks/scripts/_locks_core.py` writes to `main_local_base.parent / 'logs'` (i.e. `.plan/logs/`)
   while every other global log lives in `.plan/local/logs/`, so the lock timeline is never rotated and
   accumulates indefinitely. Point it at `get_base_dir() / 'logs'` so the timeline joins the other global
   logs. ⛔ Leave the retrospective auditor's two-root scan in place — lock logs already on developers'
   machines must keep being found until they age out. Do not edit `audit.py` in this plan.
10. **Guard the unchecked `number` conversions in the mechanical Q-Gate** (`350/#G7`). Thirteen sites in
    `manage-tasks/scripts/_cmd_qgate_mechanical.py` read a `number` field straight off a JSON record —
    five feed a `:03d` format, eight call `int(...)` — and all of them sit on the path that **emits** a
    finding, so the gate crashes when it has something to report and passes when it does not. The
    sibling module already ships the fix (`_as_int` in `_qgate_closure.py`) and documents exactly this
    reasoning. Apply it at every site; where a deliverable number is unusable, drop the record from the
    map and let the population report the loss rather than raising. Re-derive the site count.
11. **Widen `manage-lessons` component derivation to the survey pair** (`350/#G10`). `_derive_components`
    in `manage-lessons/scripts/_lessons_query.py` reads `affected_files` only, so a survey-scope
    deliverable contributes zero components and zero `unmapped_paths[]` — and `manage-lessons consult`
    then surfaces no lesson for the skills the plan will actually edit, indistinguishably from "no lesson
    applies". Replace the direct field read with `deliverable_write_set(deliverable)`, and state in the
    change whether read scopes are included and why.
12. **Enforce survey-pair disjointness in the outline validator** (`350/#G14`).
    `validate_deliverable_contract` reads `survey_scope` and `mutation_scope` only to decide whether
    *either* is present and never compares them, while `outline-workflow-detail.md` states the two lists
    are disjoint by construction and the only trace in code is a defensive-dedupe comment. Add a check
    emitting an error naming the doubly-declared path. Check the archived corpus for existing violations
    before landing — failing them is the point, but the population should be known.
13. **Normalize before deduplicating in `deliverable_write_set`** (`350/#G16`). `_plan_parsing.py`
    de-duplicates on the raw spelling, so `./src/a.py` and `src/a.py` declared under the two fields
    produce a two-member write-set while the docstring promises one — every consumer other than the
    closure (which re-normalises) sees a phantom member. Deduplicate on the normalized spelling, lifting
    `normalize_declared_path` into `_plan_parsing` (its more natural owner) and having `_qgate_closure`
    import it from there.
14. **Record the existing section-granular read verbs in plan `020`** (`020/#G11`). That plan's D2 asks
    for a section-addressed read and its § Expected surface names no precedent, while two verbs already
    implement the shape over plan documents — `manage-solution-outline read --plan-id X --section S` and
    `manage-plan-documents read --section S`, both already distinguishing missing / unreadable / empty.
    Neither is corpus-facing, so D2's literal target is genuinely unbuilt, but the plan's own
    asserted-absence rule was not applied. Add both to `doc/plans/code-intelligence-substrate/020-…/plan.md`
    § Expected surface as OBSERVED precedents with their file paths and their state-discrimination
    behaviour, and amend D2 to require an explicit extend-or-justify decision recorded against them by
    name. ⚠ If that plan's directory is no longer present in the clone, this sub-item is discharged by
    recording the two precedents in the run report instead, with the same detail — say which arm you took.

*Done when (one condition per sub-item, each falsifiable):*

- A test builds a real linked worktree, sets a non-canonical `PLAN_BASE_DIR`, chdirs to a worktree
  **subdirectory**, and asserts `capture_all` raises `MainCaptureReadTheWorktree`; mutating the
  containment check back to `!=` reddens it.
- A test drives `cmd_capture` and `cmd_verify` against a plan whose task graph carries a cycle and
  asserts `error == 'task_graph_invalid'` with the `cycle` payload present and no row written; removing
  either handler reddens it.
- A test in which the previous executor exists with a deliberately malformed `SCRIPT_SURFACES` block and
  the generation derives zero produces `status: error` rather than a surfaces-less write.
- A test enumerates each `generate` return path and asserts the presence or absence of the stats line
  matches the docstring.
- The two guard uses read from two named sets, and a test adding a second member to the entry set does
  not change completion behaviour.
- A test seeds a frozen `phase_6.steps` carrying a `project:` step that resolves to nothing and is
  absent from `marshal.json`, and `reconcile` returns it in `stale[]` and drops it under `--apply`; a
  sibling test with the step still in `marshal.json` classifies it `broken`.
- A test backfills a candidate the composer's lane resolution would have removed and asserts it is not
  written into `phase_6.steps` — or `SKILL.md` names the exempt filters and why.
- A test seeds a non-string entry alongside a genuinely stale one, runs `reconcile --apply`, and asserts
  the call errored naming the index — never that the entry disappeared unreported.
- A test writes a past-date lock log through `log_lock_event` and asserts it lands in the same root as
  the other global logs and is relocated by dormation; `audit.py` is unchanged in the diff.
- A parametrized test seeds a task whose `number` is `None`, `''`, `'holistic'`, and absent, and
  `cmd_qgate_mechanical` returns a normal result with the expected findings for each; mutating any guard
  back to a raw conversion reddens it.
- A test builds a deliverable declaring only `Files to survey:` / `Files expected to mutate:` and
  asserts `_derive_components` returns the component the mutation path maps to; reverting to
  `affected_files` reddens it.
- A test declaring the same path under both fields produces exactly the new error, and a disjoint pair
  produces none.
- A test declaring `./src/a.py` and `src/a.py` under the two fields asserts a one-member write-set;
  removing the normalization reddens it.
- Plan `020`'s § Expected surface names both `--section` verbs with their state-discrimination
  behaviour and its D2 requires the extend-or-justify decision — or the run report carries the same
  content with the arm named.

---

### D6 — Proposals recorded for the operator; nothing decided in-run

Nine defects whose fix is a genuine design decision — a contract change, a policy that must be settled
across several gates at once, a new CLI surface, or an observation that this lane structurally cannot
take. A cloud run has no operator to ask, and the run may not self-approve a change to a contract that
governs it. So this deliverable **records**, and does not decide.

Write each proposal into the run report under a dedicated `## Proposals for the operator` heading, one
subsection per item, each carrying: the defect, the file, the options with their measured consequences,
and a recommendation. That heading is the durable channel — `doc/plans/cloud-bridge.md` § Path 3 step 3
requires the collecting orchestrator to read the report's findings and route what does not belong to
this epic, and step 6 then deletes the plan directory, so a proposal recorded anywhere else in that
directory is lost.

*Covers* `110-blocking-boundary-arms-on-a-call-not-a-state/gaps.md#G4`, `#G6`;
`190-frozen-manifest-diverges-from-live-config/gaps.md#G12`, `#G13`;
`200-lsp-derivation-resolver/gaps.md#G10`;
`240-skill-lsp-server/gaps.md#G26`;
`280-outline-plan-scope-derivation-integrity/gaps.md#G12`;
`350-outline-derived-set-closure-integrity/gaps.md#G8`, `#G15`.

1. **The completion boundary's unevaluable-query disposition** (`110/#G4`). In
   `manage-status/scripts/_cmd_lifecycle.py`, `if blocking is None:` logs a WARNING and proceeds,
   delegating the fail-closed path to "the pre-merge findings-check gate" — but `None` is produced by a
   *partial query failure*, not only by an absent executor, and at archive time the executor is present
   by construction, so `None` means the store could not be read and the plan completes anyway. The
   delegated holder ran far earlier. **Executable half, do it:** add the missing test — the branch is
   currently untested — pinning today's disposition (proceed, with the WARNING envelope) for both
   `cmd_transition --completed 6-finalize` and `cmd_archive`. **Decision half, propose it:** fail closed
   with the same `query_failed` envelope `cmd_findings_check` returns, versus keep the fail-open with a
   holder that actually runs at that point — noting that failing closed could strand a plan where the
   findings subsystem is genuinely unreachable, so it needs a documented override.
2. **The finalize-phase handshake row** (`110/#G6`). Nothing writes a `6-finalize` handshake row and the
   only finalize-phase emitter deliberately writes none, so no retrospective can distinguish "evaluated
   clean" from "never evaluated". ⛔ Do not build it here: the gap states that a sibling gap's proposed
   clean-attestation row **is** this row, and that sibling is scoped to another plan in this wave (see
   § Notes). Propose only, and name the dependency.
3. **The owed Step 1.5 observation** (`190/#G12`). The finalize-entry integration — that `compose`
   writes `phase_6.candidate_steps`, that Step 1.5 parses the TOON, that `reconciled: true` triggers the
   mandated manifest re-read — is verified only by unit tests calling `cmd_reconcile` directly; the
   wiring has never executed. ⛔ **This lane cannot discharge it**: a `doc/plans/` run never executes
   `phase-6-finalize`. Record what must be captured on the next plan-marshall-lifecycle plan that
   reaches Step 1.5 (`candidate_source: marshal.json` and `backfill_determinable: true` on a freshly
   composed manifest, with `false` meaning `compose` failed to write the candidate list) and where to
   record it.
4. **Phase 5's missing frozen-view reconciliation** (`190/#G13`). `phase_5.verification_steps` is frozen
   by the same `compose` call at the same moment and has neither a candidate snapshot nor a reconcile,
   so a plan editing its own phase-5 verification steps mid-run hits the identical divergence with no
   guard. Propose: extend the snapshot-and-reconcile pattern with a `--phase` argument, versus record the
   asymmetry and its justification in `manage-execution-manifest/SKILL.md`. Note that phase 5's step ids
   use a different vocabulary with role derivation from the trailing segment, so both the boundary
   normalization and the loadability oracle would need phase-aware handling rather than reuse.
5. **The stale tracked architecture overlay** (`200/#G10`). `.plan/project-architecture/_project.json`
   is **git-tracked** — so its staleness ships to every clone — and its description undercounts the
   marketplace's bundles while one bundle has no `enriched.json` where every sibling has one. ⛔ **Do not
   edit it here.** The lane contract states this lane never touches `.plan/`, and carving the tracked
   portion out of that prohibition is a change to the contract that governs this run, which a run may
   not self-approve. Propose the carve-out, and propose the targeted repair (hand-add the missing
   `enriched.json` matching its siblings' shape plus the one-line description fix) over a full
   regeneration, which would rewrite every module's overlay and could clobber hand-curated content.
   Re-derive the bundle count from the tree rather than quoting the number in the file.
6. **A `manage-config` path for the `code_intelligence` section** (`240/#G26`). The section appears only
   in `manage-config`'s data-model standard and its canonical key order; no verb reads or writes it, and
   the user page instructs hand-editing `.plan/marshal.json` — the one workflow this repository otherwise
   scripts, and malformed blocks fail closed silently. Propose a `manage-config` verb (read-modify-write
   over the canonical key order so ordering tests stay green) and the user-page repoint. Not built here:
   this plan's branch is `fix` and a new CLI verb is a capability.
7. **The footprint-precondition policy** (`280/#G12`). `_resolve_plan_footprint` in
   `script-shared/scripts/extension/extension_base.py` returns `None` — permanently unresolvable — for a
   `disabled` plan whose footprint *is* derivable from the main checkout, so every footprint gate reports
   "no evidence" for a whole class of plans. ⚠ It is **not** a misreport: `None` is accurate about what
   the resolver read and every consumer fails toward inclusion. It is an unmet deliverable clause with no
   current owner. The decision must be taken once **across all three gates together**
   (`extension_base._resolve_plan_footprint`, `manage-references.resolve_live_worktree`, and the
   composer's footprint resolution), and one arm has a real hazard the previous run measured: resolving a
   `disabled` plan's footprint makes `not_necessary` reachable at early compose, and the manifest
   composer drops `pre-push-quality-gate` on exactly that verdict. Propose both arms with that hazard
   attached.
8. **The glob-shaped write-set neither closure can examine** (`350/#G8`). The projection closure excludes
   patterns by design and delegates to the reconciliation check, which can only report matches a
   deliverable does not *also* enumerate — so a pattern matching zero files passes both. Executed
   control: replacing the pattern with a literal fires the projection closure immediately, so the glob is
   the sole cause. ⚠ The population block is honest here (it publishes `matches_enumerated: 0`); what is
   missing is any rule about what a zero-match declared write pattern means. That is a contract question
   about the survey-scope deliverable class — propose, do not decide.
9. **`references.affected_files` and the survey pair** (`350/#G15`). The field is written from the flat
   list and does not carry a survey-scope deliverable's `Files expected to mutate:` paths, so that whole
   mutation surface is invisible to classification validation, sibling-collision detection and the metrics
   denominator (a fourth consumer, the scope-creep check, is partly protected because it also unions task
   step targets). Propose: widen the Step-7 writer to the deduplicated write-set union, versus convert the
   three unprotected consumers to derive from `manage-solution-outline list-deliverables`. ⚠ Widening the
   field changes routing — `affected_files_count` feeds the surgical-bypass predicate and the scope bands
   — so it must land with the bypass documentation in one change. That coupling is the reason this is a
   proposal and not a fix.

*Done when:* the run report carries a `## Proposals for the operator` section with one subsection per
item above, each naming the defect, the file, the options, the measured consequence of each option where
one was measured, and a recommendation — and the plan's diff contains **no** change implementing any of
them, except the `110/#G4` test, which is asserted to pin current behaviour and is named as such in its
own docstring.

## Out of scope

Each exclusion states its reason, because there is no operator to ask mid-run.

- **Making `_main_repo_root`'s override branch return `None` for a non-canonical base dir** (the
  optional arm of `310/#G1`). Measured and **it breaks the suite** — the autouse `_plan_base_dir_sandbox`
  fixture gives every test a flat `PLAN_BASE_DIR`, so the three `main_*` columns empty out everywhere.
  It needs the sandbox to move to the canonical shape first, which is a separate change with a migration
  attached. The required arm (containment in the refusal) is in D5 and is sufficient on its own.
- **The GitHub-exact heading-slug fix in `pm-documents`' reference engine** (`120/#G1`, high). It is a
  different owning surface (the doc-reference resolver, not the architecture store) and is scoped to the
  documentation-surface plan in this same wave. D3 sub-item 1 fixes the *renderer and schema* that
  under-report its output; the two are independent, and doing both here would put one plan across two
  bundles' detectors.
- **Every `bundle-docs` / `documentation-surface` gap from the same source plans** — the dotted
  `key_packages` teaching in `manage-api.md`, `module-selection.md` and the package-selection template;
  the "index is the source of truth for which modules exist" claim in the steward references, the
  `extension-api` module-discovery standard and the `pm-plugin-development` bundle; the anti-vacuity
  tables' declared-edge row across eight surfaces; the false Maven claim's *copies*. They are scoped to
  the documentation-surface plan in this wave. **This plan fixes only the claims that live in the code
  it changes** — the `crawl_all_modules` authority docstring (`300/#G5`), the handler-inventory
  docstring, the render footer, and the `client-api.md` sections D2 and D3 must edit anyway to stay
  consistent with the payloads they change.
- **Every `tests`-topic gap from the same source plans** — the `is True` identity-check tests, the
  emitter's own tests, the collapse-call-site mutation coverage, the doc-anchored refine-guard test, the
  `CONCEPT_TYPES` doc-parity test, the unresolved-key WARNING test. They are scoped to the test-suite
  plan in this wave. This plan adds the tests its own changes require and no others.
- **Reporting on the live `.plan/architecture` store's real contents.** It is machine-local and
  git-ignored, so a cloud clone has none of it: whether production documents actually carry dotted
  `key_packages` or lack a `generation` header **cannot be settled from this runtime**. Do not go looking
  for it, and do not claim a population figure over it. The fixtures and tests named above are the whole
  evidence base.
- **Any wide "did the whole suite change" figure taken in a shared tree.** Wide runs in the audit tree
  were shown to be noise — the same mutation produced different failures in different files across runs,
  all of which passed in isolation. Verify with the targeted suites the build gate runs, and if you state
  a suite-wide number, state the conditions under which you took it.
- **`/sync-plugin-cache` after editing `marketplace/bundles/`.** `CLAUDE.md` states plainly that the sync
  is inert in this lane and that a lane plan **neither performs a sync nor records one as owed** — the
  merged bundle source is authoritative.

## Expected surface

Files this plan is expected to touch. Used to judge concurrency against sibling plans and to spot
collateral change during verification. Paths are leads — confirm each exists before editing.

- `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py` — the
  freshness verdict, the staleness guard and its emitter, the crawl-cost docstring (D1, D2, D3, D4).
- `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py` — the
  single writer, the key-package migration and its resolution check, the attribution memo, the
  `crawl_all_modules` cost docstring (D1, D2, D3).
- `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_manage.py` — `api_discover`'s
  document write, provenance back-fill, migration (D1).
- `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_enrich.py` — the index
  write-through and the `minimal` carry-over (D1, D4).
- `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py` —
  `cmd_capabilities`, `cmd_find`, `cmd_search`, the module docstring (D2, D3).
- `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_render.py` — the
  resolver-provenance footer and the profile skill counts (D2, D4).
- `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md` — capabilities
  entry shapes and vocabulary, § find and § search populations and precedence (D2, D3).
- `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/architecture-persistence.md` —
  the two recorded contract statements (D1).
- `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py`,
  `.../scripts/_plan_parsing.py` — the `key_packages` reader, survey-pair disjointness, write-set
  normalization (D1, D5).
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/extension/extension_base.py` and
  `marketplace/bundles/plan-marshall/skills/extension-api/standards/module-discovery.md` — the suppression
  note's population and the `component_refs` schema (D3).
- The Axis-C resolvers that materialize `component_refs` — re-derive the set; the audit found four, in
  `pm-documents`, `pm-plugin-development`, `pm-dev-python` and `pm-code-intelligence` (D3).
- `marketplace/bundles/plan-marshall/skills/extension-api/scripts/_derivation_merge.py` — the stale
  length-is-the-discriminator docstring. ⛔ `_path_attribution_merge.py` must **not** change (D2).
- `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py`,
  `.../scripts/_handshake_commands.py`, `.../scripts/phase_handshake.py` (D5).
- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` (D5, D6 test only).
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py`
  and `.../scripts/_manifest_validation.py` (D5).
- `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` (D5).
- `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/_locks_core.py` (D5).
- `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_qgate_mechanical.py` and
  `.../scripts/_qgate_closure.py` (D5).
- `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/_lessons_query.py` (D5).
- `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/plan.md` (D5, if present).
- `test/plan-marshall/manage-architecture/`, `test/plan-marshall/plan-marshall/`,
  `test/plan-marshall/manage-tasks/`, `test/plan-marshall/manage-execution-manifest/`,
  `test/plan-marshall/tools-script-executor/`, `test/pm-documents/plan-marshall-plugin/`,
  `test/plan-marshall/script-shared/` — new and re-scoped tests.

## Claim labels

Every scoping premise is labelled. `OBSERVED` means the audit **and** an independent adversarial
re-review each reproduced it by execution against the shipped code. `HYPOTHESIS` means it rests on
reading, on a single unreplicated measurement, or on a timing figure. Every artifact named below is
reachable from a fresh clone.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `get_project_info` derives `freshness` from the root-index entry, so a document generated against a different tree reports `fresh` | OBSERVED | `_cmd_client_query.py`, the `derive_freshness(index_entry.get(GENERATION_FIELD), tree_sha)` call in `get_project_info` |
| The same function reports `fresh` **with a description** when no `enriched.json` exists | OBSERVED | Same function; the `load_module_enriched_or_empty` call a few lines above, whose emptiness is never consulted |
| `test_info_surfaces_freshness_from_index` seeds no `enriched.json` and asserts `fresh`, pinning the defect | OBSERVED | `test/plan-marshall/manage-architecture/test_concept_model.py` |
| `api_discover` writes `enriched.json` with a raw `_write_json`, bypassing the documented single writer; these are the only two writers in the bundles tree | OBSERVED | `_cmd_manage.py`; `save_module_enriched` in `_architecture_core.py`; re-derive the writer set with a content search for `enriched.json` writes |
| `migrate_key_packages` is called only from `merge_module_data`, which no writer calls, so the migration never reaches disk | OBSERVED | `_architecture_core.py`; `manage-solution-outline.py`'s `_read_module_context` as the one outside reader |
| `migrate_key_packages` overwrites on a target-key collision, discarding a curated description with no diagnostic | OBSERVED | `_architecture_core.py`, `migrated[path] = value` |
| `cmd_capabilities` can emit `module_edges` `status: not_derivable` beside `derived_count: 1` | OBSERVED | `_cmd_client_handlers.py`; reproduce with one stub resolver disabled through the machine-local binding and one module carrying `internal_dependencies` |
| `test_capabilities_reports_not_derivable_when_every_resolver_is_disabled` asserts that state as correct, and its fixture seeds no declared dependencies | OBSERVED | `test/plan-marshall/manage-architecture/test_derivation_resolver_configuration.py` |
| `content_search` returns byte-identical payloads for a never-crawled envelope and a crawled-but-file-less one | OBSERVED | `_cmd_client_handlers.py`, `cmd_capabilities`; `test/plan-marshall/manage-architecture/test_capabilities.py` encodes both as `unavailable` |
| `_PATH_CLAIM_CACHE` memoises across calls in one process, contradicting three "nothing is memoised" statements; the memo is the cause (positive control: clearing it flips the row) | OBSERVED | `_architecture_core.py`; `_cmd_client_handlers.py`; `client-api.md`; `doc/concepts/code-intelligence.adoc` |
| `enrich_add_domain` carries `minimal: true` onto a profile it then populates, both verbs returning success with no warning, and the read-path guard then reports nothing | OBSERVED | `_cmd_enrich.py` (`merged = dict(existing)`, the append); `phase-4-plan/SKILL.md`'s minimal branch, which precedes any emptiness test |
| The Axis-C suppression note prints a deduplicated triple count with a "reference(s)" label | OBSERVED | `extension_base.py`'s note renderer; `module-discovery.md`'s dedup clause; `test_doc_references.py::test_component_refs_deduped_on_triple` |
| The true reference multiplicity behind the doc corpus's two notes is ~18 and ~504 | HYPOTHESIS (single census, and the corpus grew during the audit) | Re-derive by counting references per `(target_bundle, dep_type, resolved)` triple over the live corpus before and after the fix; report both figures |
| The other three Axis-C resolvers under-report by the same mechanism | HYPOTHESIS (shape confirmed by reading; multiplicity never censused) | Census one non-`documentation` resolver's references-per-triple; the fix is shared regardless, so a null result narrows the claim without changing the change |
| `cmd_find`'s `count` is a hybrid population; `cmd_search` already ships `count` **and** `file_count` | OBSERVED | `_cmd_client_handlers.py`, the two return payloads |
| `files_scanned` increments per inventory row, not per distinct file | OBSERVED | `_cmd_client_handlers.py`'s scan loop; a doubly-attributed fixture returns `count 2 / file_count 1 / files_scanned 2` |
| The specific over-count on this repository (≈2634 rows, of which ≈479 is the claimed-doc doubling) | HYPOTHESIS (measured once; the corpus demonstrably drifts) | Re-derive post-collapse rows, distinct paths and `documentation`'s inventory in the clone; state the numbers you got |
| `unreadable[]` emits one entry per attributing module for one physical file | OBSERVED | `_cmd_client_handlers.py`'s `unreadable.append` arms |
| `client-api.md` uses "unclaimed cross-module duplicate" without ever defining the claimed case, and § find is silent on duplication | OBSERVED | `client-api.md`; a content search for `unclaimed` in that file |
| `find` and `which-module` name different owners for `README.md` | OBSERVED | The collapse's `len(rows) < 2` early-out in `_cmd_client_handlers.py`; reproduce with both verbs |
| `crawl_all_modules`' docstring claims the crawl shells out to Maven; the crawl is subprocess-free apart from one `git` call | OBSERVED | `_architecture_core.py` versus `_cmd_client_query.py`'s subprocess-free statement and `build-maven/SKILL.md`'s "discover: Subprocess-free" |
| The containment fix to `_assert_main_capture_read_main` closes every silent row and leaves the module and its directory green | OBSERVED (measured with the change applied) | `_invariants.py`; re-derive both test counts rather than quoting 19 and 570 |
| Returning `None` from `_main_repo_root`'s override branch reddens at least seven tests via the autouse flat-`PLAN_BASE_DIR` fixture | OBSERVED (measured) | `test/conftest.py`'s `_plan_base_dir_sandbox` |
| No `except TaskGraphInvalid` and no `task_graph_invalid` error code exist in the handshake scripts | OBSERVED (asserted absence, verified by search) | `plan-marshall/scripts/_handshake_commands.py`; re-run the search — an asserted absence is verified exactly as an asserted presence |
| `read_previous_surfaces` returns `{}` on every failure mode, so Guard 5 cannot fire on an unreadable previous executor | OBSERVED | `tools-script-executor/scripts/generate_executor.py` |
| `cmd_reconcile`'s only oracle short-circuits every external step to loadable, making the stale branch unreachable for `project:` steps | OBSERVED | `manage-execution-manifest.py`; `_manifest_validation.py`'s `_check_step_loadable` and the unused `_check_step_resolvable` |
| `reconcile --apply` drops a non-string `phase_6.steps` entry with no report | OBSERVED | `manage-execution-manifest.py`'s `frozen_steps` filter and the write-back |
| The `[LOCK]` timeline is written to a log root the global-log dormation never scans | HYPOTHESIS (both paths read, never executed together) | `manage-locks/scripts/_locks_core.py`'s `_resolve_lock_log_path`; the retrospective auditor's global-log scan root — confirm by writing a past-date lock log and running dormation |
| Thirteen unguarded `number` conversions sit on the finding-emitting path in the mechanical Q-Gate, while the sibling module ships `_as_int` | OBSERVED | `manage-tasks/scripts/_cmd_qgate_mechanical.py`; `_qgate_closure.py` |
| A glob write-set matching zero files passes both closures; a literal in the same position fires the projection closure | OBSERVED (with control) | `manage-tasks/scripts/_qgate_closure.py`'s pattern filter and reconciliation check |
| `deliverable_write_set` yields two members for `./src/a.py` + `src/a.py` while its docstring promises one | OBSERVED | `manage-solution-outline/scripts/_plan_parsing.py` |
| Two section-granular read verbs already exist over plan documents, and neither is corpus-facing | OBSERVED | `manage-solution-outline` `read --section`; `manage-plan-documents` `read --section` |
| `.plan/project-architecture/_project.json` is git-tracked and its bundle description is stale | HYPOTHESIS (the count will have drifted) | `git ls-files --error-unmatch` the path, then compare its description against the bundle directories present |
| No `manage-config` verb reads or writes the `code_intelligence` section | OBSERVED (asserted absence, verified by search) | `marketplace/bundles/plan-marshall/skills/manage-config/`; re-run the search before proposing |

## Verification

Beyond each deliverable's *Done when*:

1. **Build gate.** This plan changes Python in `marketplace/bundles/`, so the build gate applies —
   `./pw verify`, per `cloud-plan-lane`'s conditional gate. Read the result; do not infer it from an
   exit code.
2. **Targeted suites.** Run, at minimum, the `manage-architecture`, `plan-marshall`, `manage-tasks`,
   `manage-execution-manifest`, `tools-script-executor`, `script-shared` and `pm-documents` test
   directories, and report the counts you got. ⚠ Do not quote a whole-suite figure as evidence of
   anything unless you took it under stated conditions — wide runs in a shared tree were shown to be
   noise during the audit.
3. **Anti-regression on the two tests that pin defects.** `test_info_surfaces_freshness_from_index` and
   `test_capabilities_reports_not_derivable_when_every_resolver_is_disabled` must both still exist, both
   still assert something, and both have docstrings that describe what they now test. A deleted test is
   a failed verification, not a passing one — say explicitly in the report what each of them asserts
   after the change.
4. **Mutation checks on the new guards.** For each of these, apply the mutation, confirm the named test
   goes red, and restore from a byte snapshot (never `git checkout` / `restore` / `stash`): revert the
   `_assert_main_capture_read_main` containment check to `!=`; revert one `_as_int` guard in the
   mechanical Q-Gate to a raw conversion; remove the normalization from `deliverable_write_set`; remove
   either `TaskGraphInvalid` handler. Report each reading.
5. **Cold read of the text whose value is what it makes a reader do.** Dispatch the pre-PR verification
   sub-agent (`cloud-plan-lane` § Step 6) with an **interpretation** task, not a conformance one. Give it
   the new `client-api.md` § find paragraph **cold** — no plan, no gap file, no other context — and ask
   it two questions: *(a) `architecture find --pattern README.md` returns one row whose `module` is
   `default`, and `architecture which-module README.md` answers `documentation`. Which is authoritative
   for ownership, and why?* and *(b) A whole-corpus `search --content` returns `count: 0` and
   `files_scanned: N`. What population is N?* The correct readings are **`which-module` is
   authoritative** — `find` reports the inventorying module — and **N is distinct files scanned**. Give
   it the new `architecture-persistence.md` statements in the same cold pass and ask a third question:
   *(c) Can a `standard` concept document be written today, and if not, what has to be settled first?*
   The correct reading is **not through the CLI — only through the Python API — and the key-space
   question (where a non-module concept document lives, given the store is keyed by module name) must be
   settled first**. If the reader takes any other reading on any question, the wording failed however
   complete it looks; fix the wording and re-run the cold read. Record which reading came back for each,
   both times if it took two.
6. **Diff review for the two forbidden edits.** Confirm by reading the diff that
   `_path_attribution_merge.py`'s length-is-the-discriminator sentence is unchanged (it is correct
   there — Axis-D has no dispatch control) and that the retrospective auditor's `audit.py` is untouched.
   State both in the report.
7. **D6 contains no implementation.** Confirm the diff implements none of the nine proposals, and that
   the one test added under D6 is asserted and documented as pinning *current* behaviour.

## Notes

**Sequencing against sibling plans in this wave.** Eight fix plans were authored from the same audit,
split by topic. This plan overlaps three of them on files, and one of them on a dependency:

- **Do not run concurrently with the documentation-surface plan.** Both edit
  `manage-architecture/standards/client-api.md`, and that plan additionally owns the doc-only gaps from
  the same source plans (the dotted-identity teaching, the index-gatekeeper claim, the anti-vacuity
  tables, the Maven-claim copies). This plan edits `client-api.md` only where the payload it changes
  makes the old text false. Landing order is either way, but not at the same time.
- **Do not run concurrently with the finalize/blocking-boundary plan.** Both edit
  `manage-status/scripts/_cmd_lifecycle.py` and `manage-execution-manifest.py`. Furthermore, D6 item 2
  (`110/#G6`, the finalize handshake row) **collapses into** that plan's fix for `110/#G2`: the
  clean-attestation row that gap proposes *is* the row this one asks for. That is why it is a proposal
  here and not a build — do not build it in either plan without checking the other.
- **Do not run concurrently with the test-suite plan**, which adds tests over the same
  `manage-architecture` guards this plan changes; a test written against the pre-fix behaviour and a fix
  landing at once produces a conflict neither plan can resolve alone.
- **No ordering constraint against the LSP/resolver, measurement, detector or lane-contract plans** —
  disjoint files.

**Where the evidence came from, and what beat what.** Every defect above was found by a ground-truth
audit of a landed plan and then re-reviewed adversarially. Where the two disagreed, the adversarial
review won, and this plan already carries its corrections rather than the original claims. Three of
those corrections change what a run should do and are called out at their sites: the `310/#G1` optional
arm that **breaks the suite** and is excluded; the `120/#G3` fix that must **not** be "one entry per
reference" because a shipped test pins the dedup; and the `160/#G1` *Done when* that was rewritten
because the original asserted a condition which already passes. A fourth is a severity correction: the
bucket manifest carries `310/#G1` as high while its entry and the review both rate it medium, with the
reasoning written out — it is fixed here anyway because the fix is one line and was measured safe.

**Machine-local paths, named only so you do not go looking.** The orchestrator ledger, the plan specs,
the landing records and the live `.plan/architecture` store are all under `.plan/`, which is git-ignored
and **absent from this clone**. Nothing in this plan requires any of them. The one `.plan/` path that is
git-tracked — `.plan/project-architecture/` — is deliberately left untouched (D6 item 5), because the
lane contract's `.plan/` prohibition governs this run and a run may not amend the contract that governs
it.

**The gap files.** Every `{source-plan}/gaps.md#GN` reference above points at a git-tracked file that
should be on `main` when this runs. They are **corroboration, not required reading** — everything needed
to execute is restated here, because `doc/plans/cloud-bridge.md` § Path 3 deletes a landed cloud plan's
directory at collect and the file may already be gone. If a cited file is missing, that is not a blocker;
say so in the report and proceed.

## Gap coverage

Fifty-nine gaps across seventeen source plans: **five high, thirty-two medium, twenty-two low** by the
severity the entries themselves carry. Every one is mapped. `sev` is the severity carried in the
audit's bucket manifest; where the gap entry and its adversarial review re-rated it, the note says so
— and for `310/#G1` they agree at **medium** against a manifest that read high, so the entry wins and
the totals above count it as medium. Re-derive these three figures from the `Severity` field of the
cited entries rather than trusting this line.

| Deliverable | Source plan | Gap | sev |
|---|---|---|---|
| D1 | 150-architecture-store-concept-model | G1 | high |
| D1 | 150-architecture-store-concept-model | G2 | high |
| D1 | 150-architecture-store-concept-model | G3 | medium |
| D1 | 150-architecture-store-concept-model | G4 | medium |
| D1 | 150-architecture-store-concept-model | G5 | medium |
| D1 | 150-architecture-store-concept-model | G6 | medium |
| D1 | 150-architecture-store-concept-model | G7 | medium |
| D1 | 150-architecture-store-concept-model | G8 | medium |
| D1 | 150-architecture-store-concept-model | G9 | low |
| D1 | 150-architecture-store-concept-model | G10 | low |
| D1 | 150-architecture-store-concept-model | G14 | low |
| D1 | 150-architecture-store-concept-model | G17 | low |
| D2 | 220-resolver-configuration | G1 | high |
| D2 | 220-resolver-configuration | G2 | low |
| D2 | 220-resolver-configuration | G10 | low |
| D2 | 130-lsp-shaped-query-api | G1 | medium |
| D2 | 130-lsp-shaped-query-api | G2 | medium |
| D2 | 130-lsp-shaped-query-api | G3 | low |
| D2 | 130-lsp-shaped-query-api | G9 | low |
| D2 | 135-remove-lsp-query-facade | G2 | low |
| D2 | 135-remove-lsp-query-facade | G15 | low |
| D3 | 120-documentation-surface-provider | G3 | high |
| D3 | 120-documentation-surface-provider | G7 | medium |
| D3 | 120-documentation-surface-provider | G8 | medium |
| D3 | 120-documentation-surface-provider | G9 | low |
| D3 | 120-documentation-surface-provider | G14 | low |
| D3 | 130-lsp-shaped-query-api | G5 | medium |
| D3 | 130-lsp-shaped-query-api | G6 | low |
| D3 | 300-freshness-gate-cannot-distinguish-test-authored-evidence | G3 | medium |
| D3 | 300-freshness-gate-cannot-distinguish-test-authored-evidence | G5 | medium |
| D4 | 160-empty-skill-resolution-indistinguishable-from-minimal | G2 | high |
| D4 | 160-empty-skill-resolution-indistinguishable-from-minimal | G1 | medium |
| D4 | 160-empty-skill-resolution-indistinguishable-from-minimal | G3 | medium |
| D4 | 160-empty-skill-resolution-indistinguishable-from-minimal | G9 | medium |
| D4 | 160-empty-skill-resolution-indistinguishable-from-minimal | G13 | low |
| D4 | 160-empty-skill-resolution-indistinguishable-from-minimal | G14 | low |
| D5 | 310-main-sha-records-the-pinned-cwd | G1 | high in manifest; **medium** per the entry and its adversarial review |
| D5 | 310-main-sha-records-the-pinned-cwd | G9 | medium |
| D5 | 040-generator-fails-open-and-its-fixtures-cannot-see-it | G15 | medium |
| D5 | 040-generator-fails-open-and-its-fixtures-cannot-see-it | G10 | low |
| D5 | 110-blocking-boundary-arms-on-a-call-not-a-state | G12 | low |
| D5 | 190-frozen-manifest-diverges-from-live-config | G1 | medium |
| D5 | 190-frozen-manifest-diverges-from-live-config | G3 | medium |
| D5 | 190-frozen-manifest-diverges-from-live-config | G8 | medium |
| D5 | 290-auditor-detector-integrity | G7 | medium |
| D5 | 350-outline-derived-set-closure-integrity | G7 | medium |
| D5 | 350-outline-derived-set-closure-integrity | G10 | medium |
| D5 | 350-outline-derived-set-closure-integrity | G14 | low |
| D5 | 350-outline-derived-set-closure-integrity | G16 | low |
| D5 | 020-corpus-residency-admission-control | G11 | medium |
| D6 | 110-blocking-boundary-arms-on-a-call-not-a-state | G4 | medium |
| D6 | 110-blocking-boundary-arms-on-a-call-not-a-state | G6 | low |
| D6 | 190-frozen-manifest-diverges-from-live-config | G12 | medium |
| D6 | 190-frozen-manifest-diverges-from-live-config | G13 | low |
| D6 | 200-lsp-derivation-resolver | G10 | medium |
| D6 | 240-skill-lsp-server | G26 | low |
| D6 | 280-outline-plan-scope-derivation-integrity | G12 | medium |
| D6 | 350-outline-derived-set-closure-integrity | G8 | medium |
| D6 | 350-outline-derived-set-closure-integrity | G15 | medium |

Counts: D1 12, D2 9, D3 9, D4 6, D5 14, D6 9 — fifty-nine. Re-derive that sum from the table rather than
trusting this line. All five high-severity gaps are fixed in a deliverable (`150/#G1`, `150/#G2` in D1;
`220/#G1` in D2; `120/#G3` in D3; `160/#G2` in D4); none is out of scope. `310/#G1` is fixed in D5 too
— it is listed separately here only because it is **medium**, not high, per its entry and review.

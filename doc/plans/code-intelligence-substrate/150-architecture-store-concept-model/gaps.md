# Gaps — 150-architecture-store-concept-model

The concept model landed, but three of its four constructs stop short of the store they were meant
to govern. The **type** vocabulary is complete and correctly enforced. **Path identity** is enforced
on new writes only — the dotted→path migration runs in one in-memory merge path, is never written
back, is skipped entirely by one consumer, and can silently discard a curated description when two
dotted keys collide onto one path. **Freshness** is derived from the root-index snapshot rather than
from the concept document's own header, and because no enrich verb refreshes that snapshot the two
diverge on the first enrich after a discover — at which point `architecture info` reports `fresh`
for a document written against a different tree, and for a module with no concept document at all.
**Provenance** is never back-filled: a pre-field document survives `discover` with no `generation`
header and stays permanently `unknown`. Fourteen gaps below, one per instance, plus the shipped
documentation that still describes the retired dotted identity.

---

## G1 — Derive the `info` freshness verdict from the concept document, not the index snapshot

- **Kind:** bug
- **Severity:** high
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py:209`
  (`get_project_info`), reading `index_entry.get(GENERATION_FIELD)`
- **Evidence:** probe against the shipped `get_project_info` with the index holding
  `tree_sha: TREE-A` (matching the current tree) and the concept document holding `tree_sha: TREE-B`:

  ```
  CASE B  document tree_sha: TREE-B | current: TREE-A | info freshness: fresh
          | document-derived verdict: stale
  ```

  The document-derived verdict (`derive_freshness(doc['generation'], 'TREE-A')`) is `stale`; the
  shipped column says `fresh`. The divergence is reachable in normal operation: the index is written
  only by `api_discover` (`_cmd_manage.py:683-686`) while the document is rewritten by every enrich
  verb (`_architecture_core.py:763`), so the two headers separate on the first enrich after a
  discover, and any return of the working tree to an earlier state then produces exactly this state.
- **Why it matters:** this is the inverse of D4's *Done when* — "a document generated against a
  different tree is reported stale". The column exists so a consumer can skip stale concept
  documents before loading them; reporting `fresh` for a stale document makes it load and trust
  content generated against a tree that no longer exists. A guard that fails open is worse than no
  guard, because callers stop checking.
- **Action:** compute the verdict from the document's own `generation` header. Either read
  `load_module_enriched_or_empty(name, …).get('generation')` (the function already loads the
  document at `_cmd_client_query.py:200` for `purpose`, so this costs nothing in that path), or —
  to preserve the body-free filtering D4 promises — keep the index read but fall back to `unknown`
  whenever the index header cannot be shown to still describe the document (see G3/G6 for making the
  index trustworthy instead).
- **Done when:** a test seeds an index entry whose `tree_sha` equals the current tree and a concept
  document whose `tree_sha` differs, calls `get_project_info`, and asserts the module row's
  `freshness` is `stale`.
- **Effort:** S
- **Risk if fixed:** if the fix reads the document body, D4's "filter before loading" property is
  lost for `info` — though that path already loads every body at `_cmd_client_query.py:200`, so
  nothing regresses in practice. Modules whose index and document disagree will flip from `fresh` to
  `stale`, which may surprise a consumer that had been treating the column as stable.

---

## G2 — Report `unknown`, not `fresh`, when the concept document does not exist

- **Kind:** bug
- **Severity:** high
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py:202,208-209`
- **Evidence:** probe with an index entry present and no `enriched.json` on disk:

  ```
  CASE A  enriched.json exists: False | info freshness: fresh | description: Does things
  ```

  `_cmd_client_query.py:200` already loads the (empty) document via
  `load_module_enriched_or_empty`, so the absence is known at the point the row is built and is
  simply not consulted.
- **Why it matters:** `info` asserts a freshness verdict, and a description, for a concept document
  that does not exist. A consumer filtering on `freshness == fresh` will select this module and then
  find nothing to read. Distinct instance from G1: G1 is a *diverged* header, this is a *missing
  document*, and fixing G1 by making the index authoritative would leave this one open.
- **Action:** in `get_project_info`, when the loaded enriched document is empty, force
  `freshness` to `FRESHNESS_UNKNOWN` (and consider blanking `description`, since it too describes a
  document that is not there).
- **Done when:** a test seeds an index entry carrying a `generation.tree_sha` equal to the current
  tree, writes no `enriched.json`, and asserts the module row's `freshness` is `unknown`.
- **Effort:** S
- **Risk if fixed:** `test_info_surfaces_freshness_from_index`
  (`test/plan-marshall/manage-architecture/test_concept_model.py:224-249`) currently seeds **no**
  `enriched.json` and asserts `fresh` — it encodes this defect as expected behaviour and must be
  rewritten to seed a document, or it will go red for the right reason and be "fixed" the wrong way.

---

## G3 — Write the dotted→path `key_packages` migration back to disk

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py:919-926`
  (`merge_module_data`, the only call site of `migrate_key_packages`) and
  `:743-765` (`save_module_enriched`, which does not migrate)
- **Evidence:** probe — seed a document with `key_packages: {'com.example.pkg': …}`, run
  `enrich_module('mod', 'NEW RESPONSIBILITY')`, then read the file back:

  ```
  PERSISTED key_packages    : ['com.example.pkg']
  merged key_packages       : ['mod/src/pkg']
  ```

  The same holds through `api_discover(force=True)`:
  `after discover — key_packages: ['com.example.pkg']`. Note the asymmetry that shows this is an
  oversight rather than a design choice: `type` **is** back-filled to disk on the same code path
  (`after discover — type: module`), because `migrate_concept_document` runs inside
  `load_module_enriched_or_empty`; `key_packages` is not, because its migration lives only in
  `merge_module_data`, which no writer calls.
- **Why it matters:** D1's *Done when* is "every persisted key resolves to a path". It does not.
  The dotted pseudo-identifier system the deliverable exists to retire remains in the persisted
  store indefinitely, so the two identity schemes still have to be kept in sync by hand — the exact
  problem the plan opened with. Every consumer that does not happen to route through
  `merge_module_data` sees the un-migrated keys (see G4).
- **Action:** apply `migrate_key_packages` inside `save_module_enriched` (it has `project_dir`;
  it needs the module's derived `packages` bridge, obtainable via `load_module_derived` or by
  threading the already-loaded derived map through from the enrich verbs). Alternatively migrate in
  `api_discover` at `_cmd_manage.py:672`, where both the document and the crawled derived data are
  already in hand — that path already back-fills `type`, so `key_packages` would follow the same
  rule.
- **Done when:** a test writes a document with a legacy dotted `key_packages` key, invokes a write
  verb (or `api_discover`), re-reads the file **from disk**, and asserts the key is the repo-relative
  path with no dotted key remaining.
- **Effort:** M
- **Risk if fixed:** a document whose derived `packages` bridge is unavailable at write time (module
  not yet crawled, or a build system that emits no `packages`) would keep its dotted key; the write
  must not fail in that case. Migrating at `save` time makes every enrich verb depend on derived
  data being loadable, which is a new coupling — migrating in `api_discover` avoids it.

---

## G4 — Route `manage-solution-outline`'s `key_packages` read through the path migration

- **Kind:** omission
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py:918,929-930`
- **Evidence:**

  ```python
  enriched = load_module_enriched_or_empty(name, project_dir)
  ...
  if enriched.get('key_packages'):
      module_info['key_packages'] = list(enriched['key_packages'].keys())
  ```

  `load_module_enriched_or_empty` migrates the concept `type` but **not** `key_packages` — that
  migration lives in `merge_module_data` (`_architecture_core.py:919-926`), which this call path
  does not use. Confirmed by grepping every `key_packages` reader across
  `marketplace/bundles/`: this is the only production reader outside `manage-architecture`, and it
  is the only one that skips the migration.
- **Why it matters:** `manage-solution-outline` feeds `phase-3-outline`'s module and package
  selection (its `SKILL.md:235` documents consumers reading these fields directly). Until G3 lands,
  every legacy store surfaces dotted pseudo-identifiers to the outline phase while
  `architecture module` surfaces paths for the same module — two different answers to "what are this
  module's key packages", which is precisely the second-identity-system failure D1 set out to end.
- **Why it is a separate instance from G3:** even after G3 back-fills the store, this reader remains
  the one path with no migration, so a store written by an older toolchain (or a hand-edited
  document) still leaks dotted keys here.
- **Action:** have this reader call `merge_module_data(name, project_dir)` (it already loads derived
  data at `:908`, so the merge is nearly free), or apply `migrate_key_packages` explicitly with the
  derived `packages` map it already holds.
- **Done when:** a test seeds a module whose `enriched.json` holds a dotted `key_packages` key and a
  `derived.json` whose `packages` map bridges it, invokes the outline architecture-context reader,
  and asserts the returned `key_packages` list contains the repo-relative path and not the dotted
  name.
- **Effort:** S
- **Risk if fixed:** `merge_module_data` raises `DataNotFoundError` when `derived.json` is missing,
  whereas the current code tolerates that at `:909-913`; the migration must be applied without
  losing that tolerance.

---

## G5 — Stop silently discarding a description when two dotted keys migrate to the same path

- **Kind:** bug
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py:436-439`
  (`migrate_key_packages`)
- **Evidence:**

  ```
  migrate_key_packages({'a.b': {'v':1}, 'c.d': {'v':2}},
                       {'a.b': {'path':'pkg'}, 'c.d': {'path':'pkg'}}, root)
  -> ({'pkg': {'v': 2}}, [])
  ```

  `migrated[path] = value` overwrites unconditionally, and the discarded key never reaches the
  `unresolved` list, so `_log_unresolved_package_keys` (`:882-896`) never fires.
- **Why it matters:** a curated package description — LLM-generated content the enrichment workflow
  exists to produce — vanishes from every merged read with no signal at all. The function's own
  docstring promises "a named outcome, never a silent drop" (`:425`); the collision path violates
  that promise while reporting success. Two dotted names mapping to one directory is not exotic: a
  JVM package and its nested sub-package can share a path entry, and any hand-authored duplicate does
  too.
- **Action:** detect an already-present target key before assigning. Either merge the two entries,
  or keep the first and report the collision through the existing `unresolved`/WARNING channel (or a
  new `collisions` return element) so the loss is observable.
- **Done when:** a test passes two dotted keys whose derived entries share one `path` and asserts
  that no curated description is lost — either both survive under a merged entry, or the collision
  is reported in the function's returned diagnostics.
- **Effort:** S
- **Risk if fixed:** callers destructure the current two-tuple `(migrated, unresolved)`; adding a
  third element changes that signature. Reporting collisions through `unresolved` avoids the
  signature change but conflates two different conditions in the WARNING text.

---

## G6 — Refresh the root-index `description`/`generation` when a concept document is written

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_enrich.py:118`
  (`enrich_module`, and the sibling `save_module_enriched` calls at `:159,364,478,521,553`) — none
  touches `_project.json`. The index is written only at
  `_cmd_manage.py:683-686,710`.
- **Evidence:** probe — after `enrich_module('mod', 'NEW RESPONSIBILITY')`:

  ```
  PERSISTED responsibility  : NEW RESPONSIBILITY
  PERSISTED generation      : {'by': 'architecture', 'tree_sha': None}
  INDEX entry after enrich  : {'description': 'OLD DESC',
                               'generation': {'by': 'architecture', 'tree_sha': 'TREE-OLD'}}
  ```
- **Why it matters:** D3's purpose is that "a consumer can decide which concept documents to open
  from the index alone". The index reports the description the module had at the last `discover`,
  not the one it has now, so the decision is made on stale information. This is also the root cause
  of G1: the index and the document carry different `generation` headers, which is what lets the
  freshness column disagree with the document. `architecture-persistence.md:86,96-97` does disclose
  the index as a snapshot "refreshed at `discover` time", so the behaviour is documented — but
  documenting a stale surface does not make it serve the purpose the deliverable claims for it.
- **Why it is a separate instance from G1:** G1 is the read-side fix (do not trust the snapshot);
  this is the write-side fix (keep the snapshot true). Either alone leaves a real defect: fixing only
  G1 leaves `description` stale; fixing only G6 leaves the missing-document case (G2) open.
- **Action:** have `save_module_enriched` — or a small helper the enrich verbs call after it —
  update the module's entry in `_project.json` with the document's current `responsibility` and
  `generation`. Keep it write-through and tolerant of a missing `_project.json`.
- **Done when:** a test runs an enrich verb that changes `responsibility`, then reads
  `_project.json` and asserts the module's index entry carries the new description and the
  document's current `generation`, without an intervening `discover`.
- **Effort:** M
- **Risk if fixed:** `enrich all` writes many modules in one invocation; a naive write-through would
  rewrite `_project.json` once per module. Batch the index update, or accept the cost knowingly.
  Also, `_project.json` is written outside the atomic tmp+swap protocol here, so a crash mid-run
  could leave index and documents inconsistent — the same exposure `enrich_project` already has at
  `_cmd_enrich.py:59`.

---

## G7 — Back-fill `generation` onto pre-field concept documents

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_manage.py:672-677`
  (`api_discover` stamps `build_generation` only on the first-seen branch) and `:717`
  (raw `_write_json`, bypassing `save_module_enriched`)
- **Evidence:** probe — seed a legacy document with no `type` and no `generation`, run
  `api_discover(force=True)`:

  ```
  after discover — keys        : ['key_packages', 'responsibility', 'type']
  after discover — type        : module
  after discover — generation  : <ABSENT>
  index entry                  : {'description': 'Legacy R', 'generation': {}}
  ```

  `type` is back-filled; `generation` is not, and nothing else will ever add it until some enrich
  verb happens to rewrite that module.
- **Why it matters:** D4 states "**Every** concept document records who generated it … and against
  which tree". For the entire pre-existing store that is false, and `derive_freshness` returns
  `unknown` for all of it — so D4's freshness signal is inert across the whole installed base until
  each module is individually re-enriched. The preservation of the existing header is deliberate and
  correctly reasoned (`_cmd_manage.py:663-668` — do not falsely restamp preserved content), but the
  correct conclusion from that reasoning is a *distinguishable* back-fill, not silence.
- **Action:** when a preserved document carries no `generation`, write a header that records the
  absence honestly rather than claiming the current tree — e.g. `{'by': 'architecture',
  'tree_sha': None}`, which `derive_freshness` already maps to `unknown` (`_architecture_core.py:361`)
  and which makes "migrated, provenance unknown" distinguishable from "field never existed". Route
  the write through `save_module_enriched` (see G8) so the rule lives in one place.
- **Done when:** a test seeds a document with no `generation`, runs `api_discover`, and asserts the
  document on disk carries a `generation` key whose freshness verdict is `unknown`.
- **Effort:** S
- **Risk if fixed:** must not stamp the *current* tree sha onto preserved content — that would turn
  every legacy document into a false `fresh`, converting an inert signal into a wrong one.

---

## G8 — Route `api_discover`'s concept-document write through `save_module_enriched`

- **Kind:** bug
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_manage.py:717`
  — `_write_json(module_tmp / DIR_PER_MODULE_ENRICHED, module_documents[module_name])`
- **Evidence:** `save_module_enriched` (`_architecture_core.py:743-765`) documents itself as "the
  single concept-document writer" and enforces both concept-model constructs "so every persisted
  document carries them regardless of which caller wrote it". `api_discover` does not use it; it
  writes the raw dict. Grepping every writer of `enriched.json` across `marketplace/bundles/` returns
  exactly two: `save_module_enriched` and this line.
- **Why it matters:** the plan raised this as an explicit HYPOTHESIS — *"The named save/load
  accessors are the **only** writers. ⛔ Enumerate the callers. A second writer that does not learn
  the new validation would produce documents the readers refuse."* The hypothesis is **false** and
  the run neither reported it nor closed it. Today the bypass is benign only by accident (the
  documents happen to arrive pre-migrated from `load_module_enriched_or_empty` or
  `_empty_module_enrichment`), and it is already the direct cause of G7. Any future invariant added
  to `save_module_enriched` will silently not apply to the `discover` path.
- **Action:** write through `save_module_enriched`, or extract the invariant-stamping into a helper
  both writers call. The tmp-staging directory complicates this — `save_module_enriched` resolves
  its own path from `project_dir` — so the helper form is likely cleaner: have it return the
  document to write, and let each caller place it.
- **Done when:** either `_write_json` no longer appears in `_cmd_manage.py` for `enriched.json`, or
  a test asserts that a document written by `api_discover` and one written by `save_module_enriched`
  carry the identical set of concept-model fields.
- **Effort:** M
- **Risk if fixed:** the tmp+swap atomicity of `discover --force` must be preserved —
  `save_module_enriched` writes to the real path, not the staging directory, so a careless
  refactor would break the atomic swap.

---

## G9 — Refuse a migrated key that does not resolve

- **Kind:** bug
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py:437-439`
- **Evidence:**

  ```
  migrate_key_packages({'com.gone': …}, {'com.gone': {'path': 'no/such/dir'}}, root)
  -> ({'no/such/dir': …}, [])     # and package_key_resolves('no/such/dir', root) is False
  ```

  The bridge `path` is written straight into the migrated map with no `package_key_resolves` check,
  and the key is reported as successfully migrated.
- **Why it matters:** the migration produces a key that fails the very invariant D1 asserts
  ("every persisted key resolves to a path") while reporting no problem. A package directory deleted
  after the last crawl yields a silently broken key rather than the named unresolved outcome the
  function promises.
- **Action:** check `package_key_resolves(path, project_dir)` before adopting the bridge path; on
  failure, keep the original key and append it to `unresolved` — the branch already exists at
  `:440-442`.
- **Done when:** a test supplies a derived bridge whose `path` does not exist on disk and asserts the
  dotted key is returned in `unresolved` rather than rewritten.
- **Effort:** S
- **Risk if fixed:** in a project where the crawl and the filesystem legitimately disagree
  (a generated source tree not yet built), keys that previously migrated would start appearing in the
  WARNING. That is the correct signal, but it will be newly noisy.

---

## G10 — Refuse the project root as a package key

- **Kind:** bug
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py:392`
  — `if candidate != root and root not in candidate.parents:`
- **Evidence:**

  ```
  package_key_resolves('.',  root) -> True
  package_key_resolves('./', root) -> True
  ```

  The `candidate == root` allowance, added so the containment check would not reject the root, also
  makes the root itself a valid key.
- **Why it matters:** `enrich package --package .` would attach a package description to the entire
  repository, producing a `key_packages` entry that identifies nothing. Minor, but it is a
  fail-open in the write gate D1 exists to close.
- **Action:** reject `candidate == root` explicitly — a package key must name something *inside* the
  tree, not the tree itself.
- **Done when:** a test asserts `package_key_resolves('.', root)` and
  `package_key_resolves('./', root)` are both `False`, while `package_key_resolves('pkg', root)`
  stays `True`.
- **Effort:** S
- **Risk if fixed:** a single-module project whose module path is `.` might legitimately want a
  root-level key; check whether any fixture or live store relies on it before tightening.

---

## G11 — Correct the `--package` option description in `manage-api.md`

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/manage-api.md:257`
- **Evidence:** the shipped row reads

  ```
  | `--package` | Yes | - | Full package name |
  ```

  while `architecture.py:377-378` validates the argument as a repo-relative path and
  `architecture-persistence.md:338` states keys are "**Repo-relative paths (path is identity)**, not
  dotted pseudo-identifiers". `git show bc86398 -- …/manage-api.md` shows the run changed exactly one
  hunk in this file (the "Data Sources" paragraph); this table was not touched, contradicting the
  report's finding #4 ("the two borderline items (`manage-api.md`, module docstring) tightened in the
  same commit").
- **Why it matters:** `manage-api.md` is the API reference an agent reads before invoking
  `enrich package`. Following it produces a dotted name, which is now **refused** with
  `error: non_resolving_package_key` — the documentation actively instructs a failing call.
- **Action:** change the description to "Repo-relative path to the package (path is identity; must
  resolve to a real filesystem location)" and note the `non_resolving_package_key` refusal, matching
  `SKILL.md:576`.
- **Done when:** `manage-api.md` contains no description of `--package` as a package *name*, and its
  `enrich package` section states the path-identity rule and the named error.
- **Effort:** S
- **Risk if fixed:** none.

---

## G12 — Correct the dotted `key_packages` patterns in `phase-3-outline/standards/module-selection.md`

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-3-outline/standards/module-selection.md:20-27`
- **Evidence:** the shipped table teaches `key_packages` as dotted package patterns:

  ```
  | key_package Pattern | Typical Role |
  | `...core.pipeline`  | Main processing logic |
  | `...core.model`     | Domain/data classes |
  | `...api`            | Public interfaces |
  ```

  Keys are now repo-relative paths (`architecture-persistence.md:387`;
  `client-api.md:343` shows the corrected form
  `oauth-sheriff-core/src/main/java/…/pipeline`). The file was not touched by `bc86398`.
- **Why it matters:** this standard drives module and package selection in `phase-3-outline`. It
  teaches the retired identity system to the phase that consumes `key_packages` most directly, and
  it lives in the **same bundle** (`plan-marshall`) that the run's Step-6 instruction says to sweep
  beyond the diff. The report's own "What have we learned" section identifies the incomplete
  beyond-diff sweep as the run's one execution weakness; this is a surviving instance of it.
- **Action:** rewrite the pattern table in path terms (e.g. `.../core/pipeline`), or replace the
  pattern column with a reference to `architecture-persistence.md` § `key_packages` so it cannot
  drift again.
- **Done when:** `module-selection.md` describes `key_packages` keys as repo-relative paths and
  contains no dotted-identifier examples.
- **Effort:** S
- **Risk if fixed:** none.

---

## G13 — Correct "Package name from key_packages" in the package-selection template

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-3-outline/templates/package-selection.md:26`
- **Evidence:** `| `package` | `architecture module --module X --full` | Package name from key_packages |`
  — the named source now emits repo-relative paths, not names
  (`client-api.md:343,391`).
- **Why it matters:** the template shapes what an outline records for package placement; describing
  the value as a name invites an author to convert the path back into a dotted name, reintroducing
  by hand exactly the sync burden D1 removed. Separate instance from G12 — different file, different
  surface (template versus standard).
- **Action:** change to "Repo-relative package path from `key_packages`".
- **Done when:** the template's field table describes the value as a path.
- **Effort:** S
- **Risk if fixed:** none.

---

## G14 — Record "at what point" a concept document was generated, or amend the contract

- **Kind:** omission
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py:335-344`
  (`build_generation`), pinned by
  `test/plan-marshall/manage-architecture/test_concept_model.py:190`
- **Evidence:** D4 reads "Every concept document records who generated it, **at what point**, and
  against which tree." `build_generation` returns `{'by': by, 'tree_sha': …}` — two of the three.
  The test asserts `set(generation) == {'by', 'tree_sha'}`, which locks the omission in: adding the
  third field would turn that test red. Neither `report-01.md` nor the PR body mentions the
  omission.
- **Why it matters:** the plan's ⭐ note argues a tree identifier beats a wall-clock **expiry** —
  that justifies not *deriving the verdict* from a timestamp, which the implementation correctly
  does not. It does not justify not *recording* when. Without it, a store cannot answer "which
  documents have not been regenerated in a long time" or order two `unknown` documents, and there is
  no way to tell a document written seconds ago from one written a year ago against the same tree.
- **Action:** either add a monotonically meaningful "at what point" field to `build_generation`
  (leaving `derive_freshness` reading `tree_sha` only, so the verdict stays tree-derived), relaxing
  `test_build_generation_shape` to assert the required keys are a subset; **or** record the
  deliberate deviation in `architecture-persistence.md` § "The concept model", stating that
  provenance intentionally records who and against-which-tree but not when, and why.
- **Done when:** either `build_generation` emits a third provenance field and a test asserts it, or
  `architecture-persistence.md` carries an explicit statement that "at what point" is deliberately
  not recorded, with the reason.
- **Effort:** S
- **Risk if fixed:** a timestamp is exactly the mtime-shaped evidence this project has repeatedly
  ruled inadmissible — it must never become an input to `derive_freshness`, or the tree-identifier
  guarantee is undone. Adding the field also changes every persisted document's shape, so any
  consumer asserting on the exact generation key set breaks.

---

## G15 — Guard the `CONCEPT_TYPES` vocabulary against documentation drift

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/architecture-persistence.md:336`
  restates the five values verbatim; `_architecture_core.py:209-217` declares them
- **Evidence:** the doc enumerates "(`module`, `skill`, `script`, `standard`, `decision_record`)" as
  prose. `test_vocabulary_is_closed_and_enumerated_once`
  (`test_concept_model.py:156-159`) checks only the code constant; nothing compares the two. D2's
  *Done when* is "the vocabulary is enumerated in one place" — it is enumerated in two, one of which
  is unguarded.
- **Why it matters:** adding a sixth concept type would leave the standard silently describing a
  closed set that is no longer closed, and the standard is what a writer consults before choosing a
  type.
- **Action:** add a test that parses the accepted-types list out of
  `architecture-persistence.md` and asserts set-equality with `CONCEPT_TYPES`.
- **Done when:** a test fails if a member is added to `CONCEPT_TYPES` without updating
  `architecture-persistence.md`.
- **Effort:** S
- **Risk if fixed:** a doc-parsing test is brittle against reformatting; anchor it on a stable
  marker rather than on line position.

---

## G16 — Cover the unresolved-key WARNING, which can currently be swallowed unobserved

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py:882-896`
  (`_log_unresolved_package_keys`), called from `:926`
- **Evidence:** the whole body is wrapped in `try: … except Exception: pass`. No test in
  `test_concept_model.py` or the wider `manage-architecture` suite asserts the WARNING is emitted
  from `merge_module_data` — the two migration tests
  (`test_migrate_key_packages_reports_unresolved_without_dropping`,
  `test_merge_module_data_migrates_dotted_key_packages`) check only the returned data.
- **Why it matters:** the report's D1 guarantee is "unresolved keys → non-blocking WARNING, never
  silently dropped". The data is indeed not dropped, but the *signal* rests entirely on a log call
  that swallows its own failure with nothing observing it. If `plan_logging` moved or its signature
  changed, the guarantee would evaporate with a green build.
- **Action:** add a test that seeds a document with a dotted key having no derived bridge, calls
  `merge_module_data`, and asserts `log_entry` was invoked at `WARNING` with the key named
  (monkeypatch or capture the logging seam).
- **Done when:** a test goes red if the `log_entry` call in `_log_unresolved_package_keys` is
  removed.
- **Effort:** S
- **Risk if fixed:** the deferred `from plan_logging import log_entry` is imported inside the
  function, so the test must patch the source module rather than a module-level name.

---

## G17 — Provide a write path for the non-`module` concept types

- **Kind:** incomplete
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py:209-217`
  (vocabulary) versus `architecture.py` (no CLI verb accepts a `type`)
- **Evidence:** grepping the enrich and manage handlers shows every write path supplies either
  `_empty_module_enrichment()` (`_cmd_manage.py:526`, hard-coded `LEGACY_CONCEPT_TYPE`) or a
  previously-loaded document. No argument, no verb, and no code path sets `skill`, `script`,
  `standard`, or `decision_record`.
- **Why it matters:** D2's stated purpose is "so the store can hold more than modules (skill,
  script, standard, decision record) **without standing up a parallel store**". The vocabulary is
  declared and enforced, satisfying the literal *Done when*, but the capability it was declared for
  is unreachable through the shipped surface — which invites exactly the parallel store the
  deliverable set out to prevent when the resolver plans need to persist a non-module concept.
- **Action:** add an optional `--type` to the concept-document write path (validated by
  `validate_concept_type`, defaulting to `module`), or record in
  `architecture-persistence.md` that non-`module` types are reserved for a named later plan and
  currently reachable only through the Python API.
- **Done when:** either a CLI invocation can persist a document with `type: standard` and a test
  asserts it round-trips, or the standard states which plan owns making the extra types writable.
- **Effort:** M
- **Risk if fixed:** the store's directory layout is keyed by module name
  (`get_module_dir`, `_architecture_core.py:171-173`); persisting a non-module concept needs a key
  space decision that this plan deliberately deferred. Do not add the CLI flag without settling
  where a `standard` concept document lives.

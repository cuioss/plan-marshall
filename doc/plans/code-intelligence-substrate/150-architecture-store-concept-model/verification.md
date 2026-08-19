# Verification — 150-architecture-store-concept-model

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory at audit start)
**Tree state:** `8ae4805` on `claude/code-intelligence-substrate-analysis-kah884`
(audit opened at `61a43e5`; HEAD advanced during the run because sibling audit agents committed to
the same branch. The plan's landed commit `bc86398` is an ancestor of both, and nothing under
`marketplace/` or `test/` changed between them — verified with `git merge-base --is-ancestor bc86398 HEAD`
and `git status --porcelain -- marketplace/ test/` returning empty.)
**Adversarial re-verification:** opened at `a90adeb` and closed at `c5511dd`, still on the same
branch (HEAD advanced again mid-review as sibling agents committed). `bc86398` remains an ancestor
throughout, and `_architecture_core.py`'s md5 is unchanged at `bc7406029e7f408e633fadf99215c04d` —
the same digest this audit recorded — so every code citation below was re-checked against the same
bytes the original audit read. The md5, not the HEAD sha, is the anchor that matters here.
**Overall verdict:** PARTIALLY REFUTED

Two of the four deliverables carry a *Done when* clause that the shipped tree demonstrably does not
satisfy:

- **D1** — "every persisted key resolves to a path" is false. The dotted→path migration is
  read-only and lives in one merge path; both writers re-persist legacy dotted keys verbatim.
- **D4** — "a document generated against a different tree is reported stale" is false on the shipped
  read surface. `architecture info` derives the verdict from a denormalized index snapshot rather
  than from the concept document's own header, and reports `fresh` both for a document written
  against a different tree and for a module that has no concept document at all.

D2 is fully confirmed and its guards are non-vacuous under mutation. D3 is confirmed, including its
negative control.

Separately, and not affecting any deliverable verdict: the run's beyond-diff documentation sweep is
incomplete in both directions the plan changed vocabulary. Twelve shipped files still teach
either the retired dotted identity (D1) or the retired index-as-gatekeeper semantic (D3) — the
latter against the plan's only ⛔ **MUST NOT**, and against a PR-body claim that the correction was
made "across every document that restated it". See § Beyond-diff documentation sweep.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | Path is identity for `key_packages`; migrate existing; refuse non-resolving at write | "keys are now repo-relative paths"; write gate + named error; "read migration … never silently dropped" | Write gate and named error present and correct. Migration exists only in `merge_module_data`; nothing writes migrated keys back, one consumer skips the migration entirely, and the migration itself can silently collide two keys onto one path | **PARTIAL** |
| D2 | Required, closed, validated `type`; unknown refused naming the accepted set | `CONCEPT_TYPES` declared once; refused at write and read; absent → `module` | Exactly as claimed; all three migration states covered; guards proven non-vacuous by mutation | **CONFIRMED** |
| D3 | Root index carries per-module descriptions, not a discovery gatekeeper | `api_discover` builds `{name: {description, generation}}`; `iter_modules` unchanged | Index entries carry `description`; discovery still crawls the filesystem; negative control proven non-vacuous. Caveat: the description is refreshed only at `discover`, never by an enrich write | **CONFIRMED** |
| D4 | Generation provenance; staleness from tree id, not mtime; readable without the body | `generation = {by, tree_sha}` on every write; `derive_freshness` → fresh/stale/unknown; mirrored into the index so `info` surfaces it body-free | The primitive is correct in isolation. The *shipped read surface* reads the index snapshot, not the document, and returns `fresh` for a document written against a different tree and for an absent document. Legacy documents never gain a `generation` header. "At what point" is not recorded at all | **PARTIAL** (one Done-when clause refuted) |

## Per-deliverable detail

### D1 — path is identity

- **Required (plan):** "every persisted key resolves to a path, and a write with a non-resolving key
  is refused with a named error rather than accepted." The deliverable body also says "**Migrate
  existing entries.**"
- **Claimed (report):** write gate `enrich_package` → `validate_package_key` →
  `NonResolvingPathKeyError`, CLI `error: non_resolving_package_key`, `--package` switched to
  `validate_relative_path`; read migration via `merge_module_data` → `migrate_key_packages`;
  unresolved keys → non-blocking WARNING, "never silently dropped".

**Found — the confirmed half:**

- `_architecture_core.py:397` `validate_package_key` raises `NonResolvingPathKeyError`
  (`_architecture_core.py:129`), message at `:406-409` naming the rule.
- `_cmd_enrich.py:138` calls it before any write; `_cmd_enrich.py:617-618` maps it to
  `{'status': 'error', 'error': 'non_resolving_package_key'}`.
- `architecture.py:377` `type=validate_relative_path` (was `validate_package_name`), help text at
  `:378` states path identity.
- `_architecture_core.py:366-394` `package_key_resolves` refuses empty, leading-`/`, `..`
  components, and — via the containment check at `:392` — drive-letter keys and symlinks resolving
  out of tree.
- `_architecture_core.py:413-443` `migrate_key_packages` rewrites dotted keys through the derived
  `packages` bridge and returns an `unresolved` list; `_architecture_core.py:919-926` applies it in
  `merge_module_data` and logs unresolved keys.
- The derived `packages[*].path` really is repo-relative:
  `script-shared/scripts/extension/_build_discover.py:470-472` prefixes `relative_path` (the
  module's path from the project root) onto the package's module-relative path. Report finding #5's
  correction is therefore right.

**Found — the refuted half.** Probe (`enrich_module` on a document holding a legacy dotted key,
run with the project venv):

```
PERSISTED responsibility  : NEW RESPONSIBILITY
PERSISTED key_packages    : ['com.example.pkg']
merged key_packages       : ['mod/src/pkg']
```

The merged (in-memory) view is migrated; the **persisted document is not**. A second probe through
`api_discover(force=True)` on a legacy document gives the same result:

```
after discover — type        : module
after discover — key_packages: ['com.example.pkg']
```

Note the asymmetry that makes this a clean defect rather than a design choice: `type` **is**
back-filled to disk, because `migrate_concept_document` runs inside `load_module_enriched_or_empty`
which `api_discover` uses. `key_packages` is not, because its migration lives only in
`merge_module_data`, which no writer calls. So the store permanently keeps the second identity
system the deliverable exists to retire.

Three further defects in the same area, each proven:

| Input | Result | Why it matters |
|---|---|---|
| `migrate_key_packages({'com.gone': …}, {'com.gone': {'path': 'no/such/dir'}})` | `{'no/such/dir': …}`, `unresolved == []` | Migrates to a key that does not resolve, and reports success |
| `migrate_key_packages({'a.b': {'v':1}, 'c.d': {'v':2}}, {'a.b': {'path':'pkg'}, 'c.d': {'path':'pkg'}})` | `{'pkg': {'v': 2}}`, `unresolved == []` | `a.b`'s curated description is **silently discarded** — the exact "silent drop" the design forbids, arriving through the collision path instead of the unresolved path |
| `package_key_resolves('.', root)` and `package_key_resolves('./', root)` | `True` | The repository root itself validates as a "package" key |

And one consumer bypasses the migration entirely:
`manage-solution-outline/scripts/manage-solution-outline.py:918,929-930` reads
`load_module_enriched_or_empty(...)` and publishes `list(enriched['key_packages'].keys())` with no
migration, so `phase-3-outline` receives dotted keys.

- **Verdict:** **PARTIAL** — the write gate is correct and well tested; "every persisted key
  resolves to a path" and "migrate existing entries" are not delivered.

### D2 — a required, closed, validated `type`

- **Required (plan):** "the vocabulary is enumerated in one place, an unknown type is refused, and
  the refusal names the accepted set." Plus the claim-label requirement that an absent type produce a
  *deterministic, named* outcome and never a silent default.
- **Claimed (report):** `CONCEPT_TYPES` declared once; refused at write
  (`save_module_enriched`→`migrate_concept_document`→`validate_concept_type`) and read
  (`load_module_enriched`); absent → migrate-on-read to `module`.
- **Found:**
  - `_architecture_core.py:209-217` — `CONCEPT_TYPES` frozenset, single declaration.
  - `_architecture_core.py:238-252` — `validate_concept_type`; the message at `:250` interpolates
    `sorted(CONCEPT_TYPES)`, so the refusal cannot drift from the set.
  - `_architecture_core.py:255-277` — `migrate_concept_document`; absent → `LEGACY_CONCEPT_TYPE`
    (`:223`, named constant with a documented rationale), present → validated, unknown → raises.
    Returns a copy (`:271`), so no caller mutation.
  - `_architecture_core.py:762` (write) and `:726`/`:740` (read) both route through it.
  - Back-fill to disk confirmed by probe: a legacy document acquires `type: module` on disk after
    `api_discover`.
- **Checks run:** mutated `if concept_type not in CONCEPT_TYPES:` → `if False and …`;
  `test_concept_model.py` went from 29 passed to **4 failed, 25 passed**
  (`test_save_refuses_unknown_type`, `test_load_refuses_unknown_type_document`,
  `test_migrate_concept_document_three_states`, `test_refusal_message_names_the_accepted_set`).
  File restored from a byte snapshot; md5 `bc74060…` matches the original and
  `git status --porcelain` is clean for it.
- **Verdict:** **CONFIRMED.**
- **Noted, not a failure:** no CLI verb can set a type other than `module`, so the four extra
  vocabulary members (`skill`, `script`, `standard`, `decision_record`) are reachable only through
  the Python API. The Done-when does not require a writer, so this is a limitation rather than a gap
  — recorded in `gaps.md` at low severity because the deliverable's stated purpose ("so the store can
  hold more than modules") is not yet exercisable.

### D3 — the root index carries per-module descriptions

- **Required (plan):** "the index carries descriptions and a module present on disk but absent from
  the index is still discovered." With the ⛔ constraint that descriptions are a read-side
  enrichment, never a discovery-side filter.
- **Claimed (report):** `api_discover` builds `modules` as `{name: {description, generation}}`
  mirroring `responsibility` + generation; `iter_modules` unchanged; negative control test present.
- **Found:**
  - `_cmd_manage.py:683-686` — the index entry is exactly
    `{'description': document.get('responsibility',''), 'generation': document.get('generation', {})}`.
  - `_architecture_core.py:768-779` — `iter_modules` returns
    `sorted(crawl_all_modules(project_dir).keys())`; no index read. The gatekeeper semantics the plan
    called "OBSERVED, and load-bearing" survive.
  - `_architecture_core.py:463-469` and `tools-file-ops/scripts/constants.py:415-422` — both
    docstring/comment surfaces that formerly asserted the index was the source of truth now say the
    opposite (report findings #1 and #4, confirmed fixed).
- **Checks run:** mutated `iter_modules` to
  `sorted((load_project_meta(project_dir).get('modules') or {}).keys())`;
  `test_module_on_disk_absent_from_index_is_still_discovered` went red
  (`assert 'orphan' in []`). The negative control is real.
- **Verdict:** **CONFIRMED.**
- **Caveat carried into `gaps.md`:** no enrich verb refreshes the index. Probe: after
  `enrich_module('mod', 'NEW RESPONSIBILITY')`, the document holds `NEW RESPONSIBILITY` while the
  index still holds `{'description': 'OLD DESC', 'generation': {'by': 'architecture',
  'tree_sha': 'TREE-OLD'}}`. `architecture-persistence.md:86,96-97` does disclose the index as a
  "denormalized pre-flight snapshot … refreshed at `discover` time", so this is documented — but it
  means the surface a consumer is told to use "to decide which concept documents to open" reports
  the description the module had at the last `discover`, not the one it has now.

### D4 — generation provenance and freshness

- **Required (plan):** "Every concept document records who generated it, at what point, and against
  which tree; reads surface a staleness verdict derived from the tree identifier rather than from
  mtime." *Done when:* "a document generated against a different tree is reported stale, one
  generated against the current tree is not, and neither check reads the body."
- **Claimed (report):** `save_module_enriched` stamps `generation = {by, tree_sha}` on every write;
  `derive_freshness` → fresh/stale/unknown from the tree identifier; "mirrored into the index so
  `info` surfaces per-module `description` + `freshness` without reading any concept body."
- **Found — correct in isolation:**
  - `_architecture_core.py:335-344` `build_generation` → `{by, tree_sha}` via
    `current_worktree_sha` → the shared `script-shared/scripts/worktree_sha.compute_worktree_sha`
    (`:280-302`), not mtime. The plan's ⭐ preference for a tree identifier is honoured.
  - `_architecture_core.py:347-363` `derive_freshness` reads only `generation['tree_sha']`; absent
    on either side → `unknown`, never `fresh`.
  - `_architecture_core.py:763` stamps the header on every `save_module_enriched` call.
  - Mutation check: `return FRESHNESS_UNKNOWN` → `return FRESHNESS_FRESH` turned
    `test_derive_freshness_unknown_when_sha_absent` red. The fail-closed branch is non-vacuous.
- **Found — the refuted clause.** `_cmd_client_query.py:209` computes the verdict from
  `index_entry.get(GENERATION_FIELD)` — the **index snapshot**, not the document. Two probes on the
  shipped `get_project_info`:

  ```
  CASE A  enriched.json exists: False | info freshness: fresh | description: Does things
  CASE B  document tree_sha: TREE-B | current: TREE-A | info freshness: fresh
          | document-derived verdict: stale
  ```

  CASE B is a direct counterexample to the Done-when: a document generated against a different tree
  is reported **fresh**. CASE A reports `fresh` for a concept document that does not exist. Both are
  fail-*open* on a guard whose whole purpose is to let a consumer skip stale documents. The
  divergence is reachable in normal operation because the index is written only by `api_discover`
  while the document is rewritten by every enrich verb (see D3's caveat) — the two headers separate
  on the first enrich after a discover, and any return of the working tree to an earlier state then
  produces CASE B.
- **Found — the incomplete clause.** Probe through `api_discover` on a legacy document:
  `after discover — generation: <ABSENT>`, `index entry: {'description': 'Legacy R', 'generation': {}}`.
  `_cmd_manage.py:672-677` preserves an existing document verbatim and stamps `build_generation`
  **only** on the first-seen branch, then writes it with a raw `_write_json` at `:717` rather than
  through `save_module_enriched`. A pre-field document therefore never acquires provenance and stays
  permanently `unknown`. The preservation is deliberate and documented (`:663-668` — do not falsely
  restamp preserved content), but the consequence — no back-fill path at all — is undisclosed, and
  it makes "every concept document records who generated it … and against which tree" false for the
  entire pre-existing store.
- **Found — the unrecorded clause.** "at what point" is not recorded. `build_generation` returns
  exactly `{by, tree_sha}`, and `test_build_generation_shape`
  (`test_concept_model.py:190`) asserts `set(generation) == {'by', 'tree_sha'}`, actively locking the
  omission in. The plan's ⭐ note argues the tree identifier beats a wall-clock *expiry*, which
  justifies not deriving the verdict from a timestamp — it does not remove the requirement to record
  when. Neither the report nor the PR body discloses the omission.
- **Found — the unrealized purpose.** D4's ⛔ constraint is that the signal "must be readable
  without parsing the concept body, so a consumer can filter before loading". The *primitive*
  satisfies this: `derive_freshness` touches only `generation['tree_sha']`, and
  `test_freshness_verdict_derived_from_header_alone` (`test_concept_model.py:212-221`) exercises it
  with no `enriched.json` on disk. But the only shipped consumer of the verdict —
  `get_project_info` — loads **every** module's concept body at `_cmd_client_query.py:200`
  (`load_module_enriched_or_empty`, for the `purpose` column) before it builds the row, and
  `cmd_info` (`_cmd_client_handlers.py:92-96`) passes that dict straight to the CLI. So "filter
  before loading" is not realized anywhere the freshness column is actually surfaced. This does not
  refute the Done-when (which is scoped to "neither check reads the body", and neither check does)
  and it is not carried as its own gap, because G1's fix subsumes it — but it is why G1's fix costs
  nothing: the body is already in hand at the point the wrong verdict is computed.
- **Verdict:** **PARTIAL** — the primitive is right and body-free as required; the shipped read
  surface inverts one Done-when clause, and two sub-clauses of the deliverable body are unmet.

## Correctness review

Read in full: `_architecture_core.py` concept-model block (`:100-133`, `:186-444`), load/save
(`:451-500`, `:700-780`), `merge_module_data` (`:882-932`); `_cmd_manage.py:517-541`, `:640-796`;
`_cmd_enrich.py:1-175`, `:300-372`, `:608-623`; `_cmd_client_query.py:167-223`, `:567-598`;
`_cmd_client_handlers.py:92-100` (`cmd_info`) and `:253-280` (`cmd_module`); `architecture.py:365-384`;
`tools-input-validation/scripts/input_validation.py:197-217`;
`script-shared/scripts/extension/_build_discover.py:403-495`.

Defects found, each with the failing input and the consequence:

1. **Fail-open freshness on a diverged index — `_cmd_client_query.py:209`.**
   Input: index `generation.tree_sha == current`, document `generation.tree_sha != current`.
   Result: `freshness: fresh`. Consequence: a consumer told to filter on this column loads a stale
   document believing it current. Proven (CASE B above).
2. **Fail-open freshness on a missing document — `_cmd_client_query.py:209` + `:202`.**
   Input: index entry present with a matching `tree_sha`, `enriched.json` absent.
   Result: `freshness: fresh` and a non-empty `description` for a document that does not exist.
   Proven (CASE A above).
3. **Silent data loss in migration — `_architecture_core.py:436-439`.**
   Input: two dotted keys whose derived entries carry the same `path`. Result: the later value
   overwrites the earlier one, `unresolved` stays empty. Consequence: a curated package description
   disappears from every merged read with no signal, in a function whose contract is "never a silent
   drop".
4. **Migration can produce a non-resolving key — `_architecture_core.py:437-439`.**
   The bridge path is written straight into `migrated` with no `package_key_resolves` check, so a
   deleted package directory yields a key that fails the very invariant D1 asserts, reported as a
   successful migration.
5. **Root accepted as a package key — `_architecture_core.py:392`.**
   `candidate == root` is allowed, so `.` and `./` validate. `enrich package --package .` would key
   a description to the whole repository.
6. **No provenance back-fill; second writer bypasses the accessor — `_cmd_manage.py:672-677,717`.**
   A preserved legacy document is written by a raw `_write_json`, not `save_module_enriched`, and
   keeps no `generation`. This is also the answer to the plan's explicit HYPOTHESIS "the named
   save/load accessors are the only writers" — they are **not**; the run did not report the second
   writer.
7. **Migration never reaches disk — `_architecture_core.py:919-926` is the only call site.**
   Detailed under D1.
8. **Unmigrated consumer — `manage-solution-outline.py:929-930`.** Detailed under D1.

Checked and found **correct** (no defect): the containment check in `package_key_resolves`
(drive-letter and symlink escapes both refused — the `be98185` fix is real and effective);
`derive_freshness`'s `not isinstance(generation, dict)` and empty-sha guards; the copy-not-mutate
contract of `migrate_concept_document`; `_WORKTREE_SHA_CACHE` invalidation
(`invalidate_crawl_cache`, `_architecture_core.py:519-522`, drops the sha memo wholesale, so a refresh cannot mis-report
freshness from a stale sha); the fail-closed propagation of `InvalidConceptTypeError` out of
`api_discover` before the atomic swap, so one bad document cannot leave a half-migrated store.

## Test adequacy

`test/plan-marshall/manage-architecture/test_concept_model.py` — 29 tests, all passing
(`.venv/bin/python -m pytest … -o addopts="" -q` → `29 passed in 0.50s`). Whole skill directory:
`573 passed in 30.48s`.

| Deliverable | Covering tests | Adequacy |
|---|---|---|
| D1 | `test_enrich_package_refuses_non_resolving_key`, `…accepts_resolving_path_key`, `test_cmd_enrich_package_returns_named_error_for_non_resolving_key`, `test_package_key_resolves_rejects_absolute_and_traversal`, `test_package_key_resolves_refuses_target_escaping_root`, `test_validate_package_key_returns_key_when_resolving`, `test_migrate_key_packages_rewrites_dotted_to_path`, `…reports_unresolved_without_dropping`, `test_merge_module_data_migrates_dotted_key_packages` | Write gate well covered. **No test asserts the persisted key after a write**, which is why the on-disk gap survived. No collision test, no "bridge path does not exist" test |
| D2 | `test_empty_stub_carries_module_type`, `test_save_stamps_module_type_when_absent`, `test_save_refuses_unknown_type`, `test_load_migrates_pre_field_document`, `test_load_of_migrated_document_keeps_its_type`, `test_load_refuses_unknown_type_document`, `test_migrate_concept_document_three_states`, `…does_not_mutate_caller`, `test_vocabulary_is_closed_and_enumerated_once`, `test_refusal_message_names_the_accepted_set` | Complete; all three plan-mandated migration states present |
| D3 | `test_discover_index_carries_description_and_generation`, `…defaults_empty_for_fresh_module`, `test_module_on_disk_absent_from_index_is_still_discovered` | Negative control present and real. No test on index/document divergence after an enrich write |
| D4 | `test_save_stamps_generation_header`, `test_build_generation_shape`, `test_derive_freshness_{fresh,stale,unknown}…`, `test_freshness_verdict_derived_from_header_alone`, `test_info_surfaces_freshness_from_index` | The primitive is well covered. **Every `info` test seeds index and document consistently**, so no test can observe the fail-open — `test_info_surfaces_freshness_from_index` writes no `enriched.json` at all and asserts `fresh`, i.e. it *encodes* defect 2 as expected behaviour rather than catching it |

**Mutation evidence — guards proven non-vacuous** (byte snapshot taken to
`$TMPDIR/…/verify-150-mutsweep/_architecture_core.py.orig`, md5 `bc7406029e7f408e633fadf99215c04d`;
restored by copying the snapshot back, md5 re-verified, `git status --porcelain` clean for the file):

| Mutation | Result |
|---|---|
| `if candidate != root and root not in candidate.parents:` → `if False:` | `test_package_key_resolves_refuses_target_escaping_root` **red** |
| `return FRESHNESS_UNKNOWN` → `return FRESHNESS_FRESH` in `derive_freshness` | `test_derive_freshness_unknown_when_sha_absent` **red** |
| `if concept_type not in CONCEPT_TYPES:` → `if False and …` | 4 tests **red** |
| `iter_modules` → read the index instead of crawling | `test_module_on_disk_absent_from_index_is_still_discovered` **red** |

No vacuous test was found among the guards that exist. The test weakness is **coverage of the
untested paths** — persisted-key state, index/document divergence, and the legacy-no-generation
document — not tautology in the tests that were written. One test is worse than absent:
`test_info_surfaces_freshness_from_index` pins the fail-open behaviour as correct.

Uncovered paths warranting a test: `_log_unresolved_package_keys` is never asserted to fire from
`merge_module_data`, and its body is wrapped in `except Exception: pass`
(`_architecture_core.py:895-896`), so the "never silently dropped" guarantee reduces to a log line
that can itself be silently dropped with nothing observing it.

## Report accuracy

Verified claim-by-claim against the tree now. Claims that **held**: the D1 write-gate mechanics and
the `validate_package_name` → `validate_relative_path` switch; `CONCEPT_TYPES` declared once and
refused at write and read; `api_discover` building `{description, generation}`; `iter_modules`
unchanged; `save_module_enriched` stamping `{by, tree_sha}` via the shared `compute_worktree_sha`;
every test name the report cites exists and passes; the out-of-scope list (reasoning-field family,
markdown/frontmatter, leniency, existence-marker, new content) is genuinely untouched by the diff.

Claims that are **false, stale, or overstated**:

1. > "`key_packages` keys **are now** repo-relative paths."

   True of new writes; false of the store. Persisted legacy keys are never rewritten — proven by
   probe. The accurate statement is "new keys must be paths; legacy keys are rewritten only in the
   merged read view."

2. > "unresolved keys → non-blocking WARNING, **never silently dropped**."

   Overstated. Two silent-loss paths exist that never reach the `unresolved` list: a collision
   between two dotted keys mapping to the same path (the earlier value is discarded), and a bridge
   path that no longer exists (migrated as if valid). Both proven above.

3. > "mirrored into the index so `info` surfaces per-module `description` + `freshness`"

   True only in the window immediately after `discover`. No enrich verb refreshes the index, so both
   fields describe the last `discover`, not the current document. The freshness column is therefore
   a verdict on the snapshot, not on the document — and returns `fresh` for a document written
   against a different tree, which is the inverse of what D4 requires.

4. > Finding #4 — "the two borderline items (`manage-api.md`, module docstring) tightened in the
   > same commit"

   Partially false. `git show bc86398 -- …/manage-api.md` shows a single hunk (the "Data Sources"
   paragraph). The `enrich package` option table at `manage-api.md:258` still reads
   `| --package | Yes | - | Full package name |`, and the worked example at `:265` still emits
   `package	de.cuioss.sheriff.oauth.core.pipeline` — two shipped, now-false instructions on the
   surface the plan committed to moving in lock-step.

5. > "Step 6 Verification sub-agent … all four deliverables PASS"

   Not sustainable against the tree. D1's "every persisted key resolves to a path" and D4's "a
   document generated against a different tree is reported stale" both have demonstrated
   counterexamples reachable through the shipped CLI surface.

6. > "Implementation commit: `7219569` … Follow-up fix: `be98185`" (also `f4937d2`, `f4fef2e`)

   None of these object names exist in the repository — `git cat-file -t` returns
   `fatal: Not a valid object name` for each. The PR squash-merged as `bc86398`. Not a substantive
   defect (the SHAs were real on the branch), but the report is not self-checkable as written.

7. > "Affected manage-architecture tests re-run after each fix: green (109 after the path-boundary
   > fix)"

   **UNVERIFIABLE.** The count's population is not defined, and the directory now holds 573 tests
   after subsequent plans landed. Not asserted false — simply not re-derivable.

8. > "Whole-tree 19531 passed, 14 skipped, 0 failed"

   **UNVERIFIABLE by design** — the brief excludes running the full suite, and the tree has advanced
   many plans past this one.

9. > PR body for `bc86398`: "`architecture-persistence.md`, `SKILL.md`, `client-api.md`,
   > `manage-api.md`, and the `FILE_PROJECT_META` comment move in lock-step — including correcting
   > the now-false 'the index is the source of truth for which modules exist' claim **across every
   > document that restated it**."

   **False**, and it is the most consequential false claim in either surface. Nine shipped files
   still restate it — seven of them inside the `plan-marshall` bundle the run's own Step-6
   instruction tells it to sweep, two in `pm-plugin-development`. Enumerated and itemised in `gaps.md` at G18–G20; see
   § Beyond-diff documentation sweep below.

The report is also **silent on three things it should have disclosed**: the second concept-document
writer (`_cmd_manage.py:717`) that the plan explicitly asked to be enumerated; the absence of any
provenance back-fill for pre-field documents; and the fact that "at what point" from D4's own text
was not implemented.

## Beyond-diff documentation sweep

The run's Step-6 instruction is to "sweep beyond the diff across the owning bundle", and the
report's own "What have we learned" section names the incomplete first-pass sweep as the run's one
execution weakness — resolved, it says, by the re-dispatch loop. It was not resolved. Two families
of retired vocabulary survive in shipped documentation, and each is a family the plan's own claim
labels marked load-bearing.

**Family 1 — the retired dotted identity (D1).** Surfaces still teaching `key_packages` keys as
dotted package names, against `architecture-persistence.md:338,387` and the shipped validator
`architecture.py:377-378`:

| Location | Defect | Gap |
|---|---|---|
| `manage-architecture/standards/manage-api.md:258` | `--package` described as "Full package name" | G11 |
| `manage-architecture/standards/manage-api.md:265` | `enrich package` example output emits a dotted name — the form now **refused** | G11 |
| `phase-3-outline/standards/module-selection.md:22-28` | `key_package Pattern` table taught entirely in dotted form | G12 |
| `phase-3-outline/templates/package-selection.md:26` | "Package name from key_packages" | G13 |

**Family 2 — the retired index-gatekeeper semantic (D3).** Surfaces still asserting the index is
the source of truth for which modules exist, or authoritative over the filesystem — against
`_architecture_core.py:463-469`, `tools-file-ops/scripts/constants.py:415-422`,
`architecture-persistence.md:96-97`, and the non-vacuous negative control
`test_module_on_disk_absent_from_index_is_still_discovered` (`test_concept_model.py:304-319`):

| Location | Defect | Gap |
|---|---|---|
| `marshall-steward/references/architecture-setup.md:40` | Normative: orphan module dirs "**MUST be ignored** — the index is authoritative, not the filesystem" | G18 |
| `marshall-steward/references/menu-maintenance.md:144` | "source of truth for which modules exist" | G18 |
| `marshall-steward/references/menu-configuration.md:685` | "the source of truth for the module index" | G18 |
| `marshall-steward/references/wizard-flow.md:245` | "which is the source of truth" | G18 |
| `marshall-steward/scripts/determine_mode.py:213-224` | Docstring framing only — the function's index-driven existence check is itself correct | G18 |
| `extension-api/standards/module-discovery.md:23,26` | "(source of truth)" + "Orphan `<module>/` subdirectories … are ignored" | G18 |
| `manage-solution-outline/scripts/manage-solution-outline.py:874-876` | Attributes the claim to `_architecture_core` **by name**, and its own `:890` calls `iter_modules` | G20 |
| `pm-plugin-development/skills/plan-marshall-plugin/SKILL.md:38-43` + `scripts/plugin_discover.py:7-8` | "the index is authoritative, not the filesystem" — cross-bundle | G19 |

None of these files appears in `git show --stat bc86398`'s 17-file list. Family 2 matters more than
Family 1: D3 carries the plan's only ⛔ **MUST NOT** ("This MUST NOT reintroduce the index as the
discovery gatekeeper"), and the plan labels the crawl-fallback semantic "**OBSERVED, and
load-bearing**". The code defends it correctly and the negative control is real — but the
documentation an agent reads before running `architecture discover` still instructs the inverse,
and one instance does so in **MUST** form.

This is a documentation shortfall, not a behaviour regression: no verdict above changes. It is
recorded here because the PR body affirmatively claimed the sweep was complete.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| "The landing itself is delegated to auto-merge + the merge queue … If the queue rejects on a `merge_group` verify failure, that becomes a drive-to-green follow-up" | **Closed** | `bc86398` is on the branch's history and is an ancestor of HEAD (`git merge-base --is-ancestor bc86398 HEAD` succeeds); the squash commit's subject carries `(#1216)`. The queue accepted it |
| "`coderabbitai` and `sourcery-ai` did not review this diff (both rate-limited); a re-review could be requested when their windows reopen, but the merge is not held on it" | **Moot** | The PR merged; a re-review of a merged diff has no landing effect. Worth noting only that two of the three reviewer surfaces never inspected this change, which is consistent with the defects that reached `main` |

Undeclared residue the run should have recorded, now open: the on-disk `key_packages` migration, the
provenance back-fill, and the index/document divergence — all itemised in `gaps.md`.

## Out-of-scope and collateral

The plan's five exclusions were respected. Verified against the commit's file list
(`git show --stat bc86398`, 17 files) and by reading the diff:

- **Reasoning-field family** — untouched; no `*_reasoning` field's semantics changed.
- **Markdown/frontmatter serialization** — the store is still JSON (`_write_json`,
  `_architecture_core.py:457-460`); no parser added.
- **Leniency for broken links / unknown types** — the opposite shipped: unknown is refused at write
  *and* read.
- **The per-module existence-marker question** — no marker file introduced; the crawl fallback is
  unchanged.
- **Writing new content into the store** — only the model fields (`type`, `generation`, index
  `description`) are written; no resolver content.

Collateral beyond the plan's declared "Expected surface", all of it disclosed in the report or the
PR body: `tools-file-ops/scripts/constants.py` (the `FILE_PROJECT_META` comment, a cross-bundle
edit), `standards/manage-api.md`, `standards/client-api.md`, `SKILL.md`, and migrations of three
pre-existing test files. `_cmd_client_handlers.py`, named as a HYPOTHESIS surface, was not touched —
correctly, since the handler passes the merged dict straight through.

**Undisclosed collateral: none found.** No file changed in `bc86398` lies outside the plan's scope
or the report's account of it. The defect in this area is the inverse — files that should have
changed and did not; see § Beyond-diff documentation sweep.

## Method and coverage

**What I did.**

- Read the epic README, `plan.md`, and `report-01.md` end to end before touching the tree.
- Located the landed change (`bc86398`, squash of PR #1216) and read its full diff and file list.
- Read every production file the change touched, plus the call graph around it: all writers of
  `enriched.json` (`save_module_enriched` and the raw `_write_json` in `api_discover`), all readers
  of `key_packages` across `marketplace/bundles/`, the CLI arg validators, and the derived-`packages`
  producer in `script-shared` that the migration bridge depends on.
- Enumerated writers and readers with `Grep` over the whole bundle tree, not just the changed skill.
  Every "nothing found" was cross-checked against a pattern known to hit (e.g. searching
  `key_packages` returned 30+ hits across five bundles before I concluded which of them lacked the
  migration).
- Executed the shipped code in five probes against temporary projects using the project venv
  (`/home/user/plan-marshall/.venv/bin/python`) and the test tree's `conftest.load_script_module`
  loader, covering: enrich-then-inspect-disk, index/document divergence, freshness on a missing
  document, freshness on a diverged tree sha, legacy document through `api_discover`, and
  `package_key_resolves`/`migrate_key_packages` edge inputs.
- Ran `test_concept_model.py` (29 passed) and the whole `manage-architecture` test directory
  (573 passed).
- Mutation-tested four guards, restoring from a byte snapshot each time and re-verifying md5 and
  `git status`.

**What I could not check, and why.**

- **The live persisted store.** It lives under the git-ignored `.plan/` tree and is absent from this
  clone — exactly as the plan's claim-label table states. Every store-shape verdict above is derived
  from the writers and from fixtures I constructed, never from production data. Whether any *actual*
  production document today carries a dotted key or lacks a `generation` header is **UNVERIFIABLE**
  from here; what is verified is that the code permits and re-persists both.
- **The report's whole-tree suite count (19531) and quality-gate figures.** The brief excludes
  running `./pw verify`, and the tree has advanced many plans since. **UNVERIFIABLE**, not disputed.
- **The report's "109 affected tests" figure.** Population undefined. **UNVERIFIABLE.**
- **Reviewer participation claims** (bot verdicts, rate limits). These concern PR-time state on
  GitHub, not the tree. Not checked.
- **Windows behaviour of `package_key_resolves`.** The drive-letter path is reasoned about from the
  code and covered indirectly by the symlink-escape test on POSIX; the actual Windows
  `Path.__truediv__` behaviour was not executed. The containment check is correct on the reasoning,
  but the platform-specific claim is **UNVERIFIABLE** on this host.

**Environment note.** This audit ran concurrently with sibling verification agents on the same
working tree and branch. During the run I observed a transient modification to
`marketplace/bundles/pm-code-intelligence/skills/plan-marshall-plugin/extension.py`
(a `if False and …` mutation, since reverted by its owner) that was **not mine**; I left it alone.
HEAD advanced from `61a43e5` to `8ae4805` for the same reason. Neither affected anything under
`manage-architecture`, and `git status --porcelain -- marketplace/ test/` is empty at the close of
this audit, confirming all four of my mutations were restored.

## Adversarial review

Independent review of this document and `gaps.md`. Attacks run: A1 false positives, A2 false
negatives, A3 vacuous evidence, A4 counts and quotes, A5 actionability, A6 severity/topic,
A7 coverage, A8 internal consistency.

Reviewed across `a90adeb`…`c5511dd`, with `_architecture_core.py` at md5
`bc7406029e7f408e633fadf99215c04d` throughout — byte-identical to what this audit read, so no
finding below turns on tree drift. Concurrent agents held unstaged edits to unrelated files in the
same tree for the whole review; none touched `manage-architecture`, and my own mutated file is
absent from `git status --porcelain -- marketplace/ test/` at close.

| # | Attack | What was found | Correction applied |
|---|---|---|---|
| A1 | False positives — the two HIGH gaps | **None. Both reproduce exactly.** I rebuilt the D4 probes from scratch against the shipped `get_project_info` (not the audit's script) and got, verbatim: `CASE A enriched.json on disk: False \| info freshness: fresh \| description: 'Does things'` and `CASE B document tree_sha: TREE-B \| current: TREE-A \| info freshness: fresh \| document-derived verdict: stale`. G1 and G2 stand as written | None needed |
| A1 | False positives — the remaining gaps | **None substantive.** Independently reproduced G3 (`PERSISTED key_packages: ['com.example.pkg']` vs `merged: ['mod/src/pkg']`), G5 (`({'pkg': {'v': 2}}, [])`), G6 (index still `{'description': 'OLD DESC', 'generation': {…'TREE-OLD'}}` after an enrich), G7 (`after discover — generation: <ABSENT>`, index `{'description': 'Legacy R', 'generation': {}}`), G9 (`({'no/such/dir': …}, [])` with `package_key_resolves` False), G10 (`.` and `./` both `True`). Every quoted probe line matches the shipped code's actual output | None needed |
| A1 | Stale citations | **Six off-by-N citations found**, all in doc surfaces rather than code: `manage-api.md:257`→**258**; `SKILL.md:576`→**577**; `client-api.md:343,391`→**344,392**; `module-selection.md:20-27`→**22-28**; `constants.py:411-419`→**415-422**; `invalidate_crawl_cache:519-521`→**519-522**. Every `_architecture_core.py`, `_cmd_manage.py`, `_cmd_enrich.py`, `_cmd_client_query.py`, `architecture.py`, and `manage-solution-outline.py` line citation was checked and is **exact** | All six corrected in place |
| A2 | False negatives — the CONFIRMED deliverables | Read D2's and D3's shipped code directly rather than the audit's reasoning. **D2 is clean**: `migrate_concept_document` (`:255-277`) has no fail-open branch — absent → named `LEGACY_CONCEPT_TYPE`, present → `validate_concept_type`, which refuses non-strings too. **D3 is clean**: `iter_modules` reads no index. Both CONFIRMED verdicts survive | None needed |
| A2 | False negatives — the missed sweep | **One substantive miss, the most consequential finding of this review.** The PR body claims the run corrected the "index is the source of truth for which modules exist" claim "**across every document that restated it**". It did not: nine shipped files still restate it, seven inside the `plan-marshall` bundle, and `marshall-steward/references/architecture-setup.md:40` does so **normatively** ("orphan module dirs **MUST be ignored** — the index is authoritative, not the filesystem"), instructing the exact inverse of D3's only ⛔ MUST NOT. The audit verified the two surfaces the *report* named as fixed and never asked whether others remained | Added § Beyond-diff documentation sweep to this document; added **G18**, **G19**, **G20** to `gaps.md`; added report-accuracy item **#9** |
| A2 | False negatives — an unrealized purpose | D4's "filter before loading" is satisfied by the *primitive* but not by the *only shipped consumer*: `get_project_info` loads every concept body at `_cmd_client_query.py:200` before computing the row, and `cmd_info` (`_cmd_client_handlers.py:92-96`) passes it straight to the CLI. Does not refute the Done-when (scoped to "neither check reads the body") and needs no new gap — G1's fix subsumes it | Recorded under § D4 as "the unrealized purpose" |
| A2 | False negatives — extra `manage-api.md` instance | G11 named the option table but not the `enrich package` **worked example** at `:265`, which prints `package\tde.cuioss.sheriff.oauth.core.pipeline` — the form the shipped write gate now refuses. Checked the rest of the file: the derived `packages` block at `:162-165` legitimately keeps dotted names (it *is* the bridge) and is **not** a defect | G11 extended to `:258` **and** `:265`, with the false-positive risk at `:162-165` called out |
| A3 | Vacuous evidence — mutation sweep | **Re-ran all four mutations myself** against a byte snapshot in `$TMPDIR/adv-150-mutsweep/`, restoring by copying the snapshot back (never `git checkout`/`restore`/`stash`) and re-verifying md5 after each. Results reproduce **exactly**, including the audit's stated counts and the verbatim failure text: containment→`test_package_key_resolves_refuses_target_escaping_root` red; `FRESHNESS_UNKNOWN`→`FRESHNESS_FRESH`→`test_derive_freshness_unknown_when_sha_absent` red; `if False and concept_type not in CONCEPT_TYPES`→**4 failed, 25 passed**, the same four test names; `iter_modules`→index read→`assert 'orphan' in []`. No mutation was silently green | None needed. `git status --porcelain` confirms the file unmodified |
| A3 | Vacuous evidence — the vacuous test | Confirmed the audit's sharpest claim by reading the test: `test_info_surfaces_freshness_from_index` (`test_concept_model.py:224-249`) seeds `derived.json` and `_project.json` but **no `enriched.json`**, then asserts `fresh`. It genuinely pins defect G2 as expected behaviour | None needed — already stated, and correctly |
| A4 | Counts and quotes | Re-derived every number at check time: `test_concept_model.py` **29 passed** ✓; whole `manage-architecture` directory **573 passed** ✓; `git show --stat bc86398` **17 files** ✓; md5 `bc7406029e7f408e633fadf99215c04d` ✓; `7219569`/`be98185`/`f4937d2`/`f4fef2e` all `fatal: Not a valid object name` ✓; `bc86398` an ancestor of HEAD ✓; `manage-api.md` diff is a single "Data Sources" hunk ✓. Quotes spot-checked verbatim against source: `save_module_enriched`'s "the single concept-document writer", `migrate_key_packages`'s "a named outcome, never a silent drop", `package_key_resolves`'s containment line, `--package`'s help text, `architecture-persistence.md:96-97`. **One count wrong:** `gaps.md`'s preamble said "Fourteen gaps below" over a document holding seventeen | `gaps.md` preamble corrected (now twenty, with the grouping rule stated) |
| A5 | Actionability | Every entry already carries a concrete path, a concrete change, and an observable *Done when*. No "review X"/"consider Y"/"investigate Z" anywhere. G8's Done-when is the weakest (disjunctive) but both branches are checkable. The three new entries were written to the same bar, G18's *Done when* as a content search over three literal strings | None needed; new entries written to match |
| A6 | Severity and topic | Calibration re-applied to all twenty. G1/G2 **high** is right — both are guards that fail open and misreport. G3/G4 were weighed for promotion to high (D1's Done-when is refuted, and G4 means `phase-3-outline` and `architecture module` give two different answers for one module) and **left at medium**: the calibration's medium row names "an incomplete deliverable" exactly, and no wrong *verdict* is produced. G7 stays medium — `unknown` is honest fail-closed, not a misreport. Topics all match their owning surface; new entries take `bundle-docs`, which is where G11–G13 already sit | No changes; reasoning recorded here so a later reader sees it was weighed, not skipped |
| A7 | Coverage | All four deliverables covered, plus out-of-scope, report accuracy, declared residue, collateral, and method. One hole: the plan's HYPOTHESIS "type and provenance can be added additively because readers use an accessor rather than a whole-dict schema assertion" is never named as settled — I checked it and it holds (no reader asserts on the whole dict; `manage-solution-outline` and `_cmd_client_handlers` both project selected keys). The larger hole was the un-swept documentation, handled under A2 | § Beyond-diff documentation sweep added; the accessor hypothesis noted here |
| A8 | Internal consistency | PARTIALLY REFUTED follows from D1 PARTIAL + D4 PARTIAL ✓. All eight numbered correctness defects trace forward to G1–G10; the D3 caveat → G6; D4's "at what point" → G14; D2's note → G17; test-adequacy findings → G15/G16 ✓. **One break found:** G12 and G13 (the `phase-3-outline` dotted-identity docs) existed in `gaps.md` with **no corresponding finding anywhere in `verification.md`** — they traced to nothing | § Beyond-diff documentation sweep now carries G11–G13 and G18–G20 in a per-location table, so every gap traces back to a finding and every finding forward to a gap |

**Residual doubt:** A further round would most likely find more of Family 1/Family 2 — surfaces
teaching a vocabulary this plan retired. My sweep was anchored on the literal phrases the plan
changed (`source of truth for "which modules exist"`, `index is authoritative`, `Full package name`,
dotted `key_packages` patterns); a paraphrase that says the same thing in different words would not
have been caught, and the store's *own* documentation in other bundles was only sampled. Two things
remain genuinely unverifiable from here and are correctly labelled so in the original: the live
`.plan/` store (absent from any clone, so whether real production documents carry dotted keys or
lack a `generation` header cannot be settled) and the report's whole-tree suite figures. I did not
re-run `./pw verify`, so the build-gate claims stay unverified rather than disputed. Finally, the
`.` / `./` root-key finding (G10) and the Windows drive-letter reasoning were checked on POSIX only.

**Verdict on the audit:** SOUND AFTER CORRECTION — every probe, count, mutation, and code citation
in the original re-derived correctly and the PARTIALLY REFUTED verdict is fully earned, but the
audit stopped at the two documentation surfaces the run's report happened to name and so missed
nine files still teaching the index-as-gatekeeper semantic that D3's only ⛔ MUST NOT exists to
defend, along with six off-by-N doc citations and a wrong gap count.

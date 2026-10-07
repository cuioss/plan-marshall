# Gaps — 120-documentation-surface-provider

All five deliverables shipped and four are live-verified against the real repository crawl (doc files
resolve to `documentation`, a claimed duplicate collapses to one row, an unclaimed one does not, and
`search --content` answers over the doc corpus through the existing seam). What remains falls in four
clusters.

**D4's reference engine over-reports** (G1, G2, G11): its GitHub-style heading slug collapses
hyphen/space runs where GitHub does not, so 10 of the 18 references it currently flags as dangling are
valid — the precise failure mode its own contract and the shipped SKILL.md say it cannot produce.

**The suppression note misreports its population** (G3) — and this one is **not** a pm-documents
defect. `component_refs` is deduplicated onto `(target_bundle, dep_type, resolved)` triples because
`module-discovery.md:164` mandates exactly that, and a shipped test pins it; the shared renderer in
`extension_base.py` then prints that triple count as "N reference(s) suppressed". The doc corpus's
`unresolved-target` note reads 1 where 18 references were suppressed and its `self-edge` note reads 1
where 504 were. Every Axis-C resolver on the roster shares the defect, so the fix belongs to the
shared schema and renderer, not to the doc engine.

**D2's load-bearing wiring is untested** (G5, G6): replacing both
`_collapse_claimed_duplicate_rows` call sites with `pass` leaves 149 relevant tests green.

**D2/D5's contract surface is incomplete** (G7, G8, G9, G14): the precedence rule is written in the
concept doc and the pm-documents SKILL.md but not in `client-api.md`, the document a `find`/`search`
consumer reads; `cmd_find`'s `count` became a hybrid population with no `file_count` companion to
disambiguate it; and `find` and `which-module` now name different owners for `README.md`.

## G1 — Emit the GitHub-exact heading slug so valid anchored references stop being flagged

- **Kind:** bug
- **Severity:** high
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/pm-documents/skills/plan-marshall-plugin/scripts/doc_references.py:109`
  (`_heading_anchor_forms`)
- **Evidence:** the line is
  `github = re.sub(r'[\s-]+', '-', github).strip('-')`. GitHub maps each space to one hyphen and does
  **not** collapse runs, so the heading
  `### F1 — Nearly three quarters of the corpus lives in modules nobody can navigate`
  (`doc/plans/test-quality/findings-test-corpus-review.md:99`) has the real anchor
  `f1--nearly-three-quarters-of-the-corpus-lives-in-modules-nobody-can-navigate` — the em dash is
  dropped from between two spaces, leaving two hyphens. `_heading_anchor_forms` produces only
  `f1-nearly-…`, so the live reference at `findings-test-corpus-review.md:74` is reported dangling.
  Measured over the corpus: **479** doc files, **842** references, **18** reported unresolved, of
  which **10** are anchor references and **8** are file references. With a GitHub-exact form added to
  the same function, the identical sweep yields **8** unresolved with **zero** anchor survivors, and
  all 8 are genuine broken *file* paths — a target such as `../220-resolver-configuration.md` where
  only the directory `../220-resolver-configuration/` exists. All 10 false positives are in
  `doc/plans/test-quality/findings-test-corpus-review.md`.
- **Why it matters:** the engine's docstring (`doc_references.py:96-99`) states the over-approximation
  "can only make a reference resolve, never make a valid reference fail", and the shipped SKILL.md
  repeats it as a design guarantee. Fifty-six percent of what this detector currently reports is
  wrong. A dangling-reference signal that is wrong more often than right is worse than no signal — it
  is the "confidently wrong warning" the substrate's own concept doc refuses to ship.
- **Action:** in `_heading_anchor_forms`, add a second GitHub form computed without run-collapsing —
  strip non-`[\w\s-]` characters, then `.replace(' ', '-')` — and keep the existing collapsed form
  alongside it (both are additive; the set can only grow).
- **Done when:** both of these hold, neither of which depends on the size of the `doc/**` corpus at
  the time of the fix:
  1. `test_doc_references.py` carries a case pinning a heading whose title contains an em dash
     between spaces, asserting the doubled-hyphen slug is in `extract_anchors`;
  2. a sweep of `build_doc_component_refs('.', 'doc')`-equivalent resolution over `doc/**` reports
     **zero unresolved anchor references** — the anchor class is the one the fix owns, and zero is a
     corpus-independent target because a surviving anchor failure means the slug form is still wrong.

  The **file**-reference count is reported alongside, not asserted against a threshold: at the time
  of measurement the same sweep left 8 unresolved file references, every one a genuine broken path
  (a target `X.md` where only the directory `X/` exists). That figure is a property of the corpus and
  will move as `doc/**` changes, so a later run records what it measures and confirms each survivor
  is a real broken path rather than checking it against `8`. The pre-fix figures — 479 files, 842
  references, 18 unresolved (10 anchor + 8 file) — are likewise a dated measurement, not a criterion.
- **Effort:** S
- **Risk if fixed:** the anchor set grows, so a genuinely dangling anchor whose slug collides with the
  new form is missed. That is the same one-directional under-reporting bias the function already
  documents and accepts.

## G2 — Retract or repair the "never falsely fail one" guarantee in the pm-documents SKILL.md

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/pm-documents/skills/plan-marshall-plugin/SKILL.md:90-91`
- **Evidence:** verbatim — "The bias is one-directional — it can only make a reference resolve, never
  falsely fail one." The shipped engine falsely fails 10 live references (G1). Two further routes to
  the same contradiction, both latent on this corpus but shipped: `_has_doc_suffix` mis-classifies a
  dotted bare id as a file path (G11), and `_resolve_one`'s anchor cache stamps an **empty** anchor
  set when the target file is unreadable (`doc_references.py:299-300`, `except OSError`), so every
  anchored reference into an existing-but-unreadable doc file is reported dangling. The sentence has
  three counterexamples, not one.
- **Why it matters:** this is a false completeness claim in a manifest an agent loads as contract. A
  reader trusting it will treat every `unresolved-target` note as a real defect and go chase ten
  phantom broken links.
- **Action:** fix G1, then keep the sentence but scope it to what is actually one-directional (the
  *anchor-form over-approximation*, not the slug computation); or, if G1 is deferred, replace the
  sentence with a statement of the known slug limitation. Mirror the same wording into the parallel
  claim in `doc_references.py:96-99`.
- **Done when:** the sentence in `SKILL.md` is either true of the shipped engine (G1, G11 and the
  unreadable-target route all fixed) or names each residual class explicitly, and
  `doc_references.py`'s docstring agrees with it.
- **Effort:** S
- **Risk if fixed:** none beyond doc churn.

## G3 — The shared suppression note counts deduplicated triples but calls them "reference(s)"

- **Kind:** bug
- **Severity:** high
- **Topic:** architecture-core
- **Where:** the shared substrate, **not** the doc resolver:
  - `marketplace/bundles/plan-marshall/skills/script-shared/scripts/extension/extension_base.py:1617`
    — `f'{category}: {len(candidates)} reference(s) suppressed - sample: {sample}{suffix}'`, the
    single-sourced renderer for every Axis-C resolver.
  - `marketplace/bundles/plan-marshall/skills/extension-api/standards/module-discovery.md:164` — the
    schema clause that makes `len(candidates)` a triple count: *"Entries are deduplicated on the
    `(target_bundle, dep_type, resolved)` triple, keeping the field proportional to the module count
    rather than to the raw reference count."*
  - The four resolvers that feed it, each building one `candidate` per surviving triple:
    `pm-documents/…/extension.py:371`, `pm-plugin-development/…/extension.py:276`,
    `pm-dev-python/…/extension.py:229`, `pm-code-intelligence/…/extension.py:149`.
- **Evidence:** live `derive_edges` over the real corpus emits, verbatim:
  `unresolved-target: 1 reference(s) suppressed - sample: documentation -> documentation [path]` and
  `self-edge: 1 reference(s) suppressed - sample: documentation -> documentation [path]`.
  Re-derived reference multiplicity behind those two triples: **18** unresolved references and
  **504** self-edge references (per-triple counts over 842 references: `documentation/False` 18,
  `documentation/True` 504, `plan-marshall/True` 252, `default/True` 59, `pm-plugin-development/True`
  6, `pm-documents/True` 2, `pm-dev-java-cui/True` 1). So the two notes under-report **18×** and
  **504×** respectively.
  ⚠ **The dedup is not the doc engine's choice.** `build_doc_component_refs`'s dedup on the triple is
  mandated verbatim by `module-discovery.md:164`, and a shipped test pins it as required behaviour
  (`test/pm-documents/plan-marshall-plugin/test_doc_references.py:169-175`,
  `test_component_refs_deduped_on_triple`). Every other Axis-C resolver has the identical shape, so
  this is a substrate defect the doc resolver merely made visible — not a pm-documents defect.
- **Why it matters:** the note is the *only* surface on which the dangling-reference class is
  reported, and the number it carries is the thing a reader acts on. A corpus with eighteen broken
  references is indistinguishable from one with a single stale link. This is precisely a measurement
  misreporting its own population — the defect class this epic exists to close — and because the
  renderer is single-sourced, every resolver on the roster reports the same wrong population.
- **Action:** fix it at the layer that owns the population, and do **not** make `build_doc_component_refs`
  emit one entry per reference — that would violate `module-discovery.md:164` and break
  `test_component_refs_deduped_on_triple`. Two coherent options:
  1. **Carry the multiplicity through the schema.** Add an optional, additive `occurrences` (int,
     default 1) to the `component_refs` element in `module-discovery.md`, have each materializer
     populate it, and have `_aggregate_notes` sum `occurrences` rather than counting candidates.
     Fixes every resolver at once.
  2. **Make the renderer honest about what it counts.** If the multiplicity is deliberately not
     carried, change `extension_base.py:1617` to name the population it actually has — e.g.
     `{len(candidates)} reference group(s) suppressed` — and state in `module-discovery.md`
     § `component_refs` that a note counts groups, not references.
  Option 1 is preferred: option 2 keeps the doc corpus's eighteen dangling references invisible.
- **Done when:** for the live doc corpus, the `unresolved-target` note either reports the true
  reference count (8 after G1, 18 before) or uses a noun that is true of the number it prints; and a
  unit test in `test/plan-marshall/script-shared/` (or the resolver's own test module) supplies a
  category with several references collapsing to one triple and asserts the rendered note's number
  matches the documented population.
- **Effort:** M
- **Risk if fixed:** option 1 touches a schema four bundles write and one renderer they all read, so
  the field must be optional with a documented default (a materializer that omits it must still
  render correctly); `NOTE_SAMPLE_LIMIT` truncation must still bound the sample. Option 1 also
  changes numbers already printed in `ext-point-derivation-resolver.md`'s illustrative examples —
  check them.

## G4 — Give an unresolved-reference report enough identity to be actionable

- **Kind:** incomplete
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/pm-documents/skills/plan-marshall-plugin/extension.py:371`
  (`candidate = f'{module_name} -> {target} [{dep_type}]'`)
- **Evidence:** the live note's entire payload is
  `documentation -> documentation [path]`. It names neither the referencing file, the reference text,
  nor the anchor. A reader told "a doc reference to the documentation module is dangling" over a
  407-file corpus has no next step.
- **Why it matters:** `SKILL.md:91-94` deliberately delegates the per-file, per-line broken-link
  report to `pm-documents:ref-asciidoc`'s `asciidoc verify-links`, which makes the coarse granularity
  a design choice rather than an oversight — but the note does not say so, and nothing routes a reader
  from the note to that command. The signal is technically emitted and practically unusable.
- **Action:** either carry the referencing file path into the candidate string (which requires the
  same multiplicity work as G3, so do it together), or append a fixed pointer to
  `asciidoc verify-links` in the `unresolved-target` note so the reader has a documented next step.
- **Done when:** an `unresolved-target` note either names at least one concrete referencing file, or
  names the command that will.
- **Effort:** S
- **Risk if fixed:** longer notes; `NOTE_SAMPLE_LIMIT` already bounds the sample so the payload stays
  capped.

## G5 — Test that `cmd_find` actually applies the claimed-path collapse

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py:1090`
  (`results = _collapse_claimed_duplicate_rows(results, module_names)` inside `cmd_find`)
- **Evidence:** mutation. Snapshot taken to `$TMPDIR/verify-120-mutsweep/`, the line replaced with
  `pass  # MUTATED`, then
  `uv run python -m pytest test/plan-marshall/manage-architecture/test_doc_corpus_dedup.py
  test/plan-marshall/manage-architecture/test_search_content.py
  test/plan-marshall/manage-architecture/test_cmd_client.py
  test/plan-marshall/manage-architecture/test_find_confident_negative.py
  test/pm-documents/plan-marshall-plugin/ -o addopts="" -q`.
  Baseline `149 passed in 14.66s`; mutated `149 passed in 16.85s`. File restored from the snapshot;
  `git status --porcelain` clean.
  `test_doc_corpus_dedup.py` unit-tests the helper with `resolve_path_attribution` monkeypatched, and
  `test_search_content.py:198-216` documents in its own docstring that its doubly-attributed fixture
  carries **no** Axis-D claim, so the collapse is a deliberate no-op there.
- **Why it matters:** D2 is the plan's self-declared "load-bearing and riskiest" deliverable, and its
  observable behaviour — one physical file, one row — is asserted nowhere. Deleting the call is a
  silent regression.
- **Action:** add an integration test that seeds a project whose crawled module set genuinely contains
  both a root module and a `documentation` module (note: `iter_modules` crawls the live worktree and
  ignores a fixture's declared module set, so `seed_project` alone is not sufficient — the tmp tree
  must actually make both modules discoverable, or the attribution resolver must be injected), then
  asserts `cmd_find` returns exactly one row for a doc path, attributed to `documentation`.
- **Done when:** replacing line 1090 with `pass` makes at least one test in
  `test/plan-marshall/manage-architecture/` fail.
- **Effort:** M
- **Risk if fixed:** a test that depends on live extension discovery is slower and more coupled to the
  bundle tree than the surrounding unit tests; scope it to one case.

## G6 — Test that `cmd_search` actually applies the claimed-path collapse

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py:1245`
  (the same call inside `cmd_search`)
- **Evidence:** the same mutation run as G5 replaced **both** occurrences; 149 tests stayed green.
  Separately from G5 because `cmd_search` carries its own population contract (`count` vs
  `file_count`, documented at `_cmd_client_handlers.py:1133-1142`) that the collapse directly
  changes — a claimed duplicate must make the two *converge*, an unclaimed one must leave them
  diverged, and neither direction is asserted.
- **Why it matters:** the `count`/`file_count` distinction is the surface `client-api.md` teaches
  callers to reason with. If the collapse silently stopped running, `count` would over-report the doc
  corpus by 417 rows on this repository with no test noticing.
- **Action:** extend the same fixture used for G5 with a body token present in one claimed doc file,
  and assert `count == file_count == 1` for it while the existing unclaimed `shared/dup.py` fixture
  keeps `count == 2, file_count == 1`.
- **Done when:** replacing line 1245 with `pass` makes at least one test in
  `test/plan-marshall/manage-architecture/test_search_content.py` fail.
- **Effort:** M
- **Risk if fixed:** same as G5.

## G7 — Name `cmd_find`'s population, which the collapse turned into a hybrid

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py:1093-1101`
  (`cmd_find`'s return payload)
- **Evidence:** `cmd_find` returns `count: len(results)` and nothing else. After the collapse, a
  claimed path contributes one row per file while an unclaimed path still contributes one row per
  attributing module, so `count` is a mixture. Live proof from the real repository:
  `find doc/concepts/code-intelligence.adoc` → `count: 1` for one file, while
  `find marketplace/bundles/pm-documents/skills/plan-marshall-plugin/SKILL.md` → `count: 2` for one
  file. `cmd_search` avoids exactly this by shipping both `count` and `file_count`
  (`_cmd_client_handlers.py:1254-1255`), and its docstring calls naming the population load-bearing.
- **Why it matters:** the plan's opening problem statement is a `find` returning `count: 2` for one
  physical file. That is now fixed for the doc corpus and unchanged for 2155 other duplicate rows in
  this repository, and the response gives a caller no way to tell which regime a given result is in.
- **Action:** add `file_count: len({row['path'] for row in results})` to `cmd_find`'s payload and
  document both populations in the `find` section of
  `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md`, mirroring
  the `search` section's treatment.
- **Done when:** `architecture find` returns a `file_count` key on every success response, and
  `client-api.md` § find states what `count` and `file_count` each mean.
- **Effort:** S
- **Risk if fixed:** an added response key; any consumer pinning the exact key set of a `find`
  response would need updating (I found none — every `find` caller outside the handlers is a test or
  agent-facing prose).

## G8 — State the claimed-path precedence in `client-api.md`, where `find`/`search` consumers read

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** architecture-core
  (re-topiced from `bundle-docs`: the owning surface is `manage-architecture`'s own standard, and G7
  edits the same `§ find` section — the two must land in one fix plan, not two)
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md`
  § find (starts line 817) and § search (starts line 909)
- **Evidence:** the precedence rule appears in `doc/concepts/code-intelligence.adoc:198`, in
  `marketplace/bundles/pm-documents/skills/plan-marshall-plugin/SKILL.md:62-70`, and in the
  `_collapse_claimed_duplicate_rows` docstring — but a grep of `client-api.md` for
  `unclaimed|Axis-D|ownership claim` returns only four hits, none of which define the rule: lines 1036
  and 1119 use the phrase "unclaimed cross-module duplicate" without ever describing what a *claimed*
  one does, and § find is silent on duplication entirely.
- **Why it matters:** `client-api.md` is the contract `CLAUDE.md` itself directs readers to for the
  `search --content` coverage rule, and it is where a caller goes to learn what `count` means. A
  document that uses "unclaimed" as a qualifier without defining the claimed case leaves the reader to
  infer the mechanism from a word.
- **Action:** add a short paragraph to § find and a sentence to § search stating that an Axis-D
  ownership claim outranks the root crawl — a claimed path's duplicate rows collapse onto the owning
  module's single row, an unclaimed duplicate is untouched, and a single-rowed claimed path is never
  dropped — with a cross-reference to `ext-point-path-attribution.md`.
- **Done when:** `client-api.md` states the precedence in both the `find` and `search` sections, and
  the word "unclaimed" no longer appears there without the claimed case being defined nearby.
- **Effort:** S
- **Risk if fixed:** none.

## G9 — Collapse before scanning, so `search --content` stops reading claimed files twice

- **Kind:** incomplete
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py:1218-1245`
  (`cmd_search`'s scan loop, with the collapse applied afterwards at 1245)
- **Evidence:** re-derived inventory on this repository — `documentation` inventories **479** paths,
  the intersection with the root crawl is exactly 479 (post-collapse `find '*'` returns 5062 rows over
  2907 distinct paths, so the pre-collapse row total is 5541). A live
  `search --content "The tier ladder"` reports `files_scanned: 5541` against 2907 distinct inventoried
  paths, so every one of the 479 claimed doc files is read and regex-scanned once per attributing
  module and only then de-duplicated.
- **Why it matters:** two costs. The obvious one is 479 redundant file reads plus regex passes on
  every content search — the share this plan introduced. The subtler one is that `files_scanned` — a
  field whose documented job (`_cmd_client_handlers.py:1168-1171`) is to make a `count: 0` non-vacuous
  by naming how much was searched — is a scan count sitting beside `count` and `file_count`, which are
  meticulously population-labelled. ⚠ **The over-statement is not 479.** `files_scanned` counts every
  inventory row scanned, so it over-states distinct coverage by 5541 − 2907 = **2634**: 479 from the
  doc-corpus double-scan this plan added, and 2155 from the pre-existing unclaimed marketplace
  duplication the plan puts out of scope. Only the 479 is this plan's collateral; the field's
  population mislabel predates it and is the larger half.
- **Action:** resolve ownership before the read, so a claimed path is scanned once under its owning
  module; or, if the read order must stay, add a distinct-path figure alongside `files_scanned` and
  say in `client-api.md` which is which.
- **Done when:** `files_scanned` for a whole-corpus search equals the number of distinct paths
  scanned, or the response carries both figures with both named.
- **Effort:** M
- **Risk if fixed:** reordering the collapse ahead of the scan changes which module a hit is attributed
  to for a claimed path only if the ownership resolution disagrees with the post-scan collapse — it
  cannot, since both call the same `resolve_path_attribution` — but the `unreadable[]` list would no
  longer report a claimed file twice, which is a visible payload change.

## G10 — Stop paying a full doc-corpus read on every crawl to produce seven triples

- **Kind:** incomplete
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/pm-documents/skills/plan-marshall-plugin/extension.py:245`
  (`'component_refs': build_doc_component_refs(project_root, found_doc_dir)` inside
  `discover_modules`)
- **Evidence:** measured — `build_doc_component_refs('.', 'doc')` takes **1.03 s**, reading 479 files
  and extracting anchors from each, and returns **7** triples. `discover_modules` runs from
  `crawl_all_modules`, which every architecture reader in a fresh process triggers.
- **Why it matters:** roughly a second is added to the first `architecture` call in every process, for
  a payload of seven entries — and the deduplication that shrinks it to seven (G3) discards precisely
  the per-reference detail that would justify the read. The cost is invisible today because it hides
  inside the crawl memo, but it scales with corpus size and it is paid whether or not the caller wants
  edges.
- **Action:** once G3 lands (which makes the payload carry real information), decide deliberately
  between the two coherent shapes: keep the eager read and return per-reference detail worth its
  price, or make the materialization lazy/cached against a corpus fingerprint so an unchanged doc tree
  is not re-walked per process.
- **Done when:** either `build_doc_component_refs` returns per-reference detail (so the read earns its
  cost), or a repeat crawl over an unchanged doc tree skips the walk; and the choice is stated in
  `SKILL.md`.
- **Effort:** M
- **Risk if fixed:** a cache keyed on anything weaker than file mtimes plus paths will go stale and
  report a deleted heading as still present — the exact false negative the detector exists to avoid.

## G11 — Correct `_has_doc_suffix`'s docstring, or make the body match it

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/pm-documents/skills/plan-marshall-plugin/scripts/doc_references.py:62-72`
- **Evidence:** the docstring says "a target ending in a documentation or web suffix is a file,
  everything else (`execution-modes`) is treated as an id"; the body is
  `return '.' in lowered.rsplit('/', 1)[-1]` — any dot in the final segment. A bare
  `xref:v1.2-notes[]` would therefore be classified as a file path and resolved against a non-existent
  `v1.2-notes` file, producing a false dangling report.
- **Why it matters:** latent rather than live — I checked all 18 currently-unresolved references and
  none is of this shape — but it is the same false-positive class as G1, reached by a different route,
  and the docstring actively conceals it from a maintainer reading the function.
- **Action:** either narrow the body to an explicit suffix allowlist (a superset of `_DOC_SUFFIXES`
  plus the web/code suffixes the docstring implies), or rewrite the docstring to say "any dot in the
  final segment" and name the id-with-a-dot false-positive as a known limitation.
- **Done when:** the docstring and the body describe the same rule, and a test pins the chosen
  behaviour for a dotted bare id such as `xref:v1.2-notes[]`.
- **Effort:** S
- **Risk if fixed:** narrowing to an allowlist reclassifies some current file-references as ids, which
  would make them resolve as anchors instead — verify the corpus sweep count does not move.

## G12 — Correct the run report's "zero false positives across 803 real references"

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/120-documentation-surface-provider/report-01.md:39`,
  `:50` and `:56` (three separate assertions of the figure, not two — `:50` carries the
  "Re-measured: still 0 unresolved over 803 references" sentence the audit quotes)
- **Evidence:** the report states "**Zero false positives across 803 real references**" (`:39`),
  "Re-measured: still 0 unresolved over 803 references" (`:50`) and "Re-measured: **0 unresolved over
  803 real references**" (`:56`). Re-derived now: 842 references over 479 doc
  files, 18 reported unresolved, 10 of them false positives (proven by substituting a GitHub-exact
  slug and watching those 10 vanish, leaving zero anchor reports). The corpus file carrying all 10,
  `doc/plans/test-quality/findings-test-corpus-review.md`, was added on 2026-08-15 by PR #1242 —
  after this plan merged — so the measurement was defensible on its date; the sentence as written is a
  general property claim, and the property does not hold.
- **Why it matters:** this claim is the sole evidence offered that D4's negative direction was
  verified. A later reader collecting the epic's outcomes would record a hardened engine where one
  with a live false-positive class shipped.
- **Action:** append a short correction note to `report-01.md`'s D4 entry stating the re-measured
  figures and pointing at G1, or leave the historical text intact and let this gaps file carry the
  correction — but do not let the "zero false positives" phrasing stand unqualified as the epic's
  record of D4.
- **Done when:** the epic's record of D4 states the false-positive class, either in `report-01.md` or
  in whatever artifact supersedes it.
- **Effort:** S
- **Risk if fixed:** none — the lane's documentation standards exempt a dated run report from the
  "current state only" rule, so a correction note is the appropriate shape rather than a rewrite.

## G13 — Correct the run report's stale attributor roster

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/120-documentation-surface-provider/report-01.md:35`
- **Evidence:** the report states "`attributors` now `['documentation','plan-marshall']`". Live
  `which-module` on any of the claimed paths now returns
  `attributors: ['documentation','plan-marshall','pm-plugin-development']`, `attributor_count: 3`.
  The third attributor arrived with `cc923b6` (PR #1208), after this plan merged.
- **Why it matters:** low — it is a superseded snapshot rather than an error, but the report presents
  it as a verification result, and a reader re-running that check will see a mismatch and not know
  which side is wrong.
- **Action:** none required to the code. If the report is annotated for G12, note alongside it that
  the attributor roster has since grown to three.
- **Done when:** the epic record does not present a two-element attributor list as the current state.
- **Effort:** S
- **Risk if fixed:** none.

## G14 — `find` and `which-module` disagree on the owner of a claimed, singly-inventoried file

- **Kind:** incomplete
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py:899-901`
  (`_collapse_claimed_duplicate_rows`'s `len(rows) < 2` early-out) versus
  `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md` § find
- **Evidence:** measured live against this repository. `which-module README.md` → `module:
  documentation`; `find --pattern README.md` → `count: 1` with the single row carrying `module:
  default`. Same for `CONTRIBUTING.md`. Both are files the documentation module *claims* through
  Axis-D but does not itself inventory (they sit outside `doc/`), so the collapse's `len(rows) < 2`
  early-out fires and the lone root-crawl row survives **unrewritten**. The behaviour is deliberate
  and documented in the collapse docstring (`:875-880`) — a claimed path must never vanish — but the
  consequence, that `find`'s `module` column and `which-module`'s answer name different modules for
  the same file, is stated nowhere a caller reads.
- **Why it matters:** D1's *Done when* is "the claimed files resolve to the documentation module".
  `which-module` satisfies it; `find` does not, for exactly the two repo-root files the plan went out
  of its way to claim per-file. An agent that uses `find` to locate documentation and trusts the
  `module` column will attribute `README.md` to `default` while the ownership seam says otherwise.
- **Action:** do **not** rewrite the surviving row's module — `find` reports inventory rows, and
  changing the module of a row the owning module never inventoried would make `find --module
  documentation` and `find --pattern README.md` mutually inconsistent. Instead document it: extend the
  paragraph G8 adds to `client-api.md` § find with a sentence stating that `module` names the
  *inventorying* module, that for a claimed path the collapse picks the owner's row **only when the
  owner inventoried it**, and that `which-module` is the authoritative ownership answer — with
  `README.md` as the worked example.
- **Done when:** `client-api.md` § find contains that statement naming `which-module` as the
  ownership authority and `README.md` as the example, and a test in
  `test/plan-marshall/manage-architecture/test_doc_corpus_dedup.py` pins the divergence
  (single-rowed claimed path keeps its crawling module) — `test_single_row_claimed_path_unchanged`
  already asserts the mechanism; it needs only a docstring naming the consequence.
- **Effort:** S
- **Risk if fixed:** none — documentation only.

# Verification — 120-documentation-surface-provider

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** `0beb095` on `claude/code-intelligence-substrate-analysis-kah884` for the original
audit; every corpus figure below was **re-measured at HEAD `a90adeb`** during adversarial review, and
the figures that moved (doc-file count, `files_scanned`, inventory totals) moved only because the
audit's own documents joined the corpus they measure.
**Overall verdict:** CONFIRMED WITH GAPS

The plan landed as PR [#1201](https://github.com/cuioss/plan-marshall/pull/1201), squash-merged as
`28cce1b feat(pm-documents): documentation domain owns its corpus (#1201)`. All five deliverables
exist and four of them are live-verified against the real repository crawl. D4 ships a
false-positive class that its own contract forbids. The suppression note that under-counts its
population is a **shared-substrate** defect this plan surfaced rather than caused — the deduplication
behind it is mandated by the `component_refs` schema and pinned by a shipped test.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | doc-corpus attribution claim through the seam | `claim_paths()` claims `doc`, `README.md`, `CONTRIBUTING.md`; `CLAUDE.md`/`AGENTS.md` deliberately not | Live seam resolves exactly that; `which-module` returns `documentation` for the three, `default` for the two agent files | CONFIRMED |
| D2 | de-duplication precedence, documented, consumers enumerated | `_collapse_claimed_duplicate_rows` wired into `cmd_find`/`cmd_search`; claimed 2→1, unclaimed left at 2 | Live `find doc/concepts/code-intelligence.adoc` → `count: 1` (`documentation`); live `find` on a bundle `SKILL.md` → `count: 2`. Precedence written in three places, but **not** in the `find`/`search` consumer contract, and the wiring is covered by no test | PARTIAL |
| D3 | doc-surface content search behind the existing seam | Satisfied by existing `search --content`; no parallel verb | Live `search --content` returns doc-corpus hits attributed to `documentation`; no second search verb exists anywhere in pm-documents | CONFIRMED |
| D4 | cross-document reference resolution, both directions | "Zero false positives across 803 real references"; broken reported, valid not | Engine reports **18** unresolved over **842** live references; **10 of those 18 are false positives** on valid references. The `unresolved-target` note says "1 reference(s) suppressed" for those 18 — a shared-substrate counting defect, not D4's (see G3) | PARTIAL |
| D5 | ownership + search contract documented; attribution model in `code-intelligence.adoc` | Concept doc, pm-documents SKILL.md, both extension-point rosters updated | All four surfaces present and current; one of them carries a claim the shipped code refutes, and `client-api.md` (where a `find` consumer looks) never states the precedence | PARTIAL |

## Per-deliverable detail

### D1 — doc-corpus attribution claim

- **Required (plan):** *"the claim is registered through the seam and the claimed files resolve to the
  documentation module."*
- **Claimed (report):** `Extension` subclasses `PathAttributionBase`; `path_attributor_id() →
  'documentation'`; claims `doc`, `README.md`, `CONTRIBUTING.md`; per-file exclusion of
  `CLAUDE.md`/`AGENTS.md`.
- **Found:**
  - `marketplace/bundles/pm-documents/skills/plan-marshall-plugin/extension.py:57` — `class
    Extension(ExtensionBase, PathAttributionBase, DerivationResolverBase)`.
  - `…/extension.py:253` `path_attributor_id()`, `…/extension.py:257-289` `claim_paths()`.
  - `…/extension.py:190-247` `discover_modules` with the recursive `rglob` detection.
- **Checks run:**
  - In-process `Extension().discover_modules('.')` → `[('documentation', {'module': 'doc'},
    ['documentation'])]`. The module is real in this repo.
  - `discover_path_attributors()` + `merge_path_claims(...)` + `lookup_claim(...)` over
    `['default','documentation','plan-marshall','pm-documents','pm-dev-java']`:
    `doc/concepts/code-intelligence.adoc → documentation`, `README.md → documentation`,
    `CONTRIBUTING.md → documentation`, `CLAUDE.md → None`, `AGENTS.md → None`,
    `doc/resources/x.svg → documentation`, a marketplace `SKILL.md → None`.
    Attributor reports: `[('documentation', 3, 'ok'), ('plan-marshall', 1, 'ok'),
    ('pm-plugin-development', 0, 'ok')]`.
  - Live `cmd_which_module` against the real repo: `doc/concepts/code-intelligence.adoc`,
    `README.md`, `CONTRIBUTING.md` → `documentation`; `CLAUDE.md`, `AGENTS.md` → `default`;
    `attributors: ['documentation','plan-marshall','pm-plugin-development']`, `attributor_count: 3`.
- **Verdict:** CONFIRMED — every literal clause of the *Done when* holds against the live crawl, and
  the per-file decision the plan's Out-of-scope demanded was actually made rather than glob-swept.

### D2 — de-duplication against the root module

- **Required (plan):** *"one physical file yields one row from the affected query surfaces, the
  precedence is written down, and the consumer enumeration below has been done."* Verification section
  adds: *"D2 is verified by the consumer enumeration, not by the query output … The run report must
  list the consumers examined and state how the population was derived."*
- **Claimed (report):** new `_collapse_claimed_duplicate_rows` wired into `cmd_find`/`cmd_search`; an
  Axis-D claim outranks the root crawl; unclaimed duplicates untouched; population derived by sweeping
  `find`/`search --content` invocations across the bundle tree and `.claude/`.
- **Found:**
  - `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py:857-908`
    — the collapse.
  - Wired at `…/_cmd_client_handlers.py:1090` (`cmd_find`) and `…:1245` (`cmd_search`).
  - Precedence written down in `doc/concepts/code-intelligence.adoc:196-198`,
    `marketplace/bundles/pm-documents/skills/plan-marshall-plugin/SKILL.md:62-70`, and the collapse
    docstring itself.
- **Checks run (live, against the real repository, no `.plan/` present — `iter_modules` crawls the
  worktree):**
  - `iter_modules('.')` → `['default','documentation','plan-marshall','pm-code-intelligence',
    'pm-dev-frontend','pm-dev-frontend-cui','pm-dev-java','pm-dev-java-cui','pm-dev-oci',
    'pm-dev-python','pm-documents','pm-plugin-development','pm-requirements']` — 13 modules,
    `documentation` among them.
  - `cmd_find(pattern='doc/concepts/code-intelligence.adoc')` → `count: 1`, single row
    `{'module':'documentation','category':'doc',…}`. The plan's headline defect is closed.
  - `cmd_find(pattern='README.md')` → `count: 1`, row `{'module':'default',…}` — the single-rowed
    claimed path is left intact exactly as the docstring promises (it does not vanish).
  - `cmd_find(pattern='marketplace/bundles/pm-documents/skills/plan-marshall-plugin/SKILL.md')` →
    `count: 2` (`default` + `pm-documents`) — the unclaimed duplicate is untouched.
  - Inventory overlap re-derived: `documentation` inventories **479** paths, and every one is also in
    the root crawl (post-collapse `find '*'` returns **5062** rows over **2907** distinct paths, so
    the pre-collapse row total is **5541** — matching `files_scanned` exactly). Duplicate rows before
    the collapse: **2634**. So the collapse removes 479 of them; the remaining **2155** are the
    unclaimed marketplace duplication the plan puts out of scope.
  - `cmd_find(pattern='CONTRIBUTING.md')` → `count: 1`, row `{'module':'default',…}` — same shape as
    `README.md`. ⚠ Both are files the documentation module *claims* but does not inventory, so
    `find` reports them under `default` while `which-module` reports them under `documentation`. See
    G14.
- **Gaps against the literal contract:**
  1. **No test covers the wiring.** Mutation: both call sites replaced with `pass`. Baseline
     `test_doc_corpus_dedup.py test_search_content.py test_cmd_client.py
     test_find_confident_negative.py test/pm-documents/plan-marshall-plugin/` → `149 passed in
     14.66s`. With the mutation → `149 passed in 16.85s`. The behaviour change D2 exists to deliver is
     verified by no test at all; only the helper's internals are unit-tested (with a stubbed
     resolver). See G5/G6.
  2. **The precedence is not stated where a `find`/`search` consumer looks.**
     `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md` § find
     (line 817ff) says nothing about duplication at all, and § search uses the phrase "unclaimed
     cross-module duplicate" twice (lines 1036, 1119) without ever defining the *claimed* case. See G8.
  3. **`find`'s `count` is now a hybrid population.** `cmd_search` names both populations
     (`count` = rows, `file_count` = distinct paths); `cmd_find` returns only `count`, which after the
     collapse means "files, for claimed paths; rows, for unclaimed ones". See G7.
- **On the consumer enumeration:** the report's enumeration of `find` / `search --content` callers is
  sound as far as it goes, and its central conclusion — no programmatic consumer de-dupes by path, so
  the double-correct failure has no site — held up when I re-swept. What it does **not** enumerate is
  the second, larger change the run made: `documentation` became a *new module* in every project with
  a nested doc tree, which changes `iter_modules`, the module graph, and every module-iterating
  surface. That population was never derived. The one consequence I could check — a docs-only change
  still derives zero builds — holds (`test_derive_verification.py:390`, passing at baseline).
- **Verdict:** PARTIAL — the mechanism is correct and live-verified, the precedence is documented, but
  the load-bearing wiring is untested, the consumer-facing contract does not carry the rule, and the
  enumeration the plan made D2's *sole* verification is incomplete on the new-module axis.

### D3 — doc-surface search

- **Required (plan):** *"a content query over the doc corpus is answerable through the existing
  seam"*, with an absolute prohibition on a second search verb.
- **Claimed (report):** satisfied by the existing `search --content` seam; no parallel verb.
- **Found / checks run:** live `cmd_search(pattern='The tier ladder', literal=True)` → `count: 4`,
  `file_count: 4`, `files_scanned: 5541`, all four hits attributed to `module: documentation`
  (`doc/concepts/code-intelligence.adoc`, `match_count: 2`; plus this plan's own `report-01.md`,
  `gaps.md` and `verification.md` — the audit's own documents are now inside the corpus it measures).
  The only new script the plan shipped,
  `marketplace/bundles/pm-documents/skills/plan-marshall-plugin/scripts/doc_references.py`, is a
  library — it has no `argparse`, no `main`, no CLI entry point, and is imported only from
  `extension.py:235`. No second search verb exists.
- **Verdict:** CONFIRMED. One efficiency observation, not a contract failure: `files_scanned: 5541`
  against 2907 distinct inventoried paths, because the collapse runs *after* the body scan — every
  claimed doc file is read and regex-scanned twice. Of the 2634-row gap, only **479** is this plan's
  doubling; the other 2155 is the pre-existing unclaimed duplication. See G9.

### D4 — cross-document reference resolution

- **Required (plan):** *"a deliberately broken reference is reported as unresolvable, and a valid one
  is not."* The Verification section restates it: *"D4 is verified in both directions."*
- **Claimed (report):** `derive_edges` joins over `component_refs` materialized by
  `scripts/doc_references.py`; "**Zero false positives across 803 real references**"; the engine was
  deliberately hardened after a first pass reported 14 false positives.
- **Found:**
  - `…/scripts/doc_references.py` — the engine; `extract_references` (:160), `extract_anchors` (:121),
    `_heading_anchor_forms` (:75), `_resolve_one` (:253), `build_doc_component_refs` (:309).
  - `…/extension.py:317-382` — `derive_edges`, the pure join.
  - Live `derive_edges` over the real corpus →
    `edges: [('documentation','default'), ('documentation','plan-marshall'),
    ('documentation','pm-dev-java-cui'), ('documentation','pm-documents'),
    ('documentation','pm-plugin-development')]`, matching the report's edge set.
- **Checks run — the positive direction holds:** a deliberately broken reference *is* reported.
  `test_broken_file_reference_is_reported_unresolved`, `test_broken_anchor_reported_valid_anchor_not`,
  `test_same_file_anchor_resolution` all pass, and the live corpus does contain 8 genuinely dangling
  file references the engine correctly flags (e.g.
  `doc/plans/code-intelligence-substrate/240-skill-lsp-server/proposal-protocol-surface.md →
  ../220-resolver-configuration.md`, which is a directory, not a file).
- **Checks run — the negative direction FAILS.** Re-measured over the live doc corpus (479 files):
  **842 references, 18 reported unresolved** — 10 anchor references and 8 file references. Ten of
  those eighteen are valid references falsely flagged. The cause is a single line:

  `doc_references.py:109` — `github = re.sub(r'[\s-]+', '-', github).strip('-')`

  GitHub's slug maps each space to one hyphen and does **not** collapse runs, so
  `### F1 — Nearly three quarters of the corpus lives in modules nobody can navigate`
  (`doc/plans/test-quality/findings-test-corpus-review.md:99`) has the real anchor
  `f1--nearly-three-quarters-…` (double hyphen, the em dash having been dropped between two spaces).
  The engine produces `f1-nearly-three-quarters-…` (single hyphen), so the live reference at
  `findings-test-corpus-review.md:74` is reported as a dangling anchor. Proof by substitution: with a
  GitHub-exact slug added to `_heading_anchor_forms`, the same sweep over the same 842 references
  drops from 18 unresolved to **8**, with **zero** anchor survivors — all 8 are genuine broken file
  paths (each names `X.md` where only the directory `X/` exists).
- **Checks run — the suppression note misreports its population, at the shared layer.** Live output,
  verbatim:

  ```
  unresolved-target: 1 reference(s) suppressed - sample: documentation -> documentation [path]
  self-edge: 1 reference(s) suppressed - sample: documentation -> documentation [path]
  ```

  Re-derived multiplicity behind those two triples: **18** unresolved references and **504**
  self-edge references (full per-triple census over 842 references: `documentation/False` 18,
  `documentation/True` 504, `plan-marshall/True` 252, `default/True` 59, `pm-plugin-development/True`
  6, `pm-documents/True` 2, `pm-dev-java-cui/True` 1). The two notes under-report **18×** and
  **504×**.

  ⚠ **The dedup is schema-mandated, so this is not a pm-documents defect.**
  `build_doc_component_refs`'s collapse onto `(target_bundle, dep_type, resolved)`
  (`doc_references.py:331`, `:350`) is required verbatim by
  `extension-api/standards/module-discovery.md:164` — *"Entries are deduplicated on the
  `(target_bundle, dep_type, resolved)` triple, keeping the field proportional to the module count
  rather than to the raw reference count"* — and a shipped test pins it
  (`test_doc_references.py:169-175`, `test_component_refs_deduped_on_triple`). All four Axis-C
  resolvers build one candidate per surviving triple (`pm-documents:371`,
  `pm-plugin-development:276`, `pm-dev-python:229`, `pm-code-intelligence:149`) and hand it to the
  single-sourced renderer `DerivationResolverBase._aggregate_notes`
  (`extension_base.py:1617`), which prints `len(candidates)` under the noun "reference(s)". The
  mismatch between the schema's population and the renderer's noun is the defect, and it is shared by
  the whole roster. See G3.
- **Verdict:** PARTIAL — the positive direction is satisfied; the negative direction, which the plan
  singled out as the reason the deliverable is verified *in both directions*, is violated on 10 live
  references. The suppression-note under-count is real but lands on the shared substrate rather than
  on this deliverable: D4 conforms to the schema it was given.

### D5 — documentation

- **Required (plan):** *"the precedence rule from D2 is stated where a future reader will look for it,
  not only in the run report."*
- **Claimed (report):** `code-intelligence.adoc` attribution-model addition; pm-documents
  `plan-marshall-plugin/SKILL.md`; `ext-point-path-attribution.md` § Current implementations; plus the
  post-review fix to `ext-point-derivation-resolver.md` § Current implementations.
- **Found (all four present and current):**
  - `doc/concepts/code-intelligence.adoc:194` (the ownership claim and the per-file exclusion),
    `:196` (the duplication it exposes), `:198` (the precedence, framed as precedence-not-decree).
  - `marketplace/bundles/pm-documents/skills/plan-marshall-plugin/SKILL.md:50-94` — ownership,
    precedence, content-search-through-the-existing-seam, reference resolution.
  - `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-path-attribution.md:140`
    — the `documentation` attributor row, including the reconciled `.svg` note the report mentions
    (independently confirmed: `lookup_claim('doc/resources/x.svg') → documentation`).
  - `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-derivation-resolver.md:232`
    — the `documentation` resolver row. Live roster check confirms it is registered:
    `['documentation','lsp','markdown','maven','npm','pyproject','python']`.
- **Defects:**
  1. `SKILL.md:90-91` asserts *"The bias is one-directional — it can only make a reference resolve,
     never falsely fail one."* The shipped engine falsely fails 10 live references. A false claim in
     shipped documentation. See G2.
  2. The precedence is absent from `client-api.md`, the contract a `find`/`search` consumer reads (and
     the one `CLAUDE.md` itself points at). See G8.
- **Verdict:** PARTIAL — the plan's literal *Done when* is met (the rule is stated outside the run
  report, in two durable places), but one of those statements is now false and the consumer-facing
  contract was left behind.

## Correctness review

I read `doc_references.py` (356 lines) and `extension.py` (383 lines) in full, plus
`_collapse_claimed_duplicate_rows` and both of its call sites, `resolve_path_attribution`
(`_architecture_core.py:1125-1185`), and `_resolve_module_inventory` /
`build_module_files_inventory` to establish what the readers actually enumerate.

Defects found:

1. **`doc_references.py:109` — GitHub slug collapses hyphen/space runs.** Input: any heading whose
   title contains a non-word character surrounded by spaces (an em dash, a slash). Consequence: the
   real GitHub anchor carries a doubled hyphen the engine never emits, so a valid Markdown
   cross-reference is reported as a dangling anchor. 10 live instances, all in
   `doc/plans/test-quality/findings-test-corpus-review.md`. This is the exact failure mode the
   engine's own docstring (`:96-99`) says the over-approximation cannot produce.

2. **`extension_base.py:1617` — the shared suppression note counts triples, not references.**
   `component_refs` is deduplicated on `(target_bundle, dep_type, resolved)` **because
   `module-discovery.md:164` mandates it**, so `_aggregate_notes` renders `len(candidates)` over an
   already-collapsed population while calling the result "reference(s)". Consequence on this corpus:
   `unresolved-target: 1 reference(s) suppressed` for 18 real suppressions, and `self-edge: 1
   reference(s) suppressed` for 504. A measurement surface reporting numbers 18× and 504× smaller
   than the thing it names. **The owning layer is the shared schema plus the shared renderer, not
   `doc_references.py`** — all four Axis-C resolvers feed the renderer one candidate per triple, and a
   shipped test (`test_doc_references.py:169-175`) pins the doc engine's dedup as required. A fix
   applied inside pm-documents would put it in violation of its own schema.

3. **`doc_references.py:62-72` — `_has_doc_suffix` does not do what its docstring says.** The
   docstring says it detects "a documentation or web suffix"; the body returns True for any dot in the
   last path segment. Latent, not live: a bare `xref:v1.2-notes[]` would be treated as a file path and
   reported dangling. No instance in the current corpus (I checked all 18 unresolved entries).

4. **`_cmd_client_handlers.py:1090/1245` — the collapse runs after the work.** In `cmd_search` the
   body of every claimed doc file is read and regex-scanned once per attributing module and only then
   de-duplicated, so 479 files are scanned twice (`files_scanned: 5541` against 2907 distinct paths).
   Correct output, wasted I/O, and `files_scanned` is a scan count presented alongside fields that are
   carefully population-labelled. Note the field over-states distinct coverage by 2634, not by 479 —
   the majority of the gap is the pre-existing unclaimed duplication, which this plan neither created
   nor was scoped to fix.

5. **`_cmd_client_handlers.py:1093-1101` — `cmd_find` has no `file_count`.** After the collapse its
   `count` is neither a row count nor a file count but a mixture keyed on whether a path is claimed.
   `cmd_search` names both populations; `cmd_find` names neither.

Checked and found **clean**:

6. **`extension.py:245` — `discover_modules` pays a full doc-corpus read on every crawl.**
   `build_doc_component_refs('.', 'doc')` measured at **1.03 s**, reading 479 files, to return **7**
   triples; it runs from `crawl_all_modules`, which every architecture reader triggers in a fresh
   process. Not a correctness defect, and invisible behind the crawl memo, but it is real cost added
   to a Tier-0 path. See G10.

7. **`find` and `which-module` disagree on a claimed file's owner.** `which-module README.md` →
   `documentation`; `find --pattern README.md` → one row carrying `module: default`. The collapse's
   `len(rows) < 2` early-out (`:899-901`) is correct — a claimed path must never vanish — but for the
   two repo-root files the plan claimed per-file, the two reader surfaces now name different modules
   and nothing tells a caller which is authoritative. See G14.

- The escaping-target fail-closed path (`_resolve_one:273-282`) returns before any `.exists()` /
  `.read_text()`, and two regression tests pin it with a file that genuinely exists outside the root
  (`test_doc_references.py:197-226`) — a real, non-vacuous test of the security fix.
- `derive_edges` purity: no filesystem access; pinned by `test_derive_edges_reads_no_file`.
- The build-system scoping guard (`extension.py:362-364`) does keep the resolver off marketplace
  `path` refs; pinned by `test_resolver_ignores_non_documentation_modules`.
- `_collapse_claimed_duplicate_rows` guards: `len(rows) < 2` early-out, `owner is None` early-out, and
  `owner_rows if owner_rows else rows` — none of the three can drop a path. All three are unit-tested.
- The module-existence guard on the claim (a claim naming `documentation` is dropped where no such
  module exists) is real: it is why every synthetic tmp-project fixture is unaffected by the collapse.
- One file cannot land in two categories within one module (`build_module_files_inventory`
  classifies each walked entry exactly once), so the "owner contributes two rows" edge the collapse
  would not handle is unreachable.
- The `----` / `....` / ``` ``` ``` fence toggle in `extract_references` is not balanced by
  construction and a stray thematic rule could strand the parser inside a pseudo-fence; I swept all
  407 corpus files and **0** end inside an unclosed fence, so this is theoretical here.

## Test adequacy

| Deliverable | Covering tests | Adequacy |
|---|---|---|
| D1 discovery | `test/pm-documents/plan-marshall-plugin/test_documentation_extension.py:72-96` | Good — the nested-doc case is the exact defect the fix removes, plus a negative (`test_no_documentation_module_without_docs`) |
| D1 attribution | `…test_documentation_extension.py:104-119` | Good — pins both the three claims and the two per-file exclusions |
| D2 collapse rules | `test/plan-marshall/manage-architecture/test_doc_corpus_dedup.py` (6 tests) | Adequate for the helper in isolation; **stubs `resolve_path_attribution`**, so it proves the rules, not the integration |
| D2 wiring | *none* | **Absent — proven.** See mutation evidence below |
| D3 | `test/plan-marshall/manage-architecture/test_search_content.py` | Pre-existing; exercises the seam, not the doc corpus. `_seed_doubly_attributed_file` (`:198-216`) explicitly documents that its fixture has **no** Axis-D claim, so the collapse is a no-op there by design |
| D4 extraction/anchors | `test/pm-documents/plan-marshall-plugin/test_doc_references.py:27-111` | Good coverage of the spellings; **no test pins a heading with an em dash or any other run-producing character**, which is why the live false-positive class shipped |
| D4 both directions | `…test_doc_references.py:125-166` | Non-vacuous — `test_valid_file_reference_is_resolved` asserts `all(resolved)`, so an always-False engine goes red; `test_broken_anchor_reported_valid_anchor_not` asserts both states are present, so an always-True or always-False engine goes red. It does not bind which reference produced which state |
| D4 security fix | `…test_doc_references.py:197-226` | Strong — the fixture file genuinely exists outside the root, so the assertion cannot pass by the target simply being absent |
| D4 resolver notes | `…test_documentation_extension.py:145-169` | Covers the three suppression categories, but each fixture supplies a single `component_refs` entry, so the count-versus-triple confusion (defect 2) is structurally invisible to them |

**Mutation evidence for the D2 wiring gap.** Snapshot taken to
`$TMPDIR/verify-120-mutsweep/_cmd_client_handlers.py.orig`. Both occurrences of

```python
    results = _collapse_claimed_duplicate_rows(results, module_names)
```

(lines 1090 and 1245) replaced with `pass  # MUTATED`. Command:

```
uv run python -m pytest test/plan-marshall/manage-architecture/test_doc_corpus_dedup.py \
  test/plan-marshall/manage-architecture/test_search_content.py \
  test/plan-marshall/manage-architecture/test_cmd_client.py \
  test/plan-marshall/manage-architecture/test_find_confident_negative.py \
  test/pm-documents/plan-marshall-plugin/ -o addopts="" -q
```

Baseline: `149 passed in 14.66s`. Mutated: `149 passed in 16.85s`. **The mutation survives.**

**Independently reproduced during adversarial review** at HEAD `a90adeb`, with a fresh byte snapshot:
baseline `149 passed in 3.33s`, mutated `149 passed in 5.53s`. The mutation survives. A direct search
confirms why: `_collapse_claimed_duplicate_rows` is named by exactly one test module
(`test_doc_corpus_dedup.py`, which calls the helper directly with a monkeypatched resolver) and by one
docstring in `test_search_content.py:206` explaining that its fixture deliberately carries no claim.
No test invokes `cmd_find`/`cmd_search` against a project where the collapse can fire.

⚠ **The wide-run evidence in the original audit does not survive re-measurement and has been
discounted.** The audit reported `4 failed, 569 passed` over the whole of
`test/plan-marshall/manage-architecture/` under the mutation, attributed to a sibling session. My own
wide run under the mutation also produced 4 failures — but a *different* four
(`test_capabilities.py` ×2, `test_concept_model.py`, `test_derivation_resolver_configuration.py`), and
those three files pass **58/58 in isolation under the same mutation**, while a wide run at restored
state produced a fifth, different failure
(`test_files_inventory.py::test_bare_claude_claim_covers_the_former_unclaimed_sibling`). Wide-run
readings in this shared worktree are not reproducible and prove nothing in either direction; the
narrow baseline/mutant pair is the only evidence relied on. The file was restored from my own byte
snapshot (`cp` from the scratchpad, never `git checkout`/`restore`/`stash`); `git status --porcelain`
does not list it and a `diff -q` against the snapshot is clean.

## Report accuracy

Claims in `report-01.md` that no longer hold against the tree now:

1. > "**Zero false positives across 803 real references** (see Findings)." (`report-01.md:39`)
   > "Re-measured: still 0 unresolved over 803 references." (`:50`)
   > "Re-measured: **0 unresolved over 803 real references**" (`:56`)

   Re-derived now: **842** references over **479** doc files, **18** reported unresolved, of which
   **10** are false positives. The 803/0 figures were plausibly true on 2026-08-13 —
   `doc/plans/test-quality/findings-test-corpus-review.md`, which carries all 10 false positives, was
   added on 2026-08-15 by PR #1242 (`git log --diff-filter=A`), after this plan merged. But the
   *engine defect* was shipped by this plan, and the claim as written is a general property claim
   ("zero false positives"), not a dated measurement. It is refuted.

2. > "`attributors` now `['documentation','plan-marshall']`."

   Live now: `['documentation','plan-marshall','pm-plugin-development']`, `attributor_count: 3`. The
   third attributor arrived with PR #1208, after this plan. Stale rather than wrong-at-the-time.

3. > "the resolver table is complete and internally consistent (1 Axis-B + 3 Axis-A, matching
   > `EXPECTED_RESOLVER_IDS` …)"

   Live roster is now 7 resolvers (`documentation`, `lsp`, `markdown`, `maven`, `npm`, `pyproject`,
   `python`). Superseded by later plans, not a defect of this run.

Claims that **held** on re-check:

- `find code-intelligence.adoc` 2→1 row attributed to `documentation` — confirmed live.
- Unclaimed marketplace `SKILL.md` stays 2 rows — confirmed live (`count: 2`).
- `which-module` for the three claimed files → `documentation`, for `CLAUDE.md`/`AGENTS.md` →
  `default` — confirmed live.
- `search --content "The tier ladder"` hits `doc/concepts/code-intelligence.adoc` attributed to
  `documentation` — confirmed live (2 hits now; the second is this plan's own report, added after the
  run).
- The Axis-C edge set `documentation → {plan-marshall, pm-dev-java-cui, pm-documents,
  pm-plugin-development}` — confirmed live, plus a `default` edge the report did not name.
- The core edit was declared, and it is genuinely the only one: no other `manage-architecture` change
  is attributable to this plan.
- The D2 consumer enumeration's conclusion ("no programmatic consumer reads the result and de-dupes by
  path") — re-swept and confirmed. The `find`/`search` call sites outside the handlers are tests and
  agent-facing prose.

`19370 passed, 14 skipped` from the build gate is **UNVERIFIABLE**: it describes a `./pw verify` run
at a commit three weeks of merges ago, and the brief forbids re-running the full suite.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| Landing confirmation delegated to the orchestrator's collect | **Closed** | `28cce1b feat(pm-documents): documentation domain owns its corpus (#1201)` is on the mainline ancestry |
| A local `/sync-plugin-cache` is owed on a developer machine | **Moot** | Machine-local build step; `CLAUDE.md` § Standalone Plan Lane states a lane plan neither performs nor records one |
| D4 residual: a heading under a non-default `:idprefix:` is not resolved | **Still open** | `doc_references.py:137-138` documents it verbatim; no code covers the case. Under-reporting only, so lower-severity than the *over*-reporting defect the same function now has (G1) |
| Optional consistency item declined: `extension-architecture.adoc`'s Axis-D example omits the documentation claim | **Closed by a later plan** | `doc/concepts/extension-architecture.adoc:29` now reads "…`pm-plugin-development` the `.claude` project-local tree, and `pm-documents` the doc corpus"; `git log -S` attributes it to `cc923b6` (#1208) |

## Out-of-scope and collateral

- **"A second content-search verb" — respected.** `doc_references.py` is a library with no CLI
  surface, imported only from `extension.py:235`. D3 rides the existing seam.
- **"Sweeping the whole repo root into the documentation module by glob" — respected.** Three literal
  claims, and the two agent-instruction files are excluded with a written rationale in the code
  (`extension.py:270-275`), the concept doc, and the extension-point roster.
- **"Editing the architecture core" — deviated from, but declared.** The plan says: *"If this plan
  finds itself editing core beyond registering a claim, that means the seam is incomplete — loop back
  and report it rather than patching core here."* The run patched core (a 52-line function plus two
  call sites) after an `AskUserQuestion` to a reachable operator, and reported the edit in three
  places. Sanctioned and visible; recorded here for completeness, not as an actionable gap.
- **Undeclared collateral: the module set changed.** Making `discover_modules` recursive did more than
  enable the claim — it added a `documentation` module to every project with a nested doc tree
  (13 modules here where there were 12). The report frames this as a "necessary prerequisite" but does
  not enumerate what else reads the module list. This is the un-derived half of D2's mandated consumer
  population; it is folded into the D2 verdict rather than raised as its own gap, because the one
  consequence that could plausibly break — docs-only changes deriving a build — is tested and green.

## Method and coverage

**What I ran** (repository root `/home/user/plan-marshall`, no `.plan/` in the clone, so every
architecture reader was driven in-process through `iter_modules`' live worktree crawl):

- `Extension().discover_modules('.')`, `claim_paths()`, `path_attributor_id()`, `derive_edges(...)`
  loaded by explicit path.
- `discover_path_attributors()` / `merge_path_claims()` / `lookup_claim()` over an explicit module
  list, and `discover_derivation_resolvers()` for the live roster.
- `cmd_find`, `cmd_search`, `cmd_which_module` against the **real repository**, loaded through
  `test/conftest.py::load_script_module`.
- A full re-derivation of the doc reference corpus: 407 files, 841 references, 18 unresolved; then the
  same sweep with a GitHub-exact slug patched into `_heading_anchor_forms` → 8 unresolved.
- An inventory-overlap re-derivation across all 13 modules (417 / 2661 / 417 / 5417 / 2845 / 2572).
- Two pytest runs (baseline and mutated) over 149 tests spanning the five relevant test files.
- `git log --diff-filter=A`, `git log -S`, and `git log --grep` to date the corpus files and the
  merge commits.

**Every count in this document was re-derived at the moment it is stated.** No figure is copied from
`report-01.md`; where I quote one it is explicitly attributed to the report and contrasted with my own
measurement.

**What I could not check:**

- The report's `./pw verify` result (`19370 passed, 14 skipped`) — historical, and re-running the full
  suite is out of scope per the brief.
- Whether the collapse behaves correctly inside a real `.plan/`-backed project with persisted
  `derived.json` and an enrichment stub for the new `documentation` module — this clone has no
  `.plan/`, and my synthetic fixture attempt was invalidated when I discovered `iter_modules` crawls
  the live worktree and discards the fixture's declared module set (a trap worth recording: seeding
  `_project.json` with three modules yielded exactly one, so any fixture-based conclusion about
  cross-module duplication in a tmp project is unsound). I substituted a live run against the real
  repository, which is stronger evidence, not weaker.
- Downstream effects of the new `documentation` module on phase-4 planning, task-profile resolution,
  and module-tests scoping — these need an orchestrated run, not a reader call.

**Contamination note.** Sibling verification sessions were mutating this shared worktree concurrently
throughout (`_cmd_client_query.py`, `_lsp_workspace_edit.py`, `_findings_core.py`,
`manage-metrics.py`, `_self_review_detectors.py` were all dirty at various points, and HEAD advanced
under me). I confined my own mutation to one file, took my own byte snapshot first, restored from it,
and verified `git status --porcelain` clean plus a `diff -q` match for every file I touched. Where a
test result could have been contaminated I re-ran it narrowly; the narrow baseline/mutant pair above is
the evidence I rely on, not the wide run.

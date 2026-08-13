# Run report — 120-documentation-surface-provider (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/documentation-surface-provider-u1d4fg` (harness-assigned)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded
- `cloud-plan-lane` (working contract; loaded first).
- `plan-marshall:ref-code-quality` (read from bundle path).
- `pm-plugin-development:plugin-script-architecture` (read from bundle path).
- `pm-dev-python:python-core` / `pm-dev-python:pytest-testing` — production/test Python surface (loaded on demand while implementing).
- `pm-documents:ref-asciidoc` — `.adoc` surface (doc reference engine reuse).

GitHub access path: **GitHub MCP server** (cloud session).

## Re-derivation in the clone (mandated by the plan's claim-label table)

The plan's central premise is **refuted** by re-derivation against the live crawl. Ground truth (via an in-process crawl mirroring the executor PYTHONPATH):

- **There is no `documentation` module.** pm-documents' `discover_modules` gates on a *non-recursive* glob (`doc/*.adoc`, `doc/*.md`) plus `README.adoc`. This repo has **zero** top-level doc files under `doc/` (all 62 `.adoc` are nested in `doc/concepts/`, `doc/adr/`, `doc/developer/`, …) and no `README.adoc`, so `discover_modules` returns `[]`. Only two extensions are applicable: `plan-marshall` (→ `default` root at `.`) and `pm-plugin-development` (→ bundle modules).
- **The doc corpus is indexed ONCE, by the `default` root module.** `find doc/concepts/code-intelligence.adoc` → `count: 1` (`default:doc`). `find README.md` → `count: 1` (`default:doc`). It is **not** double-indexed.
- **`which-module` for the whole doc corpus resolves to `default`**, with the only attributor being `plan-marshall`.
- The real duplication that *does* exist is the *marketplace-bundle* one (`SKILL.md` → `default:doc` + `pm-dev-java:skill`, `count: 2`), which the plan puts **out of scope**.
- The Axis-D contract (`ext-point-path-attribution.md` § Current implementations) documents the *intended* end state — `doc/concepts/*.adoc` files should "resolve to `documentation`" — but that state is **not yet built**. This plan builds it.

**Operator decision (AskUserQuestion, recorded per lane rule for a reachable operator):**
- D1/D2 approach → **Faithful: make the `documentation` module real** (fix pm-documents discovery to detect nested docs; claim the doc corpus for `documentation` via Axis-D; add a reader-level precedence to de-duplicate the doc/** duplication this introduces — a core change the plan permits "only if needed" and requires reporting).
- D4 → **Axis-C resolver** (pm-documents becomes a `DerivationResolverBase` deriving module edges from cross-document references and reporting unresolvable ones), matching `code-intelligence.adoc`'s stated design.

## Deliverables

All five implemented. Verified against the live crawl (in-process, mirroring the executor PYTHONPATH) and by tests.

- **D1 — doc-corpus attribution claim.** `marketplace/bundles/pm-documents/skills/plan-marshall-plugin/extension.py`:
  - `discover_modules` fixed to detect nested docs (recursive `rglob`), so the `documentation` module is discovered in this repo (it was inert — the non-recursive glob missed all 62 nested `.adoc`). Necessary prerequisite: the Axis-D claim's module must exist.
  - The `Extension` now subclasses `PathAttributionBase`; `path_attributor_id() → 'documentation'`; `claim_paths()` claims `doc`, `README.md`, `CONTRIBUTING.md` for `documentation`. **Per-file decision**: `CLAUDE.md`/`AGENTS.md` deliberately NOT claimed (agent-instruction files, per Out-of-scope).
  - *Verified*: `which-module doc/concepts/code-intelligence.adoc`, `README.md`, `CONTRIBUTING.md` → `documentation`; `CLAUDE.md`/`AGENTS.md` → `default`. `attributors` now `['documentation','plan-marshall']`.
- **D2 — de-duplication precedence.** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py` — new `_collapse_claimed_duplicate_rows`, wired into `cmd_find`/`cmd_search`. An Axis-D claim outranks the root crawl: a claimed path's duplicate rows collapse onto the owning module's single row; an **unclaimed** duplicate is left untouched. **This is the one architecture-core edit the seam required** — reported here per the plan's Out-of-scope note. *Verified*: `find code-intelligence.adoc` 2→1 row (`documentation`); unclaimed marketplace `SKILL.md` stays 2 rows.
  - **Consumer enumeration** (D2's stated risk) — see Findings below.
- **D3 — doc-surface content search.** Satisfied by the **existing** `search --content` seam once the `documentation` module inventories `doc/**`; no parallel verb shipped. *Verified*: `search --content "The tier ladder"` → single hit attributed to `documentation`, `doc/concepts/code-intelligence.adoc`.
- **D4 — cross-document reference resolution (Axis-C).** The `Extension` subclasses `DerivationResolverBase`; `derivation_resolver_id() → 'documentation'`; `derive_edges` joins over `component_refs` materialized by the new engine `scripts/doc_references.py` (extracts `xref:`/`link:`/`include::`/`<<>>`/markdown links, resolves file + anchor existence, maps targets to modules). *Verified*: derives `documentation → {plan-marshall, pm-dev-java-cui, pm-documents, pm-plugin-development}` edges from real docs; a deliberately-broken reference is reported unresolved and a valid one is not (fixture tests). **Zero false positives across 803 real references** (see Findings).
- **D5 — documentation.** `doc/concepts/code-intelligence.adoc` (attribution-model addition: doc-corpus ownership + precedence); pm-documents `plan-marshall-plugin/SKILL.md` (doc-surface ownership + search + reference-resolution contract); `ext-point-path-attribution.md` § Current implementations (the `documentation` attributor row; reconciled the now-resolved `doc/resources/**.svg` out-of-scope note).

## Build gate
`git diff --name-only origin/main...HEAD` touches `*.py` (pm-documents extension + engine, manage-architecture handlers, tests) → `./pw verify` required. **Result: `verify: SUCCESS`** — `19370 passed, 14 skipped` (7m02s); full-scope mypy (production 396 + test 721 files), ruff, SPDX headers, plugin-doctor (marketplace-wide), and whole-tree pytest all clean. A prior full `module-tests` run surfaced 5 failures (the retired-idiom guard on `doc_references.py`, and 4 resolver-roster assertions); both were fixed and the re-run is clean.

## Findings

**Verification sub-agent** (Step 6): dispatched (general-purpose, read-only). Verdict: all five deliverables PASS within the diff; tests appropriate; D4 purity confirmed; the `.svg`-resolves-to-`documentation` D5 claim confirmed against `lookup_claim`'s prefix-nesting. Findings and dispositions (each recorded per instance):
- **Stale resolver roster (hard, beyond-diff).** `ext-point-derivation-resolver.md` § Current implementations listed only `maven`/`markdown`/`python` and omitted the new `documentation` resolver — a false completeness claim (the table declares itself "the one place the shipped roster is enumerated"), the symmetric sibling of the path-attribution table the diff *did* update. *Disposition: fixed* — added the `documentation` resolver row and reconciled the "two resolvers, not one" framing to three.
- **Contradictory minimal example (minor, beyond-diff).** `extension-contract.md`'s "Minimal Extension (Skill-Only Domain)" named pm-documents, now the multi-axis exemplar. *Disposition: fixed* — de-identified the example to a generic skill-only bundle with a pointer to the real multi-axis pm-documents.
- **D4 anchor-form robustness caveat (residual).** `extract_anchors` did not cover the `anchor:id[]` inline-macro or `[id="id"]` block-attribute anchor forms, so a valid reference to such an anchor could be falsely flagged (absent from this corpus, hence the measured 0/803). *Disposition: fixed* — both forms now extracted (a new test pins them); the non-default `:idprefix:` heading remains a documented residual gap. Re-measured: still 0 unresolved over 803 references.
- **README.adoc fallback cost (observation, not a defect).** The fallback set the module path to `.`, which would have `rglob`-walked the whole project root for a doc-only-README project shape (does not trigger in this repo). *Disposition: fixed* — the fallback now roots at `doc`, matching the pre-change behaviour and avoiding the whole-root walk.
- **Cleared by the sweep (no change needed):** the synthetic resolver-roster asserts in `test_derivation_resolver_discovery.py` (monkeypatched fakes), the controlled-map producer asserts in `test_derivation_merge.py` / `test_graph_resolver_provenance.py`, and the deferring cross-references in `module-discovery.md` / `extension-contract.md` / `tools-marketplace-inventory/SKILL.md` (which point at the now-updated table). The live-roster pin `test_graph_family_bundle_project.py` was already updated in-diff.

A focused re-verification confirms the fixes (below).

**D4 reference-engine false-positive sweep (self-review during implementation).** The first engine reported **14 unresolved references** over the real corpus — all false positives from AsciiDoc conventions (auto-id `_where_things_live` vs GitHub slug, natural `<<Section Title>>` cross-refs, pure-id `xref:id[]` treated as files, references quoted in inline code). A false "dangling reference" is the misleading signal this substrate forbids, so the engine was made convention-tolerant (every heading contributes its AsciiDoc auto-id, GitHub slug, and raw-title forms; inline-code and fenced references are skipped; bare `xref:id[]` is resolved as an anchor). Re-measured: **0 unresolved over 803 real references** — the corpus has no dangling references the engine can confidently detect, so D4's positive test uses a deliberate-broken fixture.

**Build guard `test_prefix_strip_idiom_retired`** (from the full test run) — `doc_references.py` used the retired char-set `lstrip('./')` idiom, and later an explanatory comment still carried the literal. *Disposition: fixed* — replaced with `removeprefix('./')`; reworded the comment to avoid the scanned literal.

**Graph-family resolver-roster tests** (4, from the full test run) — adding the `documentation` resolver changed the shipped roster. *Disposition: fixed* — updated `EXPECTED_RESOLVER_IDS` and `AXIS_A_RESOLVER_IDS` to include `documentation`, and made `test_collapse_mechanism`'s edge-count assertion robust to an inert Axis-A resolver (asserts the markdown+python corroboration pair by id rather than pinning the exact report count).

**D2 consumer enumeration** (the deliverable's stated verification — "derive the population; do not sample"). The affected surfaces are the inventory readers `find` and `search --content` (both call `_collapse_claimed_duplicate_rows`). `which-module` returns a single best-match module and is not a duplication surface. Population derived by sweeping `find`/`search --content` invocations across the bundle tree and `.claude/`: every caller is one of three kinds — (a) the handlers themselves; (b) tests (`test_cmd_client`, `test_search_content`, `test_find_confident_negative`), which seed synthetic fixtures **without** a documentation attributor claim, so the collapse is a no-op (`owner: None`) there and they were unaffected by the full run; (c) **LLM/agent-facing guidance** — `persona-plan-marshall-agent`, `execute-task`, `manage-architecture` SKILL.md/standards — where an agent uses `find`/`search` interactively. **No programmatic consumer reads the result and de-dupes by path**, so the "double-correct" failure the plan warns of has no site to occur. Confirming that:
- The collapse is **claim-keyed and conservative**: it only alters rows for a path an Axis-D claim owns AND that appears in ≥2 modules' inventories. No unclaimed path — the entire marketplace corpus, all source/test/config — changes at all, so a consumer that de-dupes marketplace rows itself cannot double-correct (its inputs are unchanged).
- A single-rowed claimed path (a repo-root prose doc the doc module does not itself inventory) is left intact, so no claimed file vanishes.
- The only behavioural change is: a `doc/**` path that previously returned two rows (`default` + `documentation`) now returns one (`documentation`). No consumer was found that depends on the doubled doc row; the doubling was the defect this plan removes.

## Reviewer participation
_Pending._

## Cost
_Pending._

## Contract check (Step 9)
_Pending._

## What have we learned (Step 9)
_Pending._

## Residue
_Pending._

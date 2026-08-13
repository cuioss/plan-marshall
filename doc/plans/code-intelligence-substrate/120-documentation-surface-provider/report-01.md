# Run report — 120-documentation-surface-provider (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/documentation-surface-provider-u1d4fg` (harness-assigned)    **PR:** [#1201](https://github.com/cuioss/plan-marshall/pull/1201)    **Outcome:** completed (landing delegated — see Merge gate)

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

**Re-verification** (Step 6, second pass): **clean.** All four findings confirmed resolved against committed HEAD; the resolver table is complete and internally consistent (1 Axis-B + 3 Axis-A, matching `EXPECTED_RESOLVER_IDS` and the test docstring); the fixes introduced no new stale claim; a fresh roster/attributor sweep across `marketplace/bundles/**` and `doc/**` found no other non-synthetic stale enumeration (the union diagrams and `resolver_count: 2` example are mechanism illustrations without completeness claims; the discovery-test asserts are synthetic monkeypatched fakes). One **optional** consistency item surfaced and was **declined-with-reason**: `extension-architecture.adoc`'s one-line Axis-D example lists only the `plan-marshall` claims and omits the documentation claim — but it is a pre-existing illustrative example carrying no completeness wording, and D5 scoped the attribution-model addition to `code-intelligence.adoc`, so touching it would be scope creep into an unnamed file without closing a defect.

**D4 reference-engine false-positive sweep (self-review during implementation).** The first engine reported **14 unresolved references** over the real corpus — all false positives from AsciiDoc conventions (auto-id `_where_things_live` vs GitHub slug, natural `<<Section Title>>` cross-refs, pure-id `xref:id[]` treated as files, references quoted in inline code). A false "dangling reference" is the misleading signal this substrate forbids, so the engine was made convention-tolerant (every heading contributes its AsciiDoc auto-id, GitHub slug, and raw-title forms; inline-code and fenced references are skipped; bare `xref:id[]` is resolved as an anchor). Re-measured: **0 unresolved over 803 real references** — the corpus has no dangling references the engine can confidently detect, so D4's positive test uses a deliberate-broken fixture.

**Build guard `test_prefix_strip_idiom_retired`** (from the full test run) — `doc_references.py` used the retired char-set `lstrip('./')` idiom, and later an explanatory comment still carried the literal. *Disposition: fixed* — replaced with `removeprefix('./')`; reworded the comment to avoid the scanned literal.

**Graph-family resolver-roster tests** (4, from the full test run) — adding the `documentation` resolver changed the shipped roster. *Disposition: fixed* — updated `EXPECTED_RESOLVER_IDS` and `AXIS_A_RESOLVER_IDS` to include `documentation`, and made `test_collapse_mechanism`'s edge-count assertion robust to an inert Axis-A resolver (asserts the markdown+python corroboration pair by id rather than pinning the exact report count).

**D2 consumer enumeration** (the deliverable's stated verification — "derive the population; do not sample"). The affected surfaces are the inventory readers `find` and `search --content` (both call `_collapse_claimed_duplicate_rows`). `which-module` returns a single best-match module and is not a duplication surface. Population derived by sweeping `find`/`search --content` invocations across the bundle tree and `.claude/`: every caller is one of three kinds — (a) the handlers themselves; (b) tests (`test_cmd_client`, `test_search_content`, `test_find_confident_negative`), which seed synthetic fixtures **without** a documentation attributor claim, so the collapse is a no-op (`owner: None`) there and they were unaffected by the full run; (c) **LLM/agent-facing guidance** — `persona-plan-marshall-agent`, `execute-task`, `manage-architecture` SKILL.md/standards — where an agent uses `find`/`search` interactively. **No programmatic consumer reads the result and de-dupes by path**, so the "double-correct" failure the plan warns of has no site to occur. Confirming that:
- The collapse is **claim-keyed and conservative**: it only alters rows for a path an Axis-D claim owns AND that appears in ≥2 modules' inventories. No unclaimed path — the entire marketplace corpus, all source/test/config — changes at all, so a consumer that de-dupes marketplace rows itself cannot double-correct (its inputs are unchanged).
- A single-rowed claimed path (a repo-root prose doc the doc module does not itself inventory) is left intact, so no claimed file vanishes.
- The only behavioural change is: a `doc/**` path that previously returned two rows (`default` + `documentation`) now returns one (`documentation`). No consumer was found that depends on the doubled doc row; the doubling was the defect this plan removes.

**PR review — cuioss-review-bot security finding (path traversal / host-file read).** `_resolve_one` in `doc_references.py`: a cross-document reference whose target escapes `project_root` (e.g. `xref:../../../../etc/passwd#x[]`) fell through the `except ValueError` branch without returning, reaching `resolved_path.exists()` and `.read_text()` on a HOST path outside the repository — both a probe and an arbitrary host-file read, and a false "resolved" for an escaping target. *Disposition: fixed* (`a37f1d8`) — the branch now returns `(module, False)` before any filesystem access; two regression tests cover the fail-closed path (escaping target that exists outside the root, with/without anchor) and the end-to-end unresolved report. Replied on the PR thread confirming the fix.

## Reviewer participation

Expected reviewer population derived from the automatic-review registry (`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{coderabbit,sourcery,pr-agent}.md` `author_login`), cross-named by `.github/workflows/pr-agent.yml`:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted a "PR Reviewer Guide" with a security finding (path traversal in `_resolve_one`) against the diff — a real review artifact. Fixed and replied. |
| `coderabbitai` | `rate-limited` | Posted only "Review limit reached … Next review available in: 49 minutes" — engaged but did not review this diff. |
| `sourcery-ai` | `rate-limited` | Posted only "you have reached your weekly rate limit of 500000 diff characters" in place of a review. |

**Coverage: 1 of 3.** The § Step 8 shortfall disclosure fires — see Contract check / Merge gate. Rate limits are routine and outside our control; the merge is not blocked on them, but the shortfall is stated explicitly.

## Cost
- **Tokens:** not available to the agent in this session — the harness does not surface a per-run token count to the model.
- **Wall-clock:** the run spanned roughly one working session (UTC 2026-08-13, ~08:00 onward); the two `./pw verify` runs were ~7 min each and the CI `verify` a comparable duration.
- **Population:** this single Claude Code cloud session's usage as the harness counts it. ⛔ NOT comparable to a plan-marshall `metrics.toon` total, which counts an orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary that a single interactive cloud session does not share. No comparable figure is available, stated plainly rather than presenting a non-comparable number.

## Contract check (Step 9)

| Step | Verdict | Evidence |
|---|---|---|
| 1 Skills loaded | done | Named in § Skills loaded; bundle-path reads (plugin not installed in this cloud session). |
| 2 Branch | done | Harness-assigned `claude/documentation-surface-provider-u1d4fg` kept as-is; pushed to `origin` before any work. |
| 3 Plan directory | done | `doc/plans/code-intelligence-substrate/120-documentation-surface-provider/plan.md` exists and opens with the first-instruction block. |
| 4 Implement | done | Commits carry the `Co-Authored-By: Claude` trailer; all deliverables addressed. |
| 4 Per-commit gate | done | Every `*.py` commit was preceded by a clean `./pw quality-gate` (ruff `All checks passed`, mypy `Success: no issues`, SPDX passed). |
| 4 Pushed | done | No unpushed commit remains; each commit pushed immediately. |
| 5 Build gate | done | `*.py` changed → `./pw verify` → `verify: SUCCESS`, 19370 passed / 14 skipped (recorded in § Build gate). |
| 6 Verification sub-agent | done | Two passes; findings + dispositions in § Findings; re-verification clean. |
| 7 PR cycle | done | PR #1201 opened (no `skip-bot-review` — the diff touches skills/bundles, so it is reviewed as code); all comments dispositioned (§ Findings, § Reviewer participation). |
| 8 Merge gate | see § Merge gate | Conditions 1–3 met after CI green on the final head; auto-merge armed; landing delegated to the orchestrator's collect (this cloud session cannot self-wake — `subscribe_pr_activity` is approval-gated). |
| 8 Bridge | done | No status/ledger write outside this plan's own directory; the report carries the PR number and per-deliverable outcome. |
| 9 This check | done | This table. |
| 9 What have we learned | done | Below. |

GitHub access path: **GitHub MCP server** (cloud session). Branch form: **harness-assigned** `claude/*`. A `/sync-plugin-cache` is **not owed** — it is a machine-local build step a cloud run never performs or records (per the lane's Scope and precedence).

## Merge gate (Step 8)

- **Condition 1** (required contexts green on the head SHA): the required `verify` check must conclude success on the final head; on this merge-queue repo, arming auto-merge defers required-ness to the queue.
- **Condition 2** (every comment handled): the one actionable comment (cuioss-review-bot security finding) was fixed and replied to; the two rate-limit notices are not actionable.
- **Condition 3** (report finalized and pushed): this report is the last pre-merge commit.
- **Condition 4** (review-coverage shortfall — a DISCLOSURE, not a block): **Review coverage: 1 of 3 — `cuioss-review-bot` reviewed (one security finding, fixed); `coderabbitai` rate-limited (window reopens in ~49 min); `sourcery-ai` rate-limited (weekly diff-character quota).** Rate limits are routine and outside our control; the merge is not held for them, but the shortfall is stated.

The squash-merge commit SHA does not exist until the queue lands the PR, so it is reported to the operator from the PR merge event rather than embedded here.

## What have we learned (Step 9)

**No contract change proposed.** The `cloud-plan-lane` contract held end-to-end for a large, five-deliverable plan whose premise the clone refuted: its re-derivation mandate (claim-label table) is exactly what surfaced the "no `documentation` module" reality before any code was written; the reachable-operator escalation clause let a genuinely load-bearing design fork (make the module real vs. minimal seam-only) be settled by the operator rather than guessed; the pre-PR verification sub-agent caught a real stale-roster defect the implementer missed; and the merge-gate's disclose-don't-block rule for a review shortfall matched the rate-limited-reviewer reality precisely. Nothing in the contract was ambiguous in practice, produced an unobtainable artifact, or named a step that did not work in this environment. A run that examined the contract and found nothing to change is a different fact from one that never looked — this run looked.

## Residue

- **Landing confirmation** is delegated to the orchestrator's collect step (this cloud session cannot self-wake to watch the queue). The operator receives the `state: MERGED` / merge-commit read from the PR merge event.
- **A local `/sync-plugin-cache`** is owed on a developer machine before the edited `marketplace/bundles/` behaviour takes effect in an installed plugin cache (a local-developer concern, not a debt this cloud run performs).
- **D4 residual gap** (documented, not a defect): a heading under a non-default AsciiDoc `:idprefix:` is not resolved by the reference engine's anchor forms — under-reporting, never a false dangling report.
- **Optional consistency item declined:** `extension-architecture.adoc`'s one-line Axis-D example omits the new documentation claim (pre-existing, illustrative, outside D5's scoped files).

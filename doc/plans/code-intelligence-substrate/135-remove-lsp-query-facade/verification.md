# Verification — 135-remove-lsp-query-facade

**Audited:** `plan.md`, `report-01.md`, `rationale.md`
**Tree state:** `61a43e5` on `claude/code-intelligence-substrate-analysis-kah884`; re-verified at
`a90adeb`, which changes only `doc/plans/**` audit documents (`git diff --name-only 61a43e5 a90adeb`
has zero entries outside `doc/plans/`), so every source citation below still holds.
**Overall verdict:** CONFIRMED WITH GAPS

The removal itself is complete, surgical, and correct: every facade artefact named by the plan is gone
from the tree, the wrapped verbs are intact and green, the documented hazard was handled, and the run
introduced no collateral. The fifteen gaps recorded in `gaps.md` are (a) nine pre-existing
documentation defects in the same query-surface files — four surfaced by the run itself and deferred
(G3–G9), two found by this audit (G1, G11) — all still open, (b) two shipped-code follow-ups: the
vocabulary nit the plan named for itself (G2) and a stale handler-inventory docstring (G15), (c) one
missing plugin-doctor detector that is why the G4–G6 drift survived plans 130 and 135 both (G14),
(d) one forward-dangling cross-reference into this plan's own directory (G10), and (e) two minor
false claims confined to `report-01.md` (G12, G13). None is a regression caused by the removal.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D0 | GATE: re-derive removal surface, confirm zero consumers | "Consumer set empty → proceeded" | Whole-tree sweep at `61a43e5` for `cmd_lsp_` / `architecture … lsp` / the four verb names returns hits only in `doc/plans/…/130-*` and this plan's own records. PR #1214 changed exactly 13 files — the 10 Expected-surface files plus this plan's 3 own documents; no consumer needed migrating. | CONFIRMED |
| D1 | Retire the `lsp` command group (code + test) | "Removed … deleted `test_lsp_facade.py` … verbs unchanged" | No `lsp` subparser, no `cmd_lsp_*` import/dispatch/re-export/handler anywhere; `architecture.py lsp hover` is an argparse *invalid choice*; `test_lsp_facade.py` absent; 163 tests over the six wrapped-verb test files pass. | CONFIRMED |
| D2 | Remove the facade's documentation (surgical; one hazard) | "Deleted … excised … hazard handled" | `doc/developer/lsp-query-facade.adoc` absent; no `lsp`/facade string in `client-api.md`, `SKILL.md`, `code-intelligence.adoc`, `code-search.adoc`, `developer/README.adoc`; no dangling `xref:`/anchor; all five misfiled `search` paragraphs present under `### search`; plugin-doctor scoped run = `status: pass, total_issues: 0`. | CONFIRMED |
| D3 | Confirm the single-vocabulary invariant | "Full `./pw verify` green; orphan sweep clean" | Orphan sweep re-derived clean (see D0). `./pw verify` not re-run here (brief forbids); PR #1214 is `merged: true` through the merge queue, which re-verifies. | CONFIRMED (grep) / UNVERIFIABLE (full verify) |
| — | Operator-requested addition: `rationale.md` | "DONE, commit `2192f3f`" | `rationale.md` present (108 lines); commit `2192f3f5c826…` confirmed on PR #1214. Its factual claims re-checked against the tree — all hold. | CONFIRMED |

## Per-deliverable detail

### D0 — GATE: re-derive the removal surface and re-confirm zero consumers

- **Required (plan):** the current removal surface is re-listed from the clone **and** the consumer set
  is confirmed empty; halt on a non-empty consumer set.
- **Claimed (report):** "swept the whole tree for `cmd_lsp_` / `architecture lsp` / the four verb names;
  every hit was the plan's own records or the historical `130-*` records. Consumer set empty."
- **Found:** `git grep -n -I -E "cmd_lsp_|architecture …lsp |lsp (hover|references|workspace-symbol|definition)"`
  at `61a43e5` returns 21 lines, all inside `doc/plans/code-intelligence-substrate/130-lsp-shaped-query-api/report-01.md`
  and `…/135-remove-lsp-query-facade/{plan.md,rationale.md,report-01.md}`. Positive control: the same
  pattern family finds the historical text, so the negative is not a filtered false negative.
- **Checks run:** the git-grep sweep above; a case-insensitive `lsp` grep over the whole
  `manage-architecture` skill directory (zero hits); a `--exclude-dir=.git` grep over the working tree
  including hidden trees, with `.claude/` positive-controlled via `cloud-plan-lane` (2 hits) and then
  swept for `lsp` (0 hits); `target/` does not exist in this clone; `marketplace/targets/` carries no
  facade text.
- **Coverage gap found and closed by the adversarial pass.** A git-grep sweep cannot see the
  git-ignored `.plan/` tree, and this document originally justified that by asserting `.plan/` does
  not exist in this clone. **It does** — it carries `execute-script.py`, `marshal.json`,
  `project-architecture/`, `temp/`, and `local/`. The generated executor is the one consumer surface
  a verb removal can leave stale, so it was swept directly: `grep -ci "cmd_lsp_|lsp hover|lsp
  workspace-symbol" .plan/execute-script.py` → **0**, and `grep -rli "cmd_lsp_" .plan/` → no files.
  The negative therefore now covers the gitignored surface as well, not only the tracked one.
- **Verdict:** CONFIRMED. The absence claim — the plan's own highest-risk claim — holds, and the PR's
  13-file footprint independently corroborates it: had a consumer existed, a fourteenth file would have
  had to change.

### D1 — Retire the `lsp` command group (code + test)

- **Required (plan):** `architecture … lsp hover` (and the other three) exits with an argparse *invalid
  choice* error; the four wrapped verbs answer identically to before; `./pw quality-gate` and the
  `manage-architecture` test module are clean.
- **Claimed (report):** the argparse group, four handlers, imports, dispatch and re-exports removed;
  `test_lsp_facade.py` deleted; wrapped verbs unchanged.
- **Found:**
  - `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/architecture.py:518-544` —
    the `handlers` dict carries 25 verbs, none of them `lsp`; `architecture.py:546-561` has exactly one
    group branch (`enrich`) and no `elif args.command == 'lsp'`.
  - `.../scripts/_cmd_client.py:72-105` — the `_cmd_client_handlers` re-export block lists 32 names,
    of which 20 are `cmd_*` handlers and 12 are private helpers; no `cmd_lsp_*` among them.
  - `.../scripts/_cmd_client_handlers.py` — 20 `def cmd_*` definitions, no `cmd_lsp_*`; no section
    banner or pointer comment survives.
  - `test/plan-marshall/manage-architecture/` — 34 files, `test_lsp_facade.py` not among them.
- **Checks run:**
  - Invoked the CLI directly with every marketplace `scripts/` dir on `PYTHONPATH`:
    `python3 …/architecture.py lsp hover --module x` →
    `error: argument command: invalid choice: 'lsp' (choose from 'discover', …, 'enrich')`. The literal
    *Done when* is met. The `choices` list argparse prints holds 26 entries — the 25 verbs of the
    `handlers` dict plus the `enrich` group.
  - Re-checked through the **second** dispatch surface, the generated executor (which does exist in
    this clone — see D0's coverage note): `python3 .plan/execute-script.py
    plan-marshall:manage-architecture:architecture lsp hover --module x` → `reason: unknown_verb`,
    `rejected: lsp`, with a 26-entry `accepted` list carrying no `lsp`. Two independent registries
    agree the verb is gone, so the *Done when* does not rest on argparse alone.
  - `uv run python -m pytest test_graph_queries.py test_cmd_resolve.py test_capabilities.py
    test_search_content.py test_feasibility_underivable_guard.py test_cmd_client.py -o addopts=""` →
    **163 passed** (re-run at `a90adeb`: 163 passed in 4.61s).
  - **The whole `manage-architecture` test module** — `uv run python -m pytest . -o addopts=""` →
    **573 passed in 26.50s** at `a90adeb`. This is the population the plan's Verification section
    actually names (it lists `test_architecture_input_validation.py` and "the `find`/`which-module`/
    `module` tests", none of which were in the six-file run above), so the six-file run alone did not
    discharge it. The 573-test run does.
  - `uv run ruff check` over the three edited scripts → "All checks passed!" (a deletion of this shape
    can strand an unused import; none was stranded).
  - Independent coverage census for the verbs the deleted test also touched: `cmd_impact` →
    `test_cmd_client.py` + `test_graph_queries.py`; `cmd_find` → `test_cmd_client.py`,
    `test_find_confident_negative.py`, `test_search_content.py`; `cmd_path` → `test_cmd_client.py` +
    `test_graph_queries.py`; `cmd_module` → `test_cmd_client.py`, `test_overview.py`; `cmd_resolve` →
    `test_cmd_client.py`, `test_cmd_resolve.py`, `test_on_demand_crawl.py`; `cmd_which_module` (which
    the deleted residue case also exercised, and which this census originally omitted) →
    `test_which_module_plan_claim.py`, `test_cmd_client.py`, `test_files_inventory.py`,
    `test_find_confident_negative.py`. The plan's claim that
    `test_residue_verbs_remain_reachable_unchanged` was redundant is true — deleting the facade test
    cost no verb its coverage.
  - Read the deleted file's assertions from the PR patch: six test functions — `test_lsp_hover_…`,
    `test_lsp_references_equals_impact`, `test_lsp_workspace_symbol_equals_find`,
    `test_lsp_definition_equals_resolve`, `test_cli_speaks_lsp_vocabulary`,
    `test_residue_verbs_remain_reachable_unchanged`. **Four** carry the `assert facade == direct`
    equality assertion; the fifth (`test_cli_speaks_lsp_vocabulary`) runs the shipped CLI with
    `'lsp', 'hover'` and asserts `status == 'success'`, which is facade-only but not an equality
    assertion; the sixth is the residue-reachability case over `impact`/`find`/`which-module`/`path`.
    100 % facade, as the plan stated.
- **Verdict:** CONFIRMED.

### D2 — Remove the facade's documentation (surgical; one hazard)

- **Required (plan):** no live document mentions the `lsp` facade; no dangling `xref:`/name-anchor
  remains anywhere; the misplaced `search` content survives; plugin-doctor is clean.
- **Claimed (report):** all six documentation sites excised, every dangling `xref` pruned, and the
  misfiled search paragraphs **relocated** under `### search`.
- **Found:**
  - `doc/developer/lsp-query-facade.adoc` — absent (`ls` → No such file).
  - `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md:554-574` —
    the Command Summary table carries **17** verb rows (558-574), no facade row; no `## LSP-shaped
    query facade` heading (H2 list is `Script Pattern`, `Commands`, `Resolver provenance (the graph
    family)`, `Command Summary`, `Error Handling`, `Consumer View`, `Data Source`).
  - `…/manage-architecture/SKILL.md:36-49` — Command Groups table has no `lsp` row; the H3 census
    contains no `### lsp`, and exactly one `### capabilities` (line 538).
  - `doc/concepts/code-intelligence.adoc` — no `== The query vocabulary…` section; the Related list
    (303-314) has no `lsp-query-facade.adoc` xref.
  - `doc/user/code-search.adoc` — no `== The same verbs, in LSP vocabulary`; section list runs
    `…Asking what the substrate can answer here` (189) → `Why this verb exists` (200) → `Related` (206).
  - `doc/developer/README.adoc:12-19` (the `== Pages` list) — no `lsp-query-facade.adoc` bullet.
  - **Hazard:** `SKILL.md:528-536` carries all five paragraphs under `### search` (509) —
    "**Anchors are per line**" (528), "**Payload boundary**" (530), "**Inventory-scope boundary**" (532),
    "**Zero-result semantics**" (534), "See client-api.md § search" (536) — with `### capabilities` now
    at 538. Nothing was duplicated: "Anchors are per line" and "Payload boundary" each occur once;
    "Zero-result semantics" occurs twice, but the second (479) is the pre-existing `files`-verb
    paragraph, not a copy.
- **Checks run:** a whole-tree grep for `lsp-query-facade`, `LSP-shaped`, `LSP vocabulary`,
  `query vocabulary`, `test_lsp_facade` over all file types, excluding `doc/plans/` — zero hits;
  positive-controlled by re-running without the exclusion, which returns the historical plan-130 and
  plan-240 records. `doctor-marketplace.py quality-gate --paths …/manage-architecture` →
  `status: pass`, `total_issues: 0`, `rules_run[36]` (re-run at `a90adeb`, identical).
- **Checked in the reverse direction too** (the *Done when* is bidirectional — "no dangling
  `xref:`/name-anchor **anywhere**", not merely "no facade text in the edited files"):
  - Forward: every relative `xref:` / `link:` / markdown link **out of** the five edited documents
    resolves to an existing file — 0 missing targets.
  - Reverse: a whole-tree sweep of every tracked `.md`/`.adoc` outside `doc/plans/` for anchored
    links **into** those five documents, resolving each fragment against the target's live heading
    set — **0 dangling anchors**. Nothing anywhere pointed at a heading the removal deleted.
- **Note on mechanism:** the PR patch shows the search paragraphs were *not themselves moved* — the run
  deleted the `### capabilities` block from above them and re-added it below them, and deleted `### lsp`.
  The end state is exactly what the plan required (the paragraphs sit under `### search`), so the *Done
  when* is met literally; the report's word "relocated" describes the outcome rather than the edit.
- **Verdict:** CONFIRMED.

### D3 — Confirm the single-vocabulary invariant

- **Required (plan):** `./pw verify` green **and** a whole-tree grep whose only surviving hits are the
  historical plan-130 records.
- **Claimed (report):** "Full `./pw verify` green; whole-tree orphan sweep clean", with 19497 passed /
  14 skipped in the Build gate section.
- **Found:** the grep half is CONFIRMED (see D0) with the expected widening that this plan's own three
  records also match — which the report states accurately. The `./pw verify` half is **UNVERIFIABLE
  here**: the audit brief forbids running the full suite. Corroborating evidence short of re-running it:
  PR #1214 is `merged: true` (merged 2026-08-13T17:36:20Z by `cuioss-oliver`) through a merge queue that
  re-verifies on `merge_group`; the targeted 163-test run, the scoped plugin-doctor gate, and ruff over
  the three edited scripts are all green at `61a43e5`.
- **Verdict:** CONFIRMED for the invariant grep; the full-verify assertion is UNVERIFIABLE-but-corroborated.

### Out-of-scope carve-outs — all respected

- **No verb renamed.** `module`, `impact`, `find`, `resolve` all present in `architecture.py:518-544`
  with unchanged names and handlers.
- **The real `lsp-client` subsystem untouched.** `marketplace/bundles/plan-marshall/skills/lsp-client/`
  (SKILL.md + 3 scripts), `manage-run-config` language-server settings,
  `doc/user/lsp-code-intelligence.adoc`, and `test/plan-marshall/lsp-client/` (4 test files) all present;
  none appears in the PR's 13-file change set. This was the plan's named highest-risk confusion, and it
  did not occur.
- **Plan 130's kept behaviour survives.** `cmd_capabilities` at `_cmd_client_handlers.py:142`; the
  refine `UNDERIVABLE` guard at
  `marketplace/bundles/plan-marshall/skills/phase-2-refine/standards/refine-workflow-detail.md:495`;
  `--ignore-case` / `file_count` documented at `client-api.md:934,1024` and exercised by
  `test_search_content.py` (in the passing 163).
- **Historical plan-130 records untouched** — `doc/plans/…/130-lsp-shaped-query-api/` is not in the PR's
  file list.
- **The `capabilities` vocabulary nit** was correctly left alone (see G2), matching the carve-out.

## Correctness review

I read `architecture.py:1-573` (parser construction, routing helper, handler table, dispatch),
`_cmd_client.py:41-140` (the re-export facade and its stale-module purge), and
`_cmd_client_handlers.py:142-250` (`cmd_capabilities`, the nearest neighbour to the deleted region),
plus every hunk of the PR patch for the three scripts.

**No defect was introduced by this change.** Specifically:

- No orphaned reference to `args.lsp_method` or to any `cmd_lsp_*` name survives, so no branch became
  unreachable and no lookup can raise `AttributeError`.
- The dispatch fallback is unchanged: an unknown `args.command` still falls through to
  `parser.print_help()` and `return 1` (`architecture.py:570-572`) — the removal did not turn an
  unknown verb into a silent success.
- No shared helper was stranded. `add_module_arg`, used by the deleted `lsp hover`/`references`/
  `definition` parsers, is still used by the surviving verb parsers; ruff reports no unused import.
- The deletion was purely subtractive in the scripts (`-59`, `-4`, `-81` lines, zero additions), so no
  new logic entered the query path.

Two pre-existing inconsistencies, **neither** caused by this run, remain live in the files it edited:

1. **The `capabilities` status vocabulary** (explicitly carved out of this plan). `cmd_capabilities`
   emits `status: 'available' / 'unavailable'` for the `content_search` entry
   (`_cmd_client_handlers.py:246`) while the other two entries emit `derivable` / `not_derivable`
   (lines 231, 239). The `§ capabilities` contract documents this split correctly at
   `client-api.md:1392-1393`, but two surfaces above it do not: the entry-shape table at
   `client-api.md:1386-1390` and the **Command Summary** row at `client-api.md:572`, which promises
   `derivable`/`not_derivable` for all three including content search. The Command Summary row is a
   false statement in shipped documentation (G1); the underlying split is the nit itself (G2). The
   handler's own docstring (`_cmd_client_handlers.py:172-176`) makes the same over-general claim, so
   the contradiction is in the code as well as the docs — folded into G2's action list.
2. **A stale hand-maintained mirror in the edited file's module docstring.**
   `_cmd_client_handlers.py:6-11` enumerates 19 handler names while the file defines 20
   `def cmd_*` functions; the omission is `cmd_capabilities` (line 142). PR #1214's patch for this
   file touches only the import block and the deleted 645-731 region, never the docstring, so this
   dates from plan 130. Filed as G15, and it is a second instance of the mirror-drift class G14
   exists to detect.

## Test adequacy

| Deliverable | Covering tests | Status |
|---|---|---|
| D1 — wrapped verbs unchanged | `test_graph_queries.py` (`cmd_graph`/`path`/`neighbors`/`impact`), `test_cmd_resolve.py`, `test_cmd_client.py`, `test_find_confident_negative.py`, `test_overview.py`, `test_architecture_input_validation.py`, `test_which_module_plan_claim.py`, `test_files_inventory.py` | **573 passed** over the whole `manage-architecture` module at `a90adeb` (superseding the earlier six-file, 163-test run, which did not include the last three files this row names). PR #1214 modified none of them, so their passing is genuine evidence that only the facade moved — and the mutation sweep below shows the coverage is not vacuous |
| D1 — `lsp` no longer parses | none — asserted by direct CLI invocation here | No regression test guards re-introduction. Not warranted: re-adding the group would require re-adding a parser block, which no existing test would silently permit but which also nothing detects. Recorded as an observation, not a gap — a "verb X must not exist" test is a poor guard shape |
| D2 — search docs intact | `plugin-doctor quality-gate` (36 rules, structural lint over `SKILL.md`/`client-api.md`) | Clean, but see below |
| Kept plan-130 behaviour | `test_capabilities.py`, `test_search_content.py`, `test_feasibility_underivable_guard.py` | All in the passing 163 |

**No vacuous test was found, and no mutation sweep was needed**, because this plan added no production
logic: it is a deletion whose *Done when* conditions are observable directly (an argparse error, an
absent file, an absent string). I therefore mutated nothing and took no byte snapshot; `git status
--porcelain` shows no modification to any production or test file by this audit.

**One genuine test/lint gap** is visible from the doctor run: none of the 36 marketplace rules compares
the argparse verb set against what `SKILL.md` and `client-api.md` document. A census I ran directly
(argparse `add_parser` names vs `### ` headings vs the Command Summary rows) shows `siblings` and
`profiles` documented in `SKILL.md` but contracted nowhere, and `descriptor-regression-check` contracted
in `client-api.md` but absent from both `SKILL.md` surfaces. The doctor passing clean while that drift
exists is why the drift survived plan 130 and plan 135 both (G4–G6).

## Report accuracy

Every substantive claim in `report-01.md` was checked against the tree at `61a43e5` and against
PR #1214 via the GitHub API. **The deliverable table, the removal inventory, the hazard claim, the
kept-behaviour claim, the orphan-sweep claim, the four deferred findings, and the reviewer verdicts all
hold.** Two claims do not, and two more are imprecise:

1. **False.** Contract check row "4 Implement": *"every commit carries the `Co-Authored-By: Claude`
   trailer"*. PR #1214 has five commits; the first — `8c490a91b963…` *"docs(plans): add plan 135 — remove
   the LSP-shaped query facade"* — carries **no** `Co-Authored-By` trailer. The other four
   (`9e469268`, `cfc4aad`, `2192f3f`, `39ffbf66`) do. (G12)
2. **Misquoted figure.** § Findings and § Reviewer participation quote coderabbit as *"Review limit
   reached — next review available in 107 minutes."* The comment on the PR
   (`#issuecomment-5283902511`, updated 2026-08-13T17:10:15Z) reads **"Next review available in: 103
   minutes"**. The comment's `updated_at` is later than its `created_at`, so the bot may have rewritten
   the figure after the report was drafted; either way the report's quotation does not match the
   artifact it cites. (G13)
3. **Imprecise, outcome correct.** *"the search-verb paragraphs misfiled under `### lsp` … were
   **relocated** under `### search`"*. The diff shows the paragraphs stayed put and the `### capabilities`
   heading was moved below them. The required end state — search content under `### search` — is what the
   tree has, so this is a description of mechanism, not a false outcome. No gap raised.
4. **Line number drifted.** Finding 3 cites `doc/concepts/code-intelligence.adoc:34`; the sentence now
   sits at **line 36**. The claim itself is true (see G7). Line drift in a dated record is expected and
   is not raised as a gap.

Claims I could **not** verify: the build-gate figures (*"19497 passed, 14 skipped"*, *"mypy production
[396] + test [726]"*, *"351s"*) — running `./pw verify` is outside this audit's remit; and the
sub-agent `subagent_tokens` self-reports, which leave no artifact in the tree. Both are recorded as
UNVERIFIABLE, not as passes.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| **Landing confirmation** — auto-merge armed on #1214, `state: MERGED` read delegated | **CLOSED** | GitHub API: PR #1214 `"merged": true`, `"merged_at": "2026-08-13T17:36:20Z"`, `merged_by: cuioss-oliver`; the facade is absent from `main`-descended `61a43e5` |
| **Pre-existing doc-hygiene: `client-api.md` H2/H3 hierarchy break** | **STILL OPEN** | `client-api.md`: last H2 before the tail is `## Error Handling` (580); the H3 sections `files` (606), `which-module` (712), `find` (817), `search` (909), `diff-modules` (1144), `descriptor-regression-check` (1284), `capabilities` (1356) all render under it — seven, exactly as reported. (G3) |
| **Pre-existing doc-hygiene: `SKILL.md` ↔ `client-api.md` verb-set drift** | **STILL OPEN** | `grep -c siblings client-api.md` → 0; `profiles` appears once (540) and only inside the `resolve` `mutating` prose, never as a verb; `grep -c descriptor-regression-check SKILL.md` → 0. (G4, G5, G6) |
| **Pre-existing doc-hygiene: `info` adjacency overstatement** | **STILL OPEN** | `doc/concepts/code-intelligence.adoc:36` — "plus the adjacency surfaces of `overview` and `module` / `info`"; `client-api.md:22-52` shows `info` returning `project` / `technologies` / `modules{name,path,purpose,description,freshness}` with no edge or dependency field, while `module` (`client-api.md:346` region) does carry `internal_dependencies`. (G7) |
| **Pre-existing doc-hygiene: intra-doc duplication in `client-api.md § search`** | **STILL OPEN** | `--ignore-case`/`--literal` composition stated at 941-946 and again at 1111-1116; `count` vs `file_count` at 1034-1038 and again at 1117-1120. (G8, G9) |
| **Rationale's permanent home** — promote to an ADR or concepts note if it should outlive collect | **STILL OPEN** | `doc/adr/` holds 17 ADRs, none about LSP conformance or the query vocabulary; no concepts page carries the argument. `rationale.md` still lives only in the plan directory. (G10, G11) |
| **No orchestrator parent** | **N/A — correct as recorded** | Nothing to transition; `.plan/` does not exist in this clone. No action possible or needed |

## Out-of-scope and collateral

**None.** PR #1214 touched exactly 13 files: the 8 surgical + 2 wholesale-delete files named under
**Expected surface**, plus this plan's own `plan.md`, `rationale.md`, `report-01.md`. The `+434 / −509`
split is fully accounted for by the three added plan documents (+232/+108/+86 = +426) and the SKILL.md
relocation (+8). Nothing on the plan's **Do NOT touch** list appears in the change set, and no
`uv.lock` churn is present.

One item the run added beyond the plan's four deliverables — `rationale.md` — is declared in the report
as an operator-requested addition and is a plan-directory document, not production surface. It is
therefore not undeclared collateral.

## Method and coverage

**Checked, with the command:**

- Whole-tree facade sweep — `git grep` over tracked files, plus `grep -rn --exclude-dir=.git` over the
  working tree including `.claude/`; each negative positive-controlled first.
- CLI behaviour — `architecture.py lsp hover --module x` with all marketplace `scripts/` directories on
  `PYTHONPATH` (the `.plan/` executor does not exist in this clone).
- Tests — `uv run python -m pytest` over the six `manage-architecture` test files that cover the wrapped
  verbs and the kept plan-130 behaviour: 163 passed, 21.24s.
- Lint — `uv run ruff check` over the three edited scripts; `doctor-marketplace.py quality-gate --paths
  marketplace/bundles/plan-marshall/skills/manage-architecture` (36 rules, 0 findings).
- Documentation state — read `SKILL.md` 36-49 and 498-556, `client-api.md` 22-52, 554-585, 909-1130,
  1356-1440, `code-intelligence.adoc` 28-44 and 300-314, `code-search.adoc` structure, `README.adoc`
  index.
- Verb census — a script comparing `add_parser` names against `### ` headings in both docs and against
  the Command Summary rows.
- Run history — GitHub API on PR #1214: `get`, `get_files` (13 files with patches), `get_commits` (5),
  `get_reviews` (1), `get_comments` (2).

**Not checked, and why:**

- `./pw verify` was not run — the audit brief forbids it. The report's suite counts are therefore
  UNVERIFIABLE, mitigated by the merge-queue-verified merge and the targeted runs above.
- Git history before the shallow boundary is unavailable: this clone is shallow (`git rev-list --count
  HEAD` → 50, `.git/shallow` present), and `git fetch --deepen` failed on an existing `index.lock` held
  by another process, which I did not remove. Commit-level claims were therefore verified through the
  GitHub API instead of local history, which is strictly better evidence for a squash-merged PR.
- The two pre-PR sub-agents' internal transcripts and token self-reports leave no artifact; only their
  conclusions could be re-derived, and each conclusion I could re-derive held.

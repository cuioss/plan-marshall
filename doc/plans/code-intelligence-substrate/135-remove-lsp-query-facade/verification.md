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
| Kept plan-130 behaviour | `test_capabilities.py`, `test_search_content.py`, `test_feasibility_underivable_guard.py` | All in the passing 573 |

**Mutation sweep — the wrapped-verb coverage is non-vacuous.** This plan added no production logic, so
the original audit reasoned that a sweep was unnecessary. That reasoning is incomplete: the *evidence*
for "the wrapped verbs are unchanged" is a set of passing tests, and a passing test is only evidence if
it could have come back red. The sweep was therefore run:

- Byte snapshot of `_cmd_client_handlers.py` taken to `$TMPDIR/adv-135-remove-lsp-query-facade-mutsweep/`
  (md5 `05f5f620…`).
- Mutation: `cmd_impact` line 648, `'impact': impact` → `'impact': []` — the reverse-dependency closure
  the deleted `lsp references` facade wrapped.
- `uv run python -m pytest test_graph_queries.py` → **2 failed, 30 passed**
  (`test_cmd_impact_returns_shape`, `test_argparse_wiring_impact_subcommand`). **RED as required.**
- File written back from the snapshot; md5 re-matches `05f5f620…`, and `git status --porcelain` lists
  no modification to it. (Two unrelated `plan-retrospective/scripts/` files are modified in this tree
  by concurrent agents; neither was touched here.)

**One genuine detector gap** is visible from the doctor run: none of the 36 marketplace rules compares
the argparse verb set against what `SKILL.md` and `client-api.md` document — and the two nearest rules
do something else (`canonical-enum-choices-drift` checks a **flag enum** against `choices=`;
`literal-count-drift` checks an **integer count** against a derived population). A census run directly
(argparse `add_parser` names vs `### ` headings vs the Command Summary rows) shows `siblings` and
`profiles` documented in `SKILL.md` but contracted nowhere, and `descriptor-regression-check` contracted
in `client-api.md` but absent from both `SKILL.md` surfaces. The doctor passing clean while that drift
exists is why the drift survived plan 130 and plan 135 both — filed as **G14**, with the drift instances
themselves as G4–G6 and a third instance of the same mirror class as G15.

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
5. **Surface misnamed, verdict correct.** § Reviewer participation attributes `cuioss-review-bot`'s
   verdict to its *"'PR Reviewer Guide' review body"*. The GitHub API returns exactly **one** review on
   #1214 and it is `sourcery-ai`'s rate-limit notice; `cuioss-review-bot`'s "No major issues detected"
   is an **issue comment** (`#issuecomment-5283908171`), not a review. Both quoted strings are verbatim
   and the `reviewed` verdict is substantively right, so this is a misnamed surface rather than a false
   claim. No gap raised.

Verified verbatim against the artifacts: `sourcery-ai`'s *"you have reached your weekly rate limit of
500000 diff characters"* (review `4929635423`); `cuioss-review-bot`'s *"No major issues detected"* /
*"No security concerns identified"*; PR #1214's file list (13 files) and `+434 / −509` split, which
reconciles exactly as this document states (232+108+86+8 = 434 added; 36+1+80+4+24+4+81+59+47+173 = 509
deleted).

Claims I could **not** verify: the build-gate figures (*"19497 passed, 14 skipped"*, *"mypy production
[396] + test [726]"*, *"351s"*) — running `./pw verify` is outside this audit's remit; and the
sub-agent `subagent_tokens` self-reports, which leave no artifact in the tree. Both are recorded as
UNVERIFIABLE, not as passes. A scoped `uv run mypy` over the three edited scripts was attempted and is
**not** reported here: outside the pyprojectx envelope it cannot resolve the cross-skill `MYPYPATH`
entries and reports import-not-found errors that are artifacts of the invocation, not of the shipped
state. The type-check half of the gate therefore remains UNVERIFIABLE, corroborated only by the
merge-queue-verified merge.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| **Landing confirmation** — auto-merge armed on #1214, `state: MERGED` read delegated | **CLOSED** | GitHub API: PR #1214 `"merged": true`, `"merged_at": "2026-08-13T17:36:20Z"`, `merged_by: cuioss-oliver`; the facade is absent from `main`-descended `61a43e5` |
| **Pre-existing doc-hygiene: `client-api.md` H2/H3 hierarchy break** | **STILL OPEN — and wider than reported** | `client-api.md`: the H3 sections `files` (606), `which-module` (712), `find` (817), `search` (909), `diff-modules` (1144), `descriptor-regression-check` (1284), `capabilities` (1356) render under `## Error Handling` (580) — seven, exactly as reported. Four **more** the report did not name — `module` (309), `overview` (449), `commands` (488), `resolve` (515) — render under `## Resolver provenance (the graph family)` (90), whose own opening sentence scopes it to "the four graph-family verbs". Only 2 of the document's 17 verb sections (`info` 22, `modules` 55) sit under `## Commands`. (G3) |
| **Pre-existing doc-hygiene: `SKILL.md` ↔ `client-api.md` verb-set drift** | **STILL OPEN** | `grep -c siblings client-api.md` → 0; `profiles` appears once (540) and only inside the `resolve` `mutating` prose, never as a verb; `grep -c descriptor-regression-check SKILL.md` → 0. (G4, G5, G6) |
| **Pre-existing doc-hygiene: `info` adjacency overstatement** | **STILL OPEN** | `doc/concepts/code-intelligence.adoc:36` — "plus the adjacency surfaces of `overview` and `module` / `info`"; `client-api.md:22-52` shows `info` returning `project` / `technologies` / `modules{name,path,purpose,description,freshness}` with no edge or dependency field, while `module` (`client-api.md:346` region) does carry `internal_dependencies`. (G7) |
| **Pre-existing doc-hygiene: intra-doc duplication in `client-api.md § search`** | **STILL OPEN** | `--ignore-case`/`--literal` composition stated at 936-947 and again at 1111-1116; `count` vs `file_count` at 1034-1040 and again at 1117-1121. (G8, G9) |
| **Rationale's permanent home** — promote to an ADR or concepts note if it should outlive collect | **STILL OPEN** | `doc/adr/` holds 17 ADRs, none about LSP conformance or the query vocabulary; no concepts page carries the argument. `rationale.md` still lives only in the plan directory. (G10, G11) |
| **No orchestrator parent** | **N/A — correct as recorded** | Nothing to transition. Evidence corrected: `.plan/` **does** exist in this clone (`execute-script.py`, `marshal.json`, `project-architecture/`, `temp/`, `local/`), but `.plan/local/` holds only `logs/` and `marshall-state.toon` — there is no `orchestrator/` directory and so no parent plan spec. Note that this local state belongs to the audit machine, not to the cloud session that ran plan 135, which genuinely had no `.plan/` at all; the report's claim is about that session and stands |

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
  `PYTHONPATH`, **and** the same call through `.plan/execute-script.py` (the generated executor does
  exist in this clone; the original "it does not" was wrong). Both registries reject `lsp`.
- Tests — `uv run python -m pytest` over the six `manage-architecture` test files that cover the wrapped
  verbs and the kept plan-130 behaviour (163 passed), then over the **whole** `manage-architecture`
  module (573 passed, 26.50s), which is the population the plan's Verification section names.
- Mutation sweep — `cmd_impact` mutated to return `[]`; `test_graph_queries.py` went red (2 failed);
  the file restored from a byte snapshot and md5-verified.
- Lint — `uv run ruff check` over the three edited scripts; `doctor-marketplace.py quality-gate --paths
  marketplace/bundles/plan-marshall/skills/manage-architecture` (36 rules, 0 findings).
- Documentation state — read `SKILL.md` 36-49 and 498-556, `client-api.md` 22-52, 554-585, 909-1130,
  1356-1440, `code-intelligence.adoc` 28-44 and 300-314, `code-search.adoc` structure, `README.adoc`
  index.
- Verb census — a script comparing `add_parser` names against `### ` headings in both docs and against
  the Command Summary rows.
- Link integrity, both directions — every relative link out of the five edited documents resolved
  against the filesystem (0 missing), and every anchored link into them from any tracked `.md`/`.adoc`
  outside `doc/plans/` resolved against their live heading sets (0 dangling).
- Gitignored surfaces — `.plan/execute-script.py` and the whole `.plan/` tree swept for `cmd_lsp_` and
  the facade invocation forms (0 hits); `.claude/` swept case-insensitively for `lsp` (0 files);
  `target/` absent; `marketplace/targets/` carries no facade text.
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

## Adversarial review

Independent review of this document and `gaps.md`. Attacks run: A1 false positives, A2 false
negatives, A3 vacuous evidence, A4 counts and quotes, A5 actionability, A6 severity/topic,
A7 coverage, A8 internal consistency.

Re-derived at `a90adeb`, after confirming `git diff --name-only 61a43e5 a90adeb` touches nothing
outside `doc/plans/**`, so every source citation the original audit made was still checkable as
written.

| # | Attack | What was found | Correction applied |
|---|---|---|---|
| A1 | False positives | **No gap was invented.** All thirteen filed gaps were re-derived at their cited paths and every one is real: G1 (`client-api.md` Command Summary vs `_cmd_client_handlers.py:246`), G2 (lines 231/239/246 read), G3, G4 (`grep -c siblings client-api.md` → 0), G5 (`profiles` occurs once, at 540, inside the `resolve` `mutating` prose), G6 (`grep -c descriptor-regression-check SKILL.md` → 0), G7, G8, G9, G10 (link present at `proposal-protocol-surface.md:45-46`), G11 (`doc/adr/` holds 17 ADRs, none on the query vocabulary), G12 and G13 (both re-confirmed against the GitHub API). **Six citations were stale or truncated**, and one supporting claim inside a gap was outright false | Retargeted G1 `571`→`572` (two places) and G6 `577`→`574` — the Command Summary table is 17 rows at 558-574, not 18 at 554-577; G2's `1391-1392`→`1392-1393`, its TOON payload rows `1404/1416`→`1403/1414`, and `code-search.adoc:199`→`198`; G8's `941-946`→`936-947`; G9's `1034-1038`→`1034-1040` and `1117-1120`→`1117-1121`. **G10's premise "plan 240 is queued, not yet run" is false** — plan 240 ran 2026-08-15/16 and landed as PR #1256 (`240-skill-lsp-server/report-01.md:3`); the false framing was struck and the gap re-argued on what survives it |
| A2 | False negatives | Two CONFIRMED verdicts rested on narrower evidence than they claimed, and one method note was factually wrong. **(a)** D1's evidence was a six-file, 163-test run, but the plan's Verification section names `test_architecture_input_validation.py` and "the `find`/`which-module`/`module` tests", none of which were in it — and the Test-adequacy table cited files it had never run. **(b)** The audit asserted "`.plan/` does not exist in this clone" and used that to justify not sweeping the gitignored tree. `.plan/` **does** exist, and its `execute-script.py` is the one consumer surface a verb removal can leave stale. **(c)** G3's evidence counted seven mis-parented verb sections; there are **eleven** — `module` (309), `overview` (449), `commands` (488) and `resolve` (515) also render under `## Resolver provenance (the graph family)`, an H2 whose own opening sentence scopes it to "the four graph-family verbs". Only 2 of 17 verb sections sit under `## Commands`. **(d)** A stale hand-maintained mirror in a file this plan edited: `_cmd_client_handlers.py:6-11` lists 19 handlers, the file defines 20, `cmd_capabilities` omitted. The verdicts themselves survive: the removal is genuinely complete | Ran the whole `manage-architecture` module — **573 passed** — and rewrote the D1 evidence and Test-adequacy row around it; swept `.plan/` directly (`cmd_lsp_` → 0 hits) and re-invoked `lsp hover` through `.plan/execute-script.py`, which rejects it with `reason: unknown_verb` — a second independent registry confirming D1; widened G3's evidence, action and *Done when* to all eleven sections and corrected the residue-table row; filed the docstring drift as **G15** and folded the handler's own over-general docstring (`172-176`) into G2's action list |
| A3 | Vacuous evidence | The audit declared "**no mutation sweep was needed**" because the plan added no production logic. That reasoning is incomplete: the evidence for "the wrapped verbs are unchanged" is a set of passing tests, and a passing test is evidence only if it could have come back red. Nothing in the document established that. The plugin-doctor claim was re-run rather than re-read (`status: pass`, `total_issues: 0`, `rules_run[36]` — identical), as was the 163-test run (163 passed) | Ran the sweep. Snapshotted `_cmd_client_handlers.py` (md5 `05f5f620…`) to `$TMPDIR/adv-135-remove-lsp-query-facade-mutsweep/`, mutated `cmd_impact` line 648 `'impact': impact` → `'impact': []`, ran `test_graph_queries.py` → **2 failed, 30 passed** (RED as required), wrote the bytes back and re-verified the md5; `git status --porcelain` shows the file unmodified. No `git checkout`/`restore`/`stash` used. Replaced the "no sweep needed" paragraph with the sweep and its result |
| A4 | Counts and quotes | Three counts were wrong and one was imprecise. "Command Summary carries **18** rows" → **17** (558-574; 18 only if the header row is counted, and the cited range 554-577 is wrong regardless). "The re-export block lists **20** names" → the block lists **32**, of which 20 are `cmd_*`. The deleted test's "six functions, **five** of them pure facade-equality (`assert facade == direct`)" → only **four** carry that assertion; the fifth, `test_cli_speaks_lsp_vocabulary`, is a CLI-level `lsp hover` invocation asserting `status == 'success'` (still 100 % facade, so the conclusion holds). `README.adoc:12-18` → the Pages list runs 12-19. Everything else re-derived clean: 25 handler-dict verbs, 26 argparse choices, 20 `def cmd_*`, 34 `.py` files in the test dir, 36 doctor rules, 17 ADRs, 684 SKILL.md lines, 108 rationale.md lines, PR #1214's 13 files and `+434 / −509` (which reconciles to the digit). Every quotation checked verbatim against its source — the G1 Command-Summary cell, the G7 concepts sentence, the `sourcery-ai` and `cuioss-review-bot` bodies, and the coderabbit "**103 minutes**" that G13 correctly catches the report misquoting as 107 | All four counts corrected in place; the verbatim reconciliation of the `+434 / −509` split and the reviewer quotations added to § Report accuracy |
| A5 | Actionability | Every entry already carried a concrete path, a concrete change and an observable *Done when*; none was a "review X"/"consider Y". Two were weaker than they read: **G7's action** proposed "plus the adjacency surface of `module`", which would have wrongly deleted `overview` — `overview`'s contract (`client-api.md:449-467`) does carry an Adjacency section, so `info` is the only wrong name in the clause. **G14 existed only as a bullet in the `gaps.md` preamble** — the previous reviewer was interrupted before writing the section, leaving a dangling forward reference | Rewrote G7's action to delete `/ \`info\`` and nothing else, citing the contract that clears `overview`. Wrote the **G14** section in full: the analyzer to add, where to register it, the two nearest rules that do *not* cover this (`canonical-enum-choices-drift` checks a flag enum against `choices=`; `literal-count-drift` checks an integer count), the house fail-closed discipline including the `enrich` group at `architecture.py:340-452`, and a *Done when* that is red-then-green against G4–G6 |
| A6 | Severity and topic | Twelve of thirteen severities and all thirteen topics survived calibration. **G10 was filed medium** but is neither wrong shipped behaviour nor a false claim in shipped documentation: the link is not yet dangling, its target is recoverable from git history, and nothing outside `doc/plans/` is affected | G10 re-severitied **medium → low**, with the reason stated in the entry so a later reader can disagree with the call rather than inherit it. New entries: G14 **medium / detectors/auditor** (a missing detector on the path that let G4–G6 survive two plans), G15 **low / architecture-core** (the owning surface is the shipped script, not a doc) |
| A7 | Coverage | `verification.md` covers D0–D3, the unplanned `rationale.md` addition, all five out-of-scope carve-outs, report accuracy, the residue list, collateral, and method. Two holes: the *Done when* for D2 is **bidirectional** ("no dangling `xref:`/name-anchor **anywhere**") and only the outbound half was checked; and the coverage census for the deleted test's verbs omitted `cmd_which_module`, which that test also exercised | Ran the inbound half — every anchored link from any tracked `.md`/`.adoc` outside `doc/plans/` into the five edited documents, resolved against their live heading sets: **0 dangling**, so D2 is now confirmed in both directions. Added `cmd_which_module`'s four covering test files to the census |
| A8 | Internal consistency | The overall verdict follows from the rows. Two internal contradictions, both from the interrupted predecessor: `gaps.md`'s preamble promised **fourteen** items including a G14 that had no section, and `verification.md`'s § Test adequacy attributed the missing-detector finding to "**(G4–G6)**" — the drift instances — rather than to the detector gap itself. `verification.md`'s own opening paragraph also described a four-bucket taxonomy that no longer matched `gaps.md`'s five | G14 written; `gaps.md`'s preamble reconciled to **fifteen** with G15 added to the taxonomy; the § Test adequacy attribution retargeted to **(G14)**; `verification.md`'s opening rewritten to the same five-bucket taxonomy, and corrected to state that G1 and G11 were found by the audit, not surfaced by the run |

**Residual doubt:** the type-check half of the build gate. `./pw verify` is out of remit, and a scoped
`uv run mypy` outside the pyprojectx envelope cannot resolve the cross-skill `MYPYPATH` entries, so it
reports import-not-found noise that is an artifact of the invocation rather than of the tree — it was
therefore discarded rather than reported. A deletion of this shape can in principle strand a
type-only import that `ruff` does not see, and nothing here rules that out independently of the
merge-queue-verified merge. A further round would most likely find more instances of the
hand-maintained-mirror class rather than anything wrong with the removal: G4, G5, G6, G15 and the
`_cmd_client.py` re-export block are all mirrors of the same verb set, and G14 exists because nothing
detects them — a sweep of that class across other bundles would probably be productive, and would be
better done as the G14 rule's first run than by hand.

**Verdict on the audit:** SOUND AFTER CORRECTION — the removal was verified correctly and no gap was
invented, but the audit under-evidenced two CONFIRMED verdicts (a narrower test population than it
claimed, and a gitignored consumer surface it wrongly believed absent), skipped the mutation sweep that
makes its test evidence non-vacuous, checked a bidirectional *Done when* in one direction, mis-stated
four counts, and shipped a dangling G14 reference from the interrupted prior pass — all now closed.

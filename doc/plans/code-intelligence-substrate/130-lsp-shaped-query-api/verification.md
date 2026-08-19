# Verification — 130-lsp-shaped-query-api

**Audited:** `plan.md`, `report-01.md` (plus, for the retirement question,
`../135-remove-lsp-query-facade/plan.md` and `../135-remove-lsp-query-facade/report-01.md`)
**Tree state:** first pass at `61a43e5`; re-derived end-to-end by the adversarial pass at `a90adeb`,
both on `claude/code-intelligence-substrate-analysis-kah884` (`61a43e5` is an ancestor of `a90adeb`;
no shipped file this audit cites changed between them)
**Overall verdict:** CONFIRMED WITH GAPS

The plan shipped as PR [#1207](https://github.com/cuioss/plan-marshall/pull/1207), squash-merged as
`8d5055f` (`merged: true`, `merged_at 2026-08-13T11:02:03Z`, read via the GitHub API). Its D1 — the
`lsp` facade and the verb mapping table — was **deliberately retired** by the later landed plan
`135-remove-lsp-query-facade` (PR #1214, squash `064b387`, on `main`). The absence of the facade is
therefore *not* a gap; it is the intended state, and this audit treats D1 as "delivered, then
withdrawn by decision". The other four deliverables survive and are audited against the tree now.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | LSP-shaped facade + per-verb mapping table | "DONE. New `lsp` subcommand group … mapping table in `client-api.md`" | Facade, its handlers, its test and its docs are **gone** — removed on purpose by plan 135. The four residue verbs (`path`, `impact`, `find`, `which-module`) are present and unchanged. | CONFIRMED-AT-MERGE, RETIRED BY 135 (not a gap) |
| D2 | `capabilities` verb: cannot-derive vs derived-nothing, envelope-scoped, uncached | "DONE … each `not_derivable`/`derivable` (+`derived_count`) or `available`/`unavailable`; read from producers that actually ran, per-call (uncached), envelope-scoped" | Verb exists and draws the cannot-derive / derived-nothing binary for `module_edges` / `path_attribution`. The `content_search` row does **not** distinguish the two empties; the "nothing is memoised" property is false in-process; and the documented three-state shape has no `derived_count` on the `path_attribution` row. | PARTIAL |
| D3 | Vacuous-consumer guard on the refine feasibility check | "DONE … `resolver_count: 0` → `FEASIBILITY: UNDERIVABLE` … Negative-control test asserts the two empty graphs are classified oppositely" | Guard text shipped and correct in both directions. The "negative-control test" re-implements the guard locally; deleting the shipped guard wholesale leaves it green. | PARTIAL |
| D4 | `search --content` measurement contract (`--ignore-case`, `file_count`) | "DONE … `--ignore-case` (composes with `--literal`) … `file_count` (distinct paths) added alongside `count` (rows); regex-mode `(?i)` documented" | Implemented exactly as specified; both properties covered by tests that go red under mutation. Two sibling counters in the same response (`files_scanned`, `unreadable[]`) remain row-populations documented as file-populations. | CONFIRMED (with residue) |
| D5 | Documentation across concepts / developer / user / skill surfaces | "DONE. concepts, developer `lsp-query-facade.adoc` + README registration, user `code-search.adoc`, `SKILL.md` + `client-api.md`" | Surviving (non-facade) doc surface is present, cross-referenced and accurate except at four points — the caching claim, the `files_scanned` / `unreadable` wording, the three-state table's `derived_count`, and the verb-summary row's vocabulary for `content_search`. The facade half of D5 was removed by plan 135 with no dangling xref. | CONFIRMED for the surviving surface |

## Per-deliverable detail

### D1 — an LSP-shaped query vocabulary over the existing capability set

- **Required (plan):** "the facade answers in LSP vocabulary, the four residue verbs remain reachable
  unchanged, and a per-verb mapping table exists for the verbs that **do** map."
- **Claimed (report):** `lsp hover|references|workspace-symbol|definition` dispatching to
  `module`/`impact`/`find`/`resolve`; mapping table in `client-api.md`; test `test_lsp_facade.py`.
- **Found:** nothing of the facade survives, by design.
  - Whole-tree sweep for `cmd_lsp_`, `architecture lsp`, and
    `lsp hover|references|workspace-symbol|definition` (excluding `.git`): every hit is a plan
    record under `doc/plans/code-intelligence-substrate/130-lsp-shaped-query-api/` or
    `.../135-remove-lsp-query-facade/`. No hit in `marketplace/`, `test/`, `doc/user/`,
    `doc/developer/`, `doc/concepts/`.
  - `test/plan-marshall/manage-architecture/` no longer contains `test_lsp_facade.py`.
  - `doc/developer/lsp-query-facade.adoc` is absent and no `xref:`/link to it survives (grep for
    `lsp-query-facade` outside `doc/plans/` returns nothing).
  - The retirement is documented and landed: `135-remove-lsp-query-facade/plan.md:54-61` is the Goal
    section ("The `lsp` command group, its test, and every piece of its documentation are gone"), and
    `git branch --contains 064b387` lists `main`.
  - The residue verbs the deliverable required to stay reachable are all still registered:
    `architecture.py:119` (`path`), `:142` (`impact`), `:233` (`which-module`), `:241` (`find`).
- **Checks run:** whole-tree grep (see above); `ls` of the test module; `git show --stat 8d5055f`
  (18 files, the facade among them) and `git show --stat 064b387`; `git branch --contains` for both
  squash commits.
- **Verdict:** CONFIRMED-AT-MERGE, RETIRED BY 135. The deliverable was built as specified and was
  then removed by a later landed plan that explicitly names it as a shim with zero adoption
  (`135-remove-lsp-query-facade/plan.md:56-61`: "The `lsp` command group, its test, and every piece
  of its documentation are gone … The three genuinely-new pieces plan 130 also shipped — the
  `capabilities` report, the refine `UNDERIVABLE` guard, and the `search --content` measurement
  contract (`--ignore-case`, `file_count`) — are untouched"). **This is not a gap and must not be
  re-filed as one.** Note for the record that the plan's claim-label obligation "walk **all**
  subcommands against the LSP method list … derive the full residue" was never discharged —
  `report-01.md:48-56` is a five-row table naming **eight distinct** existing verbs (`module`,
  `impact`, `find`, `resolve` as facade targets; `path`, `impact`, `find`, `which-module`, `graph`,
  `neighbors` on the residue row) against the **26 top-level subcommands** the argparse surface
  registers (re-counted at `a90adeb` from the `subparsers.add_parser` calls in `architecture.py`;
  a further 10 are `enrich` sub-subcommands) — but the obligation is moot now that the facade is
  gone.

### D2 — a capability-report verb

- **Required (plan):** "the report distinguishes *cannot derive* from *derived nothing*, and its
  answer is envelope-scoped and uncached", with three binding constraints (never read the tool
  declaration as the grant; no caching across dispatches; answer for the executing envelope).
- **Claimed (report):** `cmd_capabilities` reports `module_edges` / `path_attribution` /
  `content_search`, "read from producers that actually ran, per-call (uncached), envelope-scoped".
- **Found:**
  - Handler `_cmd_client_handlers.py:142-250`; argparse registration `architecture.py:286-295`;
    dispatch `architecture.py:541`; re-export `_cmd_client.py:85`.
  - `module_edges` is read from `get_module_graph`'s own provenance
    (`_cmd_client_handlers.py:188-202`) and excludes discovered-but-not-dispatched resolvers via
    `STATUS_NOT_DISPATCHED` — the actual-grant constraint is honoured, and plan 220 later extended
    it with `test_derivation_resolver_configuration.py:249-283`.
  - The error boundary the PR reviewer asked for is present: the whole evaluation sits inside one
    `try` (`:182-222`), with the raising-downstream test at `test_capabilities.py:236-257`.
  - **Defect 1 — the `content_search` row conflates the two empties.** The entry
    (`_cmd_client_handlers.py:243-248`) carries only `status` (`available`/`unavailable`) and
    `modules_inventoried`; the per-module loop swallows a missing descriptor
    (`:213-216`, `except DataNotFoundError: continue`). Measured in this clone: an envelope that was
    never crawled and an envelope crawled with two file-less modules produce a **byte-identical**
    entry — `{"capability": "content_search", "verbs": [...], "status": "unavailable",
    "modules_inventoried": 0}`, comparison `True`. That is exactly the *cannot-derive vs
    derived-nothing* ambiguity the deliverable exists to close, unresolved in one of its three rows.
    The shipped tests encode the conflation rather than catching it:
    `test_capabilities.py:121-135` (a never-crawled tmpdir) asserts `content_search` is
    `unavailable`, and `:225-233` (two crawled, file-less modules) asserts `unavailable` plus
    `modules_inventoried == 0` — two structurally different envelopes, no assertion anywhere that
    their entries differ.
  - **Defect 2 — "nothing is memoised across calls" is false in-process.**
    `resolve_path_attribution` (`_architecture_core.py:1125-1185`) serves from
    `_PATH_CLAIM_CACHE` (`:1122`), a process-lifetime memo keyed by the sorted module-name tuple
    only. Measured: two `cmd_capabilities` calls in one process, with `discover_path_attributors`
    made to return an attributor between them, both report
    `path_attribution: not_derivable producer_count 0`. The absolute claim appears verbatim in three
    shipped places — `_cmd_client_handlers.py:162-163`, `client-api.md:1375-1376`,
    `doc/concepts/code-intelligence.adoc:259` ("memoised across none"). The weaker per-dispatch
    phrasing in `SKILL.md:544` and `doc/user/code-search.adoc:198` ("never cached across dispatches")
    remains true, because each CLI invocation is a fresh process.
  - **Defect 3 — the documented three-state shape is unexpressible on the `path_attribution` row.**
    `client-api.md:1383-1390` and `doc/concepts/code-intelligence.adoc:262` state the three states as
    `not_derivable`/`producer_count: 0`, `derivable`/`derived_count: 0`, `derivable`/`derived_count:
    N`. The `path_attribution` entry (`_cmd_client_handlers.py:236-242`) carries no `derived_count`
    at all, so an attributor that ran and claimed nothing and one that claimed fifty both report
    `derivable, producer_count: 1`. The data is already in hand — each attributor report carries
    `claim_count` (`extension-api/scripts/_path_attribution_merge.py:342`). D2's literal *Done when*
    (distinguish *cannot derive* from *derived nothing*) is still met on this row, because
    `producer_count` draws that binary; what fails is the stronger three-state claim the shipped
    documentation makes. Filed as G9.
  - **Constraint not discharged — verification inside a dispatched leaf.** The plan's Verification
    section (`plan.md:155-157`) requires D2 be verified in a leaf, not in main context.
    `report-01.md:112-117, 200-203` records this as unmet and substitutes a two-project-dir test.
    Still open.
- **Checks run:** read the handler and its call chain; ran `test_capabilities.py` (10 passed);
  mutated `'status': 'derivable' if resolver_count else 'not_derivable'` →
  `'status': 'derivable'` and re-ran the file — **2 failed, 8 passed**
  (`test_empty_envelope_reports_no_capabilities_not_false_ones`,
  `test_module_edges_not_derivable_when_no_resolver_ran`), so the `module_edges` guard is
  non-vacuous; restored from a byte snapshot and confirmed `git status --porcelain` clean for the
  file. Two in-process probes (payload equality; memo staleness) as described above. Re-run
  independently at `a90adeb`: baseline 10 passed, mutation **2 failed, 8 passed** with exactly those
  two test names; the memo-staleness probe carries a positive control — clearing
  `_PATH_CLAIM_CACHE` between call 2 and call 3 flips the row to
  `derivable, producer_count 1, producers ['probe-attributor']`, which pins the memo (not attributor
  discovery) as the cause of the stale answer.
- **Verdict:** PARTIAL — the verb exists, is envelope-scoped, and draws the cannot-derive /
  derived-nothing binary on two of its three rows; the `content_search` row does not draw it at all,
  one of the three binding properties is documented more strongly than the code delivers, and the
  documented three-state shape is unexpressible on the `path_attribution` row.

### D3 — the vacuous-consumer guard

- **Required (plan):** "the consumer either gets edges or gets an explicit underivable signal — and a
  test asserts it cannot silently pass on emptiness."
- **Claimed (report):** the refine Feasibility Check gates on `resolver_count`; negative-control test
  `test_feasibility_underivable_guard.py` asserts the two empty graphs are classified oppositely.
- **Found:**
  - The shipped consumer change is prose, and it is correct and bidirectional:
    `phase-2-refine/standards/refine-workflow-detail.md:493-498` — `resolver_count: 0` ⇒
    `FEASIBILITY: UNDERIVABLE …`; `resolver_count: N` with empty edges ⇒ a clean pass is correct;
    plus a pointer to the whole-surface `capabilities` form. `git show --stat 8d5055f` confirms the
    production footprint of D3 was these 7 lines.
  - The test is a **model of the guard, not a check of it**:
    `test_feasibility_underivable_guard.py:85-93` defines `_dependency_direction_derivable` locally
    and asserts it against `get_module_graph`'s `resolver_count`. It never reads
    `refine-workflow-detail.md`, so it cannot detect the guard's removal or corruption.
  - Proven, and re-proven independently at `a90adeb`: deleting the entire `**Underivable guard …**`
    block (`refine-workflow-detail.md:492-499`, everything between the Feasibility Check prose and
    `### Scope Size Estimation`) leaves the test file green — `3 passed`, with
    `grep -c "Underivable guard"` returning `0` at the moment of the run. Restored from a byte
    snapshot; `git status --porcelain` clean for the file. A whole-tree sweep of `test/` for
    `UNDERIVABLE` finds no other test that reads the guard either, so the shipped artifact is
    unprotected by the suite as a whole, not merely by its own test file.
  - A doc-anchored guard test is both feasible and idiomatic **in this same skill**:
    `test/plan-marshall/phase-2-refine/test_phase_2_refine_scope_estimate.py:361-384` reads
    `refine-workflow-detail.md` and asserts its documented content.
  - The plan's `Expected surface` hypothesised "refine **and finalize** consumers that read graph
    output". Re-derived: the only bundle consumers of `architecture graph` are
    `manage-architecture` (its own docs), `phase-2-refine`, and two inventory scripts
    (`plugin_discover.py`, `tools-marketplace-inventory/SKILL.md`) — no finalize consumer exists, so
    covering refine alone is complete.
- **Verdict:** PARTIAL — the shipped guard satisfies the first half of the *Done when* exactly; the
  second half ("a test asserts it cannot silently pass on emptiness") is satisfied only against a
  test-local re-statement of the guard, which is the tautology the clause exists to prevent.

### D4 — the search primitive's measurement contract

- **Required (plan):** "a pattern containing metacharacters can be matched case-insensitively and
  verbatim at once, and the count states what it counts"; plus documenting the existing regex-mode
  behaviour.
- **Claimed (report):** `--ignore-case` composes with `--literal`; `file_count` alongside `count`;
  `(?i)` documented; tests added to `test_search_content.py`.
- **Found:**
  - Flag: `architecture.py:276-284` (`--ignore-case`, `dest='ignore_case'`, help text naming the
    composition). Compile: `_cmd_client_handlers.py:1192`
    `flags = re.MULTILINE | (re.IGNORECASE if ignore_case else 0)` with the escape on the orthogonal
    axis at `:1194`. Echo: `:1201` (error path) and `:1252` (success path).
  - Population: `:1254-1255` — `count: len(results)` (rows, after
    `_collapse_claimed_duplicate_rows`) and `file_count: len({row['path'] for row in results})`
    (distinct paths). Documented at `client-api.md:1117-1121`, `SKILL.md:526`,
    `doc/user/code-search.adoc:135-139`.
  - Regex-mode `(?i)` documented at `client-api.md:936-947`, `doc/user/code-search.adoc:79-87`.
  - Measured in this clone on a doubly-attributed file: `count 2 / file_count 1 / files_scanned 2`.
  - **Residue — sibling counters in the same response are still row-populations.**
    `files_scanned` (`:1238`) and `unreadable[]` (`:1233` decode, `:1236` OS) increment per
    `(module, category, path)` pair, not per distinct file, while `client-api.md:988` says
    `files_scanned` "Counts the files actually OPENED AND SCANNED", `doc/user/code-search.adoc:148`
    says "How many files were actually opened and searched", and `client-api.md:989` says of
    `unreadable` "Each entry is a file that MIGHT contain a match nobody saw". Measured: one
    physical file inventoried by two modules yields `files_scanned: 2`; one *missing* file
    inventoried by two modules yields `unreadable` = two identical
    `{"path": "shared/ghost.py", "reason": "os_error"}` entries.
- **Checks run:** mutation M1 — dropped `re.IGNORECASE` from the compile → `test_search_content.py`
  **2 failed, 18 passed**; mutation M2 — `file_count` degenerated to `len(results)` → **1 failed, 19
  passed**. Both restored, `git status --porcelain` clean for the file afterwards. Two in-process
  probes for the row-population measurements above. All four readings re-taken independently at
  `a90adeb` (baseline 20 passed; M1 → 2 failed / 18 passed, naming
  `test_ignore_case_composes_with_literal_on_a_metacharacter_pattern` and
  `test_ignore_case_flag_and_inline_marker_both_work_in_regex_mode`; M2 → 1 failed / 19 passed,
  naming `test_count_is_rows_and_file_count_is_distinct_files`) and reproduce exactly.
- **Verdict:** CONFIRMED against the literal *Done when*; the residue above is a fresh, smaller
  instance of the same row-versus-file recurrence rather than a failure of the clause.

### D5 — documentation, shipped in this plan

- **Required (plan):** the LSP query model in `doc/concepts/`, the verb mapping in `doc/developer/`,
  the operator surface in `doc/user/`, plus `SKILL.md` and `client-api.md`; "every mapped verb
  appears in the mapping table and the help text matches the implemented behaviour".
- **Claimed (report):** all five surfaces written; cold read passed (no verb read as renamed).
- **Found:**
  - The facade half (concepts `== The query vocabulary: an LSP-shaped facade`,
    `doc/developer/lsp-query-facade.adoc`, the developer-README bullet, the `client-api.md` and
    `SKILL.md` facade blocks) is gone, removed by plan 135 with no dangling reference — grep for
    `lsp-query-facade` and for `LSP` across `marketplace/bundles/plan-marshall/skills/manage-architecture/`,
    `doc/user/code-search.adoc` and `doc/concepts/code-intelligence.adoc` returns exactly one
    unrelated hit (`code-intelligence.adoc:97`, about the real `lsp-client` transport).
  - The surviving half is present and, with the exceptions named below, consistent with the code:
    `client-api.md:571-572` (summary
    rows), `:923-947` (search synopsis + case-insensitivity), `:983-1006` (anti-vacuity + the
    complete-coverage conjunction), `:1356-1434` (`capabilities`, including the elision note the
    report says it added at `:1417-1423`); `SKILL.md:509-534` (search, including the paragraphs plan
    135 relocated out of the deleted `### lsp` block) and `:538-544` (`capabilities`);
    `doc/user/code-search.adoc:46-66, 76-87, 111-155, 189-198`;
    `doc/concepts/code-intelligence.adoc:252-262`.
  - The two agent-guidance mirrors the report says it fixed are in place:
    `persona-plan-marshall-agent/standards/tool-usage-patterns.md:62` carries `[--ignore-case]` in
    the synopsis and `.../agent-behavior-rules.md:313` names `--ignore-case` in the content-lookup
    hint.
  - Help text vs behaviour: `architecture.py:276-284` help text and `client-api.md:936-947` describe
    the composition the code implements. **Four** doc statements do **not** match behaviour:
    1. the "nothing is memoised" claim (D2 Defect 2 → G2);
    2. the `files_scanned` / `unreadable` file-population wording (D4 residue → G5, G6);
    3. the three-state table's `derived_count` on the `path_attribution` row (D2 Defect 3 → G9);
    4. **the verb-summary row itself** — `client-api.md:572` describes `capabilities` as reporting
       "Per-capability `derivable`/`not_derivable` (module edges, path attribution, **content
       search**)", but `content_search` reports `available`/`unavailable` and never
       `derivable`/`not_derivable` (`_cmd_client_handlers.py:246`). The detailed section states the
       split correctly (`client-api.md:1392-1393`), so this is the summary row contradicting the
       body of its own document. Folded into G1, whose fix decides which of the two vocabularies
       survives.
- **Verdict:** CONFIRMED for the surviving surface as a whole — every surface the deliverable named
  exists, is cross-referenced, and passes the "no verb reads as renamed" criterion — with the four
  inaccuracies above filed as gaps.

## Correctness review

Read in full: `cmd_capabilities` (`_cmd_client_handlers.py:142-250`), `cmd_search` (`:1104-1261`),
`cmd_graph` (`:124-139`), `count_dispatched` / `_partition_configured_resolvers`
(`_cmd_client_query.py:939-1031`), `resolve_path_attribution` (`_architecture_core.py:1111-1185`),
and the argparse surface (`architecture.py:245-300, 460-545`).

Defects found:

1. **`content_search` cannot report "crawled and found nothing" (`_cmd_client_handlers.py:211-218,
   243-248`).** A module whose descriptor is missing is skipped by `except DataNotFoundError:
   continue`, and the entry exposes no total/attempted count, so an uncrawled envelope and a crawled
   empty one are indistinguishable. Consequence: the one row a leaf would consult before deciding
   whether a `count: 0` from `search` is trustworthy cannot tell "install/refresh the crawl" from
   "there is genuinely nothing inventoried".
2. **The capability answer is memoised in-process (`_architecture_core.py:1122, 1176-1181`)** while
   three shipped documents state the opposite. Consequence today is bounded — one CLI call per
   process — but any in-process caller (the test corpus already is one) gets a stale
   `path_attribution` row, and the memo key omits `project_dir`, so the envelope-scoping property is
   an accident of attributor discovery being process-global rather than a structural guarantee.
3. **`files_scanned` and `unreadable[]` are row populations wearing file-population names
   (`_cmd_client_handlers.py:1230-1238`).** Consequence: a caller applying the documented
   complete-coverage conjunction (`client-api.md:992-1006`) over a tree with cross-module duplicate
   inventory over-counts both the scanned population and the unreadable population; the duplicate
   `unreadable` entries additionally make `len(unreadable)` wrong as a count of at-risk files.
4. **The `path_attribution` row cannot express "ran and claimed nothing" quantitatively
   (`_cmd_client_handlers.py:236-242`)** while `client-api.md:1383-1390` and
   `code-intelligence.adoc:262` document a three-state shape keyed on `derived_count`. The binary the
   *Done when* requires is drawn (`producer_count`); the documented third state is not reachable on
   this row.

No fail-open branch, unguarded `None`, off-by-one, or stale-surface read was found in the D2/D4
code paths beyond the above. The error boundaries (`:182-222`, `:1205-1210`, `:1193-1203`) are
fail-closed and return structured errors. Two specific fail-open shapes were looked for and are
absent: `resolver_count` is `count_dispatched(resolver_reports)`
(`_cmd_client_query.py:412`, `:942-957`), which excludes only `STATUS_NOT_DISPATCHED`, so
`producer_count` and `len(producers)` can never disagree on the `module_edges` row — the invariant
`test_capabilities.py:152-156` asserts; and `resolve_path_attribution`'s degraded `(None, [])` return
on `ImportError` (`_architecture_core.py:1173-1174`) surfaces as `not_derivable`, which is the
conservative direction (an absent seam is reported as an absent capability, never as a present one).

## Test adequacy

| Deliverable | Tests | Adequacy |
|---|---|---|
| D1 | `test_lsp_facade.py` — deleted with the facade by plan 135 | N/A (retired) |
| D2 | `test/plan-marshall/manage-architecture/test_capabilities.py` (10 tests); `test_derivation_resolver_configuration.py:249-283` (plan 220) | Non-vacuous on `module_edges`: mutating the status ternary to a constant `'derivable'` turns the file red (2 failed, 8 passed). **Uncovered:** the "uncached" property (no test calls twice with changed producers); the `content_search` cannot-derive case (the two tests that touch it assert non-contradictory facts about structurally different envelopes and never that the entries differ); and any claim-count assertion on `path_attribution`. |
| D3 | `test_feasibility_underivable_guard.py` (3 tests) | **Vacuous with respect to the shipped artifact.** Deleting the whole guard block from `refine-workflow-detail.md` leaves it green (3 passed). It pins `get_module_graph`'s `resolver_count` — behaviour that predates this plan — plus a locally-defined predicate. |
| D4 | `test_search_content.py:540-666` (5 D4 tests) | Non-vacuous: dropping `re.IGNORECASE` → 2 failed; degenerating `file_count` to the row count → 1 failed. **Uncovered:** `files_scanned` / `unreadable` populations under duplicate attribution (the duplicate-attribution fixture at `:201-217` asserts `count`/`file_count` only). |

All mutations were applied from byte snapshots taken under
`…/scratchpad/verify-130-mutsweep/` (first pass) and `…/scratchpad/adv-130-mutsweep/` (adversarial
re-run) and written back; `git status --porcelain` shows neither `_cmd_client_handlers.py` nor
`refine-workflow-detail.md` modified by this audit afterwards. `git checkout` / `restore` / `stash`
were never used.

Method note 1: in a first batched sweep the D2 mutation reported green; re-run in isolation with
`-p no:cacheprovider` it is red with the two failures quoted above, and the mutated source was
printed from disk immediately before the run to prove it was in place. The isolated run is the
authoritative result; the batched green was a stale-bytecode artifact of my harness, not a property
of the test. The adversarial re-run, always with `-p no:cacheprovider`, reproduces the red.

Method note 2: during the adversarial re-run a concurrent agent held its own mutation
(`_collapse_claimed_duplicate_rows` → `pass`) in `_cmd_client_handlers.py` for part of the window.
Every mutation of mine in that file was therefore applied and reverted as a *single-line targeted
edit* rather than a whole-file restore, so no other agent's in-flight work was overwritten; a
`git diff` of the file after each revert showed my line back to HEAD content. The foreign mutation
does not disturb the readings reported here — it was verified not to change the D4 baseline
(20 passed with it present) and it is orthogonal to the `re.IGNORECASE` and `file_count` mutants.

## Report accuracy

Claims checked against the tree now:

- ✅ D2/D3/D4 implementation claims, the elision note, the two agent-guidance mirror fixes, and the
  `cuioss-review-bot` error-boundary fix are all present as described (`path:line`s above).
- ⚠️ **D1 and the D1 half of D5 are now false of the tree** — "New `lsp` subcommand group",
  "Per-verb mapping table in `client-api.md` § 'LSP-shaped query facade'", "Tests:
  `test_lsp_facade.py`", "developer/`lsp-query-facade.adoc` (new, verb mapping) + README
  registration". They were true at merge; plan 135 removed all of them by decision. Recorded as
  historical, **not** filed as a gap.
- ❌ *"D2 … per-call (uncached)"* (`report-01.md:69`) overstates the code: the path-attribution half
  is memoised for the process lifetime (`_architecture_core.py:1122`). The PR body carries the same
  overstatement in its D2 paragraph ("recomputed per call") but immediately qualifies it with the
  accurate per-dispatch gloss ("never cached across dispatches"), so the PR body is misleading only
  on its first half. Filed under G8 with the commit count.
- ❌ *"4 Implement | DONE — six commits"* (`report-01.md:170`). PR #1207 carries **eight** commits
  (`31b8ede`, `0d12e4b`, `6126013`, `8159710`, `0df29ed`, `32d4c27`, `8469daf`, `1f2fdee` — read
  from the GitHub API); all do carry the `Co-Authored-By: Claude` trailer.
- ⚠️ *"All five deliverables verified as implemented-as-specified with tests"* (`report-01.md:104-105`)
  is overstated in two respects the sub-agent did not catch: the D3 test does not exercise the
  shipped guard at all, and the D2 `content_search` row does not draw the distinction D2 is named
  for. Filed under G8.
- ℹ️ The commit SHAs cited throughout (`0d12e4b`, `6126013`, `8159710`, `0df29ed`, `8469daf`) are not
  resolvable in this clone (`git cat-file -t` → `Not a valid object name` for all eight PR SHAs)
  because the PR was squash-merged and the branch deleted; they are resolvable through the PR. Not a
  defect, but the report offers no squash SHA (`8d5055f`) that a later reader could use locally.
- ✅ The PR-level figures the report implies are exact: GitHub reports `changed_files: 18`,
  `commits: 8`, `merged: true`, matching `git show --stat 8d5055f` (18 files) in this clone.
- 🔍 UNVERIFIABLE: *"`verify: SUCCESS` — 19480 passed, 14 skipped in 336s"* and the CI check-name
  list. The brief excludes running `./pw verify`; the scoped test files I did run are green at HEAD
  (20 + 10 + 3 passed).

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| **Landing confirmation** — auto-merge armed on #1207, session could not read back `MERGED` | **Closed** | GitHub API: PR #1207 `state: closed`, `merged: true`, `merged_at 2026-08-13T11:02:03Z`, `merged_by cuioss-oliver`; squash `8d5055f` is on `main`. |
| **D2-in-a-real-leaf** — the plan requires D2 be verified inside a dispatched leaf with revoked Grep/Glob; only a two-project-dir proxy was run | **Still open** | No leaf-scoped test or evidence exists anywhere in `test/plan-marshall/manage-architecture/`; `test_capabilities.py:260-275` is the two-project-dir proxy. No later plan in the epic closes it — a bundle-wide grep for `architecture capabilities` outside `manage-architecture/` returns exactly one hit, `phase-2-refine/standards/refine-workflow-detail.md:498`; the skill's own `SKILL.md:541` and the user page `doc/user/code-search.adoc:195` are the documentation surfaces, and nothing else invokes the verb. Filed as G7. |
| Split-guard verdict "keep together" (`report-01.md:16-30`) | N/A — a recorded decision, discharged | The plan required the verdict be recorded; it is, with rationale. |

Not declared as residue but now visible: the plan's claim-label obligation to *"walk all subcommands
against the LSP method list"* was answered with a sample rather than an enumeration —
`report-01.md:48-56` names eight distinct existing verbs against the 26 top-level subcommands
`architecture.py` registers (plus 10 `enrich` sub-subcommands), the same figures re-derived in § D1.
Moot after plan 135.

## Out-of-scope and collateral

- The plan forbade "a breaking rename of the existing verbs". Honoured: every pre-existing verb is
  still registered under its own name (`architecture.py:45-340`), and plan 135's removal touched
  only the additive group.
- The plan excluded "building a language-server protocol adapter". Honoured: the real `lsp-client`
  subsystem is untouched by both plans.
- The plan excluded "fixing every consumer's compensation for the row count". Honoured — no consumer
  was rewritten.
- Collateral beyond the plan's `Expected surface`, declared in the report and confirmed in the tree:
  `persona-plan-marshall-agent/standards/tool-usage-patterns.md:62` and
  `.../agent-behavior-rules.md:313`. Both are synopsis/hint syncs consistent with D5's purpose.
- Nothing else in the merged diff (`git show --stat 8d5055f`, 18 files) falls outside the plan's
  declared surface.

## Method and coverage

- Read `plan.md`, `report-01.md`, the epic README, and `135-remove-lsp-query-facade`'s `plan.md` and
  `report-01.md` (that plan also carries a `rationale.md`, not read — it argues the retirement, which
  this audit takes as landed fact rather than as a claim to re-litigate).
- Read the shipped code: `architecture.py` (argparse + dispatch), `_cmd_client_handlers.py`
  (`cmd_capabilities`, `cmd_search`, `cmd_graph`), `_cmd_client_query.py` (provenance counting),
  `_architecture_core.py` (path-attribution seam), `_cmd_client.py` (re-exports).
- Read the shipped docs: `client-api.md`, `SKILL.md`, `doc/user/code-search.adoc`,
  `doc/concepts/code-intelligence.adoc`, `refine-workflow-detail.md`, plus the two persona mirrors.
- Ran, at HEAD: `test_search_content.py` (20 passed), `test_capabilities.py` (10 passed),
  `test_feasibility_underivable_guard.py` (3 passed) via
  `uv run python -m pytest <file> -o addopts=""`.
- Ran four mutations (drop `re.IGNORECASE`; `file_count`→row count; constant `'derivable'`; delete
  the refine guard block) from byte snapshots, each followed by a restore from the same snapshot and
  a `git status --porcelain` check.
- Ran three in-process probes against the real handlers (duplicate-attribution counts; capability
  payload equality for never-crawled vs crawled-empty; memo staleness across two calls).
- Queried the GitHub API for PR #1207's merge state and commit list.
- **Not checked:** the full `./pw verify` figure (excluded by the brief), the CI check-name list, the
  cold-read sub-agent's conclusion (its artifact is not in the tree), and any behaviour of a real
  dispatched leaf with revoked Grep/Glob — that environment cannot be synthesised here either, which
  is why G7 is filed as a verification gap rather than resolved.
- Search-negative discipline: every "nothing found" above (`cmd_lsp_`, `lsp-query-facade`, `LSP` in
  the query docs) was run with the same pattern shape that does return hits inside
  `doc/plans/.../130-*` and `doc/plans/.../135-*`, so the negatives are not artifacts of a filtered
  search.

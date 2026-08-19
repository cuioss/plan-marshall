# Gaps — 135-remove-lsp-query-facade

The facade removal itself left nothing undone: every artefact the plan named is gone from the tree, the
wrapped verbs are intact and green, the `SKILL.md` hazard was handled, and the run produced no
collateral. What remains are fifteen items **around** the removal:

- **nine pre-existing documentation defects** in the same query-surface files — G1, G3–G9, G11. Four
  of these were surfaced by the run's own cold-read sub-agent and deliberately deferred (the heading
  hierarchy → G3; the verb-set drift → G4/G5/G6; the `info` adjacency overstatement → G7; the
  intra-doc duplication → G8/G9), and no later plan has closed any of them; G1 and G11 were found by
  this audit, not by the run;
- **two shipped-code follow-ups** — the vocabulary nit the plan named for itself (G2) and a stale
  handler-inventory docstring in a file this plan edited (G15);
- **one missing detector** that is why the G4–G6 drift survived both plan 130 and plan 135 — G14;
- **one forward-dangling cross-reference** into this plan's own directory — G10;
- **two false claims confined to `report-01.md`** — G12, G13.

None of them is a regression caused by the removal.

## G1 — Correct the `capabilities` row in the client-api Command Summary

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md:572`
  (row `| capabilities | Envelope capability report | … |` — the 15th of the table's 17 verb rows,
  which run 558-574); contradicted code at
  `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py:246`
- **Evidence:** the row reads "Per-capability `derivable`/`not_derivable` (module edges, path
  attribution, content search)". The handler emits `'status': 'available' if modules_inventoried else
  'unavailable'` for the `content_search` entry, and only `module_edges` / `path_attribution` use
  `derivable`/`not_derivable` (lines 231, 239). The same document's own `§ capabilities` states the
  split correctly at `client-api.md:1392-1393` ("The `content_search` entry uses `available` /
  `unavailable` … with a `modules_inventoried` count"), so the doc contradicts itself. Note the
  `§ capabilities` entry-shape table immediately above it (1386-1390) also states only
  `derivable` / `not_derivable`, and is rescued solely by the 1392-1393 sentence that follows.
- **Why it matters:** a consumer reading the summary row writes `if status == 'not_derivable'` and gets
  a silent false negative on content search — the exact "capability present when it is absent"
  confusion the `capabilities` verb exists to close.
- **Action:** rewrite the row's Output cell to name both vocabularies, e.g. "Per-capability status —
  `derivable`/`not_derivable` for module edges and path attribution, `available`/`unavailable` for
  content search". Do not change the handler here (that is G2).
- **Done when:** the `capabilities` row of the Command Summary table names `available`/`unavailable`
  for content search, and no statement in `client-api.md` claims a single status vocabulary across
  all three entries.
- **Effort:** S
- **Risk if fixed:** none — a one-cell documentation edit; `literal-count-drift` and the other
  plugin-doctor rules do not key on this row.

## G2 — Harmonise the `capabilities` status vocabulary across all three entries

- **Kind:** incomplete
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py:243-248`
  (`cmd_capabilities`, the `content_search` entry)
- **Evidence:** `'status': 'available' if modules_inventoried else 'unavailable'` beside
  `'status': 'derivable' if resolver_count else 'not_derivable'` (231) and the identical shape at 239.
  `plan.md` § Out of scope names this explicitly — "The cosmetic vocabulary nit in `capabilities` …
  Recorded as a follow-up in Notes" — and § Notes repeats it. Still unchanged at `61a43e5`.
- **Why it matters:** a consumer branching on `status` must special-case one of three rows; every
  document describing the verb has to carry the exception (see G1, plus
  `doc/user/code-search.adoc:198`), which is how G1's contradiction arose in the first place. The
  handler's own docstring (`_cmd_client_handlers.py:172-176`) already describes the three states as
  `not_derivable` / `derivable` / `derivable` **for every entry**, so the code contradicts itself
  too, not only the docs.
- **Action:** decide one vocabulary for all three entries (`derivable`/`not_derivable` reads best,
  since a crawl that produced an inventory *is* a producer that ran) and change the handler at
  `_cmd_client_handlers.py:246`, then update: the handler docstring (172-176), `client-api.md
  § capabilities` (the 1392-1393 exception sentence and the `content_search` row of each worked TOON
  payload — 1403 and 1414), the Command Summary row (572, which G1 also touches),
  `doc/user/code-search.adoc:198`, and `test_capabilities.py`.
- **Done when:** all three `capabilities` entries emit the same two status values, `test_capabilities.py`
  asserts the unified vocabulary, and no document or docstring mentions a per-entry exception.
- **Effort:** S
- **Risk if fixed:** any consumer already matching on the literal `available` — a tree-wide grep for
  `content_search` and `'available'` must run first; at `61a43e5` the only readers are the docs and
  `test_capabilities.py`.

## G3 — Re-close the heading hierarchy in `client-api.md`

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md:580`
  (`## Error Handling`), with the orphaned H3s at 606, 712, 817, 909, 1144, 1284, 1356; and
  `client-api.md:90` (`## Resolver provenance (the graph family)`), with the mis-parented H3s at
  309, 449, 488, 515
- **Evidence:** the H2 census is `Script Pattern` (7), `Commands` (20), `Resolver provenance (the
  graph family)` (90), `Command Summary` (554), `Error Handling` (580), `Consumer View` (1437),
  `Data Source` (1448). Of the document's **17** verb sections, only **two** (`### info` 22,
  `### modules` 55) sit under `## Commands`. The break is in two places, not one:
  - Seven — `### files` (606), `### which-module` (712), `### find` (817), `### search` (909),
    `### diff-modules` (1144), `### descriptor-regression-check` (1284), `### capabilities` (1356) —
    sit between 580 and 1437 and render as subsections of **Error Handling**. This is the half
    `report-01.md` recorded as deferred finding 1.
  - Four more — `### module` (309), `### overview` (449), `### commands` (488), `### resolve` (515) —
    render under **Resolver provenance (the graph family)**, an H2 whose prose scopes itself to
    "the four graph-family verbs" (92). `commands` and `resolve` are not graph-family verbs at all.
    This half is **not** in `report-01.md`; it was found by this audit.
- **Why it matters:** any rendered or outline view of the contract files seven verbs under "Error
  Handling" and four more under a graph-family discussion, so a reader scanning for the `search` or
  `resolve` contract does not find it where the document's own structure says verbs live; agents
  summarising the doc inherit the mis-parenting.
- **Action:** re-parent all eleven mis-filed H3 sections. Either move them under `## Commands`, or
  open command H2s that own them (e.g. `## Inventory and search commands` immediately before
  `### files`) and leave `## Error Handling` after them. Keep section bodies byte-identical; this is
  a heading/ordering change only.
- **Done when:** every one of `client-api.md`'s 17 `### <verb>` sections has an H2 ancestor that is a
  command section, `## Error Handling` contains only error-handling prose, and `## Resolver
  provenance (the graph family)` contains only the four verbs its own opening sentence names.
- **Effort:** M
- **Risk if fixed:** intra-repo anchor links to these sections (`#search`, `#capabilities`, `#find`,
  `#which-module`) must survive — they are name-anchors on the H3s, so a pure re-parent preserves them;
  verify with `plugin-doctor quality-gate` (`broken-relative-link` rule).

## G4 — Contract the `siblings` verb in `client-api.md`

- **Kind:** omission
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** verb defined at
  `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/architecture.py:198`
  (`siblings_parser`), handler `cmd_siblings` at `…/scripts/_cmd_client_handlers.py:531`, invocation
  block at `…/manage-architecture/SKILL.md:447`; absent from
  `…/standards/client-api.md` entirely
- **Evidence:** `grep -c "siblings" client-api.md` → **0**. `siblings` is a live consumer-query verb
  registered in the `handlers` dict (`architecture.py:535`) with an invocation block in `SKILL.md`, but
  no response contract anywhere in `standards/`. Recorded as deferred finding 2 in `report-01.md`.
- **Why it matters:** the canonical invocation tells a caller how to *run* the verb but nothing about
  what comes back — no field list, no zero-result semantics, no error shape — so every caller must read
  the handler source, which is precisely what the contract documents exist to prevent.
- **Action:** add a `### siblings` section to `client-api.md` (arguments table, worked TOON payload,
  zero-result and error semantics) alongside the other consumer-query verbs, and a row in the
  Command Summary table; add `siblings` to the `SKILL.md` Command Groups table (36-49).
- **Done when:** `client-api.md` contains a `### siblings` section and a Command Summary row, and the
  `SKILL.md` Command Groups table names the verb.
- **Effort:** S
- **Risk if fixed:** none — additive documentation; read `cmd_siblings` to be sure the documented shape
  matches the emitted one.

## G5 — Contract the `profiles` verb in `client-api.md`

- **Kind:** omission
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** verb defined at
  `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/architecture.py:210`
  (`profiles_parser`), handler `cmd_profiles` at `…/scripts/_cmd_client_handlers.py:486`, invocation
  block at `…/manage-architecture/SKILL.md:461`; not contracted in `…/standards/client-api.md`
- **Evidence:** `profiles` occurs exactly once in `client-api.md`, at line 540, and there only inside the
  `resolve` `mutating`-field prose (`build.maven.profiles.mutating`) — never as a verb. No `### profiles`
  section, no Command Summary row. Recorded as deferred finding 2 in `report-01.md`.
- **Why it matters:** same as G4 — a shipped verb with an invocation but no answer contract. `profiles`
  additionally feeds build-profile selection, so an undocumented response shape is a correctness hazard
  for a caller that guesses.
- **Action:** add a `### profiles` section to `client-api.md` (arguments, worked payload, zero-result and
  error semantics) plus a Command Summary row; add `profiles` to the `SKILL.md` Command Groups table.
- **Done when:** `client-api.md` contains a `### profiles` verb section and Command Summary row, and the
  `SKILL.md` Command Groups table names it.
- **Effort:** S
- **Risk if fixed:** none — additive documentation.

## G6 — Surface `descriptor-regression-check` in `SKILL.md`

- **Kind:** omission
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** verb defined at
  `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/architecture.py:317`, contracted
  at `…/standards/client-api.md:1284` (`### descriptor-regression-check`) and Command Summary row 574; absent from
  `…/manage-architecture/SKILL.md`
- **Evidence:** `grep -c "descriptor-regression-check" SKILL.md` → **0**. The verb is missing from both
  `SKILL.md` surfaces: the Command Groups table (36-49) and the Canonical invocations list (342-630).
  Recorded as deferred finding 2 in `report-01.md`.
- **Why it matters:** `SKILL.md` is what an agent loads; a commit-gate predicate that never appears
  there is effectively invisible to the consumer most likely to need it, however well contracted it is
  in `standards/`.
- **Action:** add a `### descriptor-regression-check` canonical-invocation block to `SKILL.md` (bash
  fence plus a one-paragraph summary pointing at `client-api.md § descriptor-regression-check`) and a
  Command Groups row.
- **Done when:** `SKILL.md` names `descriptor-regression-check` in both the Command Groups table and the
  Canonical invocations list.
- **Effort:** S
- **Risk if fixed:** `analyze_agentfile_line_budget` — `SKILL.md` is already 680+ lines, so re-run
  `plugin-doctor quality-gate` after the addition.

## G7 — Drop `info` from the adjacency-surface claim in the concepts page

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `doc/concepts/code-intelligence.adoc:36`
- **Evidence:** the Tier 1 paragraph ends "…and it is what the `graph`, `path`, `neighbors`, and
  `impact` verbs traverse, plus the adjacency surfaces of `overview` and `module` / `info`." The
  `info` contract at `client-api.md:22-52` returns `project`, `technologies`, and
  `modules{name,path,purpose,description,freshness}` — no edge, dependency, or adjacency field.
  `module` genuinely does carry `internal_dependencies`, and `overview`'s contract
  (`client-api.md:449-467`) genuinely lists an **Adjacency** section — "table of `Module | Internal
  Dependencies`, followed by a one-line `_Edge provenance: …_` footer" — so the claim is wrong for
  `info` and for `info` alone.
  Recorded as deferred finding 3 in `report-01.md` (which cites line 34; the sentence is now at 36).
- **Why it matters:** the concepts page is the tier model's authority. Naming `info` as an edge surface
  tells a reader that a Tier 1 answer is available from a Tier 0-only verb, which is exactly the
  cannot-derive / derived-nothing confusion the rest of the page works to eliminate.
- **Action:** delete ` / \`info\`` from the clause, leaving "plus the adjacency surfaces of
  `overview` and `module`". Both survivors are verified against their contracts
  (`client-api.md:449-467` for `overview`'s Adjacency section, the `internal_dependencies` field for
  `module`); do **not** drop `overview` — it does carry adjacency.
- **Done when:** `doc/concepts/code-intelligence.adoc` no longer names `info` as an adjacency/edge
  surface, and every verb it does name is confirmed to emit an edge or dependency field.
- **Effort:** S
- **Risk if fixed:** none — a single-clause prose edit.

## G8 — De-duplicate the `--ignore-case` / `--literal` composition rule in `client-api.md § search`

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md:936-947`
  (the `**Case-insensitivity — the one combination \`--literal\` could not express.**` paragraph)
  and again at `1111-1116` (the `- \`--ignore-case\`:` edge-case bullet)
- **Evidence:** 941 states the flag "adds `re.IGNORECASE` on an axis orthogonal to `--literal`" and
  946-947 that "The echoed `ignore_case` boolean names which population the match set was computed
  over"; 1111-1116 restates both. Recorded as deferred finding 4 in `report-01.md`.
- **Why it matters:** two statements of one rule drift apart on the next edit, and the reader cannot
  tell which is authoritative — the failure mode the repository's own "No duplication —
  cross-reference instead" documentation standard exists to prevent.
- **Action:** keep the contract statement at 936-947 and reduce the recap at 1111-1116 to a
  cross-reference, or vice versa — one statement, one place.
- **Done when:** the `--ignore-case`/`--literal` composition rule is stated once in `client-api.md`, with
  any second mention being a pointer.
- **Effort:** S
- **Risk if fixed:** none.

## G9 — De-duplicate the `count` vs `file_count` explanation in `client-api.md § search`

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md:1034-1040`
  and again at `1117-1121`
- **Evidence:** 1034-1040 explains that `count` (rows) and `file_count` (distinct paths) coincide unless
  a file is attributed to two modules; 1117-1121 restates the same distinction and the same "Read
  `file_count` for 'how many files contain this?'" guidance. Recorded as deferred finding 4 in
  `report-01.md`.
- **Why it matters:** identical to G8 — a second copy of a measurement definition is a drift source, and
  this particular pair is load-bearing (a caller reading the wrong field over-counts).
- **Action:** state the `count` / `file_count` distinction once and cross-reference from the other site.
- **Done when:** the distinction appears once in `client-api.md`, with any second mention being a
  pointer.
- **Effort:** S
- **Risk if fixed:** none.

## G10 — Resolve the cross-reference from plan 240 into this plan's `rationale.md`

- **Kind:** doc-defect
- **Severity:** low — the link is **not yet** dangling (`rationale.md` is present at `a90adeb`), the
  target is recoverable from git history, and nothing outside `doc/plans/` is affected. It is a
  scheduled future breakage in a plan-directory document, not a false claim in shipped
  documentation, so it does not reach the medium bar. (The audit filed this as medium; re-calibrated.)
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/240-skill-lsp-server/proposal-protocol-surface.md:45-46`
- **Evidence:** the sentence reads "…the same zero-adoption signature that condemned the `lsp` query facade
  in plan [`135`](../135-remove-lsp-query-facade/rationale.md)." (the markdown link itself is on 46).
  `report-01.md` § Residue states
  "`rationale.md` lives in the plan directory and **is removed at collect** (git history retains it)."
  The two cannot both hold: when collect removes `rationale.md`, plan 240's live proposal document
  acquires a dangling relative link.
- **Why it matters:** the link is the survivor-sweep failure mode ADR-007 names, arriving on a
  schedule rather than at edit time: nothing breaks at edit time, and the break lands silently when
  135's collect runs. ⚠ The audit's original framing — "plan 240 is queued, not yet run" — is
  **false** and has been removed: plan 240 ran on 2026-08-15/16 and landed as PR #1256
  (`240-skill-lsp-server/report-01.md:3`), so `proposal-protocol-surface.md` is a landed record, not
  a forward-looking proposal. The gap survives that correction — a landed record that cites the
  reasoning behind a sibling decision still loses its citation — but its urgency is lower than the
  original entry implied.
- **Action:** either (a) promote the durable argument out of the plan directory first (see G11) and
  repoint `proposal-protocol-surface.md:46` at that destination, or (b) inline the two-sentence
  substance of the reference into plan 240's proposal so the link becomes decorative, or (c) exempt this
  plan's `rationale.md` from collect removal and record the exemption.
- **Done when:** no live document outside `doc/plans/…/135-remove-lsp-query-facade/` links to a file
  inside it that collect is scheduled to delete.
- **Effort:** S
- **Risk if fixed:** none if the reasoning is preserved somewhere reachable; the risk is in doing
  nothing.

## G11 — Promote the "the query API is domain-native, not LSP" argument out of the plan directory

- **Kind:** omission
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/135-remove-lsp-query-facade/rationale.md` (whole
  file); intended destination `doc/adr/` or `doc/concepts/code-intelligence.adoc`
- **Evidence:** `report-01.md` § Residue: "If the 'why the query API is domain-native, not LSP'
  reasoning should survive as a standing guard against re-proposing the facade, promote it to a
  `doc/adr/` ADR or a short concepts-page note." `ls doc/adr/` at `61a43e5` shows 17 ADRs, none on LSP
  conformance or the query vocabulary; `doc/concepts/code-intelligence.adoc` carries no such note. Still
  open.
- **Why it matters:** the facade was proposed once and shipped once. Without a standing decision record,
  the same "give the verbs LSP names" proposal is free to return, and the counter-argument (LSP is
  `(uri, position)`-oriented; renaming ships broken interop) lives only in a plan document scheduled for
  removal.
- **Action:** write a short ADR — "The architecture query vocabulary is domain-native, not LSP-shaped" —
  condensing `rationale.md` §§ "The design question examined", "Can the core be made fully
  LSP-conformant", and "Where real LSP lives"; register it in the ADR index and link it from
  `doc/concepts/code-intelligence.adoc`.
- **Done when:** an ADR (or concepts section) outside `doc/plans/` states the decision and its reasoning,
  and is reachable from the concepts page.
- **Effort:** S
- **Risk if fixed:** none; note this also supplies G10's option (a).

## G12 — Correct the "every commit carries the Co-Authored-By trailer" claim in the run report

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/135-remove-lsp-query-facade/report-01.md:64`
  (Contract check, row "4 Implement")
- **Evidence:** the row asserts "every commit carries the `Co-Authored-By: Claude` trailer". PR #1214's
  five commits are `8c490a91`, `9e469268`, `cfc4aad`, `2192f3f`, `39ffbf66`; the first —
  "docs(plans): add plan 135 — remove the LSP-shaped query facade" — has no trailer in its message. The
  other four do.
- **Why it matters:** the contract check is the lane's self-audit. A row that reports DONE on a
  condition one commit does not meet makes the check unreliable as evidence for later runs that read it
  as a template.
- **Action:** amend the row to state the true position — four of five commits carry the trailer, and the
  plan-authoring commit (made before the run session began) does not — or state the population the claim
  covers ("every commit made by this run").
- **Done when:** `report-01.md:64` states a claim that matches PR #1214's commit list.
- **Effort:** S
- **Risk if fixed:** none — the report is a dated record; correcting a factual error in it changes no
  behaviour.

## G13 — Correct the quoted coderabbit rate-limit figure in the run report

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/135-remove-lsp-query-facade/report-01.md:46` and the
  § Step 8 shortfall disclosure quoted at line 49
- **Evidence:** the report quotes coderabbit as "Review limit reached — next review available in **107
  minutes**". The comment on PR #1214 (`#issuecomment-5283902511`) reads "**Next review available in:**
  **103 minutes**". The comment's `updated_at` (2026-08-13T17:10:15Z) is later than its `created_at`
  (17:05:48Z), so the bot may have rewritten the figure after the report was drafted — but the report
  presents the text as a quotation, and it no longer matches its source.
- **Why it matters:** the reviewer-participation table is presented as evidence-backed, with a body quote
  per reviewer. A quotation that does not match the artifact undermines the discipline the table exists
  to demonstrate.
- **Action:** requote the comment as it stands (103 minutes), or mark the figure as read-at-report-time
  and note the comment was subsequently updated.
- **Done when:** the figure in `report-01.md` matches the cited comment, or the report states why it
  differs.
- **Effort:** S
- **Risk if fixed:** none.

## G14 — Add a plugin-doctor rule detecting verb-set drift between argparse and the skill's docs

- **Kind:** missing-detector
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/` (a new
  `_analyze_*.py` analyzer, registered in `doctor-marketplace.py::cmd_quality_gate` via
  `_runner.py`, with its provenance row in
  `…/plugin-doctor/references/rule-provenance.md`); the drift it must catch is G4/G5/G6
- **Evidence:** `doctor-marketplace.py quality-gate --paths
  marketplace/bundles/plan-marshall/skills/manage-architecture` returns `status: pass`,
  `total_issues: 0`, `rules_run[36]` — re-run at `a90adeb` — while `siblings` and `profiles` are
  registered subcommands absent from `client-api.md` entirely and `descriptor-regression-check` is
  contracted in `client-api.md` but absent from both `SKILL.md` surfaces. None of the 36 rules
  compares a script's argparse **subcommand set** against the verbs its skill documents. The two
  nearest rules do something else: `canonical-enum-choices-drift` compares a documented `{a|b|c}`
  **flag enum** against that flag's `choices=`, never the subcommand set
  (`rule-provenance.md:242`); `literal-count-drift` compares a stated **integer count** against a
  derived population, never a name set (`rule-provenance.md:239`).
- **Why it matters:** the repository already treats hand-maintained mirrors as a drift class and
  guards two of them by rule (`provides-method-table-drift`, `literal-count-drift`). The verb set is
  the same class of mirror and is unguarded, which is precisely why this drift survived plan 130
  (which added verbs) and plan 135 (which removed one) with a green quality gate both times. Until
  a rule exists, fixing G4–G6 by hand fixes today's instance and nothing else.
- **Action:** add an analyzer that, for each skill with a `## Canonical invocations` block, AST-parses
  the owning script's `subparsers.add_parser('<name>', …)` calls to derive the live verb set, then
  compares it against the verb names appearing as `### <verb>` headings in `SKILL.md` and in the
  skill's `standards/*.md` contract, emitting `verb_missing_from_docs` and `phantom_documented_verb`
  findings. Follow the house discipline the sibling rules already state in `rule-provenance.md`:
  derive the population (never hard-code a script list), publish `population_size` on every finding,
  and fail CLOSED (SKIP, not pass) on an unparseable script or a nested/group subparser it cannot
  resolve — the `enrich` group in `architecture.py:340-452` is exactly that case. Register it in
  `cmd_quality_gate` so it is build-failing, and add its provenance row.
- **Done when:** `doctor-marketplace.py quality-gate --paths
  marketplace/bundles/plan-marshall/skills/manage-architecture` reports the new rule in
  `rules_run[]` and emits a finding for each of `siblings`, `profiles`, and
  `descriptor-regression-check` while G4–G6 are still open, and reports zero findings for that skill
  once G4–G6 are closed.
- **Effort:** M
- **Risk if fixed:** the rule sweeps every bundle, so it will surface drift outside
  `manage-architecture` on its first run. Land it together with a triage pass, or the quality gate
  goes red across the tree; the fail-closed SKIP cases above are what keep that surface bounded.

## G15 — Refresh the stale handler inventory in the `_cmd_client_handlers.py` module docstring

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py:6-11`
- **Evidence:** the module docstring says it "Covers the CLI handlers (info, modules, graph, module,
  overview, commands, resolve, derive-verification, profiles, siblings, path, neighbors, impact,
  files, which-module, find, search, diff-modules, descriptor-regression-check)" — **19** names,
  while the file defines **20** `def cmd_*` functions. The omission is `cmd_capabilities`
  (defined at line 142). Pre-existing: PR #1214's patch for this file touches only the import block
  and the deleted 645-731 region, never the docstring, so the staleness dates from plan 130, which
  added `cmd_capabilities` without extending the list.
- **Why it matters:** this is another instance of the hand-maintained-mirror class G14 exists to
  guard, sitting in a file this plan edited. A reader auditing the handler set from the docstring —
  the cheapest surface to read — undercounts it, and a later removal plan re-deriving its surface
  from the docstring (as plan 135 re-derived its surface from `plan.md`) inherits the omission.
- **Action:** add `capabilities` to the parenthesised list at `_cmd_client_handlers.py:6-11`, in the
  position matching the file's definition order.
- **Done when:** the docstring's parenthesised handler list names all 20 `def cmd_*` functions the
  file defines, verified by comparing the list against `grep -c "^def cmd_" _cmd_client_handlers.py`.
- **Effort:** S
- **Risk if fixed:** none — a docstring edit; `ruff check` over the file stays clean.

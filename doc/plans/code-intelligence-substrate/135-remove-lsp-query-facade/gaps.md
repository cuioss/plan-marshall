# Gaps — 135-remove-lsp-query-facade

The facade removal itself left nothing undone: every artefact the plan named is gone from the tree, the
wrapped verbs are intact and green, the `SKILL.md` hazard was handled, and the run produced no
collateral. What remains are fourteen items **around** the removal:

- **nine pre-existing documentation defects** in the same query-surface files — G1, G3–G9, G11. Four
  of these were surfaced by the run's own cold-read sub-agent and deliberately deferred (the heading
  hierarchy → G3; the verb-set drift → G4/G5/G6; the `info` adjacency overstatement → G7; the
  intra-doc duplication → G8/G9), and no later plan has closed any of them;
- **one shipped-code follow-up the plan named for itself** — G2;
- **one missing detector** that is why the G4–G6 drift survived both plan 130 and plan 135 — G14;
- **one forward-dangling cross-reference** into this plan's own directory — G10;
- **two false claims confined to `report-01.md`** — G12, G13.

None of them is a regression caused by the removal.

## G1 — Correct the `capabilities` row in the client-api Command Summary

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md:571`
  (row `| capabilities | Envelope capability report | … |`); contradicted code at
  `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py:246`
- **Evidence:** the row reads "Per-capability `derivable`/`not_derivable` (module edges, path
  attribution, content search)". The handler emits `'status': 'available' if modules_inventoried else
  'unavailable'` for the `content_search` entry, and only `module_edges` / `path_attribution` use
  `derivable`/`not_derivable` (lines 231, 239). The same document's own `§ capabilities` states the
  split correctly at `client-api.md:1391-1392` ("The `content_search` entry uses `available` /
  `unavailable`"), so the doc contradicts itself.
- **Why it matters:** a consumer reading the summary row writes `if status == 'not_derivable'` and gets
  a silent false negative on content search — the exact "capability present when it is absent"
  confusion the `capabilities` verb exists to close.
- **Action:** rewrite the row's Output cell to name both vocabularies, e.g. "Per-capability status —
  `derivable`/`not_derivable` for module edges and path attribution, `available`/`unavailable` for
  content search". Do not change the handler here (that is G2).
- **Done when:** `client-api.md:571` names `available`/`unavailable` for content search, and no
  statement in `client-api.md` claims a single status vocabulary across all three entries.
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
  `doc/user/code-search.adoc:199`), which is how G1's contradiction arose in the first place.
- **Action:** decide one vocabulary for all three entries (`derivable`/`not_derivable` reads best,
  since a crawl that produced an inventory *is* a producer that ran) and change the handler, then
  update `client-api.md § capabilities` (1391-1392 and both worked TOON payloads at 1404 and 1416),
  `doc/user/code-search.adoc:199`, and `test_capabilities.py`.
- **Done when:** all three `capabilities` entries emit the same two status values, `test_capabilities.py`
  asserts the unified vocabulary, and no document mentions a per-entry exception.
- **Effort:** S
- **Risk if fixed:** any consumer already matching on the literal `available` — a tree-wide grep for
  `content_search` and `'available'` must run first; at `61a43e5` the only readers are the docs and
  `test_capabilities.py`.

## G3 — Re-close the heading hierarchy in `client-api.md`

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md:580`
  (`## Error Handling`), with the orphaned H3s at 606, 712, 817, 909, 1144, 1284, 1356
- **Evidence:** the H2 census is `Script Pattern` (7), `Commands` (20), `Resolver provenance` (90),
  `Command Summary` (554), `Error Handling` (580), `Consumer View` (1437), `Data Source` (1448).
  Seven verb sections — `### files`, `### which-module`, `### find`, `### search`, `### diff-modules`,
  `### descriptor-regression-check`, `### capabilities` — sit between 580 and 1437 and therefore render
  as subsections of *Error Handling*. Verbs appended after `resolve` were never re-parented under
  `## Commands`. Recorded as deferred finding 1 in `report-01.md`; unchanged.
- **Why it matters:** any rendered or outline view of the contract files these seven verbs under
  "Error Handling", so a reader scanning for the `search` contract does not find it where the document's
  own structure says verbs live; agents summarising the doc inherit the mis-parenting.
- **Action:** move the seven H3 sections back under `## Commands` (or open a new H2, e.g.
  `## Inventory and search commands`, immediately before `### files` and leave `## Error Handling` where
  it is, after them). Keep section bodies byte-identical; this is a heading/ordering change only.
- **Done when:** every `### <verb>` section in `client-api.md` has an H2 ancestor that is a command
  section, and `## Error Handling` contains only error-handling prose.
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
  at `…/standards/client-api.md:1284` (`### descriptor-regression-check`) and row 577; absent from
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
  `module` genuinely does carry `internal_dependencies`, so the claim is wrong for `info` only.
  Recorded as deferred finding 3 in `report-01.md` (which cites line 34; the sentence is now at 36).
- **Why it matters:** the concepts page is the tier model's authority. Naming `info` as an edge surface
  tells a reader that a Tier 1 answer is available from a Tier 0-only verb, which is exactly the
  cannot-derive / derived-nothing confusion the rest of the page works to eliminate.
- **Action:** change the clause to "plus the adjacency surface of `module`" (or, if `overview` is
  verified to carry adjacency, "of `overview` and `module`"), dropping `info`. Verify `overview`'s
  output against `client-api.md:449` before keeping it in the list.
- **Done when:** `doc/concepts/code-intelligence.adoc` no longer names `info` as an adjacency/edge
  surface, and every verb it does name is confirmed to emit an edge or dependency field.
- **Effort:** S
- **Risk if fixed:** none — a single-clause prose edit.

## G8 — De-duplicate the `--ignore-case` / `--literal` composition rule in `client-api.md § search`

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md:941-946`
  and again at `1111-1116`
- **Evidence:** 941-946 states the flag "adds `re.IGNORECASE` on an axis orthogonal to `--literal`" and
  that "the echoed `ignore_case` boolean names which population the match set was computed over";
  1111-1116 restates both in the edge-case recap. Recorded as deferred finding 4 in `report-01.md`.
- **Why it matters:** two statements of one rule drift apart on the next edit, and the reader cannot
  tell which is authoritative — the failure mode the repository's own "No duplication —
  cross-reference instead" documentation standard exists to prevent.
- **Action:** keep the contract statement at 941-946 and reduce the recap at 1111-1116 to a
  cross-reference, or vice versa — one statement, one place.
- **Done when:** the `--ignore-case`/`--literal` composition rule is stated once in `client-api.md`, with
  any second mention being a pointer.
- **Effort:** S
- **Risk if fixed:** none.

## G9 — De-duplicate the `count` vs `file_count` explanation in `client-api.md § search`

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md:1034-1038`
  and again at `1117-1120`
- **Evidence:** 1034-1038 explains that `count` (rows) and `file_count` (distinct paths) coincide unless
  a file is attributed to two modules; 1117-1120 restates the same distinction and the same "read
  `file_count` for how many files contain this" guidance. Recorded as deferred finding 4 in
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
- **Severity:** medium
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/240-skill-lsp-server/proposal-protocol-surface.md:46`
- **Evidence:** the line reads "…the same zero-adoption signature that condemned the `lsp` query facade
  in plan [`135`](../135-remove-lsp-query-facade/rationale.md)." `report-01.md` § Residue states
  "`rationale.md` lives in the plan directory and **is removed at collect** (git history retains it)."
  The two cannot both hold: when collect removes `rationale.md`, plan 240's live proposal document
  acquires a dangling relative link.
- **Why it matters:** plan 240 is queued, not yet run; its author will follow that link for the reasoning
  it depends on and find nothing. This is the survivor-sweep failure mode ADR-007 names, arriving on a
  schedule rather than at edit time.
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

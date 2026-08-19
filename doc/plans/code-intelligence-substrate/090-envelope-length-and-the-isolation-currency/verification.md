# Verification — 090-envelope-length-and-the-isolation-currency

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** `61a43e5` on `claude/code-intelligence-substrate-analysis-kah884`
**Overall verdict:** CONFIRMED WITH GAPS

The run shipped exactly one of five deliverables (D2) and reported the other three blocked behind its
own D0 gate. Everything the report claims about D2 is true of the tree now (with two quoted reviewer
bodies that are paraphrases rather than verbatim), and the gate resolution is structurally correct.
The gaps are (a) two documentation-quality defects inside the text D2 shipped, (b) two surfaces the
currency correction did not reach — the image alt text and the SVG `<title>`, (c) a mandatory SVG
verification step that was neither performed nor recorded, together with the lane-contract hole that
caused it, (d) two unsourced figures surviving in the section the run deferred, and (e) three
deliverables still open with nothing staged to pick them up.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D0 | GATE: is an instrumented population reachable in this clone? | done — resolved "no population reachable"; D1/D3/D4 blocked, D2 shippable | `.gitignore:45` ignores `.plan/*`; `git ls-files .plan` → 13 tracked files, all `marshal.json` + `project-architecture/**`, no metrics record. Gate resolved without searching, no population fabricated | CONFIRMED |
| D1 | Publish resident context + turns per phase, with populations and ranges | blocked on corpus availability | No such figures anywhere in the run's diff (4 files, all `doc/**`); none invented in the report either | CONFIRMED (correctly blocked) |
| D2 | Restate `token-management.adoc` § 6 in the measured currency | done, commit `4b392bf`, cold-read verified | `doc/concepts/token-management.adoc:49-65` + `doc/resources/diagrams/context-isolation.svg` — argument is in billing-weight/turns-resident currency, recommendation intact, all four figures gone | CONFIRMED (with doc-quality gaps G1, G8 and completeness gap G10) |
| D3 | Settle the creation/read inversion by reading the mechanism | blocked — cannot name the phase without the population | No mechanism named, no remedy shipped, no causal verb without an implementation file. The ⛔ "do not ship a remedy for an inferred mechanism" was honoured | CONFIRMED (correctly blocked) |
| D4 | One envelope-length lever, chosen by D1 | blocked — selection depends on D1 | No code, config or bundle file changed; no split landed | CONFIRMED (correctly blocked) |

## Per-deliverable detail

### D0 — GATE: is an instrumented population reachable?

- **Required (plan, `plan.md:77-83`):** "the run establishes either a reachable population or that none
  is reachable"; if none, HALT D1/D3/D4's selection and report them blocked; D2 still ships; ⛔ do not
  search for the records; do not fabricate a population.
- **Claimed (report, `report-01.md:18-29`):** no population reachable, established from the structural
  fact that `.plan/` is machine-local and git-ignored, *not* by searching.
- **Found:** `.gitignore:45` = `.plan/*`. `git ls-files .plan` returns 13 paths — `.plan/marshal.json`
  and twelve `.plan/project-architecture/**/*.json` files; no run-metrics record is tracked. Nothing
  under `doc/` carries an archived `metrics.toon` population either: `grep -rl cache_read` over
  non-bundle, non-test paths returns 21 files (including one `__pycache__` build artifact and this
  audit's own two documents) — plan prose under `doc/plans/**`, one concept page
  (`doc/concepts/build-management.adoc`), and the retrospective audit skill's own documentation and
  reader script (`.claude/skills/audit-archived-plan-retrospectives/{SKILL.md,checks/*.md,scripts/audit.py}`).
  Every one of them *names* the field; none of them *is* a metrics record.
- **Checks run:** `git ls-files .plan`; `grep -n '^\.plan\|/\.plan' .gitignore`; content sweep for
  `cache_read` outside `marketplace/` and `test/`.
- **Verdict:** CONFIRMED. The gate is resolved in the direction the tree supports, and the consequence
  (three deliverables blocked) is applied consistently.

### D1 — publish the two factors

- **Required (`plan.md:84-92`):** resident context and turns per phase and per envelope across the
  instrumented population, with per-phase population and range; exclude/label re-entered rows.
- **Claimed:** blocked; "no figure fabricated".
- **Found:** the merged diff (`git show --stat 6f1cb7b`) is `doc/concepts/token-management.adoc`,
  `doc/resources/diagrams/context-isolation.svg`, the plan-file rename (`R100`), and `report-01.md`.
  No per-phase table exists in the report, and no band or ratio is quoted anywhere in it.
- **Verdict:** CONFIRMED as blocked. The plan's own gate authorises this outcome. Note that the
  *emission* half was already landed by the sibling plan 030 (PR #1154):
  `manage-metrics/scripts/manage-metrics.py:1539` writes
  `cache_read_per_tool_use = round(cache_read_input_tokens / tool_uses)` and
  `manage-metrics/standards/data-format.md:49,146,237-244` publishes the identity and the population
  span — so the out-of-scope rule "do not add a second writer" was respected (this run touched no
  bundle file at all), but the report never records that check (G7 adjacency; see Report accuracy).

### D2 — restate § 6 in the measured currency

- **Required (`plan.md:93-100`):** § 6's argument in billing-weight terms; recommendation unchanged;
  every surviving figure re-derived or removed; verified by cold read.
- **Claimed (`report-01.md:41-59`):** all three done; figures `10-15 K`, `30-50 K`, `~6 K`,
  `~200-500 tokens` removed in prose *and* diagram; diagram's `≈ 6 K` caption recast.
- **Found:**
  - `doc/concepts/token-management.adoc:51` opens § 6 with "the currency in which it pays out is
    *turns-resident*, not orchestrator-context size" and states the model
    `cost(byte) = creation_multiplier + read_multiplier × turns_remaining` (`:54`).
  - `:51` retains the recommendation verbatim: "The biggest single token-management lever".
  - `:63` carries the corrected claim: isolation "does **not** make a byte cheaper to create … it is
    *additive to the bill*, not free. What isolation changes is **residency**."
  - Figure sweep over § 6 (lines 49-66): the only digits present are `6.` (the heading), `5-execute`
    and `8-step`. No quantitative figure survives.
  - Diagram: `context-isolation.svg` contains no `K`, `~`, `%` or range token in any text node; the
    old `~5 K + 3 × ~300 ≈ 6 K` caption is now "bounded resident turns" (file line 122, `y="488"`),
    the three `~10–15 K` box labels are now "few resident turns", `~200 – 500 tokens each` is now
    "its context never re-enters a later turn", and `<desc>` (line 8) is re-cast to residency. The
    commit replaces **14** `<text>` nodes plus the `<desc>`. `<title>` (line 7) is **not** in the
    diff and still reads "single growing context vs orchestrator-plus-execution-context-variants" —
    the pre-correction currency, surviving on an accessibility surface (→ G10).
  - Pre-state confirmed from the merge commit: `git show 6f1cb7b -- doc/concepts/token-management.adoc`
    shows the removed sentence "with each `execution-context-{level}` variant's larger context being
    independent — and never additive".
- **Checks run:** a read of `:49-65` against the gate's two questions (my reading: the currency is
  billing weight / turns-resident, and isolation is unambiguously *recommended*, not questioned).
  ⚠ This is **not** a cold read and cannot stand in for one: I had already read `plan.md` and
  `report-01.md`, so I knew the intended conclusion before reading the text. It establishes that the
  text *supports* both required answers on a primed read; it does not re-run the gate. Also: digit
  sweep over the § 6 line range; text-node dump of the SVG; `xml.etree` parse of the SVG
  (well-formed, 51 `<text>` nodes, viewBox `0 0 1000 620`); `grep -rn "never additive"` across
  `doc/`, `marketplace/bundles/`, `.claude/` — outside this audit's own two files, the only
  occurrences are this plan's `plan.md:56` and `report-01.md:44`, plus the explicitly-corrective
  parenthetical at `token-management.adoc:63`.
- **Verdict:** CONFIRMED on the literal *Done when*, with two quality defects inside the shipped text
  (G1: the transitional parenthetical violates the repository's "Current state only" documentation
  standard; G8: a new unsourced comparative claim replaced the deleted figures), one residue of the
  currency correction on the two non-visual description surfaces (G10: the `.adoc` image alt text and
  the SVG `<title>` were left in orchestrator-context framing), and one process omission on the
  co-shipped artifact (G4/G5: the mandatory SVG rasterise-and-read-back step).

### D3 — settle the creation/read inversion

- **Required (`plan.md:101-109`):** name the mechanism with the symbol that enacts it and state its
  addressability, **or** record it refuted; ⛔ read the mechanism, do not infer it; ⛔ do not ship a
  remedy for an inferred mechanism.
- **Claimed:** blocked — the inversion's phase is identified from the population, which is absent.
- **Found:** the report names no symbol and no mechanism, and the diff ships no remedy. The sibling
  plan 030 reached the same place independently — `030-.../report-01.md:69` records its D3 as
  "inversion = not-established/corpus-blocked".
- **Verdict:** CONFIRMED as blocked. The failure mode the deliverable guards against (a causal verb
  with no implementation file behind it) does not occur anywhere in the report.

### D4 — one envelope-length lever

- **Required (`plan.md:110-118`):** land the split D1 identifies; preserve what is examined; state the
  continuity cost.
- **Claimed:** blocked, selection depends on D1.
- **Found:** no change to `marketplace/bundles/**`, no change to `.plan/marshal.json` defaults, no
  change to the packing budget documented at `doc/user/configuration.adoc:355-356`
  (`[#per-envelope-packing-budget]`). The plan's "check whether D4 is a config default rather than a
  code change" prompt was therefore never exercised — correctly, since selection was gated.
- **Verdict:** CONFIRMED as blocked.

## Correctness review

No executable code shipped, so there is no fail-open branch, guard, or rounding to review. What I read
instead was the shipped prose and markup, and the surfaces it points at:

1. **`token-management.adoc:63` — transitional narration.** The parenthetical "(The older phrasing that
   a variant's context is "never additive" held only of the *orchestrator's* context …)" documents what
   the document used to say. `ref-documentation/references/organization-standards.md:133-139` ("Current
   State Only": "Remove transitional, status, or deprecation information", "Eliminate 'changed from X
   to Y' references") and `CLAUDE.md` § Documentation Standards ("No version history", "Current state
   only") both forbid it, and the lane carve-out explicitly does **not** exempt documentation
   standards. → G1.
2. **`token-management.adoc:63` — an unsourced comparative replaced the deleted figures.** "its own
   cost, re-creating each envelope's starting context, is bounded and small against the run-length read
   cost it removes" is the load-bearing justification for calling isolation the biggest lever, and it is
   quantitative in substance. The run deleted four figures on the stated ground that the population
   needed to re-derive them was unreachable, then shipped this comparative from the same unreachable
   population. The repository's own published billing weights make the comparison non-obvious rather
   than self-evident: `manage-metrics/standards/data-format.md:48` defines
   `billing_weighted_total = input + output + round(0.1 × cache_read) + round(1.25 × cache_creation)`,
   so a *created* byte is billed **12.5×** a *read* byte. Re-creating an envelope's starting context
   `n` extra times is therefore "small" only where the residency it removes exceeds `12.5 × n` turns —
   a condition, not a magnitude the document has established. → G8.
3. **`token-management.adoc:51-54` — the cost model states no mechanism.** "billed once at a creation
   multiplier and again, at a smaller read multiplier" is true under prompt caching and is exactly what
   `cache_creation_input_tokens` / `cache_read_input_tokens` measure, but § 6 names neither the
   mechanism nor the fields, even though the sibling plan landed the decomposition
   (`manage-metrics/standards/data-format.md:237-244`). → G9.
4. **Geometry of the edited SVG — checked, no defect found.** The replaced labels sit in fixed-width
   boxes: `x=170 width=160` (left column, `<rect>` at `:41`) and `x=535/685/835 width=120` (dispatch
   boxes, `:86`/`:94`/`:102`). The longest **new** string that lands *inside a box* is
   "(and risks window overflow)" (27 chars at `font-size: 11px`, `:68`), which is one character
   *shorter* than the "(or context-window overflow)" it replaced; the next longest, "resident for the
   whole run" (26 chars, `:46`), is one character longer than the unchanged neighbour in the same box,
   "Tool calls + tool outputs" (25 chars, `:49`). No box therefore receives a string longer than one it
   already carried, so no new overflow is introduced. (Longer new strings exist — "each byte is re-read
   only while its envelope is live:", 52 chars at `:121` — but they are free-standing captions at
   `text-anchor: middle`, not box-bounded, and at ~5.5 px/char centre on `x=750` inside a 1000-unit
   viewBox.) This is an analytic check only — no rasteriser is available in this environment
   (`rsvg-convert`, `inkscape`, `chromium` absent; `cairosvg` not importable), which is precisely why
   the skill's own rule requires the author to do it. → G4.
5. **Pointer integrity — checked, clean.** `image::../resources/diagrams/context-isolation.svg`
   resolves; the `xref:../user/configuration.adoc#per-envelope-packing-budget` anchor exists at
   `doc/user/configuration.adoc:355`; `manage-metrics accumulate-agent-usage` (cited at `:78`) exists
   at `manage-metrics/SKILL.md:368`.
6. **No competing currency claim survives elsewhere.** `grep -rn "isolation" doc/concepts/*.adoc`
   returns only worktree/reader isolation in other pages; `execution-context.adoc:52` says "No tokens
   are billed to the orchestrator during the suspension — only the subagent's `<usage>` is counted",
   which names its boundary and is consistent with the corrected § 6.
7. **The two non-visual descriptions of the diagram were not carried with the correction.** The commit
   rewrote the SVG's `<desc>` and every visible label into residency framing, but left both surfaces a
   non-visual reader actually gets in the pre-correction currency: the AsciiDoc image alt text
   (`token-management.adoc:61`, still "into one growing context heading toward the token-window limit"
   — the commit touched that line only to strip `(~200-500 tokens)`) and the SVG `<title>`
   (`context-isolation.svg:7`, still "single growing context vs
   orchestrator-plus-execution-context-variants"). Neither is *false*, and D2's literal *Done when*
   does not reach them, so this is a completeness defect rather than a correctness one. → G10.
8. **A second unsourced figure survives in the section the run deferred.** Beside the `~10-15 K` the
   run declared as residue (G2), `token-management.adoc:76` carries "adding ~5-10 dispatches the change
   itself doesn't need" — an unsourced count in the same bullet list, surviving the same sweep and
   never mentioned in the report. → G3.
9. **The lane contract routes no run to the SVG gate.** `.claude/skills/cloud-plan-lane/SKILL.md`
   Step 1's conditional skill table (`:104-115`) maps seven surfaces to skills and has no SVG-diagram
   row; `grep -rn "ref-svg-diagrams"` over `.claude/`, `CLAUDE.md` and `marketplace/bundles/pm-documents/skills/ref-asciidoc/`
   finds no pointer a lane run would encounter. This run followed the table faithfully and never saw
   `ref-svg-diagrams`' mandatory gate — G4 is the consequence, not an independent lapse. → G5.

## Test adequacy

**No test is warranted and none was written.** The run's entire footprint is `doc/**`: one `.adoc`, one
`.svg`, one file rename and one report (`git show --stat 6f1cb7b` → 4 files, 183 insertions, 18
deletions). There is no production symbol to cover, so no mutation sweep was performed and none is
owed; the "prove vacuity by mutating" instruction has no target here.

Two adjacent observations:

- The repository has no automated guard over `doc/concepts/**` prose that would have caught G1 — the
  `plugin-doctor` rule catalogue governs `marketplace/bundles/**` skills, not concept documents, and
  `pm-documents:recipe-doc-verify` is an on-demand recipe, not CI. I record this as context, not as a
  gap; building doc-lint is far outside this plan's scope.
- The only *executable* verification the change could have had is the `ref-svg-diagrams` rasterise gate
  (`marketplace/bundles/pm-documents/skills/ref-svg-diagrams/SKILL.md:25`), and it was not run. That is
  G4.

## Report accuracy

Every substantive claim in `report-01.md` was checked against the tree and against GitHub. All held,
with two immaterial staleness notes and one unverifiable item.

| Report claim | Status |
|---|---|
| PR [#1185](https://github.com/cuioss/plan-marshall/pull/1185), opened 17:24 UTC, 2026-08-12 | **True.** `created_at: 2026-08-12T17:24:54Z`, merged `17:45:55Z`. |
| Branch `claude/envelope-length-isolation-currency-kmo78n`, harness-assigned, kept | **True.** PR `head.ref` is exactly that. |
| Diff scope "4 files, all `doc/**`, incl. a pure `R100` rename" | **True.** `git show -M --name-status 6f1cb7b`: `M` adoc, `R100` `090-….md` → `090-…/plan.md`, `A` report, `M` svg. PR reports `changed_files: 4`, `additions: 183`, `deletions: 18`. |
| `git diff --name-only origin/main...HEAD -- '*.py'` empty → build skipped | **True.** No `.py` path in the merged diff. |
| Figures `10-15 K`, `30-50 K`, `~6 K`, `~200-500 tokens` removed in prose and diagram | **True for the surface the plan scoped — § 6 and the SVG.** Verified in the merge diff and by digit sweep of § 6 and the diagram. **Not true of the whole document:** `~10-15 K tokens of variant context` survives outside § 6, at `doc/concepts/token-management.adoc:75` (§ "Where Plan Marshall deliberately spends more"), which the residue row below records as still open. → G2 |
| Diagram caption `~5 K + 3 × ~300 ≈ 6 K` recast to bounded-residency framing | **True.** Replaced by "bounded resident turns"; the whole right-column caption block was rewritten. |
| Isolation recommendation unchanged | **True.** "The biggest single token-management lever" survives at `:51`. |
| Commits carry the `Co-Authored-By: Claude` trailer | **True** for all four PR commits, including the final `5abb757` (verified via `get_commit` — the trailer is present; a truncated `get_commits` listing initially suggested otherwise). |
| `cuioss-review-bot` posted "PR Reviewer Guide … No major issues detected" | **True in substance** (issue comment `5270148041`). Not verbatim as one line: the body is an HTML table whose three cells read "No relevant tests", "No security concerns identified", "No major issues detected"; the report flattens it. Each quoted phrase is exact. |
| `coderabbitai` skipped: "only excluded labels are configured: skip-bot-review" | **True in substance, not verbatim** (comment `5270142333`). The body reads "Review skipped / Auto reviews are limited based on label configuration." with a details block "Excluded labels (none allowed) (1) · skip-bot-review". The phrase "only excluded labels are configured" appears nowhere in it; the report presents a paraphrase in quotation marks. The PR does carry the `skip-bot-review` label. |
| `sourcery-ai` refused: "weekly rate limit of 500000 diff characters" | **True**, verbatim substring (review `4919279311`, submitted `17:25:00Z` on commit `073fe7a`; full body opens "Sorry @cuioss-oliver, you have reached your weekly rate limit …"). |
| Reviewer set derived from `automatic-review/standards/{bot_kind}.md` `author_login` | **True.** `coderabbit.md:36` → `coderabbitai`; `sourcery.md:29` → `sourcery-ai`; `pr-agent.md:58` → `cuioss-review-bot`. |
| "the same set is named by `.github/workflows/pr-agent.yml`" | **True**, at `.github/workflows/pr-agent.yml:1`, verbatim: `# Third automated PR reviewer (PR-Agent on Google Gemini), beside CodeRabbit and Sourcery.` — named as bot kinds, not logins. |
| D2 commit `4b392bf` | **True but not resolvable on `main`.** It exists on the PR branch (`get_commits` returns `4b392bfab12…`); the repository squash-merges, so `main` carries `6f1cb7b` instead. A repo-wide convention, not a defect of this report. |
| "Required check concluded `success` on head `073fe7a`" | **True of that head, and stale for the merged head** — `073fe7a` was head at PR-open; the run then pushed `5abb757`. Independently verified that the *merged* head is also green: `verify / conclusion` = `success`, `verify / gate` = `success`, `dependency-review` = `success`, `verify / verify` = `skipped` (docs-only path). No merge-gate risk; noted for precision only. |
| "`review / review` … `success`" | **UNVERIFIABLE now.** The PR-head check-run set (on `5abb757`) contains no `review / review` entry; PR-Agent subscribes only to `opened`/`reopened`/`ready_for_review` (`pr-agent.yml:12-14`), so it can only have run on `073fe7a`, whose check set this tool cannot address by SHA. Consistent with the report; not independently confirmed. |
| "One verification sub-agent reported `subagent_tokens: 70038`, `tool_uses: 14`" | **UNVERIFIABLE** — a session-local figure with no durable record; correctly labelled in the report as one dispatch, not a run total. |
| Cold-read gate passed (Findings row 1) | **Consistent, not independently re-run.** My own read of the revised § 6 reached both required conclusions (currency = billing weight/turns-resident; isolation recommended, not questioned), but it was a *primed* read — the plan and report were already in context — so it cannot re-run a gate whose whole point is an unprimed reader. The gate's outcome rests on the run's own sub-agent dispatch, which leaves no durable artifact. |

**Not claimed, and missing:** the report never records the § 4 check the plan's Expected surface asks
for (`plan.md:141`: "§ 6 (and § 4's figures)"), and never records the coordination check the plan's
Notes require (`plan.md:181-183`, the WS-04 emission plan). Both were in fact satisfied — § 4
("Skill-driven guidance") carried no numeric figure before or after the change, and no second writer
was added — but a reader cannot tell from the report whether they were checked or overlooked. → G7.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| D1, D3, D4 blocked on corpus availability; pick up in a run with a reachable population | **Open.** Nothing is staged. | `grep -rln "090-envelope\|envelope-length" doc/` returns this plan's own directory only (`plan.md`, `report-01.md`, and this audit's own two files); `grep -rln "turns_resident\|turns-resident\|envelope split"` over `doc/plans/` returns the same directory and nothing else. No sibling plan in `doc/plans/**` references this plan's residue; the epic `README.md` carries no per-plan status (verified — it is 9 lines, theme and contract only). → G6 |
| Pre-existing duplicate figure `~10-15 K tokens of variant context` in § "Where Plan Marshall deliberately spends more" | **Open.** | `doc/concepts/token-management.adoc:75`, Q-Gate bullet, verbatim: "a measurable extra `execution-context-{level}` dispatch per phase, ~10-15 K tokens of variant context". → G2 |
| "What have we learned": propose noting that MCP `get` returns `mergeable_state` (lowercase), not `mergeStateStatus` | **Closed by a later plan.** | `git log -S "the MCP payload names this field \`mergeable_state\`" -- .claude/skills/cloud-plan-lane/SKILL.md` → `ea1ac4b … (#1190)`. The note is live at `.claude/skills/cloud-plan-lane/SKILL.md:72` and `:1333-1336`. |

## Out-of-scope and collateral

The plan forbade four things. All four held:

- **Reducing what is examined** — nothing was removed from any workflow; no bundle file changed.
- **Weakening per-dispatch isolation** — the recommendation survives verbatim (`:51`), and the rewrite
  strengthens rather than qualifies it. My own cold read confirms a reader is not left doubting it.
- **Reordering the dispatch prompt for cache-prefix sharing** — untouched; no dispatch-prompt or
  agent-contract file is in the diff.
- **Emitting the two factors (second writer)** — untouched. `manage-metrics` is unchanged by this run;
  the emitter added by plan 030 (`manage-metrics.py:1539`) is the sole writer.

No collateral change: the diff is exactly the four `doc/**` paths, and the plan-file rename is `R100`
(pure move, no content change).

## Plan-level obligations beyond the five deliverables

- **`plan.md` § Verification bullet 4 — "Full `./pw verify` per the lane contract's build gate".** The
  contract's gate is conditional on a git-derived Python-change check (`CLAUDE.md` § Standalone Plan
  Lane), and the merged diff contains no `*.py` path, so the correct outcome was *skip*. Discharged.
- **`plan.md` § Claim labels (the seven-row table).** Six rows are authoring provenance for the plan's
  own premises and impose no run obligation. The one row that names a clone-reachable artifact to read
  — the dispatch token-order claim, "The execution-context agent contract under
  `marketplace/bundles/plan-marshall/skills/`. Read it." — supports the *out-of-scope* exclusion of
  prefix reordering, which the run correctly did not act on. Nothing was owed and nothing is missing.
- **`plan.md` § Expected surface bullet 3 — "check whether D4 is a config default rather than a code
  change".** Gated behind D1's selection; correctly not exercised (see D4).

## Method and coverage

**Checked, and how.**

- Read `plan.md` and `report-01.md` in full, plus the epic `README.md`.
- Recovered the merge commit `6f1cb7b` (PR #1185). The audit clone is shallow (50 commits, `.git/shallow`
  present), so the commit was initially unreachable; I ran `git fetch --deepen=200`, which brought the
  history to 262 commits and made `6f1cb7b` and the pre-change file state (`6f1cb7b^`) readable. This
  fetch is read-only — no branch, commit, or push was made, and nothing outside this plan directory was
  modified.
- Compared pre- and post-change § 6 line by line from the merge diff; swept the current § 6 line range
  for digits; dumped every `<text>` node of the SVG and diffed the SVG hunk-by-hunk.
- Queried GitHub for PR #1185: `get`, `get_commits`, `get_check_runs`, `get_comments`, `get_reviews`,
  and `get_commit` on the final head — this is how every reviewer, CI and commit claim above was
  checked against the primary source rather than against the report.
- Verified the residue's three items against the current tree and against later history.
- Verified pointer targets (image path, `xref` anchor, `manage-metrics` subcommand), the reviewer
  registry logins, the `.gitignore` rule, and the sibling emitter symbol.

**Could not check.**

- The `review / review` check conclusion on the pre-final head `073fe7a` (the tool set addresses check
  runs by PR head only). Marked UNVERIFIABLE above.
- The verification sub-agent's self-reported token/tool figures — no durable record exists.
- Visual rendering of the SVG: no rasteriser is installed in this environment (`rsvg-convert`,
  `inkscape`, `convert`, `chromium` all absent; `cairosvg` not importable), so the overflow judgement in
  Correctness review §4 is analytic (character count against box width and against pre-existing
  neighbour strings), not visual.

**Search-hygiene note.** One filtered search produced a false negative during this audit: a
case-sensitive `grep -n "coderabbit\|sourcery" .github/workflows/pr-agent.yml` returned nothing, which
would have made the report's workflow claim look false. Reading the file showed the names present as
`CodeRabbit` and `Sourcery` at line 1. Every negative result reported above was confirmed by a positive
control (the same pattern matching where it is known to exist) before being stated.

## Adversarial review

Independent review of this document and `gaps.md`. Attacks run: A1 false positives, A2 false
negatives, A3 vacuous evidence, A4 counts and quotes, A5 actionability, A6 severity/topic,
A7 coverage, A8 internal consistency.

Re-derived at tree state `57c63a8` (the audit itself was written at `61a43e5`). Every `path:line` in
both documents was opened; every count was re-run; every quoted string was diffed against its source.

| # | Attack | What was found | Correction applied |
|---|---|---|---|
| A1 | False positives | **One false claim.** The D2 detail asserted "`<title>`/`<desc>` (lines 7-8) are re-cast to residency". `git show 6f1cb7b -- doc/resources/diagrams/context-isolation.svg` shows `<title>` only as an unchanged context line; it still reads "single growing context vs orchestrator-plus-execution-context-variants". `<desc>` alone was rewritten. Every other gap and non-CONFIRMED verdict was re-opened at its citation and holds: G1 (`adoc:63`), G2 (`:75`), G3 (`:76`), G8 (`:63`), G9 (`:51-57`, Related link at `:91`) are all verbatim-present; G4's rule is at `ref-svg-diagrams/SKILL.md:25` with the Step 4 recipe at `:88`; G5's table has no SVG row; G6's blockage is real (`git ls-files .plan` → 13 files, none a metrics record). | Claim corrected in the D2 detail and the surviving `<title>` promoted into a new gap (**G10**). |
| A1 | Stale citations | `.claude/skills/cloud-plan-lane/SKILL.md:106-116` (G5) — the table actually spans `104-115` (heading `:104`, header `:107`, seven rows `:109-115`). `(:488 region)` for the SVG caption was a `y` coordinate presented as a line cite; the file is 131 lines and the node is at line 122. | Both corrected. |
| A2 | False negatives | **One real miss.** The currency correction stopped short of the two surfaces a non-visual reader receives: the `image::` alt text at `adoc:61` still says "into one growing context heading toward the token-window limit" (the commit touched that line only to strip `(~200-500 tokens)`), and the SVG `<title>` was never touched — so `<title>` and `<desc>` now describe the same picture in two different currencies. Neither string is false and D2's literal *Done when* does not reach them, so D2 stays CONFIRMED. Separately: the audit's own § 6 verdict is strengthened, not overturned, by the published billing weights — `data-format.md:48` bills creation at `1.25` and read at `0.1`, i.e. **12.5×**, which makes G8's "bounded and small" a *condition* rather than a magnitude. Deliberately **not** raised after checking: "isolation isn't just cheaper" at `:69` reads consistently with § 6's net-cost claim; "the one mechanism that attacks that factor" at `:57` is arguable against § 2's build suspension but defensible as written. | **G10** added (low, `documentation-surface`); the `1.25`/`0.1` asymmetry added to G8's evidence and to Correctness review item 2. |
| A3 | Vacuous evidence | **No mutation sweep to re-run.** `git show --stat 6f1cb7b` is 4 files, all `doc/**`, no `*.py` — the audit's "no test warranted" is correct, and the "prove vacuity by mutating" instruction has no target. No production file was mutated or restored by this review; `git status --porcelain` shows the only paths this review touched are this plan directory's `verification.md` and `gaps.md` (other modified paths in the tree belong to concurrent agents). **One evidence claim did not survive:** the audit called its own § 6 read a "cold read" and used it to corroborate the run's cold-read gate. It was a *primed* read — plan and report were already in context — so it shows the text supports both required answers, but it cannot re-run a gate whose premise is an unprimed reader. Everything else rests on checks that could have come back different (`git ls-files`, digit sweep, XML parse, GitHub API), and two of them did: one claim came back UNVERIFIABLE and one stale. | Both the D2 "Checks run" bullet and the Report-accuracy row re-labelled from "cold read / Corroborated" to a primed read that is consistent but not a re-run. |
| A4 | Counts and quotes | **Three numeric errors and two mis-quotes.** (1) G4 said "11 text nodes replaced" — the diff replaces **14** `<text>` nodes plus the `<desc>`. (2) "resident for the whole run" is **26** characters, not 25 (both documents). (3) Correctness review §4 called it "the longest new string" and compared it to "(and risks window overflow)" as a "pre-existing neighbour" — that string is itself **new** (it replaced the 28-char "(or context-window overflow)"), and the longest new string in the commit is the 52-char free-standing caption at `:121`. (4) The report's `coderabbitai` quote "only excluded labels are configured: skip-bot-review" appears nowhere in comment `5270142333`; the body reads "Review skipped / Auto reviews are limited based on label configuration" with a details block "Excluded labels (none allowed) (1) · skip-bot-review" — the audit marked a paraphrase-in-quotation-marks as "True" without flagging it. (5) `pr-agent.yml:1` was quoted as "PR-Agent on Google Gemini, beside CodeRabbit and Sourcery"; the line is `# Third automated PR reviewer (PR-Agent on Google Gemini), beside CodeRabbit and Sourcery.`. Also refined: the `cache_read` sweep returns 21 paths including a `__pycache__` artifact, `audit.py`, and `build-management.adoc` — not only "plan prose and skill documentation" as stated, though none is a metrics record so D0's conclusion is unaffected. **Re-derived and confirmed unchanged:** 13 tracked `.plan` files; `.gitignore:45`; 51 `<text>` nodes; viewBox `0 0 1000 620`; rects `x=170 w=160` / `x=535,685,835 w=120`; 4 files / 183 insertions / 18 deletions; PR #1185 `created_at 17:24:54Z`, `merged_at 17:45:55Z`, `head.ref`, `changed_files: 4`, `commits: 4`, `skip-bot-review` label; six check runs on head `5abb757` with no `review / review`; `manage-metrics.py:1539`; `data-format.md:49,146,237-244`; `030-.../report-01.md:69`; `ea1ac4b (#1190)`; the three reviewer `author_login` registry lines. | All five corrected in place; the confirmed figures left as they stood. |
| A5 | Actionability | Every entry already carried a concrete `path`, change and observable *Done when*; none used "review/consider/investigate". **Two were not executable as written.** G4's *Done when* required a rasterisation the audit had itself established is impossible in this environment, with no instruction for that case. G6's *Done when* required a per-plan status line in the epic `README.md`, which contradicts `doc/plans/README.md` § Layout — the directory shape *is* the status signal there, so the requirement would push a fixing run into a convention violation. | G4 given an explicit no-rasteriser branch (record the coverage gap, never skip silently). G6's *Done when* re-cast as a grep for a successor plan naming this plan, with the README instruction dropped and the reason stated. G7's action re-cast as a marked addendum rather than an edit to a dated run record. |
| A6 | Severity and topic | All ten severities re-derived against the calibration and all topics against the owning surface; **no re-severity or re-topic applied.** Challenged and upheld: **G1** at medium (an explicit, enforced repository documentation standard violated in a shipped concept page is more than "cosmetic doc inconsistency", though low is defensible); **G8** at medium, not high (an unsourced comparative is not a misreported measurement); **G5** at medium, not high (a routing hole in a contract, not a wrong behaviour); **G6** topic `measurement/metrics`, not `plan-lane-contract` (D1/D3 own the metrics surface; the lane is incidental); **G7** topic `documentation-surface` for want of a report topic in the closed list. New **G10** set at low: both strings are descriptive and true, and D2's *Done when* does not reach them. | None. |
| A7 | Coverage | All five deliverables, the four out-of-scope prohibitions, report accuracy and the three residue items were covered. **Three plan-level obligations were unmentioned**: the § Verification `./pw verify` bullet, the seven-row Claim-labels table, and the Expected-surface "config default rather than a code change" prompt. All three are in fact discharged or correctly gated, but a reader could not tell they had been looked at. | New section **"Plan-level obligations beyond the five deliverables"** added, discharging each. |
| A8 | Internal consistency | The overall verdict follows from the rows (five CONFIRMED, gaps confined to quality and residue). **Two gaps did not trace back:** **G3** (the `~5-10 dispatches` figure) appears nowhere in `verification.md`, and **G5**'s actual basis — the lane table's missing SVG row — was referenced only in passing inside the D2 verdict, never established. Conversely every finding in `verification.md` that warrants action does reach `gaps.md`. | Correctness review items **8** (G3) and **9** (G5) added; item **7** added for the new G10; the opening summary and the D2 verdict row updated to match the ten-gap list. |

**Residual doubt:** the one check neither the audit nor this review could perform is the mandatory
rasterisation of `context-isolation.svg` — no rasteriser is installed here (`rsvg-convert`, `inkscape`,
`convert`, `chromium` absent; `cairosvg` not importable), so both the audit's overflow judgement and my
correction of it are analytic. A further round with a working rasteriser is the most likely place to
find something new, and the plausible find is a clipped or colliding label in the left column's
`width=160` box, where the replaced strings are longest relative to the container. Second most likely:
the run's cold-read gate cannot be re-run by anyone who has read this plan, so its outcome rests
permanently on the run's own undocumented sub-agent dispatch.

**Verdict on the audit:** SOUND AFTER CORRECTION — every gap it raised is real and every deliverable
verdict survived re-derivation, but it shipped one false claim about the SVG `<title>`, three miscounts,
two paraphrases accepted as verbatim quotes, one miss (the two description surfaces the currency
correction never reached, now G10), and two gaps that traced to nothing in its own body.

# Verification — 090-envelope-length-and-the-isolation-currency

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** `61a43e5` on `claude/code-intelligence-substrate-analysis-kah884`
**Overall verdict:** CONFIRMED WITH GAPS

The run shipped exactly one of five deliverables (D2) and reported the other three blocked behind its
own D0 gate. Everything the report claims about D2 is true of the tree now, and the gate resolution is
structurally correct. The gaps are (a) two documentation-quality defects inside the text D2 shipped,
(b) a mandatory SVG verification step that was neither performed nor recorded, and (c) three
deliverables still open with nothing staged to pick them up.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D0 | GATE: is an instrumented population reachable in this clone? | done — resolved "no population reachable"; D1/D3/D4 blocked, D2 shippable | `.gitignore:45` ignores `.plan/*`; `git ls-files .plan` → 13 tracked files, all `marshal.json` + `project-architecture/**`, no metrics record. Gate resolved without searching, no population fabricated | CONFIRMED |
| D1 | Publish resident context + turns per phase, with populations and ranges | blocked on corpus availability | No such figures anywhere in the run's diff (4 files, all `doc/**`); none invented in the report either | CONFIRMED (correctly blocked) |
| D2 | Restate `token-management.adoc` § 6 in the measured currency | done, commit `4b392bf`, cold-read verified | `doc/concepts/token-management.adoc:49-65` + `doc/resources/diagrams/context-isolation.svg` — argument is in billing-weight/turns-resident currency, recommendation intact, all four figures gone | CONFIRMED (with two doc-quality gaps: G1, G8) |
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
  under `doc/` carries an archived `metrics.toon` population either (`grep -rl cache_read` over
  non-bundle, non-test paths returns only plan prose and skill documentation).
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
    old `~5 K + 3 × ~300 ≈ 6 K` caption is now "bounded resident turns" (`:488` region), the three
    `~10–15 K` box labels are now "few resident turns", `~200 – 500 tokens each` is now "its context
    never re-enters a later turn", and `<title>`/`<desc>` (lines 7-8) are re-cast to residency.
  - Pre-state confirmed from the merge commit: `git show 6f1cb7b -- doc/concepts/token-management.adoc`
    shows the removed sentence "with each `execution-context-{level}` variant's larger context being
    independent — and never additive".
- **Checks run:** independent cold read of `:49-65` (my reading: the currency is billing weight /
  turns-resident, and isolation is unambiguously *recommended*, not questioned — the cold-read gate's
  two questions both answer the way the deliverable requires); digit sweep over the § 6 line range;
  text-node dump of the SVG; `xml.etree` parse of the SVG (well-formed, 51 `<text>` nodes, viewBox
  `0 0 1000 620`); `grep -rn "never additive"` across `doc/`, `marketplace/bundles/`, `.claude/` —
  the only surviving occurrences are inside this plan's own `plan.md:56` and `report-01.md:44`, plus
  the explicitly-corrective parenthetical at `token-management.adoc:63`.
- **Verdict:** CONFIRMED on the literal *Done when*, with two quality defects inside the shipped text
  (G1: the transitional parenthetical violates the repository's "Current state only" documentation
  standard; G8: a new unsourced comparative claim replaced the deleted figures) and one process
  omission on the co-shipped artifact (G4/G5: the mandatory SVG rasterise-and-read-back step).

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
   population. → G8.
3. **`token-management.adoc:51-54` — the cost model states no mechanism.** "billed once at a creation
   multiplier and again, at a smaller read multiplier" is true under prompt caching and is exactly what
   `cache_creation_input_tokens` / `cache_read_input_tokens` measure, but § 6 names neither the
   mechanism nor the fields, even though the sibling plan landed the decomposition
   (`manage-metrics/standards/data-format.md:237-244`). → G9.
4. **Geometry of the edited SVG — checked, no defect found.** The replaced labels sit in fixed-width
   boxes: `x=170 width=160` (left column) and `x=535/685/835 width=120` (dispatch boxes). The longest
   new string, "resident for the whole run" (25 chars at `font-size: 11px`), is no longer than
   pre-existing neighbours in the same box ("Tool calls + tool outputs", 25 chars;
   "(and risks window overflow)", 27 chars), so no new overflow is introduced. This is an analytic
   check only — no rasteriser is available in this environment (`rsvg-convert`, `inkscape`, `chromium`
   absent; `cairosvg` not importable), which is precisely why the skill's own rule requires the author
   to do it. → G4.
5. **Pointer integrity — checked, clean.** `image::../resources/diagrams/context-isolation.svg`
   resolves; the `xref:../user/configuration.adoc#per-envelope-packing-budget` anchor exists at
   `doc/user/configuration.adoc:355`; `manage-metrics accumulate-agent-usage` (cited at `:78`) exists
   at `manage-metrics/SKILL.md:368`.
6. **No competing currency claim survives elsewhere.** `grep -rn "isolation" doc/concepts/*.adoc`
   returns only worktree/reader isolation in other pages; `execution-context.adoc:52` says "No tokens
   are billed to the orchestrator during the suspension — only the subagent's `<usage>` is counted",
   which names its boundary and is consistent with the corrected § 6.

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
| Figures `10-15 K`, `30-50 K`, `~6 K`, `~200-500 tokens` removed in prose and diagram | **True.** Verified in the merge diff and by digit sweep of the current file and SVG. |
| Diagram caption `~5 K + 3 × ~300 ≈ 6 K` recast to bounded-residency framing | **True.** Replaced by "bounded resident turns"; the whole right-column caption block was rewritten. |
| Isolation recommendation unchanged | **True.** "The biggest single token-management lever" survives at `:51`. |
| Commits carry the `Co-Authored-By: Claude` trailer | **True** for all four PR commits, including the final `5abb757` (verified via `get_commit` — the trailer is present; a truncated `get_commits` listing initially suggested otherwise). |
| `cuioss-review-bot` posted "PR Reviewer Guide … No major issues detected" | **True**, verbatim (issue comment `5270148041`). |
| `coderabbitai` skipped: "only excluded labels are configured: skip-bot-review" | **True** (comment `5270142333`); the PR does carry the `skip-bot-review` label. |
| `sourcery-ai` refused: "weekly rate limit of 500000 diff characters" | **True**, verbatim (review `4919279311`, on commit `073fe7a`). |
| Reviewer set derived from `automatic-review/standards/{bot_kind}.md` `author_login` | **True.** `coderabbit.md:36` → `coderabbitai`; `sourcery.md:29` → `sourcery-ai`; `pr-agent.md:58` → `cuioss-review-bot`. |
| "the same set is named by `.github/workflows/pr-agent.yml`" | **True**, at `.github/workflows/pr-agent.yml:1` ("PR-Agent on Google Gemini, beside CodeRabbit and Sourcery") — named as bot kinds, not logins. |
| D2 commit `4b392bf` | **True but not resolvable on `main`.** It exists on the PR branch (`get_commits` returns `4b392bfab12…`); the repository squash-merges, so `main` carries `6f1cb7b` instead. A repo-wide convention, not a defect of this report. |
| "Required check concluded `success` on head `073fe7a`" | **True of that head, and stale for the merged head** — `073fe7a` was head at PR-open; the run then pushed `5abb757`. Independently verified that the *merged* head is also green: `verify / conclusion` = `success`, `verify / gate` = `success`, `dependency-review` = `success`, `verify / verify` = `skipped` (docs-only path). No merge-gate risk; noted for precision only. |
| "`review / review` … `success`" | **UNVERIFIABLE now.** The PR-head check-run set (on `5abb757`) contains no `review / review` entry; PR-Agent subscribes only to `opened`/`reopened`/`ready_for_review` (`pr-agent.yml:12-14`), so it can only have run on `073fe7a`, whose check set this tool cannot address by SHA. Consistent with the report; not independently confirmed. |
| "One verification sub-agent reported `subagent_tokens: 70038`, `tool_uses: 14`" | **UNVERIFIABLE** — a session-local figure with no durable record; correctly labelled in the report as one dispatch, not a run total. |
| Cold-read gate passed (Findings row 1) | **Corroborated.** I performed my own cold read of the revised § 6 and reached both required conclusions (currency = billing weight/turns-resident; isolation recommended, not questioned). |

**Not claimed, and missing:** the report never records the § 4 check the plan's Expected surface asks
for (`plan.md:141`: "§ 6 (and § 4's figures)"), and never records the coordination check the plan's
Notes require (`plan.md:181-183`, the WS-04 emission plan). Both were in fact satisfied — § 4
("Skill-driven guidance") carried no numeric figure before or after the change, and no second writer
was added — but a reader cannot tell from the report whether they were checked or overlooked. → G7.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| D1, D3, D4 blocked on corpus availability; pick up in a run with a reachable population | **Open.** Nothing is staged. | `grep -rln "090-envelope\|envelope-length" doc/` returns only this plan's own `plan.md` and `report-01.md`. No sibling plan in `doc/plans/**` references this plan's residue; the epic `README.md` carries no per-plan status. → G6 |
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

# Gaps — 020-corpus-residency-admission-control

The run's outcome is sound: the D0 gate correctly halted on outcome (b), and that verdict still holds
at `57c63a8` (zero tracked `metrics.toon`; no `.plan/plans/`, no `.plan/local/archived-plans/`, no
`metrics*.toon` anywhere under `.plan/`; sibling plan 080 recorded the same halt two days later). No
production code shipped, nothing out of scope was built, and no collateral landed — PR #1149 changed
exactly two files, both inside this plan's directory. What remains are twelve defects in the *record*.

**The four that change a future run's behaviour:**

- **G1/G2** — the report equates the metrics field it anchors D0 on with D1's measurement. That field
  cannot supply D1 as persisted, so the re-run premise ("un-block 020 when `.plan/` is populated, then
  measure") is insufficient as written.
- **G11** — the plan's D2 premise ("no section-granular read exists") is an **unverified absence**.
  Two section-granular read verbs already ship over plan documents, one with the very
  missing/unreadable/empty discrimination D2's three negative controls demand. `plan.md:132-135`
  names this exact failure mode: *"an unverified absence produces duplicate work against something
  that already exists."*
- **G12** — a resident language server **over the skill corpus** shipped after this run. The residue's
  "do not fork a second client" pointer names only 010's `lsp-client` and so points at the wrong
  surface first.

**G10** corrects a false mechanism claim about the review registry; **G3–G9** are record hygiene.

Each defect below is tagged **wrong-when-written** or **stale**, resolved against `60c34cb` — the
commit that landed this report — so a later run can tell a mistake from a decayed citation.

## G1 — Correct the report's claim that `exploration_doc_residency_bytes` is D1's measurement

- **Kind:** report-defect (wrong-when-written)
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/report-01.md:46-52`
  (§ "D0 evidence"); the field's actual contract at
  `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:163,186` and
  `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py:754-772`
- **Evidence:** The report states the field is *"exactly D1's 'how much of each read document a step
  actually consumes.'"* Its own schema says otherwise — it is **one integer per phase**:
  `data-format.md:163` — *"the part whose call targeted a workflow/standard document: skill and
  standard markdown bodies, `doc/**`, `*.adoc`, `CLAUDE.md`"*, with no path retained; and
  `data-format.md:186` — *"There is no matching `_tool_calls` sub-split."* The field also names
  **residency**, while `plan.md:125` requires *"D1 must measure **consumption**, not just residency."*
- **Why it matters:** The report is the only durable channel back to the orchestrator
  (`report-01.md:238-242` asks that 020 be kept queued and re-handed "when the corpus is reachable").
  A re-run reading this line will believe a populated `metrics.toon` satisfies D1, discover mid-run
  that the field answers none of D1's four questions *as asked* — it is a single per-phase byte total
  with no path, no call count, and no envelope dimension — and either halt again or, worse, present
  that pooled total as per-document consumption, which is the exact defect class `plan.md:124` warns
  about twice.
- **Action:** Replace the "exactly D1's …" clause with the accurate relation: the field is the closest
  existing **proxy for D1's residency half only**; it carries no per-document breakdown, no call
  count, and measures bytes that entered context rather than bytes a step needed. Add one sentence
  pointing at G2.
- **Done when:** `report-01.md` no longer asserts equivalence between
  `exploration_doc_residency_bytes` and D1's per-document consumption measure, and names the three
  specific shortfalls (no path granularity, no `_tool_calls` sub-split, residency ≠ consumption).
- **Effort:** S (<1h)
- **Risk if fixed:** None — a record edit; the D0 halt verdict it supports is unchanged and stays
  correct.

## G2 — Re-scope D1, or specify the instrument it needs, before 020 is re-handed

- **Kind:** omission
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/plan.md:66-75`
  (D1) and `plan.md:81-85` (D3, whose magnitude D1 supplies)
- **Evidence:** D1 asks for four things — *"which documents are read, how often, how many times
  **within one envelope**, and how much of each read document a step actually consumes."* The only
  instrument in the tree is the per-phase integer `exploration_doc_residency_bytes`
  (`runtime_base.py:754-758`), and `data-format.md:186` states flatly *"There is no matching
  `_tool_calls` sub-split."* Grep for per-document instrumentation across
  `marketplace/bundles/plan-marshall/skills/{manage-metrics,platform-runtime}/` (`per-document`,
  `per_document`, `doc_paths`, `documents_read`) returns **nothing**.
  ⚠ **The raw material does exist, one layer down.** The walk that produces the aggregate extracts a
  per-call target path and then discards it into a bucket —
  `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py:1837`
  (`_classify_exploration_target(_extract_target_path(item.get("input")))`), classifier at `:253-275`,
  path extraction at `:240-250`. So D1's per-document half is a **retained field away**, not a missing
  capability: the transcript carries it, the walk sees it, nothing persists it.
- **Why it matters:** 020's residue says the plan "becomes runnable when a git-reachable population of
  instrumented corpus-residency records exists." That precondition is **insufficient**, not merely
  unmet: a fully populated `.plan/plans/**/metrics.toon` corpus answers only D1's residency half, so
  re-handing 020 on that trigger alone sends a run at a deliverable it cannot close from the persisted
  record — it would have to re-walk transcripts itself, which is unbudgeted work the plan never names.
  D3 inherits the same defect — its "drop it on evidence" branch needs an intra-envelope re-read count
  that nothing persists, and `data-format.md:186` rules out deriving one from this family
  (*"There is no matching `_tool_calls` sub-split"*).
- **Action:** Decide one of two, and write it into `plan.md`: (a) extend the `enrich` tool-call walk to
  persist the target path it already extracts — a per-document record (target path, call count within
  the phase window, result bytes) alongside the existing aggregate, making D1 answerable — a change to
  `claude_runtime.py`, `runtime_base.py` and `data-format.md` that is itself plan-sized; or (b) narrow
  D1 to the residency half the existing field *can* answer and move the per-document/consumption
  question to its own deliverable. Update D3's dependency to match, and edit the residue precondition
  in `report-01.md:238-242` in the same pass.
- **Done when:** `plan.md`'s D1 *Done when* names, for each of its four questions, either an existing
  field that answers it or the predecessor deliverable that creates one; and the re-run precondition
  states that instrument rather than only "a populated `.plan/`".
- **Effort:** M (a few hours to re-scope the plan; L if option (a) is taken and the instrument is built)
- **Risk if fixed:** Option (a) touches the `enrich` walk's per-phase bucket contract, which is
  governed by the absent-is-not-zero and partition-invariant rules at `data-format.md:175-186` — a new
  key must not join `_EXPLORATION_COUNTER_FIELDS` nor break the exact-sum partition.

## G3 — Replace the decaying `data-format.md:152` line citation with the field name

- **Kind:** doc-defect (stale — the citation was **exact when written**)
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/report-01.md:111`
- **Evidence:** The report cites the per-phase definition at `data-format.md:152`. At `60c34cb` — the
  commit that landed this report — `exploration_doc_residency_bytes` was at **line 152**
  (`git grep -n exploration_doc_residency_bytes 60c34cb -- .../data-format.md`), so the run cited it
  correctly. The file has grown since; it is at **163** at `57c63a8`. The companion citation
  `data-format.md:13` is still exact. ⚠ The earlier framing of this gap ("wrong line", inferred from
  `3cb595f` where it was 154) was itself an artefact of a shallow clone and is withdrawn.
- **Why it matters:** A reader following the citation today lands on an unrelated row of the
  token-field table and has to re-search, in a report whose whole value is that its evidence is
  checkable. Re-pinning to `163` only restarts the decay — the same fix will be owed at the next edit
  of `data-format.md`.
- **Action:** Drop the line number and cite the **field name**, which is stable: "the per-phase
  definition of `exploration_doc_residency_bytes` in `data-format.md`". Add a one-clause note that
  `:152` was correct at the time of the run, so the change reads as re-anchoring rather than as
  correcting an error.
- **Done when:** No `data-format.md:{n}` citation remains in `report-01.md` except `:13` (still exact),
  and the per-phase definition is cited by field name.
- **Effort:** S (<1h)
- **Risk if fixed:** None.

## G4 — Correct "three synthetic test fixtures" to four

- **Kind:** report-defect (stale — exhaustive when written)
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/report-01.md:68-70`
- **Evidence:** The report names
  `.../fixtures/dispatch-loop-replay/{legacy,plan,unmeasured}/work/metrics-dispatch-boundaries-5-execute.toon`.
  `git ls-tree --name-only 60c34cb .../fixtures/dispatch-loop-replay/` returns exactly those three, so
  the enumeration was complete at the time of the run.
  `ls test/plan-marshall/plan-retrospective/fixtures/dispatch-loop-replay/` now returns four entries —
  `legacy plan undatable unmeasured`. `undatable` was added by `d1c3153` (#1278), after this run.
- **Why it matters:** The claim is framed as an exhaustive enumeration ("the **only** git-tracked
  instrumented `.toon` records"), so a re-run using it as a checklist would miss one — and a fifth
  could appear the same way. The conclusion is unaffected: `undatable` carries no residency field
  either (`head -4` shows `rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens}`).
- **Action:** Either add `undatable` to the enumeration, or replace the fixed list with the *derivation*
  (`git ls-files "test/**/*.toon"` under `fixtures/dispatch-loop-replay/`) so the claim stays true as
  fixtures are added.
- **Done when:** The report's fixture claim either names all four or states the command that derives
  the current set.
- **Effort:** S (<1h)
- **Risk if fixed:** None.

## G5 — Correct the false column description of the `legacy` and `plan` fixtures

- **Kind:** report-defect (wrong-when-written)
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/report-01.md:72-73`
- **Evidence:** The report says the three named fixtures *"carry per-dispatch context-load columns
  (`input/output/cache` tokens)"*. Two of the three do not, at `57c63a8` **and at `60c34cb`, the
  report's own commit** (`git show 60c34cb:…/{legacy,plan}/work/metrics-dispatch-boundaries-5-execute.toon`):
  both carry `rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}` — no
  input/output/cache columns. Only `unmeasured` (and the later `undatable`) carry them. So this was
  wrong when written, not merely stale — established directly against the run's own tree, no longer
  inferred from a shallow-clone proxy.
- **Why it matters:** A wrong description of the evidence weakens a report whose only asset is the
  checkability of its evidence, and it is the second half of a two-part disqualification ("(a) hand
  crafted, (b) wrong columns") — the (b) half does not hold as stated for two of the three files, even
  though the real disqualifier (no residency field) does hold for all four.
- **Action:** Replace the clause with the accurate one: none of the fixtures carries any
  `exploration_*_bytes` field; two carry only dispatch-boundary totals and two additionally carry
  input/output/cache columns.
- **Done when:** The clause matches the actual `rows[]{…}` headers of the fixtures it describes.
- **Effort:** S (<1h)
- **Risk if fixed:** None.

## G6 — Re-scope or date-stamp the "no committed report mentions residency" claim

- **Kind:** report-defect (stale — accurate when written)
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/report-01.md:115-116`
- **Evidence:** The sub-agent's claim — *"Committed run reports (`doc/plans/**/report-*.md`) grepped
  for residency/consumption vocabulary — **no matches**; the one sibling report (010-lsp) …"* — held
  at `60c34cb`, where only **8** report files were committed and `git grep -il residency` over them hit
  only 020's own. It no longer holds: `git ls-files "doc/plans/**/report-*.md" | wc -l` = **112** at
  `57c63a8`, and the same grep returns **7** files (020's own report plus
  `code-intelligence-substrate/{030,090,200,240,250}` and `multiplattform/010`). All post-date this run,
  and each was checked — every hit is vocabulary (`_fold_turn_residency`, "bounded residency",
  config-domain residency), never a corpus-residency measurement.
- **Why it matters:** Read today the sentence is simply false, and a re-run re-checking the D0 gate
  might treat the seven hits as a candidate population. They are not — none carries a residency
  *measurement*, only the vocabulary — but the report as written offers no way to tell.
- **Action:** Restate as a dated observation ("at the time of this run, 010-lsp was the only sibling
  report and carried no residency data") and add the discriminator that survives: a committed prose
  report is not an instrumented record regardless of its vocabulary.
- **Done when:** The claim is either scoped to the run's date or restated so it stays true as the epic's
  report corpus grows.
- **Effort:** S (<1h)
- **Risk if fixed:** None.

## G7 — Fix the mis-attributed coordination quote

- **Kind:** report-defect (wrong-when-written)
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/report-01.md:244-245`
- **Evidence:** The report attributes to plan 010's *"closing note"* the sentence *"a sibling WS-06
  plan [that] wants this same client pointed at the document corpus."* That text is in 010's
  **`plan.md:178-179`**, not its report: `grep -rin "document corpus\|WS-06"
  doc/plans/code-intelligence-substrate/010-lsp-in-execute-lookup-and-write/report-01.md` returns
  nothing, while the same grep over the directory hits `plan.md:178`. The surrounding facts are
  correct — PR #1140 at `010-…/report-01.md:3`, and
  `marketplace/bundles/plan-marshall/skills/lsp-client/` exists.
- **Why it matters:** This is the one residue item a re-run is told to act on. Sending it to the wrong
  document to read the coordination constraint costs a search at exactly the moment the run needs the
  constraint most.
- **Action:** Change the attribution to `010-…/plan.md:178-179`. While there, note that the "right
  home" question the note leaves open now has more candidates — plans `135-remove-lsp-query-facade` and
  `240-skill-lsp-server` exist in the epic — so the re-verification it asks for is broader than an
  `lsp-client`-versus-`manage-architecture` choice.
- **Done when:** The quote's citation resolves to the file and line that contain it.
- **Effort:** S (<1h)
- **Risk if fixed:** None.

## G8 — Update the sibling-plan path, which is now a directory

- **Kind:** doc-defect (stale — correct when written)
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/report-01.md:80`
- **Evidence:** The report cites plan
  `080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case.md` as a flat file, which it
  was — `git ls-tree --name-only 60c34cb doc/plans/code-intelligence-substrate/` returns it with the
  `.md` suffix. At `57c63a8` it is a directory: `ls doc/plans/code-intelligence-substrate/` shows
  `080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case/` containing `plan.md` and
  `report-01.md` (the plan was moved by its own run, which halted the same way on 2026-08-12).
- **Why it matters:** The path does not resolve; a reader checking the corroborating sibling gate has
  to guess. Minor, but it is the evidence item that establishes the halt is an epic-wide designed
  condition rather than a local accident.
- **Action:** Cite `…/080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case/plan.md:59-60`
  — the two lines the report quotes verbatim. Add that 080 has since run (PR #1178, 2026-08-12) and
  reached the same outcome (b), per `080-…/report-01.md:3`, which strengthens item 6 from "the sibling
  carries the same gate" to "the sibling hit the same wall".
- **Done when:** The path in `report-01.md` resolves to an existing file, and the quoted D0-gate text
  is found at the line range cited.
- **Effort:** S (<1h)
- **Risk if fixed:** None.

## G9 — Record the re-derived scale figures the plan's ⛔ demanded

- **Kind:** omission
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/plan.md:43-45`
  (the instruction); no corresponding record anywhere in `report-01.md`
- **Evidence:** `plan.md:43-45` carries an unconditional ⛔: *"Both of those figures are leads:
  re-derive them in the clone (`wc -c` over the skill directory, and a re-count of registered
  components) — the tree the run sees is not guaranteed to be the tree these numbers were taken
  from."* The report records no such derivation. Derived during this audit at `61a43e5`:
  `persona-plan-marshall-agent/SKILL.md` = **14,835 bytes**; its `standards/` = **5 files, 102,086
  bytes**; the whole skill directory = **116,921 bytes**; `find marketplace/bundles -name SKILL.md |
  wc -l` = **156** across 11 bundles. All three of the plan's leads hold ("on the order of fifteen
  kilobytes", "roughly a hundred kilobytes", "well over a hundred").
- **Why it matters:** The figures are the plan's entire scale justification ("what makes it worth a
  plan rather than a cleanup"). An unexecuted ⛔ leaves that justification unverified in the record,
  and the next run has to re-derive from zero — cheap, but it is exactly the re-derivation the plan
  asked to be captured once.
- **Action:** Add a short "Scale figures re-derived" subsection to `report-01.md` (or to the re-run's
  `report-02.md`) carrying the four measurements above with the commands that produced them. Note that
  the ⛔ was not gated on D0 and so applied even to a halting run.
- **Done when:** `report-01.md` (or a successor report) states the re-derived skill-body size,
  standards total, and component count, each with its derivation command.
- **Effort:** S (<1h)
- **Risk if fixed:** None.

## G10 — Correct the false registry claim about why `cuioss-review-bot` reviewed a `skip-bot-review` PR

- **Kind:** report-defect (wrong-when-written)
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/report-01.md:168`
  (§ "Reviewer participation", the `cuioss-review-bot` row); the registry it misquotes at
  `marketplace/bundles/plan-marshall/skills/automatic-review/standards/pr-agent.md:65,168-174,266,345-352`
  and `.github/workflows/pr-agent.yml:3-6`
- **Evidence:** The report asserts *"Its Guide comment is **unconditional** — the pr-agent registry
  records that `skip-bot-review` gates only its inline `/improve` comments, not the Guide — so it
  reviewed despite the label."* The registry records the opposite on both halves:
  - `pr-agent.md:65` — `honors_skip_label: true` (annotated `UNVERIFIED`: untested, not exempted).
  - `pr-agent.md:168-174` — the label skip *"is enforced by the reusable workflow's job-level `if:`
    guard"*, i.e. over the whole `review` job, `/review` included. `.github/workflows/pr-agent.yml:3-6`
    says the same: *"The org skip rules (dependabot[bot], cuioss-release-bot[bot], the skip-bot-review
    label, fork PRs) are enforced by the reusable workflow's job-level `if:` guard."*
  - What *is* scoped to `/improve` is gated by a **different, enabling** label — `pr-agent-improve`
    (`pr-agent.md:266`, `:345-352`) — not by `skip-bot-review`.

  The underlying observation is true and was re-confirmed live (`pull_request_read get_comments` on
  #1149): `cuioss-review-bot[bot]` posted the Guide at `2026-08-10T21:22:32Z`, on a PR created
  `21:21:43Z` that carries the `skip-bot-review` label. Only the explanation is invented.
- **Why it matters:** The claim is stated as *what the registry records*, in the section a later run
  reads to decide whether a bot's silence is by design or a shortfall. Carried forward, it licenses
  treating pr-agent as exempt from `skip-bot-review` — so a future run would score a genuinely
  suppressed pr-agent as a participation failure, or a genuine outage as "by design". It also
  suppresses the real signal here: the registry predicts suppression and the bot reviewed anyway, which
  is an unexplained result worth recording (most plausibly a race between PR creation and label
  application, since the workflow fires on `pull_request: opened`).
- **Action:** Replace the mechanism clause with the observation plus its open question: pr-agent's
  registry declares `honors_skip_label: true` and the skip is enforced by the reusable workflow's
  job-level guard over the whole job, yet the Guide was posted 49 s after PR creation — record it as
  an observed exception whose cause was not established, and do not attribute it to a registry rule.
  Do **not** edit `pr-agent.md`: the registry is correct and this is a misreading of it.
- **Done when:** `report-01.md:168` no longer attributes to the pr-agent registry a rule that
  `skip-bot-review` spares the Guide, and states the observed timing instead.
- **Effort:** S (<1h)
- **Risk if fixed:** None — a record edit. The 1-of-3 coverage verdict and the disclosure-not-block
  disposition are unchanged.

## G11 — Record the existing section-granular read verbs before D2 is built

- **Kind:** omission (unverified absence)
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/plan.md:76-80`
  (D2) and `plan.md:111-118` (§ Expected surface, which lists no precedent); the precedents at
  `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py:606-636`
  (flag at `:1015`) and
  `marketplace/bundles/plan-marshall/skills/manage-plan-documents/scripts/manage-plan-documents.py:101`
  with `scripts/_cmd_request.py:172-196`
- **Evidence:** D2 asks for "a named section of a `SKILL.md` or a `standards/*.md` without loading the
  file", carrying "the same coverage contract the existing content reader ships" and three separately
  representable states. Two verbs already implement that shape over **plan documents**:
  - `manage-solution-outline read --plan-id X --section S` slugifies the requested heading
    (`_plan_parsing.py:105`), splits on top-level `##` (`:162`), and returns that section's body alone.
    Its states are already distinct: missing → `{'status': 'error', 'error': 'section_not_found',
    'requested_section': …}`; unreadable file → the read helper's error, returned before the section
    branch; empty → `status: success` with empty `content`.
  - `manage-plan-documents read --section S` is the same shape over the request document.

  Neither is corpus-facing, so D2's literal target is genuinely unbuilt — but the audit's original
  finding, "there is no section-addressed read on any surface", is false, and the plan's Expected
  surface names no precedent at all. `plan.md:132-135` makes this the plan's own stated risk: *"An
  asserted **absence** … is the higher-risk half — confirm it against the loading contract before
  building, because an unverified absence produces duplicate work against something that already
  exists."* `plan.md:106-107` compounds it: a second content-search verb is out of scope, and the run
  must "extend the existing surface or justify a new home explicitly" — which is unanswerable while the
  existing surfaces are unlisted.
- **Why it matters:** A re-run reading only the plan and the report would design D2's three-state
  coverage contract from scratch and would very likely land a third parallel `--section`
  implementation — the precise duplication `plan.md:106-107` forbids. The `section_not_found` /
  read-error / empty-body triple is already a working answer to D2's three negative controls.
- **Action:** Add both verbs to `plan.md`'s § Expected surface as **OBSERVED** precedents with the
  file:line citations above, and amend D2 to require an explicit decision, recorded in the run report:
  extend one of them to the corpus, or justify a separate home against them by name.
- **Done when:** `plan.md` § Expected surface names `manage-solution-outline read --section` and
  `manage-plan-documents read --section` with their state-discrimination behaviour, and D2's text
  requires the extend-or-justify decision to be recorded against them.
- **Effort:** S (<1h to record; the extend-or-justify decision itself belongs to the re-run's outline)
- **Risk if fixed:** None to code — a plan edit. It narrows D2 rather than widening it.

## G12 — Repoint the D2 coordination note at the corpus language server that has since shipped

- **Kind:** report-defect (stale)
- **Severity:** low
- **Topic:** lsp/resolvers
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/report-01.md:243-249`
  (§ Residue, the coordination note); the surface it omits at
  `marketplace/bundles/pm-plugin-development/skills/tools-corpus-language-server/`
- **Evidence:** The note tells the eventual D2 to coordinate with 010's `lsp-client` and to re-verify
  whether that or `manage-architecture` is the better home. Since this run, plan `240-skill-lsp-server`
  (PR #1256, commit `5edca5a`, 2026-08-16) shipped
  `pm-plugin-development:tools-corpus-language-server` — a resident language server whose stated scope
  is *"the marketplace skill corpus"* (`SKILL.md:3`), answering `textDocument/{definition,references,hover}`
  over skill and script notations, plus a one-shot `query` verb (`corpus_lsp.py:510`). `5edca5a` is an
  ancestor of `61a43e5`, so it was already in the tree when this plan's audit was first written.
  It does **not** satisfy D2: the index is component-granular, with no heading or anchor concept —
  `definition` returns the component's file at line 0 by explicit design (`_corpus_index.py:159-169`,
  *"the index records no intra-file position for a component's own declaration"*) and `hover` returns
  description plus frontmatter (`:171-185`).
- **Why it matters:** This is the one residue item a re-run is told to act on, and `plan.md:157-160`
  makes it a prohibition, not advice: *"Coordinate; do not fork a second client."* The note as written
  sends the run to a **code-facing** client (`lsp-client`) while a **corpus-facing** server already
  exists with the index, the resident-process cost model, and the opt-in switch already solved. The
  note also predates plan `135-remove-lsp-query-facade`, so the "right home" question it leaves open has
  more candidates than the two it names.
- **Action:** Rewrite the coordination note to name `pm-plugin-development:tools-corpus-language-server`
  first, state what it does and does not answer (component-granular, no section addressing), and frame
  the open question as three-way — extend that server with a section-granular request, extend
  `manage-architecture`'s content surface, or extend one of the `--section` verbs from G11 — rather than
  the two-way `lsp-client`-versus-`manage-architecture` choice it currently poses.
- **Done when:** `report-01.md`'s residue names `tools-corpus-language-server` with its granularity
  limitation, and the "right home" question it poses lists the candidates that exist at the time of
  the edit.
- **Effort:** S (<1h)
- **Risk if fixed:** None — a record edit.

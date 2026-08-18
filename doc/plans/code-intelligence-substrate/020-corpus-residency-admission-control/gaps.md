# Gaps — 020-corpus-residency-admission-control

The run's outcome is sound: the D0 gate correctly halted on outcome (b), and that verdict still holds
at `61a43e5` (zero tracked `metrics.toon`; `.plan/` holds only `marshal.json` and
`project-architecture/`; sibling plan 080 recorded the same halt two days later). No production code
shipped, nothing out of scope was built, and no collateral landed — PR #1149 changed exactly two files,
both inside this plan's directory. What remains are nine defects in the *record*, one of which is
substantive: the report equates the metrics field it anchors D0 on with D1's measurement, and that
field structurally cannot supply D1 — so the plan's re-run premise ("un-block 020 when `.plan/` is
populated, then measure") is wrong and will fail a second time unless the instrument is extended or D1
is re-scoped. G1 and G2 are the ones that change a future plan's behaviour; G3–G9 are record hygiene.

## G1 — Correct the report's claim that `exploration_doc_residency_bytes` is D1's measurement

- **Kind:** report-defect
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/report-01.md:47-53`
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
  that it answers none of D1's four questions, and either halt again or — worse — pool a per-phase
  byte total and present it as per-document consumption, which is the exact defect class
  `plan.md:124` warns about twice.
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
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/plan.md:66-73`
  (D1) and `plan.md:81-85` (D3, whose magnitude D1 supplies)
- **Evidence:** D1 asks for four things — *"which documents are read, how often, how many times
  **within one envelope**, and how much of each read document a step actually consumes."* The only
  instrument in the tree is the per-phase integer `exploration_doc_residency_bytes`
  (`runtime_base.py:754-758`), and `data-format.md:186` states flatly *"There is no matching
  `_tool_calls` sub-split."* Grep for per-document instrumentation across
  `marketplace/bundles/plan-marshall/skills/{manage-metrics,platform-runtime}/` (`per-document`,
  `per_document`, `doc_paths`, `documents_read`) returns **nothing**.
- **Why it matters:** 020's residue says the plan "becomes runnable when a git-reachable population of
  instrumented corpus-residency records exists." That is false as stated: even a fully populated
  `.plan/plans/**/metrics.toon` corpus cannot answer D1, so re-handing 020 unchanged sends a run at an
  unsatisfiable deliverable. D3 inherits the same defect — its "drop it on evidence" branch needs an
  intra-envelope re-read count that nothing produces.
- **Action:** Decide one of two, and write it into `plan.md`: (a) extend the `enrich` tool-call walk to
  emit a per-document record (target path, call count within the phase window, result bytes) alongside
  the existing aggregate, making D1 answerable — a change to `runtime_base.py` and `data-format.md`
  that is itself plan-sized; or (b) narrow D1 to the residency half the existing field *can* answer and
  move the per-document/consumption question to its own deliverable. Update D3's dependency to match.
- **Done when:** `plan.md`'s D1 *Done when* is satisfiable by an instrument that exists or that a named
  predecessor deliverable creates, and the re-run precondition in the residue names that instrument
  rather than only "a populated `.plan/`".
- **Effort:** M (a few hours to re-scope the plan; L if option (a) is taken and the instrument is built)
- **Risk if fixed:** Option (a) touches the `enrich` walk's per-phase bucket contract, which is
  governed by the absent-is-not-zero and partition-invariant rules at `data-format.md:175-186` — a new
  key must not join `_EXPLORATION_COUNTER_FIELDS` nor break the exact-sum partition.

## G3 — Fix the stale `data-format.md:152` line citation

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/report-01.md:112`
- **Evidence:** The report cites the per-phase definition at `data-format.md:152`. At `61a43e5` it is
  at **line 163** (`grep -n exploration_doc_residency_bytes
  marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md`); at the earliest
  commit reachable in this shallow clone (`3cb595f`) it was at 154. The companion citation
  `data-format.md:13` is still exact.
- **Why it matters:** A reader following the citation lands on an unrelated row of the token-field
  table and has to re-search, in a report whose whole value is that its evidence is checkable.
- **Action:** Change `data-format.md:152` to `data-format.md:163`, or drop the line number and cite
  the field name, which is stable.
- **Done when:** Every `data-format.md:{n}` citation in `report-01.md` resolves to the line it names at
  the current `main`.
- **Effort:** S (<1h)
- **Risk if fixed:** None.

## G4 — Correct "three synthetic test fixtures" to four

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/report-01.md:69-71`
- **Evidence:** The report names
  `.../fixtures/dispatch-loop-replay/{legacy,plan,unmeasured}/work/metrics-dispatch-boundaries-5-execute.toon`.
  `ls test/plan-marshall/plan-retrospective/fixtures/dispatch-loop-replay/` returns four entries —
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

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/report-01.md:72-73`
- **Evidence:** The report says the three named fixtures *"carry per-dispatch context-load columns
  (`input/output/cache` tokens)"*. Two of the three do not, at `61a43e5` **and** at the earliest
  reachable commit `3cb595f`:
  `test/plan-marshall/plan-retrospective/fixtures/dispatch-loop-replay/plan/work/metrics-dispatch-boundaries-5-execute.toon`
  and its `legacy/` sibling both carry
  `rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}` — no input/output/cache
  columns. Only `unmeasured` (and the later `undatable`) carry them. This was wrong when written, not
  merely stale.
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

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/report-01.md:115-116`
- **Evidence:** The sub-agent's claim — *"Committed run reports (`doc/plans/**/report-*.md`) grepped
  for residency/consumption vocabulary — **no matches**; the one sibling report (010-lsp) …"* — no
  longer holds. `git ls-files "doc/plans/**/report-*.md" | wc -l` = **112** at `61a43e5`, and
  `git grep -il residency` over that set returns seven files (020's own report plus
  `code-intelligence-substrate/{030,090,200,240,250}` and `multiplattform/010`). All post-date this run.
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

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/report-01.md:245-246`
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

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/report-01.md:80-81`
- **Evidence:** The report cites plan
  `080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case.md` as a flat file. At
  `61a43e5` it is a directory: `ls doc/plans/code-intelligence-substrate/` shows
  `080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case/` containing `plan.md` and
  `report-01.md` (the plan was moved by its own run, which halted the same way on 2026-08-12).
- **Why it matters:** The path does not resolve; a reader checking the corroborating sibling gate has
  to guess. Minor, but it is the evidence item that establishes the halt is an epic-wide designed
  condition rather than a local accident.
- **Action:** Cite `…/080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case/plan.md:59`
  (where the D0 gate is stated). Optionally add that 080 has since run and reached the same outcome
  (b), which strengthens item 6.
- **Done when:** The path in `report-01.md` resolves to an existing file.
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

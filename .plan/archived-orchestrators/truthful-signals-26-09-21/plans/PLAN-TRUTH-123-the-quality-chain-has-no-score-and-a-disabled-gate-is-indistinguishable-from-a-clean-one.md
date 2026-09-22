# PLAN-TRUTH-123: The quality chain has no score, and a disabled gate is indistinguishable from a clean one

epic: truthful-signals
workstream: WS-01
priority: HIGH — operator-designated 2026-09-02; takes the next freed slot ahead of queue order

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-TRUTH-123-the-quality-chain-has-no-score-and-a-disabled-gate-is-indistinguishable-from-a-clean-one.md`
> and is queued in the epic `status.json` `plans[]` field. The orchestrator EMITS the command below;
> it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief, so
> every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Operator request, 2026-09-02, designated HIGH priority. Every structural claim below was read
first-party at HEAD `30cd8aaf8` by the orchestrator before staging; the archived plan
`2026-08-31-git-artifact-scanning-and-destructive-recovery` is the worked example throughout and every
figure quoted from it was read from its own artifacts.

## Objective

Quality in this project is produced by a **chain of gates** — the build/maven runs, then
`pre-submission-self-review`, `finalize-step-simplify`, `finalize-step-security-audit`,
`automatic-review`, `sonar-roundtrip`, and `project:finalize-step-review-retrospective` — and then, after
the merge, the **orchestrator's own ground-truth corroboration of the landing** (D6). Every in-plan gate
files into the same store; the orchestrator's pass files into prose. **Nothing scores what that chain
caught.**

⭐ The project has a *quantitative* self-portrait — `doc/analyzis-cloud-plan/README.adoc`, which counts
artifacts per plan (14 vs 2-4) and reports finding **resolution rates** (local 100% in every measured
corpus). ⛔ **A resolution rate is volume-blind and therefore says almost nothing about quality: a plan
that caught 2 findings and closed both scores exactly what a plan that caught 40 and closed 40 scores.**
The missing half is the *qualitative* one the operator names — **how many issues of what kind the chain
actually caught** — and this plan builds it.

⛔⛔ **And the harder half is the one that makes a naive score actively false.** Which gates run is
**configuration-dependent**, so a mechanism that produced no findings is one of THREE different facts,
and today nothing tells them apart:

| State | Meaning | What a naive score does |
|-------|---------|-------------------------|
| **not admitted** | the step is absent from the manifest's `candidate_steps` — lane/config excluded it | scores it 0, indistinguishable from clean |
| **admitted, never fired** | present in `candidate_steps`, no `execution_log` row | scores it 0, indistinguishable from clean |
| **fired, found nothing** | ran and reported clean — a genuine checked negative | scores it 0 |

⇒ **A plan that disabled half its gates would out-score a plan that ran them all and found defects.**
That is this epic's own archetype (*a clear verdict over an empty population reported as a checked
negative*) sitting in the instrument built to measure quality, and it is the single property the design
must get right.

**First-party proof the three states are real and live**, read from the worked example's
`execution.toon`: `candidate_steps` carries 26 entries including `finalize-step-security-audit`,
`sonar-roundtrip` and `adr-propose` — and the 29-row `execution_log` **contains no row for any of the
three**. Meanwhile `lessons-capture` carries `lane: off`. So one run exhibits all three states at once,
and its findings store shows zero security and zero sonar findings — currently indistinguishable from
two clean gates.

## Deliverables

Six deliverables (D0-D5), under this epic's raised split guard of 12. D0 is a gate. **D1 is the single
point of entry both consumers call** — the operator's explicit structural requirement.

⭐ **This spec was CUT DOWN from nine on 2026-09-02, not grown.** The three producer-side deliverables
moved to `PLAN-TRUTH-124`; what remains is the instrument plus the historical analysis, and it is a
coherent shippable unit that consumes `-124` rather than duplicating it.

---

**D0 — GATE: derive the mechanism population, and settle the disposition→point mapping against the real
corpus, before any scoring code is written.** Three questions, each answered with a published count over
a named population, none of them decidable from this spec:

- *(a) The mechanism roster.* Enumerate every step that can file into the findings store, derived from
  the manifest's own step registry rather than from the operator's list or from this spec. ⛔ **The seven
  names in the Objective are the REQUEST, not the population** — treat them as a floor and publish what
  the derivation actually found. A mechanism nobody enumerated cannot be reported absent.
- *(b) The disposition mapping.* The operator's rule is *"each fixed / refuted issue is a quality point"*.
  `fixed` and `rejected` (the `ext-point-verify` refutation disposition) map cleanly. The **other four**
  members of `VALID_RESOLUTIONS` do not, and the choice must be recorded rather than defaulted:
  `accepted`, `taken_into_account`, `suppressed`, `pending`. ⭐ Two shipped frozensets already partition
  five of the six and MUST be reused rather than re-derived —
  `phase-6-finalize/scripts/review_commitments.py:96` `COMMITTED_RESOLUTIONS = {fixed, accepted,
  taken_into_account}` and `:102` `RELEASED_RESOLUTIONS = {rejected, suppressed}`. A third, competing
  partition in a third file is the duplicate-source-of-truth defect this epic repeatedly records.
- *(c) The population the first run will actually report over.* Count the archived plans, and **count how
  many of them carry an `execution.toon` with a `candidate_steps` block at all** — the presence resolver
  in D1 is unavailable for any plan that predates that block, and a corpus figure that silently spans
  both is two populations added together. Publish both numbers.

- *(d) The BACKFILL decision — this plan's, and it is the historical half of the operator's cut.*
  `-124` ships the `landings/PLAN-NN.json` schema forward-only; 200 landings already exist without one.
  Decide and record: emit only for new landings (the corpus stays two populations, reported as two), or
  backfill what is derivable — and much of it is, since `execution.toon` and the findings store are still
  on disk for archived plans, while `-124` D4's corroboration half is NOT. ⛔ **A partial backfill that
  does not mark itself partial is this plan's own thesis violated at corpus scale.**
- *(e) Whether component assessments score at all* — the 276-record second schema
  (`assessments.jsonl`, carrying `certainty`/`confidence`/`agent`/`evidence` rather than
  `type`/`title`/`resolution`). They are not findings; recorded either way.

⛔ **Do not proceed to D2 until (b) is recorded as a decision with its rationale**, nor to D8 until (d)
inside the scorer buries the one judgement call the design has.

---

**D1 — the coordinator: ONE script, one entry point, two consumers.** The operator's requirement is
explicit — *"mostly script driven with a coordinator call as single point of entry for both targets"*.

⛔⛔ **Residency is forced, not chosen: the coordinator MUST live in the marketplace tree, never in
`.claude/skills/`.** `.claude/skills/audit-archived-plan-retrospectives` is project-local by design (its
own SKILL.md says so — it reads `.plan/local/archived-plans/`, a directory only this meta-project has),
while `plan-retrospective` is a marketplace skill shipped to consumer projects. A marketplace skill can
never depend on a project-local one. ⇒ The computation core lives in the marketplace and the
project-local audit **calls into it**.

⭐ **The precedent for that call already exists and should be followed rather than reinvented:**
`audit.py:2120` `_load_routing_logic` adds every marketplace `skills/*/scripts/` directory to `sys.path`
and imports the live router, explicitly so *"the audit replays it rather than re-deriving any
threshold"*, degrading to a named `no_routing_logic` verdict on any import failure instead of aborting.
**Adopt that shape verbatim, including the named-degradation arm** — a coordinator that cannot be
imported must produce a stated `indeterminate`, never a zero.

The coordinator's own surface:

- **Two modes, one computation.** A per-plan mode (one plan directory → one score record) and a corpus
  mode (many plan directories → the aggregate plus the per-plan table). ⛔ **The corpus mode is the
  per-plan mode applied N times and summed — it is NOT a second implementation.** Two implementations
  would eventually disagree, and the disagreement would be invisible because no consumer reads both.
- **Every emitted count rides with the population it was computed over.** This epic's standing rule; a
  figure without its denominator is not publishable.

---

**D2 — the scoring core: signal presence first, yield second, and the two are NEVER folded into one
number.**

⛔⛔ **BEFORE writing (a): the honesty vocabulary this deliverable needs ALREADY EXISTS for one gate, and
a second one must not be invented.** `script-shared/scripts/build/_gate_coverage.py` implements
`CoverageBoundary` (what was checked vs what was **degraded**, with the reason), `AnalysisLimit` /
`structural_limits` (what a check can NEVER see however wide its scope), and `parity_population` — and it
states this plan's own thesis verbatim: *"a parity table computed over nothing looks identical to perfect
parity, which is exactly the confident-but-empty signal."* Its scope is the **build gate only**
(`build.py` wires it into the mypy / `verify` / `quality-gate` paths). ⇒ **This plan generalizes that
existing idea from one gate to the whole chain; it does not re-derive it.** D2 either reuses those types
directly or records why the chain-level question needs a different shape. ⭐ Note the distinction that
module already draws and that this plan inherits rather than re-invents: a **degraded** verdict is cured
by re-running, a **structural limit** is not cured by anything. A mechanism that did not fire and one
that fired but cannot see the defect class in question are not the same absence.

*(a) The three-state presence resolver.* Per plan × per mechanism, resolve `not_admitted` /
`admitted_not_fired` / `fired` from `execution.toon` — `candidate_steps` supplies admission,
`execution_log[]` supplies firing. ⚠ **`fired` must be re-fire aware**: the worked example logs
`pre-submission-self-review` **twice** (`error` at 16:47, then `executed` at 16:57), so a naive row count
reports one gate as two. A `refire-report` verb already exists on `manage-execution-manifest` for exactly
this question — read it rather than counting rows.

*(b) Coverage, published separately.* `fired / admitted` per mechanism, with the `not_admitted` members
**named, not just counted**. ⛔⛔ **The yield denominator is the FIRED set and nothing else.** Dividing by
the full mechanism roster makes disabling a gate raise the score; dividing by the admitted set makes
*failing to run* an admitted gate raise it. Both are the same defect and the design must be immune to
each. A plan's coverage and its yield are reported as two figures, and any single headline number that
combines them must carry both as visible components or not exist at all.

*(c) Yield — the quality points.* Per fired mechanism, partition the findings it produced by:

1. **Disposition class**, per D0(b) — `resolved` (fixed) · `refuted` (rejected) · the D0(b) decision for
   the absorbed/suppressed middle · `pending` (never a point).
2. **Finding type**, over the shipped 14-member `FINDING_TYPES` taxonomy at
   `tools-file-ops/scripts/constants.py:118`. ⛔ **Import it; do not restate it.** The tally must span the
   WHOLE vocabulary so a type nothing produced publishes a stated zero.
3. **Severity**, over `FINDING_SEVERITIES` (`error` / `warning` / `info`), for the same reason.

*(d) Escape distance, reported and never baked in.* The existing `quality-chain` check already
establishes the cost ordering `build → self-review → auto-review → human-review`. A defect caught at
`auto-review` slipped every cheaper gate before it, so **where** a point was earned is real information —
but it answers a *different question* (chain efficiency) than **how many** points were earned (chain
yield). ⛔ Report escape distance as its own figure. Folding a shift-left weight into the headline makes a
plan that caught 10 defects early numerically indistinguishable from one that caught 3 late, which is the
conflation the two-figure split exists to prevent.

⛔⛔ **Three traps the scorer MUST be built against, each first-party and each already observed:**

- **A bot refusal scores a point.** In the worked example, Sourcery's *"you've used your own review
  budget of 250,000 diff characters"* notice is filed as a `pr-comment` finding carrying
  `resolution: taken_into_account`. Under any mapping that credits `taken_into_account`, **a bot saying
  it did no work earns a quality point.** A recognizer already exists —
  `workflow-integration-github/scripts/github_pr.py` `_is_refusal_notice`, already imported and used by
  the participation classifier at `:971` — and it MUST be reused, not re-implemented. ⭐ A refusal is
  positive evidence the mechanism did NOT run, so it belongs on the PRESENCE side as a
  `fired_but_refused` reading, not on the yield side at all.
- **`pending` is seeded, not chosen.** `manage-findings.add_finding` stamps `resolution: pending` on
  every record, and the existing `quality-chain` check documents that the pending column is two
  populations (actionable defect debt vs structural knowledge findings). Reuse that split; do not invent
  a second one.
- **The bot attribution is already structured — do not regex for it.** The shipped `pr-comment` rows
  carry a top-level `bot_kind` field (`"bot_kind": "sourcery"` in the worked example). The existing
  `quality-chain` check classifies bots by regex over the `detail` prose (`_QC_BOT_RE`). ⇒ **Reading
  `bot_kind` is strictly better**, and where the new core and the old check disagree the discrepancy is a
  reportable finding rather than something to paper over.

---

**D3 — consumer 1: the corpus quality report, and the first run's README complement.** Extend
`.claude/skills/audit-archived-plan-retrospectives` with a check that calls D1's corpus mode and emits
its rows, following the skill's own hybrid contract to the letter: **the script computes and emits, the
LLM interprets** — and the check ships with a `checks/{name}.md` interpretation sub-document like every
one of its twenty-four siblings, because the SKILL.md contract requires every emitted block to be
processed against one.

The first run produces a report that **complements** `doc/analyzis-cloud-plan/README.adoc` rather than
restating it: that document is the quantitative view (artifact counts, resolution percentages, cost); this
is the qualitative one (points earned, by mechanism and kind, over a stated coverage). ⚠ **The comparison
must be stated as complementary, not corrective** — the README's figures are not wrong, they answer a
different question, and a report that reads as a rebuttal of a document the project already relies on
will be believed less, not more. ⛔ **Do not edit the README's own findings.** If the new view contradicts
one of them, that is a finding to report, not an edit to make in this plan.

⚠ **Scope note the operator set:** *"For the first run (until the other aspect landed) it must retrieve
all aspects regarding the quality aspects."* ⇒ The first run is a **backfill over the whole archived
corpus**, and it necessarily reads plans whose artifacts predate parts of the schema. That is what makes
D0(c)'s two-population count load-bearing: a plan with no `candidate_steps` block is `indeterminate` on
presence and MUST NOT be scored as if every gate were absent.

---

**D4 — consumer 2: augment the per-plan `plan-retrospective` output.** Register a new section that calls
D1's per-plan mode, so every future plan reports its own quality score without a corpus sweep.

The seam is already established and must be used rather than bypassed: a `collect-*.py` producer emits a
fragment, and `compile-report.py` renders it under a heading registered in `retro_sections.py`
`SECTION_SPEC` (`:119`), a `(heading, fragment_key, conditional_trigger)` triple.

⛔⛔ **The trigger choice is the whole correctness question for this section, and `retro_sections.py`
already documents the exact trap in two adjacent comments.** `Direct gh/glab Usage` and the
`Execution-Context Dispatch Audit` are both registered with `conditional_trigger = None` precisely
because *"a clean run emits a populated counts block with an EMPTY findings list"*, and a self-trigger
*"would refuse that fragment while `_fragment_has_payload` still reports payload, mis-classifying a
healthy run as `sections_dropped`."* ⇒ **This section is exactly that shape** — a plan whose gates all
fired clean produces populated coverage counts and zero points. It therefore takes
`conditional_trigger = None`, and D4 must state that reasoning in the registration comment as its
siblings do. A self-triggered registration here would silently drop the section for precisely the
highest-quality runs.

⚠ Section **position** in `SECTION_SPEC` is not free: the file records that `Chat History Analysis` pins
an adjacency between `Routing Decisions` and `Proposed Lessons`, and that the footprint aggregate is
placed before every aspect it aggregates so the reader meets the caveat first. Choose a position, and
record why it does not break either constraint.

---

**D5 — the tests, and they are the deliverable that outlives the other five.** ⛔ Every detector here is
set-guarding, so this epic's standing rule binds: **population-derived, never a restated literal**, and
each check publishes the population size so a suite that degenerates to zero cannot report green.

Four properties, each needing a **matched positive and negative control** — a test that only ever sees
the healthy case cannot fail:

1. **The three presence states are distinguishable.** A fixture with one `not_admitted`, one
   `admitted_not_fired` and one `fired`-clean mechanism must produce three DIFFERENT readings. ⛔ This is
   the test that would have caught the whole defect class; if it passes vacuously the plan has shipped
   nothing.
2. **Disabling a gate cannot raise the score.** Two fixtures identical except that one drops a mechanism
   from `candidate_steps`; assert the dropped one does not score higher. ⭐ **State it as an inequality
   over two fixtures, not as an expected constant** — a pinned constant tracks whatever the scorer
   currently does, including the defect.
3. **A refusal notice earns no point.** Feed the real Sourcery budget-refusal body; assert it lands on
   the presence side and contributes zero yield.
4. **The type and severity tallies span their whole vocabularies.** Derive both from the imported
   constants and assert every member is present as a key, so adding a 15th finding type cannot silently
   fall out of the report.

⚠ **`test_inject_project_dir.py` is this epic's recorded cautionary precedent and applies directly** — it
re-declared a whitelist as a literal list and asserted against a shape no production caller writes, which
locked a defect in rather than catching it. Import the vocabularies; never retype them.

---

**D6-D8 MOVED TO `PLAN-TRUTH-124` — this plan CONSUMES them, it no longer builds them.**

Operator decision, 2026-09-02: the work was cut two ways — a clean-slate **unified ledger model**
(forward-only) and a separate **historical analysis**. `PLAN-TRUTH-124` is the first; this plan is the
second, plus the instrument. Three former deliverables moved there because they are schema acts, not
scoring acts, and are listed here so nothing is silently dropped:

| Was | Now | Why it moved |
|---|---|---|
| D6 — orchestrator corroboration emitter | `-124` D4 | it defines a record, it does not score one |
| D7 — `landings/PLAN-NN.json` | `-124` D5 | same — the schema is forward-only; the BACKFILL question stays here |
| D8 — criticality band + relevance mark | `-124` D2/D3 | a shared vocabulary belongs with the vocabulary |

⭐⭐ **And `-124` D6 adds a `statistics` read seam this plan consumes**: one verb returning the unified
data as a standardized TOON model. ⇒ **D1's coordinator is a CALLER, not a reader.** It does not
re-implement per-ledger readers across five formats — the ledger owns the read, this instrument owns the
scoring. ⛔ A coordinator that grows its own ledger readers has taken back work `-124` shipped.

⛔⛔ **HARD ORDERING: `-124` must land before this plan is emitted.** Scoring against a schema still
being designed is the one sequencing error that makes both plans wrong at once.

## Claim Labels

Corroborated first-party at HEAD `30cd8aaf8` on 2026-09-02 unless marked otherwise; re-ground at the
plan's own HEAD before relying on any one of them.

- **OBSERVED** — `execution.toon` carries both `candidate_steps[26]` and `execution_log[29]`, and the two
  disagree: `finalize-step-security-audit`, `sonar-roundtrip` and `adr-propose` are admitted with no log
  row. Read at `.plan/local/archived-plans/2026-08-31-git-artifact-scanning-and-destructive-recovery/execution.toon`.
  ⇒ the `admitted_not_fired` state is real, not hypothetical.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Worked-example execution.toon still has candidate_steps[26] and execution_log[29]; security-audit/sonar-roundtrip/adr-propose admitted with no log row
- **OBSERVED** — the same file carries `lessons-capture: {lane: off}`, so the `not_admitted` state is
  also live in the same run. ⇒ one plan exhibits all three presence states.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Same file step_params still carries lessons-capture lane off
- **OBSERVED** — `pre-submission-self-review` appears TWICE in `execution_log` (`error` 16:47:34, then
  `executed` 16:57:29). ⇒ a row-count firing test double-counts.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: pre-submission-self-review appears twice in execution_log: error at 16:47:34.977046, executed at 16:57:29.744706
- **OBSERVED** — a Sourcery review-budget refusal is stored as a `pr-comment` finding with
  `resolution: taken_into_account` and `bot_kind: sourcery`. Read at that plan's
  `artifacts/findings/pr-comment.jsonl`, `hash_id: 536818`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: pr-comment.jsonl hash_id 536818 carries resolution taken_into_account and bot_kind sourcery, confirmed verbatim
- **OBSERVED** — `pr-comment` records carry a structured `bot_kind` field, while the existing
  `quality-chain` check classifies bots by regex over `detail` (`_QC_BOT_RE`, documented in
  `checks/quality-chain.md`). ⇒ a better-grounded reading exists and is unused.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Findings carry a structured bot_kind field; audit.py _QC_BOT_RE regex still classifies by text match over detail
- **OBSERVED** — `COMMITTED_RESOLUTIONS` / `RELEASED_RESOLUTIONS` exist at
  `phase-6-finalize/scripts/review_commitments.py:96` and `:102`; `FINDING_TYPES` (14),
  `FINDING_SEVERITIES` (3) and `VALID_RESOLUTIONS` (6) at `tools-file-ops/scripts/constants.py:118`,
  `:146`, `:174`. ⇒ every vocabulary this plan needs already has exactly one home.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: review_commitments.py:96/102 exact; constants.py FINDING_TYPES:118 (14) VALID_RESOLUTIONS:174 (6) exact; FINDING_SEVERITIES at :148 not :146, still 3 values
- **OBSERVED** — `audit.py:2120` `_load_routing_logic` already imports live marketplace logic from the
  project-local audit and degrades to a named verdict on failure. ⇒ the cross-tree call has a precedent.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: audit.py:2120 _load_routing_logic imports the live router and degrades to no_routing_logic on any import failure
- **OBSERVED** — `retro_sections.py:119` `SECTION_SPEC` is a `(heading, fragment_key,
  conditional_trigger)` registry, and two entries carry recorded comments explaining why a clean-but-
  populated fragment must register `None` rather than self-trigger.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: retro_sections.py:119 SECTION_SPEC is the heading/fragment_key/conditional_trigger tuple; both named headings present
- **OBSERVED** — `manage-execution-manifest` exposes a `refire-report` verb. ⇒ re-fire counting is a read,
  not a new derivation.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: manage-execution-manifest.py still references a refire-report verb
- **HYPOTHESIS** — that `candidate_steps` is present in every archived plan's `execution.toon`.
  ⛔ **Unswept — one plan was read, not the corpus.** Confirm/refute across
  `.plan/local/archived-plans/*/execution.toon` (verify-at-outline); this is D0(c) and a refutation
  changes the reportable population rather than merely a number.
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: REFUTED: 28 of 39 archived plans carry candidate_steps in execution.toon; 11 do not. Re-scoped: the presence oracle is a SAMPLING oracle and the 11 must be stated as a population.
- **HYPOTHESIS** — that `build-results/` is the right presence oracle for the build mechanism (the worked
  example carries three module subdirectories). Confirm/refute against `execution.toon`'s
  `verify:quality-gate` / `verify:compile` log rows, which may be the better-grounded source
  (verify-at-outline).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: HYPOTHESIS on build-results/ as presence oracle; not independently adjudicated this pass
- **OBSERVED** — `workflow-integration-sonar/scripts/sonar.py` `_map_severity` collapses `BLOCKER`,
  `CRITICAL` and `MAJOR` all into `error`, `MINOR` into `warning`, `INFO` into `info`, and returns `None`
  for anything else (the finding is then written with no severity at all). ⇒ **the criticality
  distinction D8 is asked to provide is destroyed at ingest**, and the fix is at the producer boundary,
  not in a new consumer field.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: sonar.py _map_severity confirmed exact (same site as -124 claim 2)
- **OBSERVED** — corpus key census over `.plan/local/archived-plans/*/artifacts/findings/*.jsonl`:
  **2570 records total**; `severity` present on **1941 (75.5%)** with values `error` 1427 / `warning` 472
  / `info` 42, and **absent on 629 (24.5%)**. `type`/`title`/`resolution` present on 2294; `file_path`
  2278; `module` 1335; `rule` 1328. ⇒ a criticality histogram computed today omits a quarter of the
  corpus. ⇒ `-124` D2c owns the remedy; this plan must REPORT `unclassified` honestly until it lands.
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: Findings census stale (same site as -124 claim 3): 3286 records at 68.5 pct, not 2570 at 75.5 pct. Re-scoped to a derivation pointer.
- **OBSERVED** — **no `deliverable`, `requirement` or `traceability` key exists on any of the 2570
  records** (full census above; the 30 most common keys were enumerated and none is a requirements
  anchor). Deliverable references appear only inside prose titles. ⇒ the relevance axis has no field
  today. ⇒ `-124` D3 owns the remedy.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: No deliverable/requirement/traceability key found on any record in the current 3286-record census, same as claimed
- **OBSERVED** — the store holds TWO record schemas: the 276 records lacking `type` are **all** in
  `assessments.jsonl` and carry `certainty`/`confidence`/`agent`/`evidence`. 2294 + 276 = 2570, so the
  partition is exhaustive. ⇒ summing them into one finding histogram is wrong (D0e).
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: REFUTED: the schema split no longer sums -- 2754 + 519 = 3273 against a 3286 total, a 13-record gap that nothing reports. Re-scoped: D0 gains a deliverable to identify the 13 unpartitioned records.
- **OBSERVED** — the landing corpus is 200 records across all epics; **36 (18%) carry a corroboration
  section under 20 DISTINCT heading spellings**; 111 (55%) mention "corroborated" anywhere and 20 (10%)
  mention "contradicted". Swept over `.plan/local/orchestrator/*/landings/*.md`. ⇒ D6's premise is
  measured, not asserted.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Landing corroboration shape holds: 209 records 42 (20 pct) 19 spellings
- **OBSERVED** — `templates/landing-analysis.md` carries no corroboration section at all (its five
  sections are Deliverable Fidelity, Metrics and Anomalies, Routing and Merge Behavior, Reconciliation
  Actions, Follow-Ups). ⇒ the 18% is a template gap, not authoring laxity.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: templates/landing-analysis.md five headings confirmed, no corroboration section
- **OBSERVED** — `analyze.md` Step 2b states that a corroboration not belonging to a staged spec *"is
  recorded in the landing report as before and persists no verdict"*. ⇒ the unstructured landing
  corroboration is a PRIOR DECISION that D6 reverses deliberately.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: analyze.md Step 2b sentence found verbatim
- **OBSERVED** — `plan-marshall:plan-retrospective` fires at `08:04:59` and `emit-landing` at `08:32:36`
  in the worked example's `execution_log`. ⇒ the per-plan retrospective structurally precedes the
  landing, so the orchestrator verdict cannot exist at that tier — D4 must declare it out-of-observation-window, never `not_admitted`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: plan-marshall:plan-retrospective row timestamped 08:04:59.522368, emit-landing at 08:32:36.945956 -- exact match
- **OBSERVED** — `standards/landing-payload-spec.md` defines the fenced `landing-facts` block with a
  `schema` key, a required-key table, a validator (`check_landing_completeness`) and a named
  produce/validate/drain contract. ⇒ `-124` D4a mirrors a shipped pattern; this plan consumes the result.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: landing-payload-spec.md contains the landing-facts schema key and check_landing_completeness
- **OBSERVED** — PLAN-PR-024's landing records `⛔ CONTRADICTED` against both *"the landing message is
  complete"* and *"registry pin gate holds"*. ⇒ the orchestrator mechanism demonstrably catches defects
  no in-plan gate can, because a plan cannot audit its own honesty.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: PLAN-PR-024 landing table rows read exactly: Landing message is complete CONTRADICTED, Registry pin gate holds CONTRADICTED
- **OBSERVED** — `script-shared/scripts/build/_gate_coverage.py` already implements `CoverageBoundary`,
  `AnalysisLimit` / `structural_limits` and `parity_population`, scoped to the BUILD gate and wired in by
  `build.py`. Its module docstring states this plan's thesis for that one gate. ⇒ the vocabulary exists;
  the gap is that nothing applies it across the chain. **This is a partial answer to the verify-first
  clause below and it changes D2 from "design a vocabulary" to "generalize an existing one".**
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _gate_coverage.py CoverageBoundary vs AnalysisLimit split confirmed exact
- **Verify-first clause** — before D2 is scoped, confirm that no existing check already computes a
  presence-aware score ACROSS mechanisms. Three surfaces were read first-party and none does:
  `quality-chain` and `quality-verification-report` (neither reads `execution.toon` at all) and
  `_gate_coverage.py` (build gate only). ⛔ **But the audit skill carries 24 checks and only two were
  examined in full**, so this clause is PARTIALLY discharged, not closed. Complete the sweep at outline;
  a refutation loops back to extending the existing check rather than adding a 25th.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Verify-first clause self-declared partially discharged (2 of 24 audit checks examined); not completed this pass

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/` — the coordinator's
  new module and its `collect-*` producer (D1, D2, D4). Marked HYPOTHESIS because D0/D1 settle whether
  the core's home is this skill or `script-shared`; both are declared below so neither choice
  under-declares (verify-at-outline).
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/` — the alternative home
  for the shared core if D1 finds a second consumer outside `plan-retrospective` (verify-at-outline).
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/retro_sections.py`:119 —
  the `SECTION_SPEC` registration (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py` — the
  fragment renderer and its `should_emit` dispatch (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md` — the new section's
  documented contract (D4)
- OBSERVED: `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` — the new check's
  computation entry and the marketplace import seam (D3)
- OBSERVED: `.claude/skills/audit-archived-plan-retrospectives/SKILL.md` — the check roster and the
  frontmatter description (D3)
- OBSERVED: `.claude/skills/audit-archived-plan-retrospectives/checks/` — the new interpretation
  sub-document (D3)
- OBSERVED: `doc/analyzis-cloud-plan/` — the first run's complementary qualitative report (D3).
  ⛔ **`README.adoc` itself is READ-ONLY to this plan** — see D3.
- OBSERVED: `test/plan-marshall/plan-retrospective/` — the D5 tests for the core and the section
- OBSERVED: `test/plan-marshall/audit-archived-plan-retrospectives/` — the D5 tests for the corpus check
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py` — READ-ONLY
  reference; the vocabularies are imported, never restated (D2, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py` —
  READ-ONLY reference; the resolution partitions are imported (D0b, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py` —
  READ-ONLY reference; the coverage/limit vocabulary D2 reads (its unification is `-124` D1's)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` —
  READ-ONLY reference; `_is_refusal_notice` is reused by D2's refusal exclusion. ⚠ Declared despite the
  read-only intent, because the parser cannot express read-vs-write and under-declaring would admit a
  colliding plan

## Dependencies and Sequencing

- ⛔⛔ **DEPENDS ON `PLAN-TRUTH-124`, HARD.** That plan ships the unified vocabulary, the
  `severity_reported`/`severity_assessed` pair, the requirements-relevance mark, the corroboration
  emitter, the `landings/PLAN-NN.json` schema, and the `statistics` read seam this plan's coordinator
  CALLS. **Emitting this plan first would have it score against a schema still being designed** — the one
  sequencing error that makes both plans wrong at once.
- ⚠ Re-ground the Expected Surface at outline if any of `-101` / `-102` / `-089` has landed meanwhile.
- ⛔⛔ **BLOCKED ON A LIVE CROSS-EPIC PLAN — machine-derived, not hand-predicted.** `corpus cross-check`
  reports a `live_plan` overlap with `misconfigured-reviewer-name-reads-missing-review`
  (`review-apparatus/PLAN-PR-044`, live at phase `3-outline` as of 2026-09-02) on ONE file:
  `workflow-integration-github/scripts/github_pr.py`, which this plan only READS (`_is_refusal_notice`).
  ⭐ **The re-cut SHRANK this block back to one file** — `manage-findings/standards/jsonl-format.md` moved
  to `-124` along with the fields it declares, so the write collision moved with it. ⚠ **That block is now
  `-124`'s**, and it is a genuine write collision there. A declared surface carries no read/write intent,
  so the gate will still refuse this candidate until PLAN-PR-044 lands.
- ⛔⛔ **NOT A DUPLICATE OF `review-apparatus/PLAN-PR-030`, and the ruling must not be re-opened as an
  ownership question — but its D4 is the PRODUCER side of this plan's D2(a).** PLAN-PR-030 D4 is *"make
  every gate verdict distinguish checked, degraded, not-reached, and never-performed"* — a fix INSIDE each
  gate's own output. PLAN-TRUTH-123 is a CONSUMER instrument that reads the ledgers after the fact and
  scores across plans. Different side, different artifact, different epic. ⭐⭐ **But they are two
  vocabularies for one fact, and that is the duplicate-source-of-truth defect this epic keeps recording.**
  ⇒ If PLAN-PR-030 D4 has landed by the time this plan reaches outline, D2(a) MUST read that verdict
  rather than re-deriving presence from `execution.toon`; if it has not, D2(a) must adopt its four-state
  vocabulary rather than coining a three-state near-synonym. Settle this in D0 and record the answer.
  ⚠ The two also share `phase-6-finalize/scripts/review_commitments.py` (read-only here).
- ⚠ **D6 WIDENED THIS PLAN'S SURFACE from 15 to 21 declared paths and bought new sequencing debt — this
  is the recorded cost of folding it in rather than splitting.** Reaching into the `plan-orchestrator`
  tree adds staged collisions with **`-099`, `-100`, `-106`, `-110`, `-115`, `-121`**. ⛔ Re-derive that
  set from `corpus cross-check` at emit time rather than trusting this list; it is a snapshot. If the
  sequencing cost proves worse than the coupling benefit, that is the D6 split trigger firing.
- Adjacent to: **PLAN-TRUTH-085** (*orchestrator-inbox-lifecycle-cleanup-and-landing-payload*, shipped)
  owns the landing-payload surface D6a mirrors. ⛔ **Read its landing before scoping D6a** so the new
  corroboration block does not contradict the `landing-facts` contract it settled.
- ⚠ **Heavy sibling-epic overlaps in `code-intelligence-substrate`, both staged, neither examined:**
  `PLAN-CIS-051-detector-and-auditor-integrity` shares **six** declared files (both retrospective script
  surfaces, both SKILL.mds, both test dirs) and `PLAN-CIS-050-measurement-and-cost-integrity` shares
  **five**. ⛔ **Cross-check these two before this plan is emitted** — at that overlap width the question
  is genuine ownership, not sequencing, and CIS is under a standing operator hold so the answer is not
  simply "they go first".
- Overlaps with: **PLAN-TRUTH-104** (*a clear verdict over an empty population is reported as a checked
  negative*) is the nearest archetype-sibling and its D0 sweeps for exactly this failure shape. ⭐ **The
  relationship is deliberate and is not a duplicate:** -104 sweeps the population of such verdicts across
  the tree; this plan builds ONE new instrument and is obliged not to introduce a fresh instance. If
  -104's sweep reaches the quality-score surface, it records and defers here.
- Overlaps with: **PLAN-TRUTH-110** (*a plan decides what the epic learns and nothing audits that
  decision*) also touches `plan-retrospective`. Machine-check before pairing — do not hand-derive.
- Adjacent to: **PLAN-TRUTH-108** (self-review close criteria) and **PLAN-TRUTH-112** (plugin-doctor rules
  that emit nothing) both concern gates that under-report. Neither is touched here; this plan measures
  the chain, it does not change any gate's behaviour.
- ⛔ **This plan changes NO gate.** It adds measurement only. A deliverable that starts modifying what a
  quality step does has left this plan's scope and belongs in a new spec.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-123-the-quality-chain-has-no-score-and-a-disabled-gate-is-indistinguishable-from-a-clean-one.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO
file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⛔ RE-SCOPED 2026-09-05 — cleanup re-grounding at `66320e70d` (3 claims contradicted)

⛔ **Claim bullets LEFT VERBATIM** — their ordinals address the persisted verdicts.

| Claim | Was | Is at HEAD |
|:-:|---|---|
| 9 | every archived plan's `execution.toon` carries `candidate_steps` | **REFUTED** — **28 of 39** carry it; **11 do not** |
| 12 | the findings census figures (shared with `-124` claim 3) | **3286** records at **68.5%** severity-present, not 2570 at 75.5% |
| 14 | the schema split sums exhaustively over the corpus | **It no longer does: 2754 + 519 = 3273 against a 3286 total — a 13-record gap** |

⭐⭐⭐ **Claim 14's refutation is the most valuable result of this whole re-grounding pass, and it is
this spec's own thesis firing on the spec itself.** A partition that used to be exhaustive is now short
by 13 records, and **nothing reported that** — the split still looks complete. ⇒ **D0 gains a
deliverable it did not have: identify the 13 unpartitioned records and state whether the schema grew a
third class or the partition lost one.** ⛔ Do not "fix" it by widening a bucket until the arithmetic
closes; that would restore the appearance the defect hides behind.

⚠ Claim 9's refutation NARROWS the plan honestly: a presence oracle that holds for 28 of 39 is a
**sampling** oracle, and D0 must state the 11 as a population rather than treating them as noise.

## ⛔⛔ SPLIT-GUARD NOTICE 2026-09-05 — OVER THE GUARD AT 14 DELIVERABLES. OUTLINE MUST PRESUME A SPLIT IS REQUIRED.

**Measured at cleanup: 14 deliverables, 487 lines.** The operator-raised split guard for this epic is
**12**, so this spec is over it by 2.

⛔ **This notice does NOT authorise absorbing the overage.** The default action is to split along
deliverable-group boundaries into sequential (or surface-disjoint parallel) plans. **Proceeding unsplit
requires a recorded rationale naming why the parts cannot ship independently** — a tightly-coupled
oversized plan is permitted, an unexamined one is not.

⚠ **Re-count before deciding.** This pass re-grounded every claim and re-scoped several; the
deliverable set may have moved underneath the number above. **Re-derive the count at outline rather than
inheriting it** — that is this epic's own promoted rule about restated figures, and it applies to this
notice too.

⭐ **Recorded rather than applied, by operator decision at the 2026-09-05 cleanup.** A5 redistribution is
the least-reversible class in the verb, and outline has more context about deliverable coupling than the
orchestrator does. **The orchestrator's job here was to make the overage impossible to miss, not to cut
the plan.**

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-152-the-retrospective-quality-chain-and-assessments-graded-at-report-time.md` (PLAN-TRUTH-152)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.

# PLAN-TRUTH-124: One ledger vocabulary, clean slate — so the same word means the same thing in every ledger

epic: truthful-signals
workstream: WS-01
priority: HIGH — operator-designated 2026-09-02; it is the BLOCKER for PLAN-TRUTH-123, so it precedes it

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-TRUTH-124-one-ledger-vocabulary-clean-slate-so-the-same-word-means-the-same-thing-everywhere.md`
> and is queued in the epic `status.json` `plans[]` field. The orchestrator EMITS the command below;
> it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief, so
> every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Operator decision, 2026-09-02, taken after `PLAN-TRUTH-123` had grown to nine deliverables: *"On the one
hand a unified model over all ledgers (clean-slate approach, saying even the adaptions for requirements /
plans have the same wording / schema) — a separate task for reviewing/analyzing all the plans prior to
these adaptations."* This spec is the **first** of that two-way cut; `-123` is re-cut as the second
(instrument + historical analysis) and **consumes this one**.

⭐ **The cut direction is the point.** A clean-slate model designed to be TRUE, then a separate pass
reporting how much of history maps onto it. ⛔ **The reverse — letting what happens to be parseable in
legacy artifacts shape the forward model — is how the current heterogeneity was reached**, and it is
what folding the backfill into the design would have repeated.

## Objective

**The same question is answered by different vocabularies in different ledgers, so no consumer can read
across them.** Measured first-party at HEAD `30cd8aaf8`: **58 declared vocabulary constants across 24
skills**, over **five artifact formats** (`.toon` 922 files, `.json` 517, `.md` 475, `.jsonl` 250,
`.log` 2044, across 30 archived plans).

⛔⛔ **58 is NOT the number that needs unifying, and treating it as such would be this epic's own
under-derived-completeness defect.** Most of those vocabularies are legitimately distinct domains —
`BOT_KINDS`, `MERGE_QUEUE_ELIGIBLE_STATES` and `BUILD_STATUSES` answer genuinely different questions and
must stay apart. **The defect is the subset where ONE question has many spellings**, and deriving that
subset is D0's job, not this Objective's to assert.

The clearest observed instance of the real defect — the *"did this check run, and what did it conclude?"*
question, answered by at least these, each in its own closed set:

| Vocabulary | Home | Values (as observed) |
|---|---|---|
| `FINDING_SEVERITIES` | `tools-file-ops/constants.py` | `error` / `warning` / `info` |
| Sonar issue severity | `workflow-integration-sonar` | `BLOCKER` / `CRITICAL` / `MAJOR` / `MINOR` / `INFO` |
| corroboration verdict | `plan-orchestrator/workflow/analyze.md` | `corroborated` / `contradicted` / `unverifiable` |
| re-grounding verdict | `orchestrator corpus verdicts` | its own set, plus derived `admits` / `stale` |
| `COVERAGE_VERDICTS` | `manage-lessons` | its own set |
| `CLAIM_SECTION_STATES` | `plan-orchestrator` | `absent` / `empty` / `unreadable` / `parsed` |
| `INBOX_STATES` | `plan-orchestrator` | `present` / `missing` |
| `FINDINGS_STORE_STATES` | `manage-findings` | its own set |
| compaction invariants | `orchestrator compact` | `ok` / `violated` / `indeterminate` |
| restart-readiness signals | `orchestrator cleanup` | `ready` / `not_ready` / `indeterminate` / `not_available` |
| gate coverage | `script-shared/build/_gate_coverage.py` | checked / **degraded** (+ structural `AnalysisLimit`) |

⭐ Every one of them is individually well-designed, and several carry excellent reasoning in their own
docstrings. **The defect is not any single vocabulary — it is that a reader crossing two ledgers must
learn a new dialect at every boundary, and a machine crossing them cannot.**

⇒ This plan settles ONE shared vocabulary for the shared question, gives it ONE home, and makes the
adaptations — the requirements marks, the plan-level records — speak it too. **Forward-only.**

## ⛔⛔ Scope fence — read before the first edit

- **FORWARD-ONLY. This plan performs NO BACKFILL and analyses NO archived plan** beyond D0's bounded
  feasibility probe. Mapping history onto the model is `PLAN-TRUTH-123`'s job, and it is a separate
  spec precisely so this one is not bent by what legacy artifacts happen to contain.
- **This plan computes NO SCORE.** It defines the vocabulary and the records that carry it. The
  coordinator, the scoring core and both consumers are `-123`'s.
- **It does not unify formats.** TOON for phase records, JSONL for append-only findings, JSON for state
  and Markdown for human reports are defensible per-purpose choices; **the target is one VOCABULARY, not
  one file format.** ⛔ A deliverable that starts converting `.toon` to `.json` has left this plan.

## Deliverables

Eight deliverables, under this epic's raised split guard of 12. D0 is a gate.

---

**D0 — GATE: derive the SAME-QUESTION subset, and probe feasibility, before designing anything.**

- *(a) The overlap derivation.* Walk all **58** declared vocabulary constants across the **24** skills and
  classify each: does it answer the *"did it run / what did it conclude"* question, or a genuinely
  different one? ⛔ **Publish both partitions with the population**, and name the criterion. A vocabulary
  left OUT is a decision to record, not an omission — the eleven in the Objective table are a **floor
  derived from a first-party sample, explicitly not the population.**
- *(b) The write-site population.* Enumerate every site that files a finding. **First-party floor: six
  skills** (`automatic-review`, `manage-findings`, `manage-lessons`, `workflow-integration-github`,
  `workflow-integration-gitlab`, `workflow-integration-sonar`) plus **7 `ext-triage-*` implementors**.
  Publish the derived count — it sizes D2 and D3.
- *(c) A BOUNDED feasibility probe — and it is bounded on purpose.* Read **a handful** of archived plans
  (D0 fixes the number, and it is small) purely to confirm the proposed vocabulary is expressible against
  real artifacts. ⛔⛔ **This is NOT the historical analysis and MUST NOT grow into one.** Its only
  question is *"can a real record carry this?"*, never *"what does history contain?"* ⚠ Without it the
  model is designed with zero contact with reality; with more than a handful, the clean slate is gone.

⛔ **Do not proceed past D0 until (a)'s partition is recorded as a decision with its criterion.** The
partition IS the design; deriving it inside a later deliverable buries the one judgement the plan has.

---

**D1 — one shared verdict vocabulary, one home, and a stated migration for every adopter.**

Settle the closed set for the shared question and put it in ONE place. ⭐ **`tools-file-ops/constants.py`
is the existing precedent** — it already houses `FINDING_TYPES`, `FINDING_SEVERITIES`, `QGATE_SOURCES`
and `VALID_RESOLUTIONS` as the single home several skills import. Extend that pattern rather than
founding a second registry.

⛔⛔ **A rename is a LOSSY OPERATION unless every distinction survives it.** The vocabularies in the
Objective table are not synonyms with different spellings — several draw distinctions the others do not,
and `_gate_coverage.py` draws the sharpest: a **degraded** verdict is cured by re-running, a
**structural limit** is not cured by anything. ⇒ The unified set must be at least as expressive as the
UNION of what it replaces. **Any distinction that cannot be carried is a deliberate loss to record, never
a simplification to make quietly.** ⚠ `-123`'s D2 will read this vocabulary to resolve gate presence, so
a distinction dropped here becomes unmeasurable there.

---

**D2 — severity is TWO fields, because criticality is mutable.** Operator refinement, 2026-09-02:
*"it starts with the source, but will later be updated — e.g. Sonar or a reviewer reports a critical, but
after triage we downgrade it to medium."*

| Field | Lifecycle | Written by |
|---|---|---|
| `severity_reported` | **IMMUTABLE** once written — the band as RECEIVED, plus `severity_source` naming who said it | the ingesting producer, once |
| `severity_assessed` | **MUTABLE** — the triage verdict, and the one a score reads | the triage step, each time it changes |

⛔⛔ **A single mutable field would destroy the source band on first triage** — once a reviewer's
`CRITICAL` is overwritten with `MEDIUM`, nothing can say whether it arrived critical and was downgraded
or arrived medium. ⭐ This is not a new mechanism: `resolution` is already mutable beside an immutable
`timestamp`, and triage already has a home (`manage-findings` + `ext-triage-{domain}`).

⛔ **A downgrade must be ATTRIBUTABLE** — who, when, why — or *"triage downgraded it"* is unfalsifiable.
Absent an assessment, `severity_assessed` is **unset and a reader falls back to `severity_reported`**; it
is never silently defaulted, because that makes an unassessed finding indistinguishable from a confirmed
one.

*(a) The scale.* **Recommended: the CVSS qualitative rating `NONE` / `LOW` / `MEDIUM` / `HIGH` /
`CRITICAL`** (FIRST.org CVSS specification § *Qualitative Severity Rating Scale*, unchanged v3.1→v4.0) —
a genuine published standard spanning the operator's *"critical to none"*, near-isomorphic to Sonar's
Clean Code bands so the two map without loss. ⚠ **Borrow the BANDS only:** CVSS is a vulnerability
scoring system, so a real CVSS score or vector stays restricted to genuine security findings; claiming
one for documentation drift is a category error. D0 may substitute another **published** scale — never an
invented one, and never the existing three-value diagnostic level.

*(b) Fix the narrowing at the PRODUCER, which is where the loss happens.*
`workflow-integration-sonar/scripts/sonar.py` `_map_severity` collapses **`BLOCKER`, `CRITICAL` and
`MAJOR` all into `error`** (`MINOR`→`warning`, `INFO`→`info`, unknown→no severity at all). ⇒ **The
BLOCKER-vs-MAJOR distinction is destroyed before any consumer can read it**, and no downstream field
recovers it. ⭐ This is `PLAN-TRUTH-077`'s archetype verbatim (*the writer already destroyed the
distinction the reader learned to make*) — **read that spec before scoping D2b.**

*(c) An absent band is `unclassified`, NEVER `NONE`.* `NONE` is a judgement that the finding does not
matter; defaulting to it lets the most under-recorded findings score as the most harmless. ⇒
`unclassified` is a member of the persisted vocabulary, not an absence.

---

**D3 — the requirements-relevance mark, in the same vocabulary and on the same records.** The operator's
second axis, and his framing binds: *"even the adaptions for requirements / plans have the same wording /
schema."*

⛔⛔ **Relevance and criticality are ORTHOGONAL and are never blended into one number.** A trivial typo in
a requirement-bearing contract and a severe race in a throwaway script both land mid-scale on any blend,
and the blend hides which to fix first.

Deliberately coarse, three values: **`requirement-bearing`** (touches a declared deliverable, or an
interface/contract the plan committed to) · **`incidental`** (real, but outside declared scope) ·
**`unassessed`** (nobody classified it — again NOT a synonym for `incidental`).

⚠ **`pm-requirements:traceability` owns spec↔code linkage in this project and MUST be read before an
anchor is invented.** If it already provides one, use it.

---

**D4 — the orchestrator's ground-truth corroboration gets a structured home.** *(moved here from
`-123` D6 — it is a schema act, not a scoring act.)*

Every landing gets an `analyze` pass whose Step 2 contract is *"a pasted or read claim is a lead, never a
fact"*, producing `corroborations[N]{claim,verdict,evidence}`. ⛔ **It is the least recorded mechanism in
the chain — measured over `.plan/local/orchestrator/*/landings/*.md`: 200 landing records, only 36 (18%)
carry a corroboration section, under 20 DISTINCT heading spellings, with free-prose verdict cells.**

⭐ Root cause is structural: **`templates/landing-analysis.md` has NO corroboration section**, so whether
the mandated output is recorded depends on the authoring session. ⛔ It is also a PRIOR DECISION being
reversed deliberately — `analyze.md` Step 2b states a corroboration outside a staged spec *"is recorded
in the landing report as before and persists no verdict"* — and D0 records the reversal with its
rationale.

*(a)* Add the section to the template and give it a fenced machine-readable block, **mirroring the
shipped `landing-facts` precedent** (`standards/landing-payload-spec.md`: schema key + required-key table
+ `check_landing_completeness` validator + named produce/validate/drain contract) rather than inventing a
format. *(b)* **ONE formatter**, per the `corpus set-verdict` precedent (*"the ONLY code path in the tree
that formats a `verdict:` line"*) — otherwise twenty spellings regrow. ⚠ D0 settles whether that is a new
emitter or an extension of `corpus set-verdict`'s scope; two formatters for one vocabulary is the
duplicate-source-of-truth defect this plan exists to end.

---

**D5 — `landings/PLAN-NN.json`: the machine record, forward-only.** *(moved here from `-123` D7.)*

`analyze` writes a JSON record beside the existing `landings/PLAN-NN.md`. **The markdown stays the human
record, the JSON becomes the machine record, and neither is derived from the other by re-parsing prose.**
It carries the plan's identity (`plan_id`, `pr`, `merge_commit_sha`) so a record joins its queue row
without a filename convention, D4's corroboration verdicts, and the fields `-123` will populate.

⛔ **Every count carries its population INSIDE the JSON.** A serialized figure outlives the session that
computed it and will be read by someone who cannot re-run the derivation, so a bare integer in a
persisted record is strictly worse than one in a terminal report.

⛔⛔ **The record states its OWN completeness** — an explicit `schema` version plus a per-section
readable/unreadable marker — so a consumer can tell a **measured** zero from an **unmeasurable** one. A
JSON omitting a section it could not compute is indistinguishable from one where the section was
genuinely empty.

⚠ **No backfill here.** Whether the 200 existing landings get records is `-123`'s question, answered
against this shipped schema.

---

**D6 — `statistics`: one read seam returning the unified data as a standardized TOON model.** Operator
addition, 2026-09-02: *"If we put all information uniformly in the ledger we can implement a method at
the manage-ledger like `statistics`, that returns all unified data as a standardized toon model."*

⭐⭐ **This is the payoff deliverable and it is what makes the unification worth doing.** D1-D5 make the
ledgers speak one vocabulary; without a read seam, every consumer still writes its own reader across
five formats and the heterogeneity simply moves from the data to the readers. **The seam is where a
uniform vocabulary stops being a tidiness argument and starts removing code.**

⭐⭐⭐ **It also re-layers `PLAN-TRUTH-123` and shrinks it.** `-123`'s coordinator was scoped to read the
ledgers itself; with `statistics` it becomes a pure CONSUMER — **the ledger owns the read, the instrument
owns the scoring.** ⇒ Once this lands, `-123` D1 is a call, not a reader. That layering is the reason
this spec is sequenced first, beyond the vocabulary dependency alone.

- **One output shape, whatever the input format.** The caller gets a standardized TOON model and never
  learns which facts came from `.toon`, `.jsonl`, `.json` or Markdown. ⛔ **A per-ledger output shape
  with a shared name is NOT this deliverable** — it re-exports the heterogeneity behind one verb.
- ⛔⛔ **Every count in the model carries its own population.** This epic's standing rule, and it binds
  hardest here because a statistics surface is exactly where bare integers get quoted downstream.
- ⛔⛔ **The model must be able to say "I could not look".** A measured zero and an unmeasurable one are
  different facts, and a statistics verb that renders both as `0` is the defect this whole epic
  catalogues, shipped in the one surface everyone will read. Carry the readable/unreadable discriminator
  per section, matching D5's record.
- ⚠ **Scope, and D0 settles it:** which store hosts the verb, and whether it is ONE verb over a unified
  read or a per-store verb sharing one output contract. The stores are plural today
  (`manage-findings`, `manage-execution-manifest`, `plan-orchestrator`, `manage-change-ledger`), so
  *"the manage-ledger"* names a role, not an existing skill. ⛔ Record which, with the rationale.
- ⚠ **Use the shipped TOON serializer; do not hand-render.** `ref-toon-format/scripts/toon_parser.py`
  provides `serialize_toon` (`:532`) and `parse_toon` (`:385`). ⭐ **Note first-party: a SECOND parser
  exists** — `manage-solution-outline/scripts/_plan_parsing.py:719` `parse_toon_simple` — so this format
  already has two readers. **Verify at outline whether they agree on multiline and on tables**; if they
  do not, that divergence is squarely this plan's subject and should be recorded, not routed around.
- ⛔ **Read-only.** `statistics` computes and returns; it writes nothing. A statistics verb that mutates
  the store it measures cannot be trusted by the thing measuring quality.

---

**D7 — the tests, and they are what makes the vocabulary binding rather than aspirational.** ⛔ Every
check is set-guarding, so this epic's standing rule binds: **population-derived, never a restated
literal**, each publishing its population size so a degenerate suite cannot report green. Four
properties, each with a **matched positive and negative control**:

1. **The unified vocabulary is at least as expressive as what it replaced.** Derive both sets from their
   constants and assert no distinction was lost — including `_gate_coverage`'s degraded-vs-structural
   split, the one most easily flattened. ⛔ This is the test that would catch a lossy rename; if it
   passes vacuously the plan shipped a regression.
2. **`severity_reported` is immutable.** A triage downgrade changes `severity_assessed` and leaves the
   reported band byte-identical — asserted over two states of one record, not over a constant.
3. **An unassessed finding does not read as confirmed**, and an absent band reads `unclassified`, never
   `NONE`.
4. **`statistics` renders an unmeasurable section differently from an empty one.** A fixture with one
   unreadable ledger section and one genuinely-empty section must produce two DIFFERENT readings. ⛔ The
   matched negative control is the whole test: without it the check passes on a model that renders both
   as zero.
5. **Every enumerated write site emits the new fields.** Derive the site list from D0(b)'s enumeration —
   ⛔ never a hand-typed list, which is exactly how `test_inject_project_dir.py` locked a defect in rather
   than catching it.

## Claim Labels

Corroborated first-party at HEAD `30cd8aaf8` on 2026-09-02 unless marked otherwise; re-ground at the
plan's own HEAD before relying on any one of them.

- **OBSERVED** — **58 declared vocabulary constants** matching
  `^[A-Z_]+(STATES|VERDICTS|SEVERITIES|RESOLUTIONS|STATUSES|OUTCOMES|LEVELS|KINDS)` across **24 skills**
  under `marketplace/bundles/plan-marshall/skills/*/scripts/*.py`. ⚠ Labelled OBSERVED as a **grep-derived
  count over one bundle and one naming convention** — it is D0(a)'s FLOOR, explicitly not the population;
  a vocabulary named otherwise, or living in another bundle, is not in it.
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: 58 constants across 22 distinct skills, not 24. Re-scoped: population figures are re-derived at outline or not used.
- **OBSERVED** — five artifact formats across 30 archived plans: `.log` 2044, `.toon` 922, `.json` 517,
  `.md` 475, `.jsonl` 250.
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: Archived corpus is 39 plans, not 30; format counts log 2731 toon 1221 json 644 md 597 jsonl 324. Re-scoped to a derivation pointer.
- **OBSERVED** — `sonar.py` `_map_severity` maps `BLOCKER`/`CRITICAL`/`MAJOR`→`error`, `MINOR`→`warning`,
  `INFO`→`info`, else `None`. ⇒ the narrowing is at the producer (D2b).
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: sonar.py _map_severity L171-185 maps BLOCKER/CRITICAL/MAJOR to error MINOR to warning INFO to info else None -- exact match
- **OBSERVED** — over 2570 archived finding records: `severity` present on **1941 (75.5%)**, absent on
  **629**; **no `deliverable`/`requirement`/`traceability` key on any record** (30-key census); the store
  holds **two schemas** — 2294 findings with `type`/`title`/`resolution` and **276 `assessments.jsonl`**
  records with `certainty`/`confidence`/`agent`/`evidence` (2294+276=2570, exhaustive).
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: Findings census is 3286 records with severity present 2251 (68.5 pct), not 2570 at 75.5 pct. Re-scoped to a derivation pointer.
- **OBSERVED** — 200 landing records; **36 (18%)** carry a corroboration section under **20 distinct
  heading spellings**; 111 mention `corroborated`, 20 mention `contradicted`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Landing corpus now 209 records 42 (20 pct) carry a corroboration heading under 19 distinct spellings -- same shape, counts drifted with corpus growth
- **OBSERVED** — `templates/landing-analysis.md` has no corroboration section; `analyze.md` Step 2b
  states landing-level corroborations persist no verdict.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: templates/landing-analysis.md has exactly the five named headings and no corroboration mention; analyze.md contains the verbatim persists-no-verdict sentence
- **OBSERVED** — six skills call `add_finding` (`automatic-review`, `manage-findings`, `manage-lessons`,
  `workflow-integration-github`, `workflow-integration-gitlab`, `workflow-integration-sonar`) and **7
  `ext-triage-*` implementors** exist. ⚠ A grep-derived FLOOR for D0(b), not the population.
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: Call-site list is wrong in both directions: automatic-review only MENTIONS add_finding in a docstring and does not call it, while script-shared does. Re-scoped: D0 must DERIVE the caller set.
- **OBSERVED** — `_gate_coverage.py` distinguishes a **degraded** verdict (cured by re-running) from a
  **structural limit** (cured by nothing). ⇒ the distinction D1's unified set must not flatten.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _gate_coverage.py implements CoverageBoundary (degraded, cured by re-running) and AnalysisLimit/structural_limits (never cured) exactly as described
- **HYPOTHESIS** — that `tools-file-ops/constants.py` is the right home for the unified vocabulary.
  It already houses four such vocabularies, but it sits in a `tools-*` skill and the unified set is a
  domain concept. Confirm/refute against the import graph at outline; `script-shared` is the alternative
  (verify-at-outline).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: HYPOTHESIS on vocabulary home; a design choice not yet settled
- **HYPOTHESIS** — that the eleven vocabularies tabled in the Objective all genuinely answer ONE question.
  ⛔ **Unswept — assembled from a session's first-party reads, not from a derivation.** Several may draw
  distinctions that make them properly separate. Confirm/refute per vocabulary in D0(a); a refutation
  shrinks the unification and is a re-scope, not a detail.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: HYPOTHESIS that eleven vocabularies answer one question; not independently adjudicated
- **Verify-first clause** — before D1 settles the set, confirm no shipped standard already defines a
  cross-ledger verdict vocabulary. `_gate_coverage.py` defines one for the build gate only, and
  `bot-participation-contract.md` defines a participation taxonomy; neither was found to be cross-ledger,
  but only those two were examined. A refutation loops back to adopting the existing one.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Verify-first clause; no independent re-sweep of shipped cross-ledger vocabularies performed this pass

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py` — the
  vocabulary home (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` — the
  finding writer carrying the new fields (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md` — the
  record contract (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md` — the canonical
  invocations for the new fields (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py` —
  `_map_severity`, the producer boundary where bands are narrowed away (D2b)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` —
  a finding write site (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py` —
  the symmetric write site; ⛔ changing one and not the other is a divergence this project has recorded
  before (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/` — a finding write site
  (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/landing-analysis.md` —
  the corroboration section (D4a)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md`
  — the fenced-block precedent D4a mirrors (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md` — Step 2b's
  routing rule, reversed for landing-level claims (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — the D4b
  formatter and the D5 JSON writer
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md` — the canonical
  invocations for D4/D5
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py` — the
  degraded/structural distinction D1 must not flatten; edited only if D0(a) folds it into the unified set
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py` —
  `COMMITTED_RESOLUTIONS` / `RELEASED_RESOLUTIONS`, reused not re-derived (D1)
- OBSERVED: `test/plan-marshall/manage-findings/` — the D7 severity/relevance tests
- OBSERVED: `test/plan-marshall/workflow-integration-sonar/` — the D7 narrowing-boundary tests
- OBSERVED: `test/plan-marshall/plan-orchestrator/` — the D7 emitter and JSON-record tests
- OBSERVED: `marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts/toon_parser.py` — READ-ONLY
  reference; `serialize_toon` / `parse_toon` are reused, never hand-rendered (D6)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/` — a candidate host for the
  `statistics` verb; D0 settles which store hosts it (verify-at-outline)
- OBSERVED: `marketplace/bundles/pm-requirements/skills/traceability/SKILL.md` — READ-ONLY reference; the
  shipped spec↔code linkage D3 must consult before inventing an anchor
- HYPOTHESIS: `marketplace/bundles/*/skills/ext-triage-*/` — the 7 triage implementors, touched only if
  D0(b) finds they write severity directly rather than through `manage-findings` (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- ⭐⭐ **`PLAN-TRUTH-123` DEPENDS ON THIS PLAN and must not be emitted before it lands.** `-123` is the
  instrument plus the historical analysis and consumes this vocabulary; running them concurrently would
  have `-123` scoring against a schema still being designed. **This is a hard ordering, not a preference.**
- ⛔ **Live cross-epic block:** `review-apparatus/PLAN-PR-044`
  (`misconfigured-reviewer-name-reads-missing-review`, live) shares `github_pr.py` and
  `manage-findings/standards/jsonl-format.md`. **Re-derive from `corpus cross-check` at emit time** — this
  is a snapshot, and the block was observed to deepen from one file to two within a single session.
- ⚠ **`review-apparatus/PLAN-PR-030`'s D4** — *"make every gate verdict distinguish checked, degraded,
  not-reached, and never-performed"* — is a FOUR-STATE vocabulary for D1's exact question, in a sibling
  epic. ⛔⛔ **Settle ownership in D0(a) before designing D1**: adopt it, extend it, or record why a
  different set is needed. **Two vocabularies for one question is the defect this plan exists to remove,
  and shipping a second one while a sibling ships a third would be that defect committed by its own fix.**
- ⚠ Staged siblings sharing surface, to re-derive at emit: `-104` (`review_commitments.py`), `-105`,
  `-121`, and the `plan-orchestrator` cluster `-099` / `-100` / `-106` / `-110` / `-115`.
- Adjacent to: **`PLAN-TRUTH-077`** (*the writer already destroyed the distinction the reader learned to
  make*) is D2b's archetype; **`PLAN-TRUTH-085`** (shipped) owns the landing-payload surface D4a mirrors.
  ⛔ Read both before scoping; neither is re-derived here.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-124-one-ledger-vocabulary-clean-slate-so-the-same-word-means-the-same-thing-everywhere.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO
file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⛔ RE-SCOPED 2026-09-05 — cleanup re-grounding at `66320e70d` (4 claims contradicted)

⛔ **Claim bullets LEFT VERBATIM** — their ordinals address the persisted verdicts. This section
supersedes the bullets it names.

| Claim | Was | Is at HEAD |
|:-:|---|---|
| 0 | 58 constants across **24** distinct skills | 58 constants across **22** distinct skills |
| 1 | archived corpus of **30** plans, with its format counts | **39** plans; log 2731 / toon 1221 / json 644 / md 597 / jsonl 324 |
| 3 | 2570 findings, severity present 1941 (**75.5%**), absent 629 | **3286** records, present **2251 (68.5%)**, absent 1035 |
| 6 | `add_finding` call sites include `automatic-review` | **`automatic-review` only MENTIONS it in a docstring and does not call it**; the six callers are `manage-findings`, `manage-lessons`, `script-shared`, `workflow-integration-github`, `workflow-integration-gitlab`, `workflow-integration-sonar` |

⭐⭐ **Claim 6 is the one that matters, and it is not a count drift.** A call-site list that names a
non-caller and omits a real one (`script-shared`) would send D-work to the wrong module. ⇒ **D0 must
DERIVE the caller set, never inherit this list.**

⛔⛔ **Claims 0, 1 and 3 are frozen restatements and must be converted to pointers, not corrected
numbers** — this spec is *about* one vocabulary meaning one thing, and a spec that restates a drifting
census commits the defect it exists to fix. Every population figure in this spec is re-derived at
outline or it is not used.

## ⛔⛔ SPLIT-GUARD NOTICE 2026-09-05 — OVER THE GUARD AT 13 DELIVERABLES. OUTLINE MUST PRESUME A SPLIT IS REQUIRED.

**Measured at cleanup: 13 deliverables, 400 lines.** The operator-raised split guard for this epic is
**12**, so this spec is over it by 1.

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

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-146-the-findings-ledger-one-vocabulary-and-an-experiment-told-from-a-regression.md` (PLAN-TRUTH-146)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.

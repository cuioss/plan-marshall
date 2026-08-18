# Gaps — 410-the-pipeline-talks-to-itself-and-learns-from-the-echo

**Source:** verification.md (same directory)   **Open items:** 3

All four deliverables are implemented, correct, and pinned by non-vacuous tests (both gates were
mutation-checked and go red when reverted). The three items below are completeness and
statement-accuracy defects, not behaviour defects in the shipped gates.

## G1 — Make § (e) of the routing contract state one authorship rule, not two

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/disposition-to-hint-routing.md:126-127` — § "(e) Authorship admissibility", closing paragraph
- **What is wrong:** § (e) opens by requiring that a `pr-comment` carry "a `bot_kind` that is a
  **recognized reviewer identity**, validated against the registry-derived set", and closes by
  instructing "the per-plan emitter [to exclude] `pr-comment` findings **without a `bot_kind`** when
  it aggregates dispositions" — a presence-only test. Presence-only is exactly the weaker rule the
  PR's CR-1 review finding closed on the auditor side by adding `_recognized_bot_kinds()` and
  `bot_kind.strip() in recognized_bot_kinds` (`audit.py:2277-2280`). The CR-1 fix updated § (e)'s
  opening but not its closing paragraph. The consuming doc,
  `finalize-step-preference-emitter.md:131`, states the *stronger* rule, so the shared contract now
  contradicts both itself and its own consumer. `report-01.md` § Findings claims the second
  verification pass confirmed "all four docs … mutually consistent"; they are not.
- **Why it matters:** the per-plan emitter is an LLM-executed prose contract — this paragraph *is*
  its implementation. An emitter following § (e)'s closing sentence admits an archived record whose
  `bot_kind` is a legacy, de-registered, or hand-edited value (CR-1's `sonarcloud` example), letting
  a non-reviewer identity seed a durable architecture hint. The auditor is protected; the emitter,
  as documented, is not.
- **Fix:** rewrite the closing sentence of § (e) to match the section's own opening — e.g. "…the
  per-plan emitter by excluding `pr-comment` findings that do not carry a **recognized** reviewer
  `bot_kind` (validated against the registry-derived set; see the paragraph above)". Change nothing
  else in the section.
- **Done when:** `grep -n "without a \`bot_kind\`" disposition-to-hint-routing.md` returns nothing,
  and every authorship statement in § (e), in `finalize-step-preference-emitter.md` Step 1, and in
  `checks/preference-pattern-detector.md` § "Authorship admissibility" uses the same
  "recognized reviewer `bot_kind`" wording.
- **Module/topic:** `plan-marshall:phase-6-finalize` — the disposition-to-hint routing contract.

## G2 — Assess the existing `default`-bucket hints against the D2 attribution gate, or record why they are grandfathered

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `.plan/project-architecture/default/enriched.json` — `insights[]`; decision published in
  `doc/plans/truthful-signals/410-…/report-01.md` § D0 ("**Decision this gates: filter alone, no
  corpus repair.**")
- **What is wrong:** D0 surveyed the corpus for **one** of the two artifact classes this plan
  forbids — hints minted from *self-authored* comments (the D1 question) — and correctly found none.
  It never surveyed for the other class the same plan shipped a gate against: hints promoted into the
  **unattributed `default` bucket**, which § (d) now declares non-promotable. Re-derived at HEAD,
  `default/enriched.json` holds 14 insights, of which at least **nine** (array indices 2, 3, 4, 7, 9,
  10, 12, 13, 14) are `default`-bucket disposition-recurrence generalizations — "Self-review (q-gate)
  findings … consistently folded into the work (taken_into_account)", "Review-bot meta comments …
  routinely dispositioned as accepted-without-action", "across 9 dispositions on one PR …". Whether
  the emitter minted them or a human wrote them is unrecoverable (the store keeps no provenance —
  the report's own finding), but their bucket and shape are exactly what D2 exists to stop, and no
  assessment of them appears anywhere in the report. The published conclusion reads as covering the
  whole plan while it covered half of it.
- **Why it matters:** these hints are live. `enriched.json` `insights[]` surfaces through
  `get-module-context` into the phase-3-outline `## Architecture Hints` section, so nine
  unattributed, widest-blast-radius preference statements keep biasing every future plan's outline —
  the precise harm § (d) was written to prevent — while the run report tells a reader no repair is
  owed. The residue entry likewise scopes itself to the self-authored question only.
- **Fix:** run a one-off review of `.plan/project-architecture/default/enriched.json` `insights[]`
  (and `best_practices[]`) against `disposition-to-hint-routing.md` § (d): for each entry that
  generalizes a `(finding-class, disposition)` recurrence with no concrete module attribution, either
  retire it via `architecture` (a machine-local operation — this is git-tracked but `.plan/`, so it
  cannot be done from the cloud lane), or record an explicit grandfather note in the residue stating
  that pre-gate hints are retained deliberately and why. Update the D0 residue bullet in
  `report-01.md` so the corpus-repair decision names both gates rather than only D1.
- **Done when:** every `default`-bucket disposition-recurrence hint in the store has been either
  retired or explicitly grandfathered with a stated reason, and the residue names the D2 population
  it examined alongside the D1 one.
- **Module/topic:** `plan-marshall:phase-6-finalize` / the `.plan/project-architecture` hint store.

## G3 — Teach the suspect-zero census that a preference zero can be gate-produced

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:5531` `_classify_zero`
  (and `suspect_zero_census` at `:5576`), against `cross_preference_pattern`'s
  `unattributed_excluded_count`
- **What is wrong:** after D2, `preference-pattern-detector` can emit `genuine_signal_count: 0` with
  a non-empty `plans_in_corpus` **because the attribution gate declined every threshold-clearing
  tuple** — `unattributed_excluded_count` records exactly that. `_classify_zero` reads only the
  unmeasured-status marker, the genuine count, and the examined population, so it classifies that
  zero as `disciplinary`, whose published reading is "a non-empty examined population and nothing
  genuine — a real but provisional statement about the corpus". That reading is false in this case:
  the corpus *did* contain a qualifying recurrence; a gate declined it. Note this is an interaction
  with a **later** plan — `suspect_zero_census` did not exist in `audit.py` at `d3462f95` (verified),
  so it is not an omission of this plan.
- **Why it matters:** this is the epic's own namesake defect one layer up — a zero that reads as
  evidence about the corpus when it is evidence about a filter. It is low severity only because
  `unattributed_excluded_count` is published in the same block, so the information is recoverable by
  a careful reader.
- **Fix:** either (a) have `emit_preference_pattern_block` / `_classify_zero` treat
  `unattributed_excluded_count > 0` with `genuine_signal_count == 0` as its own zero class ("gated" —
  the check fired and declined), or (b) if the census is deliberately kept generic, add a sentence to
  `checks/preference-pattern-detector.md` § "Emitted columns" stating that a `disciplinary` census
  row for this check must be read together with `unattributed_excluded_count`.
- **Done when:** a sweep in which every threshold-clearing preference tuple is dropped by the
  attribution gate no longer reports the corpus as "examined and nothing genuine" without qualifying
  it, and a test pins that behaviour.
- **Module/topic:** `audit-archived-plan-retrospectives` — `preference-pattern-detector` /
  `suspect-zero-census`.

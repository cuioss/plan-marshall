# Gaps — 410-the-pipeline-talks-to-itself-and-learns-from-the-echo

**Source:** verification.md (same directory)   **Open items:** 4

All four deliverables are implemented, correct, and pinned by non-vacuous tests (both gates were
mutation-checked and go red when reverted — independently reproduced during adversarial review). The
four items below are completeness and statement-accuracy defects; the only one that reaches shipped
behaviour is G3, and it lands on a later plan's surface, not on this plan's gates.

## G1 — Make § (e) of the routing contract state one authorship rule, not two

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/disposition-to-hint-routing.md:126-127` — § "(e) Authorship admissibility", closing paragraph
- **What is wrong:** § (e) opens by requiring that a `pr-comment` carry "a `bot_kind` that is a
  **recognized reviewer identity**, validated against the registry-derived set", and closes by
  instructing "the per-plan emitter [to exclude] `pr-comment` findings **without a `bot_kind`** when
  it aggregates dispositions" — a presence-only test. Presence-only is exactly the weaker rule the
  PR's CR-1 review finding closed on the auditor side by adding `_recognized_bot_kinds()`
  (`audit.py:2237`) and `bot_kind.strip() in recognized_bot_kinds` (`audit.py:2309`). The CR-1 fix
  updated § (e)'s opening but not its closing paragraph. The consuming doc,
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
- **Done when:** `grep -n 'without a .bot_kind.' marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/disposition-to-hint-routing.md`
  exits 1 (no match), and every authorship statement in § (e), in
  `finalize-step-preference-emitter.md` Step 1 (line 131 today), and in
  `checks/preference-pattern-detector.md` § "Attribution and authorship gates" (line 37 today) uses
  the same "recognized reviewer `bot_kind`" wording.
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
  **unattributed `default` bucket**, which § (d) now declares non-promotable. Re-derived at HEAD by
  loading the JSON and enumerating the array, `default/enriched.json` holds 14 insights (and 2
  `best_practices[]`, 5 `tips[]`; 34 entries corpus-wide across the 11 tracked files), of which
  **nine** — **zero-based `insights[]` indices 1, 2, 3, 6, 8, 9, 11, 12, 13** — are `default`-bucket
  disposition-recurrence generalizations — "Self-review (q-gate)
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
  (and `best_practices[]`) against `disposition-to-hint-routing.md` § (d), selecting **only** entries
  that generalize a `(finding-class, disposition)` recurrence with no concrete module attribution.
  ⛔ Do **not** sweep the whole `default` bucket: the same store's `default/` is also the declared
  home for cross-cutting *lessons-capture* facts (`phase-6-finalize/workflow/lessons-capture.md:142`,
  read by `phase-3-outline/standards/outline-workflow-detail.md:707`), and those entries — e.g.
  `insights[]` 0, 4, 5, 7 and every `tips[]` entry — are legitimately routed there; see G4.
  For each selected entry, either **(a)** delete it from the `insights[]` array in
  `.plan/project-architecture/default/enriched.json` (the file is git-tracked, so this is an ordinary
  tracked-file edit on a developer machine; note there is **no** removal verb — `architecture enrich`
  is append-only, `manage-architecture/scripts/_cmd_enrich.py:_append_to_list`, so a scripted
  retirement would first require adding one), or **(b)** append a `## Grandfathered pre-gate hints`
  subsection to `report-01.md` § Residue naming each retained entry by its `insights[]` index and the
  reason it is retained. Either way, edit the D0 residue bullet in `report-01.md:137` so the
  corpus-repair decision names both gates rather than only D1.
- **Done when:** every disposition-recurrence hint in `default/enriched.json` is either absent from
  the file or listed by index in a grandfather note with a stated reason, and `report-01.md`'s D0
  residue bullet names the D2 population it examined alongside the D1 one.
- **Module/topic:** `plan-marshall:phase-6-finalize` / the `.plan/project-architecture` hint store.

## G3 — Teach the suspect-zero census that a preference zero can be gate-produced

- **Kind:** false-signal
- **Severity:** medium *(raised from `low` during adversarial review — the mitigation the original
  severity rested on does not hold; see "Why it matters")*
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:5531` `_classify_zero`
  (returning `_ZERO_DISCIPLINARY` at `:5573`), `suspect_zero_census` at `:5576`, the published
  reading at `_ZERO_READINGS[_ZERO_DISCIPLINARY]` `:5640-5641` and the `census_note` at `:5667-5669`
  — against `cross_preference_pattern`'s `unattributed_excluded_count` (`:2392`)
- **What is wrong:** after D2, `preference-pattern-detector` can emit `genuine_signal_count: 0` with
  a non-empty `plans_in_corpus` **because the attribution gate declined every threshold-clearing
  tuple** — `unattributed_excluded_count` records exactly that. `_classify_zero` reads only the
  unmeasured-status marker, the genuine count, and the examined population, so it classifies that
  zero as `disciplinary`, whose published reading is "a non-empty examined population and nothing
  genuine — a real but provisional statement about the corpus". That reading is false in this case:
  the corpus *did* contain a qualifying recurrence; a gate declined it. **Confirmed by execution, not
  by reading:** feeding `emit_preference_pattern_block({'threshold': 3, 'candidate_count': 0,
  'unattributed_excluded_count': 2, 'plans_in_corpus': 17, 'rows': []})` into `_classify_zero(block,
  0, 17)` returns `disciplinary`. Note this is an interaction with a **later** plan —
  `suspect_zero_census` did not exist in `audit.py` at `d3462f95` (re-verified:
  `git show d3462f95:… | grep -c 'def suspect_zero_census\|def _classify_zero'` → 0), so it is not an
  omission of this plan.
- **Why it matters:** this is the epic's own namesake defect one layer up — a zero that reads as
  evidence about the corpus when it is evidence about a filter, i.e. a **shipped false signal**. The
  original `low` rating rested on "`unattributed_excluded_count` is published in the same block"; it
  is not. `emit_suspect_zero_census_block` (`audit.py:5645`) emits a **separate** `check:
  suspect-zero-census` block whose per-check rows carry only
  `{check, genuine_signal_count, zero_class, quiet_run_count, suspect, reading}` — no
  `unattributed_excluded_count` — and whose `census_note` states outright that "a disciplinary zero
  is evidence the corpus was clean". A reader of the census therefore has to cross-read a different
  block to discover that the corpus was not clean and a gate fired. That is recoverable, not
  self-evident, which is why this stays at `medium` rather than rising to `high`: the census is
  reporting-only (it "proposes nothing and blocks nothing") and the misreport is conditional on every
  threshold-clearing tuple being declined.
- **Fix:** in `audit.py`, add a `_ZERO_GATED = "gated"` class beside the existing `_ZERO_*` constants
  (`:5469-5473`), give it an entry in `_ZERO_READINGS` (`:5631`) reading roughly "the check examined a
  non-empty population and a declared gate declined every qualifying row — this zero is evidence
  about the gate, not about the corpus", and have `_classify_zero` return it when the block matches a
  new `_GATED_EXCLUSION_RE` for a non-zero `unattributed_excluded_count:` line and
  `genuine_count == 0`, ordered after the `structural` / `no_count` / `starved` branches and before
  the `disciplinary` fallthrough. Count it in `emit_suspect_zero_census_block`'s class tally
  (`:5652-5668`) alongside the other classes. If instead the census is deliberately kept generic,
  the fallback is to add a sentence to `checks/preference-pattern-detector.md` § "Emitted columns"
  stating that a `disciplinary` census row for this check must be read together with
  `unattributed_excluded_count` from the detector's own block.
- **Done when:** `_classify_zero` applied to an `emit_preference_pattern_block` output carrying
  `plans_in_corpus > 0`, `unattributed_excluded_count > 0` and `genuine_signal_count: 0` returns a
  class other than `disciplinary`, a test in
  `test/plan-marshall/audit-archived-plan-retrospectives/` asserts exactly that, and the existing
  tests for `disciplinary` / `starved` / `structural` still pass unchanged.
- **Module/topic:** `audit-archived-plan-retrospectives` — `preference-pattern-detector` /
  `suspect-zero-census`.

## G4 — Scope § (d)'s "`default` never means cross-cutting" claim to preference recurrences

- **Kind:** stale-statement
- **Severity:** low
- **Found by:** adversarial review (not in the original gap set)
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/disposition-to-hint-routing.md:81-87`
  — § "(d) Attribution gate", opening paragraph; restated in
  `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:2214-2218` (the
  `_UNATTRIBUTED_MODULE` comment) and in
  `.claude/skills/audit-archived-plan-retrospectives/checks/preference-pattern-detector.md:42-43`
- **What is wrong:** § (d) states, unqualified and as a property of the bucket itself, that "`default`
  only ever means *unattributed*, never *cross-cutting*", and the `audit.py` comment says § (d)
  "retires the former `--module default` cross-cutting routing target". Both sentences are true of the
  **disposition→hint routing path** — the pre-fix § (b) really did have a "Cross-cutting pattern →
  `enrich insight --module default`" branch, and this plan really did delete it (`git show d3462f95 --
  …/disposition-to-hint-routing.md`). Neither sentence is true of the `default` bucket, which is a
  shared store with a second, still-live producer: `phase-6-finalize/workflow/lessons-capture.md:142`
  instructs "use `default` when the fact is cross-cutting … The `default` module is the first-class
  home for cross-cutting project knowledge", `phase-6-finalize/standards/lessons-integration.md:94`
  routes to it, and `phase-3-outline/standards/outline-workflow-detail.md:707` reads it back as "the
  home for cross-cutting (non-module-specific) project facts". Two documents in the *same skill
  directory* therefore make opposite normative claims about the same `enriched.json` bucket.
- **Why it matters:** the two claims are load-bearing in opposite directions for G2's remediation. An
  implementer who reads § (d) literally — the bucket means nothing but "unattributed" — would retire
  the whole `default/` bucket, destroying the cross-cutting lessons-capture facts that a sibling
  contract in the same skill told a previous run to put there (`insights[]` 0, 4, 5, 7 and the five
  `tips[]` entries are of that kind). The reverse misreading leaves a lessons-capture author believing
  the `default` route was retired when it was not. No behaviour is currently wrong — this is a
  precision defect in shipped prose, which is why it is `low` rather than `medium`.
- **Fix:** in `disposition-to-hint-routing.md` § (d), replace "so `default` only ever means
  *unattributed*, never *cross-cutting*" with a scoped form — e.g. "so, **for a disposition
  recurrence**, `default` only ever means *unattributed*, never *cross-cutting*" — and append one
  sentence: "This says nothing about the `default` bucket's other producer: a lessons-capture fact
  judged cross-cutting by an author is still routed there (see
  [`../workflow/lessons-capture.md`](../workflow/lessons-capture.md) § 'Classify each candidate
  signal'); § (d) retires only the *disposition→hint* routing path to `default`." Apply the same
  scoping to the `_UNATTRIBUTED_MODULE` comment in `audit.py:2214-2218` ("retires the former
  `--module default` **disposition→hint** routing target") and to
  `checks/preference-pattern-detector.md:42-43`.
- **Done when:** `disposition-to-hint-routing.md` § (d) contains a cross-reference to
  `workflow/lessons-capture.md`, no sentence in § (d) or in `audit.py`'s `_UNATTRIBUTED_MODULE`
  comment asserts an unscoped property of the `default` bucket, and
  `phase-6-finalize/workflow/lessons-capture.md:142` is unchanged (the lessons-capture route is
  confirmed retained, not silently retired).
- **Module/topic:** `plan-marshall:phase-6-finalize` — the disposition-to-hint routing contract vs.
  the lessons-capture routing rule.

## Refuted during adversarial review

**No gap was refuted in whole.** G1, G2 and G3 were each re-verified against the tree at HEAD and all
three survive; G4 was added. The following *clauses inside* those gaps were refuted and have been
corrected above rather than deleted — the next reader should know they were wrong, because each was
asserted without being executed:

| Refuted clause | Where it appeared | Evidence that refutes it |
|---|---|---|
| "array indices 2, 3, 4, 7, 9, 10, 12, 13, **14**" | G2 § What is wrong | `default/enriched.json` has 14 `insights[]` entries, so a zero-based index 14 does not exist. The nine entries meant are 1-based positions; re-derived by loading the JSON and printing the array, the zero-based indices are 1, 2, 3, 6, 8, 9, 11, 12, 13. Corrected in place. |
| "retire it via `architecture`" | G2 § Fix | `manage-architecture` exposes no removal verb. `_cmd_enrich.py` implements `enrich tip` / `enrich insight` / `enrich best-practice` as `_append_to_list` (`:526-551`), and `manage-api.md` § "Write Commands (Enrichment)" lists no delete/retire/prune subcommand. The Fix named a mechanism that does not exist; replaced with the two paths that do. |
| G2's Fix implying the whole `default` bucket is remediable | G2 § Fix | `phase-6-finalize/workflow/lessons-capture.md:142` designates `default` as the first-class home for cross-cutting lessons-capture facts, and `outline-workflow-detail.md:707` reads it back as such. Several `default/` entries are legitimately routed there. Fix now scopes the sweep to disposition-recurrence entries only; the underlying contradiction is filed as G4. |
| "It is low severity only because `unattributed_excluded_count` is published **in the same block**" | G3 § Why it matters | It is not. `emit_suspect_zero_census_block` (`audit.py:5645`) emits a separate `check: suspect-zero-census` block whose rows carry `{check, genuine_signal_count, zero_class, quiet_run_count, suspect, reading}` only. Severity raised to `medium`; the corrected mitigation (cross-block recoverability + reporting-only census) is what now holds it below `high`. |
| G3 § Fix / § Done when ("either (a) … or (b) …", "no longer reports … without qualifying it") | G3 | Neither named a file-and-symbol change nor an observable condition. Both rewritten against concrete symbols (`_ZERO_*`, `_ZERO_READINGS`, `_classify_zero`, `emit_suspect_zero_census_block`) and a runnable assertion. |

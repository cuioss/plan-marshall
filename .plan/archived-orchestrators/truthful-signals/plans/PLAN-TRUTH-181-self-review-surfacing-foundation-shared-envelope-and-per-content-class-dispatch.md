# PLAN-TRUTH-181: Self-review surfacing foundation — a shared envelope and per-content-class dispatch

epic: truthful-signals
workstream: WS-01

> Operator-requested 2026-09-26 (after the PM-MCP sweep): consumer domains have no self-review surfacer at all.
> This plan is the prerequisite of the four domain surfacers `PLAN-TRUTH-182` (Java), `-183` (Python),
> `-184` (JavaScript), `-185` (Documents). Its invariants also belong in PM-MCP's domain-extensions
> Self-Review Surfacer Contract (now `plan-marshall-mcp/doc/implementation-watch/domain-extensions.adoc`).
>
> ⛔ **RE-ASSEMBLED 2026-09-28 — absorbs `PLAN-TRUTH-167` (row → `superseded`).** 167 D1 (applicability) is the
> same mechanism as this plan's declared-coverage + `not_covered` routing, so building it twice would be rework;
> 167 D0/D2/D4 are folded in as D0 / D2 / D5 below; 167 D3 is REFUTED by #1559 (upstream anchor) and dropped.
> This plan therefore carries 167's **operator-confirmed delivery-breaking exception**: self-review on a consumer
> diff loops to `max_iterations` and blocks push (API-Sheriff 19/20 files `other`; Token-Sheriff PR #744, 4/4,
> ~28 min). Deliverables are ordered so that fix (D1–D3) lands before the envelope extraction (D4).

## Objective

Make the `ext-point-self-review-surfacing` extension point able to host MORE THAN ONE domain implementor. Today the
dispatcher runs the first implementor that resolves, and the whole envelope machinery (candidate registry, footprint
derivation, diff parsing, `scope_statement` / `structural_limit` / `delta_coverage` composition) is private to
`ext-self-review-plan-marshall`. Extract the domain-agnostic envelope into a shared module every implementor reuses,
let each implementor declare the content classes it covers, and have the dispatcher run every APPLICABLE implementor
and merge their envelopes — so a mixed Java + AsciiDoc diff is reviewed by both, and plan-marshall's own diffs keep
today's behaviour bit-for-bit.

## Deliverables

Eight deliverables (split guard: 12). D1–D3 are the delivery-breaking fix and land first.

0. **Gate — re-ground against HEAD** (was 167 D0 + this plan's gate). Confirm the single-implementor selection and
   the private registries; derive the applicability signal; enumerate every verifier-refusal reason that is
   invariant across rounds at an unchanged HEAD (surfacer domain, content class, zero detectors) and publish it.
1. **Declared coverage per implementor → applicability** (absorbs 167 D1). Each implementor declares the content
   classes it covers (e.g. `java_source`, `python_source`, `js_source`, `asciidoc`, `markdown`). Applicability = the
   declared classes intersect the footprint's classes; the classification of footprint paths into content classes
   is shared, so every implementor sees one partition. A resolvable but inapplicable implementor is NOT run.
2. **A round-invariant refusal is terminal, not a `loop_back`** (was 167 D2). When the verifier's
   `further_round_owed` / `verdict_refused` rationale names a D0 round-invariant property, the step records the gap
   and closes once (or escalates once) instead of consuming the iteration budget — the branch two operator overrides
   improvised on API-Sheriff and Token-Sheriff PR #744.
3. **Multi-implementor dispatch and merge.** `pre-submission-self-review` Step 1 runs EVERY applicable implementor,
   each over its own class slice, and merges the envelopes: candidate lists concatenate, counts sum, and
   `delta_coverage.by_class` rows come from the implementor that owns each class. A footprint class no implementor
   covers is reported as `not_covered` with its file count, non-blocking, never folded into a clean zero; the
   no-implementor fallback verdict stays as it is.
4. **Shared surfacing envelope.** Move the domain-agnostic parts — the `CANDIDATE_LISTS` registry and its
   `in_total` / `family` fields, footprint / `--since-ref` scoping, diff and hunk parsing, and the composition of
   `counts`, `counts.by_family`, `scope_statement`, `structural_limit`, `delta_coverage` — into a shared module an
   implementor in ANY bundle can import. `ext-self-review-plan-marshall` becomes its first consumer, with output
   unchanged byte-for-byte on its existing test corpus.
5. **`not_covered` is a machine-readable landing fact** (was 167 D4), so a consuming epic can tell "no surfacer
   applied" from "reviewed clean" without reading `may_close=no` from a step fact.
6. **Implementor authoring guide.** Update the extension-point standard: the shared module, the class declaration,
   the merge rules, the "Implementations" header count derived rather than hand-kept, and a checklist for a new
   domain (registry keys emitted empty where the language has no equivalent signal).
7. **Controls.** A plan-marshall-only diff gives today's envelope byte-for-byte. A diff with no applicable
   implementor gives `not_covered`, not clean, and closes in ONE round. A round-invariant refusal closes once and
   never reaches `max_iterations`. A two-implementor diff merges and both classes appear in `delta_coverage`. Two
   implementors claiming one class is a registration error, not a silent first-wins. Fixtures: the API-Sheriff
   (19/20 `other`) and Token-Sheriff PR #744 (4/4 `other`, zero detectors) diff shapes.

## Claim Labels

- OBSERVED: the dispatcher selects exactly one implementor — "Select the first implementor whose notation **resolves
  in the current executor**" — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` line 119.
  - verdict: corroborated | checked_at: 14d624bd93a751204eb38a5d849cd32f4ea28493 | by: truthful-signals/cleanup | rescoped: n/a | evidence: pre-submission-self-review.md:119 still selects the first resolvable implementor (exactly one).
- OBSERVED: the candidate registry and the content-class registry are private to the plan-marshall implementor —
  `CANDIDATE_LISTS` at `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py:488`,
  `CONTENT_CLASSES` at `…/_self_review_detectors.py:2463`.
  - verdict: corroborated | checked_at: 14d624bd93a751204eb38a5d849cd32f4ea28493 | by: truthful-signals/cleanup | rescoped: n/a | evidence: CANDIDATE_LISTS at _self_review_patterns.py:488; CONTENT_CLASSES six classes at _self_review_detectors.py:2463-2469.
- OBSERVED: exactly one implementor exists — a directory sweep of `marketplace/bundles/*/skills/` for
  `ext-self-review-*` finds only `ext-self-review-plan-marshall` (2026-09-26); also recorded in archived
  `PLAN-TRUTH-126` as "a separate unowned item".
  - verdict: corroborated | checked_at: 14d624bd93a751204eb38a5d849cd32f4ea28493 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Glob finds exactly one ext-self-review-*/SKILL.md (pm-plugin-development); 182-185 staged, none shipped.
- HYPOTHESIS: the shared module belongs in `plan-marshall:script-shared` (the cross-bundle import home) — confirm at
  `marketplace/bundles/plan-marshall/skills/script-shared/scripts/` against how other cross-bundle helpers are
  imported by bundle scripts (verify-at-outline).
  - verdict: unverifiable | checked_at: 14d624bd93a751204eb38a5d849cd32f4ea28493 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Placement hypothesis; either placement works — decision, not fact.
- HYPOTHESIS: implementors are discovered by `implements:` frontmatter alone, so no per-bundle `extension.py` edit
  is needed — confirm at the `extension_discovery implementors` verb (verify-at-outline).
  - verdict: corroborated | checked_at: 14d624bd93a751204eb38a5d849cd32f4ea28493 | by: truthful-signals/cleanup | rescoped: n/a | evidence: extension_discovery.py:1124 defines _scan_skills_roots_for_implementors scanning SKILL.md implements: fields.
- Verify-first clause: settle what `PLAN-TRUTH-167` D1/D2 changed in Step 1 before touching the selection code. (167 is now absorbed here; the clause is settled below and stays as the record.)
  - verdict: corroborated | checked_at: 14d624bd93a751204eb38a5d849cd32f4ea28493 | by: truthful-signals/cleanup | rescoped: n/a | evidence: 167 D1/D2 never landed (superseded); #1599 last touch to pre-submission-self-review.md; Branch A selection unchanged.
- OBSERVED (carried from 167 claim 2, corroborated at `a88626306`): every non-closing verifier state records `loop_back` — `pre-submission-self-review.md:503-511` maps `verdict_refused`, `further_round_owed` and `verifier_unavailable` to `loop_back`, and `:520` "Every non-closing state above records loop_back" (D2).
  - verdict: corroborated | checked_at: 14d624bd93a751204eb38a5d849cd32f4ea28493 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Table :507-511 maps all three non-closing states to loop_back; :520 states every non-closing state records loop_back.
- OBSERVED (carried from 167 claim 5, contradicted at `a88626306`): 167's D3 premise ("footprint never diffs against `origin/{base}`") is REFUTED — `_references_core.py:259-263` returns `origin/{base}` when it resolves (#1559) — so no base-anchor deliverable is carried.
  - verdict: contradicted | checked_at: 14d624bd93a751204eb38a5d849cd32f4ea28493 | by: truthful-signals/cleanup | rescoped: yes | evidence: _references_core.py:259-263 still returns origin/{base} when it resolves: 167 D3 stays refuted; absorbed, no base-anchor deliverable.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — Step 1 selection and merge (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` — the contract (D4)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/` — becomes a consumer of the shared envelope (D1)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md` — declared classes (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/` — the shared envelope module (verify-at-outline)
- OBSERVED: `test/pm-plugin-development/ext-self-review-plan-marshall/` — byte-for-byte control (D5)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/` — dispatch and merge controls (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_discovery.py` — `_IMPLEMENTOR_FRONTMATTER_KEYS` (:894-902) parses no content-class key; D1's declaration and D7's one-class-two-implementors registration error need a discovery/validation site (cleanup 2026-09-26, understated)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` — the `not_covered` landing fact (D5; carried from 167)

## Dependencies and Sequencing

- Depends on: none (`PLAN-TRUTH-167` absorbed 2026-09-28).
- Overlaps with (cross-epic, cleanup 2026-09-26): `post-run-quality` `PLAN-PRQ-10` (staged) — same
  `ext-self-review-plan-marshall/scripts/` (`CONTENT_CLASSES`, `CANDIDATE_LISTS`, `self_review.py`) and
  `pre-submission-self-review.md`. Different subject (re-fire convergence / coverage honesty), NOT a duplicate —
  sequence, never pair. If PRQ-10 is parked by its own PM-MCP re-triage, the overlap lapses.
- Blocks: `PLAN-TRUTH-182`, `-183`, `-184`, `-185`.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-181-self-review-surfacing-foundation-shared-envelope-and-per-content-class-dispatch.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file
under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the orchestrator owns every other
ledger write — and reports its outcome through its PR and its inbox message. See
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

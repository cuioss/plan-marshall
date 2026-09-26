# PLAN-TRUTH-181: Self-review surfacing foundation — a shared envelope and per-content-class dispatch

epic: truthful-signals
workstream: WS-01

> Operator-requested 2026-09-26 (after the PM-MCP sweep): consumer domains have no self-review surfacer at all.
> This plan is the prerequisite of the four domain surfacers `PLAN-TRUTH-182` (Java), `-183` (Python),
> `-184` (JavaScript), `-185` (Documents). Its invariants also belong in PM-MCP's domain-extensions
> Self-Review Surfacer Contract (see `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md`, 167 / 216).

## Objective

Make the `ext-point-self-review-surfacing` extension point able to host MORE THAN ONE domain implementor. Today the
dispatcher runs the first implementor that resolves, and the whole envelope machinery (candidate registry, footprint
derivation, diff parsing, `scope_statement` / `structural_limit` / `delta_coverage` composition) is private to
`ext-self-review-plan-marshall`. Extract the domain-agnostic envelope into a shared module every implementor reuses,
let each implementor declare the content classes it covers, and have the dispatcher run every APPLICABLE implementor
and merge their envelopes — so a mixed Java + AsciiDoc diff is reviewed by both, and plan-marshall's own diffs keep
today's behaviour bit-for-bit.

## Deliverables

0. **Gate — re-ground against HEAD.** Confirm the single-implementor selection, the private registry, and what
   `PLAN-TRUTH-167` D1/D2 already changed (167 may land first). Re-scope if 167 already introduced applicability.
1. **Shared surfacing envelope.** Move the domain-agnostic parts — the `CANDIDATE_LISTS` registry and its
   `in_total` / `family` fields, footprint / `--since-ref` scoping, diff and hunk parsing, and the composition of
   `counts`, `counts.by_family`, `scope_statement`, `structural_limit`, `delta_coverage` — into a shared module an
   implementor in ANY bundle can import. `ext-self-review-plan-marshall` becomes its first consumer, with output
   unchanged byte-for-byte on its existing test corpus.
2. **Declared coverage per implementor.** Each implementor declares the content classes it covers (e.g.
   `java_source`, `python_source`, `js_source`, `asciidoc`, `markdown`). Applicability = the declared classes
   intersect the footprint's classes; the classification of footprint paths into content classes is shared, so every
   implementor sees one partition.
3. **Multi-implementor dispatch and merge.** `pre-submission-self-review` Step 1 runs EVERY applicable implementor,
   each over its own class slice, and merges the envelopes: candidate lists concatenate, counts sum, and
   `delta_coverage.by_class` rows come from the implementor that owns each class. A footprint class no implementor
   covers is reported as `not_covered` with its file count, never folded into a clean zero; the no-implementor
   fallback verdict stays as it is.
4. **Implementor authoring guide.** Update the extension-point standard: the shared module, the class declaration,
   the merge rules, the "Implementations" header count derived rather than hand-kept, and a checklist for a new
   domain (registry keys emitted empty where the language has no equivalent signal).
5. **Controls.** A plan-marshall-only diff gives today's envelope byte-for-byte. A diff with no applicable implementor
   gives `not_covered`, not clean. A two-implementor diff merges and both classes appear in `delta_coverage`. Two
   implementors claiming one class is a registration error, not a silent first-wins.

## Claim Labels

- OBSERVED: the dispatcher selects exactly one implementor — "Select the first implementor whose notation **resolves
  in the current executor**" — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` line 119.
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: pre-submission-self-review.md:119 selects exactly one implementor (first resolvable).
- OBSERVED: the candidate registry and the content-class registry are private to the plan-marshall implementor —
  `CANDIDATE_LISTS` at `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py:488`,
  `CONTENT_CLASSES` at `…/_self_review_detectors.py:2463`.
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: CANDIDATE_LISTS _self_review_patterns.py:488; CONTENT_CLASSES _self_review_detectors.py:2463-2470 (python, skill_doc, standards_doc, markdown_other, structured_config, other) — private; .java/.adoc fall into other.
- OBSERVED: exactly one implementor exists — a directory sweep of `marketplace/bundles/*/skills/` for
  `ext-self-review-*` finds only `ext-self-review-plan-marshall` (2026-09-26); also recorded in archived
  `PLAN-TRUTH-126` as "a separate unowned item".
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Only pm-plugin-development/skills/ext-self-review-plan-marshall exists; implements: sweep finds one implementor.
- HYPOTHESIS: the shared module belongs in `plan-marshall:script-shared` (the cross-bundle import home) — confirm at
  `marketplace/bundles/plan-marshall/skills/script-shared/scripts/` against how other cross-bundle helpers are
  imported by bundle scripts (verify-at-outline).
  - verdict: unverifiable | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Placement decision; executor PYTHONPATH already allows cross-bundle script imports (self_review.py:42 imports manage-references _references_core), so script-shared is one option, not a requirement.
- HYPOTHESIS: implementors are discovered by `implements:` frontmatter alone, so no per-bundle `extension.py` edit
  is needed — confirm at the `extension_discovery implementors` verb (verify-at-outline).
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: extension_discovery.py:1124-1204 _scan_skills_roots_for_implementors reads SKILL.md implements: via read_implements_field (:229-297); no extension.py involved.
- Verify-first clause: settle what `PLAN-TRUTH-167` D1/D2 changed in Step 1 before touching the selection code.
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Step 1 selection unchanged at :119; PLAN-TRUTH-167 D1/D2 not landed; only post-#1559 edit (#1599) touched Branch A; no applicability mechanism exists.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — Step 1 selection and merge (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` — the contract (D4)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/` — becomes a consumer of the shared envelope (D1)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md` — declared classes (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/` — the shared envelope module (verify-at-outline)
- OBSERVED: `test/pm-plugin-development/ext-self-review-plan-marshall/` — byte-for-byte control (D5)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/` — dispatch and merge controls (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_discovery.py` — `_IMPLEMENTOR_FRONTMATTER_KEYS` (:894-902) parses no content-class key; D2's declaration and D5's one-class-two-implementors registration error need a discovery/validation site (cleanup 2026-09-26, understated)

## Dependencies and Sequencing

- Depends on: `PLAN-TRUTH-167` (D1/D2 — applicability and the terminal refusal; same Step 1 surface).
- Overlaps with: `PLAN-TRUTH-167` on `pre-submission-self-review.md` and `ext-self-review-plan-marshall/scripts/`; sequence after it.
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

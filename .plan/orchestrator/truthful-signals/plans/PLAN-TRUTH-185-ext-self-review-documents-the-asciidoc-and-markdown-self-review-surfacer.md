# PLAN-TRUTH-185: `ext-self-review-documents` — the Documents domain self-review surfacer

epic: truthful-signals
workstream: WS-01

> Operator-requested 2026-09-26 (after the PM-MCP sweep). One of four domain surfacers (`PLAN-TRUTH-182` Java,
> `-183` Python, `-184` JavaScript, `-185` Documents) built on the `PLAN-TRUTH-181` foundation. The detector rule set
> this plan settles is implementation-independent domain knowledge: record it for PM-MCP's domain-extensions
> Self-Review Surfacer Contract as well (the operator carries it to
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md`).

## Objective

Ship `ext-self-review-documents` in `pm-documents`: an implementor of `ext-point-self-review-surfacing` that covers
`asciidoc` (`*.adoc`) and consumer-project `markdown` (`*.md`) outside the marketplace skill tree. Why: documentation diffs in consumer projects surface nothing — the recorded fixture is +76 lines of `doc/user/configuration.adoc` surfacing 0 candidates (216.D2). Today such a diff gets the no-implementor fallback (or, before `PLAN-TRUTH-167`, a loop to the
iteration ceiling); after this plan it gets a real candidate envelope that the domain-agnostic cognitive review
consumes unchanged.

## Deliverables

0. **Gate — re-ground against HEAD.** Confirm `PLAN-TRUTH-181` has landed (shared envelope, class declaration,
   multi-implementor merge) and read its implementor authoring guide; re-scope if its mechanism differs from this spec.
1. **The implementor skill.** `marketplace/bundles/pm-documents/skills/ext-self-review-documents/` with `SKILL.md`
   (`implements: plan-marshall:extension-api/standards/ext-point-self-review-surfacing`, declared content classes,
   Detection Rules section) and a `self_review` script exposing `surface` on the shared envelope; registered in the
   bundle's `plugin.json`.
2. **Documents detectors**, each emitting into an existing registry key (no new keys without registering them in the
   shared registry first):
   - `markdown_sections` — duplicated sections across changed documents (AsciiDoc and Markdown headings).
   - `same_document_consistency` — added RFC-2119 normative sentences, for sibling-contradiction review.
   - `count_prose` — cardinality claims ("three steps", "5 modes") in changed documents.
   - `ordinal_references` — `step N` / `item N` references into an ordered list the same diff touched.
   - `touched_claims` — one-token `-`/`+` line pairs, for whole-sentence re-verification.
   - `description_vs_body` — document front matter / header attributes vs the changed body.
   - `contract_sources` — `include::` targets and `xref:` anchors that a changed document depends on (dangling target = candidate).
   - `keep_markers` / `protected_identifiers` — honoured exactly as in the plan-marshall implementor.
   Every other registry key is emitted empty.
3. **Honest limits.** `structural_limit` names what Documents static surfacing cannot see; `delta_coverage` reports
   every declared class, seeded to zero; a file type of this domain with no detector is `not_covered`, never clean.
4. **Tests from real shapes.** Per detector: a positive and a matched negative control. End-to-end: the `doc/user/configuration.adoc` +76-line shape surfaces a non-empty envelope; a `.md` under `marketplace/bundles/**` in the meta-project stays owned by `ext-self-review-plan-marshall`.
5. **Docs.** The extension-point standard's implementor list and the bundle README name the new implementor.

## Claim Labels

- OBSERVED: no `ext-self-review-documents` exists — directory sweep of `marketplace/bundles/*/skills/` finds only `ext-self-review-plan-marshall` (2026-09-26).
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: No ext-self-review-documents; pm-documents/skills: ext-triage-docs, manage-interface, plan-marshall-plugin, recipe-doc-verify, recipe-verify-*, ref-*.
- OBSERVED: consumer implementors are explicitly invited — "Consumer projects (Java, frontend, application code) MAY contribute their own implementor by following the contract below" — read at `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` § Overview.
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: ext-point-self-review-surfacing.md:9 consumer-implementor invitation.
- OBSERVED: every registry key MUST be emitted, empty where the language has no equivalent signal — same file § Required Candidate Sub-Lists.
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: ext-point-self-review-surfacing.md:233 every registry key MUST be emitted.
- OBSERVED: `pm-documents` already ships `ref-asciidoc`, `ref-documentation`, `recipe-doc-verify`, `ext-triage-docs` — read at `marketplace/bundles/pm-documents/skills/`.
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: pm-documents/skills ships ref-asciidoc, ref-documentation, recipe-doc-verify, ext-triage-docs.
- HYPOTHESIS: the plan-marshall implementor's prose-contract detectors (`count_prose`, `ordinal_references`, `touched_claims`, `same_document_consistency`) are format-agnostic enough to reuse for AsciiDoc once `PLAN-TRUTH-181` exports them — confirm at `…/ext-self-review-plan-marshall/scripts/_self_review_detectors.py` (verify-at-outline).
  - verdict: unverifiable | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Depends on PLAN-TRUTH-181 export; CONTENT_CLASSES has no asciidoc class (.adoc -> other); count_prose is scoped to a skill dir's SKILL.md + standards/*.md (ext-point doc :250), so not plainly format-agnostic.
- HYPOTHESIS: the implementor needs no per-bundle `extension.py` registration beyond `implements:` frontmatter + `plugin.json` — confirm at `extension_discovery implementors` (verify-at-outline; `PLAN-TRUTH-181` D0 settles the same question).
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Frontmatter-only discovery (extension_discovery.py:1124-1204); pm-documents/.claude-plugin/plugin.json exists.

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/pm-documents/skills/ext-self-review-documents/` — new skill directory (D1–D3; absent today, verified)
- OBSERVED: `marketplace/bundles/pm-documents/.claude-plugin/plugin.json` — skill registration (D1)
- HYPOTHESIS: `test/pm-documents/ext-self-review-documents/` — new test directory under the existing `test/pm-documents/` (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` — implementor list (D5)
- OBSERVED: `marketplace/bundles/pm-documents/README.md` — D5 'the bundle README names the new implementor' (cleanup 2026-09-26, understated)

## Dependencies and Sequencing

- Depends on: `PLAN-TRUTH-181` (shared envelope, class declaration, multi-implementor merge).
- Overlaps with: the other three domain plans ONLY on `ext-point-self-review-surfacing.md` (D5, one line each) — otherwise disjoint by bundle, so they can run in parallel once 181 lands; sequence the D5 line edits or let the second rebase.
- Adjacent to: `ext-triage-docs` in the same bundle (finding triage, a different extension point) — untouched.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-185-ext-self-review-documents-the-asciidoc-and-markdown-self-review-surfacer.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file
under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the orchestrator owns every other
ledger write — and reports its outcome through its PR and its inbox message. See
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

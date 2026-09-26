# PLAN-TRUTH-182: `ext-self-review-java` — the Java domain self-review surfacer

epic: truthful-signals
workstream: WS-01

> Operator-requested 2026-09-26 (after the PM-MCP sweep). One of four domain surfacers (`PLAN-TRUTH-182` Java,
> `-183` Python, `-184` JavaScript, `-185` Documents) built on the `PLAN-TRUTH-181` foundation. The detector rule set
> this plan settles is implementation-independent domain knowledge: record it for PM-MCP's domain-extensions
> Self-Review Surfacer Contract as well (the operator carries it to
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md`).

## Objective

Ship `ext-self-review-java` in `pm-dev-java`: an implementor of `ext-point-self-review-surfacing` that covers
`java_source` (`*.java`) and the Java-owned build/config files the domain governs (`pom.xml`, `*.properties`, `module-info.java`). Why: API-Sheriff (19/20 changed files classed `other`) and Token-Sheriff PR #744 (4/4 `other`, ~28 min looping to the ceiling) are Java consumer repos where self-review had nothing to run; the Java analogue list was proposed by inbox `deployment-and-refresh-gaps-018` (archived) and scoped out of archived `PLAN-TRUTH-126` as a separate unowned item. Today such a diff gets the no-implementor fallback (or, before `PLAN-TRUTH-167`, a loop to the
iteration ceiling); after this plan it gets a real candidate envelope that the domain-agnostic cognitive review
consumes unchanged.

## Deliverables

0. **Gate — re-ground against HEAD.** Confirm `PLAN-TRUTH-181` has landed (shared envelope, class declaration,
   multi-implementor merge) and read its implementor authoring guide; re-scope if its mechanism differs from this spec.
1. **The implementor skill.** `marketplace/bundles/pm-dev-java/skills/ext-self-review-java/` with `SKILL.md`
   (`implements: plan-marshall:extension-api/standards/ext-point-self-review-surfacing`, declared content classes,
   Detection Rules section) and a `self_review` script exposing `surface` on the shared envelope; registered in the
   bundle's `plugin.json`.
2. **Java detectors**, each emitting into an existing registry key (no new keys without registering them in the
   shared registry first):
   - `symmetric_pairs` — `encode`/`decode`, `serialize`/`deserialize`, `open`/`close`, `acquire`/`release` method pairs, with `test_present` from the module's `src/test/java` tree.
   - `flag_guard_pairs` — boolean config/feature flags whose guards differ in the forms they cover.
   - `contract_sources` — changed interfaces, annotations, and `record` components.
   - `schema_bearing_files` — `*.xsd`, JSON schemas, OpenAPI documents, `module-info.java`.
   - `producer_consumer` — a `LogRecord`/message constant, config key or event type produced with no consumer in the diff.
   - `user_facing_strings` — log message templates (`LogRecord`/`LogMessages`), exception messages, JavaDoc summaries.
   - `regexes` — `Pattern.compile` / `String.matches` literals.
   - `unguarded_boundaries` — added I/O, `Process`/`ProcessBuilder` or network calls outside try-with-resources or an enclosing `try`.
   - `same_document_consistency` — RFC-2119 directives added in JavaDoc.
   - `source_of_truth` — the same `static final` constant bound to divergent literals across files.
   Every other registry key is emitted empty.
3. **Honest limits.** `structural_limit` names what Java static surfacing cannot see; `delta_coverage` reports
   every declared class, seeded to zero; a file type of this domain with no detector is `not_covered`, never clean.
4. **Tests from real shapes.** Per detector: a positive and a matched negative control. End-to-end: API-Sheriff and Token-Sheriff PR #744 diffs (or synthetic equivalents) must now surface a non-empty, classified envelope instead of `not_covered`/loop-to-ceiling.
5. **Docs.** The extension-point standard's implementor list and the bundle README name the new implementor.

## Claim Labels

- OBSERVED: no `ext-self-review-java` exists — directory sweep of `marketplace/bundles/*/skills/` finds only `ext-self-review-plan-marshall` (2026-09-26).
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: No ext-self-review-java; pm-dev-java/skills holds arch-gate-java, ext-triage-java, java-*, javadoc, junit-*, manage-maven-profiles, plan-marshall-plugin.
- OBSERVED: consumer implementors are explicitly invited — "Consumer projects (Java, frontend, application code) MAY contribute their own implementor by following the contract below" — read at `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` § Overview.
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: ext-point-self-review-surfacing.md:9 verbatim consumer-implementor invitation.
- OBSERVED: every registry key MUST be emitted, empty where the language has no equivalent signal — same file § Required Candidate Sub-Lists.
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: ext-point-self-review-surfacing.md:233 every registry key MUST appear, empty payload when no equivalent signal.
- OBSERVED: `pm-dev-java` already ships domain skills this surfacer can cite as its standard (`java-core`, `java-null-safety`, `javadoc`, `ext-triage-java`) — read at `marketplace/bundles/pm-dev-java/skills/`.
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: pm-dev-java/skills contains java-core, java-null-safety, javadoc, ext-triage-java.
- HYPOTHESIS: the implementor needs no per-bundle `extension.py` registration beyond `implements:` frontmatter + `plugin.json` — confirm at `extension_discovery implementors` (verify-at-outline; `PLAN-TRUTH-181` D0 settles the same question).
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: extension_discovery.py:1124-1204 discovers from SKILL.md implements: alone; pm-dev-java/.claude-plugin/plugin.json exists.

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/pm-dev-java/skills/ext-self-review-java/` — new skill directory (D1–D3; absent today, verified)
- OBSERVED: `marketplace/bundles/pm-dev-java/.claude-plugin/plugin.json` — skill registration (D1)
- HYPOTHESIS: `test/pm-dev-java/ext-self-review-java/` — new test directory under the existing `test/pm-dev-java/` (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` — implementor list (D5)
- OBSERVED: `marketplace/bundles/pm-dev-java/README.md` — D5 'the bundle README names the new implementor' (cleanup 2026-09-26, understated)

## Dependencies and Sequencing

- Depends on: `PLAN-TRUTH-181` (shared envelope, class declaration, multi-implementor merge).
- Overlaps with: the other three domain plans ONLY on `ext-point-self-review-surfacing.md` (D5, one line each) — otherwise disjoint by bundle, so they can run in parallel once 181 lands; sequence the D5 line edits or let the second rebase.
- Adjacent to: `ext-triage-java` in the same bundle (finding triage, a different extension point) — untouched.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-182-ext-self-review-java-the-java-domain-self-review-surfacer.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file
under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the orchestrator owns every other
ledger write — and reports its outcome through its PR and its inbox message. See
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

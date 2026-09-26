# PLAN-TRUTH-184: `ext-self-review-javascript` — the JavaScript domain self-review surfacer

epic: truthful-signals
workstream: WS-01

> Operator-requested 2026-09-26 (after the PM-MCP sweep). One of four domain surfacers (`PLAN-TRUTH-182` Java,
> `-183` Python, `-184` JavaScript, `-185` Documents) built on the `PLAN-TRUTH-181` foundation. The detector rule set
> this plan settles is implementation-independent domain knowledge: record it for PM-MCP's domain-extensions
> Self-Review Surfacer Contract as well (the operator carries it to
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md`).

## Objective

Ship `ext-self-review-javascript` in `pm-dev-frontend`: an implementor of `ext-point-self-review-surfacing` that covers
`js_source` (`*.js`, `*.mjs`, `*.cjs`, `*.ts`, `*.tsx`, `*.jsx`) and frontend project files (`package.json`, `tsconfig.json`, `*.css`). Why: frontend and JavaScript consumer projects have no surfacer. Today such a diff gets the no-implementor fallback (or, before `PLAN-TRUTH-167`, a loop to the
iteration ceiling); after this plan it gets a real candidate envelope that the domain-agnostic cognitive review
consumes unchanged.

## Deliverables

0. **Gate — re-ground against HEAD.** Confirm `PLAN-TRUTH-181` has landed (shared envelope, class declaration,
   multi-implementor merge) and read its implementor authoring guide; re-scope if its mechanism differs from this spec.
1. **The implementor skill.** `marketplace/bundles/pm-dev-frontend/skills/ext-self-review-javascript/` with `SKILL.md`
   (`implements: plan-marshall:extension-api/standards/ext-point-self-review-surfacing`, declared content classes,
   Detection Rules section) and a `self_review` script exposing `surface` on the shared envelope; registered in the
   bundle's `plugin.json`.
2. **JavaScript detectors**, each emitting into an existing registry key (no new keys without registering them in the
   shared registry first):
   - `regexes` — regex literals and `new RegExp(...)`.
   - `user_facing_strings` — JSX text, template literals rendered to the user, i18n message keys, error messages.
   - `contract_sources` — exported TypeScript interfaces/types, `*.d.ts`, public component props.
   - `schema_bearing_files` — `package.json`, JSON schemas, OpenAPI clients.
   - `unguarded_boundaries` — `fetch`/`XMLHttpRequest`/`fs` calls with no `catch` and no awaiting `try`.
   - `symmetric_pairs`, `flag_guard_pairs`, `producer_consumer`, `source_of_truth` — JS/TS analogues (e.g. `addEventListener`/`removeEventListener`, `subscribe`/`unsubscribe`).
   Every other registry key is emitted empty.
3. **Honest limits.** `structural_limit` names what JavaScript static surfacing cannot see; `delta_coverage` reports
   every declared class, seeded to zero; a file type of this domain with no detector is `not_covered`, never clean.
4. **Tests from real shapes.** Per detector: a positive and a matched negative control. End-to-end: a JS/TS diff surfaces a classified envelope; a mixed JS + CSS diff reports CSS as its own class (covered or `not_covered`, never silently absorbed).
5. **Docs.** The extension-point standard's implementor list and the bundle README name the new implementor.

## Claim Labels

- OBSERVED: no `ext-self-review-javascript` exists — directory sweep of `marketplace/bundles/*/skills/` finds only `ext-self-review-plan-marshall` (2026-09-26).
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: No ext-self-review-javascript; pm-dev-frontend/skills: arch-gate-js, css, ext-triage-js, javascript, javascript-security, jest-testing, lint-config, plan-marshall-plugin.
- OBSERVED: consumer implementors are explicitly invited — "Consumer projects (Java, frontend, application code) MAY contribute their own implementor by following the contract below" — read at `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` § Overview.
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: ext-point-self-review-surfacing.md:9 consumer-implementor invitation.
- OBSERVED: every registry key MUST be emitted, empty where the language has no equivalent signal — same file § Required Candidate Sub-Lists.
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: ext-point-self-review-surfacing.md:233 every registry key MUST appear.
- OBSERVED: `pm-dev-frontend` already ships `javascript`, `css`, `jest-testing`, `lint-config`, `ext-triage-js` — read at `marketplace/bundles/pm-dev-frontend/skills/`.
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: pm-dev-frontend/skills ships javascript, css, jest-testing, lint-config, ext-triage-js.
- HYPOTHESIS: the implementor needs no per-bundle `extension.py` registration beyond `implements:` frontmatter + `plugin.json` — confirm at `extension_discovery implementors` (verify-at-outline; `PLAN-TRUTH-181` D0 settles the same question).
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Frontmatter-only discovery (extension_discovery.py:1124-1204); pm-dev-frontend/.claude-plugin/plugin.json exists.

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/pm-dev-frontend/skills/ext-self-review-javascript/` — new skill directory (D1–D3; absent today, verified)
- OBSERVED: `marketplace/bundles/pm-dev-frontend/.claude-plugin/plugin.json` — skill registration (D1)
- HYPOTHESIS: `test/pm-dev-frontend/ext-self-review-javascript/` — new test directory under the existing `test/pm-dev-frontend/` (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` — implementor list (D5)
- OBSERVED: `marketplace/bundles/pm-dev-frontend/README.md` — D5 'the bundle README names the new implementor' (cleanup 2026-09-26, understated)

## Dependencies and Sequencing

- Depends on: `PLAN-TRUTH-181` (shared envelope, class declaration, multi-implementor merge).
- Overlaps with: the other three domain plans ONLY on `ext-point-self-review-surfacing.md` (D5, one line each) — otherwise disjoint by bundle, so they can run in parallel once 181 lands; sequence the D5 line edits or let the second rebase.
- Adjacent to: `ext-triage-js` in the same bundle (finding triage, a different extension point) — untouched.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-184-ext-self-review-javascript-the-javascript-domain-self-review-surfacer.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file
under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the orchestrator owns every other
ledger write — and reports its outcome through its PR and its inbox message. See
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

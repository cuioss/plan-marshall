# PLAN-TRUTH-183: `ext-self-review-python` — the Python domain self-review surfacer

epic: truthful-signals
workstream: WS-01

> Operator-requested 2026-09-26 (after the PM-MCP sweep). One of four domain surfacers (`PLAN-TRUTH-182` Java,
> `-183` Python, `-184` JavaScript, `-185` Documents) built on the `PLAN-TRUTH-181` foundation. The detector rule set
> this plan settles is implementation-independent domain knowledge: record it for PM-MCP's domain-extensions
> Self-Review Surfacer Contract as well (the operator carries it to
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md`).

## Objective

Ship `ext-self-review-python` in `pm-dev-python`: an implementor of `ext-point-self-review-surfacing` that covers
`python_source` (`*.py`) and Python project files (`pyproject.toml`, `setup.cfg`) in CONSUMER Python projects. Why: consumer Python projects have no surfacer; the plan-marshall implementor's Python detectors are tuned to the marketplace's own script conventions (executor notation, TOON output, argparse surfaces) and must not be what reviews an ordinary Python codebase. Today such a diff gets the no-implementor fallback (or, before `PLAN-TRUTH-167`, a loop to the
iteration ceiling); after this plan it gets a real candidate envelope that the domain-agnostic cognitive review
consumes unchanged.

## Deliverables

0. **Gate — re-ground against HEAD.** Confirm `PLAN-TRUTH-181` has landed (shared envelope, class declaration,
   multi-implementor merge) and read its implementor authoring guide; re-scope if its mechanism differs from this spec.
1. **The implementor skill.** `marketplace/bundles/pm-dev-python/skills/ext-self-review-python/` with `SKILL.md`
   (`implements: plan-marshall:extension-api/standards/ext-point-self-review-surfacing`, declared content classes,
   Detection Rules section) and a `self_review` script exposing `surface` on the shared envelope; registered in the
   bundle's `plugin.json`.
2. **Python detectors**, each emitting into an existing registry key (no new keys without registering them in the
   shared registry first):
   - `regexes` — `re.compile` / `re.*` literals.
   - `user_facing_strings` — docstrings INCLUDING module-level and `async def` docstrings (the reach gap recorded as 216.D1), log and exception messages.
   - `unguarded_boundaries` — added `subprocess.*`, file and network I/O without `check=True` or an enclosing `try`.
   - `hoisted_binding_shadows` — a local rebinding of a module-level import.
   - `symmetric_pairs`, `flag_guard_pairs`, `producer_consumer`, `source_of_truth`, `schema_bearing_files` — Python analogues.
   - `advertised_form_help_strings` — `argparse` `help=` forms, where the project has a CLI.
   Every other registry key is emitted empty.
3. **Honest limits.** `structural_limit` names what Python static surfacing cannot see; `delta_coverage` reports
   every declared class, seeded to zero; a file type of this domain with no detector is `not_covered`, never clean.
4. **Tests from real shapes.** Per detector: a positive and a matched negative control. End-to-end: a consumer-shaped Python diff surfaces a classified envelope; the SAME `.py` path in the plan-marshall meta-project is still owned by `ext-self-review-plan-marshall` (no double review, no class conflict).
5. **Docs.** The extension-point standard's implementor list and the bundle README name the new implementor.

## Claim Labels

- OBSERVED: no `ext-self-review-python` exists — directory sweep of `marketplace/bundles/*/skills/` finds only `ext-self-review-plan-marshall` (2026-09-26).
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: No ext-self-review-python; pm-dev-python/skills: arch-gate-python, ext-triage-python, plan-marshall-plugin, pytest-testing, python-core, python-security.
- OBSERVED: consumer implementors are explicitly invited — "Consumer projects (Java, frontend, application code) MAY contribute their own implementor by following the contract below" — read at `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` § Overview.
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: ext-point-self-review-surfacing.md:9 consumer-implementor invitation.
- OBSERVED: every registry key MUST be emitted, empty where the language has no equivalent signal — same file § Required Candidate Sub-Lists.
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: ext-point-self-review-surfacing.md:233 every registry key MUST be emitted.
- HYPOTHESIS: the plan-marshall implementor's Python-specific detectors (`unguarded_boundaries`, `hoisted_binding_shadows`, `regexes`) can be reused rather than re-written, once `PLAN-TRUTH-181` makes them importable — confirm at `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py` (verify-at-outline).
  - verdict: unverifiable | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: _detect_unguarded_boundaries/_detect_hoisted_binding_shadows/_detect_regexes exist (imported self_review.py:45-66) but are underscore-private; reuse depends on PLAN-TRUTH-181's export.
- HYPOTHESIS: class ownership in the meta-project (plan-marshall implementor keeps `.py` under `marketplace/`, Python implementor takes consumer `.py`) is expressible with the 181 class declaration — confirm against 181's landed mechanism (verify-at-outline).
  - verdict: unverifiable | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Depends on PLAN-TRUTH-181; CONTENT_CLASSES has one path-shape class 'python' with no location-based ownership split today.
- HYPOTHESIS: the implementor needs no per-bundle `extension.py` registration beyond `implements:` frontmatter + `plugin.json` — confirm at `extension_discovery implementors` (verify-at-outline; `PLAN-TRUTH-181` D0 settles the same question).
  - verdict: corroborated | checked_at: a8862630661404aeb132f95ad00b413e2493bfb9 | by: truthful-signals/cleanup | rescoped: n/a | evidence: extension_discovery.py:1124-1204 frontmatter-only discovery; pm-dev-python/.claude-plugin/plugin.json exists.

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/pm-dev-python/skills/ext-self-review-python/` — new skill directory (D1–D3; absent today, verified)
- OBSERVED: `marketplace/bundles/pm-dev-python/.claude-plugin/plugin.json` — skill registration (D1)
- HYPOTHESIS: `test/pm-dev-python/ext-self-review-python/` — new test directory under the existing `test/pm-dev-python/` (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` — implementor list (D5)
- OBSERVED: `marketplace/bundles/pm-dev-python/README.md` — D5 'the bundle README names the new implementor' (cleanup 2026-09-26, understated)

## Dependencies and Sequencing

- Depends on: `PLAN-TRUTH-181` (shared envelope, class declaration, multi-implementor merge).
- Overlaps with: the other three domain plans ONLY on `ext-point-self-review-surfacing.md` (D5, one line each) — otherwise disjoint by bundle, so they can run in parallel once 181 lands; sequence the D5 line edits or let the second rebase.
- Adjacent to: `ext-triage-python` in the same bundle (finding triage, a different extension point) — untouched.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-183-ext-self-review-python-the-python-domain-self-review-surfacer.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file
under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the orchestrator owns every other
ledger write — and reports its outcome through its PR and its inbox message. See
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

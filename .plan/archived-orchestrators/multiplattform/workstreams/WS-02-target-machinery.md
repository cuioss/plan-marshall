# WS-02: The build-target machinery scopes and transforms honestly

epic: multiplattform

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-02-target-machinery.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Own `marketplace/targets/**` — the registry, the emitters, the body-transform engine, and the
per-component scoping mechanism. The workstream closes when every structural source directive is
registered and fails closed on an unmapped target, every component that exists on only some targets
declares it, and the machinery itself is inside the repository's quality gate.

## Scope

- **In scope:** `marketplace/targets/**` (registry, both component-tree emitters, `body_transform_engine.py`, `component_targets.py`, `opencode/mapping.json`), the `targets:` frontmatter mechanism and its authoring/validation surface, the repo-scoping-versus-target-scoping design question, and `test/marketplace/targets/**`.
- **Out of scope:** the runtime seam (WS-01); the bundle prose the transforms operate on, except where a plan explicitly carves a file out (WS-03); the deploy step that consumes generated output (WS-04).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-02-target-scoped-components | landed | `targets:` frontmatter scoping end to end — filter, fail-closed validation, first consumer, authoring surface. PR #1313. |
| PLAN-05-structural-directive-coverage | staged | `read_directive` in the structural vocabulary, plus the normative tool-invocation prose the registered idioms cannot reach. |
| PLAN-11-target-scoping-adoption | staged | The file-level `targets:` extension and the steward split — the prerequisites every blocked §D/M11 candidate waits on. |
| PLAN-15-repo-scoping-design | staged | Audit cluster M10: whether the meta-repo `.claude/` tree is normative, and how repo-scoping relates to target-scoping. A design plan producing an ADR before any code. |
| PLAN-16-lint-scope-marketplace-targets | staged | `marketplace/targets/` is outside the ruff lint scope, so the machinery that enforces quality is itself unchecked. |

## Sequencing and Surface Notes

- **PLAN-05 and PLAN-16 both touch `marketplace/targets/**` — sequence them, never pair them.** PLAN-16 first is preferable: it makes the lint gate real before PLAN-05 adds code to the engine.
- PLAN-11 depends on PLAN-02 (landed) for the component-level mechanism it extends to file level. It does **not** collide with PLAN-05 — PLAN-11's surface is the frontmatter/steward split, PLAN-05's is the transform engine plus bundle prose.
- PLAN-15 is a design plan: its first deliverable is an ADR, and it must land before PLAN-11 if the ADR concludes repo-scoping needs its own mechanism. Recorded as a conditional dependency, resolved by PLAN-15's own D1.
- **Cross-workstream collision:** PLAN-05's D2–D4 reach bundle files in seven bundles, including exactly one `pm-plugin-development` file (`ext-triage-plugin/standards/pr-comment-disposition.md`) carved out of PLAN-06's surface so the byte-identical escalation-block set stays whole. That carve-out is load-bearing — do not silently widen either plan's surface across it.
- PLAN-04 (WS-04) is disjoint from every plan here.

# 05 — Live verification via an existing tool (integrate, do not build)

**Independent. Lowest priority; research spike first.**

## Problem

External workflows verify that the built thing actually works end-to-end (gstack's
`/qa` Bun+Playwright daemon). plan-marshall has no end-to-end "does it run"
verification — it stops at unit tests, quality gate, and CI. The directive is to
**integrate an existing solution rather than build a daemon.**

## Approach

Spike, then integrate an existing tool (e.g. the Playwright MCP server, or an
existing acceptance harness) behind a thin plan-marshall surface — most naturally
an optional finalize step or a recipe (`recipe-acceptance-check`) that:

- maps the diff to affected entry points (reuse `architecture which-module` /
  `architecture files`),
- runs the external tool,
- emits pass/fail + evidence into `manage-findings`.

Note on this repo's artifacts: plan-marshall's own deliverables are mostly skills
and scripts, so the analogue of "open a browser" here is "run the changed workflow
end-to-end through the executor against a fixture." The plan must decide whether to
target web-app consumer projects (a browser tool), self-hosted workflow
acceptance, or both.

## Key design decisions

- **Integrate, do not rebuild.** plan-marshall owns orchestration and the findings
  contract; the external tool owns its domain.
- **Findings sink.** Acceptance results are findings, not a standalone report, so
  triage and loop-back apply.

## Open decisions

- **Which external tool**, and **which artifact class to target first**
  (consumer web apps vs self-hosted workflow acceptance). **Recommendation:**
  research spike first — this is the least-defined workstream; pick the tool, then
  author a thin recipe/finalize-step wrapper.

## Documentation to update (deliverables of this plan)

- `doc/concepts/build-management.adoc` — where acceptance verification sits
  relative to build/test/quality gates.
- `doc/concepts/recipes.adoc` or `doc/concepts/automatic-reviews.adoc` — depending
  on whether it lands as a recipe or a finalize step.
- `doc/user/commands.adoc` — the new recipe / step invocation.
- `doc/user/installation.adoc` — any external-tool prerequisite (e.g. the
  Playwright MCP server).

## On completion (final workstream)

Delete this document and remove the `05` row from [`README.md`](README.md). As the
**last** workstream to land, this plan also removes `README.md`, `principles.md`,
and the now-empty `doc/next/` directory — see the Lifecycle section in
[`README.md`](README.md).

## Scope

Research spike → medium. Lowest priority; independent of the other workstreams.

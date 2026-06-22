# 05 — Surface encoded-test verification

**Independent. Lowest priority; guidance/standard, not integration.**

## Problem

There is a recurring instinct to add a "live verification" surface — drive a real
browser, score the running app. plan-marshall deliberately does not do this, and
the gap is that the principle is not *surfaced*, so the instinct keeps recurring:

- **Verification is encoded.** The model is reproducible, committed tests —
  module-tests, quality-gate, CI, and e2e tests. An e2e test is just *more encoded
  tests*: a plan already writes them as part of implementation and the test infra
  runs them. An ephemeral live browser run is not reproducible the way a committed
  e2e test is, so it works against the model rather than with it.
- **Exploration is the user's own tools.** Live poking-around (Chrome for Claude, a
  browser MCP) belongs to the tools the user already has. plan-marshall orchestrates
  encoded work; it does not own interactive exploration.

## Approach

Make the principle explicit and give encoded e2e verification a documented home —
**no browser or daemon integration**:

1. A concept note stating the boundary plainly: verification = encoded e2e tests;
   exploration = the user's own tools (explicitly out of scope).
2. (Optional) a thin e2e-testing standard in the domain test skills, alongside the
   existing integration-test neighbours (e.g. `junit-integration`), covering when
   an e2e test is warranted and how to encode it so a plan produces a committed,
   re-runnable test rather than a one-off check.

## Key design decisions

- **No browser/daemon, no live-run surface.** Verification stays encoded and
  reproducible; exploration stays with the user's own tools.
- **Guidance over machinery.** The deliverable is a concept doc + an optional
  testing standard — not a new finding producer, recipe, or finalize step.

## Documentation to update (deliverables of this plan)

- A verification concept doc (or `doc/concepts/build-management.adoc`) — the
  encoded-verification / exploration-out-of-scope boundary.
- The relevant domain test skills — the optional e2e-testing standard.

## On completion

Delete this document and remove the `05` row from [`README.md`](README.md); this is
part of the plan's finalize.

## Scope

Small. Guidance + an optional standard; independent, lowest priority.

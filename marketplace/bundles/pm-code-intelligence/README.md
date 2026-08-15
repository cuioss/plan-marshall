# pm-code-intelligence

Language-server-derived symbol intelligence for the Plan Marshall module graph.

## What this bundle is for

Every other derivation resolver joins over data a static reader already produced —
Maven coordinates, markdown cross-references, AST-parsed imports. This bundle
contributes the one edge set that needs a real parser to resolve: **symbol
references answered by a language server**.

It hosts exactly one thing, the `lsp` derivation resolver, and it exists as its
own bundle for a structural reason rather than a stylistic one. A bundle
registers at most one resolver, so an LSP-derived edge set added to
`pm-dev-python` would be stamped `python` and become indistinguishable from that
bundle's AST-import join. Two derivations that must stay distinguishable in an
edge's `producers[]` have to live in two bundles — which is exactly the case
here, since the whole value of the LSP edge is that a real parser resolved it.

## The lifecycle, and why it is a batch harvest

The server runs **once at discovery time**, not per query. That is forced by the
Axis-C contract: a derivation resolver is a pure function of its arguments, and
resolvers are dispatched on every `graph` / `path` / `neighbors` / `impact` call.
A server booted inside `derive_edges` would pay its entire index cost on each of
those. So the harvest runs in the discovery-time engine
(`pm-plugin-development:plan-marshall-plugin:lsp_harvest`), persists its
references into `derived.json`, and this bundle's resolver joins over them —
the same shape the `python` import join already uses.

A warm interactive client answering definition or rename queries at a cursor
position is a **different lifecycle** and deliberately not built here. See
`doc/concepts/code-intelligence.adoc` for the rationale.

## Honest failure, never a silent zero

A server that is absent, fails to start, times out, or does not support the
workspace produces `ran: false` with a stated reason, which the resolver surfaces
as a note. A dead server and an edge-free workspace are different answers and are
never collapsed into the same empty result.

## Configuration

Off by default. The harvest is opt-in through the shared extension-defaults
surface in `.plan/marshal.json`; this bundle ships no configuration mechanism of
its own. See the bundle's `plan-marshall-plugin` skill for the keys.

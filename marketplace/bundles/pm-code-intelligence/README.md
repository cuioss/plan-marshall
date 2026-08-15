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

Answering definition or rename queries at a cursor position is a **different
lifecycle**, and it already exists: `plan-marshall:lsp-client` does that for a
leaf that opts in. This bundle is the batch counterpart, and it **reuses that
client's session and its machine-local server binding** rather than shipping a
second LSP client. See `doc/concepts/code-intelligence.adoc` for why the two
lifecycles stay separate.

## Honest failure, never a silent zero

A server that is absent, fails to start, times out, or does not support the
workspace produces `ran: false` with a stated reason, which the resolver surfaces
as a note. A dead server and an edge-free workspace are different answers and are
never collapsed into the same empty result.

## Configuration

**This bundle ships no configuration of its own.** The harvest runs for a language
exactly when that language has an enabled `language_servers` binding in the shared
machine-local run-configuration store — the same binding `plan-marshall:lsp-client`
reads, set with `run_config language-server set`.

That store is git-ignored, so a fresh clone has no binding and the harvest is off
by default. Enabling it trades Tier 0's subprocess-free crawl for the reference
set, which is why it is opted into rather than out of.

## Scope

The harvest is materialized by `pm-plugin-development`'s module discovery, which
covers **marketplace-bundle modules**. In a project whose modules come from another
discovery extension, no module carries a harvest record and the resolver reports
that it did not run — it does not report a confident zero.

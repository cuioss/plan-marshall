# Why the LSP-shaped query facade was removed — reasoning and result

This is the reasoning record behind [`plan.md`](plan.md): the design discussion that settled *why*
the facade is removed rather than kept, renamed, or extended. The plan states the change; this states
the argument. The run report ([`report-01.md`](report-01.md)) references this file.

## Decision

The `manage-architecture` query client keeps a **single, domain-native verb vocabulary** —
`module`, `impact`, `find`, `resolve`, `which-module`, `path`, `graph`, `neighbors`, `files`,
`search`, `capabilities`. The `lsp` subcommand group that plan `130` added — aliasing four of those
verbs to LSP method names — is removed. **The query API is deliberately *not* LSP-conformant**, and
that is the correct design: LSP integration with real substance is owned by separate plans, not by a
naming layer over these verbs.

## What the facade was

Plan `130` shipped an **additive facade**: an `lsp` group whose four subcommands were thin
pass-throughs to existing verbs, returning their answers unchanged —
`lsp hover`→`module`, `lsp references`→`impact`, `lsp workspace-symbol`→`find`,
`lsp definition`→`resolve`. It renamed nothing and removed nothing. It also had **zero adoption**: no
workflow, persona, skill, `CLAUDE.md` rule, or test ever invoked it — every reference in the tree was
its own definition, its own test, or the documentation describing it.

## The principle: pre-1.0, no duplications and no shims

A facade over a stable public API earns its keep by preserving existing callers across a rename. Here
neither condition holds: there are **no existing callers to preserve** (zero adoption) and **no
stability obligation** (the project is pre-1.0). What remains is pure duplication cost — a second
vocabulary to learn, document, test, and keep in step with the verbs it mirrors — and a shim (four
forwarding handlers) whose only job is to restate an answer the underlying verb already gives.

## The design question examined: is the core query API LSP-conformant?

**No — and only loosely "analogous," for a minority of verbs.**

- Only **4 of the ~11 verbs** were ever given an LSP name, and only through the facade.
- The four mappings are **deliberate semantic stretches**, which the facade's own code and docs
  admitted:
  - `references`→`impact` — `impact` is a *reverse module-dependency closure*; the handler docstring
    itself noted "LSP references is neither transitive nor module-scoped." It is not
    find-all-references-to-a-symbol.
  - `definition`→`resolve` — `resolve` maps a **build-command name to its executable path**. That is
    not go-to-definition on a symbol.
  - `workspace-symbol`→`find` — `find` is a **path glob over the file inventory**, not a symbol search.
  - `hover`→`module` — module metadata, not hover-at-a-position.
- The remaining verbs (`which-module`, `path`, `graph`, `neighbors`, `capabilities`, `files`,
  `search`) have **no standard LSP method at all**; the facade parked them under
  `workspace/executeCommand` "residue."

The reason is structural. **LSP is `(uri, position)`-oriented** — a cursor on a symbol in a text
document, resolved by a real parser/index. **This substrate is module- and inventory-oriented**,
derived once at crawl time, with no symbol index and no cursor concept. The two models do not line up.

## Can the core be made *fully* LSP-conformant instead? (feasibility)

**No — not without either losing functionality or shipping semantics that break real LSP clients.**

1. **It would require becoming a language server.** A conformant `hover` / `references` / `definition`
   must accept `(uri, position)` and answer over a real symbol index — a warm, long-lived,
   parser-backed process. That is the exact architecture this substrate rejects by design: its
   consumers are one-shot subprocesses and dispatched leaves, and "booting a server per query is not
   viable" (the premise of the derivation-resolver plan).
2. **Most verbs have no conformant expression.** The module-graph and inventory verbs would have to be
   dropped, or demoted to the generic `workspace/executeCommand` escape hatch — which is arbitrary RPC
   over the LSP transport, *not* conformant semantics. Either way the substrate's actual value is lost
   or disguised.
3. **Conformance is interop, not vocabulary.** The point of being LSP-conformant is that a real LSP
   client can talk to you. A client calling `textDocument/references` expects symbol-reference
   locations; this substrate would return **module** dependency data — broken interop. Renaming a verb
   to an LSP method it does not honestly implement ships a lie that breaks clients, which is strictly
   worse than an honest domain name that never claimed to be LSP.

So "one LSP-shaped vocabulary at the core" is not a smaller, cleaner version of the facade — it is a
different, larger system the substrate is deliberately not, obtained by discarding the functionality
that makes the substrate useful.

## The decision, restated

- **Remove the facade** — the shim and the duplication both.
- **Keep the domain-native vocabulary** as the single vocabulary. It is honest about what it answers.
- **Do not rename** the verbs to LSP names. Two reasons: the semantics do not match (renaming would be
  dishonest, per the interop point above), and the blast radius is large — these verbs are embedded
  across `CLAUDE.md` hard-rules, the persona agent-behaviour standards, and multiple bundles.

## Where real LSP lives — and why removal aligns with the epic

LSP is used correctly elsewhere in the `code-intelligence-substrate` epic, as substance rather than
vocabulary:

- **`200-lsp-derivation-resolver`** — a language server as a **derivation-time producer**: it runs
  once at crawl time, harvests real symbol references, lifts them to module-level edges, and stamps
  them with their producer. LSP as an edge *source*, not a query backend.
- **`240-skill-lsp-server`** — a real **LSP surface** (editor/agent-facing) that *translates* editor
  requests down onto these native verbs. Its own Notes anticipated exactly this outcome: *"if it
  descoped to an additive facade, this plan absorbs the translation work and must be re-scoped
  upward."* Plan `130` was that descope — an LSP *name* without LSP *substance*. Removing the facade
  clears the false start so `240` can be the honest translation layer over a clean, single-vocabulary
  core.

## Result

The facade, its test, and every piece of its documentation are removed; the established verbs are
unchanged in name, arguments, and behaviour; and plan `130`'s genuinely-new behaviour — the
`capabilities` report, the refine `UNDERIVABLE` guard, and the `search --content` measurement contract
(`--ignore-case`, `file_count`) — is retained, because none of those is a shim. Full `./pw verify` is
green, and an independent fresh-eyes read of the query docs confirmed the surface now presents **one
coherent vocabulary, with no facade trace and no dangling references**.

# Proposal — which protocol surface should expose the skill corpus's reference intelligence?

This is the **written proposal** deliverable D0(b) of [`plan.md`](plan.md) requires. Its analysis —
everything up to § "Decision" — is written **undecided**: it lays out the options, what each costs and
buys, and the consumer and measurement evidence that bears on the choice. ⛔ **The operator decides,
and did**; the run that wrote this had no authority to choose. What the operator settled, and what the
run then built on that instruction, is recorded in § "Decision (operator, this run)" at the end — kept
separate from the analysis so the two are never read as one voice.

Read it with [`report-01.md`](report-01.md), which records how each figure below was obtained.

## The question

The skill corpus carries real cross-file reference intelligence — five edge types with line-level
provenance — and **nothing reaches it**. What surface should expose it?

The plan framed this as a genuine fork: *is an editor protocol the right surface at all, given that
the consumers of this repository's intelligence are predominantly agents rather than humans in an
editor?* Two findings from this run reshape that framing, and one of them was not available at the
plan's research date.

## Evidence

### E1 — The intelligence exists, and it is real

`pm-plugin-development:tools-marketplace-inventory:resolve-dependencies` builds a full index over
`marketplace/bundles/` and answers `deps` / `rdeps` / `tree` / `validate`. Measured on this clone:

| Quantity | Value |
|---|---|
| Components indexed | 306 |
| Forward edges | 5 301 |
| Edge types | `script`, `skill`, `import`, `path`, `implements` |
| Provenance | line-level (`context: "line:288"`) |

The plan's load-bearing claim — *the cross-file skill intelligence already exists and returns real
edges with line-level provenance* — is **confirmed**. Nothing here needs building.

### E2 — Nothing consumes it

A tree-wide search for `resolve-dependencies` outside `doc/plans/` returns **six** files: the
skill's own `SKILL.md`, its three scripts, and its two test files. No workflow, persona, skill,
`CLAUDE.md` rule, or command invokes any of the four dependency verbs.

⚠ This is the same zero-adoption signature that condemned the `lsp` query facade in plan
[`135`](../135-remove-lsp-query-facade/rationale.md). It does **not** condemn this plan — the facade
was zero-adoption *duplication*, whereas this is zero-adoption *capability* — but it does mean the
choice below is not "which protocol do existing callers want." **There are no existing callers.**
The protocol decision creates the first consumer, so it should be made by asking which consumer is
actually wanted, not which is cheapest to build.

### E3 — Latency: the index is interactive only if it is resident

D1's gate, measured on this clone (3 runs, median reported):

| Path | Latency |
|---|---|
| One-shot CLI, end to end (`deps`, `rdeps`, `validate`) | **≈ 2.0 s** |
| `build_dependency_index` alone, in-process | **≈ 1.87 s** |
| `get_forward_deps` / `get_reverse_deps`, warm index | **< 0.1 ms** |
| `resolve_transitive_deps` depth 10, warm index | **≈ 1.5 ms** |
| `detect_circular_deps` (whole graph), warm index | **≈ 4.0 ms** |

**Essentially the entire cost is index construction, and it is paid per process.** A warm index
answers every verb the plan names in single-digit milliseconds — comfortably interactive. A cold one
costs 2 s, which is not.

⭐ **This is the most decision-relevant number in the proposal, and it does not point where the plan
expected.** D1 was written as a *risk* — *if the verbs are too slow, an incremental or cached index
becomes a deliverable*. The measurement says something narrower and more useful: the index does not
need to be incremental or cached. **It needs to be resident.** Any surface that survives across
requests — which a language server is by construction — turns a 2 s query into a 2 s startup plus
microsecond answers. Any surface that forks a process per query pays the 2 s every single time.

So latency does not merely permit the protocol choice; it **discriminates between the options
below**, and it is the axis on which they most differ.

### E4 — The asserted absence, re-verified (2026-08-15)

⛔ The plan flagged this as its highest-risk claim. Re-verified by web search on **2026-08-15**;
the method and queries are recorded in [`report-01.md`](report-01.md). The claim is **partially
refuted**, and the refutation matters.

**Still true.** Nothing in the ecosystem understands a *skill corpus*. The agent-skills tooling that
exists is file-local spec-conformance linting — `agent-skills-lint`, `skillcheck`, and comparable
CLI validators check YAML frontmatter shape, description quality, body size, and cross-agent
compatibility against the [agentskills.io](https://agentskills.io/specification) specification. One
such project states the gap explicitly: the specification *"only validates frontmatter basics but has
no concept of verifying related_skills against the actual skill index."* None is a language server,
and none resolves a `bundle:skill:script` notation.

**No longer true as stated.** Generic **Markdown** language servers now exist and do overlap this
surface:

| Project | Provides | Covers which of this repo's five edge types |
|---|---|---|
| `markmark` | go-to-definition, find-references, link completion, link validation, project-wide | `path` only — and only where the reference is a real Markdown link |
| `mdbase` language server | diagnostics, completions, hover, go-to-definition over frontmatter and link targets | `path`, partially; frontmatter shape but not `skills:`/`implements:` semantics |

⚠ **Neither understands the notation.** `bundle:skill:script`, `skills:` frontmatter, `implements:`,
and the Python-import edges are invisible to both — they are plain text to a generic Markdown server.
So an off-the-shelf server covers roughly **one of five edge types**, and the four that carry this
corpus's actual structure remain unserved. The absence claim survives where it matters; it should
simply no longer be stated as *"nothing exists."*

**And the second claim is confirmed.** The mature "language server for agents" projects do run the
opposite direction — `lsp-skill` (LSAP), `lsp-validation`, `setup-lsp`, `claude-code-lsps`,
`claude-languages` all bridge **per-language code** servers to agents, each requiring the language
server binary installed separately, and none offering documentation or Markdown-corpus intelligence.
⛔ Do not rebuild them.

### E5 — ⭐ The new fact: Claude Code consumes LSP servers natively, from the plugin manifest

This did not exist at the plan's research date, and it collapses the fork's original framing.

Claude Code's plugin schema now supports an **`lspServers`** field — declared inline in
`plugin.json` or in a sibling `.lsp.json` — with this shape:

```json
{
  "lspServers": {
    "skill-corpus": {
      "command": "…",
      "args": ["…"],
      "extensionToLanguage": { ".md": "…" }
    }
  }
}
```

Optional keys include `transport` (`stdio` default), `env`, `initializationOptions`, `settings`,
`startupTimeout`, `restartOnCrash`, `maxRestarts`, and `diagnostics` (default `true` — **pushes
diagnostics into Claude's context**). Plugin-declared servers start automatically when the plugin is
enabled, and give Claude go-to-definition and find-references over the matched extensions.

⭐ **So "editor protocol" and "agent protocol" are no longer opposed on this platform.** The plan's
fork rested on the premise that an editor protocol serves humans in an editor while agents want tool
calls. On Claude Code today, an LSP server declared by a plugin *is* an agent-facing surface: the
agent is a first-class LSP client, and diagnostics flow into its context automatically. A single LSP
server would serve both audiences.

Two caveats bound that, and both are real:

- ⚠ **`extensionToLanguage` binds by file extension, and `.md` is enormous.** The documented
  behaviour when several enabled servers claim one extension is that **the first registered wins and
  the others never start**. A `.md` server shipped by this marketplace could therefore silently
  disable a user's own Markdown server. This is a strong, concrete argument for D4's strict opt-in —
  and an argument that opt-in must be *default-off at the manifest level*, not merely a config flag
  the server reads after it has already claimed the extension.
- ⚠ **The binary must be on `$PATH`.** `lspServers` configures a connection; it ships no server. Any
  option below still owes an install story.

## The options

### Option A — A real LSP server over the corpus

A long-lived stdio server, declared via `lspServers`, answering `textDocument/definition`,
`textDocument/references`, `textDocument/hover`, and (gated) `textDocument/publishDiagnostics` for
skill and script notations inside Markdown.

- ✅ **Latency is solved by the architecture** (E3): index once at `initialize`, answer in
  microseconds. This is the only option where the 2 s cost is paid once.
- ✅ **Serves both consumers at once** (E5): humans in any LSP editor, and Claude Code natively.
- ✅ Honest semantics — unlike the removed facade, `(uri, position)` on a notation token genuinely
  *is* go-to-definition, and a notation *is* a symbol. The mismatch that killed plan `130`'s facade
  does not exist here.
- ❌ Largest build: JSON-RPC lifecycle, document sync, position→token resolution, incremental
  re-index on change.
- ❌ Inherits the `.md` extension-collision risk (E5).
- ❌ Needs an install-and-launch story for a Python entry point.

### Option B — A tool-calling / MCP surface

Expose `definition` / `references` / `hover` as agent tool calls rather than LSP methods.

- ✅ Matches the stated consumer if the answer to "who consumes this?" is *only* agents.
- ✅ No extension collision, no document-sync machinery, no position arithmetic.
- ❌ ⛔ **Latency is unsolved unless the surface is resident** (E3). A one-shot subprocess per tool
  call pays 2 s every call. An MCP server *is* resident and would solve it; a script-executor verb is
  not and would not. **This distinction, not the protocol name, is what actually decides.**
- ❌ Serves no human in an editor.
- ⚠ Risks repeating plan `130`: a second vocabulary over verbs nothing yet calls. E2 says there are
  no callers to preserve — so this option must justify itself by creating a consumer, not by
  wrapping one.

### Option C — Extend the existing `plan-marshall:lsp-client` seam, inverted

This repository already ships an LSP **client** (`plan-marshall:lsp-client`) with a settled opt-in
model: machine-local `language_servers` config in `run-configuration.json`, a `not_configured` /
`unreachable` / `ok` coverage contract, and a documented fail-soft path to `Read`/`Edit`.

- ✅ **Reuses a proven opt-in and degradation design** — which is most of what D4 asks for, already
  built and documented.
- ✅ Consistent with the epic: plan `200` used LSP as a derivation-time *producer*; this would use it
  as a query-time *provider*, in the same configuration store.
- ❌ The client's own hosting model is **short-lived subprocess per call, no daemon** — explicitly
  "cold start is paid once per call." Inverting it without changing that model reproduces the 2 s
  problem (E3).
- ⚠ Really a *configuration and packaging* answer rather than a protocol answer; it composes with A
  or B rather than competing with them.

#### Option C examined against the code, not its prose

The reusable part is real, and it is the **degradation contract**: `not_configured` / `unreachable` /
`ok` as distinct states, `provider_count` as the discriminator that keeps *no server ran* separable
from *ran and found nothing*, `fallback: read_edit`, `preflight` naming its healthy state `ready`
rather than `ok` (a precondition is not an outcome), and the documented promise that *a project that
never configures a server loses nothing*. That is most of D4, already designed and tested.

⛔ **But the store itself is a direction error, not merely a costly one.** Every existing user of
`language_servers` is a *client of a binary someone else installed*; the schema is literally the argv
needed to spawn a third-party server on this machine. A surface shipped *by this repository* inverts
that, and three schema assumptions break:

1. **`command` is machine-specific because the binary is machine-installed.** A repo-shipped server's
   command is identical for every developer, so a git-ignored machine-local store would make each one
   hand-enter the same constant.
2. **The key is a *language*** (`python`, `go`). A corpus is not a language. Keying it `markdown`
   collides semantically with a real Markdown server — and on Claude Code, literally, on `.md`.
3. **`enabled` is one switch per language, and it is already overloaded.** The run-config standard
   itself warns that enabling a language also switches on a whole-workspace harvest at every crawl,
   and concedes that a project wanting leaf lookup *without* the harvest "has no separate switch
   today". A third consumer with a third cost profile worsens a known wart.

⚠ **And the residency mismatch is in the code, not inferred from the prose.** `_session()` constructs
`StdioTransport → LspSession → initialize()` per call; `_with_session` closes it afterwards;
`preflight` spawns and immediately tears down. The skill states the model outright: *"There is no
daemon, no socket, and no long-lived child — cold start is paid once per call."* So Option C's hosting
model **is** the ~2 s-per-query shape of E3. It cannot be reused for residency; its core would be
replaced and only the naming kept.

⚠ One further coupling: plan [`220-resolver-configuration`](../220-resolver-configuration.md) has not
executed, and the run-config standard records this section as *"the shared configuration surface the
resolver-configuration work extends"*. This plan's own Notes forbid running concurrently with that
surface.

**So C is not a competitor to A — it is a sub-decision inside A: where does A's configuration live?**
The answer this analysis reaches is *not this store* — while its degradation contract is worth copying
verbatim.

### Option D — Do nothing yet, and create the consumer first

Ship no surface. Given E2 — nothing consumes the intelligence at all — first make one existing
workflow depend on the dependency verbs, then let that consumer's shape pick the protocol.

- ✅ ⭐ Directly answers the epic's own recurring failure mode: plan `130` shipped a surface with zero
  adoption and plan `135` removed it. This option refuses to make that mistake a third time.
- ✅ Cheapest by a wide margin, and forecloses nothing.
- ❌ Leaves the intelligence unreachable, which is the problem the plan was written to solve.
- ❌ Defers rather than decides.

## What the evidence does and does not settle

**Settled by measurement, and true of every option:** the surface must be **resident**. A protocol
choice that forks a process per query is a 2 s-per-query surface regardless of which protocol it
speaks (E3). This is the constraint the operator should weigh first, because it eliminates the
one-shot-CLI shape entirely rather than merely disfavouring it.

**Settled by re-verification:** nothing off-the-shelf serves this corpus's notation (E4). Generic
Markdown servers cover about one edge type of five, so integrating one is a complement, not a
substitute. ⛔ And the agent-LSP bridges run the other direction — do not rebuild them.

**Newly true, and reframes the plan's question:** on Claude Code, an LSP server declared in the
plugin manifest is consumed by the *agent*, automatically, with diagnostics pushed into its context
(E5). The plan's premise that an editor protocol serves the wrong audience is therefore **no longer a
reason to reject Option A** — though it remains a reason to ask whether an editor is wanted at all.

**Not settled, and genuinely the operator's call:** whether this repository wants a human-facing
editor surface in addition to an agent-facing one; whether creating the first consumer (Option D)
should precede building any surface, given that zero adoption has already cost this epic one full
build-and-remove cycle; and how much appetite there is for the `.md` extension-collision risk that
Option A carries on Claude Code.

## What this analysis, on its own, settles — and what it does not

⛔ **Nothing above chooses.** Read to this point, the proposal leaves the fork open: D2 (the surface),
D4 (configuration), and D5's developer page all wait on a decision this run had no authority to make.
D5's developer page in particular is required to *record* the decision and its rationale, which cannot
be written before there is one.

That decision was subsequently taken **by the operator** and is recorded at the end of this document;
the work it authorised shipped in the same branch. This section states the position as of the analysis
alone, which is what makes the separation legible.

⛔ D3 (live diagnostics) is blocked independently of the fork, and remains unimplemented. Its hard gate — the
validator-precision plan [`230-validate-precision`](../230-validate-precision.md) — has not been
executed. Measured on this clone, the validator reports **380 unresolved edges of 5 301**, of which
**370 (97.4 %)** are demonstrable false positives:

| Class | Count | Share | Example |
|---|---:|---:|---|
| Documentation placeholder — not a reference at all | 55 | 14.5 % | `groupId:artifactId:scope`, `bundle:skill:script` |
| Foreign namespace — build command, Maven GAV, lint target | 116 | 30.5 % | `default:verify:compile`, `lint:js:fix` |
| Real component; third segment is a verb or module, not a script | 199 | 52.4 % | `plan-marshall:manage-execution-manifest:compose` |
| Residue — plausibly a genuine broken reference | 10 | 2.6 % | `pm-dev-java:build-maven:maven` |

⛔ **Streaming this set into an editor would ship roughly 370 confident-wrong diagnostics** at the
highest-visibility surface this epic has. The plan's hard gate is correctly placed, and it is unmet.

## Decision (operator, this run)

⭐ The proposal above was presented to the operator, who **decided A + D**: build the resident LSP
server (A), sequenced with D's discipline that the surface must not ship without a consumer.

⭐ **E5 is what makes that pairing coherent rather than contradictory.** D's whole point is to avoid a
third zero-adoption surface after the `130`→`135` build-and-remove cycle. On Claude Code, a
plugin-declared LSP server is consumed by the **agent**, automatically — so declaring the server
*creates* its first consumer instead of waiting for one. A and D partially collapse into a single step
on this platform rather than being sequential.

⚠ **One tension the decision had to resolve.** A plugin-declared server **starts automatically when
its plugin is enabled**, which is the opposite of D4's "strictly opt-in". Satisfying D4 therefore
required the opt-in to be enforced *inside* the server: it starts, reads its own configuration, and
when not enabled advertises **no capabilities**, answers every request emptily, and never builds the
index. The manifest cannot be the switch.

Per Option C's analysis, the configuration went to the project's version-controlled
`.plan/marshal.json` (`code_intelligence.corpus_language_server.enabled`) rather than to the
machine-local `language_servers` store, while that store's degradation contract was reused verbatim.

⛔ **D3 remains blocked and unimplemented** — its hard gate
([`230-validate-precision`](../230-validate-precision.md)) has not executed, and no diagnostic
capability is advertised. The 97.4 % false-positive measurement above is why.

The decision and its rationale are recorded for the long term in
`doc/developer/corpus-language-server-protocol.adoc`; this section records only that the choice was
the operator's, not the run's.

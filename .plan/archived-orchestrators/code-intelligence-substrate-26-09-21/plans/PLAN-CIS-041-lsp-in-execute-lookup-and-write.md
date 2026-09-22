# PLAN-CIS-041: A Warm Language Server In The Execute Envelope — Used At Both Ends Of A Task

epic: code-intelligence-substrate
workstream: WS-03

> Staged 2026-08-09 on operator direction, grounded against the PLAN-CIS-031 landing (#1126).
> ✅ **Operator decision recorded 2026-08-09: STRICTLY OPT-IN (configured), not default-on.**
> An unconfigured project must lose nothing. Self-sufficient spec.

## Objective

Give `phase-5-execute` an **opt-in** live language-server client, used at **both ends of one
task**:

- **Upfront — lookup.** `workspace/symbol`, `textDocument/definition`, `references`,
  `documentSymbol` answer *where is X* and *what shape is this file* with **coordinates, not
  bodies**. A task locates its work without reading the files it does not need to change.
- **Later — writing.** `textDocument/rename`, `codeAction`, `formatting` return a
  `WorkspaceEdit` — a complete, parser-verified, multi-file patch — and
  `publishDiagnostics` returns a correctness signal without a build.

⭐ **The "both ends" framing is what makes the lifecycle work, and it is the answer to the
objection `PLAN-CIS-026` recorded.** LSP assumes a long-lived editor session amortizing index
cost over thousands of queries; the epic correctly concluded that booting a server *per query*
is not viable. But the amortization unit here is neither the editor session nor the query — it
is **the task envelope**, and #1126 measured `5-execute` at **~122 turns per envelope**. A
server started once at task entry, used to locate at the start and to edit and diagnose at the
end, is amortized over ~122 turns. **Cold start is paid once per task, not once per query.**

## Why `5-execute`, specifically — the data picks the same phase the operator did

From #1126's six-phase instrumented `metrics.toon` (first-party, recomputed by the orchestrator):

| phase | index-answerable share of exploration | resident ctx | turns/envelope |
|---|---:|---:|---:|
| 2-refine | 3.3% | 237K | ~47 |
| 3-outline | 16.8% | 359K | ~61 |
| 4-plan | 0.0% | 273K | ~70 |
| **5-execute** ⚠ | **33.6%** | **696K** | **~122** |
| 6-finalize | 13.8% | 721K | ~37 |

⭐ **`5-execute` has the highest index-answerable exploration share of any phase — the single
best case for a code substrate anywhere in the plan — and the longest envelopes.** Both LSP
directions attack the same product: lookup reduces the **bytes** (coordinates instead of file
bodies), writing reduces the **turns** (one call instead of N `Read`+`Edit` pairs, and a
diagnostic instead of a build round-trip). ⚠ `5-execute` is re-entered on this plan
(`close_count: 2`), so its figures are **labelled, not quoted as rates**; the *ranking* is what
this section rests on and it is robust to the row's arithmetic.

## ⭐ The write side is the build-management trick applied to editing

`doc/concepts/token-management.adoc` § 2's whole argument for the build skills is: spawn a
subprocess, suspend the LLM, return one TOON — **token cost independent of build duration**.
A `rename` across twenty files is the identical shape one axis over: **token cost independent
of the number of files edited.** Today that rename is ~20 `Read` calls, ~20 `Edit` calls, and a
verify round-trip, every byte of it resident for the remainder of a ~122-turn envelope.

And the read side is a discipline the epic has **already written down and never applied above
Tier 0**: `code-intelligence.adoc` § "Location and strength, never the lines" argues that a
response's size should be a function of file count rather than match density. `references`
returns locations; it is the same rule, one tier up.

## ⛔⛔ Three hard problems — read these before scoping anything

### 1. This REOPENS what PLAN-CIS-026 deliberately closed. It is not an extension of it.

`PLAN-CIS-026` scopes the language server as a **derivation resolver**: batch, run-once,
edges into the persisted store, with *"live pass-through … deliberately OUT of scope"*, recorded
so *"the next reader does not treat its absence as an oversight"*. **This plan is that recorded
alternative, now commissioned.** ⛔ **Do NOT fold this into CIS-026** — a batch harvester and a
warm interactive client are two incompatible lifecycles, and a plan carrying both would ship
neither. The two may share a server *binary* and a *configuration surface*; they share no
lifecycle. ⚠ CIS-026 is **not** a dependency: this plan needs no edges in the graph.

### 2. `marshalld` is the right host and its scope wall says no.

The daemon already is the warm, long-lived, opt-in, registration-gated, per-machine process an
LSP lifecycle needs — and `doc/concepts/build-server.adoc` states it owns **"exactly build-class
work"**, with remote-CI waits *"deliberately out of scope"*. An LSP session is neither. ⇒ **D1
must make an explicit hosting decision**, and if it widens the daemon, it inherits the daemon's
trust discipline verbatim: **verify, never resolve**; owner-only socket; clean server-side
baseline environment; a `killed` child classified as `killed` and never as `failure`. ⛔ **A
language server holding an open workspace is a NEW class of long-lived child** — the existing
security model was derived for a build child that exits, and must be re-derived, not assumed.

### 3. ⛔⛔ A `WorkspaceEdit` is a mutation no context reviewed. This is the real risk.

Every mutation in this system today passes through an LLM that can be asked why. A `rename`
touching twenty files is a mutation **nothing read**. That collides with three things the epic
already knows:

- `code-intelligence.adoc` § The honest limit — *"provenance makes an answer auditable; it does
  not make it correct"*. CIS-026 D2 already warns it *"is capable of producing
  [confidently-labelled wrong edges] at volume"*. **This one writes them to disk.**
- The `affected_files` under-declaration archetype — **fifth sighting on #1126 itself** (14
  declared, 19 realized). A `WorkspaceEdit`'s footprint must be **captured from the edit**, never
  derived from a later diff.
- The change ledger and the plan write-boundary.

⇒ **The binding design rule, which D3 must ship rather than assert**: a `WorkspaceEdit` is
applied through the same recorded, footprint-capturing path an ordinary `Edit` takes; its file
list comes from the edit itself; and it is **verified after application** by re-running
diagnostics, with a worsened diagnostic set failing the step. **An edit nobody read must at
minimum be an edit the parser re-checked.**

## Deliverables

1. **D1 — GATE: feasibility and hosting, settled against a running server before anything else
   is scoped.** Can a dispatched leaf reach a warm server at all, and where does it live —
   inside the envelope, in `marshalld` (with the scope-widening decision and its trust
   re-derivation), or a per-task sidecar? Measure cold start and per-call latency for one
   language (**the project's own Python surface is the obvious first target**). ⛔ **This is the
   plan's central risk and its cheapest test — run it first.** A negative result re-scopes the
   plan to lookup-only, or retires it.
2. **D2 — the read side.** `definition` / `references` / `documentSymbol` / `workspace/symbol`
   reachable from an execute envelope, returning coordinates. ⛔ **Carry the coverage contract
   the substrate already ships**: the caller must distinguish *no server ran* from *the server
   ran and found nothing* — the `resolver_count` / `attributor_count` / `files_scanned` shape,
   one tier up. A silent empty result is the archetype this epic exists to remove.
3. **D3 — the write side, applied through the recorded path.** `rename` / `codeAction` produce a
   `WorkspaceEdit`; it is applied with its footprint captured **from the edit**, and verified by
   a post-application diagnostics re-run. ⛔ **A worsened diagnostic set fails the step.**
   ⚠ **Evaluate the split guard here** — the natural cut is (D1+D2: lookup) then (D3+D4: write).
4. **D4 — diagnostics as a pre-build correctness signal.** Replace the build round-trip **for the
   class of errors a server can see** — unresolved imports, syntax, type errors.
   ⛔ **This does NOT replace the quality gate and must not be allowed to read as if it did.**
   A green diagnostic set is not a green build; state the boundary where the capability is
   stated.
5. **D5 — opt-in configuration, no-op degradation, and documentation.** ✅ **Operator-decided:
   strictly opt-in.** An unconfigured project takes today's `Read`/`Edit` path, byte-identical.
   ⛔ **A missing server is a REPORTED degradation, never a silent one** — the difference between
   *no server configured* and *a server configured and unreachable* must be legible.
   ⚠ **Coordinate the config surface with `PLAN-CIS-005`** (resolver configuration) and
   `PLAN-CIS-026` D4 — **do not ship a third parallel mechanism.**

⚠ **Five deliverables, D1 a gate.** At the split guard's edge; the recorded natural cut is
lookup (D1+D2+D5) then write (D3+D4). **Evaluate and record the decision at outline.**

## Claim Labels

- **OBSERVED (first-party, recomputed from #1126's `work/metrics.toon`)**: every figure in the
  phase table; `5-execute`'s 33.6% index-answerable share is the highest of the six phases.
- **OBSERVED**: `PLAN-CIS-026` records live pass-through as the explicit out-of-scope
  alternative, *"hosted in the opt-in `marshalld` daemon"*.
- **OBSERVED**: `doc/concepts/build-server.adoc` scopes the daemon to build-class work and
  states the verify-never-resolve trust posture, the owner-only socket, and the clean baseline
  environment.
- **OBSERVED**: `code-intelligence.adoc` § "Location and strength, never the lines" states the
  cost asymmetry this plan applies one tier up.
- **OBSERVED (external, `PLAN-CIS-007`)**: `agent-lsp` and `lsp-skill` already bridge ordinary
  code language servers to agents, both requiring a per-language server installed.
  ⛔ **Do not rebuild these — evaluate integrating one at D1** before writing a client.
- **HYPOTHESIS — the load-bearing one**: that a warm server is reachable from inside a
  dispatched leaf's envelope at tolerable latency. **D1 is this verification.** ⚠ A dispatched
  leaf has a constrained tool surface and cannot spawn subagents; whether it can hold or reach a
  long-lived process is **unestablished** and is exactly what D1 must settle against a running
  server rather than by reading documentation.
- **HYPOTHESIS**: that lookup-by-coordinate materially reduces bytes in practice — i.e. that
  execute tasks currently read files they do not need to change. **Plausible and unmeasured.**
  ⚠ If a task must read a file's body to change it anyway, D2's ceiling is the *locating* reads
  only, which may be small. **Measure before claiming.**
- ⛔ **Verify-first**: `PLAN-CIS-007`'s asserted absence of a skill-corpus language server was
  established by web research on 2026-07-29 and **carries the higher verification burden for an
  absence claim.** It does not gate this plan (this is the code surface, not the corpus one),
  but D1 must re-check the code-side integrations named above before building a client.

## Expected Surface

- **HYPOTHESIS**: the client's home — a new skill, or `platform-runtime`, or the
  `build-server-client` pattern re-used. **Decide at D1** (verify-at-outline).
- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/manage-build-server/` +
  `doc/concepts/build-server.adoc` — **only if D1 widens the daemon.** ⛔ That decision is D1's
  and must not be assumed by the scoping.
- **HYPOTHESIS**: `phase-5-execute` / `execute-task` — the consumer side (verify-at-outline)
- **HYPOTHESIS**: configuration — shared with `PLAN-CIS-005` (verify-at-outline)
- **OBSERVED**: `doc/user/` — the opt-in wiring page; this is the only kind of deliverable in
  the epic an operator must actively configure, so it must state plainly that an unconfigured
  project loses nothing.

## Dependencies and Sequencing

- **Depends on**: nothing hard. ⛔ **NOT gated on `PLAN-CIS-026`** — this plan needs no edges in
  the graph, and CIS-026's batch lifecycle is not this plan's lifecycle.
- ⚠ **Coordinates with `PLAN-CIS-005`** (config surface) and **`PLAN-CIS-026`** (which server
  binary, which language) — coordinate, never pair.
- ⭐ **Coordinates with `PLAN-CIS-039`** (WS-06): a live protocol client in a dispatched envelope
  is the mechanism CIS-039 needs pointed at the **corpus** rather than the code. **The marginal
  cost of the second consumer is small and the addressable share is 4× larger** — sequence so
  039 can consume this client rather than forking one.
- ⚠ **Adjacent to `PLAN-CIS-007`** (skill-LSP server, same workstream): CIS-007 is editor-facing
  and human-consumed; this is agent-facing and leaf-consumed. **Re-verify at outline that they
  are not building the same client twice.**
- ⛔ **Never pair with `PLAN-CIS-026` or `PLAN-CIS-007`** — shared server/config surface.

## Anti-goals

- ⛔ **Do not make it default-on.** Operator-decided 2026-08-09.
- ⛔ **Do not let "the language server said so" become an unaudited authority.** A `WorkspaceEdit`
  is a mutation nothing reviewed; D3's verification obligation is what makes it admissible.
- ⛔ **Do not let diagnostics read as a replacement for the quality gate.**
- ⛔ **Do not claim a token saving.** Report measured shares; sizing belongs to WS-04/WS-06.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-041-lsp-in-execute-lookup-and-write.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

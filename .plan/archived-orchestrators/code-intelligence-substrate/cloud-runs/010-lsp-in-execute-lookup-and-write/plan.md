> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# A warm language server inside the execute envelope, used at both ends of one task

**Epic:** code-intelligence-substrate
**Branch prefix:** feature

## Problem

`phase-5-execute` locates its work by reading files. To find where a symbol is defined it reads
candidate files whole; to rename a symbol across twenty files it performs roughly twenty `Read`
calls and twenty `Edit` calls, then pays a build round-trip to learn whether the result parses.
Every byte read that way stays resident for the remainder of the envelope.

A language server answers both halves of that in a different currency. `workspace/symbol`,
`textDocument/definition`, `references` and `documentSymbol` return **coordinates, not bodies**.
`textDocument/rename`, `codeAction` and `formatting` return a `WorkspaceEdit` — one complete,
parser-verified, multi-file patch — and `publishDiagnostics` returns a correctness signal without a
build.

The mechanism that makes this viable is the **amortization unit**. The standing objection to LSP in
this system is that it assumes a long-lived editor session amortizing index cost over thousands of
queries, while our consumers are one-shot subprocesses — booting a server per query is not viable.
That objection is answered by scoping the server to the **task envelope** rather than to the query
or to the editor session: a server started once at task entry, used to locate at the start and to
edit and diagnose at the end, pays cold start **once per task**.

## Goal

`phase-5-execute` can, **when a project opts in**, reach a warm language server for the two things a
server is better at than reading files: locating work by coordinate, and applying a verified
multi-file edit. An unconfigured project takes today's `Read`/`Edit` path byte-identically, and a
configured-but-unreachable server is a **reported** degradation rather than a silent one.

## Deliverables

1. **D0 — GATE: is a warm server reachable from a dispatched leaf at all?**
   Settle it **against a running server**, not by reading documentation. Measure cold start and
   per-call latency for one language — this repository's own Python surface is the obvious first
   target. Decide the hosting question in the same breath: inside the envelope, inside `marshalld`,
   or a per-task sidecar.
   ⛔ **This is the plan's central risk and its cheapest test — run it first.**
   *Done when:* a recorded measurement from a live server exists, **or** the run reports the premise
   refuted. **On refutation, HALT and re-scope to lookup-only (or report the plan retired) — do not
   proceed to D2/D3 on an unverified premise, and do not substitute a hand-built stand-in for the
   server.**
2. **D1 — the read side.** `definition` / `references` / `documentSymbol` / `workspace/symbol`
   reachable from an execute envelope, returning coordinates.
   ⛔ **Carry the coverage contract the substrate already ships**: the caller must be able to tell
   *no server ran* from *the server ran and found nothing* — the `resolver_count` /
   `attributor_count` / `files_scanned` shape, one tier up. A silent empty result is the archetype
   this epic exists to remove.
   *Done when:* a leaf obtains a symbol's locations without reading the containing files, and the
   three states above are separately representable in the returned payload.
3. **D2 — the write side, applied through the recorded path.** `rename` / `codeAction` produce a
   `WorkspaceEdit`; it is applied with its footprint captured **from the edit itself**, never
   derived from a later diff; and it is verified **after** application by re-running diagnostics.
   *Done when:* a multi-file rename lands through the recorded footprint-capturing path, the
   captured file list matches the edit, and **a worsened diagnostic set fails the step**.
4. **D3 — diagnostics as a pre-build correctness signal.** Cover the class of errors a server can
   see — unresolved imports, syntax, type errors — ahead of the build round-trip.
   ⛔ **This does not replace the quality gate and must not be allowed to read as if it did.**
   *Done when:* the capability is stated together with the boundary, and an independent cold reader
   (see Verification) reports that it read the text as *supplements the gate*, not *replaces it*.
5. **D4 — opt-in configuration, no-op degradation, documentation.** An unconfigured project takes
   today's path byte-identically.
   *Done when:* a project with no configuration produces byte-identical behaviour to today, and
   *no server configured* is distinguishable in the output from *a server configured and
   unreachable*.

⚠ **Five deliverables with D0 a gate — at the split guard's edge.** The recorded natural cut is
lookup (D0+D1+D4) then write (D2+D3). **Evaluate the split and record the decision before
implementing**; proceeding unsplit is permitted with the rationale written into the run report.

## Out of scope

- **Default-on behaviour.** The operator decided this is strictly opt-in. Excluded because an
  unconfigured project must lose nothing — a default-on language server changes the execution path
  of every project that never asked for one.
- **Batch harvesting of symbol references into the module graph.** That is a separate, already-staged
  piece of work with an incompatible lifecycle (run-once batch vs warm interactive). Excluded
  because a plan carrying both lifecycles would ship neither; the two may share a server binary and
  a configuration surface, never a lifecycle.
- **An editor-facing or human-consumed language server over the skill corpus.** Excluded because
  this plan's consumer is a dispatched leaf, not a human in an editor; conflating them builds one
  index twice.
- **Any claim of a token saving.** Excluded because sizing requires the measurement instrument that
  other plans in this epic own. Report measured shares only.
- **Widening the build daemon's scope silently.** If D0 chooses the daemon as host, the
  scope-widening is an explicit, recorded decision that inherits the daemon's trust discipline
  verbatim. Excluded as an implicit step because a language server holding an open workspace is a
  **new class of long-lived child**, and the existing security model was derived for a build child
  that exits.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/` — the client's home. **HYPOTHESIS**: a new skill, or
  `platform-runtime`, or the existing build-server-client pattern re-used. Decide at D0.
- `marketplace/bundles/plan-marshall/skills/manage-build-server/` and
  `doc/concepts/build-server.adoc` — **only if D0 widens the daemon.** That decision is D0's and
  must not be assumed by the scoping.
- `marketplace/bundles/plan-marshall/skills/phase-5-execute/` and `.../execute-task/` — the consumer
  side.
- Configuration surface — shared with the staged resolver-configuration work; **do not ship a third
  parallel mechanism.**
- `doc/user/` — the opt-in wiring page. This is the only kind of deliverable in the epic an operator
  must actively configure, so it must state plainly that an unconfigured project loses nothing.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| A warm server is reachable from inside a dispatched leaf's envelope at tolerable latency | **HYPOTHESIS** | D0's live measurement against a running server. A dispatched leaf has a constrained tool surface and cannot spawn subagents; whether it can hold or reach a long-lived process is **unestablished**. |
| Lookup-by-coordinate materially reduces bytes in practice — i.e. execute tasks currently read files they do not need to change | **HYPOTHESIS** | A measurement taken during D1. If a task must read a file's body to change it anyway, D1's ceiling is the *locating* reads only, which may be small. **Measure before claiming.** |
| The build daemon is scoped to "exactly build-class work", with a verify-never-resolve trust posture, owner-only socket, and clean baseline environment | **OBSERVED** | `doc/concepts/build-server.adoc` |
| The cost asymmetry this plan applies one tier up is already written down | **OBSERVED** | `doc/concepts/code-intelligence.adoc` § "Location and strength, never the lines" |
| The build skills' argument — spawn a subprocess, suspend the LLM, return one TOON, token cost independent of build duration — is the same shape as an edit whose cost is independent of file count | **OBSERVED** | `doc/concepts/token-management.adoc` § 2 |
| Third-party bridges between ordinary language servers and agents already exist, each requiring a per-language server installed | **OBSERVED (external, dated 2026-07-29)** | ⛔ **Re-derive at D0 before writing a client** — an external-ecosystem claim decays, and building a client that already exists is the failure this label exists to prevent. |
| `phase-5-execute` has the highest index-answerable exploration share of any phase and the longest envelopes | **OBSERVED, but the supporting record is NOT reachable from this clone** | The measurement lives in a machine-local metrics record under `.plan/`, which is git-ignored. ⛔ **Do not go looking for it.** It is stated here as the reason the phase was chosen; **nothing in this plan requires re-deriving it**, and no deliverable may be gated on it. |

An asserted **absence** ("X does not exist, build it") is verified exactly as an asserted presence,
and is the higher-risk half here: the third-party-bridge row above is precisely such a claim, and an
unverified absence sends this plan to build a client that already exists.

## Verification

- **D0 is verified by execution, not by reading.** A latency and cold-start figure from a live
  server, or an explicit refutation. No documentation read substitutes for it.
- **D2 is verified adversarially**: introduce a deliberate defect through the `WorkspaceEdit` path
  and confirm the post-application diagnostics re-run **fails the step**. A positive-only test
  passes against a no-op implementation and proves nothing.
- **D3 and D4 carry a cold read.** Their value is what a later reader *does* with the text — whether
  a diagnostics pass reads as supplementing or replacing the quality gate, and whether the opt-in
  page reads as "you must configure this" or "you lose nothing if you don't". Dispatch the pre-PR
  verification sub-agent to read both **cold** and report which reading it took. **If the reading is
  wrong, the wording failed, however complete it looks.**
- **D1's coverage contract is verified by a negative control**: a configured-but-unreachable server
  and a server that ran and found nothing must produce distinguishable output. Assert both.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Why this phase.** Among the six phases, `5-execute` has both the highest index-answerable share
  of exploration and the longest envelopes (~122 turns), so both LSP directions attack the same
  product: lookup reduces the **bytes**, writing reduces the **turns**. The supporting figures are
  machine-local (see Claim labels) and are context, not a dependency.
- **The recorded alternative, now commissioned.** A sibling plan in this epic scopes the language
  server as a *derivation resolver* — batch, run-once, edges into a persisted store — and records
  live pass-through as deliberately out of scope so that "the next reader does not treat its absence
  as an oversight". This plan **is** that recorded alternative. It is not an extension of the other
  and must not be folded into it.
- ⛔ **The real risk is D2, and it is not latency.** Every mutation in this system today passes
  through a context that can be asked why it made the change. A `WorkspaceEdit` touching twenty
  files is a mutation **nothing read**. Two things the project already knows bear on it: provenance
  makes an answer auditable but does not make it correct, and under-declared change footprints are a
  recurring defect here. Hence the binding design rule D2 must **ship** rather than assert — applied
  through the recorded footprint-capturing path, file list taken from the edit, verified by a
  diagnostics re-run. **An edit nobody read must at minimum be an edit the parser re-checked.**
- **Sequencing.** No hard dependency. Coordinates with the resolver-configuration plan (config
  surface) and the derivation-resolver plan (which server binary, which language) — coordinate,
  never pair; they share a server and config surface. A sibling WS-06 plan wants this same client
  pointed at the **document corpus** rather than at code, where the addressable share is larger —
  so **build the client so a second consumer can reuse it**, rather than in a shape only
  `5-execute` can call.

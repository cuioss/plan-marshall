# PLAN-CIS-007: A Language-Server Surface Over the Skill Corpus

epic: code-intelligence-substrate
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

The operator's prioritised item: a language-server surface for the agent/skill layer, which no
external tooling provides. Expose the skill corpus's reference intelligence — go-to-definition on a
skill notation, find-references, broken-reference diagnostics, hover — through an editor-facing
protocol.

⭐ **This plan is deliberately RE-SCOPED from its original framing.** It was staged as building the
cross-file skill intelligence; that intelligence **already exists and works** in
`resolve-dependencies`. What remains is **presentation over an existing index**, not construction.
That is a materially smaller and lower-risk plan, and scoping it as greenfield would rebuild a
working engine.

## Deliverables

1. A protocol decision, recorded: true LSP (editor protocol) vs MCP surface vs skill wrapper — with
   the consumer need that decides it.
2. The server/surface itself, answering from the existing index: go-to-definition on
   `bundle:skill[:script]` notation, find-references, hover (skill description + frontmatter).
3. Live broken-reference diagnostics sourced from `validate`.
4. Configuration as **strictly opt-in**, with a documented no-op path when unconfigured.
5. **Documentation across all three trees.** `doc/user/` — installation and editor/client setup, the
   highest-value page here because this is the only deliverable in the epic an operator must
   actively wire up; it must state plainly that an unconfigured project loses nothing.
   `doc/concepts/` — where the language-server surface sits in the tier model (Tier 2, accelerator,
   never a prerequisite). `doc/developer/` — the protocol decision from deliverable 1 and its
   rationale, so the choice between LSP and MCP is not re-litigated later. ⛔ Ship docs **in this
   plan**.

## Claim Labels

- **OBSERVED (external absence, verified)**: no language server exists for the SKILL.md / agent-skill
  surface. The ecosystem ships only **file-local spec-conformance validators** — `skills-ref`
  (agentskills.io), `agent-skills-lint`, `skill-md-validator`, `skill-linter` — which check
  frontmatter fields, naming, and directory structure, i.e. what `plugin-doctor` already does.
- **OBSERVED (external inverse)**: the mature "LSP for agents" projects are the opposite direction —
  `agent-lsp` (MCP server orchestrating gopls/rust-analyzer/jdtls; 65 tools, 30 languages) and
  `lsp-skill` (LSAP) both **bridge ordinary CODE language servers to agents**, both require a
  per-language server installed, and both explicitly carry **no markdown/documentation support**.
  ⛔ **Do not rebuild these** — if per-language code intelligence is wanted, integrate them.
- **OBSERVED (internal presence)**: the cross-file skill intelligence already exists in
  `resolve-dependencies` — `deps`, `rdeps`, `tree`, `validate` over five edge types including
  AST-parsed Python imports — verified live returning real edges with line-number provenance.
- **HYPOTHESIS**: an editor protocol is the right surface at all. The consumers of this repo's
  intelligence are predominantly **agents**, not humans in an editor, and `agent-lsp` chose MCP over
  LSP for exactly that reason. Confirm/refute against the actual intended consumer before building
  (verify-at-outline). ⛔ **This is a genuine fork and it must reach the operator, not be decided
  inside the plan** — escalate rather than assume.
- **HYPOTHESIS**: the index is fast enough to answer interactively. `validate --scope marketplace`
  walks 294 components and 2467 dependencies; interactive latency was never measured. Confirm/refute
  by timing the existing verbs (verify-at-outline). ⚠ If it is not, an incremental/cached index
  becomes a deliverable and this plan must be re-scoped or split.
- **Verify-first clause**: the "no external skill-LSP exists" claim is an **asserted absence** and
  carries the higher verification burden. It was established by web research on 2026-07-29 and the
  ecosystem is moving fast — **re-verify at outline** before building. If one has appeared, evaluate
  integrating it before constructing one.

## Expected Surface

- **HYPOTHESIS**: a new skill under `marketplace/bundles/pm-plugin-development/skills/` — the server/surface (verify-at-outline; the operator's placement rule puts marketplace-domain tooling in this bundle)
- **OBSERVED**: `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/` — consumed as the index, NOT edited
- **HYPOTHESIS**: editor/client configuration surface — shape depends on deliverable 1 (verify-at-outline)
- **OBSERVED**: `test/pm-plugin-development/` — tests

## Dependencies and Sequencing

- **Depends on**: PLAN-CIS-006 (precision) — ⛔ **hard gate**. Surfacing a broken-reference set with a
  large false-positive share into an editor ships confident-wrong diagnostics at the
  highest-visibility surface this epic has.
- **Depends on**: PLAN-CIS-002 (LSP-shaped query API). ⭐ **This shrinks the plan a second time.** With the
  substrate already speaking `definition` / `references` / `hover` / `documentSymbol`, this plan
  becomes a thin protocol adapter over an LSP-shaped API rather than a translation layer. ⚠ If
  PLAN-CIS-002 is dropped or descopes to an additive facade, this plan **absorbs the translation work and
  must be re-scoped upward** — do not carry the "thin adapter" assumption past PLAN-CIS-002's landing.
- **Depends on**: PLAN-01 (inventory) — the index is blind to 130 files including 33 `workflow/`
  docs, where verb contracts live; find-references would return false negatives.
- ⚠ **The tier contract binds this plan's priority**: it is a **Tier 2 accelerator**, so it MUST NOT
  become a prerequisite for Tier 0 or Tier 1 correctness. Prioritising it does not reclassify it as
  load-bearing, and it must degrade to a clean no-op when unconfigured — the operator's binding
  constraint that an unconfigured project loses nothing.
- **Adjacent to**: PLAN-CIS-003's resolver consumes the same index but exposes it to `manage-architecture`
  rather than to an editor. Different surface, same substrate — a landing in either informs the other.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-007-skill-lsp-server.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

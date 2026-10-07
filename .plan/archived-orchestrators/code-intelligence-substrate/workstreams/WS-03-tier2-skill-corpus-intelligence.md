# WS-03: Tier 2 — Skill-Corpus Intelligence and the LSP Surface

epic: code-intelligence-substrate

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-03-tier2-skill-corpus-intelligence.md` and is tracked in the
> epic `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Tier 2 is the **optional accelerator** — pure upside, so a project that configures nothing loses
nothing. This workstream owns the agent-surface half of it: making the skill-corpus reference index
precise enough to gate on, and then exposing it through an editor-facing language-server surface.

⭐ **The scope of this workstream was cut in half by evidence.** The cross-file skill-corpus
intelligence was believed to need building; it already exists and works
(`pm-plugin-development:tools-marketplace-inventory:resolve-dependencies`). The remaining delta is
**precision plus presentation**, not construction.

## Scope

- **In scope**: the precision of `resolve-dependencies validate` (making it gate-ready), and the
  language-server presentation layer over the existing index — live diagnostics, hover,
  go-to-definition, find-references in-editor.
- **Out of scope**: the index and its derivation, which is WS-02's product; the files inventory
  underneath it, which is WS-01's (and a hard prerequisite); anything requiring a per-language code
  LSP — the external `agent-lsp` / `lsp-skill` bridges already serve that and are explicitly **not**
  rebuilt here.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-06-validate-precision | staged | 120 unresolved of 2467 is an OVERCOUNT — three false-positive classes make `validate` unusable as a gate |
| PLAN-07-skill-lsp-server | staged | The operator's prioritised item, **re-scoped**: presentation over an existing index, not greenfield intelligence |

## Sequencing and Surface Notes

- ⛔ **PLAN-06 MUST land before PLAN-07.** An LSP surfacing an index with a ~50% false-positive
  rate on broken references would ship confident-wrong diagnostics straight into the editor — the
  epic's own archetype, at the highest-visibility surface it has yet reached.
- ⛔ **PLAN-01 (WS-01) is a hard prerequisite for BOTH.** The index is blind to 130 files including
  33 `workflow/` docs; an LSP built on it reports false "no references" answers.
- ⛔ **PLAN-06 collides with PLAN-04 (WS-02) and PLAN-01 (WS-01)** on
  `tools-marketplace-inventory`. Never pair those three.
- ⚠ **The tier contract binds the priority**: prioritising PLAN-07 does NOT reclassify it as
  load-bearing. It is a Tier 2 accelerator for the agent surface and MUST NOT become a prerequisite
  for Tier 0 or Tier 1 correctness. The non-Maven zero-edge defect (WS-02) stays a consumer-facing
  obligation in its own right regardless of when the LSP ships.
- ⚠ **Open question for PLAN-07's outline**: whether the LSP is a true LSP server (editor protocol)
  or an MCP surface. The external precedent is split — `agent-lsp` chose MCP over LSP for agent
  consumption, `lsp-skill` chose a skill wrapper. Settle against actual consumer need before
  committing to a protocol.

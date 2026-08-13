# Run report — 302-the-terminal-report-is-a-machine-readable-emission-the-inbox-drains (run 01)

**Date (UTC):** 2026-08-13    **Branch:** claude/terminal-report-machine-readable-x35bc9    **PR:** (pending)    **Outcome:** in-progress

## Skills loaded

- `cloud-plan-lane` (working contract, loaded first)
- `plan-marshall:ref-code-quality` (always)
- `pm-plugin-development:plugin-script-architecture` (always)
- `plan-marshall:ref-workflow-architecture` (workflow docs / dispatch topology)
- `pm-plugin-development:plugin-architecture` (SKILL.md / bundle structure)
- `plan-marshall:persona-implementer` (production-code work identity)
- `pm-dev-python:python-core` + `pm-dev-python:pytest-testing` — loaded on-demand before writing Python

GitHub access path: GitHub MCP server (cloud session). Branch form: harness-assigned `claude/*` (kept as-is).

## Deliverables

### D0 — GATE (mutates nothing): re-derive the seam against HEAD

**Verdict: GATE PASSES. Plan 300 has landed; the reserved terminal slot exists.** All four required facts read by symbol at HEAD (308528d):

1. **300's slot exists — CONFIRMED.** The banded allocation contract landed as PR #1211 (`308528d feat(finalize): banded order-allocation contract + collision check (plan 300)`). `extension-api/standards/finalize-step-order-bands.md` § "The bands" declares the **Terminal emission** band **1000–1099**, "Shared bundle (reserved) … The single machine-readable terminal emission — the run's landing, emitted after every reporting step and before the archive move. Reserved; occupied by the terminal-emission step." `default:archive-plan` moved to the **Terminus** band at **1100** (declares `destroys: [plan-directory]`). The last reporting step is `default:finalize-step-print-phase-breakdown` at 999 / `default:record-metrics` at 998. So the reserved integer slot for a terminal step sits after the last reporting step (999) and before `archive-plan` (1100) — the plan takes **order 1000** (1001–1099 stays reserved for a future co-terminal step per the band doc). Also confirmed by `_manifest_core.py` DEFAULT_PHASE_6_STEPS comment (lines 276-296): "The reserved terminal-emission band (1000-1099) sits below it".

2. **The typed facts map exists WITH both-direction guards — CONFIRMED. ⭐ D4 is ROUTING, not modelling.** `ext-point-finalize-step.md` § "Structured step facts (`records_facts`)" defines the `records_facts: list[str]` frontmatter field and the `mark-step-done --fact KEY=VALUE` persistence. Both directions are guarded: **∃-direction** ("No orphan declaration — every declared key MUST be recorded by at least one terminal call site") and **∀-direction** ("No undeclared record — every `--fact {key}=` wired at any terminal call site MUST appear in that doc's `records_facts` declaration"). A conformance test asserts these two and no third scope.

3. **The report renders from PROSE (`display_detail`), not from the facts map — CONFIRMED.** `phase-6-finalize/standards/output-template.md` line 5: "The renderer is a pure assembler: it never invents per-step content. Each finalize step authors its own one-line `display_detail` string at `mark-step-done` time; the renderer only concatenates those strings." Line 88: "All remaining `{...}` values come verbatim from each step's `display_detail`." Snapshot Procedure step 1 reads `metadata.phase_steps["6-finalize"]` = `{step_name: {outcome, display_detail}}` — the typed `facts` map is discarded at this render boundary. **This is the OPERATOR report channel; it is out of D4's routing scope — see the note below.**

4. **The plan's `source_id` IS available at COMPOSE time — CONFIRMED. D2 is a compose-time decision.** `_orchestrator_inbox.classify_source_id` (plan-orchestrator) is a PURE classifier of `request.md`'s already-persisted `source_id` string — "no filesystem access and no second detector." It returns `SourceIdClassification(orchestrated, epic, plan_spec, detection)` over the closed `DETECTION_TOKENS` vocabulary. The composer (`manage-execution-manifest compose`, `cmd_compose`) receives `--plan-id` and reads freely from the plan directory (marshal.json / status.json / tasks / references); it does **not** currently read `source_id` (grep: zero `source_id` matches in `manage-execution-manifest`), but `request.md` (written by phase-1-init, which precedes phase-4-plan compose) is on disk and reachable by plan-id. So the compose path CAN classify `source_id` and compose the terminal step OUT observably (a decision-log-emitting pre-filter, exactly like the existing `_apply_commit_push_disabled` / `_apply_simplify_inactive`).

**Current landing emission (the thing D1 relocates):** The `kind: landing` inbox message is emitted today **inside `lessons-capture` (order 991)** — `phase-6-finalize/workflow/lessons-capture.md` line 82: "Exactly one `kind: landing` message per orchestrated finalize run, emitted unconditionally." The dispatcher resolves `orchestrated` at RUNTIME (phase-6-finalize SKILL Step 3 item 4b.a0) via `manage-plan-documents request read --section source_id` then `orchestrator inbox detect` (which calls `classify_source_id`). `finalize-step-preference-emitter` (992) emits `candidate-lesson` messages but NO landing. This matches the plan's Problem B exactly ("The landing emission sits inside a finalize step at order: 991").

**Scope clarification (D4 target):** D4 routes typed facts into the **terminal INBOX emission** (the `kind: landing` message drained by the orchestrator), NOT into the operator `output-template.md` report. The operator report rendering from prose (finding 3) is the *evidence* that the two channels differ (Problem A); D4 fixes the inbox channel by carrying typed facts in the landing payload rather than narrative. Confirmed the plan's framing: "The emission is a ROUTING gap … the typed facts already exist; nothing routes them to a drainable channel."

## Build gate

(pending)

## Findings

(pending — verification sub-agent, CI, PR review)

## Reviewer participation

(pending)

## Cost

(pending)

## Contract check (Step 9)

(pending)

## What have we learned (Step 9)

(pending)

## Residue

(pending)

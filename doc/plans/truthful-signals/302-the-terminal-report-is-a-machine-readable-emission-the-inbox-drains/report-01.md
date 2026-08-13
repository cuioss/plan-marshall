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

### Design (post-D0, drives D1-D5)

- **New terminal step `default:emit-landing`** — inline (modeled on `finalize-step-preference-emitter`), `standards/emit-landing.md`, `order: 1000`, `default_on: true`, `mutates_source: false`, `post_run_review: true`, `presets: [local, standard, full]`. Reads per-step facts via `manage-status read`, assembles a machine-readable landing payload (fenced ` ```landing-facts ` block + narrative residue), writes it via `orchestrator inbox write --kind landing`. Runs after `record-metrics` (998) so it carries token totals; before `archive-plan` (1100). (D1/D4)
- **lessons-capture loses the landing.** Branch B4 emits only `candidate-lesson` messages now; the `kind: landing` emission moves to emit-landing. The three-zero short-circuit **orchestration carve-out is removed** — it existed solely to emit the landing at zero signals; with the landing gone, lessons-capture skips at zero signals regardless of orchestration. The a0 orchestration resolution stays (candidate-lesson routing still needs it) and adds emit-landing as a 4th consumer. (D1)
- **record-metrics gains `records_facts`** — wires its already-computed `total_tokens`/`total_wall_seconds`/`any_phase_missing_end_time` as `--fact` so the landing can carry token totals as machine-readable facts (the "already computed, discarded at the record boundary" routing fix the ext-point doc names for sonar's scan facts). (D4)
- **D2 compose gate** — new pre-filter in `manage-execution-manifest.cmd_compose` reads `source_id` from `request.md` (via `parse_document_sections`), classifies via imported `classify_source_id` (the single sanctioned detector — no second detector, no new persisted field), and drops `emit-landing` for non-orchestrated plans with a `[STATUS]` decision-log line (observable). (D2)
- **D3 payload spec** — new `plan-orchestrator/standards/landing-payload-spec.md`: the report↔inbox delta, seven findings classified MECHANISABLE/NARRATIVE-ONLY, and the required machine-readable landing fact keys (the shared contract D4 emits and D5 validates). (D3)
- **D5 completeness check** — `check_landing_completeness(payload_body) -> (complete, missing_keys)` in `_orchestrator_inbox.py` + `orchestrator inbox landing-check` verb, wired into `analyze.md`'s landing drain. Test feeds a pre-fix prose-only landing (FAILS — no facts block) and a post-fix facts landing (PASSES). (D5)

### D1 — A dedicated terminal step, in the slot D0 confirmed — DONE

New `phase-6-finalize/standards/emit-landing.md` (`default:emit-landing`, `order: 1000`, inline, `default_on: true`, `mutates_source: false`, `post_run_review: true`, `presets: [local, standard, full]`). It reads per-step facts and assembles the machine-readable landing, and is the last thing before `archive-plan` (1100). Only the emission moved: `lessons-capture` (991) keeps its candidate-lesson stream; its Branch B4 no longer emits the landing, and its three-zero short-circuit carve-out (which existed solely to emit the landing at zero signals) is removed. Wired into: DEFAULT dispatch table (SKILL.md), ext-point Current Implementations table (25→26), and the item-4b.a0 orchestration-verdict consumer list (three→four steps). Commit `249a2d7`. Verified by the discovery-driven routing tests (dispatch-table set equality, no-order-collision, post-run-review ordering) which now include emit-landing automatically.

### D2 — The step exists ONLY under an orchestrator — DONE

New compose-time pre-filter `_apply_terminal_emission_orchestration_gate` in `manage-execution-manifest.cmd_compose`: reads `request.md`'s `source_id`, classifies via the imported `classify_source_id` (the single sanctioned detector — no second detector, no new persisted field), and drops `emit-landing` for a non-orchestrated plan, reporting the drop as a `{step, reason}` record (the shared subtraction convention) that surfaces as a `[STATUS]` decision-log line and `terminal_emission_dropped` in the compose result — an OBSERVABLE compose-time decision. `emit-landing` is default-on via discovery (not added to the `DEFAULT_PHASE_6_STEPS` CSV fallback — that tuple already omits several default_on steps, and the fallback path cannot determine orchestration; documented in the tuple comment). Commit `249a2d7`. Verified by `test_terminal_emission_gate.py` (compose a non-orchestrated plan → step absent + why; orchestrated → kept) and registered in `test_subtraction_visibility_population.py` (the no-silent-drop conformance sweep).

### D3 — Derive the report↔inbox DELTA, in both directions — DONE

New `plan-orchestrator/standards/landing-payload-spec.md`: the set difference between the report render schema (`output-template.md`) and the inbox envelope schema, with each item classified MECHANISABLE or NARRATIVE-ONLY, and the seven known findings as the non-empty control. Two of the seven are irreducibly NARRATIVE-ONLY: the false-merge report (#4, "arrived as operator narrative, not a step fact" — the item the plan flags as maybe-not-mechanisable) and the review-bot withdrawal (#7). The delta IS the required-fact-key set the payload carries. The `.plan/` empirical "over three archived plans" sample is stated as unreachable from this clone, not claimed. Commit `249a2d7`. Verified by `TestPayloadSpecDoc` (names both classes, carries the seven-finding control, keeps false-merge narrative-only).

### D4 — The terminal emission carries the facts, machine-readable — DONE

The landing body carries a fenced `landing-facts` block (`schema=landing-facts/1` + required keys) consuming the existing typed facts map (`records_facts` / `mark-step-done --fact`) rather than prose — a ROUTING fix, confirmed by D0 that the map exists with both-direction guards. `record-metrics` wires its already-computed `total_tokens`/`total_wall_seconds`/`any_phase_missing_end_time` as `--fact` (routing, not modelling; ext-point Declared-obligations table updated). Verified the report renders from `display_detail` prose (D0 finding 3), so routing facts into the landing changes the inbox channel, not the operator report. Commit `249a2d7`. Verified by `test_step_records_facts_contract.py` (record-metrics both-direction guard passes).

### D5 — A drain-completeness check, and retire the workaround — DONE

`check_landing_completeness(payload_body) -> (complete, missing_keys)` + `orchestrator inbox landing-check` verb in `_orchestrator_inbox.py`/`orchestrator.py`, wired into `analyze.md`'s landing drain (records incomplete landings as Open Defects; `landings_incomplete` counter; a zero-drain with zero incomplete landings establishes nothing material outstanding). **SEEN to FAIL on a known-incomplete input**: a pre-fix prose-only landing has no `landing-facts` block → the check reports every required key missing (pinned by `TestSeenToFailOnPreFixLanding.test_pre_fix_prose_landing_is_reported_incomplete` and the end-to-end CLI test). **Manual-paste retirement:** the mechanisable delta is now drained as facts, so a paste stops yielding the mechanisable findings; the irreducibly-narrative residue (false-merge contradiction #4, bot withdrawal #7, and any producer-gap the run could not mechanise) rides the landing's `## Residue` section and correctly keeps a manual channel. Commit `249a2d7` (plus the gate-reshape follow-up commit).

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` verdict: **Python changed** (composer, orchestrator scripts, tests) → the full path applies. `./pw verify` (quality-gate + full test suite) — result recorded below once it completes. `./pw quality-gate` already GREEN (mypy 396 files clean, ruff clean, SPDX clean, plugin-doctor 0 issues). Targeted test run: the three touched dirs (phase-6-finalize, plan-orchestrator, manage-execution-manifest) — 2048 passed + the plan-302 tests green after the subtraction-visibility registration and the gate return-shape reshape.

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

# PLAN-LB-45: Every plan records the harness, model, effort and plan-marshall version it ran under

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-45-runtime-stamp.md` and is queued as one row file, `queue/PLAN-LB-45.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the Open Defect "Zero tokens is recorded as a real number and no plan records its harness" (`lessons-routing-013.md`, recurrence `lessons-routing-028.md` item 148). This spec covers the record of who ran the plan. The zero-token half and the first preflight call on the plan start path stay with PLAN-LB-39 D5. This plan extends that work and does not repeat it.

## Objective

A plan's records cannot show which harness, model, effort level or plan-marshall version ran it.

- `runtime-info` reads model and effort only from environment variables that no harness sets, and its CLI accepts no arguments. A live call at this checkout returned only `harness: claude` and `build_version: "0.1"`.
- The version it reports is the marketplace manifest's `0.1`, not the installed bundle (`0.1.1919`) and not the executor (`0.1.1916`).
- The harness is resolved, but how it was resolved is dropped, so a fallback `claude` cannot be told from a detected one.

This plan makes `client.toon`, the plan metadata and the landing-facts block carry all four values, each with its source. They become required landing keys, and `unknown` stands only for a value that could not be read.

## Deliverables

1. **`runtime-info` accepts self-reported model and effort, and tags every value with its source.**
   - The `runtime-info` operation gains optional `--model` and `--effort` flags, passed through to the existing overrides of `collect_runtime_info`.
   - Each value is recorded with `model_source` / `effort_source`:
     - `self_reported` when it came from a flag;
     - `measured` when it came from a script-readable source (the environment lists stay as that source);
     - absent when neither applies.
   - Nothing is estimated.

   *Done when:* `platform_runtime runtime-info --model claude-opus-5-5 --effort high` returns `model: claude-opus-5-5`, `model_source: self_reported`, `effort: high`, `effort_source: self_reported`. A call with no flags and no environment variables returns neither key. At HEAD the first call is an argparse rejection (exit 2).

2. **The plan-marshall version is the installed bundle and executor version, not the marketplace manifest.**
   - `runtime-info` reports `bundle_version` — the `version` in `.claude-plugin/plugin.json` of the bundle the collector is running from — and `executor_version` (`MARSHALL_VERSION`, read through `plugin_registry.read_executor_version`).
   - It replaces the `build_version` reading of `.claude-plugin/marketplace.json` `metadata.version`.
   - The shared `plugin_registry` reader is reused. No second parser is written.

   *Done when:* a fixture bundle with `plugin.json` version `0.1.1919` and an executor with `MARSHALL_VERSION = '0.1.1916'` yields both values. An unreadable executor yields `executor_version` absent, never `0.1`. At HEAD the fixture yields `build_version: "0.1"`.

3. **The harness carries the tier that produced it, and a mismatch is reported.**
   - `runtime-info` adds `harness_source` (`env` / `local_config` / `fallback`) and the fallback `reason`, both from `target_context.resolve_target`.
   - When the environment tier and the machine-local configuration name different targets, it adds `harness_configured` and `harness_mismatch: true`.
   - The stale statements that the target comes from `marshal.json` are corrected in the router docstring and in `runtime-info.md`.

   *Done when:*
   - With `OPENCODE=1` set and a local config naming `claude`: the output is `harness: opencode`, `harness_source: env`, `harness_mismatch: true`.
   - With no signal at all: the output is `harness_source: fallback` plus its reason.

   At HEAD neither field exists.

4. **The plan start path records all four values.**
   - Building on PLAN-LB-39 D5's `phase-1-init` preflight call: `orchestrator preflight` forwards self-reported `--model` / `--effort` to `runtime-info`.
   - The `phase-1-init` call passes the values the executing LLM reports about itself.
   - The `harness` field PLAN-LB-39 adds to plan `status.json` metadata is extended with `harness_source`, `model`, `effort`, `bundle_version` and `executor_version`.

   *Done when:* a fresh fixture plan started through the documented call has a `client.toon` entry and status metadata carrying all of the above with their source tags. A preflight call without the flags still writes the entry, with the model and effort keys absent.

5. **The landing-facts block requires the four values.**
   - `harness`, `model`, `effort` and `plugin_version` (bundle version, with the executor version in an optional `executor_version`) become required keys in `landing-payload-spec.md`, in `LANDING_REQUIRED_KEYS` in `_orchestrator_inbox.py`, and in what `emit-landing.md` writes.
   - `emit-landing` reads them from the plan metadata.
   - An unreadable value is written as `unknown`, which the existing could-not-read rule reports as incomplete.

   *Done when:* `landing-check` on a block missing any of the four reports it missing; a block carrying all four is complete; a block with `model=unknown` is reported incomplete. At HEAD a block without them is complete.

Split guard: five deliverables on one chain — collector, start path, landing. No split.

## Claim Labels

- OBSERVED: `runtime_info.py` reads model name/type/version and effort only from `_MODEL_NAME_ENV` … `_EFFORT_ENV` (L54-79): `CLAUDE_CODE_MODEL`, `ANTHROPIC_MODEL`, `OPENCODE_MODEL`, `PLAN_MARSHALL_EFFORT` and others. `collect_runtime_info` (L191-239) already accepts explicit overrides. Read at `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_info.py`.
- OBSERVED: the router's `runtime-info` parser declares no flag (`p.parse_args(remaining)` then `runtime.runtime_info()`), so the overrides cannot be reached from the CLI — `platform_runtime.py` L777-780. `runtime-info.md:22` says "Takes no arguments".
- OBSERVED: a live `platform_runtime runtime-info` at this checkout returned `harness: claude` and `build_version: "0.1"` and nothing else.
- OBSERVED: `read_build_version` reads `.claude-plugin/marketplace.json` → `metadata.version` (`runtime_info.py` L139-188). The installed `~/.claude/plugins/cache/plan-marshall/plan-marshall/0.1.1919/.claude-plugin/plugin.json` carries `"version": "0.1.1919"`; the source `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json` carries `"0.1"`.
- OBSERVED: `plugin_registry.read_executor_version` (L224-246) and `read_registry` (L142-175) exist, use only the standard library, and are already imported by `plan-orchestrator/scripts/orchestrator.py` (restart-check `registry_parity`) — read at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/plugin_registry.py`.
- OBSERVED (corrects the premise this plan was raised on): the router does not take the target from `marshal.json`. `main()` resolves it through `target_context.resolve_target` (`platform_runtime.py` L865-869). The environment tier comes first: `ANTIGRAVITY_AGENT` → antigravity, `OPENCODE`/`OPENCODE_PID` → opencode, `CLAUDE_CODE_SESSION_ID` → claude (`target_context.py` L145-171). Then `.plan/local/harness/*.json` or `.plan/run-configuration.json`, then the fallback `claude` (L248-282). `marshal.json` is read only as an existence check (L854-863). The router docstring (L4-5, L40-42) and `runtime-info.md:22-24` still say the target comes from `marshal.json`.
- OBSERVED: `resolve_target` returns `target_source` and `reason`, but `runtime-info` emits only `harness`, so a fallback is indistinguishable from detection — `target_context.py` L104-115, L248-282.
- HYPOTHESIS: each harness puts its signal into the environment of a Bash subprocess (OpenCode `OPENCODE` / `OPENCODE_PID`, Antigravity `ANTIGRAVITY_AGENT`, Claude Code `CLAUDE_CODE_SESSION_ID`) — confirm at `target_context.detect_target_from_env` with one live call per harness, or against `platform-runtime/standards/contract.md` (verify-at-outline).
- HYPOTHESIS: the machine-local harness file is written by `marshall-steward/scripts/configure_harness.py` — confirm there (verify-at-outline).
- OBSERVED: `plan-orchestrator/workflow/preflight.md` Step 1 calls `orchestrator preflight --plan-id {plan_id}` only (L24-29).
- OBSERVED: the required landing keys are `schema`, `plan_id`, `pr`, `merge_state`, `cleanup_owed`, `deliverables_total`, `deliverables_done`, `total_tokens` and `steps` — `plan-orchestrator/standards/landing-payload-spec.md` L82-99, enforced by `LANDING_REQUIRED_KEYS` in `plan-orchestrator/scripts/_orchestrator_inbox.py`.
- OBSERVED: `unknown` at any required key is incomplete ("could-not-read class") — `landing-payload-spec.md` L119-123.
- OBSERVED: PLAN-LB-39 D5 (running) adds the `phase-1-init` preflight call, a `harness` field in plan `status.json` metadata, and an OPTIONAL `harness=` landing key — read at `plans/PLAN-LB-39-antigravity-execution-fidelity.md`.
- Verify-first clause: rebase onto PLAN-LB-39's landing before outlining deliverables 4 and 5. Extend its `harness` field and its landing key; do not add a second preflight call or a second metadata key. If PLAN-LB-39 has not landed, stop after deliverables 1-3 and report.
- Verify-first clause: making the four keys required makes every landing emitted before this change incomplete. The operator asked for that. State it in the PR and do not add a grandfather rule.
- Verify-first clause: the model value is self-reported by the executing LLM. Record it as `self_reported`, never as `measured`.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_info.py` — overrides, source tags, version readers (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/platform_runtime.py` — `runtime-info` parser flags, docstring (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/runtime-info.md` (D1, D2, D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md` — only if it states the `runtime-info` argument surface (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_claude_runtime_impl.py`, `opencode_runtime.py`, `antigravity_runtime.py` — only if `runtime_info()` must take the new arguments through the base class (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — `preflight` forwarding (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/preflight.md` (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md` — the PLAN-LB-39 preflight call gains the self-report (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py` — `LANDING_REQUIRED_KEYS` (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md` (D5)
- OBSERVED: `test/plan-marshall/platform-runtime/test_runtime_info.py` (D1, D2, D3)
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_preflight_client_toon.py` (D4)
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_landing_completeness.py` (D5)
- HYPOTHESIS: `test/plan-marshall/script-shared/test_target_context.py` — only if the mismatch probe adds a helper in `target_context.py` (verify-at-outline)

## Dependencies and Sequencing

- Depends on: PLAN-LB-39 (running) — D5 adds the preflight call, the `harness` metadata field and the optional `harness=` landing key that deliverables 4 and 5 extend.
- Overlaps with:
  - PLAN-LB-39 on `phase-1-init/SKILL.md`, `landing-payload-spec.md`, `emit-landing.md` and the `test/plan-marshall/platform-runtime/` directory. Possibly also `platform-runtime/standards/contract.md` and the runtime classes.
  - None of the other four candidates in this batch shares a file. `consumer-leaf-workflow-resolution` reads platform-runtime `layout bundle-cache-root` but does not edit `platform_runtime.py`.
- Adjacent to:
  - `manage-metrics` and the `total_tokens=0` producer (PLAN-LB-39 D5) — not touched here.
  - The orchestrator restart check's `registry_parity` — reused as a reader, not changed.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-45-runtime-stamp.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

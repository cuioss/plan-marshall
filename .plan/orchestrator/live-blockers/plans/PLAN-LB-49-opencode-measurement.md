# PLAN-LB-49: OpenCode plans report their real tokens and sub-agent dispatches

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-49-opencode-measurement.md` and is queued as one row file, `queue/PLAN-LB-49.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from § Non-Claude-Code Failures "OpenCode: no token measurement exists at all" and the
> Open Defect recurrence "Eighth landing: PLAN-LB-26 (OpenCode)" (dispatch audit "0 dispatched"
> against 77 sub-agent sessions). The zero-versus-`unknown` half is PLAN-LB-39 D5 and is not
> repeated here.

## Objective

Every OpenCode landing reports `total_tokens=0`, and the retrospective's dispatch audit reports no
dispatches. Both rest on a premise that is no longer true: that OpenCode gives the shell no session
id and keeps no transcript. OpenCode 2 sets `OPENCODE_SESSION_ID` in every shell-tool subprocess
and keeps each session in `~/.local/share/opencode/opencode.db` — session totals, sub-agent sessions
linked to their parent, and token use per message. PLAN-LB-26's two root sessions and their 77
sub-agent sessions hold 55.0M input tokens and $7.54.

This plan adds one read-only reader for that database, captures the session id, serves the
existing `metrics normalized-tokens` operation from the database (so `manage-metrics enrich` fills
the phase rows without a change of its own), and lets the dispatch audit count the sub-agent
sessions OpenCode records.

## Deliverables

1. **One read-only OpenCode session reader.**
   - A module in `platform-runtime/scripts/` opens the database with `mode=ro`, located through
     `OPENCODE_DB`, else `$XDG_DATA_HOME/opencode/opencode.db`, else
     `~/.local/share/opencode/opencode.db`, and checks the schema it needs (`session_v2` with
     `parent_id`, `directory` and the `tokens_*` / `cost` columns; `session_message` with `type`,
     `time_created`, `data`).
   - It provides root resolution through `parent_id`; totals over a session and all descendants;
     per-window sums of assistant-message `tokens` / `cost`, split main versus sub-agent; and the
     list of sub-agent sessions with the `name:` / `plan_id:` header of their first prompt.
   - A missing database or unsupported schema returns a named reason, never a zero.

   *Done when:* fixture-database tests cover each function and the reasons `opencode_db_absent` and
   `opencode_db_schema_unsupported`. At `501aeb313` no such module exists.

2. **OpenCode captures and binds its session identity.**
   - `session capture` reads `OPENCODE_SESSION_ID`, resolves it to the root session, and appends
     the root to `status.metadata.session_ids` through the same manage-status store the Claude
     runtime uses; `session bind` and `session resolve-plan` do the same.
   - The "#9292 / no session id" statements in the module docstring and methods are corrected; an
     unset variable keeps today's `no-op`.

   *Done when:* with the variable set to a fixture child session, capture stores the fixture root
   id; unset, it returns `no-op`. At `501aeb313` it is always `no-op`.

3. **`metrics normalized-tokens` on OpenCode returns per-phase buckets from the database.**
   - For each phase window: the four usage fields (input, output, cache_read, cache_creation) plus
     `subagent_total_tokens`, `subagent_samples` and the message count, covering every root session
     the plan captured (the verify-first clause settles how those roots reach the operation).
   - `manage-metrics enrich` and the finalize `record-metrics` step work unchanged.

   *Done when:* a fixture database with one root, two sub-agent sessions and two windows makes
   `enrich` persist exact per-phase figures and `generate` report a non-zero total; a second
   captured root is included. At `501aeb313` the operation returns `transcript_not_found`.

4. **The dispatch audit counts OpenCode's sub-agent sessions.**
   - On the OpenCode target, `check-dispatch-audit.py` adds a harness-observed source counting the
     sub-agent sessions of the plan's captured roots whose first prompt carries `plan_id: {plan_id}`,
     reports `harness_observed_dispatches`, and raises a channel-completeness finding when there are
     fewer `[DISPATCH]` lines than that count — instead of a bare "0 dispatched".

   *Done when:* a fixture database with N matching sub-agent sessions and an empty work log yields
   `harness_observed_dispatches: N` and the gap finding. At `501aeb313` the audit reports 0.

Split guard: four deliverables, one source (the database) read by three consumers. The enforcement
half is PLAN-LB-48.

## Claim Labels

- OBSERVED: the OpenCode 2.0.28 shell tool sets `AGENT="1"`, `OPENCODE="1"`, `AI_AGENT||="opencode"` and `OPENCODE_SESSION_ID=<sessionID>` in each command's environment, and no `OPENCODE_PID` — read in the binary at the shell tool's `execute`.
- HYPOTHESIS: a sub-agent's shell gets the sub-agent's own session id, which the reader resolves to its root — confirm with one live env read inside a dispatched leaf (verify-at-outline).
- OBSERVED: `opencode.db` schema: `session_v2(id, project_id, parent_id, directory, title, version, agent, model, cost, tokens_input, tokens_output, tokens_reasoning, tokens_cache_read, tokens_cache_write, time_created, time_updated, …)`, indexed on `parent_id`; `session_message(session_id, type, seq, time_created, data)`, assistant `data` carrying `tokens{input,output,reasoning,cache{read,write}}` and `cost`; a `location-switched` message records each session's move into a worktree.
- OBSERVED: PLAN-LB-26 totals: main session `ses_ec99635dbffewFspW7ypqPPJCr` and its 74 sub-agent sessions 52.53M input, 0.79M output, 799.7M cache-read, $7.16; resumed session `ses_ec62f10b9ffe3HUmW2lsFp0m1n` and its 3 sub-agent sessions 2.50M input, 40.3K output, $0.37. Per-message sums match `session_v2` totals within an in-flight delta. Titles are not a key (the resumed session is titled "Implementing PLAN-LB-39 …").
- OBSERVED: `opencode_runtime.py` is a no-op on every token and session path: `session_capture` (`:399-411`), `metrics_capture` (`:1109-1151`, declining an explicit count too), `metrics_normalized_tokens` (`:1153-1180`), `chat_extract_signal` (`:1182-1205`).
- OBSERVED: the existing plumbing needs no change once the operation answers: `phase-6-finalize/SKILL.md` § "How to obtain session_id" takes the last entry of `status.metadata.session_ids`; `record-metrics.md` passes it to `manage-metrics enrich`; `cmd_enrich` (`manage-metrics.py:3899-3952`) forwards it to the runtime operation; the `no_session_id_transcript_less` skip (`:3845-3927`) fires only when no session id is passed.
- OBSERVED: `check-dispatch-audit.py` reads only `logs/work.log` (`[DISPATCH]`) and `logs/decision.log` (`effort resolve-target`), at `:105-106` and `:1273-1274`. A dispatched OpenCode sub-agent's first prompt starts "You are a subagent spawned by another session.\nname: {name}\nplan_id: {plan_id}".
- HYPOTHESIS: `claude_runtime._manage_status_store_session` is target-independent and reusable — confirm at `platform-runtime/scripts/claude_runtime.py` (verify-at-outline).
- Locating a plan's sessions after the fact (evidence for the outline): roots are `SELECT DISTINCT session_id FROM session_message WHERE type='location-switched' AND json_extract(data,'$.location.directory') = :abs_worktree` plus `session_v2.parent_id IS NULL AND directory = :abs_worktree`; sub-agents are `parent_id IN roots`. For PLAN-LB-26 this yields exactly the two roots and 77 sub-agent sessions. Totals over a tree: a recursive CTE over `parent_id` summing `tokens_*` and `cost`.
- Verify-first clause (deliverable 3): how the operation sees every root session of the plan — (a) the `session_binding` reverse index after deliverable 2 binds each root; (b) all roots whose `location-switched` directory equals the given root's; (c) forwarding the whole `session_ids` list, which edits `manage-metrics.py` and `phase-6-finalize/SKILL.md` — choose only after PLAN-LB-39 D5 lands, and coordinate. Prefer (a); record the choice.
- Verify-first clause: an absent database must follow PLAN-LB-39 D5's `unknown` rule. Rebase onto LB-39's landing before outlining deliverable 3.

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_opencode_sessions.py` — new reader (verify-at-outline) (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — `session_capture`, `session_bind`, `session_resolve_plan`, `metrics_normalized_tokens` (D2, D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py` — only if the store helper moves to a shared home (verify-at-outline) (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/session_binding.py` — only if option (a) needs a reverse read (verify-at-outline) (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md` — OpenCode session and metrics rows (verify-at-outline) (D2, D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/no-op-policy.md` — OpenCode no-op list (verify-at-outline) (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-dispatch-audit.py` (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/standards/execution-context-dispatch-audit.md` (D4)
- HYPOTHESIS: `test/plan-marshall/platform-runtime/test_opencode_sessions.py` — new (verify-at-outline) (D1)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_runtime.py` (D2, D3)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_degrade_paths.py` (D2, D3)
- OBSERVED: `test/plan-marshall/plan-retrospective/test_check_dispatch_audit.py` (D4)
- HYPOTHESIS: `test/plan-marshall/manage-metrics/test_manage_metrics_enrich.py` — end-to-end enrich fixture only (verify-at-outline) (D3)

## Dependencies and Sequencing

- Depends on: PLAN-LB-39 (running) — D5 owns `unknown` versus `0` and the `transcripts:`
  capability flag; PLAN-LB-48 — shares `opencode_runtime.py` and `test_opencode_runtime.py`, lands
  first.
- Overlaps with: PLAN-LB-39 on `platform-runtime/standards/contract.md` and the
  `test/plan-marshall/platform-runtime/` directory (this plan does not edit `manage-metrics.py`
  unless option (c) is chosen); PLAN-LB-45 (staged) on its HYPOTHESIS `opencode_runtime.py` and the
  `test/plan-marshall/platform-runtime/` directory — PLAN-LB-45's model/effort/harness stamp can
  read `model` from the same database once this lands; PLAN-LB-43 / PLAN-LB-47: none.
- Adjacent to: `chat_extract_signal` and `metrics_capture`'s explicit count (left as no-ops); the
  general "Dispatch-boundary rows carry no step id" defect (every harness, not absorbed); the
  metrics re-entry accounting defect (not touched).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-49-opencode-measurement.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

# PLAN-LB-86: OpenCode measurement reports what the store holds — tool use, reasoning, cost, the plan's whole spend, and the phase it was spent in

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-86-lb-49-completion.md` and is queued as one row file, `queue/PLAN-LB-86.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-49 (#1833, `3baf825e4`),
> `landings/PLAN-LB-49.md` § Code defects. Priority is **high**: PLAN-LB-49 gave OpenCode plans a measurement
> for the first time, and the figures it records are the yardstick this epic judges every later plan by.
> It records a measured `0` for something it never measured, drops reasoning and cost, and states a landing
> total that is 63% of the plan's input and output. **Each deliverable is its own outline deliverable, and each
> Done-when is its own success criterion. Do not merge them.** A Done-when says "fails at `3baf825e4`" only
> where the behaviour is new at that sha; a clause that already holds says "holds at `3baf825e4`". A Done-when
> is never labelled "holds at" while a claim it rests on is still a HYPOTHESIS below.

## Objective

An OpenCode landing says what the plan cost. After PLAN-LB-49 it says a number, and the number is not the cost:
`subagent_tool_uses` is `0` in every phase of the plan that shipped the reader, reasoning tokens and cost are read
by the reader and never reach a consumer, the landing's `total_tokens` sums the sub-agent spend of five phases
with the main-context spend of one, and the phase that finalize work is booked to depends on the plan's last
phase window rather than on when the work happened. This plan makes each of those figures either the store's
number or an explicit gap, and makes the test that guards the reader able to fail on the store's real shape.

## Deliverables

1. **The reader counts tool use where the store keeps it, and carries reasoning and cost.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - Tool use is counted from the assistant messages' `content[]` parts whose `type` is `tool`, not from a
     `session_message` row whose type contains "tool" (`_opencode_sessions.py` L105, L793-794 look for a row
     type the store does not have). Where the store cannot answer, the group is OMITTED, never `0`.
   - `tokens.reasoning` is read and reaches the normalized buckets; decide at outline whether it is its own
     field or folded into `output_tokens`, after checking whether OpenCode's `tokens.output` already includes
     it (the store's `session_v2` keeps a separate `tokens_reasoning` column), and record why.
   - The per-bucket `cost` the reader sums reaches the operation's output (`_per_phase_buckets`,
     `opencode_runtime.py` L128-202 drops it), and `billing_weighted_total` does not apply Claude cache weights
     to a model they were not written for: it is omitted for such a model, or priced from the store's cost;
     decide at outline.
   - `subagent_duration_ms` is the summed duration of the sub-agent sessions' own spans inside the window, not
     the first-to-last span over all of them (`_opencode_sessions.py` L795-796): a 20.9-hour figure for a phase
     whose sub-agents ran minutes each is not a duration.
   - The contract text `runtime_base.py` rewrote for PLAN-LB-49 ("a target that emits a phase bucket MUST carry
     the full counter key set" became "groups may be omitted") is restored or the new rule is stated with the
     reason an omitted group is distinguishable from a zero.

   *Done when:* each of these fails at `3baf825e4`:
   - a fixture database whose assistant messages carry `content[]` tool parts (the shape the store has)
     yields the exact count, and one with no such parts yields no `tool_uses` key, not `0`;
   - a fixture message with reasoning tokens yields them in the answer;
   - a fixture message with a cost yields the summed cost in the answer;
   - two sub-agent sessions of one window with disjoint spans yield the sum of their spans, not the outer span;
   - the contract test names the rule that distinguishes an omitted group from a zero.

2. **The landing's `total_tokens` states its population and equals what the store holds for it.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `record-metrics` does not sum a phase's sub-agent figure for some phases and its main-context figure for
     others (`total_tokens_population: inline | mixed`, `tokens_cell_source` in `work/metrics.toon`). The total
     is main plus sub-agent for every phase, or the landing names the population it sums; decide at outline
     which and record why. The PLAN-LB-49 run's total, 16,614,516, is the sub-agent input plus output of phases
     2 to 6 plus the main-context figure of phase 1 — 63% of the store's 26,338,572 input plus output.
   - `metrics.md` does not label a phase "(inline) — this phase dispatched nothing" when it dispatched
     (`subagent_samples` 3, 2 and 3 for phases 2 to 4 of that run).
   - The run counter `four_field_phases_attributed` counts distinct phases, not attributions (it read 7 for
     six phases).

   *Done when:* each of these fails at `3baf825e4`:
   - a fixture plan with main-context usage in phase 3 and sub-agent usage in phase 3 totals both;
   - a phase with `subagent_samples > 0` is never labelled as having dispatched nothing;
   - a run with a re-entered phase reports a distinct-phase count that equals the number of phases.

3. **A phase that is re-entered is measured per interval.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `_phase_window_lookup` (`manage-metrics.py` L3793-3811) emits one window per phase, from the phase's first
     start to its last end. A plan that went 5-execute, 6-finalize, 5-execute, 6-finalize books the finalize work
     between the first transition and the last return to 5-execute. It emits one window per interval the phase
     was open, so the duplicate-window aggregation PLAN-LB-49 added is reachable from the production caller.

   *Done when:* each of these fails at `3baf825e4`: a phase log with 5→6→5→6 transitions yields four windows
   in order, and usage dated inside the first 6-finalize interval is attributed to 6-finalize, not 5-execute.

4. **Session identity is resolved the same way in all three session operations, and the docs say what the code does.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester, pm-documents:ref-documentation
   - Persona: plan-marshall:persona-implementer
   - `session bind` and `session resolve-plan` resolve the id to the root as `session capture` does, so a
     sub-agent shell's `resolve-plan` sees the plan's root binding.
   - Root resolution does not take an unrelated long-lived outer session as the plan's root when the plan's
     driving session is a child of it: decide at outline whether it stops at the session whose directory is the
     plan's worktree, and record why.
   - The documents that still say OpenCode session capture is a no-op or has no session id are corrected:
     `phase-5-execute/SKILL.md` (L1315, L1446) and `plan-retrospective/SKILL.md` (L104, L447), plus any other
     the outline finds with a content search for the retired wording.
   - The reader reads the sessions it needs with a bound, not a full scan of `session_v2` on every call
     (`_opencode_sessions._session_rows` L339), or the outline records why a full scan is acceptable at the
     store's size.

   *Done when:* each of these fails at `3baf825e4`: `bind` of a child id stores the root; `resolve-plan` from a
   child id finds the binding; a fixture whose driving session is a child of an unrelated outer session does
   not count the outer session's other descendants; no document in the touched skills says capture is a no-op
   on OpenCode.

5. **The tests that guard the reader can fail on the store's real shape.**
   - Skills: pm-plugin-development:plugin-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-module-tester
   - One test drives a fixture database with one root, two sub-agent sessions and two phase windows through
     `manage-metrics enrich` and `generate`, and asserts the persisted per-phase figures and a non-zero
     `generate` total; a second captured root is included. This is PLAN-LB-49 D3's own Done-when, which no test
     of that plan satisfies (its enrich tests stub `subprocess.run`).
   - The tool-use fixture row `('ses-child','tool',…)` (`test_opencode_runtime.py` L1035) is replaced by the
     store's shape; the two tests that pass at the base,
     `test_session_bind_without_an_id_is_a_noop` and `test_session_resolve_plan_without_an_id_is_a_noop`,
     are kept as controls and labelled so, and each deliverable above has a test that fails at the base.

   *Done when:* each new or replaced test fails when its named behaviour is mutated, run and recorded
   (`order=mutation-after` acceptable and labelled), and the fixture-database test fails at `3baf825e4`.

Split guard: five deliverables, all in the OpenCode measurement path (the reader, `opencode_runtime.py`,
`manage-metrics.py`, their docs and tests). Proceeding unsplit: D1 and D2 are one reader-to-landing chain, D3 is
one function, D4 is the same reader's session handling plus four doc lines, D5 changes tests only. If D1's cost
and billing decisions grow into a pricing table, split D1 at outline and say so in the outline's first deliverable.

## Claim Labels

- OBSERVED: `_MESSAGE_TOKEN_PATHS` maps input, output, cache read and cache write only; `tokens.reasoning` is not read — `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_opencode_sessions.py` L92-97 (read by the orchestrator at `3baf825e4`).
- OBSERVED: tool use is counted only for a `session_message` row whose lower-cased `type` contains `tool` (`_TOOL_TYPE_MARKER`, L105; L793-794) — read by the orchestrator.
- OBSERVED: `subagent_tool_uses: 0` in all six phases of the PLAN-LB-49 run — `archived-plans/2026-10-22-lb-49-opencode-measurement/work/metrics.toon` L47, L68, L89, L111, L138, L162 (read by the orchestrator).
- OBSERVED: the landing's `total_tokens=16614516` is `15,351 + 564,950 + 353,076 + 537,949 + 10,022,929 + 5,120,261` — the phase-1 main-context figure and the sub-agent input plus output of phases 2 to 6 — from the same `metrics.toon` (read and summed by the orchestrator).
- OBSERVED: the store holds, for that run's two roots and 76 sub-agent sessions, input 25,372,003, output 966,569, reasoning 1,474,767, cache read 890,907,904, cost $7.9433 — read-only, recursive over `parent_id`, by the corroboration of the landing (not re-run by the orchestrator).
- OBSERVED: the store's tool calls are `content[]` parts with `type: "tool"` inside assistant messages (6,378 in that tree, 3,099 of them shell) and the store's message types are assistant, idle, user, synthetic, system, compaction, location-switched, model-switched and shell — by the corroboration (not re-run by the orchestrator).
- OBSERVED: `subagent_duration_ms` is max minus min of the sub-agent message times in a window (`_opencode_sessions.py` L795-796), 75,100,795 ms for phase 5 of that run — by the corroboration.
- OBSERVED: `_phase_window_lookup` emits one window per phase (`manage-metrics.py` L3793-3811); phase 5's window ran 10-20T21:50 to 10-21T21:16 while 5→6 transitions occurred at 10-21T06:11, 12:25 and 17:41 (`work.log` L1168, L3692, L4985) — by the corroboration.
- OBSERVED: `session bind` and `resolve-plan` bind the raw id and `capture` the root (`opencode_runtime.py`) — by the corroboration.
  - verdict: corroborated | checked_at: d60b36f8d | by: live-blockers/analyze | rescoped: n/a | evidence: #1835 only shifted these -14: session_bind L1288-1311 binds the raw sid (L1300, L1307), session_resolve_plan L1313+ reads the raw sid (L1324, L1331), session_capture L1217-1263 stores the root from _opencode_sessions.session_root (L1248, L1255).
- OBSERVED: `phase-5-execute/SKILL.md` L1315, L1446 and `plan-retrospective/SKILL.md` L104, L447 still describe OpenCode session capture as a no-op; flagged at `decision.log:312` of that run and not fixed — by the corroboration.
- OBSERVED: the `test_opencode_runtime.py` L1035 fixture invents a `tool` row type, and the six `test_manage_metrics_enrich.py` multi-root tests stub `subprocess.run` — by the corroboration.
- HYPOTHESIS: OpenCode's `tokens.output` already includes reasoning, so carrying `reasoning` separately would double-count if added to output — settle against the store before choosing (verify-at-outline).
- HYPOTHESIS: the `(inline)` label and the `total_tokens_population` / `tokens_cell_source` choice are made in `manage-metrics.py` `generate`/`record-metrics`, not in the runtime — confirm (verify-at-outline).
- HYPOTHESIS: `session_v2.directory` for the plan's driving session equals the plan's worktree, so root resolution can stop there — confirm against the store (verify-at-outline).
- Verify-first clause (deliverable 2): decide the population the total sums before scoping, and read PLAN-LB-87 D1 so the two plans do not decide the unmeasured-versus-zero rule twice.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_opencode_sessions.py` — tool use, reasoning, cost, spans, session scan (D1, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — `_per_phase_buckets`, `session_bind`, `session_resolve_plan` (D1, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py` — the absent-is-not-zero rule (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py` — window lookup, population, label, counter (D2, D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md` (verify-at-outline) (D1, D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md` and `no-op-policy.md` (verify-at-outline) (D1, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — L1315, L1446 (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md` — L104, L447 (D4)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_sessions.py` (D1, D4, D5)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_runtime.py` (D1, D4, D5)
- OBSERVED: `test/plan-marshall/manage-metrics/test_manage_metrics_enrich.py` (D2, D3, D5)
- HYPOTHESIS: `test/plan-marshall/manage-metrics/` — the fixture-database enrich-to-generate test and its fixture module (verify-at-outline) (D5)

## Dependencies and Sequencing

- Depends on: PLAN-LB-49 (shipped, `3baf825e4`) — the reader, the capture path and the multi-root enrich this plan completes.
- Overlaps with: PLAN-LB-84 on `runtime_info.py` only if deliverable 4 moves the root resolution the runtime stamp also reads (`runtime_info.py` now reads the tree through this reader, so PLAN-LB-84 D2's mixed-variant read must go through the same reader: sequence this plan BEFORE PLAN-LB-84 D2, or state in the outline which of the two owns the per-message model read); PLAN-LB-83 on `opencode_runtime.py` and `test_opencode_runtime.py` (different functions; PLAN-LB-83's line references moved by #1833); PLAN-LB-87 on `manage-metrics.py` (this plan owns the reader-to-landing chain and the window lookup, PLAN-LB-87 owns the call sites that record boundaries). The gate will ask.
- Adjacent to: `emit-landing.md` and the landing payload (PLAN-LB-84), neither edited here.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-86-lb-49-completion.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

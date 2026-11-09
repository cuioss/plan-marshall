# PLAN-LB-140: Generated Antigravity documents name the native sub-agent mechanism, and the dispatch seam carries the resolved level

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-140-antigravity-native-dispatch.md` and is queued as one row file, `queue/PLAN-LB-140.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Regrouped on the operator's word of 2026-11-09 from the parked PLAN-LB-51 D1 (the largest piece of the old plan). The operator
> ruled on 2026-10-12 that Antigravity issues are this epic's highest priority and on 2026-10-15 that the OpenCode plans come first.
> Every claim was re-grounded against `main` at `9cd644892` by a read-only leaf on 2026-11-09, and the fix is bigger than the old spec
> said: a mapping change alone cannot reach `workflow/*.md` or `standards/*.md`, because the emitter runs the body transformer on
> `SKILL.md` only and copies every other file byte for byte. **Each deliverable is its own outline deliverable, and each Done-when is
> its own success criterion. Do not merge them.** Every Done-when below fails at `9cd644892` unless it says "holds at". No Sonar. No
> token or measurement work.

## Objective

The generated Antigravity documents carry a bare `Task: plan-marshall:{target}` line at the phase-5 dispatch and the
verification-feedback dispatch, with no native sub-agent mechanism, and the platform-runtime dispatch seam is called without the
resolved level or a spawning-tool signal, so its inline branch is unreachable. This plan makes the generated documents name
`invoke_subagent` with the resolved level, makes the sub-files of a skill go through the transformer, and makes the seam's inline
branch reachable and recorded.

## Deliverables

1. **The Antigravity emitter transforms every Markdown file of a skill, and a dispatch line becomes the native instruction.**
   - `marketplace/targets/antigravity/mapping.json` (L48-51) maps `Task:` as `preserve`, which `rewrite_registered_idioms`
     (`body_transform_engine.py` L345-369) leaves untouched; only the backticked `` `Task` `` is rewritten (`mapping.json` L37-41).
     The emitter runs the body transformer on `SKILL.md` only (`emitter.py` L230, L244) and copies every other file in the skill
     directory byte for byte (L247-250), so `workflow/execution.md` (L157, L352) reaches the install unchanged.
   - A dispatch-line disposition and an engine applier match a full-line `Task: plan-marshall:{x}` plus its indented `prompt:` block
     and emit an `invoke_subagent` instruction naming the resolved target (`{target}` is the output of `manage-config effort
     resolve-target`, `execution.md` L138-145; it is not a literal `execution-context-{level}`).
   - The emitter applies the transformer to the Markdown files a skill copies, not only `SKILL.md`. That also starts rewriting the
     `Skill:` and `Read:` directives in those files, which are not rewritten today: the outline decides whether the sub-file transform
     is restricted to the dispatch applier or is the full transformer, and records why; the choice is pinned by a test either way.
   - OpenCode's mapping (`Task` to `subagent`) is a different target's and is not touched.

   *Done when:* each of these fails at `9cd644892`: generating the Antigravity target over the plan-marshall bundle leaves
   `skills/plan-marshall-plan-marshall/workflow/execution.md` with no line matching `^\s*Task: plan-marshall:` and naming
   `invoke_subagent` at both dispatch sites (the file is byte-identical to its source at `9cd644892`); the generated
   `phase-5-execute` and `execute-task` documents carry no bare `Task:` line. New tests belong in
   `test/marketplace/targets/antigravity/test_body_transforms.py` (the applier) and `test_emitter_skill_dir.py` (the sub-file
   transform). And these hold at `9cd644892` and must keep holding: the `Skill:` to `view_file`, `AskUserQuestion` to `ask_question`
   and slash-command rewrites in `SKILL.md`; the pins in `test/marketplace/targets/test_body_transform_engine.py` (read at outline,
   it may pin `preserve`).

2. **The dispatch seam is called by the orchestrator with the resolved level and the spawning-tool signal, and the inline branch writes one boundary row.**
   - The runtime code is reachable only with an explicit `--context` (the router passes a caller-built JSON through,
     `platform_runtime.py` L751-767). All three documented callers send `--agent execution-context --context {"plan_id": …}` with no
     level and no flag: `phase-5-execute/SKILL.md` L591, `phase-5-execute/standards/operations.md` L49, `execute-task/SKILL.md`
     L73-75 (which skips the seam on Claude). `spawning_tool_available` appears only in `runtime_base.py`, the two runtimes,
     `standards/contract.md` and the two runtime tests.
   - The seam call belongs at the orchestrator's per-harness branch (`plan-marshall/workflow/execution.md` L178), where the `Task:`
     block (L156-169) goes straight to the dispatch today and the inline branch is "logged at INFO" only; a dispatched leaf calling the
     seam (`phase-5-execute/SKILL.md` L591) conflicts with the rule that a leaf cannot dispatch. The call passes the resolved
     `{target}` as `--agent` and `spawning_tool_available`; the inline branch (`antigravity_runtime.py` L982-991,
     `opencode_runtime.py` L2596-2606) is reached with an explicit `dispatch_mode: inline`, and `execution.md` L186-197 ("record the
     dispatch boundary after every `execution-context` dispatch returns") writes one boundary row per inline envelope.
   - Verify first: whether `record-dispatch-boundary` can record a row for the inline branch, and whether any caller outside these
     three exists. A harness with no sub-agent mechanism runs an envelope inline only through the explicit branch.

   *Done when:* each of these fails at `9cd644892`: a doc-contract test asserts the seam call in `execution.md` carries the resolved
   level and `spawning_tool_available` and that the inline branch names a `dispatch_mode: inline` boundary row; a test drives the
   Antigravity runtime with the flag unset and reads the inline branch and one boundary row. New tests belong in
   `test/plan-marshall/platform-runtime/test_antigravity_runtime.py` and `test_platform_runtime_router.py`. This holds at `9cd644892`:
   the OpenCode dispatch shape (`test_opencode2_dispatch_shape.py`).

Split guard: two deliverables, both on the Antigravity dispatch path. D1 is the larger (an emitter change that widens what is
transformed); D2 splits off first if the plan is split.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- The generated documents are generated: the fix is in the mapping, the engine and the emitter, never in a hand-edited `target/` file.
- A leaf never dispatches; the seam is called at the orchestrator branch.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture, are shown red where a Done-when says so.
- Executor regeneration only if a verb or a flag is added; a harness sync is owed after merge (the generated tree changes).
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: `mapping.json` L48-51 `"Task:": {"disposition": "preserve"}`; `body_transform_engine.py` L345-369 `rewrite_registered_idioms` skips everything except `rewrite_inline_code`; `emitter.py` L230, L244 (SKILL.md transformed) and L247-250 (other files copied byte for byte) — `marketplace/targets/antigravity/`, `marketplace/targets/body_transform_engine.py`
- OBSERVED: `diff --no-index` of `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` and `target/antigravity/skills/plan-marshall-plan-marshall/workflow/execution.md` shows no difference; the generated file carries `Task: plan-marshall:{target}` at L157 and L352; the generated `phase-5-execute` and `execute-task` documents differ from source in frontmatter, `Skill:` to `view_file`, `AskUserQuestion` to `ask_question` and slash commands only
- OBSERVED: the dispatch seam's callers send `--agent execution-context --context {"plan_id": …}` and no level or flag (`phase-5-execute/SKILL.md` L591, `phase-5-execute/standards/operations.md` L49, `execute-task/SKILL.md` L73-75); `antigravity_runtime.py` L982-991 and `opencode_runtime.py` L2596-2606 hold the inline branches; `spawning_tool_available` is in no workflow document; `dispatch_mode` appears only in `test_architecture_refresh.py`
- HYPOTHESIS: `record-dispatch-boundary` can record a row for the inline branch — confirm at `execution.md` L186-197 and the verb's script (verify-at-outline, D2)
- HYPOTHESIS: restricting the sub-file transform to the dispatch applier leaves the sub-files' `Skill:` / `Read:` directives untouched and is enough for the Done-when — confirm against the engine's applier set (verify-at-outline, D1)
- Verify-first clause (D1): generate the target at `9cd644892` and read the two dispatch sites in the output before editing; record the sub-file transform scope chosen and why.

## Expected Surface

- OBSERVED: `marketplace/targets/antigravity/mapping.json` (D1)
- OBSERVED: `marketplace/targets/antigravity/emitter.py` — the sub-file copy loop (D1)
- OBSERVED: `marketplace/targets/body_transform_engine.py` — `rewrite_registered_idioms` and a dispatch-line applier (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — L156-197 (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — L591 (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/operations.md` — L49 (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/execute-task/SKILL.md` — L73-75 (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py` — L982-991 (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` and `runtime_base.py` — only if the seam contract changes (verify-at-outline) (D2)
- OBSERVED: `test/marketplace/targets/antigravity/test_body_transforms.py`, `test/marketplace/targets/antigravity/test_emitter_skill_dir.py` and `test/marketplace/targets/antigravity/test_emitter.py` (D1)
- HYPOTHESIS: `test/marketplace/targets/test_body_transform_engine.py` — if it pins `preserve` behaviour (verify-at-outline) (D1)
- OBSERVED: `test/plan-marshall/platform-runtime/test_antigravity_runtime.py` and `test/plan-marshall/platform-runtime/test_platform_runtime_router.py` (D2)

## Dependencies and Sequencing

- Depends on: PLAN-LB-136 for the order on `antigravity_runtime.py` (that plan lifts the bridge helpers out of it).
- Overlaps with: PLAN-LB-136 on `antigravity_runtime.py` and `test_antigravity_runtime.py`; PLAN-LB-134 and PLAN-LB-135 on `opencode_runtime.py` only if D2 changes the seam contract. The gate decides.
- Adjacent to: OpenCode's mapping (`Task` to `subagent`, not touched), the harness/model stamp and the measurement work (out of scope).

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-140-antigravity-native-dispatch.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

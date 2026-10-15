# PLAN-LB-50: Fix what PLAN-LB-39 broke

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-50-lb-39-regression-fixes.md` and is queued as one row file, `queue/PLAN-LB-50.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-39 (#1768, `c8adaf178`), recorded at
> `landings/PLAN-LB-39.md` § Regressions. Every OBSERVED claim below was read at `c8adaf178` by the
> orchestrator or a delegated read-only agent; claims 1 and 4 were re-read by the orchestrator.

## Objective

PLAN-LB-39 shipped five defects onto `main`. Two damage consumer projects (a project setup erases
the installed target rules; the shared `.plan/marshal.json` gets a harness-specific key again),
one changes Claude Code behaviour (phase-5 leaves are told to dispatch a sub-agent per task), one
makes Claude landings fail `landing-check`, and the rest are reachability and documentation
defects in the new harness stamp. This plan removes each regression without undoing the parts of
PLAN-LB-39 that work (the `unknown` token rule, the unrecorded-commit transition guard).

## Deliverables

1. **Project setup never overwrites the installed target rules.**
   - `_write_rules_bridge` (`antigravity_runtime.py`, `opencode_runtime.py`) writes to its own
     file, never to `plan-marshall-target-rules.md`, which `install.sh --emit-rules` owns
     (`marketplace/targets/antigravity/templates/install.sh:522`, `:526`).
   - Setup and the steward upgrade path detect a `plan-marshall-target-rules.md` that holds the
     bridge stub (it carries `bridge-version:`) and report it as damaged with the re-emit command;
     they do not rewrite it themselves.

   *Done when:* a test runs setup over a workspace whose `plan-marshall-target-rules.md` holds the
   full emitted rules and reads them byte-identical afterwards; a second test seeds the stub there
   and reads the damage report. The first fails at `c8adaf178`.

2. **`runtime.target` stays retired from the shared `marshal.json`.** PR #1686 removed the seeding
   of `runtime.target` into the git-tracked `.plan/marshal.json` because each harness rewrote it;
   PLAN-LB-39 reintroduced it (`_seed_marshal_runtime_target`, `antigravity_runtime.py:79`,
   `opencode_runtime.py:103`) and rewrote the tests that pinned the retirement, with no recorded
   decision. Remove the seeding and the `standing_rules_bridge` block; if the bridge needs
   persisted state, keep it in git-ignored local state. Restore the retirement pins
   (`marshal_written is False`, byte-identical preservation) in both runtimes' tests.

   *Done when:* the restored pins pass, and fail at `c8adaf178`.

3. **Claude Code phase-5 leaves do not dispatch per task.** `execute-task/SKILL.md:73` and
   `phase-5-execute/SKILL.md:591` tell the leaf to call `platform-runtime subagent dispatch` per
   task and dispatch via `Task` on success; on Claude Code that always succeeds, contradicting the
   leaf rule and `plan-marshall/workflow/execution.md:175` ("NOT a per-task Task: dispatch").
   Scope the instruction so the Claude Code path is exactly what it was before `c8adaf178`; the
   non-Claude routing belongs to PLAN-LB-51 and PLAN-LB-48.

   *Done when:* a doc test asserts the leaf documents carry no per-task dispatch instruction on the
   Claude Code path and agree with `execution.md`.

4. **A partly measured run still produces a complete landing.** Any phase row without a token
   figure makes the Tokens Total `unknown` (`manage-metrics.py:2452-2459`), and `landing-check`
   treats `unknown` as a could-not-read sentinel (`_orchestrator_inbox.py:1354`), so one
   unmeasured phase on a Claude run makes the landing incomplete. Pick one contract and name it in
   `landing-payload-spec.md`: either the total carries the measured subset with its count
   (`N (n=k/M)`, the form PLAN-LB-39 removed from `test_print_phase_breakdown.py`), or the payload
   distinguishes "unmeasured" from "could not read" and `landing-check` accepts the former as
   complete with a named gap. A run with nothing measured still says `unknown`, never `0`.

   *Done when:* a test renders a breakdown with one unmeasured phase and the landing built from it
   passes `landing-check`; a run with no measured phase still renders `unknown`.

5. **The harness stamp is reachable and its documents are correct.**
   - phase-1-init Step 8a.6 is reached (Step 8a currently ends "continue to Step 8a.5" and the
     step-8 overview omits 8a.6) and calls `orchestrator preflight`, as its own prose says, so a
     `client.toon` is written; or the prose stops claiming the preflight hook — choose by whether
     PLAN-LB-45 needs `client.toon` (read its spec).
   - `platform-runtime/standards/contract.md:1478` error example ("'antigravity' is not in the
     registry; valid targets are: antigravity, …") is corrected; the runtime-info success example
     carries the now-required `transcripts` field.
   - `_load_target_tool_permissions` (`runtime_base.py`) walks up to `marketplace/targets/`, which
     installed caches do not have, and then passes everything: it reports "not checkable" there
     instead of a pass.

   *Done when:* a doc test reads Step 8a.6 in the step-8 overview and in the step chain; a test runs
   the tool-permission check with no `marketplace/targets/` above it and reads "not checkable".

Split guard: five deliverables, all repairs of one landing; no split.

## Claim Labels

- OBSERVED: `_write_rules_bridge` writes `# Plan Marshall target rules (Antigravity bridge bridge-version: 1)` plus one sentence to `_bridge_rules_path` = `.agents/rules/plan-marshall-target-rules.md`, and rewrites any file there that lacks the marker — `antigravity_runtime.py:59-150` (orchestrator-read).
- OBSERVED: `install.sh --emit-rules` copies the full target rules to the same path — `marketplace/targets/antigravity/templates/install.sh:33`, `:522-526` (orchestrator-read).
- OBSERVED: the bridge stub carries no `CLAUDE.md` content; giving it content is PLAN-LB-51 D2, not here.
- OBSERVED: `_seed_marshal_runtime_target` writes `runtime.target` and, for a new file, `standing_rules_bridge` into `.plan/marshal.json` — `antigravity_runtime.py:79-117`; the OpenCode twin at `opencode_runtime.py:103`.
- HYPOTHESIS: PR #1686 is the retirement of `runtime.target` seeding — confirm with `git log -S "runtime.target" -- marketplace/bundles/plan-marshall/skills/platform-runtime` (verify-at-outline).
- OBSERVED: `manage-metrics.py:2452-2459` renders `UNKNOWN_TOKEN` whenever `TOTALS_TOKENS_UNKNOWN_PHASES_FIELD` is non-empty; `_orchestrator_inbox.py:1354` `LANDING_COULD_NOT_READ_SENTINELS = {'unknown'}` (orchestrator-read).
- HYPOTHESIS: Claude Code runs routinely leave a phase unmeasured (1-init runs in the main context) — confirm on a recent Claude-run archived plan's `metrics.md` (verify-at-outline).
- OBSERVED: phase-1-init Step 8a.6 is inserted after Step 8a's "continue to Step 8a.5" and calls `platform_runtime runtime-info`, while its first paragraph says "via the orchestrator preflight hook" — `git show c8adaf178 -- marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md` (orchestrator-read).
- OBSERVED: `execute-task/SKILL.md:73`, `phase-5-execute/SKILL.md:591` per-task dispatch instruction; `execution.md:175` "NOT a per-task Task: dispatch" (delegated agent).
- Verify-first clause: PLAN-LB-40 (running, steward-upgrade-integrity) touches the steward upgrade flow; read its landing or branch before editing `marshall-steward/references/upgrade-flow.md` or `configure_harness.py` for D1.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py` (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md` (D5)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/configure_harness.py` — damage report on upgrade (verify-at-outline) (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/execute-task/SKILL.md` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py` (D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py` — only if the "unmeasured" contract is chosen (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md` (D5)
- OBSERVED: `test/plan-marshall/platform-runtime/test_antigravity_runtime.py` (D1, D2)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_runtime.py` (D1, D2)
- OBSERVED: `test/plan-marshall/manage-metrics/test_print_phase_breakdown.py` (D4)
- HYPOTHESIS: `test/plan-marshall/phase-5-execute/test_dispatch_envelope_contracts.py` — D3 doc test (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none. High priority: deliverables 1 and 2 damage consumer projects on every setup.
- Overlaps with: PLAN-LB-48 on `opencode_runtime.py` and `test_opencode_runtime.py` (different
  functions); PLAN-LB-47 on `phase-5-execute/SKILL.md`; PLAN-LB-49 on `manage-metrics.py`;
  PLAN-LB-45 on phase-1-init Step 8a.6; PLAN-LB-40 (running) possibly on the steward upgrade path.
  The gate will ask.
- Precedes: PLAN-LB-51 (its D2 gives the bridge real content in the file D1 creates).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-50-lb-39-regression-fixes.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

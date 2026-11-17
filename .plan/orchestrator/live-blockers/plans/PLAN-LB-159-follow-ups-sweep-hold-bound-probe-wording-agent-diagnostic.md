# PLAN-LB-159: Follow-ups from the PLAN-LB-154, PLAN-LB-155 and PLAN-LB-157 landings — a bounded merge-mutex sweep, the first-drift wording, and a bundle-qualified agent name that says why it missed

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Objective

Three loose ends the last three landings left behind, closed in one plan because the operator asked for a single follow-up covering every open issue:

1. **A sweep that can pin the merge mutex.** The pre-merge step-sequence sweep runs while the cross-plan merge mutex is held and issues one local verb per earlier manifest step plus one manifest read, each bounded at 60 s. A wedged executor therefore pins the mutex for up to 60 s times the roster length (780 s for 13 steps), against the spec wording that the sweep run outside the hold window. Bound the sweep by one budget that does not grow with the roster.
2. **An unstated case.** The unchanged-probe stop in the baseline-drift recovery says what an equal and a different signature do, and is silent on the first drift return of a plan, when nothing is recorded yet.
3. **A miss that misleads.** `platform_runtime subagent dispatch --agent plan-marshall:execution-context-level-3` (the `{bundle}:{name}` notation a `Task:` call uses) answers `Agent '...' not found; searched: <roots>`, which reads as a wrong name or an unsearched root, when the real cause is that `--agent` takes a file stem only. Make the miss say so.

## Deliverables

1. `execution-recovery.md` § "Baseline drift recovery", in the unchanged-probe block, states the case where no probe is recorded: the first drift return of a plan has nothing to compare against, so it records its signature (the same `manage-status metadata --set` call) and continues with step 1 of the procedure, and the `drift_unchanged` stop cannot fire on it. The two existing bullets (equal, different) keep their text.
   - Skills: plan-marshall:ref-code-quality, pm-documents:ref-documentation, pm-plugin-development:plugin-architecture
   - Persona: documenter
2. The step-sequence sweep in `pre_merge_gate.py` is bounded by one total budget, a named constant no greater than 180 s, independent of the number of earlier steps: each verb the sweep runs receives the lesser of its per-verb bound and the budget still remaining, and when the budget is spent the sweep stops reading and refuses `merge_earlier_step_unrecorded` with `remedy: stop`, listing the steps it did not read as `step_record_unreadable` rows (a read fault, per the closed vocabulary). The verdicts reached inside the budget are unchanged: every earlier step recorded proceeds, a step gap answers `remedy: dispatcher`, and the mutex is released on every refusal as before. `branch-cleanup.md` § "Pre-merge step-sequence gate" states the bound and its figure, and the sentence "inside the hold window the step already owns" says what the bound is. An outline that instead moves the sweep ahead of the hold window is accepted when this deliverable's Done-when holds for it.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: implementer
3. A `--agent` value in `{bundle}:{name}` notation is refused on Claude as `prompt_not_found` with a message that says `--agent` takes a file stem and names the stem the value would have meant (the part after the colon); the stem guard (`_is_agent_file_stem`) still refuses a path or a glob in either half, and the bare-stem resolution, its flat-before-versioned order and every existing miss message are unchanged. `platform-runtime/standards/contract.md` § arguments of `subagent dispatch` and the error-table row in `SKILL.md` carry the new message. No bundle-qualified name is ever resolved: the plan adds a diagnosis, not a second lookup form.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: implementer
4. Tests pin deliverables 1 and 2: the doc-contract suite for the recovery names the no-recorded-probe sentence; in `test_pre_merge_step_sequence_gate.py` a roster longer than the budget allows (verbs stubbed to consume their bound) is refused `remedy: stop` with the unread steps as `step_record_unreadable` rows and finishes inside the budget plus one bound; a roster that fits keeps every existing verdict (all recorded proceeds, a gap answers `remedy: dispatcher`, a mixed payload keeps `remedy: dispatcher`); every existing test in that file still passes.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: module-tester
5. Tests pin deliverable 3: the qualified notation answers the stem-naming miss; a path-shaped and a glob-shaped name in either half stay refused (the two mutation-proven guard tests keep failing when the guard is bypassed); the bare stem still resolves from the versioned cache and from the source tree; the contract and `SKILL.md` text matches the message.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: module-tester

## Standing Constraints

- The three clusters share no file; no deliverable edits another's surface.
- The sweep change (D2) changes no refusal code and no reason in the merge-gate vocabulary; it adds one way to reach `step_record_unreadable` and `remedy: stop`. It acquires nothing and releases nothing.
- The agent change (D3) must not change which names resolve: every name that resolved before still resolves to the same file.
- Recorded and not changed by this plan: a step whose latest record is `loop_back` stays admitted by the sweep (the sweep's spec set, documented as a deliberate trade); `worktree-rebase-to` answering `status: conflict` instead of `error: rebase_failed` in a linked worktree stays (both callers, `branch-cleanup` and `finalize-step-sync-baseline`, halt on it); the OpenCode and Antigravity runtimes still supply no deployed agent root, so their tool-mapping check is vacuous on an install that has no source tree (pre-existing, documented in `contract.md`, outside this plan).
- No change under `.plan/orchestrator/` other than the plan's own inbox message.
- Scope-bloat note: five deliverables in three independent clusters, kept in one plan on the operator's word; two of the five are the tests of the other three.

## Claim Labels

- OBSERVED (re-read at HEAD): `_STEP_SEQUENCE_VERB_TIMEOUT_SECONDS = 60` bounds the manifest read and each `assert-step-recorded` call, its comment states the 13-step worst case as 780 s — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pre_merge_gate.py` lines 766-789; the sweep is `_step_sequence_refusal` (`:980`), called from `merge()` through the `step_sequence_check` seam (`:2293`) after the mutex proof.
- OBSERVED (re-read at HEAD): `branch-cleanup.md` line 857 says the gate "acquires nothing and releases nothing. It runs at the merge dispatch, inside the hold window the step already owns".
- OBSERVED (re-read at HEAD): the unchanged-probe block names the equal and the different signature and no absent one — `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/execution-recovery.md` lines 15-29.
- OBSERVED (re-read in the merged diff): `_AGENT_STEM_CHARS` has no `:`, so a `{bundle}:{name}` value fails `_is_agent_file_stem`, `_find_agent_file` returns `None`, and `_claude_runtime_impl.py` (lines 1860-1868) answers `Agent {agent!r} not found; searched: <roots>`; `contract.md` states that `--agent` is a stem and not the notation a `Task:` call uses.
- OBSERVED (re-read): the only production caller passes a bare name — `plan-marshall/workflow/execution.md` lines 178-184 (`--agent {target}`).
- HYPOTHESIS: a total budget can be enforced by handing each verb `min(per-verb bound, remaining)` through `_run_verb`'s `timeout` — confirm/refute at `_run_verb` and at `_step_sequence_refusal`'s loop (verify-at-outline).
- HYPOTHESIS: the doc-contract suite for the recovery, `test/plan-marshall/plan-marshall/test_baseline_drift_recovery.py`, already asserts the unchanged-probe block and is the place to pin the new sentence (verify-at-outline).
- Verify-first clause: the outline settles (a) which of the two shapes of D2 (a total budget inside the sweep, or the sweep ahead of the hold window) is the smaller change that keeps the existing tests green, and the budget's value within the 180 s ceiling; (b) that no caller other than `merge()` reaches `_step_sequence_refusal`.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/execution-recovery.md`
- HYPOTHESIS: `test/plan-marshall/plan-marshall/test_baseline_drift_recovery.py` (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pre_merge_gate.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_pre_merge_step_sequence_gate.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_claude_runtime_impl.py`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py` (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/SKILL.md`
- OBSERVED: `test/plan-marshall/platform-runtime/test_agent_file_versioned_layout.py`

## Dependencies and Sequencing

- Depends on: none (PLAN-LB-154, -155 and -157 are shipped).
- Overlaps with: none staged. PLAN-LB-158 (staged, then running on the operator's word) names none of the files above: its surfaces are the ledger and git skill documents, the Maven executor and the pre-push freshness gate.
- Adjacent to: `PLAN-LB-145` (the merge-mutex proof) and `PLAN-LB-157` (the sweep itself) shipped the surfaces D2 changes; the sweep's verdicts and vocabulary stay untouched.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-159-follow-ups-sweep-hold-bound-probe-wording-agent-diagnostic.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.

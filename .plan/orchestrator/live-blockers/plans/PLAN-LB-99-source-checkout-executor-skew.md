# PLAN-LB-99: A lane in a source checkout is not asked the executor-skew question it cannot answer

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-99-source-checkout-executor-skew.md` and is queued as one row file, `queue/PLAN-LB-99.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-28, **high** (the operator ruled the executor-skew question high on 2026-10-27 and asked for this follow-up
> after PLAN-LB-98 landed), from a finding made right after PLAN-LB-98's sync: on a flat install the check now answers
> (`skew` for a stale executor, `match` after regeneration), but in THIS repository's own lanes it still answers
> `could_not_check` and the lane still stops to ask. **The operator challenged the first fix I proposed ("derive a version from
> the tree's evidence") and was right to:** `generate_executor preflight` already answers whether the executor is stale, so a
> second derivation would rebuild it. This plan therefore has one outline decision, stated under Verify-first, and does not
> prescribe the mechanism. **Each deliverable is its own outline deliverable, and each Done-when is its own success criterion.
> Do not merge them.** A criterion that says "fails at HEAD" means the lane's worktree base, not a fixed SHA, and a reproduction
> in this spec names which copy of the script ran.

## Objective

In a plan-marshall source checkout (the meta-project) the executor maps every script to the checkout's own
`marketplace/bundles/…` tree. A lane there runs the source copy of `runbook_lane.py`, whose layout the check classifies as
"nested, no version directory", and the verdict is `could_not_check`. The lane then asks the operator whether to proceed, and
the answer has always been "proceed".

The question guards against a lane text that names a verb which the executor's mapped script does not have (the executor is
older than the text). In a source checkout the mapped script IS the checkout's script, and the lane text is the checkout's
text, so that failure cannot occur for a script the executor knows; a notation it does not know fails at once with an
unknown-notation error. The question is therefore asked where it cannot change the outcome, which is the cost the operator
named. What this plan must not do is read the unmakeable comparison as "no skew": the rule in `runbook-lane/SKILL.md` stands.

## Where the delta is (measured)

- `runbook-lane/scripts/runbook_lane.py` `_lane_version_probe` (merged by PLAN-LB-98, #1876): the versioned leg reads a
  `{bundle}/{version}/skills/{skill}` directory, the flat leg reads the sync stamp at the deploy root, and a bundle directory
  with neither returns layout `nested` with `version = None`, so `_executor_skew` returns `could_not_check` with the reason
  `lane text version unknown: no version directory under {bundle dir}`.
- Reproduced 2026-10-28 in this checkout: `env OPENCODE=1 python3 .plan/execute-script.py
  plan-marshall:runbook-lane:runbook_lane executor-skew` printed `verdict: could_not_check`, `executor_version: 0.1.2025`,
  `lane_version: unknown`, that reason. **That call ran the SOURCE copy**: the executor's only mapping is
  `"plan-marshall:runbook-lane:runbook_lane": "…/marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py"`,
  so `OPENCODE=1` selects nothing here. The installed flat copy, called directly, answers `skew` and `match` correctly.
- A source checkout is told apart from a versioned cache by where the bundle manifest sits:
  `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json` directly under the bundle (source) against
  `{bundle}/{version}/.claude-plugin/plugin.json` (cache); `resolve_bundles_root` already probes exactly these two shapes.
- `generate_executor preflight` already answers staleness: `executor_action: fresh`, `installed_version: 0.1.2025`,
  `executor_version: 0.1.2025` here. **But `cmd_preflight` regenerates the executor in place when it is stale**
  (`executor_action: regenerated`, `generate_executor.py` around L3769 and L3842), so it is a write on the shared main
  executor and is not a read-only witness a lane may call.
- `runbook-lane/SKILL.md` L132-146 states the rule: a `could_not_check` stops the run for the operator, never read as no skew,
  and gives the reason the check cannot live inside `resolve` (a stale executor runs the stale `resolve`).

## Deliverables

1. **A source checkout answers an explicit verdict that is not `match`, and the lane proceeds without asking.**
   - The check recognises a source-checkout layout (the bundle manifest directly under the bundle, no version directory, no
     flat install) and answers a distinct verdict, working name `not_applicable`, with a reason that says why: the executor
     dispatches this checkout's own scripts. It is never `match`, and `skew` and `could_not_check` are unchanged for every
     other case (a stale executor in a versioned cache, a flat install without a stamp, an unreadable executor).
   - The mechanism is chosen at outline against the Verify-first clause. This deliverable is stated in terms of the verdict a
     lane sees, not the code that produces it.

   *Done when:* tests, with a source-checkout fixture (the executor maps into a tree whose bundle carries
   `.claude-plugin/plugin.json` directly): the verdict is the new one, with the reason, and not `match`; a versioned-cache
   fixture and a flat fixture with and without a stamp return what they returned before (PLAN-LB-98's tests stay green); an
   executor that cannot be read in a source checkout is still `could_not_check`. The first fails at the worktree base
   (`could_not_check`).

2. **The lane text says when the question is asked, and the new verdict does not stop a run.**
   - `runbook-lane/SKILL.md` § executor-skew names the verdicts (`match`, `skew`, `could_not_check`, and the new one), says that
     the new one proceeds and is recorded in the landing, and keeps the sentence that `could_not_check` is asked and never read
     as no skew. The reason the new verdict is safe (the mapped scripts are the checkout's own) is stated once, with what it
     does not cover (Verify-first).

   *Done when:* a test pins the SKILL.md statement for each verdict and fails at the worktree base for the new one; the
   documentation verify passes.

3. **The verdict is proved the way a lane reaches it.**
   - One test drives `runbook_lane executor-skew` through a generated executor whose mapping points into a source-checkout
     fixture and asserts the new verdict, so the proof does not stop at the helper.

   *Done when:* the end-to-end test returns the new verdict and no question-worthy `could_not_check`, and returns
   `could_not_check` when the executor file is removed; the first fails at the worktree base.

Split guard: three deliverables, one theme. D1 is the verdict, D2 the text, D3 the end-to-end proof; a run may order them
freely and report each on its own.

## Claim Labels

- OBSERVED (D1): `runbook_lane.py` `_lane_version_probe` returns layout `nested` with `version = None` for a bundle directory that carries neither a live version directory nor a flat stamp, and `_unreadable_lane_text_reason` reports `no version directory under {path}` for it (read in the merged PLAN-LB-98 diff, `b8961015b`).
  - verdict: corroborated | checked_at: b8961015b06578ea608fa12713bb411c60273a83 | by: live-blockers/cleanup | rescoped: n/a | evidence: Read the merged PLAN-LB-98 diff (b8961015b): _lane_version_probe returns layout nested with version None when only a version-less bundle directory is found; _unreadable_lane_text_reason reports 'no version directory under {path}' for it.
- OBSERVED (D1, D3): in this checkout the executor's only mapping for `plan-marshall:runbook-lane:runbook_lane` is the source file under `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/`, and `env OPENCODE=1 python3 .plan/execute-script.py plan-marshall:runbook-lane:runbook_lane executor-skew` answered `could_not_check` with the `no version directory under …/marketplace/bundles/plan-marshall` reason (orchestrator-run, 2026-10-28; the call ran the source copy).
  - verdict: corroborated | checked_at: b8961015b06578ea608fa12713bb411c60273a83 | by: live-blockers/cleanup | rescoped: n/a | evidence: grep of .plan/execute-script.py shows one mapping for runbook_lane, the source file under marketplace/bundles; the OPENCODE=1 executor-skew call answered could_not_check with the 'no version directory under ...marketplace/bundles/plan-marshall' reason, so it ran the source copy.
- OBSERVED (D1): `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json` exists directly under the bundle in this checkout (find, 2026-10-28).
  - verdict: corroborated | checked_at: b8961015b06578ea608fa12713bb411c60273a83 | by: live-blockers/cleanup | rescoped: n/a | evidence: find over marketplace/bundles/plan-marshall/.claude-plugin lists plugin.json directly under the bundle (no version directory), as a source checkout.
- OBSERVED (Objective): `generate_executor preflight` ran here and answered `executor_action: fresh`, `installed_version: 0.1.2025`, `executor_version: 0.1.2025`, `marshal_status: stale` (orchestrator-run, 2026-10-28).
  - verdict: corroborated | checked_at: b8961015b06578ea608fa12713bb411c60273a83 | by: live-blockers/cleanup | rescoped: n/a | evidence: Run 2026-10-28: generate_executor preflight printed executor_action fresh, installed_version 0.1.2025, executor_version 0.1.2025, marshal_status stale.
- OBSERVED (Objective, D1): `cmd_preflight` regenerates the executor in place when it is stale and then reports `executor_action: regenerated` (docstring and code lines at `generate_executor.py` L3769-3771 and L3842, grep lines at `b8961015b`; the function body was not read in full).
  - verdict: corroborated | checked_at: b8961015b06578ea608fa12713bb411c60273a83 | by: live-blockers/cleanup | rescoped: n/a | evidence: grep lines in generate_executor.py: cmd_preflight at L3759, its docstring says it regenerates in place when executor_version is below executor_changed_at_version (L3769-3771) and the code sets executor_action regenerated (L3842). The function body was not read in full.
- OBSERVED (Objective): `runbook-lane/SKILL.md` L132-146 stops the run for the operator on `could_not_check`, forbids reading it as no skew, and explains why the check cannot live inside `resolve` (read at `b8961015b`).
  - verdict: corroborated | checked_at: b8961015b06578ea608fa12713bb411c60273a83 | by: live-blockers/cleanup | rescoped: n/a | evidence: Read runbook-lane/SKILL.md L132-146 earlier this session: could_not_check stops the run for the operator and is never read as no skew; the check cannot live inside resolve because a stale executor runs the stale resolve.
- HYPOTHESIS (Objective): in a source checkout the lane text names no verb that the mapped scripts lack, because the mapped scripts are the checkout's own and an unknown notation fails at once (verify-at-outline by running an unknown notation through this checkout's executor and by reading how the executor reports it).
  - verdict: unverifiable | checked_at: b8961015b06578ea608fa12713bb411c60273a83 | by: live-blockers/cleanup | rescoped: n/a | evidence: Reasoned from the executor mapping (one entry per notation pointing into the tree) but not tested: no unknown notation was run through this checkout's executor and the executor's unknown-notation reporting was not read.
- HYPOTHESIS (Verify-first): the executor TEMPLATE can be stale in a way a lane in a source checkout would hit even though its mapped scripts are current (the PLAN-LB-95 template bug is the precedent); a verdict of "not applicable" would not cover that (verify-at-outline).
  - verdict: unverifiable | checked_at: b8961015b06578ea608fa12713bb411c60273a83 | by: live-blockers/cleanup | rescoped: n/a | evidence: The PLAN-LB-95 template bug is the precedent (the template itself, not the mapped scripts, put the wrong versions on PYTHONPATH); whether any such template staleness would reach a source-checkout lane today was not examined.
- Verify-first clause (D1): decide between (a) an explicit `not_applicable` verdict for the source-checkout layout, (b) using `generate_executor preflight` as the witness, (c) leaving the question in place for this repository. Record the reason. Option (b) is a write on the shared main executor (`cmd_preflight` regenerates when stale), and a concurrent lane once broke the executor that way (PLAN-LB-97 and PLAN-LB-58), so it needs a read-only variant or is rejected. Option (a) must state what it does not cover (a stale template) and whether `preflight`'s read-only half can supply that.
  - verdict: unverifiable | checked_at: b8961015b06578ea608fa12713bb411c60273a83 | by: live-blockers/cleanup | rescoped: n/a | evidence: Outline-time design decision (not_applicable verdict, a read-only preflight witness, or leaving the question), not a code fact at HEAD.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` — `_lane_version_probe`, `_executor_skew`, `cmd_executor_skew`, `_unreadable_lane_text_reason` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — § executor-skew (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_bundles.py` and `deployed_layout.py` — the source-versus-cache probe `resolve_bundles_root` already makes, reused rather than re-spelled (verify-at-outline) (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` — only if option (b) is chosen, to add a read-only preflight (verify-at-outline) (D1)
- OBSERVED: `test/plan-marshall/runbook-lane/test_executor_skew_flat_install.py` and `test_runbook_lane.py` — the existing skew tests that stay green (D1, D2, D3)
- HYPOTHESIS: `test/plan-marshall/_flat_install_fixtures.py` — extended with a source-checkout fixture (verify-at-outline) (D1, D3)

## Dependencies and Sequencing

- Depends on: PLAN-LB-98 (shipped, #1876): the probe and its tests.
- Overlaps with: nothing running or staged (nothing is running). It touches the same file as PLAN-LB-98 only.
- The operator workaround until this ships: answer "proceed" after checking that the executor's `MARSHALL_VERSION` equals the
  version `generate_executor preflight` reports as installed.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-99-source-checkout-executor-skew.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

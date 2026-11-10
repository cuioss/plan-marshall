# PLAN-LB-120: The merge gate does not admit a step it could not see, and the push gate does not turn an unreadable build row into a pass

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-120-merge-and-push-gate-truth-fixes.md` and is queued as one row file, `queue/PLAN-LB-120.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word ("add to the existing fix plan or create a new one"; decision 16). The existing fix plan, PLAN-LB-119,
> is already seven deliverables on the review gate, above the six-deliverable guard, and this is a different surface (the merge gate and
> the push gate), so this is a new plan. It is the fix plan for PLAN-LB-107 (PR 1920, merge `1d2b559fd`; report
> `landings/PLAN-LB-107.md`). Every finding id below (L1-n, L2-n, L3-n) is that report's. The points the orchestrator re-read at their
> lines are OBSERVED; the points the analysis leaf read and the orchestrator did not re-read, and every claim about reach, are
> HYPOTHESIS and are settled first.
>
> Ruling check. D1 is a fail-open at the merge gate (a step the gate could not see is admitted), D2 is a fail-open at the push gate
> (a narrow build row with an extra flag stops refuting a whole-tree change); both are graded blocking as gate integrity, under the
> epic's done-condition "the review gate can be trusted to mean what it says". D3 and D4 are minor and separable. No token or
> measurement work. No Sonar.

## Objective

PLAN-LB-107 made the merge gate read the dispatcher's re-entry table and made the push gate read a build row's recorded scope. Two of
its choices open a pass. The merge gate reads head-dependence from a reader that answers "undeclared" for a step it could not find, so
a stale record for a head-dependent step that discovery cannot see is admitted, where it used to be refused. The push gate reads any
unknown flag after the canonical command as an unreadable row, and an unreadable row is an inability that passes, so a narrow row with
a trailing executor flag no longer refutes a whole-tree change.

After this plan the merge gate separates "this step declares no head-dependence" from "this step could not be found" and refuses the
second, the push gate reads the executor's own flags apart from the payload's flags or fails closed on a row it cannot read, and the
gate's tests, bounds and texts state what they pin.

## Deliverables

1. **The merge gate separates a step that declares no head-dependence from a step it could not find.** *(L3-1, L1-2; blocking)*
   - A stale record for a step that is absent from the discovered finalize-step population is not listed under `unconsulted_stamps`
     and not admitted; it takes the same fail-closed field-presence fallback as an underivable declaration, and the payload names the
     reason ("step not found in the discovered population"). `mark-step-done`'s reading of the same function (a phase-5 step that
     legitimately matches no finalize-step implementor resolves to "not head-dependent") keeps its contract: the gate asks a
     distinguishing question, by a sibling reader in `_cmd_mark_step.py` or a gate-side population check, decided at outline and
     recorded once (`pre_merge_gate.py:313-338,445-451`; `_cmd_mark_step.py:203-240`).
   - A declared document that cannot be read is "not derived", never "undeclared" (`extension_discovery._read_frontmatter_fields`).
   - `unconsulted_stamps[]` and `head_dependence_fallback[]` are persisted: `record-merge` records a fact for each, as it already does
     for `waived_steps`, so a merge that passed on either leaves a trace in the step record (`branch-cleanup.md:1659`, L3-4).

   *Done when:* a fixture whose stale record names a head-dependent step that the discovery stub does not return is refused with the
   fallback reason (red at `1d2b559fd`); the same record for a step that resolves as undeclared is still listed and admitted
   (control); a project-tier (`project:`-prefixed) declared step and a bundle-tier declared step are each pinned through the
   production reader, not a stub; a fixture with an unreadable declared document is refused, not listed; `record-merge` records a
   fact for a merge that passed with an unconsulted stamp or a fallback.

2. **The push gate does not turn an unreadable build row into a pass.** *(L1-1; blocking lead)*
   - Settle first, at the freshness consumer, whether `UNDETERMINED` (reason scope-unreadable) lets the push gate pass, and what the
     real ledger rows look like: whether a build row records the executor's own flags (`--plan-id`, `--timeout`, `--format`,
     `--mode`) apart from the payload's flags, and whether the quoting survives in the row (`_freshness_crosscheck.py:610-669`).
   - If the executor's flags can be told from the payload: they are read as executor flags and not as scope, so `verify
     plan-marshall --format json` reads as scope `plan-marshall` again and a profile flag such as `-Ppre-commit` beside `-pl core-api`
     (the documented call shape, `build-execution.md:395-396`) is read, not unreadable. If they cannot be told apart: a row that
     carries an unknown flag is an inability that blocks a change that needs whole-tree coverage and passes a change that does not,
     decided at outline, never a silent pass.
   - The extra-flag shapes the documents show are enumerated and each is pinned: `verify -Ppre-commit -pl core-api`,
     `verify --format json`, `verify --mode errors --format json`, `module-tests -k foo`.
   - The Maven resolver's real shapes are run through `cross_check_candidates`, not only `parse_row_scope`: `verify -pl X -am`,
     `package -pl X -am`, `test -pl X -am` (L1-4). The Done-when shape `module-tests -pl` that PLAN-LB-107 pinned is never emitted by
     the resolver; the resolver shapes replace it.
   - The module's two comments that call the unreadable row "fail-closed" say what the row does at the gate
     (`_freshness_crosscheck.py:589-598`; `test_freshness_notation_crosscheck.py:696-699`, L2-3).

   *Done when:* a fixture with a whole-tree change and one candidate row `verify plan-marshall --format json` is not `UNDETERMINED`-pass
   (red at `1d2b559fd`, or the decision made at outline is recorded and its test shows it); the documented `verify -Ppre-commit -pl
   core-api` row is read with scope `core-api`, or is an inability the gate treats as decided at outline; each Maven resolver shape
   above is judged through `cross_check_candidates` with the expected verdict; the control `verify` with no flag is still whole-tree
   and adequate.

3. **The gate's tests, bounds and fault reports state what they pin.** *(separable; L2-1, L2-2, L2-4, L3-3, L3-5, L3-6)*
   - The abbreviated-SHA waiver case uses `HEAD_MERGED[:7]`, so a lost full-SHA predicate or a prefix match turns it red
     (`test_lb55_merge_head_binding.py:225`).
   - The hand-listed count at `test_pre_merge_gate.py:1658` is removed; the list-equality assertion beside it already proves it.
   - The classifier's error, timeout and unknown-verdict answers each have a test that shows the step refused
     (`pre_merge_gate.py:464-466`).
   - A fault in the override-label import is named in the refusal, not swallowed (`pre_merge_gate.py:1115-1118`), and a fault in the
     in-process status read is named in the evidence payload, not an empty admit (`:230-237`).
   - The discovery read and the status read run bounded while the merge mutex is held, and the discovery result is read once per
     merge, not once per stale step (`:445,464`); the number of classifier calls is bounded by what the dispatcher would run.

   *Done when:* each test change is shown to fail against a stub of the behaviour it pins; a fixture with an import fault shows the
   named reason in the refusal; a merge with three stale declared steps runs the discovery once.

4. **The documents state what the gate does.** *(separable; L3-2, L3-7, L3-8, L3-4 text)*
   - The sentence "the offending set equals the steps the dispatcher would re-fire" is either made true or stated with its two
     exceptions: a declared step with `outcome == done` and no `head_at_completion` (the dispatcher re-fires it, the gate skips it,
     `pre_merge_gate.py:437-439`) and a declared step with a failed or loop-back outcome whose head equals the candidate (the
     dispatcher retries it, the gate admits it, `:441`). If the gate is changed to match, D1's tests pin it.
   - Plan ids and history wording are removed from current-state text: the `PLAN-LB-107 D1–D5` headers in the four test files, the
     `PLAN-LB-26` mentions at `branch-cleanup.md:838` and `pre_merge_gate.py:401`, "used to ignore the waiver", "which is how a
     declared head-dependent step could be missed".
   - `manage-status/SKILL.md:504` ("there are exactly two readers … no other reader exists") is guarded by a test that enumerates the
     readers, or states what it does not guarantee.

   *Done when:* a read of each cited line shows the wording corrected; a test enumerates the waiver readers.

Split guard: four deliverables on two gates. D1 and D2 are the two fail-opens and are independent of each other (merge path, push
path); D3 and D4 are the first to split off, D4 first. A split runs in sequence, since D1, D3 and D4 edit one module.

## Standing Constraints

- **Settle each HYPOTHESIS first.** A refuted claim is dropped from its deliverable, not worked around, and the PR says so.
- **The gate gets more precise, never more permissive.** Every relaxation ships with a control showing that a genuine stale step or a
  genuinely narrow row still blocks.
- **Keep the waiver and the re-entry table.** Do not change the waiver's write shape (`{head, basis}`), `loop-back close`, the
  dispatcher's re-entry table in `phase-6-finalize/SKILL.md`, `BARRIER_OVERRIDE_LABELS`, the exact-label check in `merge-authorization
  grant`, or `required_coverage`.
- **Keep the freshness module's split fail-direction.** A refutation fails closed; an inability passes with the inability recorded
  — except where D2 decides that an unreadable row must block a change that needs whole-tree coverage, and then that decision is
  stated in the module docstring once.
- **One reader for head-dependence.** D1 does not add a second frontmatter parser; it asks the existing discovery a second question.
- **Keep the gate's reads inside the existing seams** and bounded, because they run while the merge mutex is held.
- **Documentation states the current behaviour.** No comment or doc describes a change or the old behaviour.
- **Tests state their purpose**, use the `PLAN_MARSHALL_HOME` fixture, and are shown red where a Done-when says so. A test that
  renames or inverts an existing control says why in its docstring; counts come from an enumeration, not a hand list.
- **No token or measurement work.** **No Sonar.**

## Claim Labels

- OBSERVED: `_derive_head_dependence` returns `(False, None)`, "resolved, undeclared", for a step absent from the discovered
  population, and `(False, reason)` only when the machinery could not run or the population is empty; its docstring says the first is
  deliberate because a phase-5 step legitimately matches no finalize-step implementor —
  `manage-status/scripts/_cmd_mark_step.py:203-240`.
- OBSERVED: the gate delegates to that reader (`pre_merge_gate.py:313-338`), skips a record with no `head_at_completion` (`:437-439`),
  skips a record whose head equals the candidate before any outcome check (`:441`), lists a step that reads as undeclared and does not
  refuse it (`:445-451`), and admits a waiver only for `outcome == done` (`:452-463`).
- OBSERVED: the override-label import is guarded by `except Exception: pass` — `pre_merge_gate.py:1115-1118`.
- OBSERVED: an unknown flag after the canonical command returns `None` (`_freshness_crosscheck.py:634-638`); `_SCOPE_FLAGS` holds
  `-pl`, `--projects`, `--workspace` and `_SCOPE_NEUTRAL_FLAGS` holds `-am`, `--also-make` (`:352-366`); a row that returns `None` is
  `ROW_ARGS_UNREADABLE` (`:714-716`), an inability (`:732-734`); a candidate list of only inabilities is `UNDETERMINED` with reason
  scope-unreadable (`:950-960`).
- OBSERVED: the ledger joins a row's `args` without quoting, so a flag after the canonical cannot be placed inside or outside the
  command's own quoting — the module's own statement at `_freshness_crosscheck.py:589-598` and `:347-351`.
- OBSERVED: the documented call shapes include `--command-args "verify -Ppre-commit -pl core-api"` and `--command-args "verify"
  --format json` — `extension-api/standards/build-execution.md:395-408`. The first reads as unreadable at the first unknown flag
  (`-Ppre-commit`) although `-pl core-api` narrows the run.
- OBSERVED: the existing control `run --command-args verify --timeout 900` was changed from `('verify', ())` to `None` and its
  comment says "fail-closed" — `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py:696-699`; the abbreviated
  waiver case is `{'head': 'abc1234', ...}` — `test/plan-marshall/phase-6-finalize/test_lb55_merge_head_binding.py:225`.
- HYPOTHESIS: a stale record for a head-dependent step can reach the gate while discovery does not return the step in the gate's
  process (a project-tier step whose root does not resolve from the gate's cwd, an opt-in bundle step missing from the cache, a step
  renamed since the record was written) — confirm/refute at `extension_discovery.py` § `find_implementors` and the five-surface scan
  (verify-at-outline). It decides how often D1's case occurs; the code path itself is OBSERVED.
- HYPOTHESIS: `extension_discovery._read_frontmatter_fields` returns `{}` for an unreadable document instead of raising — confirm/refute
  at `extension_discovery.py` (verify-at-outline). It decides D1's unreadable-document bullet.
- HYPOTHESIS: `verdict_currency` treats the same input as `REASON_STEP_UNRESOLVED` (fail-closed) — confirm at
  `phase-6-finalize/scripts/verdict_currency.py` near `:362` (verify-at-outline). It decides whether D1 can reuse that reading.
- HYPOTHESIS: the push gate lets an `UNDETERMINED` freshness verdict pass — confirm/refute at the freshness consumer
  `manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` and the push-gate caller (verify-at-outline). It decides whether D2 is a
  code change or a documentation line.
- HYPOTHESIS: a build row in the ledger carries the executor's own flags apart from the payload's flags, or a recorded `command` that
  keeps the quoting — confirm/refute by reading real `kind=build` rows and the row writer (verify-at-outline). It decides D2's
  first branch.
- HYPOTHESIS: the dispatcher re-fires a declared step with `outcome == done` and no `head_at_completion`, and retries a failed or
  loop-back step at the candidate head — confirm/refute at `phase-6-finalize/SKILL.md` L612-614 (verify-at-outline). It decides
  D4's first bullet.
- HYPOTHESIS: `record-merge` accepts a `head_binding_waived` fact and could accept two more — confirm/refute at `pre_merge_gate.py`
  § `_fact_map` / `record_merge` (verify-at-outline).
- HYPOTHESIS: Maven `test` and `package` goals are outside the coverage dimension's canonical vocabulary, so a narrow Maven
  module-tests row is an inability that passes before scope is judged — confirm/refute at `_freshness_crosscheck.py` §
  `_build_examined` and the vocabulary (verify-at-outline). If it is, it is recorded as residue: `required_coverage` is not changed.
- Verify-first clause (D1): reproduce the missing-step shape as a fixture at `1d2b559fd` before editing. A shape that does not
  reproduce is reported and its Done-when narrowed in the PR.
- Verify-first clause (D2): settle the `UNDETERMINED` consumer and the row shape first; read at least three real `kind=build` rows
  before choosing between the two branches.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pre_merge_gate.py` — the head binding loop, the reader, the label import, the status read (D1, D3, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py` — `_derive_head_dependence`; a sibling reader only if the outline chooses it (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` — `parse_row_scope`, the row refusal, the comments (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — the not-gated disposition, the visibility sentence (D1, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` — the waiver readers sentence (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` — the scope-flag reading (D2)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_lb55_merge_head_binding.py` — the waiver, declaration and fallback fixtures (D1, D3, D4)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_pre_merge_gate.py` — the label and classifier fixtures (D3)
- OBSERVED: `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py` — the scope fixtures (D2, D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_discovery.py` — only if the unreadable-document bullet needs a change at its source (D1; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` — the consumer of the verdict (D2; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-execution.md` — only if the call-shape documentation changes (D2; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py` — consulted, edited only if D1 reuses its reader (D1; verify-at-outline)

## Dependencies and Sequencing

- **Depends on:** the merge of PLAN-LB-107 (`1d2b559fd`), which is on the base branch.
- **Overlaps with parked PLAN-LB-46** (`branch-cleanup.md`, `manage-status/SKILL.md`) and **parked PLAN-LB-75** (the directory
  `test/plan-marshall/phase-6-finalize/`): re-ground both against this plan's line moves before either is un-parked. If either is
  un-parked first, sequence this plan after it.
- **Overlaps with the running PLAN-LB-110 (Maven consumer test truth)** on the Maven build-row shape that D2 reads (`-pl X -am` rows);
  whether the two interact is not checked. The disjointness gate decides the pairing at emit; this spec names explicit files, not
  directories.
- **Independent of PLAN-LB-119** (review gate): no shared file is known; the gate's read at emit decides.
- **Adjacent to** (left untouched): the dispatcher's re-entry table and the waiver writer (`phase-6-finalize/SKILL.md`,
  `_cmd_loop_back.py`), the grant verb and its labels, the coverage vocabulary (`required_coverage`).
- **Owed outside this plan, operator-run:** a harness sync after merge. No verb or flag is added unless the outline decides D1 needs
  one; then an executor regeneration is owed and the landing says so.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-120-merge-and-push-gate-truth-fixes.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

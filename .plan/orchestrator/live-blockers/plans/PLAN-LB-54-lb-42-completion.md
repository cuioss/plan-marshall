# PLAN-LB-54: Finish the outline Q-Gate integrity work PLAN-LB-42 left partial

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-54-lb-42-completion.md` and is queued as one row file,
> `queue/PLAN-LB-54.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-15 from the adversarial landing analysis of PLAN-LB-42 (#1773, `8442a5e33`),
> `landings/PLAN-LB-42.md`. PLAN-LB-42 graded 0 met / 4 partial against its spec. Its outline
> merged four deliverables into one and lost their Done-whens. **Each deliverable below is its own
> deliverable in the outline, and each Done-when is its own success criterion. Do not merge
> them.** A criterion that says "fails at `8442a5e33`" is evidenced only by a run against that
> tree, never by a green run at HEAD.

## Objective

PLAN-LB-42 made the outline Q-Gate report "not run" in prose, but left the parts that make that
report checkable undone:

- the hash verb does not persist anything;
- the phase-keyed skip exists only as prose and no test executes it;
- the domain-narrowing docs still describe clearing the list as correct;
- the shipped change introduced five regressions.

## Deliverables

1. **The `deliverable-hashes` verb owns the artifact and the skip decision.**
   - `manage-solution-outline deliverable-hashes --phase P --write` persists the phase-keyed
     `work/deliverable-hashes.toon`, with one row per deliverable and a `__whole_outline__:{phase}`
     row. The agent no longer writes the artifact by hand (`q-gate-validation.md` L210-227).
   - A `--check --phase P` form returns, per deliverable and for the whole outline, `skip` or
     `run`, applying the same-phase rule. A skip reads `not run (cached from phase {X})`.
   - The validator-input snapshot (assessments, task list) is hashed by the script from the
     `manage-*` reads, not transcribed verbatim by the agent (L159-173).
   - The orchestrator re-run readers (`planning-outline.md` L203, L504) call `--check` instead of
     hashing by hand.
   - Fix the verb's defects:
     - the `deliverable_count` cross-check is computed but never compared (L622-637);
     - an `OSError` from `read_bytes` is uncaught (L608);
     - the module docstring omits the verb;
     - `q-gate-validation.md:231` "no new script surface" contradicts L134.

   *Done when:* tests, each failing at `8442a5e33`:
   - with a two-deliverable outline, editing one deliverable changes exactly that row and the
     aggregate;
   - a 3-outline artifact makes `--check --phase 4-plan` return `run` for every row;
   - a same-phase unchanged outline returns `skip`;
   - `--write` writes the artifact that `--check` reads.

2. **An empty assessment store does not switch the cache off, and "not run" is reported
   completely.**
   - When the store is empty, the full-pass gate still records `__whole_outline__:{phase}`
     (L229, L1044), and Step 5 is scoped to the phase that runs it. This undoes regression 2.
   - The not-run outcome names the outline skill resolved by the existing
     `manage-config resolve-outline-skill` verb, in the return TOON, not only in a log line
     (L283-289).
   - §2.2 Pass/Fail (L291-295) and the Verification Criteria Matrix (L1053, L1065) gain the
     not-run state.
   - The Output carries a field for a cached whole-outline skip.
   - The Inputs (L30-35) declare `activation_context`.
   - The vacuous `test_record_and_count_steps_take_phase_from_context` is replaced by a test
     that pins Steps 6 and 8 by section.

   *Done when:*
   - a test with an empty store and an unchanged outline reaches the skip on the second pass;
   - a test reads the outline skill in the not-run return;
   - the Steps 6/8 test fails at `8442a5e33^`.

3. **Domain narrowing: one parser, an honest error, no side door.**
   - The deliverable leg reads `domain:` through `_plan_parsing` (`extract_deliverables` →
     `metadata.domain`) instead of the hand-written parser (`_cmd_domain_narrow.py` L252-298),
     so a case or backtick or comment variant is no longer dropped.
   - `would_empty` fires only when narrowing dropped a user domain. An already-empty or
     `system`-only set with nothing dropped is a success no-op, as before `8442a5e33`.
   - Remove `--apply` (`manage-config.py:953`, `_cmd_domain_narrow.py` L495-533) together with
     its `domains_unreadable` overload and the `_APPLY_REREAD_ERROR` indirection. Nothing calls
     it; the write path is `manage-references`.

   *Done when:* tests, each failing at `8442a5e33`:
   - `**Domain:** \`java\`` and `domain: Java  # main` are retained;
   - an already-empty set returns success;
   - `domain-narrow --apply` is rejected by argparse.

4. **The outline docs describe the shipped contract.**
   - `phase-3-outline/SKILL.md` § Domain Narrowing step 3 (L633) is rewritten so `retained_csv`
     is never empty on success, and the "clear the list — the correct outcome" sentence is gone.
   - L604 no longer says "three-outcome contract".
   - `light-lane.md:244` is aligned.
   - Both callers branch on `would_empty` separately from the "could not evaluate" path
     (SKILL.md L596/L601, light-lane L207/L212), with log text that says the run evaluated and
     refused.

   *Done when:* a doc-contract test asserts that none of the three stale phrases remains and that
   `would_empty` has its own branch in both callers. It fails at `8442a5e33`.

Split guard: four deliverables, one surface family (the outline Q-Gate and domain narrowing).

## Claim Labels

- OBSERVED: `manage-solution-outline.py` at `8442a5e33` defines no `--write`; `--phase` is "provenance only" (`manage-solution-outline/SKILL.md` § deliverable-hashes) — orchestrator spot check.
- OBSERVED: `8442a5e33^:q-gate-validation.md` contains `--phase {phase}` three times, so the shipped Steps 6/8 test passes pre-fix — orchestrator spot check.
- OBSERVED: `phase-3-outline/SKILL.md:633` still ends "… which `set-list` accepts as 'clear the list' — the correct outcome for that state" — orchestrator spot check.
- OBSERVED: `_cmd_domain_narrow.py:479-493` returns `would_empty` whenever `retained_user` is empty, independent of `dropped` — orchestrator spot check.
- OBSERVED: `manage-config.py:953` registers `--apply` — orchestrator spot check.
- OBSERVED: the hand-written marker match is case-sensitive and the value regex is `[A-Za-z0-9_.-]+\s*$` (`_cmd_domain_narrow.py` L257-261); `_plan_parsing._extract_metadata_block` (L310-325) uses IGNORECASE (delegated agent).
- OBSERVED: the full-pass gate withholds the `__whole_outline__` row unless Step 5 passed, and Step 5 is not phase-scoped (`q-gate-validation.md` L229, L910-933, L1044) (delegated agent).
- HYPOTHESIS: an absent `__whole_outline__` row makes the orchestrator re-run gate re-dispatch every iteration — confirm at `planning-outline.md` L203/L504 (verify-at-outline).
- HYPOTHESIS: `manage-config resolve-outline-skill` returns the skill the calling phase resolves — confirm with `--help` before naming it (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_narrow.py` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/manage-config.py` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md` (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-3-outline/workflow/light-lane.md` (D4)
- OBSERVED: `test/plan-marshall/manage-solution-outline/test_manage_solution_outline_cli.py` (D1)
- OBSERVED: `test/plan-marshall/q-gate-validation-agent/test_qgate_outline_integrity_regression.py` (D1, D2)
- OBSERVED: `test/plan-marshall/q-gate-validation-agent/test_q_gate_validation_worktree_linter.py` (D2)
- OBSERVED: `test/plan-marshall/manage-config/test_cmd_domain_narrow.py` (D3)
- OBSERVED: `test/plan-marshall/manage-config/test_domain_narrow_reason_codes_documented.py` (D3)

## Dependencies and Sequencing

- Depends on: none (PLAN-LB-42 shipped).
- Overlaps with:
  - PLAN-LB-40 (running), possibly on `manage-config.py` — it edits other `manage-config` scripts;
  - PLAN-LB-52 (staged), which reads the outline Q-Gate for D1.

  The gate will ask.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-54-lb-42-completion.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

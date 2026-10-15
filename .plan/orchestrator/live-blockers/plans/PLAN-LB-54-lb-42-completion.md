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

PLAN-LB-42 made the outline Q-Gate report "not run" in prose, but left two high-severity holes:

- the phase-keyed skip that decides whether a validator runs exists only as prose, executed by the
  agent, so a "pass over zero validator runs" (the Open Defect graded high) is still possible;
- the new deliverable-domain claim leg parses `domain:` with a narrower grammar than the outline
  parser and silently drops a declared domain, and `would_empty` now errors on a plan whose domain
  set was already empty (a regression on `main`).

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

   *Done when:* tests, each failing at `8442a5e33`:
   - with a two-deliverable outline, editing one deliverable changes exactly that row and the
     aggregate;
   - a 3-outline artifact makes `--check --phase 4-plan` return `run` for every row;
   - a same-phase unchanged outline returns `skip`;
   - `--write` writes the artifact that `--check` reads.

2. **Domain narrowing: one parser and an honest error.**
   - The deliverable leg reads `domain:` through `_plan_parsing` (`extract_deliverables` →
     `metadata.domain`) instead of the hand-written parser (`_cmd_domain_narrow.py` L252-298),
     so a case or backtick or comment variant is no longer dropped.
   - `would_empty` fires only when narrowing dropped a user domain. An already-empty or
     `system`-only set with nothing dropped is a success no-op, as before `8442a5e33`.

   *Done when:* tests, each failing at `8442a5e33`:
   - `**Domain:** \`java\`` and `domain: Java  # main` are retained;
   - an already-empty set returns success.

Split guard: two deliverables.

**Dropped 2026-10-15 as medium** (operator instruction: high and critical only on the OpenCode
work; `settled.md` § "Dropped 2026-10-15"): the empty-store hash-cache regression and the
not-run reporting completeness (former D2), the `--apply` side door and its `domains_unreadable`
overload, the stale outline docs (former D4), and the verb's minor defects (an unused count
cross-check, an uncaught `OSError`, the docstring, the stale "no new script surface" line).

## Claim Labels

- OBSERVED: `manage-solution-outline.py` at `8442a5e33` defines no `--write`; `--phase` is "provenance only" (`manage-solution-outline/SKILL.md` § deliverable-hashes) — orchestrator spot check.
- OBSERVED: `_cmd_domain_narrow.py:479-493` returns `would_empty` whenever `retained_user` is empty, independent of `dropped` — orchestrator spot check.
- OBSERVED: the hand-written marker match is case-sensitive and the value regex is `[A-Za-z0-9_.-]+\s*$` (`_cmd_domain_narrow.py` L257-261); `_plan_parsing._extract_metadata_block` (L310-325) uses IGNORECASE (delegated agent).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_narrow.py` (D2)
- OBSERVED: `test/plan-marshall/manage-solution-outline/test_manage_solution_outline_cli.py` (D1)
- OBSERVED: `test/plan-marshall/q-gate-validation-agent/test_qgate_outline_integrity_regression.py` (D1)
- OBSERVED: `test/plan-marshall/manage-config/test_cmd_domain_narrow.py` (D2)

## Dependencies and Sequencing

- Depends on: none (PLAN-LB-42 shipped).
- Overlaps with:
  - PLAN-LB-52 (staged) on the `manage-solution-outline/scripts/` directory (its snapshot verb).
  - PLAN-LB-40 (running): none declared (it edits other `manage-config` scripts).

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

# PLAN-10: An `always_on`-only resolve is not evidence about this plan

epic: operator-ux
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-10-always-on-is-not-a-resolve.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

PLAN-01 made a zero narrative match over-provision instead of prompting — but only when the
inclusion union is EMPTY. A single `always_on` domain is enough to short-circuit that safety
net, and the plan then resolves to that domain alone. The failure is epistemic:
**`always_on` is evidence about the PROJECT, `glob_matched` is evidence about THIS PLAN, and
the code treats them as interchangeable.** A resolve backed only by `always_on` has found
nothing whatsoever about the work at hand — it is the same state as an empty union, wearing a
result. Observed live: a Python-heavy plan (`target.py`, `generate.py`, pytest suites)
resolved to `plan-marshall-plugin-dev` alone and omitted `python`, whose standards it needed.
Split the guard so only PLAN-SPECIFIC evidence suppresses over-provisioning.

## Deliverables

1. `_cmd_domain_detect.py`: replace the `if inclusion_union:` guard on the zero-narrative-match
   path with a test on plan-specific evidence only. A non-empty `glob_matched_set` resolves on
   the legs (that leg matched this plan's file signal); a union consisting solely of
   `always_on` domains falls through to the over-provision branch, which unions the offerable
   set on top of the `always_on` domains rather than replacing them.
2. A distinguishable `reason` for the new path (e.g. `over_provisioned_always_on_only`), kept
   separate from both `inclusion_only_resolve` and `over_provisioned_resolve` — three
   different epistemic states must not share a token.
3. `standards/skill-domains.md` and `manage-config/SKILL.md`: state the
   project-evidence / plan-evidence distinction explicitly as the rule governing the branch,
   so a future reader cannot restore the collapse by simplifying the condition.
4. Tests in `test/plan-marshall/manage-config/test_cmd_domain_detect.py`: zero narrative match
   with `always_on` only → over-provisions AND retains the `always_on` domain; zero match with
   a real `glob_matched` hit → resolves on the legs, unchanged; zero match with both → resolves
   on the legs; empty union → `over_provisioned_resolve`, unchanged.

## Claim Labels

- OBSERVED: The short-circuit is literal and unconditional — `if inclusion_union:` returns
  `reason='inclusion_only_resolve'` with `ambiguous: False` BEFORE the over-provision branch is
  reached. Read at
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_detect.py`
  § the zero-narrative-match block, at HEAD after PLAN-01 (#1380).
- OBSERVED: `plan-marshall-plugin-dev` carries `always_on: true` and `file_globs: []` in this
  project; `python` carries `always_on: false` and `file_globs: ['**/*.py']`. Read via
  `manage-config skill-domains get --domain {d}`. So the observed instance is exactly the
  always_on-only path, and `python` was reachable by the glob leg had that leg had a file
  signal.
- OBSERVED: At init the glob leg's file signal is path-like tokens extracted from the
  NARRATIVE, not a real file list — `--affected-files` is supplied only later, by
  `phase-2-refine`. Read at `manage-config/SKILL.md` § `domain-detect`. A prose request naming
  no `.py` path therefore leaves the glob leg empty even in a project whose globs are correct.
- OBSERVED: The executing agent escalated to the operator DESPITE `ambiguous: false`. The
  documented flow raises no prompt on that branch, so the prompt was the agent working around a
  resolve it judged wrong. ⛔ A caller that does not trust its detector's verdict is itself
  evidence for this defect — and a second-order UX cost, since the epic's goal is fewer prompts.
- HYPOTHESIS: Unioning the offerable set ON TOP of the `always_on` domains (rather than
  replacing them) is correct and breaks no consumer — confirm/refute at the
  `references.domains` consumers swept by PLAN-01 (verify-at-outline).
- HYPOTHESIS: `phase-2-refine`'s re-merge would have added `python` from the real
  `affected_files`, so this defect bites hardest when refine does not run — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/phase-2-refine/SKILL.md` § Domain Re-merge and at
  whatever gates refine's execution (verify-at-outline). ⛔ Note that file was MODIFIED by
  PLAN-01 without being declared; read it at current HEAD, not from any prior description.
- Verify-first clause: settle at outline whether `always_on` is the only project-scoped leg. If
  a future leg is added with the same property, the guard must test a *category* of evidence
  rather than enumerate `always_on` by name.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_detect.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/standards/skill-domains.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md`
- OBSERVED: `test/plan-marshall/manage-config/test_cmd_domain_detect.py`
- REALIZED: `marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md` — added 2026-09-03
  from the plan's realized footprint (`git diff --name-only main...feature/always-on-is-not-a-resolve`),
  which is 5 files against the 4 declared here. Declared late, in the same act that observed it.
  ⛔ This is the file PLAN-08 collides with, so the omission mattered: the disjointness gate was
  saved only because `corpus cross-check` compares a launched plan by its REALIZED footprint
  rather than by this declaration.

## Dependencies and Sequencing

- Depends on: none. PLAN-01 has landed, so the branch this plan corrects exists at HEAD.
- Overlaps with: PLAN-02 and PLAN-03 (`skill-domains.md`, `manage-config/SKILL.md`), PLAN-03
  (`_cmd_domain_detect.py` — hard sequence, this plan first: PLAN-03 narrows what this plan
  widens, and narrowing a set that is still wrongly narrow is meaningless).
- Adjacent to: `_cmd_skill_domains.py` — PLAN-02's surface. This plan changes how the detector
  WEIGHS the legs; PLAN-02 changes what feeds one of them. Complementary, and neither
  substitutes for the other: PLAN-02 would have fixed this INSTANCE (by giving the glob leg
  something to match) but not the CLASS (a project with a blanket `always_on` and no globs
  still resolves blind).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/operator-ux/plans/PLAN-10-always-on-is-not-a-resolve.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

envelope_version=1
sender_type=plan
sender_id=executor-rejects-invalid-invocations-before-spawn
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-09T14:52:41Z

category: improvement
component: plan-marshall:automatic-review
title: A review bot re-litigates decisions the plan already settled, because the rationale lives where the bot cannot read it

## Owed architecture hint

- target `--module`: `default` (cross-cutting — the pattern is not attributable to one module)
- enrich verb: `architecture enrich insight --module default`
- verbatim hint text:

  > When a plan settles a design question deliberately and records the rationale only in its
  > Q-Gate finding store or decision log, an automated reviewer cannot see it and will propose
  > reversing it. Surface a settled decision where the reviewer reads — the code comment or the
  > doc the decision governs — so the review round spends itself on new ground instead of
  > re-arguing closed ground.

## Evidence (within-plan recurrence, threshold 2)

The per-plan sweep aggregated `(module, finding-class, disposition)` over this plan's user-gate
dispositions: 0 `suppressed`, 1 `accepted`, 4 `taken_into_account`. One tuple cleared the
`preference_min_recurrence: 2` threshold — `(default, pr-comment, taken_into_account)` at **4**.

Two of the four are the substantive half, and both are explicit reversals of decisions this branch
had already taken and recorded:

- `c80c7d` proposed deriving the executor's universal-flag accept-set instead of mirroring it —
  reversing qgate `c32ae7`, which had settled the mirror deliberately because the generated
  executor dispatches before any shared directory is on `sys.path` and therefore cannot import the
  shared module. The mirror is pinned by an ast-based parity test comparing maps, with a negative
  control.
- `b89631` proposed adding a total wall-clock budget to the edit-time derivation — reversing qgate
  `27509a`, which had settled the same observation the other way by scoping the documentation,
  because a budget would make a build-gating verdict host-speed-dependent by silently shrinking the
  accept-set.

The other two are bot acknowledgments carrying no proposal, dispositioned to keep the store
terminal rather than because a judgement was owed.

## Why this generalizes past the instance

Both reversals were correct observations with wrong remedies, and in both cases the reason the
remedy was wrong had already been written down — in a finding-store resolution the reviewer has no
access to. The cost is not the disposition itself but the round trip: each one consumed a triage
slot and an operator decision to re-establish a conclusion the plan had already reached with
evidence.

The generalization deliberately does not say "ignore the reviewer" — both findings were worth
raising. It says the rationale for a settled decision belongs at the site the decision governs,
where the next reader (human or bot) meets it.

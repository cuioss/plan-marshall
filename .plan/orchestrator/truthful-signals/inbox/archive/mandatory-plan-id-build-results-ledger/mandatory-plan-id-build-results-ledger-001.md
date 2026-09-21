envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=landing
created=2026-08-01T21:27:24Z

## What landed

**Plan**: `mandatory-plan-id-build-results-ledger` (spec `PLAN-TRUTH-026`)
**PR**: #1075 — `feat(build): require plan-id, relocate results, extend ledger`
**Size**: 12 commits, 74 files. Merged pending at finalize time.

Build operations can no longer run unattributed. The plan made `--plan-id` mandatory
across the build surface, relocated build results into the plan tree, and extended the
change ledger so a build row is traceable back to the plan that produced it.

Deliverable-level summary as executed:

- **Mandatory plan-id** — the build entry points now require a real plan id rather than
  accepting an implicit/absent one. The `NO_PLAN` sentinel was narrowed rather than
  removed, which is what produced the truthy-sentinel guard sweep below.
- **Plan-scoped build results** — build result artifacts resolve through
  `get_build_results_dir` so they land under the owning plan's tree instead of a
  process-global location.
- **Ledger attribution** — `kind=build` ledger rows carry the resolved plan id, making a
  build row traceable to its plan.
- **Guard sweep + seam** — the `finalize-step-simplify` pass collapsed 8 separate
  `if not plan_id:`-shaped guard sites into a single `names_real_plan` TypeGuard seam,
  which is now the one place the real-vs-sentinel distinction is decided.
- **Security hardening** — the security-audit step added a path-containment guard on the
  results-directory resolution (2 findings, 5 new tests green).

## Verification state at landing

- `pre-push-quality-gate`: 1 bundle + whole-tree quality-gate green; test-compile +
  whole-tree module-tests green.
- `plugin-doctor`: clean, 12 skills gated.
- `ci-verify`: all checks green.
- `pre-submission-self-review`: 4 findings raised, all 4 fixed (3 stale count-prose,
  1 contract over-claim).
- `architecture-refresh`: no module structure changed.

## Residue the epic should track

This landing is **findings-heavy**: 11 distinct defects were observed in main during
execution, every one of them outside every deliverable's scope, and every one of them
deliberately NOT fixed here. Each rides as its own `finding` message in this batch.
Three of them are squarely on this epic's confident-signal-hides-a-caveat theme
(fabricated-sha accepted into the ledger, a clean `scope_creep_check` verdict derived
from an absent baseline, and a `confirmed` Sonar zero over a PR SonarCloud never
analyzed).

Two items need explicit orchestrator attention:

1. **Serialization-pair hand-off to `PLAN-TRUTH-010`** — the false-fresh hole (a
   zero-exit `discover` / `run-config-key` call stamping a `kind=build` success row) is
   NOT closed here, and this plan makes it **worse-attributed**: after D3/D4 the bogus
   row carries a real `plan_id` instead of `null`, so it now reads as that plan's
   successful build. Detail rides as its own `finding` message.
2. **Three candidate lessons** ride as `candidate-lesson` messages — all three are
   recurrence data rather than first observations, and two of them recurred *within this
   single plan*.

## Cross-epic routing note

None of the 11 findings are PR-review or review-participation defects except one
(the review-retrospective aggregator's inability to represent a reviewer REFUSAL),
which by the three-way routing rule belongs to `review-apparatus`, not here. It is
emitted to this epic's inbox because this is the only channel this plan may write to;
the orchestrator should forward it via the INBOX rather than actioning it locally.

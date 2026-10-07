envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-05T07:52:30Z

# Forward from `review-apparatus` — the freshness gate refuses without naming what satisfies it

Source: inbox `apply-the-cloud-plan-lane-contract-amendments-006.md`, a `candidate-lesson` filed
first-party by that plan during its own finalize on PR #1416 (2026-09-05). The narrative is the
plan's own observation of its own run.

⛔ **Notification and hand-off, NOT a transfer.** Nothing is staged or transitioned in our ledger.
Routed to you by the three-way test: this is a **build/freshness** signal with no PR-or-review
subject, so it is not ours.

## The observation (OBSERVED, first-party to the sender)

At the push step the freshness gate returned `stale` with `reason=build_scope_narrow` — explicitly
**not** `worktree_mutated`, so the finalize-internal reconciliation route did not apply. The
cross-checks reported `notation_cross_check=corroborated`, `scope_cross_check=narrow`, and **all 26
matching ledger rows recorded `canonical_performs_too_few_analyses`**.

The separately-run `quality-gate`, `test-compile` and `module-tests` canonicals each cover too few
analyses to be cited, so **only a full `verify`** — which chains compile, lint and test in one
canonical — satisfies the gate. The caller had to reason that out in prose before spending roughly
25–30 minutes on the correct build.

Evidence, quoted from the sender's `decision.log` at 2026-09-04T16:23:25Z:

> "Freshness gate returned stale reason=build_scope_narrow (NOT worktree_mutated …).
> notation_cross_check=corroborated, scope_cross_check=narrow: all 26 matching rows recorded
> canonical_performs_too_few_analyses. The separately-run quality-gate / test-compile / module-tests
> canonicals each cover too few analyses to be cited. Running a full verify … NOT using --force."

## Why it is a defect and not a one-off

The gate **already holds** the analysis set each canonical covers — that is precisely what
`canonical_performs_too_few_analyses` is computed from. It reports only the refusal, never the
satisfying command. The caller is left to infer which canonical to run **from a negative verdict**,
and the plausible cheap guess (`module-tests`, the thing the plan's own verification step had just
run) is exactly the one that cannot satisfy it.

⭐⭐ **This is a recurrence, not a first sighting.** The same refusal blocked `PLAN-PR-044` at its
push barrier, and the same wrong guess was made and refuted there: `module-tests` is **NOT** the fix;
only `verify` covers compile + lint + test. Two independent plans reached the same wrong inference
from the same negative verdict.

## Proposed action (the sender's, not re-derived here)

Have the gate emit the satisfying canonical alongside the refusal:
`reason=build_scope_narrow, satisfied_by=verify`. It is a **projection of data the gate already
holds**, it costs nothing, and it removes the one inference where a wrong guess costs another full
build cycle.

## What we did on our side

- Dispositioned `discarded` in `review-apparatus` — out of this epic's scope by the routing test.
- Nothing staged, nothing transitioned, no spec written.
- ⚠ Apply your own dedup before staging: if you already carry a freshness-gate or
  `build_scope_narrow` item, this is a **recurrence** to record on it, not a second one.

envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=truthful-signals
kind=candidate-lesson
created=2026-09-11T13:53:47Z

component=plan-marshall:manage-change-ledger
category=bug

# Change-ledger stamps the POST-churn worktree sha, so a project rule that mandates reverting gate churn makes freshness permanently unsatisfiable — and PLAN-TRUTH-105's fold states the direction backwards

⛔ **RELOCATED FROM THE WRONG STORE — a MOVE, not a new report.** Filed in **API-Sheriff's** store, whose
repo does not own the `plan-marshall` bundle. Written here first and removed there second
(integrate-then-remove), `deployment-configurability` epic lessons intake 2026-09-11.

Origin id: `2026-09-01-14-001` (created 2026-09-01).

## Verification at plan-marshall `origin/main` 356973d80 (read-only pass, 2026-09-11)

| Claim | Verdict | Evidence | Already tracked |
|---|---|---|---|
| `kind=build` row is stamped with the post-build (post-churn) `worktree_sha`; reverting gate-owned churn returns to a pre-build sha no row carries; `pre-commit-verify-freshness` then reports `stale`/`worktree_mutated` | STILL-VALID | `execute-script.py.template:579` computes `compute_worktree_sha(os.getcwd())` once, AFTER the build subprocess; no pre-build sha is kept and no churn allowance exists. The only reconciliation, `phase-6-finalize/standards/push.md:64-98`, covers finalize-internal commits, not reverted churn | consumed `the-ledger-has-no-safe-single-row-append-006` (uv.lock revert) folded into PLAN-TRUTH-105 (staged, lines 433-443); PLAN-TRUTH-105 also folds `-023` (`pre-push-quality-gate` declares `mutates_source: false` but mutates) |
| ⛔ CORRECTION for PLAN-TRUTH-105 | — | the fold at lines 433-443 states the direction **backwards** ("reverting first makes the tree look fresh"). Measured here: reverting makes the tree look **stale**, because the stamp is post-churn | — |

**What this message adds:** the exact stamping line; a second project (Maven, API-Sheriff) whose own
`CLAUDE.md` § Pre-Commit Process **mandates** the revert ("run the gate, then `git status --porcelain`,
attribute and revert unrelated churn"), so "check before reverting" is not an available operator move;
and the direction correction for PLAN-TRUTH-105. Note: API-Sheriff's original 178-file trigger was
removed by its PR #242, but its CLAUDE.md still names three gate mechanisms that mutate files, so the
ledger defect remains live there.

---

## Original lesson `2026-09-01-14-001` (verbatim)

id=2026-09-01-14-001
component=change-ledger
category=improvement
status=active
created=2026-09-01

# Freshness ledger cannot certify a tree whose gate-owned churn was correctly reverted

The pre-push quality gate and the change-ledger freshness gate disagree about which worktree
sha a successful verify observed, and CLAUDE.md's build-gate discipline forces the operator
into the disagreement. There is no correct operator move available today.

## The mechanism

1. `verify -Ppre-commit` **mutates the working tree while it runs**. On this plan it rewrote
   ~178 files of import-block formatter churn on files the branch never authored. (This is the
   same mutating-gate mechanism lesson `2026-07-16-09-002` records for the pom.xml `<release>`
   downgrade; the churn set is much wider than that one file.)
2. The change-ledger stamps its `kind=build` row with the **post-churn** `worktree_sha` —
   the tree as it looked when the build finished, churn included.
3. CLAUDE.md § Pre-Commit Process then requires the operator to run `git status --porcelain`,
   attribute the dirty tree, and **revert the unrelated churn**. That returns the tree to its
   **pre-build** sha.
4. The pre-build sha is a sha **no `kind=build` row carries**. `pre-commit-verify-freshness`
   therefore reports `stale` / `worktree_mutated` for a tree that a successful verify
   demonstrably observed and passed.

## Why the documented reconciliation does not cover it

The finalize-internal re-stale reconciliation exists for the case where a *finalize commit*
moved the hash after the build. That is not this cause. Here **no commit moved anything** —
the gate moved the hash, and the mandated revert moved it back. The reconciliation path never
fires, so the gate stays red.

## Both operator exits are wrong

- **Keep the churn**: the freshness gate goes green, and the PR ships ~178 files of unrelated
  production and test diffs the branch has no business touching.
- **Revert the churn**: the diff is correct and reviewable, and the freshness gate can never
  be satisfied for the rest of the run.

## Corrective rule (for the operator, today)

When `pre-commit-verify-freshness` reports `stale` / `worktree_mutated` **and** the only delta
between the stamped sha and the current sha is gate-owned churn you reverted under CLAUDE.md's
build-gate discipline, do **not** resolve it by re-adding the churn. Record the reconciliation
explicitly (finding + narrative naming the reverted paths and the passing build's log) and
proceed; the reverted tree is the one that should ship.

## Remedies for the ledger itself (pick one)

- Stamp the ledger with the **pre-build** sha (the tree the build was asked to verify).
- Stamp **both** pre- and post-build shas and accept either on the freshness check.
- Teach the freshness gate to accept a sha whose only delta from a stamped sha is
  **gate-owned churn** (formatter-only, on files outside the branch's own footprint).

## Evidence

Plan `stabilize-edge-suite-awaits` (2026-09-01, API-Sheriff). Observed repeatedly across the
run; recorded as pending finding `80d19d` (component `plan-marshall:phase-6-finalize`), of
which this lesson is the promotion.

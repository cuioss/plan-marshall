# PLAN-16: The build machinery is inside the quality gate it enforces

epic: multiplattform
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> **Authored at ingestion** from the PLAN-02 landing analysis, where the gap was found by that
> plan's own round-15 verification and left OPEN. Source evidence: `landings/PLAN-02.md`
> § Follow-Ups item 1.

## Epic Constraints (bind every deliverable)

- **The principles bind:** no target enumeration in contracts, no wire format across the runtime boundary, no universal templating, honest no-ops. Read `../reference/principles.md`.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim.
- **Never edit another plan's surface**, even for an obvious adjacent fix.
- **Confirm the Expected Surface against the tree as the first action** and report any file the work needs beyond it.

## Objective

`marketplace/targets/` — the code that generates every target's output and enforces the Claude
equality gate — is **outside the repository's own lint scope**. `pyproject.toml`'s lint command reads
`marketplace/bundles/ test/ .claude/` and omits it, which PLAN-02 discovered the hard way: a
branch-introduced `ruff I001` in that tree passed every check and reached round 15 of its own
verification loop before a human noticed. PLAN-02 recorded the gap OPEN rather than fixing it, on the
stated reason that widening the scope surfaces pre-existing violations outside that plan's ownership.
This plan owns them. Bring the build machinery inside the gate, and fix what that reveals.

## Deliverables

1. **D1 — The violations are enumerated before anything is fixed.** Run the linter against `marketplace/targets/` and write the full violation set into the PR body and the inbox message: rule, count, and file distribution. ⛔ **Enumerate before fixing** — the size of this set is the plan's actual risk, and a run that starts fixing has no baseline to report against. If the set is large enough that fixing it in one PR is unreviewable, **stop and report**: the orchestrator splits it by rule class.
   *Done when:* the PR body carries the violation set with counts per rule and per file.
2. **D2 — The scope is widened and the violations are fixed.** `pyproject.toml`'s lint command includes `marketplace/targets/`, and the tree passes. ⛔ **Fix, never suppress** — a blanket `noqa` or a per-rule exclusion re-creates the gap under a different name. A rule that genuinely should not apply to this tree is disabled **with a stated reason in the PR body**, and that is a finding, not a routine step.
   *Done when:* the lint command covers `marketplace/targets/`, the tree passes, and every suppression carries a reason.

⛔ **Deliberately two deliverables, and deliberately small.** The temptation is to widen the scope to
every remaining uncovered path at the same time. Resist it: `marketplace/targets/` is the tree with a
*demonstrated* escape, and a scope-widening plan that also fixes three other trees cannot be reviewed
against the escape that motivated it. Other uncovered paths are a reported finding.

## Out of Scope

- **Widening the lint scope to any other uncovered path.** Report them; do not fix them here.
- **Changing lint rules, the ruff version, or the quality-gate structure** — this plan changes *coverage*, not policy.
- **`marketplace/targets/` behaviour.** ⛔ D2 is a lint-compliance change. A violation whose fix would change behaviour is **reported, not made** — that is a different plan.

## Claim Labels

- OBSERVED: `pyproject.toml:98` reads `lint = "uv run ruff check marketplace/bundles/ test/ .claude/"` and omits `marketplace/targets/` entirely — re-derived at HEAD `2cd1a19c`. Line number is a lead; locate by content.
- OBSERVED: the escape is demonstrated, not hypothetical — PLAN-02's round 15 found a branch-introduced `ruff I001` in `marketplace/targets/` that had passed every check. Read at `archive/020-target-scoped-components/report-01.md`.
- OBSERVED: PLAN-02 recorded the gap OPEN in its § Residue with the stated reason (pre-existing violations outside its ownership), rather than fixing it. This plan is the draw.
- HYPOTHESIS: the pre-existing violation set is small enough to fix in one reviewable PR — D1 settles it (verify-at-outline). ⛔ **If it refutes, halt and report** rather than shipping an unreviewable diff; the orchestrator splits by rule class.
- HYPOTHESIS: no violation's fix changes behaviour — confirm/refute per violation during D2 (verify-at-outline). A behaviour-changing fix is reported and deferred, not made.

## Expected Surface

⛔ **D1 determines the file set; only the lint-command edit is knowable in advance.** The glob below
is the honest statement of breadth — do not treat any single file under it as pre-committed.

- OBSERVED: `pyproject.toml` — D2, the lint command only (the one certain edit)
- OBSERVED: `marketplace/targets/generate.py` — D2, representative anchor inside the newly-covered tree; edited only if it carries violations
- HYPOTHESIS: `marketplace/targets/**` — D2, whichever files carry violations (verify-at-outline: D1 determines the set)

## Dependencies and Sequencing

⛔ **Behaviour excluded inside an in-scope tree.** `component_targets.py` is PLAN-11's and
`body_transform_engine.py` is PLAN-05's *for behaviour*. A **lint fix** inside either file is in
this plan's scope; a **behaviour change** is not. Report rather than make one.

- Depends on: none.
- Overlaps with: **PLAN-05** and **PLAN-11** on `marketplace/targets/**`. ⛔ Not concurrent with either.
- **Preferred first among the three.** Running this before PLAN-05 and PLAN-11 means the lint gate covers the engine *before* those plans add code to it — otherwise each of them ships code into an unchecked tree and this plan later has to lint their output too, conflating "pre-existing violations" with "violations the neighbours just added".
- Overlaps with: **PLAN-02** (landed) — `pyproject.toml` was last touched by its PyYAML dependency addition. No live collision.
- Concurrent with: PLAN-04, PLAN-13 (both fully disjoint), and any WS-01 or WS-03 plan.

## Verification

- The full verify gate, read from its exit status **and** its result `status`/`errors[]` — ⛔ the wrapper exits 0 even on failure, so neither alone is sufficient. This matters more here than usual: the plan's whole subject is a check that silently passed.
- **The escape pin:** plant a deliberate violation in `marketplace/targets/` and assert the lint command now fails on it — red-first, before the fix. Without this, the widened scope is asserted rather than shown, which is exactly the failure mode that produced this plan.
- `generate.py --target all` exits 0 on the edited tree and the Claude equality check still passes, confirming D2 changed no behaviour.
- The PR body carries D1's violation set, D2's fix disposition per rule, every suppression with its reason, and any other uncovered path found along the way.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/multiplattform/plans/PLAN-16-lint-scope-marketplace-targets.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write.

# PLAN-03: The build path records what it actually did

epic: tooling-truthfulness
workstream: WS-03

> Staged plan spec — one shippable unit of work. SELF-SUFFICIENT.

## Epic Constraints (bind every deliverable)

- **ADR-019 binds reflexively:** every guard is red-first.
- **Confirm the Expected Surface against the tree as the first action.** ⛔ A surface expansion updates this section IN THE SAME ACT.

## Objective

The change ledger is the machine-local record of what the build path ran. For one `multiplattform`
plan it recorded SIX entries, all failures, for a run whose gate was green — because the daemon route
failed on this host and the gate fell back to `in_process`, which writes no entry at all. A reader
querying the ledger for that plan sees only failures and would reasonably conclude it shipped
ungated. Separately, the executor's self-heal walks the wrong plugin-cache depth, surfaced only
because a run happened to trip it.

⛔ **Misleading evidence is worse than missing evidence** — it defeats the check rather than merely
failing to answer it. That is this plan's whole subject.

## Deliverables

1. **D1 — every gate route leaves a ledger record of what it ran.** The `in_process` route writes no `kind=build` entry, so its outcome is invisible while the failed daemon attempts that preceded it remain. ⛔ The remedy is NOT to suppress the failure entries — they are true. It is that the successful route must be recorded too, and that the entry names WHICH route ran.
   *Done when:* an `in_process` gate run produces a ledger entry carrying its route, its exit code and its test population; a red-first test drives the `in_process` path and asserts the entry exists. ⚠️ A matched control is required: the daemon route's entry must be unchanged, or the fix has moved the problem.
2. **D2 — the executor self-heal resolves the depth it claims to.** The self-heal walks the wrong plugin-cache depth. ⛔ Re-derive the actual behaviour before scoping — this row entered the ledger from a single observed run, not from a measurement, and this epic has repeatedly found such rows already closed.
   *Done when:* either the walk resolves correctly with a red-first test pinning the depth, or a positive account records that it was already fixed, naming the commit or symbol that closed it.

## Claim Labels

- OBSERVED: the change ledger holds six `kind=build` entries for the `runtime-fact-prose-and-single-sources` worktree and all six are failures (`exit -1` / `exit 1`) — queried directly 2026-09-09. CI for the same PR (#1458) is `overall_status: success` with `verify / verify` SUCCESS in 1186s.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: the six kind=build failure entries for runtime-fact-prose-and-single-sources and the green CI (#1458 overall_status success) are a recorded historical observation; the mechanism claim (in_process writes nothing) is separately corroborated at claim 2
- OBSERVED: the operator's account that daemon mode could not build the worktree project-dir on this host (`pwx` unresolved) and the gate ran `in_process` — trusted as the operator's own narrative, and consistent with the ledger's shape.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: operator narrative that daemon mode could not build the worktree project-dir and the gate fell back to in_process - trusted as operator's own narrative; consistent with the six-failure ledger shape and the in_process omission corroborated at claim 2
- HYPOTHESIS: `in_process` writes no entry *by omission* rather than by design — confirm/refute at `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_execute.py` before scoping (verify-at-outline). ⛔ If the omission is deliberate, D1 becomes a decision about whether that deliberate choice is right, not a bug fix, and the PR body must say so.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: _pyproject_execute.py in-process leg contains no change-ledger/kind=build write path; the daemon-routing seam and self-heal are the only in_process mentions - omission corroborated
- HYPOTHESIS: the self-heal depth defect is still live — confirm/refute by driving it, not by reading the ledger entry (verify-at-outline). ⛔ **Six ledger entries surveyed for this epic were already closed.** Treat this row as a lead.
  - verdict: unverifiable | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: self-heal depth correctness requires driving the walk at runtime (generate_executor.py max_depth=6 exists but whether it walks the WRONG cache depth is not settleable from a static read) - per spec, the row is a lead, re-derive by driving
- Verify-first clause: if D2's defect is already closed, the plan ships D1 alone and records D2's positive account. That is a legitimate outcome, not a shortfall.
  - verdict: unverifiable | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: whether D2's defect is already closed is the launched plan's re-derivation (drive it), not a source-settleable fact at HEAD - spec's own verify-first clause names driving as the confirm/refute

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_execute.py` — D1, D2
- OBSERVED: `test/plan-marshall/build-pyproject/**` — the red-first guards
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/**` — only if D1's entry cannot be written through the existing append surface (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` and `test/plan-marshall/tools-script-executor/**` — only if D2's self-heal lives there rather than in the build path (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: nothing else in this epic — no other member touches the build path.
- Adjacent to: PR **#1445**, open, which documents `--project-dir` and basetemp gate footguns. ⛔ Read it before scoping D1: the daemon-route failure that caused this defect is in its subject area, and it may already state part of the account.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/tooling-truthfulness/plans/PLAN-03-build-path-evidence.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO file under
`.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.

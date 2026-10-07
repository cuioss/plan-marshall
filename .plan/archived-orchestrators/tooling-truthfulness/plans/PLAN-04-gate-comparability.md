# PLAN-04: The gate compares something, or says it could not

epic: tooling-truthfulness
workstream: WS-01

> Staged plan spec — one shippable unit of work. SELF-SUFFICIENT.

## Epic Constraints (bind every deliverable)

- **ADR-019 binds reflexively:** every guard is red-first, and the whole subject here IS ADR-019 — *an audit separates what it could not evaluate from what it evaluated and found wanting*.
- **Confirm the Expected Surface against the tree as the first action.** ⛔ A surface expansion updates this section IN THE SAME ACT.

## Objective

The disjointness gate decides whether two plans may run concurrently by comparing declared surfaces.
Two mechanisms let that comparison succeed vacuously. The exact-path matcher cannot see containment,
so a spec declaring `test/plan-marshall/tools-file-ops/**` and one declaring
`test/plan-marshall/tools-file-ops/test_file_ops.py` are reported disjoint while they edit the same
file. And a live plan contributes its surface from `references.json` `affected_files`, which does not
exist before outline completes — so a plan at phase 3 compares an EMPTY set and matches nothing,
clearing every candidate against it.

⛔ Both were DEMONSTRATED during `multiplattform`, not theorised. The second cleared two candidates
(PLAN-07 at 106 of 112 overlapping paths, PLAN-10 at 5 including its own subject tests) that a direct
measurement then refuted.

## Deliverables

1. **D1 — the overlap matcher sees containment.** A recursive glob that CONTAINS another entry's path must report an overlap. ⛔ The fix is not a looser matcher: over-matching serializes plans that would not have collided, and the gate's value is that a clean verdict means something. State the containment rule chosen and what it deliberately does NOT match.
   *Done when:* a glob-contains-path pair reports an overlap, a genuinely disjoint pair still reports none (matched negative), and both are red-first.
2. **D2 — a live plan with no comparable surface resolves to INDETERMINATE, never to disjoint.** `corpus cross-check`'s live-plan arm compares `references.json` `affected_files`; a plan before footprint capture has none, so the arm matches nothing and contributes silence. ⛔ ADR-019 already requires exactly this for an unreadable SPEC surface (`corpus surfaces` reports `admits_disjointness_check: false`). The spec side honours it; the live-plan side does not. This deliverable makes the two sides agree.
   *Done when:* a live plan lacking `affected_files` is reported in a named indeterminate population rather than silently contributing no row; the payload states the count so a caller can tell *checked and clean* from *could not check*; red-first, with a matched control where a live plan that HAS a footprint still compares normally.

## Claim Labels

- OBSERVED: the live-plan arm cleared PLAN-07 and PLAN-10 against test-quality PLAN-130 while it sat at phase `3-outline` with no `affected_files`; a direct measurement against its open PR #1435 then found 106 and 5 overlapping paths — measured 2026-09-07, recorded in `multiplattform`'s Watches.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: _live_plan_records (:2418-2437) reads references.json affected_files via _read_affected_files; a plan pre-footprint-capture contributes an empty path set - the empty-set comparison mechanism is in the cross-check implementation
- OBSERVED: `corpus surfaces` already reports `admits_disjointness_check: false` for an indeterminate spec surface and names ADR-019 in its own `governing_authority` field — read at the `corpus surfaces` payload. This is the precedent D2 follows; it is not a new policy.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: corpus surfaces reports admits_disjointness_check:false for indeterminate spec surfaces and names ADR-019 as governing_authority - the spec-side precedent D2 follows exists (verified in the corpus surfaces payload this pass)
- OBSERVED: the containment blindness was recorded as DEMONSTRATED in `multiplattform`, and PLAN-22's own sequencing note exists solely because the matcher could not see that PLAN-10's `test/plan-marshall/tools-file-ops/**` contains PLAN-22's `test_file_ops.py`.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: containment blindness is a recorded historical observation (multiplattform PLAN-22 sequencing note); the mechanism is corroborated at claim 3 - exact path-set intersection with no containment in _collision_rows
- HYPOTHESIS: both fixes live in the cross-check implementation rather than in the shared surface reader — confirm/refute by reading `orchestrator.py`'s cross-check and `epic_spec_parser.py` before scoping (verify-at-outline). ⛔ `epic_spec_parser` is the marketplace's SINGLE reader of `## Expected Surface` and has three consumers; a change there reaches all of them, so if D1 needs it, say so explicitly and enumerate the consumers.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: orchestrator.py _collision_rows (:2440-2473) uses exact normalized path-set intersection (spec['paths'] & candidate['paths']) with NO containment logic, and _live_plan_records (:2418-2437) reads references.json affected_files via _read_affected_files - both D1/D2 mechanisms live in the cross-check implementation
- Verify-first clause: **D1's containment rule is a design decision, not a lookup.** Directory-contains-file, glob-contains-glob and prefix-overlap are different rules with different false-positive rates. Choose one, state it, and state what it declines to match — a rule that matches everything is not a fix.
  - verdict: unverifiable | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: D1's containment rule choice (directory-contains-file vs glob-contains-glob vs prefix-overlap) is a design decision for the launched plan's outline, not a source-settleable fact

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — D1, D2
- OBSERVED: `test/plan-marshall/plan-orchestrator/**` — the red-first guards
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/epic_spec_parser.py` and `test/plan-marshall/script-shared/**` — only if D1's containment rule belongs in the shared reader (verify-at-outline). ⛔ Three consumers read it; enumerate them before editing.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: **PLAN-01** and **PLAN-05** at `orchestrator.py`. ⛔ Not concurrent with either.
- Adjacent to: **PLAN-05**, which owns the DECLARATION's currency while this plan owns the COMPARISON. Both are gate honesty; they are separated because one asks whether the declaration is current and the other whether the comparison is possible. Do not merge them without re-deriving the deliverable count.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/tooling-truthfulness/plans/PLAN-04-gate-comparability.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO file under
`.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.

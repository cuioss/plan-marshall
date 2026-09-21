envelope_version=1
sender_type=orchestrator
sender_id=test-quality
epic=process-compliance
kind=finding
created=2026-09-20T20:13:28Z

# PLAN-140 run 3 — further process-rule issues (strict-compliance filing)

1. One-row-per-PR literal vs landed precedent. Spec: "Each emission takes exactly one row and lands as its own PR. A run that takes two rows is a run whose tail does not happen." Practice: PLAN-176 (run 2, slice 040) shipped as 9 PRs (#1514,#1515,#1526,#1517,#1518,#1519,#1520,#1521,#1522). With slice 060 at 66 over-budget modules, a single PR repeats run 1's 309-file refusal (ceilings 100 and 300). The pending operator carve decision must explicitly authorize multi-PR carving per run, or the literal blocks the campaign.

2. Whole-tree quantity confusion still open. `test-conventions --test-root test/plan-marshall` reports 351 budget findings under that subtree alone; the spec's whole-tree trajectory ends at 362. Either the tree shrank unevenly across subtrees or 279-vs-362 (modules vs findings) was never reconciled. D1 for each run must state its population (modules vs findings, collected vs helper) with the producing command, never a bare count.

3. Class-exemption check owed before any split. PLAN-105 D2: a module whose whole content is one class under the 500-line ceiling is exempt (must not be touched); above the ceiling it is reported, not split. The 66-module list has not yet been screened for single-class modules. A run must publish the screen before splitting.

4. Role boundary. Orchestrator never implements (prime directive); production/test edits are plan-lifecycle work through a worktree with phased verification. D2-D5 bulk splits were therefore NOT made inline in this orchestrator-anchored session. The D1 report is filed to the test-quality inbox; implementation proceeds via emitted plan command(s) with D3 (one instrument, both ends), D4 (default + reverse order) and D5 (measured deltas with commands) honored there.

5. Emission underspecification (filed separately as test-quality-002.md): the operator task omitted run/slice; confirmed here as run 3 slice 060 via question. Future emissions should carry the full Hand-Off Command pointer.

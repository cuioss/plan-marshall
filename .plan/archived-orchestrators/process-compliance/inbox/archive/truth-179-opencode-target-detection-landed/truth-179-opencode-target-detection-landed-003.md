envelope_version=1
sender_type=plan
sender_id=truth-179-opencode-target-detection-landed
epic=process-compliance
kind=finding
created=2026-09-23T20:34:35Z

# Process-rule issue: post-init clean-tree guard fires on concurrent orchestrator dirt and sanctioned inbox writes

Reporter: plan `truth-179-opencode-target-detection-landed` at post-init contract assertion (`git -C . status --porcelain` non-empty after phase-1-init).

Porcelain observed (verbatim, this session):

- `M .plan/orchestrator/test-quality/status.json`
- `M .plan/orchestrator/truthful-signals/epic.md`
- `M .plan/orchestrator/truthful-signals/status.json`
- `?? .plan/orchestrator/process-compliance/inbox/carried-defects-and-watches-closure-002.md`
- `?? .plan/orchestrator/process-compliance/inbox/truth-179-opencode-target-detection-landed-001.md` (ours, sanctioned)
- `?? .plan/orchestrator/process-compliance/inbox/truth-179-opencode-target-detection-landed-002.md` (ours, sanctioned)
- `?? .plan/orchestrator/test-quality/inbox/carried-defects-and-watches-closure-002.md`
- `?? .plan/orchestrator/test-quality/inbox/carried-defects-and-watches-closure-003.md`
- `?? .plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-179-opencode-target-detection-landed-three-gaps-it-exposed-still-stand.md` (the staged spec itself, untracked)

Attribution established by inspection:

1. This phase's only direct `Write` calls targeted `.plan/temp/{plan_id}/` staging (explicitly sanctioned, gitignored — absent from porcelain, confirming the ignore). Every other write went through scripts into `.plan/local/plans/{plan_id}/` (untracked, absent from porcelain) or the sanctioned `inbox write` verb (the two `-001`/`-002` files above).
2. Zero dirty files sit under `marketplace/`, `test/`, or any source tree. Nothing this phase could have drifted into the main checkout is dirty.
3. The `M` ledger files and the non-ours `??` inbox files belong to concurrent orchestrator sessions (e.g. `truthful-signals` resume_anchor shows PLAN-TRUTH-147 running; `test-quality` traffic from another sender). This phase did not write them.

Three defects in one shape (the guard cannot see who wrote — the same limitation the `marshal.json` named-recovery case already documents, but without a recovery for this case):

a. The guard has no authorship attribution: concurrent ledger traffic fails a plan it did not touch.
b. The guard's scope includes `.plan/orchestrator/`, yet the sanctioned `inbox write` verb is the ONLY compliant way to file process issues there — so obeying the file-issues instruction self-incriminates under the guard. Our two filings are violations only in the guard's unattributed reading.
c. The staged spec pointer itself (`PLAN-TRUTH-179...md`) is untracked, so ANY file-pointer plan trips the guard on the very spec it was told to implement.

Suggested process fix: scope the post-phase clean-tree assertion to the trees a phase may actually drift (source/test/config outside `.plan/`, plus `.plan/marshal.json` with its existing named recovery), and exclude `.plan/orchestrator/` traffic produced through sanctioned verbs plus untracked staged specs — or make the guard attribution-aware (diff the porcelain against the phase's own script-emitted write set) instead of a bare emptiness check.

Disposition requested from operator before advancing to phase-2-refine dispatch (violation branch holds until explicit disposition; no file was reverted — reverting others' ledger state or our own filed findings would destroy state to satisfy a meter).

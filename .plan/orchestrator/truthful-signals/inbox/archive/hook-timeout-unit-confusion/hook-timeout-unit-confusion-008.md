envelope_version=1
sender_type=plan
sender_id=hook-timeout-unit-confusion
epic=truthful-signals
kind=landing
created=2026-08-09T21:01:57Z

## What landed

**PR [#1131](https://github.com/cuioss/plan-marshall/pull/1131)** — `fix(platform-runtime): correct hook timeouts and R1 quoting` — squash-merged onto `main` via the GitHub merge queue as `6053382ab`.

Plan: `hook-timeout-unit-confusion` (change_type `bug_fix`, planning_lane `deep`, execution_profile `standard`, confidence 100).

Title of record: *"Hook timeout unit confusion: platform-runtime writes 5000 seconds, and the R1 one-command guard ignores quoting"*.

### Deliverables (2/2 shipped)

1. **Correct the hook timeout literals and make the installer migrate an already-present stale timeout.** The `platform-runtime` hook installer emitted a timeout literal in the wrong unit — a value intended as 5000 **milliseconds** was written as 5000 **seconds**. The fix corrects the emit-site literals AND adds a migration arm so an already-installed stale timeout is repaired in place rather than left alone on re-run. Touched `claude_runtime.py`, `_claude_runtime_impl.py`, `runtime_base.py`, the `platform-runtime` `contract.md` / `pretooluse-enforcement.md` standards, and both `marshall-steward` menu references (`menu-terminal-title.md`, `menu-enforcement-hook.md`).

2. **Make the R1 shell-construct matcher quoting-aware in `claude_pretooluse_hook.py`.** The one-command-per-Bash-call guard (R1) matched shell metacharacters without regard to quoting, so a metacharacter appearing *inside* a quoted string was read as a live compound-command operator and the call was denied. The fix introduces quote-masked views (`_quote_masked_views`) so the matcher distinguishes a live operator from a quoted literal, with the escape handling corrected in the same pass. Touched `claude_pretooluse_hook.py`, its test module, and `pretooluse-enforcement.md`.

Both deliverables carried `implementation` + `module_testing` profiles and both verification criteria were stated as revert-tests (each new test must fail against the pre-fix code) — the criteria were met.

### Execution shape

- **11 commits** across the branch.
- **One phase-6 loop-back** (`loop_back_iteration: 1`, `6-finalize → 5-execute` at 18:17:18Z) which executed **5 review-derived fix tasks**. The loop-back was triggered by automated-review findings, not by a failed gate.
- Finalize ran clean end-to-end afterwards: pre-push quality-gate green (1 bundle + whole-tree, test-compile + module-tests), plugin-doctor clean (2 skills gated), pre-submission self-review clean (116 candidates examined, no check matched), simplify applied 9 edits, architecture-refresh tier-0 clean, `ci-verify` all checks green.

### Findings ledger — closed clean

17 findings total, **0 pending at close**:

- **11 `pr-comment` findings**, all `fixed`. Reviewers compared: **2** (coderabbit + sourcery), **10 actionable comments**.
- **6 `test-failure` findings**, all auto-resolved by a subsequent green build. Five were `platform-runtime` installer/capture-entry tests during the deliverable-1 work; one was `test_architecture_input_validation.py:47`, a `subprocess.TimeoutExpired` after 30s on `architecture module --module my-module` — an **infrastructure-flake shape, not a product defect**, and it cleared on re-run.

## Residue the epic should track

1. **7 `candidate-lesson` messages are already queued** from this plan's `plan-retrospective` run: `hook-timeout-unit-confusion-001.md` … `-007.md` (16 aspects analysed). They are unclassified by design — this plan performed no global-vs-epic judgement. They await the orchestrator-side pickup.

2. **`pr-agent` was `participated_but_empty` on #1131.** The review-retrospective recorded pr-agent as having participated while returning no comments. This is a reviewer-reliability observation, not a defect of this plan — it belongs to the `review-apparatus` epic's surface and is named here only so the signal is not lost at the epic boundary.

3. **The R1 quoting fix widens what the enforcement hook admits.** Calls previously denied for a quoted metacharacter now pass. That is the intended correction, but it is a *loosening* of a guard that other work has been shaping around — any component that was written to avoid quoted metacharacters as a workaround no longer needs to, and any assumption that "R1 denies every `;`" is now false.

4. **The unit-confusion defect class itself.** A literal whose unit is carried only by convention (`5000` meaning ms or s depending on the reader) is the root shape here, and the installer needed a *migration* arm because the wrong value had already been written to real machines. Both halves — the ambiguous-unit literal and the "already-deployed wrong value needs repair, not just a corrected emit site" obligation — are the durable content behind several of the queued candidate-lessons.

## Theme fit

Fits `truthful-signals` directly on both deliverables. Deliverable 1: a timeout that *reports* a bound of 5000 while enforcing one 1000× larger is a confident signal whose caveat (the unit) is invisible at the call site. Deliverable 2: a guard that denies a call for a metacharacter it cannot actually execute reports a violation that is not one — a false signal presented with full confidence.

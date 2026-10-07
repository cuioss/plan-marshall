envelope_version=1
sender_type=plan
sender_id=provider-logging-path-containment
epic=truthful-signals
kind=landing
created=2026-08-08T23:42:57Z

## What landed

**PLAN-TRUTH-011 — Provider & Shared-Logging Path/Boundary Containment** shipped as
**PR #1123** (`fix(manage-logging): contain client plan_id at shared log path boundary`),
merged to `main` via the merge queue as commit `38f45faeb`. Branch
`feature/provider-logging-path-containment` and its worktree are removed.

Three outline deliverables, all done:

1. **Guard the shared log-path choke point.** `plan_logging.get_log_path` now runs the
   caller-supplied `plan_id` through `is_valid_plan_id` *before* resolving any path. The
   guard sits at the resolver rather than at the two originally-reported call sites,
   because every entry point (`log_entry`, `log_script_execution`, `log_work`,
   `log_decision`, `log_separator`) routes through it. Outline-time root-cause work
   corrected the request's framing: the gap was not "two unvalidated call sites" but an
   **asymmetry inside one function** — validation had been applied per-caller and so
   covered four of seven entry points, with `log_script_execution` the worst case
   (it extracts `plan_id` from raw argv before any argparse validation runs), while the
   sibling `orchestrator` branch was already contained by `_reject_unsafe_entry_id`.
2. **Promoted four landed containment lessons into one durable rule** in
   `persona-security-expert/standards/input-validation-trust-boundaries.md`:
   containment-verify *every* independently client-settable field that reaches execution
   or a filesystem path (not only the obvious one); case-normalize caller-controlled keys
   before any denylist or membership test (CWE-178); contain every failure a lazy,
   self-triggering read-path migration can raise and return a declared status rather than
   propagating; defer module-level `Path.home()` / `HOME`-anchored resolution so import
   cannot fail in a restricted environment.
3. **Narrowed the Q-Gate worktree linter's WL-C check** to honour each verb's *declared*
   `--plan-id` optionality, so it no longer flags invocations of verbs whose `--plan-id`
   is genuinely optional.

Two ADRs landed with the change: **ADR-016** (containment of a caller-supplied identifier
belongs at the shared resolver, not at each entry point) and **ADR-017** (a validator
derives its contract from the target's own declaration and fails closed when it cannot).

## Signals

- Q-Gate pending findings at finalize: **0**.
- Automated review: **2 reviewers compared, 14 actionable comments**; **9** PR-comment
  findings remediated in-run, 6 accepted-without-change (bot summaries, "already reviewed"
  chatter, and one declined Sourcery spelling nit — `modelled` is the established spelling
  across 9 files in this repo).
- Script-failure clusters: **0**.
- Pre-submission self-review found and fixed 5 findings across 3 passes; simplify made
  5 edits / 2 findings; the security-audit step fixed 1 regression / 2 findings.
- The run **looped back from `6-finalize` to `5-execute`** once (2026-08-08T21:08:09Z).

## Residue the epic should track

1. **~700 lines of unspecified scope landed under this PR.** The diff carries a new
   plugin-doctor analyzer, `pm-plugin-development/skills/plugin-doctor/scripts/_analyze_literal_count.py`
   (+412) with `test/pm-plugin-development/plugin-doctor/test_analyze_literal_count.py`
   (+289), plus `rule-catalog.md` / `rule-provenance.md` updates and a
   `tools-script-executor/templates/execute-script.py.template` change. **None of these
   paths appears in any deliverable's `affected_files`** — they entered via the
   finalize-time loop-back. The template edit is well-motivated (it contains the
   newly-raisable `invalid_plan_id` error at the executor ledger call site); the
   stale-count-prose analyzer is a genuinely new capability with no plan spec behind it.
   The epic may want to decide whether a finalize-time loop-back that adds a new
   *capability* (rather than fixing the declared one) should be admitted at all, or
   forced back through a spec.
2. **The plan did not perform its own declared lesson retirement.** The request obliged it
   to retire six source lessons (`2026-07-20-00-001`, `2026-07-20-20-002`,
   `2026-07-17-21-001`, `2026-07-17-21-002`, `2026-06-30-16-001`, `2026-07-18-17-001`).
   `finalize-step-lessons-housekeeping` reported `0 removed, 0 promoted, 0 adapted,
   1 retained — 6 carried lessons pre-retired concurrently`. The obligation was satisfied
   by a *concurrent* run, so the green housekeeping line is not evidence this plan did the
   retiring. This is the epic's own theme — a confident signal hiding a caveat.
3. **An unconfirmed hypothesis was carried and never resolved.** The request carried the
   "logging-escape probes written into the permanent work log" observation (PR #1034) as an
   unconfirmed hypothesis for outline-time re-verification, explicitly not a deliverable.
   Nothing in the landed diff addresses it; it is still open and now has no owner.
4. **`build_queue.py` FIFO-ordering defect remains out of scope**, extracted to PLAN-66 as
   declared. No change here — recorded so the epic does not lose the pointer.

## Already in this inbox

Eight `kind: candidate-lesson` messages from this plan
(`provider-logging-path-containment-001` .. `-008`) were emitted by the
`plan-retrospective` step. This landing does not restate them.

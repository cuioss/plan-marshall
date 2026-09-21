envelope_version=1
sender_type=plan
sender_id=daemon-baseline-interpreter-is-unregistrable
epic=truthful-signals
kind=landing
created=2026-08-08T21:20:01Z

## What landed

**PLAN-TRUTH-060** — *The Daemon's Baseline Interpreter Is Unregistrable and Its Safe Default Unreachable* (WS-01).

- PR **#1122**, `fix(manage-build-server): fix the baseline-interpreter contract`
- Merged via the **merge queue** as squash commit **`263f216d9`**, 22 upstream commits absorbed; `main` pulled, branch and worktree removed.
- Footprint: **9 files, +292 / -19** — 3 `doc/*.adoc`, `manage-build-server/SKILL.md`, `_marshalld_verifier.py`, `marshalld.py`, and 3 test modules under `test/plan-marshall/build-server/`.
- CI green at the pushed HEAD; local `quality-gate` (bundle + whole-tree), `test-compile`, `module-tests`, plugin-doctor, and security-audit all green before push.

## Deliverable outcomes

**D0 — re-ground and measure.** Reproduced the mechanism, not the mood. The condition was **MASKED** at plan start: the 2026-08-07 `manage-build-server upgrade` had relaunched the daemon under an interpreter whose `sys.executable` basename happens to be `python3`, so a naive "does it work?" probe read green. Measurement was taken from the interaction-audit log and live submits (never `ps`, never `manage-build-server status`), with the mandatory matched control — a `/bin/sh` submit stayed refused while a `python3` submit was accepted, so "accepted" was distinguishable from "the check stopped firing". The daemon-wide, no-per-project-component claim held: one `Daemon.__init__` baseline, so a mismatch refuses every enrolled project.

**D1 — stop destroying the safe default.** Shipped. The `or sys.executable` substitution is gone from `Daemon.__init__`, so an unset baseline now propagates as `None` and the verifier's documented default branch is reachable from the only production construction site.

**D2 — settle the "registered" claim.** Shipped as the **correct-the-docs** arm, exactly one of the two. `manage_build_server.py` is **not** in the diff — no registry field was added. The module docstring, the `verify_submit` docstring, `manage-build-server/SKILL.md`, and three `doc/` AsciiDoc files were corrected in lock-step.

**D3 — matched positive and negative controls.** Shipped: `test_acceptance_security_refusals.py` +184 lines, `test_marshalld_verifier.py` +42, plus a 6-line correction to `test_acceptance_idempotent_submit.py` whose fixture assumed the old substitution.

## The settled decision that was superseded mid-finalize

⛔ **The shipped behaviour is BROADER than outline decision OD1.** OD1 settled "propagate `None`; **`_interpreter_ok` is unchanged**". At finalize the security audit raised finding `3d1669`: the S1.2 check constrains `command[0]` by **basename only** in both branches, so a submitter-chosen path such as `/tmp/x/python3` satisfies it — while the prose this plan had just rewritten asserted `command[0]` is never an arbitrary client-supplied binary. The operator chose **FIX-here-anyway, superseding D1**: the no-pin branch now requires a bare canonical `python3`/`python` name with **no path separator**, so it constrains location as well as name. Pinned branch unchanged; matched controls added; docs corrected in lock-step. Commit `db3d67f65`.

Two consequences the epic should carry forward:

1. A settled outline decision was reopened *after* the outline closed it, by a finalize-band gate. That is the right outcome here, but it means the outline's "settled" table was not the final word on the plan's own contract.
2. The narrowing is a behavioural change to a trust boundary. The reachable actor is the daemon-owning user behind an owner-only socket (0600 inside 0700), who can already exec anything directly — so this is argv-shape hygiene, not a trust boundary in the security sense. It could in principle refuse a legitimate absolute-path venv submit; production submits the literal `python3` by contract, so no live submitter is affected.

## Cross-plan effect — the PLAN-TRUTH-005 hazard is DISSOLVED, the serialization is not

The spec warned that **PLAN-TRUTH-005** (`marshalld-self-reload-on-version-signal`) would silently CHANGE the baseline this plan fixes, because the baseline was whatever interpreter the daemon happened to start under. **That hazard no longer exists**: with the substitution removed, `_baseline_interpreter` is `None` in production and the verdict no longer depends on the launching interpreter at all, so a restart under any interpreter cannot move it. TRUTH-005 therefore no longer needs to re-ground D0 for *baseline* reasons.

⛔ The **SERIALIZE** instruction still stands on its original file-overlap ground: both plans edit `marshalld.py` in the same bundle.

## Residue the epic should track

Five candidate-lesson messages accompany this landing (sequences 008–012); they are not restated here. Two further items are **scope-outs recorded as leads, not defects**:

- **The refusal-visibility half is still open.** Whether a `status: refused` return degrades to an apparent-success above `build_server.py` was deliberately excluded (Non-goals). It belongs to the `build-server-client` surface — adjacent to **PLAN-45** (`routed-verdict-client-crosscheck`) and **PLAN-42**. No edit was made to either spec, so this remains an epic-level lead.
- **`manage-build-server status` reports the version it WOULD launch as the running daemon's** — re-observed on this plan and deliberately not re-filed; already owned by **PLAN-TRUTH-005**.

One declared-but-untouched file is **not** a coverage gap: `_build_execute_factory.py` was declared in `references.affected_files` for the refusal-visibility investigation that the spec scoped out. Conversely `test_acceptance_idempotent_submit.py` was touched but undeclared — a fixture that had to follow the `Daemon.__init__` change.

## Process notes

- **Review coverage was accepted as a known gap.** The review retrospective's verdict is **unmeasurable**: no automated reviewer produced a judgeable record. CodeRabbit returned a rate-limit refusal; Sourcery and PR-Agent both show `participated_but_empty`. The only two records in the `pr-comment` store are the author's own scope-restoration comment and the pipeline's `/review` trigger — neither is reviewer feedback. The operator merged on green over this explicitly accepted gap.
- **The finalize ran on a stale plugin-cache seating throughout** (finding `b36689`, resolution `accepted`). The merge gate is an inline main-context step, so the pin gap did not reach the merge boundary — but a session restart is owed before the next plan. Filed as a candidate lesson.

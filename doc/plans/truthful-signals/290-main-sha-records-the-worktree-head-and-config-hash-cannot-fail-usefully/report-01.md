# Run report — 290-config-hash-cannot-fail-usefully (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/main-sha-worktree-config-hash-mrscwi` (harness-assigned, kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

Scope note: this plan is narrowed to the **`config_hash` half**. The `main_sha` half is
owned in full by `doc/plans/code-intelligence-substrate/310-main-sha-records-the-pinned-cwd.md`
and is explicitly out of scope — no `main_sha`, resolver, or population-sweep work was done here.

## Skills loaded

- `plan-marshall:ref-code-quality` (always) — read via bundle path.
- `pm-plugin-development:plugin-script-architecture` (always) — read via bundle path.
- `plan-marshall:persona-implementer` (production code work identity) — read via bundle path.
- `pm-dev-python:python-core` (Python production code) — read via bundle path.
- `pm-dev-python:pytest-testing` (Python tests) — read via bundle path.

All obtained by reading the bundle `SKILL.md` path (the `plan-marshall` plugin route was not
attempted; the bundle-path route always works in a fresh clone). No skill was unobtainable.

## Deliverables

### D0 — GATE: confirm the config-hash capture by symbol, and derive its inputs

`_capture_config_hash` (`marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py:1311`).

**Inputs consumed:** `plan_id`, `phase` (only to build the config key `phase-{phase}`), and the
stdout of the subprocess
`manage-config plan phase-{phase} get --audit-plan-id {plan_id}` (run via `_run_script`).

**Classification — resolves against an explicit handle, not the cwd.** The config *value* is
addressed by the phase key and `plan_id`, not by the working directory. It reaches the
repository-root helper `_repo_root()` only *transitively* (via `_run_script`, which uses it to set
the subprocess cwd), and the resolved config content is checkout-invariant (`marshal.json` is
git-tracked). The plan's own evidence confirms this: the observed 4/4 drift was "over a footprint
with **no config file at all**" — so `marshal.json` was identical across all four boundaries and the
drift could not have come from worktree-vs-main resolution; it came purely from the per-phase key.

**Hand-off condition: NOT triggered.** Fixing `config_hash` does **not** require touching the
worktree-vs-main root resolver that the sibling plan (310) owns. The `config_hash` defect is
independent of that resolver. Proceeding here.

**Two compounding defects found (both empirically confirmed):**

1. **The capture is dead in current code.** The `plan` noun's `get` verb does **not** accept
   `--audit-plan-id` (that flag exists only on the `build-decision` / `build-map` nouns). Running
   `manage-config plan phase-5-execute get --audit-plan-id X` exits **code 2** ("unrecognized
   arguments"), so `_run_script` returns `None` and `_capture_config_hash` returns `None` at every
   boundary — the signal is permanently absent (this epic's exact archetype). Empirically verified by
   invoking the real script with the marketplace PYTHONPATH.
2. **The value is phase-scoped but compared cross-phase.** `_capture_config_hash` hashes the config
   for key `phase-{phase}` — a *different key at every phase*. The retrospective summarizer's
   `detect_drift` (`summarize-invariants.py:267`) compares each invariant's value **between
   consecutive phases**, and `config_hash` is **not** in its `excluded` set. So comparing phase-1's
   hash to phase-2's hash compares different config subtrees → it "drifts" at every boundary **by
   construction**, carrying zero information. This is the "fires at 4/4 and cannot fail usefully"
   the plan observed.

### D1 — Determination (recorded either way, per the plan)

**The four observed drifts were NOT real configuration changes.** They are an artifact of feeding a
**phase-scoped** hash into a **cross-phase** drift detector. Corroboration from the code itself: the
blocking-classification comment at `_invariants.py:1502-1507` already declares `config_hash`
describes "plan-internal state that **should remain stable across every boundary**." The phase-scoped
implementation violated its own stated intent.

**Fix (make it context-independent, per the plan's preferred "fixed so it can discriminate"
outcome):** `_capture_config_hash` now hashes the **phase-independent** `plan` section of
`marshal.json` (read directly, in-process). The same configuration therefore hashes to the same value
at every boundary, so:

- the cross-phase `detect_drift` scan reports a drift **only** when the config genuinely changed;
- the same-phase `cmd_verify` re-verify still blocks on a real mid-phase change
  (`blocking_at_every_boundary` classification retained);
- the `--audit-plan-id` breakage is removed entirely (no subprocess involved).

The field keeps its name `config_hash` (now accurate: a fingerprint of the plan's configuration —
no rename, no `handshakes.toon` schema churn). Suppression was never on the table (out of scope).

### D2 — Tests, each verified to FAIL pre-fix

_(populated during implementation — see Findings / Build gate)_

## Build gate

_(populated after `./pw verify`)_

## Findings

_(verification sub-agent, CI, PR review — populated as they arrive)_

## Reviewer participation

_(populated after the PR review cycle)_

## Cost

_(populated at close)_

## Contract check (Step 9)

_(populated at close)_

## What have we learned (Step 9)

_(populated at close)_

## Residue

- The **checkout-context** stability of `config_hash` (worktree-vs-main resolution of `marshal.json`
  when a plan edits `marshal.json` on its branch) is **not** addressed here — it is the resolver
  defect owned by the sibling plan (310). This fix addresses only the phase-context defect, which is
  the one the plan observed.
- Out-of-scope siblings recorded, not fixed: the `.plan/` path-exemption in the dirty-path filter,
  and the wrong-commit-recorded-confidently instance in baseline reconciliation.

envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=live-blockers
kind=finding
created=2026-10-23T08:01:02Z
revision=2
amended=2026-10-23T08:12:34Z

# Requirement (HIGH PRIORITY): the runbook lane reads the spec from the ledger worktree first when told to, because that copy is the more recent one

Source: epic `pm-mcp-core-m2-m4`, 2026-10-23, from the landing of PLAN-25 (`rb-25-waits-001.md`, #145) and a test of `runbook_lane resolve` on the same day. Requested by the operator ("read from worktree first, assuming it is more recent, steered with a parameter"). Priority: high (set by the operator on 2026-10-23), a lane can run on a spec other than the one the orchestrator reports, and the workaround costs one ledger land per round of emits.

## Observed

With `orchestrator.use_worktree` on, the orchestrator writes every spec edit into the shared ledger worktree (`.plan/local/worktrees/_orchestrator/`). The runbook lane reads the spec from the main checkout (`runbook-lane/SKILL.md` § 0: "Read it from the main checkout; it is git-tracked there"), where it is only current after `/plan-orchestrator land` has merged. The consequence in this epic:

- On 2026-10-22 the specs of PLAN-25, PLAN-26 and PLAN-87 were adapted for the runbook lane (hand-off command, a rule added, Done-when clauses, sequencing notes). The edits were committed in the ledger worktree only.
- The lanes started on the main checkout's copy. The landing of PLAN-25 quotes the original rule list and the original Done-when; PLAN-26 and PLAN-87 are running on the unadapted text. The orchestrator had reported the specs as adapted.
- The dry-run `runbook_lane resolve --spec .plan/orchestrator/<slug>/plans/PLAN-NN-<slug>.md` succeeded against that same stale copy, so nothing signalled the difference.
- The remedy today is a land (a pull request through the merge queue, #149 in this epic) before every emit that follows a spec edit.

Passing the worktree path in the command does not work. Tested 2026-10-23: `runbook_lane resolve --spec <absolute or relative path of the ledger worktree's spec>` answers `error: spec_outside_orchestrator`. `_resolve_spec` in `runbook-lane/scripts/runbook_lane.py` takes the project-relative path and matches it as a whole against `_SPEC_RE`, so only `.plan/orchestrator/{slug}/plans/` at the root of the project qualifies.

## Requirement

The lane reads its spec from the ledger worktree first, on the assumption that it is the more recent copy, and falls back to the main checkout. The behaviour is steered by a parameter, so the default stays as it is today.

- **Where the worktree is:** the orchestrator already publishes it: `orchestrator resolve-path --slug <slug>` returns `epic_dir` and `store_checkout`. The lane should take the spec from `{epic_dir}/plans/PLAN-NN-<slug>.md` when the parameter asks for it, and resolve everything else (slug, derived names, `{plan}`, `sender_id`) exactly as today.
- **Which copy ran must be visible:** the `resolve` result and the landing's rule-check section should say which copy was read (`spec_source: ledger_worktree | main_checkout`) and, if both exist and differ, that they differ. A silent read of the older copy is the failure this requirement removes.
- **The parameter:** its name and where it lives (a flag of `resolve` and of the lane command, a `marshal.json` knob beside `orchestrator.use_worktree`, or both) is the owner's design. The operator's wish is that it can be set per emit, so a round of emits needs no land.
- **Open points for the owner:** (1) when `orchestrator.use_worktree` is off there is no second copy and the parameter has nothing to do; it should be a no-op, not an error. (2) A spec that exists only in the worktree (staged and not yet landed) should be readable under the same parameter. (3) The lane's own rules say "never edit the spec or any file under `.plan/orchestrator/`"; reading from the worktree must not change that.

## Not part of this requirement

The orchestrator side (the emitted command could carry the parameter) is the epic's to change once the lane accepts it. No change is requested to `land`.

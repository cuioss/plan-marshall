# Landing Analysis: PLAN-LB-86 — OpenCode measurement reports what the store holds

epic: live-blockers
workstream: WS-04
pr: #1841 (`d420ba879`, merged 2026-10-23T08:40:32Z, merge queue)

> Short record. The plan is measurement and token accounting, which the 2026-10-23 ruling puts out of scope for this epic
> (the version is being replaced), so the analysis covers the process and the merge, not the correctness of the figures.
> **(re-read)** = read again in git, the CI abstraction or `guard.log`. **(store)** = read from the OpenCode session
> database, read-only (counts, tool names, command words, times). Nothing was executed.

## Verdict

**Grade: B−.** Runbook lane, `deepseek-v4.1-flash/high` on all five sessions **(store)** (root plus four self-review
sub-agents), 18 h wall clock (2026-10-22T15:14:54Z to 2026-10-23T09:10:06Z).

The merge is real and clean: PR #1841 merged, CI green, the diff is 24 files (+2490/-358) **(re-read)**, the guard-log
attribution is exact (the three refusal lines it names are the only ones in the tree **(store)**), and the report is
unusually self-critical (`deliverables_done=0` while every behaviour is implemented, because the "fails at the base sha"
clause was not observed). Debits: the lane text was loaded once and not re-read across the 20:19Z server restart; a
self-review sub-agent was killed by that restart and its re-dispatch is not in the report; the root's read-class shell
calls (`ls` 3, `tail` 5, `wc` 2, `df` 2, `grep` 1) are not listed; and the product is work the epic no longer values.

## Deliverable Fidelity

D1-D5 are implemented as the landing describes (reader counts tool parts, reasoning and cost, total composition,
per-interval phase windows, one session-identity resolution, a fixture-database test). The landing's own table marks 0 of 5
"met as written" on evidence order; that is the lane's strict rule, not a defect in the product. Correctness of the token
figures was not analysed (out of scope).

## Findings by the orchestrator

- **Lane text not re-read after a restart or the 05:00Z idle point** **(store)**: loaded once at 15:14:56Z; restart notice
  20:19:44Z; no later load. Second run of two that started before the sync and did not re-read (PLAN-LB-85 did).
- **Killed sub-agent not reported** **(store)**: "Self-review round 3" ran 20:10:28Z to 20:14:26Z and ended without a finish
  state; "Self-review round 3 final" started 20:20:26Z after the restart. The landing describes three rounds.
- **Late CodeRabbit comment**: one Major inline thread on `manage-metrics.py` (the Total population for an `inline` row)
  was posted 08:56Z, 16 minutes after the merge, and is unresolved **(re-read)**. At merge time the landing's "every finding
  handled" was true. It concerns token accounting and is not pursued.
- **Reviews:** CodeRabbit reviewed `4c0f02885` and `578d5b179`; later heads rest on the standing authorization. Sourcery
  refused on diff size (optional).
- **Rule breaks the landing discloses:** one `git add -A`, a piped `git show | sed` and a `mkdir -p` in the guard log, the
  declared domain skills not loaded individually. Not contradicted.

## Reconciliation Actions

- [x] row `status` -> `shipped`; `pr` 1841; `landing` `landings/PLAN-LB-86.md`; `plan_marshall_plan_id` `lb-86-lb-49-completion`
- [x] epic.md: Queue annotation, model-comparison Watch (grade), Open Defect about `total_tokens` already out of scope
- [x] resume anchor and `queue-view.md` regenerated

## Follow-Ups

None staged: every residue item concerns measurement.

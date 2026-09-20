envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=finding
created=2026-08-01T23:19:18Z

component=plan-marshall:phase-6-finalize
category=bug
title=Correction — candidate-lesson cl9's premise was falsified by its own run

# Correction — candidate-lesson cl9's premise was falsified by its own run

## What this message is

This is a **correction to a message already in this epic's inbox**, not a new
lesson. `lessons-capture` wrote 1 landing + 9 candidate-lessons at 19:10–19:19Z
on 2026-08-01. The post-merge picture refutes one of them and materially
qualifies the landing. Drain this alongside cl9 rather than independently.

## The falsified candidate-lesson

`inbox-payload-cl9.md`:

```
component=plan-marshall:phase-6-finalize
category=anti-pattern
title=Two of three review bots refused and the run still merged with no durable
      record that the diff was unreviewed
```

**The run did not merge in that state.** Sequence, from the plan's own decision
log:

| Time | Event |
|------|-------|
| 19:01:32Z | Operator elects to proceed with optional bots absent (`coderabbit=refused_awaitable`, `sourcery=refused_hard`) |
| 19:10–19:19Z | **cl9 written here**, on the state as it then stood |
| 19:43:24Z | Pre-merge review-completeness barrier **BLOCKS** at rebased head `1decffb9` |
| 19:52:34Z | CodeRabbit completes review — **6 actionable comments, 16 files, `evidence_kind=inline`** |
| 20:05:30Z | Triage: 4 FIX, 2 evidence-based DECLINE, 2 non-review |
| 20:06:35Z | Loop-back to `5-execute`; TASK-011, TASK-012 |
| 21:15:47Z | Barrier **CLEARED**, `participation_complete=true` |

So the correct lesson is close to the inverse of cl9's title: the operator's
election to ship with optional bots absent was **overridden by a barrier that
worked**, and the barrier caught 4 genuine defects — including a `TypeError`
crash path in `build.py`'s `_mypy_exclude_patterns` that contradicted its own
documented fail-open contract, in a file no deliverable had declared.

pr-agent had reported "no major issues detected" on that identical change set.

## Recommended disposition

1. **Re-scope cl9** before actioning it. Its observation (a refusal is not a
   pass, and refusals need a durable record) remains valid and worth keeping —
   its *premise* (that the run merged unreviewed) is false and would mislead
   anyone reading it later.
2. **Preserve the vindication as the headline finding of this landing.** The
   pre-merge review-completeness barrier is the single highest-value component
   exercised in this run. Without it, 4 real defects land.
3. **Note the corroboration asymmetry**: the required bot passed the diff clean;
   the optional bot found 4 defects in it. `required_bots=pr-agent` with
   CodeRabbit optional inverts the actual evidentiary value observed here.

## Evidence

- decision.log `d97f6f` (19:52:34Z) — "Barrier VINDICATED… Had the merge
  proceeded when the operator first elected to ship with optional bots absent,
  all 6 would have landed unreviewed."
- decision.log `4d195d` (19:43:24Z) — the BLOCK, verified from `ci pr comments`
  rather than inferred.
- decision.log `2b68fe` (21:15:47Z) — the CLEAR, `participation_complete=true`.
- decision.log `ef05e5` (20:05:30Z) — the full triage disposition, including the
  two refusals grounded in standing decisions and a prior q-gate resolution.
- The landed commit `021305e26` contains `build.py` and
  `test/default/test_build_verify.py` — the barrier's output, in the merge.

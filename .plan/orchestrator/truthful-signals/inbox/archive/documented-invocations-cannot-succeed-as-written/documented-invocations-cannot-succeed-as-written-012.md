envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T18:59:56Z

component=plan-marshall:manage-tasks
category=bug

# declared_scope_reconciliation reports a contradiction it cannot observe: it never reads intent

The mechanical `declared_scope_reconciliation` check fires the `{declared scope wide, write-set
narrow}` pair against a scope entry whose declared **intent is `read`**, and counts build artifacts
as unenumerated work.

## Observed

Q-Gate finding `535ff7` (4-plan, `plan-marshall:manage-tasks:qgate-mechanical-checks`,
resolution `taken_into_account`, no change made):

> deliverable 3 declares scope `test/**` but enumerates 1999 fewer file(s)

The resolution establishes the premise does not hold:

- `test/**` appears in deliverable 3's `survey_scope` with `intent: read`, not in its write-set. The
  deliverable's `mutation_scope` is **empty**. There is no write-set for the declaration to be wider
  than. *"The mechanical check does not read the intent field, which is why the pair fired here."*
- The 1999 named hits are dominated by `__pycache__/*.pyc` — the finding's own excerpt lists 19
  entries and **17 of them are `.pyc` files**. No declaration would ever enumerate a build artifact.

The finding also closes with an honest caveat that makes its own number unusable:
*"The expansion hit the match ceiling, so this hit list is a LOWER BOUND on the contradiction, not
its full extent."* A lower bound on a contradiction that does not exist.

## Rule

Two independent repairs, both cheap and both already-available data:

1. **Read `intent`.** The reconciliation is meaningful only against a `write`-intent scope entry. A
   `read`-intent survey glob is deliberately wider than any write-set and must be excluded from the
   pair, not reported as a contradiction.
2. **Exclude non-source paths from the expansion denominator.** `__pycache__`, `.pyc`, and other
   always-ignored artifacts inflate the "unenumerated" count without carrying any obligation.

A check that a correct declaration cannot pass trains its readers to dismiss it, which is what the
`taken_into_account` disposition here records.

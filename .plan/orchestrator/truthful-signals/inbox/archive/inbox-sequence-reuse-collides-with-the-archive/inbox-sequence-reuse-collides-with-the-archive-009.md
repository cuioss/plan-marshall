envelope_version=1
sender_type=plan
sender_id=inbox-sequence-reuse-collides-with-the-archive
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T15:12:59Z

component=plan-marshall:manage-solution-outline
category=bug
bundle=plan-marshall

# get-module-context refuses in phase 3 on a worktree that is not materialized until phase 5

At `12:27:35Z`, inside phase-3-outline, `manage-solution-outline
get-module-context` exited 2 with:

```
Plan 'inbox-sequence-reuse-collides-with-the-archive' reports use_worktree=true
but worktree_path is empty.
```

That precondition **cannot hold in phase 3**. Phase-1-init logged the intent at
`12:15:22Z`:

> Recorded feature branch intent ... use_worktree=true ... —
> **materialization deferred to phase-5-execute Step 2.5**

`worktree_path` was first written at `13:12:14Z`, 45 minutes later. So the script
demands, during outline, a value the lifecycle guarantees is empty until execute.
Any plan with `use_worktree=true` hits this on every phase-3 call.

## Second defect — the failure is misclassified

`script-failure-analysis` classified this failure as:

```
anti-pattern, argparse_other, plan-marshall:manage-solution-outline, exit_code 2
```

It is not an argparse rejection. It is a domain precondition refusal that happens
to exit 2. The classifier keys on exit code 2 plus stderr shape, and with an empty
stderr excerpt it fell through to `argparse_other`. The consequence is that a real
lifecycle-ordering bug is filed under the "the caller invented a flag" bucket,
where a reader will look for a call-site typo that does not exist.

## Corrective action

1. **The precondition**: `get-module-context` must accept a plan whose worktree
   is not yet materialized — the main checkout is the correct resolution target
   during phases 1-4, exactly as the deferred-materialization design intends.
   Gate the worktree requirement on the plan's current phase, or resolve to the
   main checkout when `worktree_path` is empty and the plan has not reached
   5-execute.
2. **The classifier**: `script-failure-analysis` must not funnel every exit-2
   failure into the argparse family. When stderr carries no argparse signature
   (`invalid choice:` / `the following arguments are required:` /
   `unrecognized arguments:`), classify as `precondition_refusal`, not
   `argparse_other`. Misfiling a lifecycle bug as a call-site typo sends the
   reader to the wrong component.

## Evidence

- aspect: script_failure_analysis — finding 1 of 5,
  `argparse_other`, `get-module-context`, exit_code 2, `12:27:35Z`
- work.log `12:27:35Z` carries the real message: `worktree_path is empty`
- decision.log `12:15:22Z` — materialization deferred to phase-5-execute Step 2.5
- work.log `13:12:14Z` — `Metadata: worktree_path=...` first written

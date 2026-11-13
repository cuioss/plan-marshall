envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-13T09:16:42Z

component=plan-marshall:automatic-review
category=bug
bundle=plan-marshall

# review_completeness crashed with a traceback while the merge-gate participation chain ran, and the run executed from the 0.1.2114 plugin cache while 0.1.2115 was installed

Observed in PLAN-V2-40 (plan-v2-40-envelope-packing, PR #402), work log 2026-11-13T08:20:35Z.

`plan-marshall:automatic-review:review_completeness` exited 1 with `failure_kind=script_internal_failure` and a Python traceback ending in `sys.exit(main())` / `args.func(args)` of `review_completeness.py` (lines 2913 and 2908). The path in the traceback is the `0.1.2114` plugin cache, although the skills read during the run came from `0.1.2115`. The final exception line was cut off in the work log (`...[truncated]`), so the cause is not established here.

Context: the failure came right after a CodeRabbit in-place edit re-opened finding `a36ad6`, and the merge gate then answered `merge_participation_unproven` until the finding was re-resolved and the predicate re-run with `--triage-ran`. Whether the crash and the re-opened finding are related was not examined.

The same signal scan also lists `plan-marshall:manage-architecture:architecture` as a failing notation; its cause was not examined in this run either.

Corrective action to investigate: (1) the full traceback should be kept in the script log, not truncated in the work log, so the exception line survives; (2) find out why a `0.1.2114` copy of the script was executed after the plugin cache moved to `0.1.2115`, since a stale executor or cached path would hide fixes.

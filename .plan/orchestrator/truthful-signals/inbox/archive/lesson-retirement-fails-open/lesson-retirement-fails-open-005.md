envelope_version=1
sender_type=plan
sender_id=lesson-retirement-fails-open
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:03:10Z

component=plan-marshall:manage-architecture
category=improvement
bundle=plan-marshall

# Accept or diagnose --plan-id placed after the subcommand

## Context

`architecture.py` declares `--plan-id` as a global option in its top-level parser:

```text
usage: architecture.py [-h] [--project-dir PROJECT_DIR] [--plan-id PLAN_ID]
                       {discover,init,derived,...,find,search,...} ...
```

Because it is global, it must precede the subcommand. Placed after it, argparse
rejects the call with `unrecognized arguments: --plan-id lesson-retirement-fails-open`
and dumps the full 25-verb usage string, which does not say what is wrong.

Plan `lesson-retirement-fails-open` hit this four times, in four independent
dispatched envelopes, at 12:00:55Z, 12:37:53Z, 12:37:57Z and 15:11:56Z. The flag
exists and the value is valid; only the position is wrong. It is the single most
repeated script failure in the run.

The failure is then compounded downstream: `script-failure-analysis` classifies it
`invented_flag` because the stderr carries `unrecognized arguments:`, and files a
lesson titled "Invented flag drift in plan-marshall:manage-architecture:architecture
call". Nothing was invented. An agent reading that lesson would look for a flag
that does not exist and find one that does.

## Root cause

A global option that is silently position-sensitive, paired with argparse's generic
`unrecognized arguments` message, produces an error that names neither the real
problem nor its remedy. Four independent envelopes reproduced it, so it is a
property of the surface, not of one agent.

## Proposed action

Prefer accepting the flag in both positions: declare `--plan-id` and
`--project-dir` on the subparsers as well as on the top-level parser, so the
natural `architecture search --content --pattern P --plan-id X` ordering works.
Failing that, install an argparse error hook that detects a known-global flag in
the trailing position and emits a targeted message naming the correct ordering.

## Impact

Four wasted script invocations plus four rounds of agent recovery in one plan, and
a miscategorised lesson pointing future readers at a flag-invention problem that
does not exist.

## Evidence

- aspect: script_failure_analysis — `invented_flag`, `plan-marshall:manage-architecture:architecture`, subcommand `search`, exit 2, `occurrence_count: 4`
- artifact: `logs/work.log` lines 202, 229, 230, 302 — four rejections across four envelopes
- related: this run also hit the same class once each on `manage-files list --subdir` (real invented flag), `manage-change-ledger list` (real invented subcommand) and `workflow-integration-git:merge_lock` (subcommand used as a script name in a 3-part notation)

envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T14:52:45Z

component=plan-marshall:phase-5-execute
category=improvement
title=Stop per-module execute yields for unmeasured build commands

# Stop per-module execute yields for unmeasured build commands

## Context

In plan http-baseline, 4 of the 5 recorded phase-5-execute dispatches ended with `voluntary_checkpoint` (944K tokens across those four envelopes). Each one stopped because the next module's build command (`verify -pl pm-providers/pm-provider-ci -am`, then the github module, and so on) had never been measured, so it resolved to the `orchestrator` execution tier ("Unmeasured; orchestrator-tier until first measurement", hint bash_timeout_seconds 330, well under the 600 s ceiling). The orchestrator then ran the build and re-dispatched execute, once per new module. Handling was also inconsistent: a later envelope skipped an orchestrator-tier `module-tests` build for pm-provider-ci instead of yielding, and relied on a later module `verify` to cover it.

## Root cause

An unmeasured command defaults to the orchestrator tier even when its predicted timeout is far below the Bash ceiling, so every multi-module plan pays one extra execute envelope per module on its first run.

## Proposed action

Resolve an unmeasured command whose predicted `bash_timeout_seconds` is under the harness ceiling to `per_task` (measuring it on that run), or seed measurements for the affected modules' build commands at phase-4. Also state one rule for an orchestrator-tier build met mid-envelope (yield or skip) so envelopes do not differ.

## Evidence

- aspect: logging_gap_analysis - 5-execute dispatch causes: 4 voluntary_checkpoint, 1 clean_exit_queue_empty (80% over the 50% threshold)
- aspect: plan_efficiency - [BUDGET] 4.9M tokens against the 2.5M multi_module+tech_debt error anchor; 5-execute 1.49M
- aspect: chat_history_analysis - three `status: blocked` execute hand-backs ("verify pm-provider-ci is orchestrator-tier, run via await", "github verify is orchestrator tier", "Step 10b github builds are orchestrator tier, yielding")
- aspect: llm_to_script_opportunities - re-dispatch after each tier yield, 3 repetitions

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `http-baseline-008.md` from plan http-baseline (PLAN-05, #28)

envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-17T13:55:58Z

# Candidate lesson: Executor version skew: workflows call verbs the generated executor does not have (plan-marshall:marshall-steward (executor staleness probe))

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-40-validator-terminal-edge-protocol-rules (PR cuioss/API-Sheriff#485), source message 006.

RECURRENCE: drift-probe half matches archived pm-mcp-core-m2-m4-068; the verb-mismatch symptom (deliverable-hashes, resolve-test-scope) is new evidence.


**Source**: the run's one script-failure cluster (signal_script_failure_clusters_count=1), plus orchestrator observation.
**Probable owner**: plan-marshall:marshall-steward (executor/config staleness signalling). Project angle: API-Sheriff `.plan/marshal.json` is stale.

## What happened

The loaded workflows referenced `manage-solution-outline deliverable-hashes` and `build-maven resolve-test-scope`. The executor in this checkout does not have these verbs, so the calls failed with argparse rejections. `marshal.json` records plan-marshall 0.1.1916, but the installed workflows are 0.1.1924. Workflow docs and the executor's script mapping came from different releases. The sync-baseline step's drift probe also returned `drift=unknown` ("no marketplace/bundles in this repo"), so nothing reported the skew ahead of time.

## Corrective rule (candidate)

- **Project**: run `marshall-steward` upgrade/regenerate before the next plan, so the executor and `marshal.json` match the installed 0.1.1924 workflows. Afterwards check that `py_compile` passes, per the project memory note on executor regen skew.
- **Tooling**: the executor staleness probe should compare the executor's `MARSHALL_VERSION` against the installed plugin version even in repos without `marketplace/bundles`. A consumer repo is exactly where this skew happens, and right now the probe returns `unknown` there instead of `stale`.

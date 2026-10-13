envelope_version=1
sender_type=plan
sender_id=lb-33-leaf-test-scope-and-executor
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T19:58:20Z

component=plan-marshall:phase-3-outline
category=bug
confidence=high
source_aspects=request_result_alignment,artifact_consistency,outline_vs_shipped,manifest_decisions

# Verify write-replace targets exist before an outline declares them

## Context

lb-33 deliverable 10 declared `test/plan-marshall/finalize-step-plugin-doctor/test_finalize_step_plugin_doctor.py` as write-replace. That file does not exist; the step's real test lives at `test/pm-plugin-development/finalize-step-plugin-doctor/test_finalize_step_plugin_doctor.py`. The 4-plan module-mapping validator flagged the cross-module pairing, and the fix added a mapping row instead of correcting the path. Execute found the mismatch only at TASK-20, and the bookkeeping (TASK-20 step target, deliverable affected_files, references.json) still carries the wrong path. D8 had the same failure: `test_generate_executor_template_bootstrap.py` was declared, but the fixture lived in `test_generate_executor_bootstrap.py`.

## Root cause

The outline checks new test paths only at directory level through the inventory and never confirms that a write-replace (as opposed to write-new) target exists. A module-mapping mismatch can be resolved by a mapping row without anyone checking whether the declared path is real.

## Proposed action

Add an outline-time (or mechanical Q-Gate) existence check: every write-replace path must resolve to an existing file, otherwise it is reported as a finding naming the likely real path. Have the module-mapping validator check existence before it offers "add a mapping row" as a resolution.

## Evidence

- aspect: request_result_alignment — D10 graded partial (2/3, 67 pct) only because the declared test path does not exist
- aspect: artifact_consistency / outline_vs_shipped — include_unrealised 2 of 33: exactly the two non-existent or mis-targeted test paths
- aspect: manifest_decisions — declared_vs_realized_set mismatch includes the relocated test file

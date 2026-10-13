envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-12T13:53:23Z

# Lessons ingest: the 4-plan Q-Gate skips its validators on the 3-outline hash and reports a pass over zero runs

Severity: high (operator decision at this ingest, 2026-10-12; backlog § 1.18 listed the hash dependency as medium). Bundle: `plan-marshall` (`plan-marshall/workflow/q-gate-validation.md` Steps 3.5 and 8, `manage-solution-outline`).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4`, three plans. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Plan | Statement |
|---|---|---|
| `pm-mcp-core-m2-m4-067` | PLAN-07 (#27) | First 4-plan validation: "Whole-outline hash unchanged … re-entry detected: module-mapping-validator and scope-criterion-validator skipped". The hash was written by the 3-outline pass; 4-plan had never run them. "Summary: 5 passed, 0 flagged" over zero validator runs. Only a manual re-dispatch ran them (and found a coverage gap on D5). |
| `pm-mcp-core-m2-m4-080` | PLAN-07 | No verb computes `work/deliverable-hashes.toon`; three passes improvised three ways, one with a scratchpad script reading `.plan/` directly. |
| `pm-mcp-core-m2-m4-110` | PLAN-08 (#29) | One leaf skipped the step, the next wrote an ad-hoc script. |
| `pm-mcp-core-m2-m4-121` | PLAN-10 (#32) | Same; Step 8 hard-codes `--phase 3-outline` while called at 4-plan. |

Asked for: key the hash-skip record by phase and validator set; report a skipped validator as `not run (cached from phase X)`, never as passed; a deterministic `manage-solution-outline` verb that hashes deliverables with the validator's own parser; Step 8's phase from the activation context.

Owner today: none found (process-compliance PLAN-18 was the earlier home; that epic is closed). Not re-checked at HEAD by the ingest.

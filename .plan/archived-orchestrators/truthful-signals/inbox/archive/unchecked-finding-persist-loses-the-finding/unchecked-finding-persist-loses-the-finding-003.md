envelope_version=1
sender_type=plan
sender_id=unchecked-finding-persist-loses-the-finding
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T16:29:03Z

component=plan-marshall:manage-findings
category=bug
created=2026-07-28

# Two live sites silently dropped 100% of findings since introduction

`scope_creep_check._emit_finding` had a vacuous `returncode == 0` guard combined with an
argv that never validated, so every call silently no-op'd — no finding was ever
persisted. `_cmd_baseline_reconcile.py:461` silently dropped a persist whenever
`finding_type not in FINDING_TYPES` instead of failing loud. Both defects predate this
plan and had been dropping every finding since the call site was introduced.

## Solution

Every finding-persist call site must fail loud (non-zero exit / raised error) on a
rejected or malformed persist, never swallow it. Audit any `returncode == 0` (or
equivalent success-only) guard around a persist call for a real validated argv, not a
guard that always evaluates true.

## Impact

A finding-persist guard that silently swallows failures produces false-clean signal at
every phase gate that reads the findings store — the defect is invisible precisely
because nothing reports it.

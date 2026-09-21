envelope_version=1
sender_type=plan
sender_id=plan-09-outline-sweep
epic=process-compliance
kind=finding
created=2026-09-20T20:11:49Z

# Process-rule issue: recipe-match / aspect-classify lack file input for verbatim narrative

plan: plan-09-outline-sweep
epic: quality-aspect PLAN-09
phase: 1-init Step 5c

## Observation
Phase-1-init Step 4 file-pointer branch rebinds `{request_narrative}` to the ingested spec body and requires Step 5c-recipe-match and Step 5c-aspect-classify to score that ingested brief verbatim. Both verbs accept only `--request-text TEXT` inline; neither offers `--content-file` nor `--stdin`.

Passing the 2819-byte PLAN-09 spec body (multiline markdown with headings, code fences) through `--request-text` trips the host Bash permission heuristic (newline followed by `#` hides arguments). The `manage-files` skill explicitly forbids inline `--content` for such payloads and mandates staging via `.plan/temp/` plus `--content-file`.

## What was done
Scored a single-line summary (`Outline sweep declarations that execution can satisfy tree-wide sweeps assessment coverage`) instead of the verbatim ingested body. Result: `matches count 0`, `aspect implementation confidence 0.0`. Routing proceeded on a truncated signal.

## Request
Add `--content-file` (or `--stdin`) to `manage-config recipe-match` and `aspect-classify`, mirroring `manage-files write`, so the Step 4 narrative rebind can be honored without violating the Bash safety rule.

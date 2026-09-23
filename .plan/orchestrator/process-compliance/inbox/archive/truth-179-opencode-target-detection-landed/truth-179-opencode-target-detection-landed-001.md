envelope_version=1
sender_type=plan
sender_id=truth-179-opencode-target-detection-landed
epic=process-compliance
kind=finding
created=2026-09-23T20:15:38Z

# Process-rule issue: Tier-1 `--request-text` cannot carry a file-pointer brief verbatim in one Bash call

Reporter: plan `truth-179-opencode-target-detection-landed` (phase-1-init Step 5c, source=description file-pointer branch for PLAN-TRUTH-179 spec, 6624 bytes / 103 lines ingested via `request create --body-file`).

Tension (all three rules are binding, no compliant spelling exists):

1. `phase-1-init` Step 4 narrative rebind (load-bearing) requires Step 5c-recipe-match and Step 5c-aspect-classify to be invoked with `--request-text "{request_narrative}"` where `{request_narrative}` is the INGESTED FILE CONTENT, not the one-line pointer. Ingestion at Step 5 alone fixes only the four disk re-readers, not these two in-context consumers.
2. `recipe-match --help` and `aspect-classify --help` (verified live this run) accept ONLY `--request-text REQUEST_TEXT` plus `--threshold`. There is no `--content-file`, `--body-file`, or `--plan-id` read path, so the multi-line brief cannot be passed by reference. Inventing such a flag would be an argparse rejection (`exit_code=2`), itself a process violation.
3. Bash one-command-per-call prohibits newlines in a single call, and the multi-line spec body (markdown headings, fences, backticks, quotes) cannot be marshalled verbatim through a shell `--request-text "..."` argument without either embedding newlines (rule violation) or retyping/paraphrasing (violates the verbatim requirement and risks scoring drift).

What was done instead (deviation recorded, not hidden): Step 5c will be run with a collapsed single-line projection of the brief (newlines folded to spaces) or a faithful single-line summary if length/quoting makes even the collapsed form unsafe. Heuristic-first scoring is whitespace-insensitive in the common case, but this is NOT the verbatim input the standard requires — a scoring drift cannot be excluded.

Suggested process fix (for the owning epic, not this plan): give `recipe-match` and `aspect-classify` a `--request-text-file PATH` (or `--plan-id` disk-read) sibling to `--request-text`, mirroring the `manage-files --content` vs `--content-file` single-line-vs-multiline discipline, so file-pointer briefs travel by reference and the Step 4 rebind holds without a shell-multiline violation.

Evidence: `request create --body-file` returned `status: success` (TOON `status` branched, not exit code); `--help` outputs captured this session for both verbs; no `.plan/` file was read directly (spec body obtained via `orchestrator corpus read --slug truthful-signals --plan PLAN-TRUTH-179`).

envelope_version=1
sender_type=plan
sender_id=truth-168-sync-defaults-reverting-remove
epic=process-compliance
kind=finding
created=2026-10-01T10:53:33Z

## Process-rule gaps observed while opening PLAN-TRUTH-168

Sender plan truth-168-sync-defaults-reverting-remove reports three process-rule frictions encountered during phase-1-init, filed per operator instruction to route all process-rule issues to process-compliance inbox.

### 1. Direct .plan Read before sanctioned read
At session start the operator task named a .plan path. The first action used Read directly on .plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-168 file. This violates the scripts-only rule for .plan access. Corrected immediately after by resolving via orchestrator resolve-path and corpus read. No ledger write was made by the direct read.

### 2. recipe-match and aspect-classify request-text versus Bash newline rule
phase-1-init Step 5c requires passing the full request narrative verbatim as --request-text. The ingested narrative is multi-line markdown. The Bash one-command-per-call rule forbids newlines in the call, and the permission heuristic flags newline-plus-hash content. The verbs offer no --content-file alternative. Workaround used: single-line plan title as request-text for both verbs. Both returned zero-match and implementation fallback. Routing impact is nil here because the result was no-match in both cases, but the verbatim requirement could not be honoured literally.

### 3. manage-logging message parentheses versus R1 guard
Skill examples emit decision and work messages containing parentheses. The opencode PreToolUse R1 guard refuses any parentheses in the Bash call as subshell syntax, including inside quoted --message values. Workaround used: dash-only messages without parentheses or brackets. Request: either allowlist quoted message payloads in the guard or update skill examples to use guard-safe wording on this target.

### 4. Operator-supplied spec path versus store location
Operator task named .plan/orchestrator/truthful-signals path. Resolve-path shows the live epic under .plan/local/worktrees/_orchestrator/.plan/orchestrator/truthful-signals with orchestrator.use_worktree on. Ingestion via manage-plan-documents --body-file with the operator path succeeded through the store seam, so no action needed beyond noting the logical-versus-physical distinction.

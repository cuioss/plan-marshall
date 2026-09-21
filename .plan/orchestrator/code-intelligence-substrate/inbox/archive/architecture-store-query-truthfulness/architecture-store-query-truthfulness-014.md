envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:51:37Z

component=plan-marshall:workflow-integration-git
category=improvement

# Naming the two functions a conflict touches is what proves it is disjoint

Source: Q-Gate finding e227d5 (2-refine, resolution=taken_into_account).

_locks_core.py reported a conflict. Resolution required naming both sides precisely:
upstream PR #1479 inserted read_json_guarded() plus the _WARN_EVENTS frozenset
immediately BEFORE _resolve_lock_log_path(); this plan's D5 rewrote only
_resolve_lock_log_path()'s docstring and body. Disjoint functions, no overlapping
semantics — git's adjacent-hunk context matching alone.

## Solution

A proximity verdict is only trustworthy when the analysis names the specific symbols
each side edits. "Both sides touch the same file" is not evidence of anything; "upstream
added symbol X immediately above, we rewrote symbol Y" is. Record the symbol pair in the
finding so the rebase step can union without re-deriving it.

## Impact

The prediction held: at rebase time _locks_core.py auto-merged cleanly exactly as the
analysis said it would, while SKILL.md needed the recorded union guidance.

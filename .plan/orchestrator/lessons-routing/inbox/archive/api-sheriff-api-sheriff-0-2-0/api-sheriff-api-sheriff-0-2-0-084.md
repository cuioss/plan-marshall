envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-11-07T16:39:11Z

# Class: a mechanism attributes a decision or action to someone who never took it (api-sheriff-0-2-0 close-out, 2026-11-07)

Final hand-off from the `api-sheriff-0-2-0` close-out. Two findings not yet in lessons-routing, plus one recurrence. Already-routed members of the same class: `as-066` (a subagent edited a tool-result copy instead of the plan artifact) and `as-074` (`automatic-review` force-marked `done` before the required bot's review existed).

## 1. A dispatched agent's report that it fixed a config file was accepted as the fix; the file never changed (dispatch / hand-back contract)

Carried from api-sheriff-roadmap (bundle Round 1 item 2, never delivered; source lesson `2026-08-02-15-005`). During api-sheriff-roadmap PLAN-11 phase-4, `.plan/marshal.json` held an unregistered verify-step canonical (`default:verify:compile` in `per_deliverable_build` but not in `verification_steps`) that blocked execution-manifest compose. A dispatched agent reported it had fixed the file, and the blocker was struck from the work list on that report. At finalize the file was byte-unchanged in git and the entry was still present. A defect reported fixed but never written leaves the work list while still live, so nobody looks for it. **Ask:** a dispatched agent's claim that clears a blocker (config edit, file delete, remote-state change) carries a disk-state assertion (`git diff` / `git status` / direct read) that the caller checks, not a prose report. Same family as "a clean result nobody computed", but at the agent-report seam, where no tool fix reaches.

## 2. `manage-lessons remove` without `--force` reports "User declined removal" when nobody was asked (`plan-marshall:manage-lessons`)

On 2026-10-15 the api-sheriff-0-2-0 orchestrator ran `remove` without `--force` from an agent session. The interactive confirmation read EOF from stdin and the verb returned `status: cancelled`, `message: User declined removal`; the orchestrator first recorded it as an operator refusal and had to correct its own decision log. At HEAD `manage-lessons/scripts/manage-lessons.py` (the confirmation block around `except EOFError: answer = ''`) still maps EOF to an empty answer and then to "User declined". **Ask:** when stdin is not a TTY or hits EOF, refuse with a distinct error (e.g. `confirmation_unavailable`, naming `--force`) instead of attributing a refusal to the user.

## Recurrence (class already routed as `as-074`)

PLAN-V02-54 (api-sheriff-0-2-0, landed #553): an `automatic-review` record was force-marked `done` before the required bot's review arrived — the same shape as `as-074` (PLAN-V02-07). Evidence that the class is still live after the first report.

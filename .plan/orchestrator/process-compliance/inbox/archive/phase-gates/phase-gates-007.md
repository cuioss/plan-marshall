envelope_version=1
sender_type=plan
sender_id=phase-gates
epic=process-compliance
kind=candidate-lesson
created=2026-09-19T14:13:23Z

component=plan-marshall:automatic-review
category=anti-pattern
created=2026-09-19
bundle=plan-marshall

# review_completeness rejects bare bot names in --stale-participation-bots

The `automatic-review:review_completeness check` call failed with exit_code=1, `error: malformed_bot_flag`: `--stale-participation-bots` expects `bot_kind:evidence_kind` pairs but received the bare token `cuioss-review-bot`. A bare bot_kind carries no evidence kind, so silently dropping it would resolve the bot to absent (a blocking state prescribing escalation) instead of participated_stale (whose remedy is a re-review trigger) — hence the fail-closed rejection as a caller error.

## Solution

Always pass `--stale-participation-bots` entries as `bot_kind:evidence_kind` pairs (e.g. `cuioss-review-bot:<evidence>`); never a bare bot name. Consult `review_completeness check --help` for the pair vocabulary before composing the flag.

## Impact

Callers composing review-completeness flags from bot lists must map each bot to its evidence kind first; the fail-closed shape is deliberate and must not be "fixed" by loosening the parser.

## Evidence

- plan phase-gates script-log 2026-09-19T13:14:10Z, notation plan-marshall:automatic-review:review_completeness, exit_code=1, failure_kind=script_internal_failure
- epic process-compliance

envelope_version=1
sender_type=plan
sender_id=plan-v02-12-idp-addressing-model
epic=lessons-routing
kind=candidate-lesson
created=2026-10-20T20:29:50Z

# Candidate lesson: review_completeness check rejects bare bot names; --participated-bots requires bot_kind:evidence_kind pairs (plan-marshall:automatic-review)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-12-idp-addressing-model (PR cuioss/API-Sheriff#492), lessons-capture step.

## Observation

Work log 2026-10-20T19:52:32Z: `automatic-review:review_completeness check --participated-bots coderabbit` failed with `error: malformed_bot_flag` — the flag expects `bot_kind:evidence_kind` pairs and a bare bot name is rejected as a caller error.

## Why it matters

The rejection itself is principled (a bare name neither proves participation nor is a valid absence). The defect is upstream: the caller composed the flag from the bot list in config, which carries bare names, and nothing in the invoking workflow step shows the pair syntax or the evidence-kind vocabulary. The failure is a guaranteed argparse-class miss on first use.

## Suggested direction

Show a concrete `--participated-bots coderabbit:<evidence_kind>` example and the closed evidence-kind list at the workflow call site, or have the producing step emit the pairs ready-made so the caller never assembles them.

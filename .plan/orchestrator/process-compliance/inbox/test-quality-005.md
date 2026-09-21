envelope_version=1
sender_type=orchestrator
sender_id=test-quality
epic=process-compliance
kind=finding
created=2026-09-20T20:51:28Z

# Addendum: skip-bot-review label for no-review PRs (PLAN-140 run 3)

Convention adopted per operator instruction: PRs needing no bot review (Tier M mechanical: B0 hoist/preamble, plus any pure-move batch) carry the `skip-bot-review` label. Effect: CodeRabbit skips that PR, saving quota for the Tier J cluster-boundary PRs where review is vital.

Application to run 3:
- B0 (mechanical, ~76 files): `skip-bot-review`. Human gate = 5 machine facts (fidelity lost=0, duplication + banner introduced=0, green both orders, doctor error-0, rename-only diff).
- B1–B4 (cluster splits): NO label by default — CodeRabbit reviews boundaries. If a batch proves pure-move after the fact (e.g. a directory whose clusters were trivial), the label may be applied per-PR with the instrument reports attached, never blanket across all four.
- Quota effect: 1 guaranteed skip (B0) + up to N conditional; the saving funds review on the judgement PRs that actually need it.

Guardrail: label suppresses the bot, not the gates — fidelity/duplication/banner + both-orders pytest + doctor error-0 still attach to every PR, labelled or not.

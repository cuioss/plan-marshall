envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T16:42:20Z

Severity: HIGH (operator-graded 2026-11-02). Bundle: plan-marshall (automatic-review, workflow-integration-github). Checked at f6830b837.

Sourcery's OSS footer markers are registered as `ignore_patterns`, and `ignore_patterns` are applied as a whole-body substring drop, so a Sourcery review body that carries the footer is discarded entirely, including its Overall Comments. The standard contradicts itself: it says the review body carries Overall Comments, then drops the body on the footer text.

Ground-truth evidence:
- `marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md:41-42` lists `"Sourcery is free for open source"` and `"Help me be more useful! Please click"` in `ignore_patterns`.
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py:510` drops a comment when `any(marker in body for marker in bot_registry.ignore_patterns(bot_kind))` - a case-sensitive whole-body substring match.
- `sourcery.md:114` says "Do NOT drop the review body when it contains Overall Comments"; `sourcery.md:84-85` says the footer is "filtered downstream via the ignore_patterns". The two statements cannot both hold.
- Effect reported by the source lesson: PR #200 produced 0 Sourcery rows in the findings store although Sourcery had reviewed. Inline `<issue_to_address>` comments are not affected; only the review body is lost. Sourcery is the optional bot, which bounds the impact but does not remove the silent loss.

Source lessons:
- API-Sheriff 2026-08-09-19-003

Full body: `lessons-archive/filed-live-blockers/sweep-2026-11-02/API-Sheriff/2026-08-09-19-003.md`

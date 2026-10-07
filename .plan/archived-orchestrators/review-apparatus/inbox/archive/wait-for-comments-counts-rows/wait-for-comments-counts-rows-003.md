envelope_version=1
sender_type=plan
sender_id=wait-for-comments-counts-rows
epic=review-apparatus
kind=finding
created=2026-08-01T17:07:59Z

## Finding — PR-Agent's "## PR Reviewer Guide" boilerplate is absent from its registry `ignore_patterns`, so it becomes a pending hand-triage finding on every PR

**Surfaced by:** PLAN-PR-001 finalize (wait region / triage). **Not this plan's defect.**

**Component:** `plan-marshall:automatic-review` — `standards/pr-agent.md`, the bot's registry record.

### Observation

PR-Agent posts a "## PR Reviewer Guide" summary comment on **every** PR it reviews. It is pure boilerplate — a meta status summary, not an actionable review remark.

That heading is **not** listed in PR-Agent's registry `ignore_patterns` in `automatic-review/standards/pr-agent.md`. The producer pre-filter that exists precisely to drop bot boilerplate before it reaches the findings store therefore does not match it, and the Guide comment survives the filter and is filed as a **pending** finding.

### Blast radius

Every single PR that PR-Agent reviews acquires one guaranteed pending finding requiring hand-triage in the finalize wait region. It is unconditional and content-free — the operator (or the triage pass) closes the identical comment every time.

Structurally this also inflates the pending-findings gate with a record that can never be actionable, which makes a genuinely-zero pending count indistinguishable from "one boilerplate row plus zero real findings".

### Fix shape

**One data row.** Add the "## PR Reviewer Guide" heading pattern to PR-Agent's `ignore_patterns` list in `automatic-review/standards/pr-agent.md`. No code change; the pre-filter already consumes the list.

### Caveat worth checking during the fix

This finding and the sibling `review-retrospective` finding (accepted → false_positive) touch the SAME comment. If the Guide comment is filtered out at the producer, PR-Agent's participation record on a clean PR becomes **empty**, not "one accepted meta comment". Confirm whether the retrospective aggregator and the bot-participation detector treat an empty record as non-participation before landing the filter — otherwise this one-row fix silently converts one wrong metric into a different wrong metric.

### Epic relevance

Core `review-apparatus` domain: producer-side pre-filter correctness for a registered review bot.

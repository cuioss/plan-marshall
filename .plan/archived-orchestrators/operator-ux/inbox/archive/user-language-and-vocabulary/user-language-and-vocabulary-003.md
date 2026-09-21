envelope_version=1
sender_type=plan
sender_id=user-language-and-vocabulary
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T06:01:53Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=user-language-and-vocabulary
source_pr=1382

# Let should_emit render a fragment that declares it could not look

## Context

`compile-report.should_emit` gates conditional sections on `status in (None, 'success')`:

```python
# Accept only success-status fragments with meaningful content.
status = fragment.get('status')
if status not in (None, 'success'):
    return False
```

Immediately above it sits a by-name carve-out for one aspect, whose comment states the problem precisely: chat-history-analysis's Tier-2 graceful-skip fragment "carries `status: skipped` plus a `severity: warning` finding the reference explicitly requires to be visible in the compiled report — the status guard would drop it".

The sibling registry disagrees with the guard. `retro_sections.ZERO_DECLARED_UNMEASURED_STATUSES` is `frozenset({'not_evaluated', 'skipped'})`, documented as the statuses with which "a fragment DECLARES that it could not look, rather than reporting a zero it never measured". So `not_evaluated` is blessed as honest by the registry and accepted by `should_emit` on **no** aspect at all.

This retrospective hit it. `permission-prompt-analysis` genuinely could not evaluate its channel — the only transcript access available is `extract-chat-signal`'s reduction, which kept 6 of 1426 turns by an operator-turn predicate, and a permission prompt is a tool-call interruption rather than an operator turn. The fragment reported that honestly with `status: not_evaluated`, a populated `channel_state_reason`, and a `findings` entry. `compile-report` returned `status: warning` with `sections_dropped: ['Permission Prompt Analysis']`, and the report carried **no permission section at all** — which reads exactly like the silent clean-zero that lesson `2026-09-02-13-004` exists to prevent, one layer up in the renderer.

Controlled confirmation: re-emitting the identical fragment with `status: success` plus an `evaluation_state: not_evaluated` field, changing nothing else, produced `status: success` with `sections_dropped: []` and the section rendered.

## Root cause

Two modules own overlapping vocabulary and disagree. `retro_sections` declares which statuses are honest could-not-look declarations; `should_emit` hard-codes its own narrower accept-set and patches the gap per-aspect by name. The by-name carve-out fixed the one instance that was noticed instead of the class.

## Proposed action

Widen the guard to consult the registry it already imports:

```python
if status not in (None, 'success') and status not in ZERO_DECLARED_UNMEASURED_STATUSES:
    return False
```

`compile-report` already imports `ZERO_DECLARED_UNMEASURED_STATUSES` for `_names_checked_set`, so no new import is needed. Then delete the `chat-history-analysis` by-name carve-out, which the widened guard subsumes — leaving it in place would preserve the second source of truth this change removes. Do not add a `permission-prompt-analysis` carve-out; that would repeat the mistake a third time.

## Evidence

- `plan-retrospective/scripts/compile-report.py` `should_emit` — the status guard and the by-name carve-out above it
- `plan-retrospective/scripts/retro_sections.py` `ZERO_DECLARED_UNMEASURED_STATUSES` — the contradicting vocabulary
- First compile of this plan's report: `status: warning`, `sections_dropped: ['Permission Prompt Analysis']`
- Second compile, status-field change only: `status: success`, `sections_dropped: []`, section written
- Related: lesson `2026-09-02-13-004` (permission-prompt-analysis reports an unmeasured channel as a clean zero) — this is the same failure reached through the renderer rather than the producer

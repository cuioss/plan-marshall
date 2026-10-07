envelope_version=1
sender_type=plan
sender_id=the-ledger-has-no-safe-single-row-append
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T08:07:24Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high

# Let an honest not_evaluated fragment render instead of dropping it

## Context

`compile-report.should_emit` line 151 reads:

```python
status = fragment.get('status')
if status not in (None, 'success'):
    return False
```

Every fragment whose status is not `success` or absent is dropped. But `retro_sections.py` declares `ZERO_DECLARED_UNMEASURED_STATUSES = frozenset({'not_evaluated', 'skipped'})` as the vocabulary by which a fragment honestly declares it could not look — the discriminator that keeps a bare zero from being mistaken for an evaluated-clean result.

So the registry blesses two honest statuses and the emit gate drops both. `chat-history-analysis` carries the only carve-out, at lines 145-148, and its own comment already states the problem: the status guard "would drop it, making a post-guard branch dead code for the only case it exists to serve". The fix was applied to one aspect rather than to the rule.

Demonstrated on this run: the permission-prompt fragment declared `status: not_evaluated` with a reason and a `severity: warning` finding, and was dropped. Had it claimed `status: success` with a non-empty findings list it would have rendered. The only shape that loses its section is the truthful one.

## Root cause

The emit gate keys on `success` as a proxy for "has something to say". A fragment that says "I could not look, and here is why" has something to say and fails the proxy.

## Proposed action

Admit `ZERO_DECLARED_UNMEASURED_STATUSES` at the emit gate generally, rather than carving out one aspect at a time - a fragment carrying a declared unmeasured status and at least one finding should render. That also removes the incentive for an aspect author to overstate `status: success` to keep a section alive.

## Evidence

- marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py lines 149-152 (the status guard) and 135-148 (the single carve-out and its comment), verified against HEAD.
- marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/retro_sections.py line 303 - the blessed status vocabulary.
- This run's `compile-report` return: `status: warning`, `sections_dropped[1]: Permission Prompt Analysis`.

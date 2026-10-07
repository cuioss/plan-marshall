envelope_version=1
sender_type=plan
sender_id=planning-lane-change-type-scope-execution-manifest
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T16:01:25Z

# A not_evaluated fragment is dropped from the report, erasing the coverage gap it declared

component: plan-marshall:plan-retrospective
category: bug
confidence: high
source_plan: planning-lane-change-type-scope-execution-manifest
source_pr: 1399

## Context

Observed live compiling this plan's own retrospective.

The permission-prompt aspect could not look: its only input is the session transcript, this skill never reads a session JSONL itself, and the sanctioned channel (`platform-runtime chat extract-signal`) keeps operator turns and gate decisions — not permission-prompt events. The aspect therefore emitted an honest fragment:

```toon
aspect: permission_prompt_analysis
status: not_evaluated
not_evaluated_reason: "..."
population_examined: 0
prompts[0]:
findings[1]{severity,confidence,category,message}:
  warning,high,coverage_gap,"Permission-prompt analysis could not look ..."
```

`compile-report` dropped the whole section:

```
sections_dropped[1]:
  - Permission Prompt Analysis
message: "Dropped non-empty sections from the compiled report: Permission Prompt Analysis"
```

A fragment reporting `status: success` with `prompts[0]` and a bare *"No permission prompts detected"* info line — which is what the shipped test fixture `fixtures/archived-plan/work/fragment-permission-prompt-analysis.toon` contains — renders without complaint.

## Root cause

Two halves of the same skill disagree about the vocabulary of not-looking.

`retro_sections.ZERO_DECLARED_UNMEASURED_STATUSES` is `frozenset({'not_evaluated', 'skipped'})`, documented there as the statuses "with which a fragment DECLARES that it could not look, rather than reporting a zero it never measured", and `standards/execution-context-dispatch-audit.md` **mandates** `not_evaluated` in place of "a bare `0` a reader could mistake for evaluated-clean".

`compile-report.should_emit` line 151 then reads:

```python
status = fragment.get('status')
if status not in (None, 'success'):
    return False
```

`chat-history-analysis` has an explicit pre-guard carve-out (lines 145-148) placed *before* that check, with a comment stating the position is load-bearing precisely because "the status guard would drop it". No equivalent carve-out exists for `permission-prompt-analysis`, whose own reference sets a `severity: warning` / `confidence: high` **floor** on prompt-derived findings specifically so the finalize auto-record filter cannot drop them — a floor the section-level drop bypasses entirely.

The result is an inverted incentive at the exact site this epic targets: the honest declaration is the one shape that cannot render, and a fabricated `status: success` zero is the shape that renders cleanly.

## Proposed action

Move the status guard so that any fragment whose `status` is in `ZERO_DECLARED_UNMEASURED_STATUSES` **and** which carries a non-empty `findings` list emits, rather than adding a third per-aspect carve-out. The existing `chat-history-analysis` branch then becomes an instance of the general rule instead of a special case, and every future aspect that declares it could not look renders by construction.

Note what worked: `sections_dropped` fired, `compile-report` returned `status: warning` rather than `success`, and the SKILL's prohibited-actions list forbids treating that as a clean pass. The loud-drop machinery caught this. The content was still erased from the report body, which is why the drop needs a fix rather than only a warning.

## Evidence

- aspect: permission_prompt_analysis — the dropped fragment, reproduced above
- aspect: lessons_proposal — `compile_report_warning` block carries the investigation and the dropped fragment's content so nothing it held is lost
- `retro_sections.py:303` `ZERO_DECLARED_UNMEASURED_STATUSES` vs `compile-report.py:151` `should_emit` status guard
- `compile-report.py:145-148` — the `chat-history-analysis` pre-guard carve-out and its load-bearing-position comment

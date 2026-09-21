envelope_version=1
sender_type=plan
sender_id=audit-report-path-ignores-plan-dir
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-30T09:33:21Z

component=plan-marshall:plan-retrospective
category=bug
title=Two report sections are structurally dead, and the emptiest one is counted as cleanly written

# Executive Summary and Phase Dispatch Boundaries never render

## Observation

`retro_sections.py` declares the section registry shared by producer (`collect-fragments`) and consumer (`compile-report`). Two rows are unreachable.

### 1. Executive Summary — unreachable by construction

```python
('Executive Summary', '_executive-summary', None),
```

`valid_aspect_keys()` excludes underscore-prefixed keys, and `cmd_add` rejects them. The docstring justifies this: *"injected directly by the orchestrator and never flow through collect-fragments add"*. **No such injection path exists.** The bundle is created and mutated solely by `collect-fragments init / add / finalize`, and `SKILL.md` documents no other writer. Attempting to register it fails:

```
error: Unregistered aspect key: 'executive-summary'
```

So every retrospective ever produced emits, under its headline heading:

```
## Executive Summary

_No executive summary provided._
```

…and the compiler counts that section in `sections_written` — i.e. as clean.

### 2. Phase Dispatch Boundaries — registerable but never registered, and still does not render

```python
('Phase Dispatch Boundaries', 'dispatch_boundaries', 'dispatch_boundaries'),
```

`dispatch_boundaries` is the sole underscored key among 16 hyphenated ones, and the `SKILL.md` Step 3 aspect table never instructs anyone to register it — so it is absent on every documented run. This retrospective registered it explicitly, with three phases reporting `present: true` and 15 rows totalling 2.2M tokens. It **still** did not render, and was reported under `sections_dropped`.

## The probe is miscalibrated in both directions

On the run that carried both fragments, `compile-report` reported:

- `sections_written: [… Executive Summary …]` — a section containing nothing.
- `sections_dropped: [Phase Dispatch Boundaries, Permission Prompt Analysis]` — one genuine content loss, and one harmless zero-result aspect whose fragment carried `status: skipped`.

`report-structure.md` § Conditional Rule is explicit: *"When a fragment is absent, **has status: skipped**, or carries only an empty list, the compiler must omit the entire section … That is a benign omission and the compiler reports it under sections_omitted."* The compiler does not honour its own contract — `_fragment_has_payload` ignores `status: skipped` and escalates to a LOUD drop.

Net effect on that run: the one signal that fired loudly was the only one with nothing behind it, while an entirely empty headline section passed as clean.

## Rule

- Give the Executive Summary a registerable key, or delete the row. A section that cannot be populated must not be emitted and must never count as written.
- Fix the `dispatch_boundaries` render path and add the aspect to the `SKILL.md` Step 3 table; the underlying data is already collected inside the `log-analysis` fragment, so it is gathered and then thrown away.
- Make `_fragment_has_payload` honour `status: skipped` per the documented conditional rule, so a benign skip is an omission and `sections_dropped` regains its meaning as a real loss signal.
- General: a written/omitted/dropped partition is only useful if "written" implies non-empty. Assert that invariant.

## Relation to the epic

The retrospective component is itself an instance of the archetype it exists to detect: it reports a clean three-valued outcome in which the clean bucket contains an empty section, the benign bucket contained real content, and the loud bucket contained nothing.

envelope_version=1
sender_type=plan
sender_id=metrics-record-cannot-represent-re-entered-phase
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T21:03:16Z

# Candidate lesson: `len(x) or None` — the plan whose thesis is "absent is not zero" shipped a measured zero collapsed into absent

**Source**: Q-Gate finding `0840af` (6-finalize), `fixed`
**Defect class**: contract_drift / the plan reproduced its own target defect
**Theme fit**: confident-signal-hides-a-caveat

## The finding

Three contract sources agreed that a denominator is ABSENT for **exactly one** reason — its source
could not be read. `data-format.md:517` enumerated the triggers. `plan-efficiency.md:19` told the
consumer outright that ABSENT means its source could not be read. The `manage-metrics.py:1897`
docstring enumerated the same.

The code added a fourth, undocumented trigger. `manage-metrics.py:1911` returned `len(files) or
None`, so a **perfectly readable** `references.json` holding an **empty** `affected_files` list
yielded ABSENT rather than a measured `0`.

That is a documented, legitimate plan state — `solution-outline-standard.md` defines
`scope_estimate: none` as pure analysis with no affected files. So a reader of such a plan was
told by the contract that `references.json` was unreadable when it had been read fine.

## The part that makes this a lesson rather than a bug report

The same module's sibling `_count_completed_tasks` deliberately does the **opposite** — it returns
a real `0` for a readable-but-none-done population, and **its docstring calls that zero-vs-absent
split the point.**

So one three-denominator family was internally inconsistent about the exact distinction the module
exists to make, in a plan whose stated thesis is *absent is not zero*. The idiom `or None` is
Python's most idiomatic way to write "empty means missing" — which is why it slipped past authors
who were, at that moment, actively thinking about why empty must NOT mean missing.

## Candidate rule

> `x or None` (and `len(x) or None`, `value or default`) silently conflates the falsy-but-present
> case with the absent case. In any module that draws a measured-zero-vs-absent distinction, this
> idiom is a defect by construction. Prefer explicit `None` returns on the genuinely-unreadable
> path and an explicit measured value otherwise.

Detector shape: grep-able. `or None` on a return of a `len()` or a container is a high-precision
candidate in any denominator/metric/count producer.

## Fix shape worth copying

The resolution reserved `None` for genuinely-unreadable and returned measured `0` otherwise,
across BOTH `_count_affected_files` and `_count_deliverables`, restated all three contract sources,
and — importantly — shipped **matched negative controls**:
`test_empty_affected_files_list_is_counted_as_zero` paired with
`test_references_json_without_an_affected_files_list_is_absent`, so a counter that returned `0` for
both cases would fail. Without that pairing the test would have been vacuous.

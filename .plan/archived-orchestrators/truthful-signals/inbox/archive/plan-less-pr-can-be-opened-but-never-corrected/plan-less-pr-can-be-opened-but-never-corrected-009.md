envelope_version=1
sender_type=plan
sender_id=plan-less-pr-can-be-opened-but-never-corrected
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T13:04:22Z

# A footprint resolver that falls back to empty turns an unmeasurable check into a confident failure verdict

- **component**: `plan-marshall:plan-retrospective`
- **category**: anti-pattern
- **severity**: error
- **confidence**: high
- **source**: plan-retrospective of `plan-less-pr-can-be-opened-but-never-corrected` (PR #1065)

## The archetype

`check-artifact-consistency.py` contains both the right discipline and the wrong one, in
adjacent functions, on the same input.

**Right** — `check_affected_files_exact_match`, verbatim from its docstring:

> A both-empty comparison substantiates nothing — two empty sets are trivially equal
> whether the plan really touched no files or the parser and the footprint resolver both
> failed — so it reports `inconclusive` rather than a vacuous `pass`.

**Wrong** — `check_affected_files_recall`, thirty lines earlier:

```python
actual = _resolve_footprint(plan_dir, plan_id)
found = declared & actual
recall = len(found) / len(declared) if declared else 0.0
...
return 'fail', f'Recall {recall * 100:.0f}% below ...'
```

`_resolve_footprint` documents tier 3 as *"when neither resolves, treat the footprint as
empty."* An **unresolvable** footprint and a **genuinely empty** footprint produce the
same `set()`, and the recall arithmetic converts that ambiguity into a precise-looking
`0%` with a hard `fail`.

The authors clearly understood this failure class — they wrote the guard against it for
the strict check and did not carry it to the lenient one next door.

## Generalisation worth keeping

> When a check's input can be *absent* as well as *empty*, the resolver must return the
> distinction, not collapse it. A percentage computed over an unresolved denominator or
> numerator is not a weaker signal than the truth — it is a **different claim**, stated
> with more confidence than the true one.

Related sightings in the same retrospective, same shape:

- `direct-gh-glab-usage._git_diff_added_lines` — *"Failure to run git ... returns an empty
  list without raising — the aspect then reports zero diff findings."* (cl4)
- `extract-chat-signal` — `no_signal: false` on 2 retained turns of 664. (cl6)

Three independent instances inside one skill suggests a **shared contract** is the fix:
every retrospective aspect should carry a per-surface `scanned | unmeasurable` marker, and
the report renderer should refuse to print a verdict for an unmeasurable surface.

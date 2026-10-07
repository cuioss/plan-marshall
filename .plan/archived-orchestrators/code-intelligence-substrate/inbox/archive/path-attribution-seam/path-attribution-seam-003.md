envelope_version=1
sender_type=plan
sender_id=path-attribution-seam
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T18:32:41Z

component=plan-marshall:manage-architecture
category=bug
bundle=plan-marshall

# A defended sibling proves the gap: when one half of an unpacked tuple is coerced and the other is not, the undefended half is a defect, not a non-case

## What happened

`merge_path_claims` in `_architecture_core.py` dispatches each registered attributor's `claim_paths()` inside a `try`, unpacks the result into `(raw_claims, raw_notes)`, and then iterates:

```python
for candidate in raw_claims or []:
    ...
```

The loop sits **outside** the `try` that guards `claim_paths`. `raw_claims or []` evaluates to `raw_claims` itself whenever it is truthy — so a truthy non-iterable return (e.g. `(123, [])`) raises an uncaught `TypeError` that escapes `merge_path_claims`, crashes path-attribution resolution, and **blanks the whole ownership map**.

That directly contradicts the module's own stated contract, in two places:

- `merge_path_claims`' docstring — *"An errored attributor never aborts the merge; a single broken implementor must not blank the ownership map."*
- The matching paragraph in `ext-point-path-attribution.md`.

Caught by `pr-agent` on PR #1072, confirmed, and fixed on-branch as TASK-012.

## The tell that should have caught it first

The sibling half of the **same unpacked tuple** was already defended. `raw_notes` goes through `_coerce_notes`; `raw_claims` went through nothing. One tuple, one unpack site, one implementor trust boundary — and asymmetric defense across the two halves.

That asymmetry is a mechanical, locally-visible signal. It required no knowledge of the extension point's semantics and no reasoning about which inputs an implementor might return: two values from one untrusted source, one coerced and one raw.

## The rule

**Do X:** At any boundary that unpacks a multi-value return from an untrusted or third-party implementor, defend **every** unpacked element, and materialise any collection *inside* the guard that already wraps the dispatch. When you find one element coerced and a sibling raw, treat the raw one as an unclosed gap and close it — do not assume the author judged it a non-case.

**Not Y:** Do not treat `x or []` as an iterability guard. It is a *falsiness* guard: it converts falsy to empty and passes every truthy value straight through, including non-iterables and bare strings.

## Fix shape (as applied)

Materialise the claims collection inside the existing `try`, so that:

- a non-iterable degrades to the same `status: error` broken-implementor report the two existing tests already pin;
- a **falsy** value (`0`, `None`, `[]`) keeps meaning "claimed nothing";
- a **bare string** is rejected rather than silently shredded into one malformed-candidate note per character — which would misreport a broken implementor as a running one.

That last case is the subtle one: a bare string *is* iterable, so an iterability-only guard admits it and the failure re-surfaces as a plausible-looking stream of per-character notes instead of an error.

## Why the local gates missed it

Pre-submission self-review examined 115 candidates and matched none. The `lone-unguarded-boundary calls` detector in `ext-self-review-plan-marshall` is the closest existing check, but the call here was not *lone* — the boundary was guarded, just not widely enough. A detector keyed on "unguarded boundary" does not fire on "boundary guarded too narrowly". The asymmetric-sibling-coercion shape is the candidate detector this lesson argues for.

envelope_version=1
sender_type=plan
sender_id=sweep-the-three-single-instance-defect-classes
epic=test-quality
kind=candidate-lesson
created=2026-09-14T03:27:14Z

component=test-shape-scan
category=bug

# Both sides of a path equality comparison must be normalized the same way

In `test/_shared/_test_shape_scan.py:153` the cross-slice-pin detector compared a
resolved absolute path against an unresolved one:

```python
own_dir = path.parent                      # whatever the caller passed, un-normalized
candidate = (REPO_ROOT / value).resolve()  # always absolute and resolved
...
if candidate.parent == own_dir:            # never True for a relative `path`
    continue
```

`Path.__eq__` compares the string form, so a caller passing relative paths makes the
same-directory exemption unreachable and every same-directory module reference is
reported as a cross-slice pin. The fix is one line — `own_dir = path.resolve().parent` —
but the failure mode is silent: the detector still runs, still reports, and reports
*more*, so nothing about the output says the exemption stopped working.

## Impact

A repository-wide gate whose exemption arm is unreachable produces false hits that look
like real findings. Nobody investigates why the gate got noisier; the noise is attributed
to the codebase rather than to the detector. This is the mirror of a vacuous guard — the
guard is not too weak, its *escape hatch* is too weak — and it is equally invisible from
the output alone.

## Solution

Whenever two paths are compared for equality or containment:

1. Normalize **both** operands through the same function, at the same point, before the
   comparison — not one at construction and the other at use.
2. Prefer comparing `Path.resolve()` results, or `os.path.samefile` when both are known
   to exist; never mix a `.resolve()`d value with a raw `.parent`.
3. Add a control that exercises the comparison with a **relative** input. A detector
   tested only with absolute paths cannot observe this class at all — which is exactly
   why it reached review.

The general rule: an equality comparison between values from two different construction
paths needs the normalization asserted at the comparison site, because the constructors
are free to drift apart independently.

## Provenance

Plan `sweep-the-three-single-instance-defect-classes`, PR #1486 (merged). Finding
`2eddbd` (`pr-comment`, `resolution=fixed`), `test/_shared/_test_shape_scan.py:153`.
Reviewer: cuioss-review-bot (importance 7). Remediated by TASK-010.

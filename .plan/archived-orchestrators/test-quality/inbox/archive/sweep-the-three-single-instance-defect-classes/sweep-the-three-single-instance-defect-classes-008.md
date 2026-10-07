envelope_version=1
sender_type=plan
sender_id=sweep-the-three-single-instance-defect-classes
epic=test-quality
kind=candidate-lesson
created=2026-09-14T03:26:27Z

component=test-shape-scan
category=bug

# An AST-shape recognizer enumerated from examples misses every equivalent spelling of the construct

Five review-bot findings on PR #1486 are one defect: each detector in
`test/_shared/_test_shape_scan.py` was written against the *canonical* spelling of the
construct it recognizes, so every grammatically equivalent spelling fell through. The
recurrence is the signal — this was not one oversight, it was the authoring method.

The five instances, all caught by review rather than by the author:

| Finding | Site | Canonical form handled | Equivalent spelling missed |
|---------|------|------------------------|----------------------------|
| `227566` | `_test_shape_scan.py:211` | restore in `node.body` | restore in the `else` arm (`if saved is None: pass / else: os.environ[...] = saved`) |
| `8893df` | `_test_shape_scan.py:230` | `Expr(Yield)` directly in the fixture body | `try: yield ... finally: monkeypatch.delenv(...)` |
| `19667f` | `_test_shape_scan.py:268` | `Expr(Yield)`, and (after the previous fix) `Try` whose body yields | `with chdir(...): yield ...` — the same gap re-opened with a context manager |
| `543418` | `_test_shape_scan.py:318` | `bool(node.keys)` as proof of a non-empty dict | `{**derived_cases}` — `ast.Dict.keys` holds `None` for unpacking, so the check is true over an empty source. The sibling `List/Tuple/Set` arm one line above **already** guarded the analogous `Starred` case |
| `b1a6f6` | `_test_shape_scan.py:439` | `Gt` / `GtE` / `Eq` in `_len_comparison_names` | `assert len(CASES) != 0` (`NotEq` against `0`) |

Two of the five (`8893df`, `19667f`) are literally the same gap found twice, three days
apart, because the first fix enumerated one more spelling instead of enumerating the
construct. `543418` is the same failure visible *inside a single function*: one dispatch
arm guarded the unpacking case and its sibling arm did not.

## Impact

The consequence runs in both directions, which is why "the detector is conservative" is
not a defence:

- **False negative** (`227566`, `8893df`, `19667f`, `543418`) — the gate passes over
  code it exists to reject. A repo-wide sweep reports clean over a population it never
  scanned.
- **False positive** (`b1a6f6`) — the gate reds a correctly-guarded module, in a
  repository-wide gate armed at zero. That erodes trust in the gate faster than a miss.

## Solution

When authoring or extending an AST-shape detector, derive the handled case set from the
**grammar node type**, not from the examples in front of you:

1. For every `isinstance(node, X)` dispatch, enumerate `X`'s siblings and its
   variant-carrying fields (`If` has `body` **and** `orelse`; `Try` has `body`,
   `handlers`, `orelse`, `finalbody`; `With`/`AsyncWith` pair; `Dict.keys` carries
   `None` for `**`; `Compare` ops include `NotEq`/`Lt`/`LtE`).
2. When one dispatch arm guards a variant, check every sibling arm for the analogous
   variant in the same change (the `Starred`-vs-`**` divergence would have been caught
   by reading one line up).
3. Add a *negative control* per equivalent spelling — a fixture written in the
   non-canonical form that the detector must still flag. A detector with no
   negative control per spelling is asserting its own completeness.
4. When a review finds one missed spelling, fix the **enumeration**, not the instance.
   `8893df` → `19667f` is the cost of not doing this.

## Provenance

Plan `sweep-the-three-single-instance-defect-classes`, PR #1486 (merged). Findings
`227566`, `8893df`, `543418`, `19667f`, `b1a6f6` — all `pr-comment`, all
`resolution=fixed` in-run. Reviewers: coderabbitai. Remediated by TASK-010 and TASK-014.

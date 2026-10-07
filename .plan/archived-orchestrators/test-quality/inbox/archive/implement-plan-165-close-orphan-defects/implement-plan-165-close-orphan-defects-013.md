envelope_version=1
sender_type=plan
sender_id=implement-plan-165-close-orphan-defects
epic=test-quality
kind=candidate-lesson
created=2026-09-13T11:24:42Z

component=pm-dev-python:pytest-testing
category=bug

# A parametrize bound to a runtime-resolved collection passes vacuously when that collection empties

`test_configure.py` parametrized over `CLI_AUTH_TYPES`, read at line 22-24 as an
attribute off a **runtime-loaded module** rather than as a literal in the test
file. `empty_parameter_set_mark` is not overridden in `pyproject.toml`, and its
pytest default is `skip`. So if that attribute ever resolves empty — renamed,
relocated, emptied upstream — the test is SKIPPED, the suite stays green, and the
auth-type coverage the test exists to provide is gone with no signal at all.

This is the vacuous-test failure mode in its most durable form: the test is not
wrong, it simply stops running, and a skip is not a failure.

## Solution

Assert non-vacuity at the **binding site**, next to where the collection is
resolved, so the vacuous case fails loudly at collection time:

```python
CLI_AUTH_TYPES = _configure.CLI_AUTH_TYPES
assert CLI_AUTH_TYPES, "CLI_AUTH_TYPES resolved empty - parametrize would skip silently"
```

The guard belongs at the binding, not inside the test body: a body-level assert
never runs in the empty case, because there is no parameter set to run it with.

Project-wide, `empty_parameter_set_mark = fail_at_collect` in the pytest config
converts every such skip into a collection error. That is the stronger fix and the
one worth considering for the repository as a whole; the per-site guard is what
closes an individual occurrence without changing global behaviour.

## Impact

Applies to every `@pytest.mark.parametrize` whose argvalues are computed rather
than literal — resolved off an imported module, derived from a registry, filtered
from a glob, or read from config. Those are exactly the parametrizations written
to stay in sync with a source of truth, so the ones whose silent disappearance
matters most.

Surfaced by CodeRabbit on PR #1480 and fixed in-run; the same theme as this epic's
`inspect.getsource` vacuous-pin survey.

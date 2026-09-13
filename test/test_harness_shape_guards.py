#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Suite-level guards that fail when a swept test-harness defect shape reappears.

Each shape below is a way for a test to stop testing what it names while still
reporting green. Running the suite cannot catch any of them — a vacuous test
passes — which is what makes them worth a mechanical predicate rather than
review attention alone.

**R1 — a cross-slice filename pin.** A guard whose correctness depends on a path
literal naming a file another slice owns reds on an unrelated rename, and the
failure then reports a filename instead of the contract under test.

**R4 — a presence-keyed restore.** A teardown that puts state back on one arm
only leaves the mutation in place on the other, so a deleted key's absence
carries into every later test in the session.

**R5 — an unguarded runtime-derived parametrize.** An argvalues expression that
is computed rather than displayed reports its own emptiness as a skip or a
collection failure, never as the failure of the cases it was meant to produce.

Why each shape is a defect in detail, and what each predicate does and
deliberately does not report, is stated in :mod:`_test_shape_scan` beside the
predicate itself. The general, forward-looking form of the three rules lives in
the ``plan-marshall:persona-module-tester`` testing-methodology standard, which
names this module as the concrete instance.

**Why R3 has no guard here.** R3 — a hand-kept constant mirror, where a test
restates a production constant as its own literal — admits no mechanical
predicate. Whether a literal MIRRORS a production constant or legitimately PINS
an independently chosen expected value is a question about the author's intent:
the two are textually identical, so a predicate keyed on textual equality would
flag every correct expected-value assertion in the suite. R3 was swept and its
instances decided on their merits; it is held by review, not by a check.

**Every guard is matched by a negative control.** A predicate that always
returned an empty set would satisfy every whole-tree assertion here and silently
disarm the guard, so each shape is additionally fed a synthetic module carrying
it and asserted to be caught. The population each scan examined is asserted
non-zero for the same reason, and a module that failed to parse is asserted to
arrive as unmeasured coverage rather than as a clean read.
"""

from __future__ import annotations

from pathlib import Path

import _test_shape_scan as shape_scan

#: ``(label, predicate)`` for every armed shape. The label is what a failure
#: names, so it matches the shape's name in the standard and in the scan module.
_PREDICATES = (
    ('R1', shape_scan.r1_cross_slice_filename_pins),
    ('R4', shape_scan.r4_presence_keyed_restores),
    ('R5', shape_scan.r5_unguarded_runtime_parametrize),
)

# ⛔ Vacuity guard — every loop below iterates this table, so an empty one would
# make each of them pass while checking no shape at all.
assert _PREDICATES, 'no shape predicate is armed'


def _write(directory: Path, name: str, source: str) -> Path:
    """Write a synthetic module and return its path.

    The name deliberately does NOT begin with ``test_``: the predicates walk the
    real tree by that glob, and a synthetic instance of a defect must never be
    reachable from the whole-tree scans it exists to falsify.
    """
    path = directory / name
    path.write_text(source, encoding='utf-8')
    return path


# =============================================================================
# The examined population — asserted before any hit set is read
# =============================================================================


def test_every_predicate_examines_a_non_empty_population() -> None:
    """A zero-hit result from a scan that walked nothing proves nothing.

    Asserted first and separately from the hit sets below, because the two
    failures mean opposite things: an empty hit set over a real population is the
    armed state, while an empty hit set over an empty population is a scan that
    never looked.
    """
    for label, predicate in _PREDICATES:
        result = predicate()

        assert result.modules_examined > 0, (
            f'{label} examined 0 modules, so its empty hit set is unmeasured coverage rather than a clean tree'
        )


def test_no_predicate_reports_a_module_it_could_not_parse() -> None:
    """An unparseable module is a module that might carry the shape.

    It is reported as unmeasured rather than counted clean, so a tree whose
    modules stopped parsing cannot be read as a tree without defects.
    """
    for label, predicate in _PREDICATES:
        result = predicate()

        assert not result.unparseable, (
            f'{label} could not parse {len(result.unparseable)} module(s), so its hit set covers '
            f'less than the tree: {result.unparseable}'
        )


def test_an_unparseable_module_is_reported_as_unmeasured_not_as_clean(tmp_path: Path) -> None:
    """Matched negative control for the two population assertions above.

    Without it, a predicate that swallowed a parse failure would satisfy both —
    the unparseable list stays empty and the hit set stays empty — while having
    read strictly less than the tree it reports on.
    """
    broken = _write(tmp_path, 'synthetic_unparseable.py', 'def (:\n')

    for label, predicate in _PREDICATES:
        result = predicate([broken])

        assert result.unparseable == [str(broken)], f'{label} did not report the unparseable module: {result}'
        assert result.modules_examined == 0, f'{label} counted an unparseable module as examined'
        assert not result.clean, f'{label} reported a scan that read nothing as clean'


# =============================================================================
# R1 — cross-slice filename pin
# =============================================================================


def test_no_test_module_pins_another_slices_filename() -> None:
    """The armed guard: the tree carries no cross-slice path literal."""
    result = shape_scan.r1_cross_slice_filename_pins()

    assert not result.hits, (
        f'{len(result.hits)} cross-slice filename pin(s) over {result.modules_examined} module(s): {result.hits}'
    )


def test_r1_catches_a_synthetic_cross_slice_pin(tmp_path: Path) -> None:
    """Matched negative control — a predicate that never fires cannot guard.

    The pinned path is READ OFF the tree rather than written here as a literal,
    for two reasons: a literal would be an instance of the very shape this module
    guards, and it would go stale the moment the module it named was renamed —
    which is the defect, reappearing inside its own check.
    """
    walked = shape_scan.test_modules()
    assert walked, 'the test tree yielded no modules, so this control has nothing to pin'
    victim = walked[0].relative_to(shape_scan.REPO_ROOT).as_posix()

    pinning = _write(tmp_path, 'synthetic_r1.py', f'PINNED = {victim!r}\n')
    result = shape_scan.r1_cross_slice_filename_pins([pinning])

    assert len(result.hits) == 1, f'R1 did not catch a synthetic cross-slice pin on {victim}: {result}'
    assert victim in result.hits[0], f'the R1 hit does not name what was pinned: {result.hits[0]}'


# =============================================================================
# R4 — presence-keyed restore
# =============================================================================


def test_no_teardown_restores_state_on_one_arm_only() -> None:
    """The armed guard: the tree carries no leaking restore."""
    result = shape_scan.r4_presence_keyed_restores()

    assert not result.hits, (
        f'{len(result.hits)} presence-keyed restore(s) over {result.modules_examined} module(s): {result.hits}'
    )


def test_r4_catches_a_synthetic_one_armed_restore(tmp_path: Path) -> None:
    """Matched negative control for the leaking form."""
    leaking = _write(
        tmp_path,
        'synthetic_r4.py',
        'import os\n\n\ndef drive():\n'
        "    saved = os.environ.get('PM_SYNTHETIC')\n"
        "    os.environ.pop('PM_SYNTHETIC', None)\n"
        '    try:\n'
        '        run()\n'
        '    finally:\n'
        '        if saved:\n'
        "            os.environ['PM_SYNTHETIC'] = saved\n",
    )
    result = shape_scan.r4_presence_keyed_restores([leaking])

    assert len(result.hits) == 1, f'R4 did not catch a synthetic one-armed restore: {result}'


def test_r4_passes_a_synthetic_two_armed_restore(tmp_path: Path) -> None:
    """Matched POSITIVE control — the complete dichotomy is not the defect.

    Paired with the control above because the two differ by exactly the arm that
    makes one leak. A predicate keyed on the condition rather than on the missing
    arm would flag both, and the rule would then be read as forbidding a correct
    restore — which is how a guard turns into churn.
    """
    complete = _write(
        tmp_path,
        'synthetic_r4_complete.py',
        'import os\n\n\ndef drive():\n'
        "    saved = os.environ.get('PM_SYNTHETIC')\n"
        "    os.environ.pop('PM_SYNTHETIC', None)\n"
        '    try:\n'
        '        run()\n'
        '    finally:\n'
        '        if saved is None:\n'
        "            os.environ.pop('PM_SYNTHETIC', None)\n"
        '        else:\n'
        "            os.environ['PM_SYNTHETIC'] = saved\n",
    )
    result = shape_scan.r4_presence_keyed_restores([complete])

    assert not result.hits, f'R4 flagged a restore that covers both arms and leaks nothing: {result.hits}'


# =============================================================================
# R5 — unguarded runtime-derived parametrize
# =============================================================================


def test_no_runtime_derived_parametrize_is_unguarded() -> None:
    """The armed guard: every derived parameter set is asserted non-empty."""
    result = shape_scan.r5_unguarded_runtime_parametrize()

    assert not result.hits, (
        f'{len(result.hits)} unguarded runtime-derived parametrize binding(s) over '
        f'{result.modules_examined} module(s): {result.hits}'
    )


def test_r5_catches_a_synthetic_unguarded_derivation(tmp_path: Path) -> None:
    """Matched negative control for the unguarded form."""
    unguarded = _write(
        tmp_path,
        'synthetic_r5.py',
        "import pytest\n\n\n@pytest.mark.parametrize('case', derive_cases())\ndef test_case(case):\n    assert case\n",
    )
    result = shape_scan.r5_unguarded_runtime_parametrize([unguarded])

    assert len(result.hits) == 1, f'R5 did not catch a synthetic unguarded derivation: {result}'


def test_r5_passes_a_synthetic_guarded_derivation(tmp_path: Path) -> None:
    """Matched POSITIVE control — a guarded derivation is not the defect.

    Paired with the control above because the two differ by exactly the
    module-level assertion the rule asks for. Without this pairing a predicate
    that flagged every computed argvalues expression would satisfy the negative
    control while making the rule unsatisfiable.
    """
    guarded = _write(
        tmp_path,
        'synthetic_r5_guarded.py',
        'import pytest\n\n'
        'CASES = derive_cases()\n'
        "assert CASES, 'the derived case population is empty'\n\n\n"
        "@pytest.mark.parametrize('case', CASES)\n"
        'def test_case(case):\n'
        '    assert case\n',
    )
    result = shape_scan.r5_unguarded_runtime_parametrize([guarded])

    assert not result.hits, f'R5 flagged a derivation carrying a module-level non-vacuity guard: {result.hits}'

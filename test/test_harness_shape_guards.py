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
arrive as unmeasured coverage rather than as a clean read. Every armed-guard
failure reports the finding count beside the scanned and unclassifiable counts
plus the exact command that reproduces the scan, so a red run is a diagnosis,
not just a report.
"""

from __future__ import annotations

from pathlib import Path

import _test_shape_scan as shape_scan
import pytest

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


def _reproduce_command(test_name: str) -> str:
    """The exact command that replays one guard of this module, by test nodeid.

    Appended to every armed-guard failure message: a count without a reproducer is
    a report, not a diagnosis. The nodeid is passed by the caller rather than read
    off the running test, so the message states how to reproduce even when the
    failure is raised outside a pytest run.
    """
    return f'python3 -m pytest test/test_harness_shape_guards.py::{test_name} -q'


def _guard_report(noun: str, result: shape_scan.ScanResult, test_name: str) -> str:
    """The failure line an armed guard reports: findings, scanned and unclassifiable counts, reproducer.

    All four travel together because each one alone misleads: a hit count without
    the scanned population is a numerator without a denominator, a population
    without the unparseable count reads unmeasured coverage as clean, and either
    without the reproducing command leaves the reader to reconstruct the invocation.
    """
    return (
        f'{len(result.hits)} {noun} over {result.modules_examined} module(s), '
        f'{len(result.unparseable)} unparseable: {result.hits}. '
        f'Reproduce: {_reproduce_command(test_name)}'
    )


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

        assert len(result.unparseable) == 1, f'{label} did not report exactly one unparseable module: {result}'
        # Pins the module's IDENTITY rather than one of the two spellings _rel may
        # legitimately return: it reports a path under the repository root
        # relative, and any other path whole. Joining REPO_ROOT back on holds under
        # both arms, because `/` yields an absolute right-hand operand unchanged —
        # so this control stays correct whether or not pytest's basetemp (here
        # .plan/temp/pytest-basetemp/) sits inside the repository.
        assert (shape_scan.REPO_ROOT / result.unparseable[0]).resolve() == broken.resolve(), (
            f'{label} did not report the unparseable module: {result}'
        )
        assert result.modules_examined == 0, f'{label} counted an unparseable module as examined'
        assert not result.clean, f'{label} reported a scan that read nothing as clean'


# =============================================================================
# R1 — cross-slice filename pin
# =============================================================================


def test_no_test_module_pins_another_slices_filename() -> None:
    """The armed guard: the tree carries no cross-slice path literal."""
    result = shape_scan.r1_cross_slice_filename_pins()

    assert result.clean, _guard_report(
        'cross-slice filename pin(s)', result, 'test_no_test_module_pins_another_slices_filename'
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


def _two_slice_root(root: Path) -> None:
    """Lay out two sibling slices, the first carrying a module worth pinning."""
    (root / 'slice_a').mkdir()
    (root / 'slice_b').mkdir()
    (root / 'slice_a' / 'test_victim.py').write_text('VALUE = 1\n', encoding='utf-8')


def test_r1_reads_a_relative_caller_against_its_own_resolved_directory(tmp_path: Path, monkeypatch) -> None:
    """Matched pair for the directory comparison, both arms reached by a RELATIVE path.

    The candidate side is always absolute-and-resolved, so an unresolved caller
    parent can never equal it. Both arms then move together: the same-directory
    reference a slice is entitled to make would be reported, and the reported
    reason would name the wrong thing. The correct form failing is the costlier
    half, which is why it is the arm asserted first.
    """
    _two_slice_root(tmp_path)
    monkeypatch.setattr(shape_scan, 'REPO_ROOT', tmp_path)
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / 'slice_a', 'synthetic_r1_own.py', "PINNED = 'slice_a/test_victim.py'\n")
    _write(tmp_path / 'slice_b', 'synthetic_r1_cross.py', "PINNED = 'slice_a/test_victim.py'\n")

    own = shape_scan.r1_cross_slice_filename_pins([Path('slice_a/synthetic_r1_own.py')])
    cross = shape_scan.r1_cross_slice_filename_pins([Path('slice_b/synthetic_r1_cross.py')])

    assert not own.hits, f'R1 reported a slice naming a module in its own directory: {own.hits}'
    assert len(cross.hits) == 1, f'R1 missed a cross-slice pin reached by a relative path: {cross}'


def test_r1_reads_an_absolute_caller_against_its_own_resolved_directory(tmp_path: Path, monkeypatch) -> None:
    """Matched pair for the directory comparison, both arms reached by an ABSOLUTE path.

    The mirror of the relative-path pair above: the same-directory reference a slice
    is entitled to make must pass, and the cross-slice pin must fire, when the caller
    hands an absolute path. Resolving the caller parent meets the absolute-and-resolved
    candidate side on both spellings, so the exemption stays reachable however the
    caller spells its own path. R4 and R5 carry no path comparisons at all — the only
    resolved/unresolved site the sweep found is R1's own-directory check — so this
    pair and the relative one above exhaust the spellings the fix must hold over.
    """
    _two_slice_root(tmp_path)
    monkeypatch.setattr(shape_scan, 'REPO_ROOT', tmp_path)
    _write(tmp_path / 'slice_a', 'synthetic_r1_own_abs.py', "PINNED = 'slice_a/test_victim.py'\n")
    _write(tmp_path / 'slice_b', 'synthetic_r1_cross_abs.py', "PINNED = 'slice_a/test_victim.py'\n")

    own = shape_scan.r1_cross_slice_filename_pins([tmp_path / 'slice_a/synthetic_r1_own_abs.py'])
    cross = shape_scan.r1_cross_slice_filename_pins([tmp_path / 'slice_b/synthetic_r1_cross_abs.py'])

    assert not own.hits, f'R1 reported a slice naming a module in its own directory: {own.hits}'
    assert len(cross.hits) == 1, f'R1 missed a cross-slice pin reached by an absolute path: {cross}'


# =============================================================================
# R4 — presence-keyed restore
# =============================================================================


def test_no_teardown_restores_state_on_one_arm_only() -> None:
    """The armed guard: the tree carries no leaking restore."""
    result = shape_scan.r4_presence_keyed_restores()

    assert result.clean, _guard_report(
        'presence-keyed restore(s)', result, 'test_no_teardown_restores_state_on_one_arm_only'
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


def test_r4_catches_the_mirrored_one_armed_restore(tmp_path: Path) -> None:
    """Matched negative control for the leak spelled with the acting arm in the ``else``.

    It leaks exactly what the unmirrored form leaks — the absent-value branch
    does nothing, so the key the capture removed is never put back. A predicate
    that read only the ``if`` body would report one spelling and pass its mirror,
    which is a rule that depends on how the condition happens to be written.
    """
    mirrored = _write(
        tmp_path,
        'synthetic_r4_mirror.py',
        'import os\n\n\ndef drive():\n'
        "    saved = os.environ.get('PM_SYNTHETIC')\n"
        "    os.environ.pop('PM_SYNTHETIC', None)\n"
        '    try:\n'
        '        run()\n'
        '    finally:\n'
        '        if saved is None:\n'
        '            pass\n'
        '        else:\n'
        "            os.environ['PM_SYNTHETIC'] = saved\n",
    )
    result = shape_scan.r4_presence_keyed_restores([mirrored])

    assert len(result.hits) == 1, f'R4 did not catch the mirrored one-armed restore: {result}'


#: A generator fixture that protects its yield with a ``try``; ``{call}`` is the
#: single monkeypatch call its ``finally`` makes.
_FIXTURE_YIELDING_INSIDE_TRY = 'import pytest\n\n\n@pytest.fixture\ndef resource(monkeypatch):\n    try:\n        yield object()\n    finally:\n        monkeypatch.{call}\n'


def test_r4_reads_a_fixtures_finally_as_its_teardown_half(tmp_path: Path) -> None:
    """Matched pair for the yield-inside-try form: the deletion fires, the restore does not.

    The two modules differ only in the teardown call. A scan that recognised only
    a direct post-yield statement finds no teardown at all here, so BOTH pass —
    the silent half of the gap, where the shape is missed rather than misreported.
    """
    deleting = _write(
        tmp_path, 'synthetic_r4_try_delete.py', _FIXTURE_YIELDING_INSIDE_TRY.format(call="delenv('PM_SYNTHETIC')")
    )
    restoring = _write(
        tmp_path, 'synthetic_r4_try_restore.py', _FIXTURE_YIELDING_INSIDE_TRY.format(call="setenv('PM_SYNTHETIC', 'v')")
    )

    caught = shape_scan.r4_presence_keyed_restores([deleting])
    passed = shape_scan.r4_presence_keyed_restores([restoring])

    assert len(caught.hits) == 1, f'R4 missed a delenv in a fixture that yields inside a try: {caught}'
    assert not passed.hits, f'R4 flagged a monkeypatch restore in the same teardown position: {passed.hits}'


#: A generator fixture holding a context manager open across its yield, with the
#: teardown in the statements after the block; ``{call}`` is its monkeypatch call.
_FIXTURE_YIELDING_INSIDE_WITH = 'import pytest\n\n\n@pytest.fixture\ndef env(monkeypatch, tmp_path):\n    with chdir(tmp_path):\n        yield tmp_path\n    monkeypatch.{call}\n'


def test_r4_reads_the_statements_after_a_with_wrapped_yield_as_its_teardown_half(tmp_path: Path) -> None:
    """Matched pair for the with-wrapped yield: the deletion fires, the restore does not.

    The two modules differ only in the teardown call. A scan that recognised a
    bare post-yield statement and a ``try`` body but not a ``with`` one finds no
    teardown at all here, so BOTH pass — the silent half of the gap, where the
    shape is missed rather than misreported.
    """
    deleting = _write(
        tmp_path, 'synthetic_r4_with_delete.py', _FIXTURE_YIELDING_INSIDE_WITH.format(call="delenv('PM_SYNTHETIC')")
    )
    restoring = _write(
        tmp_path,
        'synthetic_r4_with_restore.py',
        _FIXTURE_YIELDING_INSIDE_WITH.format(call="setenv('PM_SYNTHETIC', 'v')"),
    )

    caught = shape_scan.r4_presence_keyed_restores([deleting])
    passed = shape_scan.r4_presence_keyed_restores([restoring])

    assert len(caught.hits) == 1, f'R4 missed a delenv after a with-wrapped yield: {caught}'
    assert not passed.hits, f'R4 flagged a monkeypatch restore in the same teardown position: {passed.hits}'


# =============================================================================
# R5 — unguarded runtime-derived parametrize
# =============================================================================


def test_no_runtime_derived_parametrize_is_unguarded() -> None:
    """The armed guard: every derived parameter set is asserted non-empty."""
    result = shape_scan.r5_unguarded_runtime_parametrize()

    assert result.clean, _guard_report(
        'unguarded runtime-derived parametrize binding(s)', result, 'test_no_runtime_derived_parametrize_is_unguarded'
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


#: A parametrize bound directly to a dict display; ``{spelling}`` is that display.
_DICT_ARGVALUES = (
    "import pytest\n\n\n@pytest.mark.parametrize('case', {spelling})\ndef test_case(case):\n    assert case\n"
)


def test_r5_reads_a_dict_of_only_unpackings_as_runtime_derived(tmp_path: Path) -> None:
    """Matched pair for the dict display: only-unpackings is derived, one explicit key is not.

    An unpacking is recorded as a ``None`` key, so a display made entirely of them
    looks populated to a bare key-count test while being exactly as empty as what
    it unpacks. The keyed arm is asserted alongside it because a predicate that
    rejected every dict would satisfy the first assertion and make the rule
    unsatisfiable for a display that plainly carries a case.
    """
    unpacked = _write(tmp_path, 'synthetic_r5_unpacked.py', _DICT_ARGVALUES.format(spelling='{**derive_cases()}'))
    keyed = _write(tmp_path, 'synthetic_r5_keyed.py', _DICT_ARGVALUES.format(spelling="{'a': 1, **derive_cases()}"))

    derived = shape_scan.r5_unguarded_runtime_parametrize([unpacked])
    displayed = shape_scan.r5_unguarded_runtime_parametrize([keyed])

    assert len(derived.hits) == 1, f'R5 read a dict of only unpackings as non-empty by construction: {derived}'
    assert not displayed.hits, f'R5 flagged a dict display carrying an explicit key: {displayed.hits}'


#: A derivation with one module-level claim beside it; ``{claim}`` is that claim.
_CLAIMED_DERIVATION = (
    'import pytest\n\nCASES = derive_cases()\nassert {claim}\n\n\n'
    "@pytest.mark.parametrize('case', CASES)\ndef test_case(case):\n    assert case\n"
)

#: ``(claim, guards)`` — module-level claims beside an IDENTICAL derivation,
#: differing only in what each one proves about the population's cardinality. The
#: rejected rows are the point: each mentions ``CASES`` and each is true of an
#: empty derivation, so accepting any of them would suppress the hit on exactly
#: the population that vanished.
_R5_CLAIMS = (
    ('CASES', True),
    ('len(CASES) > 0', True),
    ('len(CASES) >= 1', True),
    ('len(CASES) != 0', True),
    ('isinstance(CASES, list)', False),
    ('len(CASES) >= 0', False),
    ('len(CASES) != 3', False),
)


@pytest.mark.parametrize('claim,guards', _R5_CLAIMS, ids=[claim for claim, _ in _R5_CLAIMS])
def test_r5_accepts_only_a_claim_that_implies_positive_cardinality(tmp_path: Path, claim: str, guards: bool) -> None:
    """Matched controls for the shared guard predicate, positive and negative in one table."""
    module = _write(tmp_path, 'synthetic_r5_claim.py', _CLAIMED_DERIVATION.format(claim=claim))
    result = shape_scan.r5_unguarded_runtime_parametrize([module])

    if guards:
        assert not result.hits, f'R5 flagged a derivation guarded by `assert {claim}`: {result.hits}'
    else:
        assert len(result.hits) == 1, f'R5 read `assert {claim}` as a guard, though an empty derivation satisfies it'


#: A parametrize bound to a helper that asserts its input before returning;
#: ``{returned}`` is the expression the helper returns.
_HELPER_GUARDED_DERIVATION = (
    'import pytest\n\n\ndef derive_cases():\n'
    '    candidates = discover_cases()\n'
    '    assert candidates\n'
    '    return {returned}\n\n\n'
    "@pytest.mark.parametrize('case', derive_cases())\ndef test_case(case):\n    assert case\n"
)


def test_r5_credits_a_helper_guard_only_for_the_population_it_returns(tmp_path: Path) -> None:
    """Matched pair for the helper guard: the returned result counts, a narrowed one does not.

    The two modules differ only in the returned expression, and ``assert
    candidates`` proves the INPUT non-empty in both. That says nothing about a
    filtered view of it — every candidate can be excluded and the
    parametrization still receives no case — so crediting the assertion merely
    because the name it uses reappears in the return expression is the vacuous
    pass this shape exists to report. The unfiltered arm is asserted alongside
    it because a predicate that credited no helper at all would satisfy the
    first assertion while making the rule unsatisfiable.
    """
    direct = _write(tmp_path, 'synthetic_r5_direct.py', _HELPER_GUARDED_DERIVATION.format(returned='candidates'))
    filtered = _write(
        tmp_path,
        'synthetic_r5_filtered.py',
        _HELPER_GUARDED_DERIVATION.format(returned='[case for case in candidates if case.enabled]'),
    )

    guarded = shape_scan.r5_unguarded_runtime_parametrize([direct])
    vacuous = shape_scan.r5_unguarded_runtime_parametrize([filtered])

    assert not guarded.hits, f'R5 flagged a helper asserting the very result it returns: {guarded.hits}'
    assert len(vacuous.hits) == 1, f'R5 credited an assertion about the input of a narrowing helper: {vacuous}'

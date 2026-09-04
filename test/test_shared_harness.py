# SPDX-License-Identifier: FSL-1.1-ALv2
"""Meta-tests protecting the shared test harness in ``test/conftest.py``.

The harness is consumed by every bundle's tests at once, so a regression in it
is a regression everywhere. Four properties are pinned here:

1. :func:`conftest.parse_ns` applies parser defaults the caller did not name —
   the whole reason it exists instead of a hand-built ``argparse.Namespace``.
2. :func:`conftest.parse_ns` raises its named error for a script with no
   reachable parser seam, rather than degrading to a namespace it invented.
3. :func:`conftest.create_marshal_json`'s named presets produce genuinely
   distinct baselines, so collapsing three builders into one did not average
   two different fixtures into a third that serves neither.
4. No module under ``test/`` matches pytest's collection pattern while declaring
   zero tests. Such a module is imported by pytest, collects nothing, and is
   invisible in the run.

The whole-tree guard follows ``test/marketplace/test_prefix_strip_idiom_retired.py``:
the scan returns its population alongside its offender list, and the assertion
checks the population is non-empty BEFORE checking the offender list is empty, so
a mis-rooted walk cannot pass vacuously. Positive controls prove the detector
fires; negative controls prove it does not over-fire.
"""

import argparse
import ast
from pathlib import Path

import pytest

from conftest import (
    MARSHAL_PRESET_JAVA,
    MARSHAL_PRESET_MINIMAL,
    MARSHAL_PRESETS,
    ParserSeamNotFound,
    create_marshal_json,
    parse_ns,
)

TEST_ROOT = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# 1. parse_ns applies the parser's defaults
# ---------------------------------------------------------------------------

#: A real script with a rich defaulted flag set, reached through the
#: main()-interception seam. Coupling the test to a real script is deliberate:
#: the property under test is that the PRODUCTION parser's defaults arrive, which
#: a synthetic parser could not demonstrate.
_DEFAULTS_CASE = ('plan-marshall', 'manage-findings', 'manage-findings.py')
_DEFAULTS_ARGV = ('list', '--plan-id', 'p1')

#: Flags the caller above does NOT name, which the real parser defaults anyway.
_UNNAMED_DEFAULTS = ('type', 'resolution', 'promoted', 'file_pattern', 'author', 'kind', 'bot_kind')


def test_parse_ns_applies_defaults_the_caller_did_not_name():
    """The namespace carries parser defaults for flags the caller never passed."""
    ns = parse_ns(*_DEFAULTS_CASE, *_DEFAULTS_ARGV)

    assert ns.command == 'list'
    assert ns.plan_id == 'p1'
    # A store_true flag defaults to a real value, not to absence.
    assert ns.include_qgate is False
    missing = [name for name in _UNNAMED_DEFAULTS if not hasattr(ns, name)]
    assert missing == [], f'parse_ns dropped parser defaults the CLI would apply: {missing}'


def test_hand_built_namespace_lacks_the_defaults_parse_ns_supplies():
    """The defect parse_ns closes, stated as a test.

    A hand-built namespace carries only what its author remembered. This is the
    control that makes the test above meaningful: without it, a `parse_ns` that
    happened to return a namespace with every attribute set would look identical
    to one that returned a hand-built guess.
    """
    hand_built = argparse.Namespace(command='list', plan_id='p1')

    assert not hasattr(hand_built, 'include_qgate')
    assert [name for name in _UNNAMED_DEFAULTS if not hasattr(hand_built, name)] == list(_UNNAMED_DEFAULTS)


# ---------------------------------------------------------------------------
# 2. parse_ns raises its named error when no seam is reachable
# ---------------------------------------------------------------------------

#: A real module that constructs an ``ArgumentParser`` but publishes no builder
#: and has no ``main()`` — a library module, not a CLI entry point.
_NO_SEAM_CASE = ('plan-marshall', 'tools-integration-ci', 'ci_base.py')

# ⛔ Both no-seam cases below pass ``register=False``, and it is load-bearing rather
# than tidiness. ``parse_ns`` loads the script to reach its parser, and its default
# publishes what it loaded in ``sys.modules`` under the file's stem — REPLACING the
# entry. ``ci_base`` and ``platform_runtime`` are both imported plainly elsewhere in
# this suite, so registering a second copy leaves those modules holding an object no
# longer reachable by name: a ``mock.patch('platform_runtime.X')`` then patches the
# copy published here while the function under test keeps reading its own
# ``__globals__``, and ``ci_base.get_default_cwd()`` reads a ``_DEFAULT_CWD`` that
# the ``set_default_cwd`` the production code called never wrote to. Neither patch
# fails — they silently do nothing, and which copy wins is decided by run order.
# Only the namespace is wanted here, which is exactly the case ``register=False``
# exists for; see ``conftest.parse_ns`` and the collision guard in
# ``test/plan-marshall/script-shared/test_conftest_loader_contract.py``.


def test_parse_ns_raises_named_error_for_a_script_with_no_parser_seam():
    """A script with no reachable seam raises, rather than degrading."""
    with pytest.raises(ParserSeamNotFound, match='no parser seam'):
        parse_ns(*_NO_SEAM_CASE, 'anything', register=False)


def test_a_router_script_fails_loudly_rather_than_yielding_a_guess():
    """A script that dispatches before parsing raises, instead of a partial namespace.

    ``platform_runtime``'s ``main()`` resolves an operation and dispatches BEFORE it
    reaches any ``parse_args``, so the interception seam has nothing to capture.
    The contract is that this fails loudly and steers the caller to the published
    builder — never that it returns a namespace assembled from whatever was
    reachable. This pins the limitation the ``parse_ns`` docstring states, so the
    documented caveat is checked rather than merely asserted.
    """
    with pytest.raises(ParserSeamNotFound):
        parse_ns(
            'plan-marshall',
            'platform-runtime',
            'platform_runtime.py',
            'statusline',
            'render',
            register=False,
        )


def test_invalid_argv_is_not_reported_as_a_missing_seam():
    """A rejected command line raises SystemExit, not ParserSeamNotFound.

    The two are different defects — a broken test versus an unreachable script —
    and conflating them sends the reader to the wrong place. Both seams fail this
    way, so the error does not depend on which seam the script exposes.
    """
    with pytest.raises(SystemExit):
        parse_ns('plan-marshall', 'manage-findings', 'manage-findings.py', 'no-such-verb')


# ---------------------------------------------------------------------------
# 3. The marshal presets stay distinct
# ---------------------------------------------------------------------------


def test_marshal_presets_are_not_averaged_into_one(tmp_path):
    """The two named baselines produce different configs, each with its own shape."""
    import json

    minimal = json.loads(create_marshal_json(tmp_path / 'a', preset=MARSHAL_PRESET_MINIMAL).read_text())
    java = json.loads(create_marshal_json(tmp_path / 'b', preset=MARSHAL_PRESET_JAVA).read_text())

    assert minimal != java

    # The minimal baseline carries no language domain and no providers.
    assert set(minimal['skill_domains']) == {'system'}
    assert 'providers' not in minimal

    # The java baseline carries its domains, its branch-cleanup params and a provider.
    assert 'java' in java['skill_domains']
    assert java['plan']['phase-6-finalize']['steps']['default:branch-cleanup']['pr_merge_strategy'] == 'squash'
    assert java['providers'][0]['provider'] == 'github'


def test_every_registered_preset_is_reachable_by_name(tmp_path):
    """Each name in the preset table builds; the table is the contract."""
    import json

    assert set(MARSHAL_PRESETS) == {MARSHAL_PRESET_MINIMAL, MARSHAL_PRESET_JAVA}
    for name in MARSHAL_PRESETS:
        written = json.loads(create_marshal_json(tmp_path / name, preset=name).read_text())
        assert written == MARSHAL_PRESETS[name]


def test_building_a_fixture_leaves_the_shared_baseline_untouched(tmp_path):
    """Building fixtures does not rewrite the module-level baseline.

    Scope, stated honestly: the builder applies ``skill_domains`` and ``extra``
    at the TOP level only, so today no code path reaches a nested object and this
    assertion cannot fail. It is a pin, not a detector — it fixes the invariant
    now, so that an override path which later merges nested keys has to keep it.
    The builder deep-copies its baseline for the same forward-looking reason.
    """
    import copy
    import json

    before = copy.deepcopy(MARSHAL_PRESETS[MARSHAL_PRESET_MINIMAL])

    create_marshal_json(tmp_path / 'one', preset=MARSHAL_PRESET_MINIMAL, skill_domains={'replaced': {}})
    create_marshal_json(tmp_path / 'two', preset=MARSHAL_PRESET_MINIMAL, extra={'added': 1})

    assert MARSHAL_PRESETS[MARSHAL_PRESET_MINIMAL] == before

    # And a later build still reproduces the pristine baseline.
    third = json.loads(create_marshal_json(tmp_path / 'three', preset=MARSHAL_PRESET_MINIMAL).read_text())
    assert third == before


def test_full_config_form_is_written_verbatim(tmp_path):
    """The full-config form writes what it was given, ignoring every baseline."""
    import json

    written = create_marshal_json(tmp_path, {'skill_domains': {}, 'marker': 'verbatim'})
    assert json.loads(written.read_text()) == {'skill_domains': {}, 'marker': 'verbatim'}


def test_the_two_call_forms_may_not_be_combined(tmp_path):
    """Passing both forms is refused rather than silently resolved one way."""
    with pytest.raises(ValueError, match='not both'):
        create_marshal_json(tmp_path, {'skill_domains': {}}, extra={'x': 1})


def test_an_unknown_preset_is_refused(tmp_path):
    """A misspelled preset name fails loudly instead of falling back to a default."""
    with pytest.raises(ValueError, match='unknown preset'):
        create_marshal_json(tmp_path, preset='no-such-preset')


def test_the_destination_is_explicit(tmp_path):
    """Nesting under .plan/ is a stated argument, not an inherited surprise."""
    nested = create_marshal_json(tmp_path / 'n', preset=MARSHAL_PRESET_MINIMAL, nest_in_plan_dir=True)
    flat = create_marshal_json(tmp_path / 'f', preset=MARSHAL_PRESET_MINIMAL, nest_in_plan_dir=False)

    assert nested.parent.name == '.plan'
    assert flat.parent.name == 'f'


def test_the_project_data_companion_is_opt_in(tmp_path):
    """raw-project-data.json is written only when asked for."""
    with_data = create_marshal_json(tmp_path / 'w', preset=MARSHAL_PRESET_JAVA, with_project_data=True)
    without = create_marshal_json(tmp_path / 'o', preset=MARSHAL_PRESET_JAVA)

    assert (with_data.parent / 'raw-project-data.json').is_file()
    assert not (without.parent / 'raw-project-data.json').exists()


# ---------------------------------------------------------------------------
# 4. Whole-tree guard: no collected module declares zero tests
# ---------------------------------------------------------------------------

#: Directory names that never hold collectable test source. ``fixtures`` is in
#: ``norecursedirs`` (pyproject), so pytest never collects under it — a scan that
#: walked it would report a testless module pytest does not import.
EXCLUDED_DIR_NAMES = frozenset(
    {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'fixtures'}
)


def _is_collected_name(name: str) -> bool:
    """Whether a basename matches a pytest collection pattern.

    Deliberately a SUPERSET of this project's ``python_files`` setting, which is
    ``test_*.py`` alone: D3's done-when names both spellings, and a ``*_test.py``
    helper would be an offender the moment the setting widened. Over-collecting
    here only ever guards more.
    """
    return name.startswith('test_') or name.endswith('_test.py')


def _declares_a_test(tree: ast.Module) -> bool:
    """Whether a parsed module declares any test function or ``Test*`` class."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith('test'):
            return True
        if isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
            return True
    return False


def scan_for_testless_collected_modules(root: Path) -> tuple[list[str], int]:
    """Find modules pytest collects that declare no test.

    Read and parse failures are deliberately NOT swallowed: a file that cannot be
    read is a file that might be an offender and was never checked, which is a
    coverage gap rather than a clean result.

    Args:
        root: Directory to walk. A non-existent directory yields an empty
            population, which the caller's population assertion then catches.

    Returns:
        ``(offenders, scanned)`` — ``scanned`` is how many collected modules were
        parsed, returned alongside the list precisely so a caller can prove the
        scan had something to examine.
    """
    offenders: list[str] = []
    scanned = 0
    if not root.is_dir():
        return offenders, scanned

    for path in sorted(root.rglob('*.py')):
        if EXCLUDED_DIR_NAMES.intersection(path.parts):
            continue
        if not _is_collected_name(path.name):
            continue
        scanned += 1
        if not _declares_a_test(ast.parse(path.read_text(encoding='utf-8'))):
            offenders.append(str(path))

    return offenders, scanned


def test_no_collected_module_under_test_declares_zero_tests():
    """Every module pytest collects under ``test/`` declares at least one test."""
    offenders, scanned = scan_for_testless_collected_modules(TEST_ROOT)

    # Population first: an empty offender list is only meaningful once the walk
    # is known to have read something.
    assert scanned > 0, (
        f'Scanned 0 collected modules under {TEST_ROOT} — the guard examined '
        'nothing, so its clean result is vacuous. Check TEST_ROOT resolution.'
    )
    assert offenders == [], (
        f'{len(offenders)} module(s) of {scanned} match pytest\'s collection '
        'pattern while declaring no test. pytest imports them and collects '
        'nothing, so they are invisible in the run. Rename each to '
        f'_{{domain}}_fixtures.py per test/README.md: {offenders}'
    )


def test_scanned_population_covers_the_real_test_tree():
    """The population is large enough to be the real tree, not a stray directory."""
    _offenders, scanned = scan_for_testless_collected_modules(TEST_ROOT)

    assert scanned > 100, f'Only {scanned} collected modules scanned — too few to be the test tree'


def test_detector_fires_on_a_testless_test_prefixed_module(tmp_path):
    """Positive control: ``test_*.py`` with only helpers is reported."""
    offender = tmp_path / 'test_helpers.py'
    offender.write_text('def create_thing():\n    return 1\n', encoding='utf-8')

    offenders, scanned = scan_for_testless_collected_modules(tmp_path)

    assert scanned == 1
    assert offenders == [str(offender)]


def test_detector_fires_on_the_suffix_spelling(tmp_path):
    """Positive control: ``*_test.py`` is collected too, so it is guarded too."""
    offender = tmp_path / 'thing_test.py'
    offender.write_text('VALUE = 1\n', encoding='utf-8')

    offenders, scanned = scan_for_testless_collected_modules(tmp_path)

    assert scanned == 1
    assert offenders == [str(offender)]


def test_detector_accepts_a_module_that_declares_tests(tmp_path):
    """Negative control: a real test module is not flagged.

    Without this, a detector that flagged every collected module would satisfy
    both positive controls while failing the whole tree.
    """
    real = tmp_path / 'test_real.py'
    real.write_text('def test_something():\n    assert True\n', encoding='utf-8')

    offenders, scanned = scan_for_testless_collected_modules(tmp_path)

    assert scanned == 1
    assert offenders == []


def test_detector_accepts_a_test_class(tmp_path):
    """Negative control: a ``Test*`` class counts as declaring tests."""
    real = tmp_path / 'test_classy.py'
    real.write_text('class TestThing:\n    def test_it(self):\n        assert True\n', encoding='utf-8')

    offenders, scanned = scan_for_testless_collected_modules(tmp_path)

    assert offenders == []


def test_a_fixtures_module_is_not_collected_and_not_flagged(tmp_path):
    """Negative control: the supported helper name is outside the population.

    This is the shape the guard steers offenders toward, so flagging it would
    make the remedy fail the check.
    """
    helper = tmp_path / '_domain_fixtures.py'
    helper.write_text('def create_thing():\n    return 1\n', encoding='utf-8')

    offenders, scanned = scan_for_testless_collected_modules(tmp_path)

    assert scanned == 0
    assert offenders == []


def test_scan_reports_zero_population_for_a_missing_root(tmp_path):
    """A mis-rooted walk reports 0, never a false clean pass.

    This is what makes the population assertion in the whole-tree test load
    bearing.
    """
    offenders, scanned = scan_for_testless_collected_modules(tmp_path / 'does-not-exist')

    assert offenders == []
    assert scanned == 0

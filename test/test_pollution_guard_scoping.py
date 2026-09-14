# SPDX-License-Identifier: FSL-1.1-ALv2
"""Meta-test: collection derives ``touches_real_state`` over the whole state-driving set.

``_pollution_guard`` only takes its before/after real-path snapshot for tests
carrying ``touches_real_state``, so whatever that marker misses, the backstop does
not check. The marker used to be applied on ONE signal — the test requests the
``plan_context`` fixture — which left every module that drives plan state through
``PlanContext`` / ``EmptyPlanContext`` / ``BuildContext``, or by setting
``PLAN_BASE_DIR`` itself, unmarked. Those are precisely the modules whose redirect
the backstop exists to verify, so the scoping skipped the tests it was for while
still reporting a scoped guard.

This module pins the derivation both ways. The signals are driven individually
against synthetic sources, so each one is shown to mark ON ITS OWN rather than
riding on a sibling; the matched negative controls pin that a pure-logic module and
a module that merely READS ``PLAN_BASE_DIR`` stay unmarked, without which a
predicate that marked everything would satisfy every positive assertion here and
silently undo the scoping. Every population here is derived by walking the tree
rather than from a list, and publishes its counts, so none can pass over an empty
or near-empty set.

The real-module coverage names a ROLE, never a filename. It sweeps whatever the
tree derives as state-driving and separately asserts that the ``PLAN_BASE_DIR``-
setting route — the half a fixture-name-only predicate missed — is populated. The
retired form instead named five modules by path, one per slice, so an unrelated
slice renaming its own test file failed this module with "named module has moved":
a report about a filename rather than about the marking contract under test.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pytest

import conftest
from conftest import TEST_ROOT


@lru_cache(maxsize=1)
def _walked_test_modules() -> tuple[Path, ...]:
    """Every collectable test module in the tree, walked rather than listed.

    The walk is what lets the real-module coverage below name a ROLE instead of a
    filename. The retired form pinned five modules by path, each owned by a
    different slice, so an unrelated slice renaming its own test file failed THIS
    module with "named module has moved" — a report about a filename, not about the
    marking contract the module exists to check.

    Cached: the three callers below would otherwise walk the same tree three times
    per session for an answer that cannot change within a run.
    """
    return tuple(sorted(p for p in TEST_ROOT.rglob('test_*.py') if '__pycache__' not in p.parts))


def _state_driving(modules: tuple[Path, ...]) -> list[Path]:
    """The subset that collection derives as driving real plan state."""
    return [p for p in modules if conftest._module_drives_real_state(p)]


def _sets_plan_base_dir(module_path: Path) -> bool:
    """Whether a module's SOURCE sets ``PLAN_BASE_DIR`` itself.

    One half of :func:`conftest._module_drives_real_state`'s disjunction, read on
    its own so that route can be asserted POPULATED rather than merely folded into
    the union. The five modules the retired list named were all of this shape, and
    they were exactly the ones the fixture-only predicate left unmarked.

    An unreadable path answers ``False``, matching the predicate it mirrors.
    """
    try:
        source = module_path.read_text(encoding='utf-8')
    except OSError:
        return False
    return bool(conftest._PLAN_BASE_DIR_SET_RE.search(source))


#: One synthetic source per signal, each carrying that signal and nothing else.
_SOURCE_SIGNALS = {
    'plan_context_manager': 'def test_x():\n    with PlanContext("p") as ctx:\n        assert ctx\n',
    'empty_plan_context': 'def test_x():\n    with EmptyPlanContext() as ctx:\n        assert ctx\n',
    'build_context': 'def test_x():\n    with BuildContext() as ctx:\n        assert ctx\n',
    'setenv': "def test_x(monkeypatch):\n    monkeypatch.setenv('PLAN_BASE_DIR', '/tmp/x')\n",
    'setattr': "def test_x(monkeypatch):\n    monkeypatch.setattr(mod, 'PLAN_BASE_DIR', '/tmp/x')\n",
    'os_environ_assignment': "def test_x():\n    os.environ['PLAN_BASE_DIR'] = '/tmp/x'\n",
    'module_attribute_assignment': "PLAN_BASE_DIR = '/tmp/x'\n",
}


class _StubItem:
    """The slice of a collected item that ``pytest_collection_modifyitems`` reads."""

    def __init__(self, path: Path, fixturenames: tuple[str, ...] = ()) -> None:
        self.path = path
        self.fixturenames = fixturenames
        self.nodeid = f'{path}::test_x'
        self.markers: list[str] = []

    def add_marker(self, marker: str) -> None:
        self.markers.append(marker)

    def get_closest_marker(self, name: str) -> str | None:
        return name if name in self.markers else None


def _marked(item: _StubItem) -> bool:
    """Run collection over ``item`` alone and report whether it came back marked."""
    conftest.pytest_collection_modifyitems([item])
    return 'touches_real_state' in item.markers


def _synthetic_module(tmp_path: Path, source: str, name: str = 'test_synthetic.py') -> Path:
    """Write ``source`` to a uniquely-named file so the per-path memo cannot alias it."""
    module = tmp_path / name
    module.write_text(source, encoding='utf-8')
    return module


def test_every_state_driving_module_yields_marked_items():
    """Every module the tree derives as state-driving comes back MARKED.

    The role-expressed successor to the five modules this used to name by path. The
    population is whatever the tree's state-driving modules ARE, so no rename in any
    slice can make this module report a missing FILE in place of a marking failure —
    and the sweep covers strictly more than the five filenames ever did.

    Driven through ``pytest_collection_modifyitems`` rather than through the
    predicate directly, so what is asserted is the marking the backstop actually
    receives: the hook reads ``item.path`` and consults the per-path memo, and a
    change to either would leave the predicate right while the collection went
    wrong. Every unmarked member is reported in one message, because a predicate
    regression takes the whole population down at once and the useful report is the
    set, not the first element of it.
    """
    driving = _state_driving(_walked_test_modules())

    assert driving, (
        'no test module derives as state-driving, so this sweep asserts nothing; '
        'test_the_derived_population_is_neither_empty_nor_the_whole_tree owns the '
        'population floor this leans on'
    )

    unmarked = [p.relative_to(TEST_ROOT).as_posix() for p in driving if not _marked(_StubItem(p))]

    assert not unmarked, (
        f'{len(unmarked)} of {len(driving)} state-driving module(s) came back unmarked, so '
        f'_pollution_guard skips the very tests whose redirect it exists to verify: {unmarked}'
    )


def test_the_plan_base_dir_setting_route_is_populated_and_marks():
    """The regression target, by ROLE: the modules that SET ``PLAN_BASE_DIR``.

    ``_module_drives_real_state`` is a disjunction, so the sweep above stays green
    even if the env/attribute route matches nothing at all and every derived member
    arrives via the ``PlanContext`` symbol route instead. That route is the one the
    fixture-only predicate missed, and it is what the five retired filenames stood
    for, so its population is asserted non-empty in its own right — the sub-population
    anti-vacuity the sweep cannot supply for itself.
    """
    setters = [p for p in _walked_test_modules() if _sets_plan_base_dir(p)]

    assert setters, (
        'no test module sets PLAN_BASE_DIR itself, so the env/attribute half of '
        '_module_drives_real_state matches nothing and the sweep above rests entirely '
        'on the PlanContext symbol route'
    )

    unmarked = [p.relative_to(TEST_ROOT).as_posix() for p in setters if not _marked(_StubItem(p))]

    assert not unmarked, (
        f'{len(unmarked)} of {len(setters)} module(s) that set PLAN_BASE_DIR were left '
        f'unmarked by collection: {unmarked}'
    )


@pytest.mark.parametrize('signal', sorted(_SOURCE_SIGNALS), ids=sorted(_SOURCE_SIGNALS))
def test_each_source_signal_marks_on_its_own(tmp_path: Path, signal: str):
    """One signal per module: none of them depends on a sibling being present too."""
    module = _synthetic_module(tmp_path, _SOURCE_SIGNALS[signal], f'test_{signal}.py')

    assert _marked(_StubItem(module)), f'the {signal} signal did not mark on its own'


def test_a_plan_context_requester_is_marked_even_when_its_module_is_silent(tmp_path: Path):
    """The fixture signal survives the broadening — it is added to, not replaced."""
    module = _synthetic_module(tmp_path, 'def test_x(plan_context):\n    assert True\n', 'test_silent.py')

    assert _marked(_StubItem(module, fixturenames=('plan_context', 'tmp_path')))


def test_a_pure_logic_module_is_not_marked(tmp_path: Path):
    """Matched negative control: without it, marking EVERY test passes every case above.

    A predicate that always returned True would satisfy each positive assertion here
    while restoring the whole-suite snapshot cost the scoping removed — and would do
    so silently, because an over-marked run is green.
    """
    module = _synthetic_module(tmp_path, 'def test_x():\n    assert 1 + 1 == 2\n', 'test_pure.py')

    assert not _marked(_StubItem(module))


def test_a_module_that_only_reads_plan_base_dir_is_not_marked(tmp_path: Path):
    """Reading the variable is being a passenger of the sandbox; setting it is not.

    The distinction is the whole reason the predicate matches assignment shapes
    rather than the bare name: a substring match on ``PLAN_BASE_DIR`` would mark the
    ~160 modules that merely read it and collapse the scoping back to whole-suite.
    """
    module = _synthetic_module(
        tmp_path,
        "def test_x():\n    assert os.environ['PLAN_BASE_DIR']\n",
        'test_reader.py',
    )

    assert not _marked(_StubItem(module))


def test_the_derived_population_is_neither_empty_nor_the_whole_tree():
    """Anti-vacuity in both directions, over the walked population with its counts.

    An empty derived set would make every positive case above a statement about
    synthetic files only; a set equal to the whole tree would mean the scoping buys
    nothing. Both counts are published so a future shift is readable from the
    failure rather than needing a re-derivation.
    """
    modules = _walked_test_modules()
    driving = _state_driving(modules)

    assert len(modules) >= 100, f'walked only {len(modules)} test modules — the population is not the tree'
    assert 20 <= len(driving) < len(modules), (
        f'{len(driving)} of {len(modules)} test modules derive as state-driving; expected a '
        'substantial minority — an empty set makes the guard unscoped-by-omission, and the '
        'whole tree makes the scoping a no-op'
    )

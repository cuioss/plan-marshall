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
silently undo the scoping. The population check is derived by walking the tree
rather than from a list, and publishes its counts, so it cannot pass over an empty
or near-empty set.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import conftest
from conftest import TEST_ROOT

#: The named modules that set ``PLAN_BASE_DIR`` themselves, re-derived by sweep.
#: They are the concrete regression targets: each drives the resolver directly and
#: none of them requests ``plan_context``, so under the fixture-only predicate every
#: one of them went unmarked.
_NAMED_STATE_DRIVING_MODULES = (
    'plan-marshall/manage-logging/test_logging.py',
    'plan-marshall/manage-providers/test_list_providers.py',
    'plan-marshall/build-maven/test_maven_run.py',
    'plan-marshall/build-npm/test_npm_run.py',
    'plan-marshall/script-shared/test_build_parse.py',
)

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


@pytest.mark.parametrize('relative_path', _NAMED_STATE_DRIVING_MODULES)
def test_a_named_state_driving_module_yields_marked_items(relative_path: str):
    """Each named module's tests are marked, so the backstop actually checks them.

    Driven against the REAL file rather than a copy of its idiom: the point is that
    these specific modules — the ones the ownership migration touched — are covered,
    and a synthetic stand-in would pass even if the real file drifted away from the
    shape the predicate recognises.
    """
    module_path = TEST_ROOT / relative_path
    assert module_path.is_file(), f'named module has moved or been renamed: {module_path}'

    assert _marked(_StubItem(module_path)), (
        f'{relative_path} sets PLAN_BASE_DIR but collection left its items unmarked, '
        'so _pollution_guard skips the very tests whose redirect it exists to verify'
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
    modules = sorted(p for p in TEST_ROOT.rglob('test_*.py') if '__pycache__' not in p.parts)
    driving = [p for p in modules if conftest._module_drives_real_state(p)]

    assert len(modules) >= 100, f'walked only {len(modules)} test modules — the population is not the tree'
    assert 20 <= len(driving) < len(modules), (
        f'{len(driving)} of {len(modules)} test modules derive as state-driving; expected a '
        'substantial minority — an empty set makes the guard unscoped-by-omission, and the '
        'whole tree makes the scoping a no-op'
    )

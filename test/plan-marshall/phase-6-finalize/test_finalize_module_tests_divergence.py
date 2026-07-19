#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavioral fixture — the scoped-green / whole-tree-red divergence is CAUGHT.

Drives the D1 seam (``_test_scope_divergence.resolve_test_scope`` +
``classify_divergence``) through a model of the phase-6-finalize
whole-tree module-tests divergence gate (``pre-push-quality-gate.md``), with an
INJECTED build runner rather than a real build. Proves the load-bearing PLAN-14
acceptance: a change that a scoped run would pass but a whole-tree run fails is
routed to the whole-tree target and classified ``caught=True``.

The gate's routing prose (D2) is modelled once by ``_gate_route`` below; the
decision logic itself lives in the pure D1 seam, so this test exercises the real
seam behavior end-to-end without spawning pytest.
"""

import importlib.util
from pathlib import Path

import pytest

_MODULE_PATH = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'script-shared'
    / 'scripts'
    / 'build'
    / '_test_scope_divergence.py'
)


def _load(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_mod = _load('_test_scope_divergence', _MODULE_PATH)
resolve_test_scope = _mod.resolve_test_scope
classify_divergence = _mod.classify_divergence

# The real Python build_map globs (single-``*`` fnmatch spans ``/``).
_GLOBS = ['marketplace/bundles/*.py', 'test/*.py', 'pyproject.toml']

# A footprint the D1 seam classifies divergence_possible=True: it touches the
# shared build layer, exactly the PLAN-08 cross-module regression class.
_DIVERGENT_FOOTPRINT = [
    'marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_x.py',
]
# A footprint spanning two distinct modules — also divergence_possible=True.
_MULTI_MODULE_FOOTPRINT = [
    'marketplace/bundles/plan-marshall/skills/foo/scripts/a.py',
    'marketplace/bundles/pm-dev-python/skills/bar/scripts/b.py',
]
# A single isolated module, no shared infra — divergence_possible=False.
_ISOLATED_FOOTPRINT = [
    'marketplace/bundles/pm-dev-python/skills/bar/scripts/b.py',
]


def _gate_route(resolution, whole_tree_available: bool):
    """Model the D2 divergence-gate routing over a D1 resolution.

    Returns ``(route, target)`` where ``route`` is one of ``'whole_tree'`` /
    ``'scoped'`` / ``'warn'`` and ``target`` is the module arg a scoped run
    would carry (``None`` for the whole-tree, no-module-arg route). Mirrors the
    branch order in ``pre-push-quality-gate.md`` § "Whole-tree module-tests
    divergence gate".
    """
    if not whole_tree_available:
        return 'warn', None
    if resolution.divergence_possible:
        return 'whole_tree', None
    return 'scoped', resolution.recommended_target


class _InjectedRunner:
    """A build runner returning scripted outcomes per target — no real build.

    ``None`` keys the whole-tree (no-module-arg) run; a module name keys a
    scoped run.
    """

    def __init__(self, outcomes: dict[str | None, str]):
        self._outcomes = outcomes
        self.calls: list[str | None] = []

    def run(self, target: str | None) -> str:
        self.calls.append(target)
        return self._outcomes[target]


@pytest.mark.parametrize(
    'footprint',
    [
        pytest.param(_DIVERGENT_FOOTPRINT, id='shared_build_infra'),
        pytest.param(_MULTI_MODULE_FOOTPRINT, id='multi_module'),
    ],
)
def test_scoped_green_whole_tree_red_is_caught(footprint):
    """A divergent footprint routes to whole-tree and CATCHES the regression."""
    # Arrange: the scoped target(s) are green, the whole-tree run is red.
    resolution = resolve_test_scope(footprint, _GLOBS)
    runner = _InjectedRunner({None: 'error', resolution.recommended_target: 'success'})

    # Act: the gate routes on divergence risk, then the seam classifies the pair.
    route, target = _gate_route(resolution, whole_tree_available=True)
    scoped_outcome = 'success'  # what a scoped run would have reported
    whole_tree_outcome = runner.run(target)
    verdict = classify_divergence(scoped_outcome, whole_tree_outcome)

    # Assert: routed to whole-tree (no module arg) and the divergence is caught.
    assert resolution.divergence_possible is True
    assert route == 'whole_tree'
    assert target is None
    assert runner.calls == [None]
    assert verdict.divergent is True
    assert verdict.caught is True


def test_isolated_module_stays_scoped_and_both_green_not_divergent():
    """A single isolated module runs scoped (no whole-tree cost) and is not divergent."""
    # Arrange
    resolution = resolve_test_scope(_ISOLATED_FOOTPRINT, _GLOBS)
    runner = _InjectedRunner({'pm-dev-python': 'success'})

    # Act
    route, target = _gate_route(resolution, whole_tree_available=True)
    scoped_outcome = runner.run(target)
    verdict = classify_divergence(scoped_outcome, whole_tree_outcome='success')

    # Assert: scoped route to the single module, no whole-tree run, not divergent.
    assert resolution.divergence_possible is False
    assert route == 'scoped'
    assert target == 'pm-dev-python'
    assert runner.calls == ['pm-dev-python']
    assert verdict.divergent is False
    assert verdict.caught is False


def test_whole_tree_unavailable_routes_to_warn():
    """When no pytest module set is discoverable the gate degrades to a WARNING."""
    # Arrange: a divergent footprint, but whole-tree module-tests is unavailable.
    resolution = resolve_test_scope(_DIVERGENT_FOOTPRINT, _GLOBS)

    # Act
    route, target = _gate_route(resolution, whole_tree_available=False)

    # Assert: honest degradation — warn, never a silent whole-tree skip masquerading as green.
    assert resolution.divergence_possible is True
    assert route == 'warn'
    assert target is None

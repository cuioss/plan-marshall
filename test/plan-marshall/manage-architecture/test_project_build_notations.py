#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the project's resolved build-notation set and its classifier.

``resolve_project_build_notations`` is the COMPARISON TARGET the pre-commit
freshness gate's notation cross-check judges ledger evidence against, and
``build_notation_for_executable`` is how a resolved command becomes a notation.
Both are covered here because the gate's own tests stub the resolver seam: a
cross-check whose target silently resolved nothing would reduce to a permanent
``unverified`` pass while every gate test stayed green — the same
right-for-the-wrong-reason class the cross-check exists to close, one level up.

Two properties get particular attention:

* **The notation is lifted from the executable, never recovered by inverting the
  tool-name map.** That inversion is only value-preserving while the map's values
  stay distinct, and nothing enforces distinctness.
* **One malformed command entry cannot take the whole sweep down.** The sweep's
  caller reads an exception as "the architecture could not be resolved", so a
  single bad entry in one module would otherwise disable the cross-check
  project-wide while the record still reported a pass.
"""

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = (
    _REPO_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-architecture' / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_client_build = _load_module('_cmd_client_build', '_cmd_client_build.py')
_cmd_client_query = _load_module('_cmd_client_query', '_cmd_client_query.py')

build_notation_for_executable = _cmd_client_build.build_notation_for_executable
resolve_project_build_notations = _cmd_client_query.resolve_project_build_notations

_PYPROJECT = 'plan-marshall:build-pyproject:pyproject_build'
_MAVEN = 'plan-marshall:build-maven:maven'


def _executable(notation: str, command_args: str = 'verify') -> str:
    """Render the canonical build-executable shape ``architecture resolve`` emits."""
    return f'python3 .plan/execute-script.py {notation} run --command-args "{command_args}"'


# =============================================================================
# build_notation_for_executable
# =============================================================================


def test_every_registered_build_notation_round_trips() -> None:
    """Each notation in the live map is recovered from its own executable.

    Derived from ``_BUILD_NOTATIONS`` rather than a transcribed list, so a newly
    registered build skill is covered without editing this test.
    """
    for notation in _cmd_client_build._BUILD_NOTATIONS:
        assert build_notation_for_executable(_executable(notation)) == notation


def test_the_notation_is_lifted_not_recovered_from_the_tool_name() -> None:
    """Two notations sharing a ``tool_name`` are still told apart.

    The map's values are tool names, and nothing requires them to be distinct —
    the map's own docstring notes the value prefixes every ``timeout_set`` key,
    which is a reason two wrappers for one language would deliberately share it.
    Recovering the notation by inverting the map would then answer with whichever
    entry was written last, so every real build row for the OTHER notation would
    be refused and the gate would hard-block every transition in the repository.
    """
    shadow = 'plan-marshall:build-shadow:shadow'
    shared_tool = _cmd_client_build._BUILD_NOTATIONS[_PYPROJECT]
    patched = dict(_cmd_client_build._BUILD_NOTATIONS)
    patched[shadow] = shared_tool
    original = _cmd_client_build._BUILD_NOTATIONS
    _cmd_client_build._BUILD_NOTATIONS = patched
    try:
        assert build_notation_for_executable(_executable(_PYPROJECT)) == _PYPROJECT
        assert build_notation_for_executable(_executable(shadow)) == shadow
    finally:
        _cmd_client_build._BUILD_NOTATIONS = original


def test_non_build_executables_resolve_to_none() -> None:
    """Anything outside the canonical build shape is not a build notation."""
    assert build_notation_for_executable('') is None
    assert build_notation_for_executable('./pw verify') is None
    assert build_notation_for_executable('python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks list --plan-id p') is None
    # A build skill reached by a QUERY verb is not a build executable.
    assert build_notation_for_executable(f'python3 .plan/execute-script.py {_PYPROJECT} discover --x y') is None
    # ``run`` with no ``--command-args`` is not the canonical shape either.
    assert build_notation_for_executable(f'python3 .plan/execute-script.py {_PYPROJECT} run') is None


# =============================================================================
# resolve_project_build_notations
# =============================================================================


def _with_crawl(monkeypatch, modules: dict) -> None:
    """Pin the module crawl so the sweep is exercised without a live project."""
    monkeypatch.setattr(_cmd_client_query, 'crawl_all_modules', lambda _project_dir: modules)


def test_the_set_is_the_union_over_every_module(monkeypatch) -> None:
    """A polyglot project resolves every build system it actually uses.

    Union-over-all-modules is what keeps the gate tier-agnostic: an
    orchestrator-tier build runs at the root module with no plan, and a second
    module may legitimately use a different tool.
    """
    _with_crawl(
        monkeypatch,
        {
            'py-mod': {'commands': {'verify': _executable(_PYPROJECT)}},
            'java-mod': {'commands': {'verify': _executable(_MAVEN)}},
            'docs-mod': {'commands': {'lint': 'markdownlint .'}},
        },
    )

    assert resolve_project_build_notations('.') == frozenset({_PYPROJECT, _MAVEN})


def test_both_command_entry_shapes_are_read(monkeypatch) -> None:
    """A command map holds bare strings and ``{'executable': ...}`` dicts alike."""
    _with_crawl(
        monkeypatch,
        {
            'a': {'commands': {'verify': _executable(_PYPROJECT)}},
            'b': {'commands': {'verify': {'executable': _executable(_MAVEN), 'mutating': True}}},
        },
    )

    assert resolve_project_build_notations('.') == frozenset({_PYPROJECT, _MAVEN})


def test_a_malformed_entry_does_not_take_the_sweep_down(monkeypatch) -> None:
    """One bad command entry must not cost the whole project its notation set.

    The caller reads an exception as "the architecture could not be resolved" and
    passes the gate ``unverified``, so a single list-valued command entry in one
    module would silently disable the cross-check project-wide — while the
    decision record still said the gate passed.
    """
    _with_crawl(
        monkeypatch,
        {
            'broken-list': {'commands': {'verify': ['a', 'b']}},
            'broken-none': {'commands': {'verify': None}},
            'broken-number': {'commands': {'verify': 7}},
            'broken-executable-type': {'commands': {'verify': {'executable': 12}}},
            'broken-commands-type': {'commands': ['not', 'a', 'map']},
            'broken-module': 'not a dict at all',
            'good': {'commands': {'verify': _executable(_PYPROJECT)}},
        },
    )

    assert resolve_project_build_notations('.') == frozenset({_PYPROJECT})


def test_no_modules_resolves_to_the_empty_set(monkeypatch) -> None:
    """An un-crawled project resolves nothing — an inability, not a refutation.

    The caller MUST NOT read this as "the project builds with nothing"; its own
    contract turns an empty set into ``unverified``, never ``refuted``.
    """
    _with_crawl(monkeypatch, {})

    assert resolve_project_build_notations('.') == frozenset()


# =============================================================================
# Positive control against the real repository
# =============================================================================


def test_the_live_repository_resolves_its_own_build_notation() -> None:
    """Anti-vacuity: the real crawl resolves a real build notation for a real tree.

    Every other case here pins the crawl, and the gate's own tests pin the
    resolver seam — so all of them would stay green if this function resolved
    nothing against a real tree. The cross-check would then be a permanent no-op
    reporting ``unverified`` forever, and nothing in the suite would notice.
    This case is the one that would.

    ⛔ It does **not** cover an import-path fault, and must not be described as
    doing so. The module is loaded here by absolute path through ``_load_module``,
    which bypasses ``sys.path`` entirely, so a missing ``PYTHONPATH`` entry is
    invisible from this case by construction. The
    runtime import is exercised by the sibling gate-level case
    ``test_freshness_notation_crosscheck.test_the_real_resolution_path_refuses_and_corroborates_against_this_repository``,
    which reaches the resolver the way production does — ``from _cmd_client_query
    import …`` by NAME, inside ``resolve_expected_notations``. Neither case alone
    covers both halves; the pair does, and that is why both exist.

    Asserted as a superset rather than an equality: the repository is Python-only
    today, and pinning that would turn adding a second build system into a test
    failure for no reason.
    """
    notations = resolve_project_build_notations(str(_REPO_ROOT))

    assert notations, (
        'the live crawl resolved no build notation for this repository; the '
        'freshness gate cross-check would report unverified on every row.'
    )
    assert _PYPROJECT in notations, notations

# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``@lru_cache`` memoization of ``_read_verification_steps``.

The pre-commit freshness check calls ``_read_verification_steps`` twice with the
same ``plan_id`` within one short-lived CLI process — once from
``_is_documentation_only`` and once from ``_is_lint_only``.
``@lru_cache(maxsize=1)`` makes the second call a cache hit, so ``execution.toon``
is read from disk and parsed exactly once per freshness check. An autouse fixture
clears the module-level cache around each test so the cache never leaks across
cases (the production correctness relies on each CLI invocation being a fresh
process).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT

_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-tasks'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_freshness_mod = _load_module(
    '_cmd_pre_commit_verify_freshness_cache_under_test',
    '_cmd_pre_commit_verify_freshness.py',
)


@pytest.fixture(autouse=True)
def _clear_cache():
    # The module-level lru_cache must not leak across tests (or into the rest of
    # the suite) — clear before and after each case.
    _freshness_mod._read_verification_steps.cache_clear()
    yield
    _freshness_mod._read_verification_steps.cache_clear()


def _write_manifest(plan_dir: Path) -> None:
    """Create an ``execution.toon`` so ``is_file()`` passes.

    Its bytes are irrelevant: the patched ``parse_toon`` ignores them and returns
    a controlled dict, isolating the cache assertion from TOON round-tripping.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / _freshness_mod._MANIFEST_FILENAME).write_text(
        'phase_5:\n', encoding='utf-8'
    )


def _patch_counting_parse(
    monkeypatch: pytest.MonkeyPatch, plan_dir: Path, steps: list[str]
) -> dict:
    """Point the manifest read at ``plan_dir`` and count ``parse_toon`` calls."""
    monkeypatch.setattr(_freshness_mod, 'get_plan_dir', lambda plan_id: plan_dir)
    calls = {'parse': 0}

    def _counting_parse_toon(_text):
        calls['parse'] += 1
        return {'phase_5': {'verification_steps': steps}}

    monkeypatch.setattr(_freshness_mod, 'parse_toon', _counting_parse_toon)
    return calls


def test_manifest_read_once_across_both_call_sites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    plan_dir = tmp_path / 'plan'
    _write_manifest(plan_dir)
    calls = _patch_counting_parse(monkeypatch, plan_dir, ['verify:quality-gate'])

    # Act: drive BOTH internal call sites; each calls _read_verification_steps.
    doc_only = _freshness_mod._is_documentation_only('plan-x')
    lint_only = _freshness_mod._is_lint_only('plan-x')

    # Assert: the manifest is parsed from disk exactly once (the second call hits
    # the cache), and both predicates read consistent data.
    assert calls['parse'] == 1
    assert doc_only is False
    assert lint_only is True


def test_cache_clear_forces_a_fresh_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    plan_dir = tmp_path / 'plan'
    _write_manifest(plan_dir)
    calls = _patch_counting_parse(monkeypatch, plan_dir, ['verify:quality-gate'])

    # Act + Assert: the first read parses; the second is a cache hit; an explicit
    # cache_clear forces the next call to re-parse (the test-isolation contract).
    _freshness_mod._read_verification_steps('plan-x')
    assert calls['parse'] == 1
    _freshness_mod._read_verification_steps('plan-x')
    assert calls['parse'] == 1
    _freshness_mod._read_verification_steps.cache_clear()
    _freshness_mod._read_verification_steps('plan-x')
    assert calls['parse'] == 2

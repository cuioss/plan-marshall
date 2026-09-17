# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the GitHub `repo merge-queue` probe/enable handlers.

All fixtures are API-shape-faithful (no live gh). The probe reads the evaluated
branch rules via ``GET /repos/{owner}/{repo}/rules/branches/{branch}`` and maps
each result to the shared eligibility discriminator; enable creates a
``merge_queue`` ruleset via ``POST /repos/{owner}/{repo}/rulesets`` and is
idempotent.
"""

import argparse
import json

import github_ops
import pytest


@pytest.fixture(autouse=True)
def _hermetic_bypass_config(monkeypatch):
    """Neutralise the real marshal.json for every test.

    ``_read_merge_queue_bypass_config`` reads ``merge_queue.bypass_app_id`` /
    ``merge_queue.bypass_app_slugs`` from the live config via the lazy
    ``_config_core`` seam. Pinning ``load_config`` to an empty dict makes the
    default resolution ``(None, [])`` regardless of the meta-project's real
    config, so the existing enable/probe tests stay deterministic. Tests that
    exercise config-driven resolution override this by patching
    ``github_ops._read_merge_queue_bypass_config`` (behaviour) or
    ``_config_core.load_config`` (reader unit).
    """
    import _config_core

    monkeypatch.setattr(_config_core, 'is_initialized', lambda: True)
    monkeypatch.setattr(_config_core, 'load_config', lambda: {})


def _branch_cleanup_config(pr_merge_strategy):
    return {
        'plan': {
            'phase-6-finalize': {
                'steps': {
                    'default:branch-cleanup': {'pr_merge_strategy': pr_merge_strategy},
                }
            }
        }
    }


def test_github_ops_exposes_repo_merge_queue_handlers():
    assert callable(github_ops.cmd_repo_merge_queue_probe)
    assert callable(github_ops.cmd_repo_merge_queue_enable)


def test_config_reader_reads_both_knobs(monkeypatch):
    import _config_core

    monkeypatch.setattr(
        _config_core,
        'load_config',
        lambda: {'merge_queue': {'bypass_app_id': 4242, 'bypass_app_slugs': ['release-bot', 'other']}},
    )
    app_id, slugs = github_ops._read_merge_queue_bypass_config()
    assert app_id == 4242
    assert slugs == ['release-bot', 'other']


def test_config_reader_absent_block_yields_empty(monkeypatch):
    import _config_core

    monkeypatch.setattr(_config_core, 'load_config', lambda: {'plan': {}})
    assert github_ops._read_merge_queue_bypass_config() == (None, [])


def test_config_reader_rejects_bool_and_malformed_slugs(monkeypatch):
    import _config_core

    # bool is an int subclass — must NOT be read as an id; non-str slugs dropped.
    monkeypatch.setattr(
        _config_core,
        'load_config',
        lambda: {'merge_queue': {'bypass_app_id': True, 'bypass_app_slugs': ['ok', 5, '']}},
    )
    app_id, slugs = github_ops._read_merge_queue_bypass_config()
    assert app_id is None
    assert slugs == ['ok']


def test_config_reader_never_raises_on_load_error(monkeypatch):
    import _config_core

    def _boom():
        raise RuntimeError('no git root')

    monkeypatch.setattr(_config_core, 'load_config', _boom)
    assert github_ops._read_merge_queue_bypass_config() == (None, [])


@pytest.mark.parametrize(
    ('configured', 'expected'),
    [('squash', 'SQUASH'), ('merge', 'MERGE'), ('rebase', 'REBASE')],
)
def test_resolve_merge_method_maps_configured_strategy(monkeypatch, configured, expected):
    import _config_core

    monkeypatch.setattr(_config_core, 'load_config', lambda: _branch_cleanup_config(configured))
    assert github_ops._resolve_merge_queue_merge_method() == expected


def test_resolve_merge_method_defaults_to_squash_on_unknown_value(monkeypatch):
    import _config_core

    monkeypatch.setattr(_config_core, 'load_config', lambda: _branch_cleanup_config('fast-forward'))
    assert github_ops._resolve_merge_queue_merge_method() == 'SQUASH'

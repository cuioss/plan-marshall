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


def test_ruleset_payload_targets_branch_with_merge_queue_rule():
    payload = github_ops.build_merge_queue_ruleset_payload('main')
    assert payload['target'] == 'branch'
    assert payload['enforcement'] == 'active'
    assert payload['conditions']['ref_name']['include'] == ['refs/heads/main']
    rule_types = [r.get('type') for r in payload['rules']]
    assert 'merge_queue' in rule_types


def test_payload_omits_bypass_actors_without_ids():
    # No ids (default) and explicit empty list both preserve today's behavior.
    assert 'bypass_actors' not in github_ops.build_merge_queue_ruleset_payload('main')
    assert 'bypass_actors' not in github_ops.build_merge_queue_ruleset_payload('main', [])


def test_payload_weaves_bypass_actors_when_ids_supplied():
    payload = github_ops.build_merge_queue_ruleset_payload('main', [12345, 678])
    actors = payload['bypass_actors']
    assert [a['actor_id'] for a in actors] == [12345, 678]
    for actor in actors:
        assert actor['actor_type'] == 'Integration'
        assert actor['bypass_mode'] == 'always'
    # The merge_queue rule is still present and unchanged.
    assert 'merge_queue' in [r.get('type') for r in payload['rules']]


@pytest.mark.parametrize('method', ['SQUASH', 'MERGE', 'REBASE'])
def test_payload_emits_mapped_merge_method(method):
    payload = github_ops.build_merge_queue_ruleset_payload('main', merge_method=method)
    merge_queue_rules = [r for r in payload['rules'] if r.get('type') == 'merge_queue']
    assert merge_queue_rules[0]['parameters']['merge_method'] == method


def test_payload_default_merge_method_is_merge():
    # The pure function's default preserves the historical MERGE behavior;
    # callers pass the config-resolved method explicitly.
    payload = github_ops.build_merge_queue_ruleset_payload('main')
    merge_queue_rules = [r for r in payload['rules'] if r.get('type') == 'merge_queue']
    assert merge_queue_rules[0]['parameters']['merge_method'] == 'MERGE'


def test_resolve_merge_method_defaults_to_squash_when_absent(monkeypatch):
    import _config_core

    # Empty config — no plan block, no step params at all.
    monkeypatch.setattr(_config_core, 'load_config', lambda: {})
    assert github_ops._resolve_merge_queue_merge_method() == 'SQUASH'


def test_resolve_merge_method_defaults_to_squash_on_malformed_value(monkeypatch):
    import _config_core

    # A non-string value is malformed — never raises, falls back to SQUASH.
    monkeypatch.setattr(_config_core, 'load_config', lambda: _branch_cleanup_config(['squash']))
    assert github_ops._resolve_merge_queue_merge_method() == 'SQUASH'


def test_resolve_merge_method_never_raises_on_load_error(monkeypatch):
    import _config_core

    def _boom():
        raise RuntimeError('no git root')

    monkeypatch.setattr(_config_core, 'load_config', _boom)
    assert github_ops._resolve_merge_queue_merge_method() == 'SQUASH'

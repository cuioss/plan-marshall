#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the shared ``--extra`` passthrough guard (deliverable 3).

``apply_extra_passthrough`` in ``_providers_core`` is the single guard the
``credentials configure`` and ``credentials edit`` commands share so that both
accept and reject ``--extra KEY=VALUE`` keys identically. The guard rejects
secret-named keys (``token`` / ``username`` / ``password``) — which must never
land in the git-tracked ``marshal.json`` — and skips empty/duplicate keys.

These tests exercise the guard directly, exercise the exact call shapes
``configure`` and ``edit`` use, and assert behavioural parity between the two
commands for the same inputs.
"""

import sys
from pathlib import Path

from conftest import load_script_module

sys.path.insert(0, str(Path(__file__).parent))


_providers_core = load_script_module(
    'plan-marshall', 'manage-providers', '_providers_core.py', '_providers_core'
)
_cred_edit = load_script_module('plan-marshall', 'manage-providers', '_cred_edit.py', '_cred_edit')

apply_extra_passthrough = _providers_core.apply_extra_passthrough
SECRET_PLACEHOLDERS = _providers_core.SECRET_PLACEHOLDERS


# === Direct guard behaviour ===


def test_secret_keys_are_rejected():
    """A key naming any secret field is dropped, never written to the config."""
    config: dict = {}
    applied = apply_extra_passthrough(
        config, ['token=leak', 'username=admin', 'password=hunter2']
    )
    assert applied == []
    assert config == {}


def test_each_secret_placeholder_key_is_rejected():
    """Every key in SECRET_PLACEHOLDERS is on the denylist."""
    for secret_key in SECRET_PLACEHOLDERS:
        config: dict = {}
        applied = apply_extra_passthrough(config, [f'{secret_key}=value'])
        assert applied == [], f'{secret_key} should be rejected'
        assert secret_key not in config


def test_secret_keys_are_rejected_case_insensitively():
    """A capital/mixed-case variant of a secret key is rejected too (CWE-178).

    The denylist normalizes the key with ``.lower()`` before the membership
    check, so ``Token`` / ``TOKEN`` / ``Password`` can never bypass the guard
    and persist a secret into the git-tracked ``marshal.json``.
    """
    config: dict = {}
    applied = apply_extra_passthrough(
        config, ['Token=leak', 'TOKEN=leak', 'Password=hunter2', 'UserName=admin']
    )
    assert applied == []
    assert config == {}


def test_benign_keys_are_applied_in_order():
    """Non-secret keys are written and returned in supplied order."""
    config: dict = {}
    applied = apply_extra_passthrough(config, ['organization=acme', 'project_key=acme_proj'])
    assert applied == ['organization', 'project_key']
    assert config == {'organization': 'acme', 'project_key': 'acme_proj'}


def test_empty_and_whitespace_only_keys_are_skipped():
    """A whitespace-only key collapses to empty and is skipped."""
    config: dict = {}
    applied = apply_extra_passthrough(config, ['=novalue', '   =spaces', 'region=eu'])
    assert applied == ['region']
    assert config == {'region': 'eu'}


def test_keys_are_whitespace_stripped():
    """Surrounding whitespace is stripped from the key before it is stored."""
    config: dict = {}
    applied = apply_extra_passthrough(config, ['  region  =eu'])
    assert applied == ['region']
    assert config == {'region': 'eu'}


def test_pairs_without_equals_are_skipped():
    """An entry lacking ``=`` is ignored entirely."""
    config: dict = {}
    applied = apply_extra_passthrough(config, ['noseparator', 'region=eu'])
    assert applied == ['region']
    assert config == {'region': 'eu'}


def test_value_may_contain_equals():
    """Only the first ``=`` splits key from value; the value keeps the rest."""
    config: dict = {}
    applied = apply_extra_passthrough(config, ['filter=a=b=c'])
    assert applied == ['filter']
    assert config == {'filter': 'a=b=c'}


def test_duplicate_keys_are_deduped_last_value_wins():
    """A repeated key appears once in the returned list; the last value wins."""
    config: dict = {}
    applied = apply_extra_passthrough(config, ['region=eu', 'region=us'])
    assert applied == ['region']
    assert config == {'region': 'us'}


def test_existing_config_keys_are_preserved():
    """Pre-existing keys not named by --extra survive untouched."""
    config: dict = {'url': 'https://example', 'organization': 'old'}
    applied = apply_extra_passthrough(config, ['organization=new', 'project_key=p'])
    assert applied == ['organization', 'project_key']
    assert config == {
        'url': 'https://example',
        'organization': 'new',
        'project_key': 'p',
    }


# === configure-command call shape ===


def test_configure_style_usage_rejects_secret_and_collects_supplied_keys():
    """Mirror configure's exact use: secret dropped, supplied keys collected."""
    provider_config: dict = {'url': 'https://sonar'}
    supplied_keys = set(
        apply_extra_passthrough(provider_config, ['token=leak', 'organization=acme'])
    )
    assert supplied_keys == {'organization'}
    assert 'token' not in provider_config
    assert provider_config == {'url': 'https://sonar', 'organization': 'acme'}


# === edit-command path ===


def test_edit_upsert_rejects_secret_and_persists_benign(monkeypatch):
    """``_upsert_extra_fields`` drops a secret key and writes only the benign one."""
    captured: dict = {}
    monkeypatch.setattr(_cred_edit, 'read_provider_config', lambda skill: {'url': 'https://sonar'})
    monkeypatch.setattr(
        _cred_edit, 'write_provider_config', lambda skill, cfg: captured.update(cfg=cfg)
    )

    upserted = _cred_edit._upsert_extra_fields('skill-x', ['token=leak', 'region=eu'])

    assert upserted == ['region']
    assert 'token' not in captured['cfg']
    assert captured['cfg']['region'] == 'eu'
    # The pre-existing url survives the upsert.
    assert captured['cfg']['url'] == 'https://sonar'


def test_edit_upsert_skips_write_when_only_secret_supplied(monkeypatch):
    """When every supplied key is rejected, no write occurs (nothing to persist)."""
    writes: list = []
    monkeypatch.setattr(_cred_edit, 'read_provider_config', lambda skill: {})
    monkeypatch.setattr(_cred_edit, 'write_provider_config', lambda skill, cfg: writes.append(cfg))

    upserted = _cred_edit._upsert_extra_fields('skill-x', ['password=hunter2'])

    assert upserted == []
    assert writes == []


# === parity between configure and edit ===


def test_configure_and_edit_reject_secret_keys_identically(monkeypatch):
    """The same inputs produce the same accepted keys on both command paths."""
    pairs = ['token=leak', 'username=admin', 'organization=acme', 'project_key=p', 'region=eu']

    # configure path: build provider_config and apply the guard.
    configure_config: dict = {'url': 'https://sonar'}
    configure_keys = set(apply_extra_passthrough(configure_config, pairs))

    # edit path: run the same pairs through _upsert_extra_fields.
    captured: dict = {}
    monkeypatch.setattr(_cred_edit, 'read_provider_config', lambda skill: {'url': 'https://sonar'})
    monkeypatch.setattr(
        _cred_edit, 'write_provider_config', lambda skill, cfg: captured.update(cfg=cfg)
    )
    edit_keys = set(_cred_edit._upsert_extra_fields('skill-x', pairs))

    # Both commands accept exactly the non-secret keys — and reject the secrets.
    assert configure_keys == edit_keys == {'organization', 'project_key', 'region'}
    assert {'token', 'username'}.isdisjoint(configure_config)
    assert {'token', 'username'}.isdisjoint(captured['cfg'])

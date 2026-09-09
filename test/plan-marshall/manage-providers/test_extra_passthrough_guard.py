#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the shared ``--extra`` passthrough guard.

``apply_extra_passthrough`` in ``_providers_core`` is the single guard the
``credentials configure`` and ``credentials edit`` commands share so that both
accept and reject ``--extra KEY=VALUE`` keys identically. The guard rejects
secret-named keys (``token`` / ``username`` / ``password``) — which must never
land in the git-tracked ``marshal.json`` — and skips empty/duplicate keys.

These tests exercise the guard directly, exercise the exact call shapes
``configure`` and ``edit`` use, and assert behavioural parity between the two
commands for the same inputs.
"""

import _providers_core
import pytest

from conftest import load_script_module

_cred_edit = load_script_module('plan-marshall', 'manage-providers', '_cred_edit.py', '_cred_edit')

apply_extra_passthrough = _providers_core.apply_extra_passthrough
SECRET_PLACEHOLDERS = _providers_core.SECRET_PLACEHOLDERS


# === Direct guard behaviour ===


#: ``(initial_config, pairs, expected_applied, expected_config)`` per case. The
#: initial config is COPIED into each test so a case row is never mutated by the
#: run that consumes it.
_PASSTHROUGH_CASES = [
    ({}, ['token=leak', 'username=admin', 'password=hunter2'], [], {}),
    ({}, ['Token=leak', 'TOKEN=leak', 'Password=hunter2', 'UserName=admin'], [], {}),
    (
        {},
        ['organization=acme', 'project_key=acme_proj'],
        ['organization', 'project_key'],
        {'organization': 'acme', 'project_key': 'acme_proj'},
    ),
    ({}, ['=novalue', '   =spaces', 'region=eu'], ['region'], {'region': 'eu'}),
    ({}, ['  region  =eu'], ['region'], {'region': 'eu'}),
    ({}, ['noseparator', 'region=eu'], ['region'], {'region': 'eu'}),
    ({}, ['filter=a=b=c'], ['filter'], {'filter': 'a=b=c'}),
    ({}, ['region=eu', 'region=us'], ['region'], {'region': 'us'}),
    (
        {'url': 'https://example', 'organization': 'old'},
        ['organization=new', 'project_key=p'],
        ['organization', 'project_key'],
        {'url': 'https://example', 'organization': 'new', 'project_key': 'p'},
    ),
]


@pytest.mark.parametrize(
    ('initial_config', 'pairs', 'expected_applied', 'expected_config'),
    _PASSTHROUGH_CASES,
    ids=[
        'every-secret-named-key-is-dropped',
        'a-mixed-case-secret-key-is-dropped-too',
        'benign-keys-are-written-in-the-order-supplied',
        'empty-and-whitespace-only-keys-are-skipped',
        'a-padded-key-is-stored-in-its-stripped-form',
        'an-entry-without-an-equals-sign-is-ignored',
        'only-the-first-equals-splits-key-from-value',
        'a-repeated-key-is-reported-once-and-the-last-value-wins',
        'pre-existing-config-keys-survive-untouched',
    ],
)
def test_the_guard_reports_the_keys_it_accepted_and_writes_exactly_those(
    initial_config, pairs, expected_applied, expected_config
):
    """The returned key list and the resulting config agree on what got through.

    Case-insensitivity is part of the denylist rather than a separate contract:
    the key is lowered before the membership check, so ``Token`` can no more
    reach ``marshal.json`` than ``token`` can (CWE-178).
    """
    config: dict = dict(initial_config)

    applied = apply_extra_passthrough(config, pairs)

    assert applied == expected_applied
    assert config == expected_config


def test_each_secret_placeholder_key_is_rejected():
    """Every key in SECRET_PLACEHOLDERS is on the denylist."""
    for secret_key in SECRET_PLACEHOLDERS:
        config: dict = {}
        applied = apply_extra_passthrough(config, [f'{secret_key}=value'])
        assert applied == [], f'{secret_key} should be rejected'
        assert secret_key not in config


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

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Producer vocabulary accept and reject directions for verification-feedback."""

from __future__ import annotations

from pathlib import Path

from conftest import MARKETPLACE_ROOT

_DOC = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-marshall' / 'workflow' / 'verification-feedback.md'

_ACCEPT_SET = (
    'build-runner',
    'sonar',
    'pr-comment',
    'plugin-doctor',
    'pr-state',
    'finalize-feedback',
)


def _read_doc() -> str:
    """Return the workflow doc text."""
    return Path(_DOC).read_text(encoding='utf-8')


def test_accept_set_lists_every_producer():
    """The Inputs table accepts every vocabulary member."""
    text = _read_doc()
    for producer in _ACCEPT_SET:
        assert f'`{producer}`' in text, f'accept-set member missing: {producer}'


def test_reject_direction_names_timeout_and_owner():
    """The reject direction states the timeout rejection with its owner."""
    text = _read_doc()
    assert 'ci-verify-timeout' in text, 'rejection target missing'
    assert 'rejected on every producer path' in text, 'rejection scope missing'
    assert 'default:ci-verify' in text, 'rejection owner missing'


def test_single_accept_set_without_second_list():
    """The doc carries one accept-set and no second producer list."""
    text = _read_doc()
    assert text.count('Single accept-set') == 1, 'vocabulary must declare one accept-set'

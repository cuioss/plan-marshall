#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the marshal.json-resolved ``DEFAULT_CI_TIMEOUT`` in ``ci_base.py``.

The resolver contract (``ci_base._resolve_ci_timeout``):

* When marshal.json is absent OR the
  ``plan.phase-6-finalize.checks_wait_timeout_seconds`` key is unset, the
  resolver returns ``600`` (the conservative fallback that replaces the prior
  hard-coded 300s default).
* When marshal.json sets ``plan.phase-6-finalize.checks_wait_timeout_seconds``
  to a positive integer, the resolver returns that value.
* The argparse ``--timeout`` flag on both ``checks wait`` and
  ``pr wait-for-comments`` defaults to ``DEFAULT_CI_TIMEOUT`` (i.e. they share
  the same resolver-derived default).
* An explicit ``--timeout`` CLI value overrides both the resolver and the
  argparse default.
"""

import json

import ci_base
import pytest


@pytest.fixture
def fresh_marshal(tmp_path, monkeypatch):
    """Point ``_config_core.MARSHAL_PATH`` at a temporary marshal.json.

    Returns the path to the marshal.json file; tests overwrite it to drive
    the resolver branches. Returning the absolute path lets callers reuse
    the standard ``write_text`` API rather than re-deriving the location.

    The fixture monkey-patches the three plan-directory constants that
    ``_config_core`` snapshots at import time — ``PLAN_BASE_DIR``,
    ``MARSHAL_PATH``, and ``RUN_CONFIG_PATH`` — so the resolver under test
    reads from the sandboxed temp tree instead of the real repo's
    ``.plan/marshal.json``. This mirrors the ``tmp_config_dir`` fixture in
    ``test/conftest.py`` (which is private to manage-config tests).
    """
    import _config_core

    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    marshal_path = plan_dir / 'marshal.json'
    monkeypatch.setattr(_config_core, 'PLAN_BASE_DIR', plan_dir)
    monkeypatch.setattr(_config_core, 'MARSHAL_PATH', marshal_path)
    monkeypatch.setattr(_config_core, 'RUN_CONFIG_PATH', plan_dir / 'run-configuration.json')
    return marshal_path


def test_resolver_returns_fallback_when_marshal_absent(fresh_marshal):
    """marshal.json is absent -> resolver returns the 600s fallback."""
    assert not fresh_marshal.exists()

    timeout = ci_base._resolve_ci_timeout()

    assert timeout == 600


def test_resolver_returns_fallback_when_key_unset(fresh_marshal):
    """marshal.json present without the finalize timeout key -> resolver returns 600."""
    fresh_marshal.write_text(json.dumps({'plan': {}, 'skill_domains': {}}), encoding='utf-8')

    timeout = ci_base._resolve_ci_timeout()

    assert timeout == 600


def test_resolver_returns_marshal_value_when_key_set(fresh_marshal):
    """``plan.phase-6-finalize.checks_wait_timeout_seconds: 900`` -> resolver returns 900."""
    fresh_marshal.write_text(
        json.dumps({'plan': {'phase-6-finalize': {'checks_wait_timeout_seconds': 900}}}),
        encoding='utf-8',
    )

    timeout = ci_base._resolve_ci_timeout()

    assert timeout == 900


def test_resolver_returns_fallback_when_value_non_positive(fresh_marshal):
    """Non-positive integer guards against accidental zero/negative configs."""
    fresh_marshal.write_text(
        json.dumps({'plan': {'phase-6-finalize': {'checks_wait_timeout_seconds': 0}}}),
        encoding='utf-8',
    )

    timeout = ci_base._resolve_ci_timeout()

    assert timeout == 600


def test_resolver_returns_fallback_when_value_not_int(fresh_marshal):
    """A string value is rejected and the resolver falls back to 600."""
    fresh_marshal.write_text(
        json.dumps({'plan': {'phase-6-finalize': {'checks_wait_timeout_seconds': 'not-an-int'}}}),
        encoding='utf-8',
    )

    timeout = ci_base._resolve_ci_timeout()

    assert timeout == 600


def test_resolver_returns_fallback_on_malformed_json(fresh_marshal):
    """A corrupted marshal.json must not raise — resolver falls back to 600."""
    fresh_marshal.write_text('{not valid json', encoding='utf-8')

    timeout = ci_base._resolve_ci_timeout()

    assert timeout == 600


def test_checks_wait_argparse_default_uses_resolver():
    """``checks wait --pr-number 1`` defaults --timeout to DEFAULT_CI_TIMEOUT."""
    parser, _, _, _, _ = ci_base.build_parser('test')

    args = parser.parse_args(['checks', 'wait', '--pr-number', '1'])

    assert args.timeout == ci_base.DEFAULT_CI_TIMEOUT


def test_pr_wait_for_comments_argparse_default_uses_resolver():
    """``pr wait-for-comments --pr-number 1`` shares the same default."""
    parser, _, _, _, _ = ci_base.build_parser('test')

    args = parser.parse_args(['pr', 'wait-for-comments', '--pr-number', '1'])

    assert args.timeout == ci_base.DEFAULT_CI_TIMEOUT


def test_checks_wait_explicit_timeout_flag_overrides_default():
    """Explicit ``--timeout`` wins over the resolver-derived default."""
    parser, _, _, _, _ = ci_base.build_parser('test')

    args = parser.parse_args(['checks', 'wait', '--pr-number', '1', '--timeout', '1200'])

    assert args.timeout == 1200


def test_pr_wait_for_comments_explicit_timeout_flag_overrides_default():
    """Explicit ``--timeout`` also wins on the pr wait-for-comments subparser."""
    parser, _, _, _, _ = ci_base.build_parser('test')

    args = parser.parse_args(['pr', 'wait-for-comments', '--pr-number', '1', '--timeout', '1200'])

    assert args.timeout == 1200

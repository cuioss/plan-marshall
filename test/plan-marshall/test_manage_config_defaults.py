#!/usr/bin/env python3
"""Tests for the manage-config bootstrap defaults surface.

Asserts the runtime contract returned by ``get_default_config()`` (the
authoritative bootstrap shape consumed by ``marshall-steward`` and the
``manage-config init`` wizard). Complementary to the text-level assertions
in ``test_phase_6_manifest_executor.py`` — those scan the source for the
literal ``'loop_back_without_asking': True`` token, this one asserts the
dict returned by the function actually exposes the value.
"""

import importlib.util
import sys
from pathlib import Path

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_config_defaults = _load_module('_config_defaults', '_config_defaults.py')


class TestLoopBackWithoutAskingDefault:
    """``loop_back_without_asking`` is the reverse-direction symmetric
    counterpart of ``finalize_without_asking``. Default ``True`` produces
    the full unattended cycle (subject to ``max_iterations`` cap)."""

    def test_default_is_true(self) -> None:
        """``get_default_config()`` MUST expose
        ``plan.phase-6-finalize.loop_back_without_asking == True``."""
        cfg = _config_defaults.get_default_config()
        assert (
            cfg['plan']['phase-6-finalize']['loop_back_without_asking']
            is True
        ), (
            'get_default_config()["plan"]["phase-6-finalize"]'
            '["loop_back_without_asking"] must default to True'
        )

    def test_finalize_block_default_matches(self) -> None:
        """The ``DEFAULT_PLAN_FINALIZE`` module constant MUST agree with the
        value exposed by ``get_default_config()`` — they are the same
        physical default and must never drift."""
        assert (
            _config_defaults.DEFAULT_PLAN_FINALIZE['loop_back_without_asking']
            is True
        )

    def test_symmetric_with_finalize_without_asking(self) -> None:
        """Both auto-continuation knobs default to ``True`` — full unattended
        cycle in both forward and reverse directions. If either drifts to
        ``False``, the symmetric contract documented in
        ``manage-config/SKILL.md`` § Symmetric auto-continuation knobs is
        broken."""
        cfg = _config_defaults.get_default_config()
        forward = cfg['plan']['phase-5-execute']['finalize_without_asking']
        reverse = cfg['plan']['phase-6-finalize']['loop_back_without_asking']
        assert forward is True and reverse is True, (
            'Both finalize_without_asking and loop_back_without_asking must '
            'default to True (symmetric auto-continuation pair)'
        )

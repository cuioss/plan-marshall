#!/usr/bin/env python3
"""Tests for the manage-config bootstrap defaults surface.

Asserts the runtime contract returned by ``get_default_config()`` (the
authoritative bootstrap shape consumed by ``marshall-steward`` and the
``manage-config init`` wizard). Complementary to the text-level assertions
in ``test_phase_6_manifest_executor.py`` — those scan the source for the
literal ``'loop_back_without_asking': False`` token, this one asserts the
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
    counterpart of ``finalize_without_asking``. The defaults are
    intentionally asymmetric: forward auto-continue is the common case and
    defaults to ``True``; reverse loop-back surfaces a control return to
    the user and defaults to ``False`` so unattended runs cannot silently
    re-enter execute on a finalize-side fix."""

    def test_default_is_false(self) -> None:
        """``get_default_config()`` MUST expose
        ``plan.phase-6-finalize.loop_back_without_asking == False``."""
        cfg = _config_defaults.get_default_config()
        assert (
            cfg['plan']['phase-6-finalize']['loop_back_without_asking']
            is False
        ), (
            'get_default_config()["plan"]["phase-6-finalize"]'
            '["loop_back_without_asking"] must default to False'
        )

    def test_finalize_block_default_matches(self) -> None:
        """The ``DEFAULT_PLAN_FINALIZE`` module constant MUST agree with the
        value exposed by ``get_default_config()`` — they are the same
        physical default and must never drift."""
        assert (
            _config_defaults.DEFAULT_PLAN_FINALIZE['loop_back_without_asking']
            is False
        )

    def test_asymmetric_with_finalize_without_asking(self) -> None:
        """The two auto-continuation knobs default asymmetrically —
        ``finalize_without_asking=True`` (forward auto) and
        ``loop_back_without_asking=False`` (reverse halt). If they drift
        to a symmetric pair, the contract documented in
        ``marshall-steward/references/wizard-flow.md`` § Step 7c is
        broken."""
        cfg = _config_defaults.get_default_config()
        forward = cfg['plan']['phase-5-execute']['finalize_without_asking']
        reverse = cfg['plan']['phase-6-finalize']['loop_back_without_asking']
        assert forward is True and reverse is False, (
            'finalize_without_asking must default to True and '
            'loop_back_without_asking must default to False '
            '(asymmetric auto-continuation pair)'
        )

    def test_fresh_project_fallback_seeds_key(self) -> None:
        """A fresh project bootstrap (calling ``get_default_config()``
        without any prior marshal.json) MUST seed
        ``loop_back_without_asking`` explicitly — the key being absent
        would force every downstream consumer to apply its own fallback,
        and the silent-default surface area is exactly the bug pattern
        this test guards against."""
        cfg = _config_defaults.get_default_config()
        finalize = cfg['plan']['phase-6-finalize']
        assert 'loop_back_without_asking' in finalize, (
            'Fresh-project bootstrap must seed loop_back_without_asking '
            'explicitly in plan.phase-6-finalize'
        )
        # Sanity: the fresh-project value matches the module-level constant
        assert (
            finalize['loop_back_without_asking']
            == _config_defaults.DEFAULT_PLAN_FINALIZE['loop_back_without_asking']
        )

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared isolation helpers for manage-providers tests.

The autouse ``_plan_base_dir_sandbox`` fixture in ``test/conftest.py`` redirects
``PLAN_BASE_DIR`` (env var) and the ``_config_core`` module-level path attributes
into a fresh per-test tmp sandbox. ``_providers_core`` resolves ``marshal.json``
through ``file_ops.get_marshal_path()``, which reads the ``PLAN_BASE_DIR`` env var
live, so a test that wrote its ``marshal.json`` to a cwd-relative ``.plan/`` would
be shadowed by the empty sandbox and read no providers.

:func:`stage_marshal` composes WITH the sandbox: it re-points ``PLAN_BASE_DIR``
(env) and the ``_config_core`` attributes at a directory the test controls and
writes ``marshal.json`` exactly where ``file_ops.get_marshal_path()`` resolves it
(``{base}/marshal.json`` — note ``get_tracked_config_dir()`` returns the base
directly, not ``{base}/.plan``). Because ``monkeypatch`` is later-wins, this
override beats the autouse default while leaving the sandbox's leak prevention
intact (writes still land in the test's tmp tree, so the pollution guard stays
green).
"""

import json
from pathlib import Path
from typing import Any


def stage_marshal(base_dir: Path, monkeypatch, config: dict[str, Any] | None = None) -> Path:
    """Stage an isolated ``marshal.json`` and redirect resolution at it.

    Points ``PLAN_BASE_DIR`` (env, for subprocesses) and the ``_config_core``
    module attributes (for in-process callers) at ``base_dir``, then writes
    ``config`` to ``{base_dir}/marshal.json`` — the path
    ``file_ops.get_marshal_path()`` resolves under that base.

    Args:
        base_dir: Directory the test owns (typically ``tmp_path``).
        monkeypatch: The pytest ``monkeypatch`` fixture.
        config: marshal.json content. When ``None``, no file is written (the
            caller is exercising the missing-marshal path).

    Returns:
        Path to the resolved ``marshal.json`` (written iff ``config`` is given).
    """
    import _config_core

    marshal_path = base_dir / 'marshal.json'

    monkeypatch.setenv('PLAN_BASE_DIR', str(base_dir))
    monkeypatch.setattr(_config_core, 'PLAN_BASE_DIR', base_dir)
    monkeypatch.setattr(_config_core, 'MARSHAL_PATH', marshal_path)
    monkeypatch.setattr(_config_core, 'RUN_CONFIG_PATH', base_dir / 'run-configuration.json')

    if config is not None:
        marshal_path.write_text(json.dumps(config))

    return marshal_path

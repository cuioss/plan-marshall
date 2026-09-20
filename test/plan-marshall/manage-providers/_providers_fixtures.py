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


def stage_provider_subprocess_env(tmp_path: Path, monkeypatch) -> Path:
    """Stage an empty-domains marshal and redirect the subprocess env at it.

    Creates ``tmp_path/.plan/marshal.json`` holding ``{'skill_domains': {}}``
    and points ``PLAN_BASE_DIR`` (the staged plan dir), ``HOME`` (``tmp_path``)
    and ``PLAN_MARSHALL_CREDENTIALS_DIR`` (``tmp_path/creds``) at the test's tmp
    tree, so a ``run_script`` subprocess reads the staged marshal and writes
    credentials nowhere near the real home directory. The credentials dir is
    redirected but not created, exactly as the call sites it replaces did.

    Args:
        tmp_path: Directory the test owns (the pytest ``tmp_path`` fixture).
        monkeypatch: The pytest ``monkeypatch`` fixture.

    Returns:
        The staged plan directory (``tmp_path / '.plan'``).
    """
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'marshal.json').write_text(json.dumps({'skill_domains': {}}))
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    # Redirect credential dir for the subprocess so nothing lands in
    # the real ~/.plan-marshall-credentials/.
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(tmp_path / 'creds'))
    return plan_dir


def stage_provider_marshal_with_creds(
    tmp_path: Path, monkeypatch, config: dict[str, Any]
) -> tuple[Path, Path]:
    """Stage ``marshal.json`` via :func:`stage_marshal` plus an isolated creds dir.

    Composes :func:`stage_marshal` (which redirects both the ``PLAN_BASE_DIR``
    env the subprocess writer reads and the ``_config_core`` module attributes
    the in-process reader binds through) with a created ``tmp_path/creds``
    directory pinned as ``PLAN_MARSHALL_CREDENTIALS_DIR`` (env, for
    subprocesses) and ``_providers_core.CREDENTIALS_DIR`` (module attribute,
    for in-process callers). Setting only the env would leave the two bound to
    different marshal files.

    Args:
        tmp_path: Directory the test owns (the pytest ``tmp_path`` fixture).
        monkeypatch: The pytest ``monkeypatch`` fixture.
        config: marshal.json content staged through :func:`stage_marshal`.

    Returns:
        ``(plan_dir, creds_dir)`` — the staged plan and credentials directories.
    """
    import _providers_core

    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    stage_marshal(plan_dir, monkeypatch, config)
    creds_dir = tmp_path / 'creds'
    creds_dir.mkdir()
    monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(creds_dir))
    monkeypatch.setattr(_providers_core, 'CREDENTIALS_DIR', creds_dir)
    return plan_dir, creds_dir


def isolate_credentials_dir(fixture_dir: Path, monkeypatch) -> Path:
    """Redirect credential I/O at a fresh ``creds`` dir under ``fixture_dir``.

    Creates ``fixture_dir/creds`` and points the ``_providers_core``
    ``CREDENTIALS_DIR`` module attribute (evaluated at module import, so the
    env alone does not move it) at it.

    Args:
        fixture_dir: Directory the test owns.
        monkeypatch: The pytest ``monkeypatch`` fixture.

    Returns:
        The created credentials directory.
    """
    import _providers_core

    creds_dir = fixture_dir / 'creds'
    creds_dir.mkdir()
    monkeypatch.setattr(_providers_core, 'CREDENTIALS_DIR', creds_dir)
    return creds_dir


def enter_bare_dir(outside_repo_dir: Path, monkeypatch) -> Path:
    """Create a bare cwd with no ``marketplace/bundles`` ancestor and enter it.

    Creates ``outside_repo_dir/bare``, clears the explicit-anchor
    ``PM_MARKETPLACE_ROOT`` override, and changes into the bare directory, so
    provider discovery resolves through the cache-only path. Uses
    ``outside_repo_dir`` (not ``tmp_path``): pytest's ``tmp_path`` roots under
    the repo-local ``--basetemp``, which has a ``marketplace/bundles``
    ancestor, so the no-marketplace precondition only holds outside the repo.

    Args:
        outside_repo_dir: Directory outside the repository the test owns.
        monkeypatch: The pytest ``monkeypatch`` fixture.

    Returns:
        The bare directory, now the process cwd.
    """
    bare = outside_repo_dir / 'bare'
    bare.mkdir()
    monkeypatch.delenv('PM_MARKETPLACE_ROOT', raising=False)
    monkeypatch.chdir(bare)
    return bare

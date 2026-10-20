#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for opencode_runtime.py — OpenCode implementation of all 26 operations.

Asserts the measured session-identity contract (capture resolves the root session
through the session store and appends it; bind/resolve-plan round-trip through the
shared policy; every unavailable ground declines with a named reason), the
database-backed normalized-token operation, the two-tier deny/ask permission
contract (OpenCode carries a real permission backend: ``to_opencode_grant``
threads ``allow``/``ask``/``deny`` actions, ``protect-path`` emits a real writing
deny) and the ``success`` no-op pins for the maintenance operations
(``consolidate``, ``normalize``) and for the ``wait for`` waiting op (OpenCode
holds no wait channel), the success/no-op paths for metrics operations, and error
paths for invalid arguments across all 26 operations defined in the Runtime ABC.
"""

import json
import pathlib
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

# conftest.py sets up PYTHONPATH so imports resolve without manual sys.path work.
from _method_code import method_code
from opencode_runtime import OpenCodeRuntime, to_opencode_grant
from runtime_base import PERMISSION_FIX_OPERATIONS
from toon_parser import parse_toon

from conftest import get_skill_dir

# ⛔ Vacuity guard — the operation set is production's, so emptying it there collects
# zero cases at the parametrize below and still reports green.
assert PERMISSION_FIX_OPERATIONS, 'runtime_base.PERMISSION_FIX_OPERATIONS is empty'


# =============================================================================
# Shared fixture
# =============================================================================


@pytest.fixture()
def runtime() -> OpenCodeRuntime:
    """Return a fresh OpenCodeRuntime instance."""
    return OpenCodeRuntime()


# =============================================================================
# Helper
# =============================================================================


def _parse(toon_str: str) -> dict:
    """Parse a TOON string and assert it is non-empty."""
    result = parse_toon(toon_str)
    assert isinstance(result, dict), f'parse_toon returned non-dict: {toon_str!r}'
    return result


# =============================================================================
# session_teardown — honest no-op (no terminal-title channel on OpenCode)
# =============================================================================


def test_session_teardown_returns_honest_noop(runtime: OpenCodeRuntime) -> None:
    """session_teardown is an honest no-op naming what is actually missing.

    Teardown is now a session-BINDING release and writes no title reset, so the
    honest reason names the absent session binding rather than an absent
    terminal-title channel — naming the wrong missing thing would misdescribe
    why the verb cannot act.
    """
    result = _parse(runtime.session_teardown())
    assert result['status'] == 'no-op'
    assert result['operation'] == 'session teardown'
    assert 'session' in result['reason']
    assert 'binding to release' in result['reason']
    assert result['alternative']


# =============================================================================
# 1. project_initial_setup
# =============================================================================


def test_project_initial_setup_does_not_write_marshal_json(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """project_initial_setup leaves .plan/marshal.json unwritten; runtime.target is retired."""
    result = _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))
    assert result['status'] == 'success'
    assert result['operation'] == 'project initial-setup'
    assert result['target'] == 'opencode'
    assert result['marshal_written'] is False
    assert (tmp_path / '.plan').is_dir()
    assert (tmp_path / '.plan' / 'temp').is_dir()
    assert (tmp_path / 'opencode.json').is_file()
    assert not (tmp_path / '.plan' / 'marshal.json').exists()


def test_project_initial_setup_writes_no_runtime_owned_keys(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """Shared marshal carries no runtime.target and no standing_rules_bridge after setup."""
    result = _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))
    assert result['marshal_written'] is False
    assert not (tmp_path / '.plan' / 'marshal.json').exists()


def test_project_initial_setup_leaves_existing_marshal_untouched(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path
) -> None:
    """An existing marshal.json is left untouched and gains no runtime-owned keys."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    marshal_path = plan_dir / 'marshal.json'
    initial = json.dumps({'existing_key': 'existing_value'})
    marshal_path.write_text(initial, encoding='utf-8')

    result = _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))

    assert result['status'] == 'success'
    assert result['marshal_written'] is False
    assert marshal_path.read_text(encoding='utf-8') == initial
    data = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert data['existing_key'] == 'existing_value'
    assert 'runtime' not in data
    assert 'standing_rules_bridge' not in data


def test_project_initial_setup_ignores_corrupt_marshal(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """A corrupt marshal.json is left alone — setup writes nothing, so there is nothing to refuse."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'marshal.json').write_text('{not json', encoding='utf-8')

    result = _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))
    assert result['status'] == 'success'
    assert result['marshal_written'] is False
    assert (plan_dir / 'marshal.json').read_text(encoding='utf-8') == '{not json'


def test_project_initial_setup_ignores_non_object_runtime(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """A present-but-non-object runtime is left alone — no seeding path remains to repair it."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    marshal_file = plan_dir / 'marshal.json'
    marshal_file.write_text(json.dumps({'runtime': 'opencode'}), encoding='utf-8')

    result = _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))
    assert result['status'] == 'success'
    assert result['marshal_written'] is False

    data = json.loads(marshal_file.read_text(encoding='utf-8'))
    assert data['runtime'] == 'opencode'


def test_project_initial_setup_reports_bridge_drift(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """project_initial_setup reports the standing-rules bridge drift verdict."""
    from opencode_runtime import standing_rules_drift_status

    result = _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))
    assert 'bridge_drift' in result
    assert 'bridge_reason' in result
    status = standing_rules_drift_status(str(tmp_path))
    assert status['drift'] is False


def test_standing_rules_drift_detects_marker_mismatch(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """A bridge file without the version marker reports drift."""
    from opencode_runtime import standing_rules_drift_status

    (tmp_path / 'CLAUDE.md').write_text('# baseline\n', encoding='utf-8')
    bridge = tmp_path / '.opencode' / 'rules' / 'plan-marshall-standing-rules.md'
    bridge.parent.mkdir(parents=True)
    bridge.write_text('stale foreign content\n', encoding='utf-8')

    status = standing_rules_drift_status(str(tmp_path))
    assert status['drift'] is True
    assert status['reason'] == 'marker_mismatch'


def test_project_initial_setup_hook_skip_reason_present(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """project_initial_setup reports hook_skip_reason explaining no SessionStart hook."""
    result = _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))
    assert 'hook_skip_reason' in result
    assert 'OpenCode' in result['hook_skip_reason']


def test_project_initial_setup_invalid_dir_returns_error(runtime: OpenCodeRuntime, unwritable_dir: str) -> None:
    """project_initial_setup returns io_error when ``.plan`` cannot be created.

    ``unwritable_dir`` is a path under ``/dev/null`` — a character device, so
    creating any child of it raises ``ENOTDIR`` (an ``OSError``) for EVERY uid.
    A path merely assumed absent under ``/`` (``/nonexistent/...``) would NOT
    exercise this branch as root: the OS bypasses the DAC permission check, so
    the ``mkdir`` would SUCCEED (returning ``success``, not ``io_error``) and
    additionally leak the sentinel under ``/``, poisoning every sibling test
    that probes it for absence. See the ``unwritable_dir`` /
    ``_root_fs_pollution_guard`` fixtures in ``test/conftest.py``. The
    ``/dev/null`` path exercises the ``io_error`` branch identically on an
    unprivileged host and on a root sandbox.
    """
    result = _parse(runtime.project_initial_setup(unwritable_dir, 'opencode'))
    assert result['status'] == 'error'
    assert result['error'] == 'io_error'


# =============================================================================
# 1b. project_install_hook — always no-op
# =============================================================================


def test_project_install_hook_is_noop(runtime: OpenCodeRuntime) -> None:
    """project_install_hook returns no-op — OpenCode exposes no hook channel to wire."""
    result = _parse(runtime.project_install_hook('opencode'))
    assert result['status'] == 'no-op'
    assert result['operation'] == 'project install-hook'
    assert 'reason' in result
    assert 'alternative' in result


# =============================================================================
# 2. session capture / bind / resolve-plan — measured identity
# =============================================================================

#: Fixed clock so a usage window boundary never depends on the wall clock.
_BASE = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)


def _iso(minutes: int) -> str:
    """Return the ISO stamp *minutes* after the fixed clock."""
    return (_BASE + timedelta(minutes=minutes)).isoformat()


def _at(minutes: int) -> int:
    """Return the epoch-millisecond stamp *minutes* after the fixed clock."""
    return int((_BASE + timedelta(minutes=minutes)).timestamp() * 1000)


def _isolate_store(monkeypatch: pytest.MonkeyPatch, db_path: pathlib.Path) -> None:
    """Point the runtime at *db_path*, ahead of any ambient override."""
    monkeypatch.delenv('OPENCODE_DB', raising=False)
    monkeypatch.setenv('OPENCODE_DB_PATH', str(db_path))


def _write_tier1_db(db_path: pathlib.Path, rows: list[tuple[str, str | None]]) -> None:
    """Create a tier-1 store with ``session_v2(id, parent_id, model)`` rows."""
    connection = sqlite3.connect(str(db_path))
    try:
        connection.execute('CREATE TABLE session_v2 (id TEXT, parent_id TEXT, model TEXT)')
        connection.executemany(
            'INSERT INTO session_v2 (id, parent_id, model) VALUES (?, ?, NULL)',
            rows,
        )
        connection.commit()
    finally:
        connection.close()


def _write_usage_db(
    db_path: pathlib.Path,
    sessions: list[tuple[str, str | None, int, int, int, int]],
    messages: list[tuple[str, str, int, Any]],
) -> None:
    """Create a tier-2 store with token columns and a ``session_message`` table.

    Args:
        db_path: Database file to create.
        sessions: ``(id, parent_id, input, output, cache_read, cache_write)``.
        messages: ``(session_id, type, time_created_ms, data)`` rows.
    """
    connection = sqlite3.connect(str(db_path))
    try:
        connection.execute(
            'CREATE TABLE session_v2 (id TEXT, parent_id TEXT, model TEXT, directory TEXT,'
            ' tokens_input INTEGER, tokens_output INTEGER, tokens_cache_read INTEGER,'
            ' tokens_cache_write INTEGER, cost REAL)'
        )
        connection.executemany(
            'INSERT INTO session_v2 (id, parent_id, model, directory, tokens_input,'
            ' tokens_output, tokens_cache_read, tokens_cache_write, cost)'
            ' VALUES (?, ?, NULL, NULL, ?, ?, ?, ?, 0.0)',
            sessions,
        )
        connection.execute(
            'CREATE TABLE session_message (session_id TEXT, type TEXT, time_created INTEGER, data TEXT)'
        )
        connection.executemany(
            'INSERT INTO session_message (session_id, type, time_created, data) VALUES (?, ?, ?, ?)',
            [
                (session_id, message_type, created, data if isinstance(data, str) else json.dumps(data))
                for session_id, message_type, created, data in messages
            ],
        )
        connection.commit()
    finally:
        connection.close()


@pytest.fixture()
def session_cache(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    """Redirect the shared per-session binding cache into ``tmp_path``."""
    cache = tmp_path / 'sessions'
    monkeypatch.setattr('session_binding._SESSION_CACHE_BASE', cache)
    return cache


def test_session_capture_resolves_a_child_id_to_the_root(
    runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """A child session id is measured as its ROOT session and stored."""
    db_path = tmp_path / 'opencode.db'
    _write_tier1_db(db_path, [('ses-root', None), ('ses-mid', 'ses-root'), ('ses-leaf', 'ses-mid')])
    _isolate_store(monkeypatch, db_path)
    monkeypatch.setenv('OPENCODE_SESSION_ID', 'ses-leaf')
    seen: list[tuple[str, str]] = []
    monkeypatch.setattr(
        'claude_runtime._manage_status_store_session',
        lambda plan_id, session_id: seen.append((plan_id, session_id)) or True,
    )

    result = _parse(runtime.session_capture('my-plan'))

    assert result['status'] == 'success'
    assert result['operation'] == 'session capture'
    assert result['plan_id'] == 'my-plan'
    assert result['session_id'] == 'ses-root'
    assert result['stored'] is True
    assert seen == [('my-plan', 'ses-root')]


def test_session_capture_unset_variable_is_a_noop_that_stores_nothing(
    runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """An unset ``OPENCODE_SESSION_ID`` declines and writes no identity."""
    _isolate_store(monkeypatch, tmp_path / 'opencode.db')
    monkeypatch.delenv('OPENCODE_SESSION_ID', raising=False)
    monkeypatch.setattr(
        'claude_runtime._manage_status_store_session',
        lambda *_args: pytest.fail('an unset variable must store nothing'),
    )

    result = _parse(runtime.session_capture('my-plan'))

    assert result['status'] == 'no-op'
    assert result['operation'] == 'session capture'
    assert 'OPENCODE_SESSION_ID' in result['reason']
    assert result['alternative']


def test_session_capture_missing_database_names_its_reason(
    runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """A set variable whose store is absent declines with the reader's named reason."""
    _isolate_store(monkeypatch, tmp_path / 'absent.db')
    monkeypatch.setenv('OPENCODE_SESSION_ID', 'ses-root')
    monkeypatch.setattr(
        'claude_runtime._manage_status_store_session',
        lambda *_args: pytest.fail('an unreadable store must store nothing'),
    )

    result = _parse(runtime.session_capture('my-plan'))

    assert result['status'] == 'no-op'
    assert result['reason'] == 'db_not_found'


def test_session_capture_unsupported_schema_names_its_reason(
    runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """A store carrying no session table declines with ``schema_unsupported``."""
    db_path = tmp_path / 'opencode.db'
    connection = sqlite3.connect(str(db_path))
    try:
        connection.execute('CREATE TABLE unrelated (id TEXT)')
        connection.commit()
    finally:
        connection.close()
    _isolate_store(monkeypatch, db_path)
    monkeypatch.setenv('OPENCODE_SESSION_ID', 'ses-root')

    result = _parse(runtime.session_capture('my-plan'))

    assert result['status'] == 'no-op'
    assert result['reason'] == 'schema_unsupported'


def test_session_capture_unknown_session_stores_nothing(
    runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """An id naming no row declines with ``session_not_found`` — the raw id is never stored."""
    db_path = tmp_path / 'opencode.db'
    _write_tier1_db(db_path, [('ses-root', None)])
    _isolate_store(monkeypatch, db_path)
    monkeypatch.setenv('OPENCODE_SESSION_ID', 'ses-absent')
    monkeypatch.setattr(
        'claude_runtime._manage_status_store_session',
        lambda *_args: pytest.fail('an unresolved id must store nothing'),
    )

    result = _parse(runtime.session_capture('my-plan'))

    assert result['status'] == 'no-op'
    assert result['reason'] == 'session_not_found'


def test_session_bind_and_resolve_plan_round_trip(
    runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch, session_cache: pathlib.Path
) -> None:
    """Binding writes the caller's own slot; resolve-plan reads it back."""
    monkeypatch.setenv('OPENCODE_SESSION_ID', 'ses-abc')

    bound = _parse(runtime.session_bind('my-plan'))
    resolved = _parse(runtime.session_resolve_plan())

    assert bound['status'] == 'success'
    assert bound['session_id'] == 'ses-abc'
    assert bound['bound'] is True
    assert (session_cache / 'ses-abc' / 'active-plan').read_text(encoding='utf-8') == 'my-plan'
    assert resolved['status'] == 'success'
    assert resolved['resolved'] is True
    assert resolved['plan_id'] == 'my-plan'


def test_session_bind_is_last_driven_wins(
    runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch, session_cache: pathlib.Path
) -> None:
    """A second bind on the same session replaces the first binding."""
    monkeypatch.setenv('OPENCODE_SESSION_ID', 'ses-abc')

    _parse(runtime.session_bind('first-plan'))
    _parse(runtime.session_bind('second-plan'))

    assert _parse(runtime.session_resolve_plan())['plan_id'] == 'second-plan'


def test_session_bind_without_an_id_is_a_noop(runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch) -> None:
    """No session id keeps the historical no-op rather than binding a phantom slot."""
    monkeypatch.delenv('OPENCODE_SESSION_ID', raising=False)

    result = _parse(runtime.session_bind('my-plan'))

    assert result['status'] == 'no-op'
    assert result['operation'] == 'session bind'
    assert result['alternative']


def test_session_resolve_plan_without_an_id_is_a_noop(
    runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No session id keeps the historical no-op on the read side too."""
    monkeypatch.delenv('OPENCODE_SESSION_ID', raising=False)

    result = _parse(runtime.session_resolve_plan())

    assert result['status'] == 'no-op'
    assert result['operation'] == 'session resolve-plan'
    assert result['alternative']


def test_session_resolve_plan_reports_unbound(runtime: OpenCodeRuntime, session_cache: pathlib.Path) -> None:
    """A session with no slot resolves to an empty plan id, not a fabricated one."""
    result = _parse(runtime.session_resolve_plan('ses-unbound'))

    assert result['status'] == 'success'
    assert result['resolved'] is False
    assert result['plan_id'] == ''


# =============================================================================
# 4. session_render_title — always no-op
# =============================================================================


def test_session_render_title_is_noop(runtime: OpenCodeRuntime) -> None:
    """session_render_title returns no-op because OpenCode has no plugin-driven hook."""
    result = _parse(runtime.session_render_title())
    assert result['status'] == 'no-op'
    assert result['operation'] == 'session render-title'


def test_session_render_title_noop_fields(runtime: OpenCodeRuntime) -> None:
    """session_render_title no-op includes reason and alternative."""
    result = _parse(runtime.session_render_title())
    assert 'reason' in result
    assert 'alternative' in result


# =============================================================================
# 4b. session_push_title_token — always no-op
# =============================================================================


def test_session_push_title_token_is_noop(runtime: OpenCodeRuntime) -> None:
    """session_push_title_token returns no-op because OpenCode has no push channel."""
    result = _parse(runtime.session_push_title_token('my-plan', '⏳'))
    assert result['status'] == 'no-op'
    assert result['operation'] == 'session push-title-token'


def test_session_push_title_token_noop_fields(runtime: OpenCodeRuntime) -> None:
    """session_push_title_token no-op includes reason and alternative."""
    result = _parse(runtime.session_push_title_token('my-plan', '⏳'))
    assert 'reason' in result
    assert 'alternative' in result


# =============================================================================
# 4c. session_reload_directive — no-op (full-restart alternative)
# =============================================================================


def test_session_reload_directive_is_noop(runtime: OpenCodeRuntime) -> None:
    """session_reload_directive returns no-op — OpenCode has no live plugin-reload
    command equivalent to Claude's /reload-plugins."""
    result = _parse(runtime.session_reload_directive())
    assert result['status'] == 'no-op'
    assert result['operation'] == 'session reload-directive'


def test_session_reload_directive_noop_names_restart_alternative(runtime: OpenCodeRuntime) -> None:
    """The no-op carries reason + alternative, and the alternative is a full
    session restart (the OpenCode fallback for picking up regenerated artifacts)."""
    result = _parse(runtime.session_reload_directive())
    assert 'reason' in result
    assert 'restart' in result['alternative'].lower()


# =============================================================================
# Permission Operations & Settings
# =============================================================================


def test_permission_settings_path_global(
    runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Global permission settings resolve to ~/.config/opencode/opencode.json."""
    cfg_dir = tmp_path / 'opencode'
    monkeypatch.setenv('OPENCODE_CONFIG_DIR', str(cfg_dir))
    path = runtime.permission_settings_path('global')
    assert path == str(cfg_dir / 'opencode.json')


def test_permission_settings_path_invalid_scope(runtime: OpenCodeRuntime) -> None:
    """Invalid scope raises ValueError."""
    with pytest.raises(ValueError, match='Unsupported scope'):
        runtime.permission_settings_path('invalid_scope')


def test_permission_settings_path_project_finds_existing(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """permission_settings_path('project') finds opencode.json in project dir."""
    cfg = tmp_path / 'opencode.json'
    cfg.write_text('{"permission": {}}', encoding='utf-8')
    assert runtime.permission_settings_path('project', project_dir=str(tmp_path)) == str(cfg)


def test_permission_settings_path_project_finds_dot_opencode(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """permission_settings_path('project') finds .opencode/opencode.json."""
    dot_dir = tmp_path / '.opencode'
    dot_dir.mkdir()
    cfg = dot_dir / 'opencode.json'
    cfg.write_text('{"permission": {}}', encoding='utf-8')
    assert runtime.permission_settings_path('project', project_dir=str(tmp_path)) == str(cfg)


def test_permission_settings_path_project_creates_when_writing(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path
) -> None:
    """permission_settings_path with write=True creates opencode.json if missing."""
    target_path = runtime.permission_settings_path('project', write=True, project_dir=str(tmp_path))
    assert pathlib.Path(target_path).is_file()
    data = json.loads(pathlib.Path(target_path).read_text(encoding='utf-8'))
    assert 'permission' in data
    assert 'bash' in data['permission']


def test_permission_load_and_save_settings(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """permission_load_settings and permission_save_settings round-trip JSON."""
    settings_file = tmp_path / 'opencode.json'
    data = {'permission': {'bash': {'./pw *': 'allow'}}}
    assert runtime.permission_save_settings(str(settings_file), data) is True
    assert settings_file.is_file()
    loaded = runtime.permission_load_settings(str(settings_file))
    assert loaded == data


def test_permission_ensure_defaults(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """permission_ensure_defaults adds missing baseline commands to permission.bash."""
    settings_file = tmp_path / 'opencode.json'
    settings: dict = {'permission': {'bash': {}}}
    res = runtime.permission_ensure_defaults(settings, str(settings_file), dry_run=False)
    assert res['defaults_added_count'] > 0
    assert res['applied'] is True
    assert settings_file.is_file()

    # Second call is idempotent
    res2 = runtime.permission_ensure_defaults(settings, str(settings_file), dry_run=False)
    assert res2['defaults_added_count'] == 0
    assert res2['applied'] is False


def test_permission_ensure_defaults_dry_run(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """permission_ensure_defaults with dry_run=True does not write to file."""
    settings_file = tmp_path / 'opencode.json'
    settings: dict = {'permission': {'bash': {}}}
    res = runtime.permission_ensure_defaults(settings, str(settings_file), dry_run=True)
    assert res['defaults_added_count'] > 0
    assert res['applied'] is False
    assert not settings_file.exists()


# 5. permission_configure


def test_permission_configure(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """permission_configure adds grants to opencode.json."""
    monkeypatch.chdir(tmp_path)
    grants = [
        {'rule': 'python3 .plan/execute-script.py *'},
        {'rule': 'read_file(**)'},
    ]
    result = _parse(runtime.permission_configure('project', grants))
    assert result['status'] == 'success'
    assert result['operation'] == 'permission configure'
    assert result['grants_added'] >= 1


def test_permission_configure_invalid_scope_returns_error(runtime: OpenCodeRuntime) -> None:
    """permission_configure with invalid scope returns error."""
    result = _parse(runtime.permission_configure('workspace', [{'rule': 'test'}]))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_scope'


# 6. permission_analyze


def test_permission_analyze(runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """permission_analyze reports analysis of permissions."""
    monkeypatch.chdir(tmp_path)
    result = _parse(runtime.permission_analyze('project', ['all'], None))
    assert result['status'] == 'success'
    assert 'project' in result['analysis']
    assert 'has_executor' in result['analysis']['project']


def test_permission_analyze_invalid_scope_returns_error(runtime: OpenCodeRuntime) -> None:
    """permission_analyze with invalid scope returns error."""
    result = _parse(runtime.permission_analyze('workspace', ['all'], None))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_scope'


def test_permission_analyze_invalid_check_returns_error(runtime: OpenCodeRuntime) -> None:
    """permission_analyze with an unknown check name returns error."""
    result = _parse(runtime.permission_analyze('global', ['nonexistent-check'], None))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_check'


# 7. permission_fix


def test_permission_fix_ensure_and_remove(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """permission_fix adds and removes grants."""
    monkeypatch.chdir(tmp_path)
    # Ensure
    res_add = _parse(runtime.permission_fix('project', 'ensure', ['python3 custom.py *'], False))
    assert res_add['status'] == 'success'
    assert res_add['added'] == 1

    # Remove
    res_rem = _parse(runtime.permission_fix('project', 'remove', ['python3 custom.py *'], False))
    assert res_rem['status'] == 'success'
    assert res_rem['removed'] == 1


def test_permission_fix_consolidate(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """permission_fix consolidate is a success no-op on OpenCode."""
    monkeypatch.chdir(tmp_path)
    result = _parse(runtime.permission_fix('project', 'consolidate', [], False))
    assert result['status'] == 'success'
    assert result['operation'] == 'permission fix'


def test_permission_fix_normalize_is_success_noop(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """permission_fix normalize is a success no-op on OpenCode, mirroring consolidate."""
    monkeypatch.chdir(tmp_path)
    result = _parse(runtime.permission_fix('project', 'normalize', [], False))
    assert result['status'] == 'success'
    assert result['operation'] == 'permission fix'
    assert result['fix_operation'] == 'normalize'


def test_to_opencode_grant_threads_deny_action() -> None:
    """A deny(...) wrapper intent survives the grant translation as deny."""
    category, pattern, action = to_opencode_grant('deny(git push *)')
    assert category == 'bash'
    assert pattern == 'git push *'
    assert action == 'deny'


def test_to_opencode_grant_threads_ask_action() -> None:
    """An ask(...) wrapper intent survives the grant translation as ask."""
    category, pattern, action = to_opencode_grant('ask(git push *)')
    assert category == 'bash'
    assert pattern == 'git push *'
    assert action == 'ask'


def test_to_opencode_grant_bare_form_defaults_to_allow() -> None:
    """Bare forms default to allow — the carve-out permit needs no wrapper."""
    category, pattern, action = to_opencode_grant('python3 .plan/execute-script.py *')
    assert category == 'bash'
    assert pattern == 'python3 .plan/execute-script.py *'
    assert action == 'allow'


def test_permission_fix_ensure_persists_deny_action(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """permission_fix ensure persists a deny grant into the bash map."""
    monkeypatch.chdir(tmp_path)
    result = _parse(runtime.permission_fix('project', 'ensure', ['deny(git push *)'], False))
    assert result['status'] == 'success'
    assert result['added'] == 1
    settings = json.loads((tmp_path / 'opencode.json').read_text(encoding='utf-8'))
    assert settings['permission']['bash']['git push *'] == 'deny'


def test_permission_fix_ensure_persists_ask_action(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """permission_fix ensure persists an ask grant into the bash map."""
    monkeypatch.chdir(tmp_path)
    result = _parse(runtime.permission_fix('project', 'ensure', ['ask(git fetch *)'], False))
    assert result['status'] == 'success'
    assert result['added'] == 1
    settings = json.loads((tmp_path / 'opencode.json').read_text(encoding='utf-8'))
    assert settings['permission']['bash']['git fetch *'] == 'ask'


def test_the_permission_fix_operation_population_is_not_empty() -> None:
    """The operation set must not be empty."""
    assert PERMISSION_FIX_OPERATIONS, 'the operation set must not be empty'


@pytest.mark.parametrize('operation', sorted(PERMISSION_FIX_OPERATIONS), ids=sorted(PERMISSION_FIX_OPERATIONS))
def test_permission_fix_handles_every_published_operation(
    runtime: OpenCodeRuntime, operation: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every published operation name is accepted without error."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('OPENCODE_CONFIG_DIR', str(tmp_path))
    args: list = [str(tmp_path / 'arg')] if operation == 'protect-path' else []
    result = _parse(runtime.permission_fix('global', operation, args, True))
    assert result['status'] in ('success', 'no-op')


def test_permission_fix_invalid_scope_returns_error(runtime: OpenCodeRuntime) -> None:
    """permission_fix with invalid scope returns error."""
    result = _parse(runtime.permission_fix('unknown', 'normalize', [], False))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_scope'


def test_permission_fix_invalid_operation_returns_error(runtime: OpenCodeRuntime) -> None:
    """permission_fix with unknown operation name returns error."""
    result = _parse(runtime.permission_fix('project', 'delete-all', [], False))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_operation'


# 8. permission_ensure_wildcards


def test_permission_ensure_wildcards(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """permission_ensure_wildcards ensures default commands in OpenCode."""
    monkeypatch.chdir(tmp_path)
    result = _parse(runtime.permission_ensure_wildcards('project', 'marketplace/', False))
    assert result['status'] == 'success'
    assert result['operation'] == 'permission ensure-wildcards'


def test_permission_ensure_wildcards_invalid_scope_returns_error(runtime: OpenCodeRuntime) -> None:
    """permission_ensure_wildcards with invalid scope returns error."""
    result = _parse(runtime.permission_ensure_wildcards('workspace', 'marketplace/', False))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_scope'


# 9. permission_ensure_steps


def test_permission_ensure_steps_success(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """permission_ensure_steps reports a measured zero for a marshal.json with no project steps."""
    marshal_path = tmp_path / 'marshal.json'
    marshal_path.write_text(json.dumps({'runtime': {'target': 'opencode'}}), encoding='utf-8')

    result = _parse(runtime.permission_ensure_steps(str(marshal_path), 'project', False))
    assert result['status'] == 'success'
    assert result['operation'] == 'permission ensure-steps'
    assert result['steps_scanned'] == 0
    assert result['permissions_added'] == 0


def test_permission_ensure_steps_missing_marshal_returns_error(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path
) -> None:
    """permission_ensure_steps returns error when marshal.json does not exist."""
    missing_path = str(tmp_path / 'nonexistent' / 'marshal.json')
    result = _parse(runtime.permission_ensure_steps(missing_path, 'project', False))
    assert result['status'] == 'error'
    assert result['error'] == 'marshal_not_found'


def test_permission_ensure_steps_invalid_scope_returns_error(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """permission_ensure_steps with invalid scope returns error."""
    marshal_path = tmp_path / 'marshal.json'
    marshal_path.write_text('{}', encoding='utf-8')

    result = _parse(runtime.permission_ensure_steps(str(marshal_path), 'workspace', False))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_scope'


def test_load_marshal_config_invalid_utf8_returns_error(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """Invalid UTF-8 in marshal.json is a load error, not an uncaught exception."""
    marshal_path = tmp_path / 'marshal.json'
    marshal_path.write_bytes(b'\xff\xfe\x00\x01')

    result = runtime.permission_load_marshal_config(str(marshal_path))
    assert 'error' in result
    assert 'marshal.json' in result['error']


def test_extract_project_steps_rejects_empty_project_prefix(
    runtime: OpenCodeRuntime,
) -> None:
    """A bare 'project:' entry yields no step record (empty skill is rejected)."""
    steps = runtime.permission_extract_project_steps(
        {'plan': {'phase-5-execute': {'steps': ['project:', 'project:real-skill']}}}
    )
    assert steps == [{'skill': 'real-skill', 'step': 'project:real-skill', 'phase': 'phase-5-execute'}]


def test_extract_project_steps_reads_the_keyed_map_shape(
    runtime: OpenCodeRuntime,
) -> None:
    """The keyed map is the shape the live marshal.json writes.

    The inlined reader this replaced guarded on ``isinstance(entries, list)`` and
    so returned an empty scan against a real marshal.json — a value
    indistinguishable from "this marshal.json declares no project steps". The
    shared reader accepts both shapes; the cross-runtime agreement cases live in
    ``test_project_steps_extraction.py``.
    """
    steps = runtime.permission_extract_project_steps(
        {
            'plan': {
                'phase-5-execute': {'steps': {'default:push': {}, 'project:real-skill': {'lane': 'minimal'}}},
            }
        }
    )
    assert steps == [{'skill': 'real-skill', 'step': 'project:real-skill', 'phase': 'phase-5-execute'}]


def test_extract_project_steps_delegates_to_the_shared_reader() -> None:
    """This module names neither the phase roster nor the ``steps`` shape.

    Asserted over the method's CODE, docstring excluded — see ``_method_code``.
    """
    body = method_code('plan-marshall', 'platform-runtime', 'opencode_runtime.py', 'permission_extract_project_steps')
    assert 'extract_project_steps(' in body
    assert "'phase-5-execute'" not in body
    assert 'isinstance(entries, list)' not in body


# 10. permission_web_analyze & permission_web_apply


def test_permission_web_analyze_and_apply(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """permission_web_apply enables webfetch and permission_web_analyze reads it."""
    monkeypatch.chdir(tmp_path)
    res_apply = _parse(runtime.permission_web_apply('project', add=['example.com'], remove=[], dry_run=False))
    assert res_apply['status'] == 'success'
    assert res_apply['changed'] is True

    res_analyze = _parse(runtime.permission_web_analyze('project'))
    assert res_analyze['status'] == 'success'
    assert res_analyze['webfetch_permission'] == 'allow'


def test_permission_web_analyze_invalid_scope_returns_error(runtime: OpenCodeRuntime) -> None:
    """permission_web_analyze with invalid scope returns error."""
    result = _parse(runtime.permission_web_analyze('local'))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_scope'


def test_permission_web_apply_invalid_scope_returns_error(runtime: OpenCodeRuntime) -> None:
    """permission_web_apply with invalid scope returns error."""
    result = _parse(runtime.permission_web_apply('workspace', add=[], remove=[], dry_run=False))
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_scope'


# =============================================================================
# 12. metrics_capture
# =============================================================================


def test_metrics_capture_with_total_tokens_is_honest_noop(runtime: OpenCodeRuntime) -> None:
    """metrics_capture with total_tokens declines rather than fabricating success.

    OpenCode reaches no token-persistence boundary, so reporting ``success``
    for a manual count would be a success the caller cannot distinguish from a
    stored one — a silently lost measurement. The op returns an honest ``no-op``
    with a reason and the alternative.
    """
    result = _parse(runtime.metrics_capture('my-plan', 'phase-1-init', total_tokens=42000))
    assert result['status'] == 'no-op'
    assert result['operation'] == 'metrics capture'
    assert result['reason']
    assert 'alternative' in result
    assert result.get('tokens_captured') is None


def test_metrics_capture_without_tokens_is_noop(runtime: OpenCodeRuntime) -> None:
    """metrics_capture without total_tokens is no-op (no session transcript on OpenCode)."""
    result = _parse(runtime.metrics_capture('my-plan', 'phase-2-refine', total_tokens=None))
    assert result['status'] == 'no-op'
    assert result['operation'] == 'metrics capture'
    assert 'OpenCode' in result['reason']
    assert 'alternative' in result


def test_metrics_capture_zero_tokens_is_honest_noop(runtime: OpenCodeRuntime) -> None:
    """metrics_capture with total_tokens=0 is still a no-op — even zero needs persisting."""
    result = _parse(runtime.metrics_capture('my-plan', 'phase-3-outline', total_tokens=0))
    assert result['status'] == 'no-op'
    assert result['operation'] == 'metrics capture'
    assert 'alternative' in result


# =============================================================================
# 12b. metrics_normalized_tokens — measured per-phase buckets
# =============================================================================


def _usage_messages() -> list[tuple[str, str, int, Any]]:
    """Return one main, one sub-agent and one tool message inside ``[0, 30)``."""
    return [
        (
            'ses-root',
            'assistant',
            _at(5),
            {'tokens': {'input': 10, 'output': 20, 'cache': {'read': 3, 'write': 4}}, 'cost': 0.5},
        ),
        (
            'ses-child',
            'assistant',
            _at(10),
            {'tokens': {'input': 100, 'output': 200, 'cache': {'read': 30, 'write': 40}}, 'cost': 1.5},
        ),
        ('ses-child', 'tool', _at(12), {'tool': 'bash', 'state': {'status': 'completed'}}),
    ]


def test_metrics_normalized_tokens_writes_measured_buckets(
    runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Per-phase buckets split the root's usage from its sub-agents'."""
    db_path = tmp_path / 'opencode.db'
    _write_usage_db(
        db_path,
        [('ses-root', None, 10, 20, 3, 4), ('ses-child', 'ses-root', 100, 200, 30, 40)],
        _usage_messages(),
    )
    _isolate_store(monkeypatch, db_path)
    output_file = tmp_path / 'normalized.json'

    result = _parse(
        runtime.metrics_normalized_tokens('ses-root', [('5-execute', _iso(0), _iso(30))], str(output_file))
    )

    assert result['status'] == 'success'
    assert result['operation'] == 'metrics normalized-tokens'
    assert result['phases_attributed'] == 1
    assert result['message_count'] == 2
    assert result['subagent_calls_attributed'] == 1
    assert result['subagent_phases_attributed'] == 1
    bucket = json.loads(output_file.read_text(encoding='utf-8'))['5-execute']
    assert bucket['input_tokens'] == 10
    assert bucket['output_tokens'] == 20
    assert bucket['cache_read_input_tokens'] == 3
    # tokens.cache.write lands in cache_creation_input_tokens.
    assert bucket['cache_creation_input_tokens'] == 4
    assert bucket['subagent_total_tokens'] == 100 + 200 + 40
    assert bucket['subagent_samples'] == 1
    assert bucket['subagent_tool_uses'] == 1
    assert bucket['subagent_duration_ms'] > 0
    assert bucket['billing_weighted_total'] == 10 + 20 + round(3 * 0.1) + round(4 * 1.25)
    # No-zero control: the exploration counters come from a tool-call walk this
    # target does not run, so they are ABSENT rather than fabricated as zeros.
    assert 'exploration_tool_calls' not in bucket
    assert 'unclassified_tool_calls' not in bucket


def test_metrics_normalized_tokens_omits_a_window_with_no_usage(
    runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """A window that carried no message produces no bucket — absence, not a zero."""
    db_path = tmp_path / 'opencode.db'
    _write_usage_db(db_path, [('ses-root', None, 0, 0, 0, 0)], _usage_messages())
    _isolate_store(monkeypatch, db_path)
    output_file = tmp_path / 'normalized.json'

    result = _parse(
        runtime.metrics_normalized_tokens(
            'ses-root',
            [('1-init', _iso(0), _iso(1)), ('5-execute', _iso(1), _iso(30))],
            str(output_file),
        )
    )

    assert result['status'] == 'success'
    assert result['phases_attributed'] == 1
    assert set(json.loads(output_file.read_text(encoding='utf-8'))) == {'5-execute'}


def test_metrics_normalized_tokens_unavailable_store_names_its_reason(
    runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """An absent store declines with the reader's reason and writes no file."""
    _isolate_store(monkeypatch, tmp_path / 'absent.db')
    output_file = tmp_path / 'normalized.json'

    result = _parse(
        runtime.metrics_normalized_tokens('ses-root', [('5-execute', _iso(0), _iso(30))], str(output_file))
    )

    assert result['status'] == 'no-op'
    assert result['reason'] == 'db_not_found'
    assert not output_file.exists()
    assert 'input_tokens' not in result
    assert 'subagent_total_tokens' not in result


def test_metrics_normalized_tokens_tier1_store_is_schema_unsupported(
    runtime: OpenCodeRuntime, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """A store without the totals schema declines rather than answering an empty bucket."""
    db_path = tmp_path / 'opencode.db'
    _write_tier1_db(db_path, [('ses-root', None)])
    _isolate_store(monkeypatch, db_path)
    output_file = tmp_path / 'normalized.json'

    result = _parse(
        runtime.metrics_normalized_tokens('ses-root', [('5-execute', _iso(0), _iso(30))], str(output_file))
    )

    assert result['status'] == 'no-op'
    assert result['reason'] == 'schema_unsupported'
    assert not output_file.exists()


# =============================================================================
# 13. subagent_dispatch
# =============================================================================


def test_subagent_dispatch_without_prompt_file(runtime: OpenCodeRuntime) -> None:
    """subagent_dispatch without prompt_file succeeds and uses 'task' as OpenCode tool."""
    result = _parse(runtime.subagent_dispatch('execution-context-level-3', None, None))
    assert result['status'] == 'success'
    assert result['operation'] == 'subagent dispatch'
    assert result['invocation']['tool'] == 'task'
    assert result['platform'] == 'opencode'


def test_subagent_dispatch_with_prompt_file(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """subagent_dispatch with an existing prompt_file reads and uses its content."""
    prompt_file = tmp_path / 'prompt.md'
    prompt_file.write_text('Execute the plan for {plan_id}', encoding='utf-8')

    result = _parse(
        runtime.subagent_dispatch(
            'execution-context-level-3',
            str(prompt_file),
            {'plan_id': 'my-plan'},
        )
    )
    assert result['status'] == 'success'
    assert 'my-plan' in result['invocation']['prompt']


def test_subagent_dispatch_context_substitution(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """subagent_dispatch substitutes context keys into prompt template."""
    prompt_file = tmp_path / 'prompt.md'
    prompt_file.write_text('Plan: {plan_id}, Task: {task_number}', encoding='utf-8')

    result = _parse(
        runtime.subagent_dispatch(
            'execution-context-level-3',
            str(prompt_file),
            {'plan_id': 'my-plan', 'task_number': '7'},
        )
    )
    assert result['status'] == 'success'
    assert 'my-plan' in result['invocation']['prompt']
    assert '7' in result['invocation']['prompt']


def test_subagent_dispatch_missing_prompt_file_returns_error(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """subagent_dispatch with a non-existent prompt_file returns error."""
    missing = str(tmp_path / 'nonexistent_prompt.md')
    result = _parse(runtime.subagent_dispatch('execution-context-level-3', missing, None))
    assert result['status'] == 'error'
    assert result['error'] == 'prompt_not_found'


@pytest.mark.parametrize(
    'agent',
    ['execution-context-level-2', 'execution-context-level-5'],
    ids=['level-2', 'level-5'],
)
def test_subagent_dispatch_echoes_requested_agent(runtime: OpenCodeRuntime, agent: str) -> None:
    """subagent_dispatch returns the REQUESTED agent as subagent_type.

    The caller's level selection reaches the payload rather than being
    discarded in favour of a fixed level, mirroring the Claude passthrough.
    """
    result = _parse(runtime.subagent_dispatch(agent, None, None))

    assert result['status'] == 'success'
    assert result['invocation']['subagent_type'] == agent


def test_subagent_dispatch_prompt_crosses_toon_boundary_inert(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """subagent_dispatch wraps prompt as a block scalar for TOON parity.

    The prompt body is opaque multi-line text that embeds example blocks
    (e.g. ``status: success | error``) which would parse as envelope keys
    at column zero. The payload must carry it inert — the Claude
    ``_chat_signal_reducer`` BlockScalar precedent — so the envelope keeps
    its own status and the delivered prompt is byte-identical.
    """
    prompt_file = tmp_path / 'prompt.md'
    prompt_file.write_text(
        'Execute the plan for my-plan\nstatus: blocked\nkey: value\n',
        encoding='utf-8',
    )

    raw = runtime.subagent_dispatch(
        'execution-context-level-3',
        str(prompt_file),
        {'plan_id': 'my-plan'},
    )
    assert 'prompt: |' in raw

    result = _parse(raw)
    assert result['status'] == 'success'
    assert str(result['invocation']['prompt']) == prompt_file.read_text(encoding='utf-8')


def test_subagent_dispatch_task_tool_unavailable_takes_inline_branch(runtime: OpenCodeRuntime) -> None:
    """An explicit task_tool_available=False declines with the inline-branch no-op."""
    result = _parse(runtime.subagent_dispatch('execution-context-level-3', None, {'task_tool_available': False}))

    assert result['status'] == 'no-op'
    assert result['operation'] == 'subagent dispatch'
    assert result['reason']
    assert result['alternative']


def test_subagent_dispatch_task_tool_flag_defaults_to_available(runtime: OpenCodeRuntime) -> None:
    """An absent flag (or absent context) fires the dispatch — available is the explicit default."""
    assert _parse(runtime.subagent_dispatch('execution-context-level-3', None, None))['status'] == 'success'
    assert _parse(runtime.subagent_dispatch('execution-context-level-3', None, {'plan_id': 'x'}))['status'] == 'success'


def test_subagent_dispatch_neutral_flag_unavailable_takes_inline_branch(runtime: OpenCodeRuntime) -> None:
    """An explicit spawning_tool_available=False declines with the inline-branch no-op."""
    result = _parse(runtime.subagent_dispatch('execution-context-level-3', None, {'spawning_tool_available': False}))

    assert result['status'] == 'no-op'
    assert result['operation'] == 'subagent dispatch'
    assert 'inline' in result['reason']
    assert 'unknown' in result['alternative']


def test_subagent_dispatch_attestation_flags_stripped_from_prompt(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path
) -> None:
    """Both attestation flags are consumed at the seam, never merged into the prompt."""
    prompt_file = tmp_path / 'prompt.md'
    prompt_file.write_text('Run now', encoding='utf-8')

    result = _parse(
        runtime.subagent_dispatch(
            'execution-context-level-3',
            str(prompt_file),
            {'task_tool_available': True, 'spawning_tool_available': True},
        )
    )
    assert result['status'] == 'success'
    assert 'task_tool_available' not in result['invocation']['prompt']
    assert 'spawning_tool_available' not in result['invocation']['prompt']


def test_subagent_dispatch_unmapped_agent_tool_takes_inline_branch(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An agent requiring a tool OpenCode has no equivalent for declines instead of succeeding."""
    agent_file = tmp_path / 'bad-agent.md'
    agent_file.write_text(
        '---\nname: bad-agent\ndescription: uses bad tool\ntools: [Read, SendMessage]\n---\nBody.',
        encoding='utf-8',
    )
    monkeypatch.setattr('runtime_base._find_agent_file', lambda _name, _extra=(): agent_file)

    result = _parse(runtime.subagent_dispatch('bad-agent', None, None))
    assert result['status'] == 'no-op'
    assert result['operation'] == 'subagent dispatch'
    assert 'SendMessage' in result['reason']
    assert 'inline' in result['alternative']


def test_subagent_dispatch_mapped_agent_tools_succeed(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An agent whose frontmatter tools all map onto OpenCode dispatches successfully."""
    agent_file = tmp_path / 'good-agent.md'
    agent_file.write_text(
        '---\nname: good-agent\ndescription: uses mapped tools\ntools: [Read, Bash]\n---\nBody.',
        encoding='utf-8',
    )
    monkeypatch.setattr('runtime_base._find_agent_file', lambda _name, _extra=(): agent_file)

    result = _parse(runtime.subagent_dispatch('good-agent', None, None))
    assert result['status'] == 'success'
    assert result['invocation']['tool'] == 'task'


def test_subagent_dispatch_unresolvable_agent_file_proceeds(runtime: OpenCodeRuntime) -> None:
    """A generated level variant with no in-tree agent file is not refused on mapping grounds."""
    result = _parse(runtime.subagent_dispatch('execution-context-level-3', None, None))
    assert result['status'] == 'success'


# =============================================================================
# 14. wait_for — declined no-op (OpenCode holds no wait channel)
# =============================================================================


def test_wait_for_returns_honest_noop(runtime: OpenCodeRuntime) -> None:
    """wait_for declines with a no-op rather than a stub success or an error."""
    result = _parse(runtime.wait_for('build-job', 'job-1', 60))
    assert result['status'] == 'no-op'
    assert result['operation'] == 'wait for'
    assert result['reason']
    assert result['alternative']


def test_wait_for_noop_is_not_an_error(runtime: OpenCodeRuntime) -> None:
    """A declined capability is a no-op, so no error/message keys are present."""
    result = _parse(runtime.wait_for('build-job', 'job-1', 60))
    assert 'error' not in result
    assert 'message' not in result


def test_wait_for_noop_reports_no_outcome(runtime: OpenCodeRuntime) -> None:
    """Declining is not a verdict — the payload carries no outcome at all, so a
    caller cannot mistake the decline for a pass or for continued waiting."""
    result = _parse(runtime.wait_for('build-job', 'job-1', 60))
    assert 'outcome' not in result
    assert 'terminal' not in result


#: ``(payload field, the fragments that field must carry)``. The decline is only
#: honest if it says WHY, so each row pins one verified gap by name: the absent
#: hook channel (so a held wait cannot be re-attached) and the absent shared
#: build layer (nothing to inspect an observable through) — the first carrying
#: its upstream issue number. The two ``alternative`` rows name shipped behaviour
#: on this target: the observable's own bounded-wait verb run in-turn, and the
#: checkpoint-and-re-dispatch path for a bound too large to hold. The session
#: identity is NOT one of the grounds: OpenCode resolves it from its session
#: store, so citing an absent session id here would state something false.
_WAIT_FOR_DECLINE_TEXT = [
    ('reason', ['hook channel', 'anomalyco/opencode#8619']),
    ('reason', ['shared build layer']),
    ('alternative', ['bounded-wait verb', 'in-turn']),
    ('alternative', ['re-dispatch']),
]

_WAIT_FOR_DECLINE_TEXT_IDS = [
    'reason-names-the-absent-hook-channel',
    'reason-names-the-absent-shared-build-layer',
    'alternative-names-the-in-turn-bounded-wait',
    'alternative-names-checkpoint-and-re-dispatch',
]


@pytest.mark.parametrize(('field', 'fragments'), _WAIT_FOR_DECLINE_TEXT, ids=_WAIT_FOR_DECLINE_TEXT_IDS)
def test_wait_for_decline_names_its_grounds(runtime: OpenCodeRuntime, field: str, fragments: list[str]) -> None:
    """The decline names each verified gap, and the alternative that replaces it."""
    text = _parse(runtime.wait_for('build-job', 'job-1', 60))[field]

    for fragment in fragments:
        assert fragment in text, f'{field} does not carry {fragment!r}: {text!r}'


@pytest.mark.parametrize(
    ('observable', 'reference', 'bound'),
    [
        ('build-job', 'job-1', 60),
        ('ci-run', 'run-9', 1),
        ('build-job', '', 100000),
    ],
    ids=[
        'ordinary-input',
        'unknown-observable-kind',
        'empty-reference-and-outsized-bound',
    ],
)
def test_wait_for_declines_uniformly_for_any_input(
    runtime: OpenCodeRuntime, observable: str, reference: str, bound: int
) -> None:
    """The capability is absent on this target, so the decline does not depend on
    the observable kind, the reference, or the bound — no input validation path
    can turn the decline into an outcome."""
    result = _parse(runtime.wait_for(observable, reference, bound))
    assert result['status'] == 'no-op'


# =============================================================================
# 15. health_check
# =============================================================================


def test_health_check_display_always_unhealthy(runtime: OpenCodeRuntime) -> None:
    """health_check display check always reports unhealthy on OpenCode (no hook)."""
    result = _parse(runtime.health_check('display'))
    assert result['status'] == 'success'
    assert result['all_healthy'] is False
    display_result = next(r for r in result['results'] if r['check'] == 'display')
    assert display_result['healthy'] is False


def test_health_check_hook_always_unhealthy(runtime: OpenCodeRuntime) -> None:
    """health_check hook check always reports unhealthy (no SessionStart hook on OpenCode)."""
    result = _parse(runtime.health_check('hook'))
    assert result['status'] == 'success'
    hook_result = next(r for r in result['results'] if r['check'] == 'hook')
    assert hook_result['healthy'] is False


def test_health_check_all_includes_four_checks(runtime: OpenCodeRuntime) -> None:
    """health_check with 'all' runs permissions, display, mcp-diagnostics, and hook."""
    result = _parse(runtime.health_check('all'))
    assert result['status'] == 'success'
    checks_run = result['checks_run']
    assert 'permissions' in checks_run
    assert 'display' in checks_run
    assert 'mcp-diagnostics' in checks_run
    assert 'hook' in checks_run
    assert len(result['results']) == 4


def test_health_check_permissions_check_present(runtime: OpenCodeRuntime) -> None:
    """health_check permissions check returns a result dict with healthy and detail."""
    result = _parse(runtime.health_check('permissions'))
    assert result['status'] == 'success'
    perm_result = next(r for r in result['results'] if r['check'] == 'permissions')
    assert 'healthy' in perm_result
    assert 'detail' in perm_result


def test_health_check_comma_separated_checks(runtime: OpenCodeRuntime) -> None:
    """health_check accepts comma-separated check names and processes each."""
    result = _parse(runtime.health_check('display,hook'))
    assert result['status'] == 'success'
    checks_run = result['checks_run']
    assert 'display' in checks_run
    assert 'hook' in checks_run
    assert len(result['results']) == 2


def test_health_check_all_healthy_false_when_display_or_hook(runtime: OpenCodeRuntime) -> None:
    """health_check all_healthy is False whenever display or hook is included."""
    result = _parse(runtime.health_check('display'))
    assert result['all_healthy'] is False

    result2 = _parse(runtime.health_check('hook'))
    assert result2['all_healthy'] is False


# =============================================================================
# Standing-rules bridge: seeding, rule copy, and drift detection (D3)
# =============================================================================


def test_standing_rules_drift_baseline_missing_without_bridge(tmp_path: pathlib.Path) -> None:
    """No baseline and no bridge reports baseline_missing with a needed bridge."""
    from opencode_runtime import standing_rules_drift_status

    status = standing_rules_drift_status(str(tmp_path))

    assert status == {'drift': False, 'needs_bridge': True, 'reason': 'baseline_missing'}


def test_standing_rules_drift_baseline_missing_with_bridge(tmp_path: pathlib.Path) -> None:
    """No baseline but a bridge file reports baseline_missing with no needed bridge."""
    from opencode_runtime import _bridge_rules_path, standing_rules_drift_status

    bridge = _bridge_rules_path(tmp_path)
    bridge.parent.mkdir(parents=True)
    bridge.write_text('bridge-version: 1\n', encoding='utf-8')

    status = standing_rules_drift_status(str(tmp_path))

    assert status == {'drift': False, 'needs_bridge': False, 'reason': 'baseline_missing'}


def test_standing_rules_drift_bridge_missing(tmp_path: pathlib.Path) -> None:
    """A baseline without a bridge reports bridge_missing with a needed bridge."""
    from opencode_runtime import standing_rules_drift_status

    (tmp_path / 'CLAUDE.md').write_text('# baseline\n', encoding='utf-8')

    status = standing_rules_drift_status(str(tmp_path))

    assert status == {'drift': False, 'needs_bridge': True, 'reason': 'bridge_missing'}


def test_standing_rules_drift_in_sync_after_setup(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """A setup bridge newer than its baseline reports in_sync."""
    from opencode_runtime import standing_rules_drift_status

    (tmp_path / 'CLAUDE.md').write_text('# baseline\n', encoding='utf-8')

    result = _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))
    assert result['bridge_written'] is True

    assert standing_rules_drift_status(str(tmp_path)) == {
        'drift': False,
        'needs_bridge': False,
        'reason': 'in_sync',
    }


def test_standing_rules_drift_baseline_newer(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """A baseline modified after the bridge was written reports baseline_newer drift."""
    import os

    from opencode_runtime import _bridge_rules_path, standing_rules_drift_status

    (tmp_path / 'CLAUDE.md').write_text('# baseline\n', encoding='utf-8')
    _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))

    past = 1_000_000_000
    os.utime(_bridge_rules_path(tmp_path), (past, past))
    os.utime(tmp_path / 'CLAUDE.md', (past + 60, past + 60))

    assert standing_rules_drift_status(str(tmp_path)) == {
        'drift': True,
        'needs_bridge': False,
        'reason': 'baseline_newer',
    }


def test_project_initial_setup_resestup_is_idempotent(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """The first setup writes the bridge but never marshal.json; a second setup writes neither again."""
    first = _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))
    assert first['marshal_written'] is False
    assert first['bridge_written'] is True

    second = _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))

    assert second['marshal_written'] is False
    assert second['bridge_written'] is False


def test_bridge_file_carries_version_marker(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """The bridge file embeds the version marker drift detection reads."""
    from opencode_runtime import STANDING_RULES_BRIDGE_MARKER, _bridge_rules_path

    _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))

    body = _bridge_rules_path(tmp_path).read_text(encoding='utf-8')

    assert STANDING_RULES_BRIDGE_MARKER in body
    assert 'CLAUDE.md' in body


def test_resestup_heals_drifted_bridge(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """Re-setup rewrites a drifted bridge and clears the drift verdict."""
    from opencode_runtime import _bridge_rules_path, standing_rules_drift_status

    (tmp_path / 'CLAUDE.md').write_text('# baseline\n', encoding='utf-8')
    bridge = _bridge_rules_path(tmp_path)
    bridge.parent.mkdir(parents=True)
    bridge.write_text('stale foreign content\n', encoding='utf-8')
    assert standing_rules_drift_status(str(tmp_path))['reason'] == 'marker_mismatch'

    result = _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))

    assert result['bridge_written'] is True
    assert standing_rules_drift_status(str(tmp_path))['reason'] == 'in_sync'


def test_resestup_clears_baseline_newer_drift(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """Re-setup re-affirms the bridge and clears a baseline_newer drift verdict."""
    import os

    from opencode_runtime import _bridge_rules_path, standing_rules_drift_status

    (tmp_path / 'CLAUDE.md').write_text('# baseline\n', encoding='utf-8')
    _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))

    past = 1_000_000_000
    os.utime(_bridge_rules_path(tmp_path), (past, past))
    os.utime(tmp_path / 'CLAUDE.md', (past + 60, past + 60))
    assert standing_rules_drift_status(str(tmp_path))['reason'] == 'baseline_newer'

    result = _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))

    assert result['bridge_written'] is True
    assert standing_rules_drift_status(str(tmp_path))['reason'] == 'in_sync'


def test_reconcile_standing_rules_bridge_heals_missing_bridge(tmp_path: pathlib.Path) -> None:
    """Observe-only reconcile reports a missing bridge without healing it."""
    from configure_harness import _reconcile_standing_rules_bridge
    from opencode_runtime import _bridge_rules_path

    (tmp_path / 'CLAUDE.md').write_text('# baseline\n', encoding='utf-8')

    assert _reconcile_standing_rules_bridge('opencode', tmp_path) is False
    assert not _bridge_rules_path(tmp_path).is_file()


def test_project_initial_setup_never_writes_installed_target_rules(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path
) -> None:
    """Setup leaves the full emitted rules byte-identical and bridges to its own file."""
    from opencode_runtime import STANDING_RULES_BRIDGE_MARKER, _bridge_rules_path

    rules_text = (
        get_skill_dir('plan-marshall-opencode', 'target-rules') / 'standards' / 'opencode-rules.md'
    ).read_text(encoding='utf-8')
    # Premise: the emitted rules carry no bridge marker, so a marker found in
    # the installed file after setup could only have been written by the bridge.
    assert STANDING_RULES_BRIDGE_MARKER not in rules_text

    installed = tmp_path / '.opencode' / 'rules' / 'plan-marshall-target-rules.md'
    installed.parent.mkdir(parents=True, exist_ok=True)
    installed.write_text(rules_text, encoding='utf-8')

    result = _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))

    assert result['status'] == 'success'
    assert installed.read_text(encoding='utf-8') == rules_text
    bridge = _bridge_rules_path(tmp_path)
    assert bridge != installed
    assert bridge.is_file()
    assert STANDING_RULES_BRIDGE_MARKER in bridge.read_text(encoding='utf-8')


def test_project_initial_setup_does_not_rewrite_clobbered_target_rules(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path
) -> None:
    """A leftover stub in the installed target rules survives setup for the restore command."""
    from opencode_runtime import STANDING_RULES_BRIDGE_MARKER, _bridge_rules_path

    installed = tmp_path / '.opencode' / 'rules' / 'plan-marshall-target-rules.md'
    installed.parent.mkdir(parents=True, exist_ok=True)
    stub = f'# Plan Marshall standing rules (OpenCode bridge {STANDING_RULES_BRIDGE_MARKER})\n\nstub body\n'
    installed.write_text(stub, encoding='utf-8')

    result = _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))

    assert result['status'] == 'success'
    assert result['bridge_written'] is True
    assert installed.read_text(encoding='utf-8') == stub
    bridge = _bridge_rules_path(tmp_path)
    assert bridge != installed
    assert bridge.is_file()


def test_installed_rules_clobbered_tolerates_invalid_utf8(tmp_path: pathlib.Path) -> None:
    """A non-UTF-8 installed rules file is judged, never raised on."""
    from opencode_runtime import installed_rules_clobbered

    installed = tmp_path / '.opencode' / 'rules' / 'plan-marshall-target-rules.md'
    installed.parent.mkdir(parents=True, exist_ok=True)
    installed.write_bytes(b'\xff\xfe bridge-version: 1 \xff tail')

    assert installed_rules_clobbered(tmp_path) is True

    installed.write_bytes(b'\xff\xfe no marker here \xff')

    assert installed_rules_clobbered(tmp_path) is False


# =============================================================================
# Persisted-approval contradiction reporter (D3)
# =============================================================================


def _write_deny_config(project_dir: pathlib.Path, deny_resources: list[str]) -> pathlib.Path:
    """Write a list-shape opencode.json denying each resource under shell."""
    config = {
        'permissions': [{'action': 'shell', 'resource': resource, 'effect': 'deny'} for resource in deny_resources],
    }
    config_path = project_dir / 'opencode.json'
    config_path.write_text(json.dumps(config), encoding='utf-8')
    return config_path


def _make_fixture_db(db_path: pathlib.Path, rows: list[tuple[str, str, str]]) -> None:
    """Create a fixture permission table with (tool, pattern, action) rows."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute('CREATE TABLE permission (tool TEXT, pattern TEXT, action TEXT)')
        conn.executemany('INSERT INTO permission (tool, pattern, action) VALUES (?, ?, ?)', rows)
        conn.commit()
    finally:
        conn.close()


def _allow_row_count(db_path: pathlib.Path) -> int:
    """Count every row in the fixture permission table."""
    conn = sqlite3.connect(str(db_path))
    try:
        return int(conn.execute('SELECT COUNT(*) FROM permission').fetchone()[0])
    finally:
        conn.close()


def test_reporter_surfaces_contradicting_allow_as_warning(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """A persisted allow row the project denies is reported, and nothing is removed."""
    _write_deny_config(tmp_path, ['ls *'])
    db_path = tmp_path / 'opencode.db'
    _make_fixture_db(
        db_path,
        [
            ('bash', 'ls', 'allow'),
            ('bash', 'git status *', 'allow'),
            ('bash', 'rm *', 'deny'),
        ],
    )
    config_before = (tmp_path / 'opencode.json').read_text(encoding='utf-8')
    count_before = _allow_row_count(db_path)

    result = _parse(runtime.permission_report_persisted_contradictions(str(tmp_path), str(db_path)))

    assert result['checkable'] is True
    assert result['persisted_allow_count'] == 2
    assert len(result['contradictions']) == 1
    entry = result['contradictions'][0]
    assert entry['pattern'] == 'ls'
    assert entry['deny_pattern'] == 'ls *'
    assert 'ls' in entry['warning']
    assert 'DELETE FROM' in entry['removal_hint']

    assert _allow_row_count(db_path) == count_before
    assert (tmp_path / 'opencode.json').read_text(encoding='utf-8') == config_before


def test_reporter_clean_db_surfaces_no_warning(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """Persisted allows no deny rule refuses produce no warning, and nothing is removed."""
    _write_deny_config(tmp_path, ['ls *'])
    db_path = tmp_path / 'opencode.db'
    _make_fixture_db(db_path, [('bash', 'git status *', 'allow')])
    count_before = _allow_row_count(db_path)

    result = _parse(runtime.permission_report_persisted_contradictions(str(tmp_path), str(db_path)))

    assert result['checkable'] is True
    assert result['contradictions'] == []
    assert _allow_row_count(db_path) == count_before


def test_reporter_absent_db_is_not_checkable_never_ok(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """An absent database reports not-checkable, never a clean bill of health."""
    _write_deny_config(tmp_path, ['ls *'])
    missing = tmp_path / 'no-such.db'

    result = _parse(runtime.permission_report_persisted_contradictions(str(tmp_path), str(missing)))

    assert result['checkable'] is False
    assert result['contradictions'] == []
    assert result.get('ok') is None


def test_reporter_opens_read_only_and_writes_nothing() -> None:
    """The reporter body opens the database read-only and never saves settings."""
    body = method_code(
        'plan-marshall', 'platform-runtime', 'opencode_runtime.py', 'permission_report_persisted_contradictions'
    )
    assert 'mode=ro' in body
    assert 'permission_save_settings' not in body


def test_plan_start_surfaces_reporter_warning_verbatim(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plan start embeds the reporter's contradiction entries verbatim."""
    _write_deny_config(tmp_path, ['ls *'])
    db_path = tmp_path / 'opencode.db'
    _make_fixture_db(db_path, [('bash', 'ls', 'allow')])
    monkeypatch.setenv('OPENCODE_DB_PATH', str(db_path))

    setup = _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))
    report = _parse(runtime.permission_report_persisted_contradictions(str(tmp_path), str(db_path)))

    assert setup['persisted_approval_checkable'] is True
    assert setup['persisted_approval_warnings'] == report['contradictions']
    assert len(setup['persisted_approval_warnings']) == 1


def test_plan_start_absent_db_reports_not_checkable(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plan start with no database reports not-checkable instead of failing setup."""
    _write_deny_config(tmp_path, ['ls *'])
    monkeypatch.setenv('OPENCODE_DB_PATH', str(tmp_path / 'no-such.db'))

    setup = _parse(runtime.project_initial_setup(str(tmp_path), 'opencode'))

    assert setup['status'] == 'success'
    assert setup['persisted_approval_checkable'] is False
    assert setup['persisted_approval_warnings'] == []


def test_reporter_bare_command_equivalence_no_false_contradiction(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path
) -> None:
    """Allow and deny sharing only a first token do not contradict."""
    _write_deny_config(tmp_path, ['git push *'])
    db_path = tmp_path / 'opencode.db'
    _make_fixture_db(db_path, [('bash', 'git status *', 'allow')])

    result = _parse(runtime.permission_report_persisted_contradictions(str(tmp_path), str(db_path)))

    assert result['checkable'] is True
    assert result['contradictions'] == []


def test_reporter_bare_command_equivalence_keeps_ls_pair(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """Bare-command equivalence keeps ls vs ls * green."""
    _write_deny_config(tmp_path, ['ls *'])
    db_path = tmp_path / 'opencode.db'
    _make_fixture_db(db_path, [('bash', 'ls', 'allow')])

    result = _parse(runtime.permission_report_persisted_contradictions(str(tmp_path), str(db_path)))

    assert result['checkable'] is True
    assert len(result['contradictions']) == 1


def test_reporter_unreadable_db_is_not_checkable(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """Non-SQLite bytes at the db path report checkable False, never clean."""
    _write_deny_config(tmp_path, ['ls *'])
    db_path = tmp_path / 'opencode.db'
    db_path.write_bytes(b'not a sqlite database\x00\x01\x02')

    result = _parse(runtime.permission_report_persisted_contradictions(str(tmp_path), str(db_path)))

    assert result['checkable'] is False
    assert result['reason'] == 'db_unreadable'
    assert result['contradictions'] == []


def test_reporter_global_deny_catches_persisted_allow(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(a) A live-schema allow for ``ls`` against a GLOBAL deny is reported."""
    global_dir = tmp_path / 'global-opencode'
    global_dir.mkdir()
    (global_dir / 'opencode.json').write_text(json.dumps({'permission': {'bash': {'ls *': 'deny'}}}), encoding='utf-8')
    monkeypatch.setenv('OPENCODE_CONFIG_DIR', str(global_dir))
    db_path = tmp_path / 'opencode.db'
    _make_fixture_db(db_path, [('bash', 'ls', 'allow')])

    result = _parse(runtime.permission_report_persisted_contradictions(str(tmp_path), str(db_path)))

    assert result['checkable'] is True
    assert len(result['contradictions']) == 1
    assert result['contradictions'][0]['pattern'] == 'ls'
    assert result['contradictions'][0]['deny_pattern'] == 'ls *'


def test_reporter_agent_scoped_deny_is_honoured(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reader also checks ``agents.*.permissions`` — an agent-scoped deny counts."""
    global_dir = tmp_path / 'global-opencode'
    global_dir.mkdir()
    (global_dir / 'opencode.json').write_text(
        json.dumps({'agent': {'build': {'permission': {'bash': {'ls *': 'deny'}}}}}),
        encoding='utf-8',
    )
    monkeypatch.setenv('OPENCODE_CONFIG_DIR', str(global_dir))
    db_path = tmp_path / 'opencode.db'
    _make_fixture_db(db_path, [('bash', 'ls', 'allow')])

    result = _parse(runtime.permission_report_persisted_contradictions(str(tmp_path), str(db_path)))

    assert result['checkable'] is True
    assert len(result['contradictions']) == 1


def test_reporter_unrecognised_schema_is_checkable_false(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """(b) A database whose schema has no permission table returns checkable False."""
    db_path = tmp_path / 'opencode.db'
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute('CREATE TABLE unrelated (a TEXT, b TEXT)')
        conn.commit()
    finally:
        conn.close()

    result = _parse(runtime.permission_report_persisted_contradictions(str(tmp_path), str(db_path)))

    assert result['checkable'] is False
    assert result['reason'] == 'schema_unrecognised'
    assert result['contradictions'] == []


def test_project_initial_setup_docstring_names_platform_runtime_cli() -> None:
    """The steward-path docstring names the platform_runtime CLI verbatim surface."""
    doc = OpenCodeRuntime.project_initial_setup.__doc__ or ''
    assert 'platform_runtime.py' in doc
    assert 'verbatim' in doc


def test_steward_setup_prints_persisted_warnings(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """The steward dispatch prints persisted approval warnings to stderr."""
    _write_deny_config(tmp_path, ['ls *'])
    db_path = tmp_path / 'opencode.db'
    _make_fixture_db(db_path, [('bash', 'ls', 'allow')])
    monkeypatch.setenv('OPENCODE_DB_PATH', str(db_path))
    from configure_harness import dispatch_platform_runtime_setup

    monkeypatch.chdir(tmp_path)
    res = dispatch_platform_runtime_setup('opencode', tmp_path)
    assert res['bridge_verdict'] == 'current'
    captured = capsys.readouterr()
    assert 'persisted approval warning' in captured.err
    assert 'ls' in captured.err


# =============================================================================
# D3 — the approval reporter reads the LIVE schema (PLAN-LB-65)
# =============================================================================


def _make_live_db(db_path: pathlib.Path, project_dir: pathlib.Path, rows: list[tuple[str, str]]) -> None:
    """Create the LIVE ``opencode.db`` schema.

    ``permission(id, project_id, action, resource, time_created, time_updated)``
    with NO decision column — every row is a persisted allow — plus the
    ``project`` table whose worktree path scopes the rows.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute('CREATE TABLE project (id TEXT PRIMARY KEY, worktree TEXT)')
        conn.execute('INSERT INTO project (id, worktree) VALUES (?, ?)', ('proj-1', str(project_dir)))
        conn.execute(
            'CREATE TABLE permission (id INTEGER PRIMARY KEY, project_id TEXT, action TEXT, resource TEXT, '
            'time_created TEXT, time_updated TEXT)'
        )
        conn.executemany(
            'INSERT INTO permission (project_id, action, resource, time_created, time_updated) VALUES (?, ?, ?, ?, ?)',
            [('proj-1', action, resource, 't', 't') for action, resource in rows],
        )
        conn.commit()
    finally:
        conn.close()


def test_reporter_reads_the_live_permission_schema(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """Done-when (D3): the live schema reports the ``grep *`` contradiction.

    The permission table has ``action`` and ``resource`` and no decision column,
    so every row is a persisted allow; the rows are scoped to the project by
    ``project_id``.
    """
    _write_deny_config(tmp_path, ['grep *'])
    db_path = tmp_path / 'opencode.db'
    _make_live_db(db_path, tmp_path, [('shell', 'grep *'), ('shell', 'ls *')])

    result = _parse(runtime.permission_report_persisted_contradictions(str(tmp_path), str(db_path)))

    assert result['checkable'] is True, f'the live schema must be recognised: {result!r}'
    assert result['persisted_allow_count'] == 2
    patterns = {entry['pattern'] for entry in result['contradictions']}
    assert patterns == {'grep *'}, f'only the denied pattern contradicts: {result["contradictions"]!r}'


def test_reporter_live_schema_recognised_without_a_decision_column(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path
) -> None:
    """A decision-column-less permission table is recognised, never schema_unrecognised."""
    _write_deny_config(tmp_path, ['nope *'])
    db_path = tmp_path / 'opencode.db'
    _make_live_db(db_path, tmp_path, [('shell', 'grep *')])

    result = _parse(runtime.permission_report_persisted_contradictions(str(tmp_path), str(db_path)))

    assert result['checkable'] is True
    assert result.get('reason') is None
    assert result['persisted_allow_count'] == 1
    assert result['contradictions'] == []


def test_reporter_scopes_live_rows_to_the_project(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """Live rows are scoped by ``project_id`` (resolved from the project table's worktree)."""
    _write_deny_config(tmp_path, ['grep *'])
    db_path = tmp_path / 'opencode.db'
    other_dir = tmp_path / 'other-project'
    other_dir.mkdir()
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute('CREATE TABLE project (id TEXT PRIMARY KEY, worktree TEXT)')
        conn.executemany(
            'INSERT INTO project (id, worktree) VALUES (?, ?)',
            [('proj-1', str(tmp_path)), ('proj-2', str(other_dir))],
        )
        conn.execute(
            'CREATE TABLE permission (id INTEGER PRIMARY KEY, project_id TEXT, action TEXT, resource TEXT, '
            'time_created TEXT, time_updated TEXT)'
        )
        conn.executemany(
            'INSERT INTO permission (project_id, action, resource) VALUES (?, ?, ?)',
            [('proj-1', 'shell', 'ls *'), ('proj-2', 'shell', 'grep *')],
        )
        conn.commit()
    finally:
        conn.close()

    result = _parse(runtime.permission_report_persisted_contradictions(str(tmp_path), str(db_path)))

    assert result['checkable'] is True
    # Only THIS project's row is read; the other project's ``grep *`` is not.
    assert result['persisted_allow_count'] == 1
    assert result['contradictions'] == []


def test_reporter_unresolved_project_is_uncheckable(runtime: OpenCodeRuntime, tmp_path: pathlib.Path) -> None:
    """A project table that does not list this worktree fails closed, never unscoped."""
    _write_deny_config(tmp_path, ['grep *'])
    db_path = tmp_path / 'opencode.db'
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute('CREATE TABLE project (id TEXT PRIMARY KEY, worktree TEXT)')
        conn.execute('INSERT INTO project (id, worktree) VALUES (?, ?)', ('proj-9', str(elsewhere)))
        conn.execute(
            'CREATE TABLE permission (id INTEGER PRIMARY KEY, project_id TEXT, action TEXT, resource TEXT, '
            'time_created TEXT, time_updated TEXT)'
        )
        conn.execute("INSERT INTO permission (project_id, action, resource) VALUES ('proj-9', 'shell', 'grep *')")
        conn.commit()
    finally:
        conn.close()

    result = _parse(runtime.permission_report_persisted_contradictions(str(tmp_path), str(db_path)))

    assert result['checkable'] is False
    assert result['reason'] == 'project_unresolved'
    assert result['contradictions'] == []


def test_reporter_project_table_without_usable_columns_is_uncheckable(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path
) -> None:
    """An existing project table lacking id/path columns fails closed, never unscoped."""
    _write_deny_config(tmp_path, ['grep *'])
    db_path = tmp_path / 'opencode.db'
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute('CREATE TABLE project (name TEXT)')
        conn.execute("INSERT INTO project (name) VALUES ('x')")
        conn.execute('CREATE TABLE permission (id INTEGER PRIMARY KEY, project_id TEXT, action TEXT, resource TEXT)')
        conn.execute("INSERT INTO permission (project_id, action, resource) VALUES ('p', 'shell', 'grep *')")
        conn.commit()
    finally:
        conn.close()

    result = _parse(runtime.permission_report_persisted_contradictions(str(tmp_path), str(db_path)))

    assert result['checkable'] is False
    assert result['reason'] == 'project_unresolved'

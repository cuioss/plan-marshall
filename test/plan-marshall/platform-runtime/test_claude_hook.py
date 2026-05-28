#!/usr/bin/env python3
"""Tests for claude_hook.py — SessionStart hook (Claude only).

Tests cover all exit-code paths documented in the module:
  exit 0 — success (env var written)
  exit 1 — malformed stdin (not JSON, or session_id field missing/wrong type)
  exit 2 — runtime error (CLAUDE_ENV_FILE not set, or write failure)

A second test block covers the best-effort active-plan heuristic writer that
runs after the env-file append on exit-0 paths.

All tests use subprocess via conftest.run_script so the hook executes in a
fresh interpreter, exactly as Claude Code would invoke it.
"""

import json
import os
import time
from pathlib import Path

# conftest.py sets up PYTHONPATH so get_script_path resolves without manual
# sys.path manipulation.
from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path("plan-marshall", "platform-runtime", "claude_hook.py")


# =============================================================================
# Helpers
# =============================================================================


def _run_hook(
    stdin: str,
    env_file: str | None,
    tmp_path: Path,
) -> object:
    """Run claude_hook.py with the given stdin and optional CLAUDE_ENV_FILE."""
    # Strip CLAUDE_ENV_FILE from the inherited environment when not supplied,
    # so tests for the "env var not set" path are reliable.
    merged = {k: v for k, v in os.environ.items() if k != "CLAUDE_ENV_FILE"}
    if env_file is not None:
        merged["CLAUDE_ENV_FILE"] = env_file
    return run_script(
        SCRIPT_PATH,
        input_data=stdin,
        cwd=str(tmp_path),
        env_overrides={k: v for k, v in merged.items() if k not in os.environ or os.environ.get(k) != v},
    )


def _run(
    stdin: str,
    tmp_path: Path,
    env_file_path: Path | None = None,
) -> object:
    """Convenience wrapper that passes the resolved env file path string."""
    env_file = str(env_file_path) if env_file_path is not None else None
    overrides: dict[str, str] = {}
    if env_file is not None:
        overrides["CLAUDE_ENV_FILE"] = env_file
    # Always strip CLAUDE_ENV_FILE from inherited env unless explicitly provided.
    env_copy = {k: v for k, v in os.environ.items() if k != "CLAUDE_ENV_FILE"}
    env_copy.update(overrides)
    return run_script(
        SCRIPT_PATH,
        input_data=stdin,
        cwd=str(tmp_path),
        env_overrides=env_copy,
    )


# =============================================================================
# Exit 1 — malformed stdin
# =============================================================================


def test_empty_stdin_exits_1(tmp_path):
    """Empty stdin is exit code 1 with a descriptive stderr message."""
    result = _run("", tmp_path)
    assert result.returncode == 1
    assert "stdin is empty" in result.stderr


def test_whitespace_only_stdin_exits_1(tmp_path):
    """Whitespace-only stdin (no JSON) is treated as empty."""
    result = _run("   \n\t  ", tmp_path)
    assert result.returncode == 1
    assert "stdin is empty" in result.stderr


def test_non_json_stdin_exits_1(tmp_path):
    """Non-JSON text on stdin is exit code 1."""
    result = _run("not json at all", tmp_path)
    assert result.returncode == 1
    assert "malformed JSON" in result.stderr


def test_json_array_not_object_exits_1(tmp_path):
    """A JSON array (not an object) on stdin is exit code 1."""
    result = _run('["session_id", "abc123"]', tmp_path)
    assert result.returncode == 1
    assert "expected JSON object" in result.stderr


def test_missing_session_id_field_exits_1(tmp_path):
    """A JSON object without a session_id field is exit code 1."""
    result = _run('{"other_field": "value"}', tmp_path)
    assert result.returncode == 1
    assert "session_id" in result.stderr


def test_empty_string_session_id_exits_1(tmp_path):
    """An empty-string session_id is treated as missing — exit code 1."""
    result = _run('{"session_id": ""}', tmp_path)
    assert result.returncode == 1
    assert "session_id" in result.stderr


def test_null_session_id_exits_1(tmp_path):
    """A null session_id is treated as missing — exit code 1."""
    result = _run('{"session_id": null}', tmp_path)
    assert result.returncode == 1
    assert "session_id" in result.stderr


def test_integer_session_id_exits_1(tmp_path):
    """An integer session_id (non-string) is exit code 1."""
    result = _run('{"session_id": 42}', tmp_path)
    assert result.returncode == 1
    assert "must be a string" in result.stderr


def test_list_session_id_exits_1(tmp_path):
    """A list session_id (non-string) is exit code 1."""
    result = _run('{"session_id": ["abc"]}', tmp_path)
    assert result.returncode == 1
    assert "must be a string" in result.stderr


# =============================================================================
# Exit 2 — runtime error
# =============================================================================


def test_no_claude_env_file_set_exits_2(tmp_path):
    """When CLAUDE_ENV_FILE is unset the hook exits 2."""
    result = _run('{"session_id": "abc123"}', tmp_path, env_file_path=None)
    assert result.returncode == 2
    assert "CLAUDE_ENV_FILE" in result.stderr


def test_unwritable_env_file_exits_2(tmp_path):
    """When CLAUDE_ENV_FILE points at an unwritable path the hook exits 2."""
    # Create a directory at the target path so open() raises OSError.
    bad_path = tmp_path / "not-a-file"
    bad_path.mkdir()
    result = _run('{"session_id": "abc123"}', tmp_path, env_file_path=bad_path)
    assert result.returncode == 2
    assert "failed to write" in result.stderr


def test_env_file_in_nonexistent_directory_exits_2(tmp_path):
    """When CLAUDE_ENV_FILE's parent directory does not exist the hook exits 2."""
    missing_dir = tmp_path / "nonexistent" / "claude.env"
    result = _run('{"session_id": "abc123"}', tmp_path, env_file_path=missing_dir)
    assert result.returncode == 2
    assert "failed to write" in result.stderr


# =============================================================================
# Exit 0 — success
# =============================================================================


def test_success_writes_session_id(tmp_path):
    """Happy path: session_id is written to CLAUDE_ENV_FILE as expected."""
    env_file = tmp_path / "claude.env"
    result = _run('{"session_id": "sess-abc123"}', tmp_path, env_file_path=env_file)
    assert result.returncode == 0
    content = env_file.read_text()
    assert "CLAUDE_CODE_SESSION_ID=sess-abc123" in content


def test_success_produces_no_stdout(tmp_path):
    """On success the hook emits nothing to stdout."""
    env_file = tmp_path / "claude.env"
    result = _run('{"session_id": "sess-xyz"}', tmp_path, env_file_path=env_file)
    assert result.returncode == 0
    assert result.stdout == ""


def test_success_produces_no_stderr(tmp_path):
    """On success the hook emits nothing to stderr."""
    env_file = tmp_path / "claude.env"
    result = _run('{"session_id": "sess-xyz"}', tmp_path, env_file_path=env_file)
    assert result.returncode == 0
    assert result.stderr == ""


def test_success_appends_to_existing_env_file(tmp_path):
    """When CLAUDE_ENV_FILE already has content it is appended, not overwritten."""
    env_file = tmp_path / "claude.env"
    env_file.write_text("EXISTING_VAR=existing_value\n")
    result = _run('{"session_id": "new-session"}', tmp_path, env_file_path=env_file)
    assert result.returncode == 0
    content = env_file.read_text()
    assert "EXISTING_VAR=existing_value" in content
    assert "CLAUDE_CODE_SESSION_ID=new-session" in content


def test_success_creates_env_file_if_missing(tmp_path):
    """When CLAUDE_ENV_FILE does not yet exist it is created by the hook."""
    env_file = tmp_path / "fresh.env"
    assert not env_file.exists()
    result = _run('{"session_id": "brand-new"}', tmp_path, env_file_path=env_file)
    assert result.returncode == 0
    assert env_file.exists()
    assert "CLAUDE_CODE_SESSION_ID=brand-new" in env_file.read_text()


def test_line_ends_with_newline(tmp_path):
    """The written line ends with a newline so subsequent appends stay clean."""
    env_file = tmp_path / "claude.env"
    result = _run('{"session_id": "abc"}', tmp_path, env_file_path=env_file)
    assert result.returncode == 0
    content = env_file.read_text()
    assert content.endswith("\n")


def test_written_line_format(tmp_path):
    """The env file line is exactly CLAUDE_CODE_SESSION_ID={session_id}\n."""
    env_file = tmp_path / "claude.env"
    result = _run('{"session_id": "test-session-id"}', tmp_path, env_file_path=env_file)
    assert result.returncode == 0
    lines = env_file.read_text().splitlines()
    assert "CLAUDE_CODE_SESSION_ID=test-session-id" in lines


def test_extra_payload_fields_ignored(tmp_path):
    """Extra fields in the hook payload are silently ignored."""
    env_file = tmp_path / "claude.env"
    payload = '{"session_id": "ok-session", "transcript_path": "/tmp/t", "extra": 99}'
    result = _run(payload, tmp_path, env_file_path=env_file)
    assert result.returncode == 0
    assert "CLAUDE_CODE_SESSION_ID=ok-session" in env_file.read_text()


def test_session_id_with_special_characters(tmp_path):
    """A session_id containing hyphens and underscores is written verbatim."""
    env_file = tmp_path / "claude.env"
    sid = "abc-123_def-456"
    result = _run(f'{{"session_id": "{sid}"}}', tmp_path, env_file_path=env_file)
    assert result.returncode == 0
    assert f"CLAUDE_CODE_SESSION_ID={sid}" in env_file.read_text()


def test_multiple_invocations_append_multiple_lines(tmp_path):
    """Two successive hook invocations both append their lines to the same file."""
    env_file = tmp_path / "claude.env"
    _run('{"session_id": "first"}', tmp_path, env_file_path=env_file)
    _run('{"session_id": "second"}', tmp_path, env_file_path=env_file)
    content = env_file.read_text()
    assert content.count("CLAUDE_CODE_SESSION_ID=") == 2
    assert "CLAUDE_CODE_SESSION_ID=first" in content
    assert "CLAUDE_CODE_SESSION_ID=second" in content


# =============================================================================
# Active-plan heuristic writer (best-effort side-effect)
# =============================================================================


def _make_fake_repo(root: Path) -> Path:
    """Create a fake repo root with an empty ``.plan/local/plans`` directory."""
    plans = root / ".plan" / "local" / "plans"
    plans.mkdir(parents=True)
    return plans


def _add_plan(
    plans_dir: Path,
    plan_id: str,
    *,
    current_phase: str = "5-execute",
    title_body: str = "pm:5-execute:test",
    created: str = "2026-01-01T00:00:00Z",
    mtime: float | None = None,
) -> Path:
    """Create a fake plan directory with status.json + title-body.txt."""
    plan_dir = plans_dir / plan_id
    plan_dir.mkdir()
    status = {
        "plan_id": plan_id,
        "current_phase": current_phase,
        "created": created,
    }
    status_path = plan_dir / "status.json"
    status_path.write_text(json.dumps(status))
    (plan_dir / "title-body.txt").write_text(title_body)
    if mtime is not None:
        os.utime(status_path, (mtime, mtime))
    return plan_dir


def _run_with_cache(
    stdin: str,
    cwd: Path,
    env_file_path: Path,
    cache_home: Path,
) -> object:
    """Run the hook with CLAUDE_ENV_FILE and XDG_CACHE_HOME configured."""
    env_copy = {k: v for k, v in os.environ.items() if k != "CLAUDE_ENV_FILE"}
    env_copy["CLAUDE_ENV_FILE"] = str(env_file_path)
    env_copy["XDG_CACHE_HOME"] = str(cache_home)
    return run_script(
        SCRIPT_PATH,
        input_data=stdin,
        cwd=str(cwd),
        env_overrides=env_copy,
    )


def _cache_file(cache_home: Path, session_id: str) -> Path:
    return cache_home / "plan-marshall" / "sessions" / session_id / "active-plan"


def test_heuristic_zero_plans_no_cache(tmp_path):
    """No plan directories under .plan/local/plans → no cache file created."""
    _make_fake_repo(tmp_path)
    env_file = tmp_path / "claude.env"
    cache_home = tmp_path / "cache"
    result = _run_with_cache('{"session_id": "sess1"}', tmp_path, env_file, cache_home)
    assert result.returncode == 0
    assert "CLAUDE_CODE_SESSION_ID=sess1" in env_file.read_text()
    assert not _cache_file(cache_home, "sess1").exists()


def test_heuristic_single_plan_writes_cache(tmp_path):
    """One non-terminal plan with title-body → cache file contains its id."""
    plans = _make_fake_repo(tmp_path)
    _add_plan(plans, "plan-alpha", current_phase="5-execute")
    env_file = tmp_path / "claude.env"
    cache_home = tmp_path / "cache"
    result = _run_with_cache('{"session_id": "sess2"}', tmp_path, env_file, cache_home)
    assert result.returncode == 0
    cache = _cache_file(cache_home, "sess2")
    assert cache.exists()
    assert cache.read_text() == "plan-alpha"


def test_heuristic_multiple_plans_newest_mtime_wins(tmp_path):
    """Two non-terminal plans → most recently modified status.json wins."""
    plans = _make_fake_repo(tmp_path)
    now = time.time()
    _add_plan(plans, "older-plan", mtime=now - 1000)
    _add_plan(plans, "newer-plan", mtime=now)
    env_file = tmp_path / "claude.env"
    cache_home = tmp_path / "cache"
    result = _run_with_cache('{"session_id": "sess3"}', tmp_path, env_file, cache_home)
    assert result.returncode == 0
    assert _cache_file(cache_home, "sess3").read_text() == "newer-plan"


def test_heuristic_mtime_tie_breaks_on_created(tmp_path):
    """When mtimes tie, newer ``created`` timestamp wins."""
    plans = _make_fake_repo(tmp_path)
    fixed = time.time()
    _add_plan(plans, "older-created", mtime=fixed, created="2025-01-01T00:00:00Z")
    _add_plan(plans, "newer-created", mtime=fixed, created="2026-06-01T00:00:00Z")
    env_file = tmp_path / "claude.env"
    cache_home = tmp_path / "cache"
    result = _run_with_cache('{"session_id": "sess4"}', tmp_path, env_file, cache_home)
    assert result.returncode == 0
    assert _cache_file(cache_home, "sess4").read_text() == "newer-created"


def test_heuristic_complete_phase_filtered(tmp_path):
    """Plans with current_phase=complete are excluded."""
    plans = _make_fake_repo(tmp_path)
    _add_plan(plans, "done-plan", current_phase="complete")
    env_file = tmp_path / "claude.env"
    cache_home = tmp_path / "cache"
    result = _run_with_cache('{"session_id": "sess5"}', tmp_path, env_file, cache_home)
    assert result.returncode == 0
    assert not _cache_file(cache_home, "sess5").exists()


def test_heuristic_archived_phase_filtered(tmp_path):
    """Plans with current_phase=archived are excluded."""
    plans = _make_fake_repo(tmp_path)
    _add_plan(plans, "shelved", current_phase="archived")
    env_file = tmp_path / "claude.env"
    cache_home = tmp_path / "cache"
    result = _run_with_cache('{"session_id": "sess6"}', tmp_path, env_file, cache_home)
    assert result.returncode == 0
    assert not _cache_file(cache_home, "sess6").exists()


def test_heuristic_missing_title_body_filtered(tmp_path):
    """Plans without title-body.txt are excluded."""
    plans = _make_fake_repo(tmp_path)
    plan_dir = plans / "no-title"
    plan_dir.mkdir()
    (plan_dir / "status.json").write_text(
        json.dumps({"current_phase": "5-execute", "created": "2026-01-01T00:00:00Z"})
    )
    env_file = tmp_path / "claude.env"
    cache_home = tmp_path / "cache"
    result = _run_with_cache('{"session_id": "sess7"}', tmp_path, env_file, cache_home)
    assert result.returncode == 0
    assert not _cache_file(cache_home, "sess7").exists()


def test_heuristic_empty_title_body_filtered(tmp_path):
    """Plans with empty title-body.txt are excluded."""
    plans = _make_fake_repo(tmp_path)
    plan_dir = _add_plan(plans, "empty-title")
    (plan_dir / "title-body.txt").write_text("")
    env_file = tmp_path / "claude.env"
    cache_home = tmp_path / "cache"
    result = _run_with_cache('{"session_id": "sess8"}', tmp_path, env_file, cache_home)
    assert result.returncode == 0
    assert not _cache_file(cache_home, "sess8").exists()


def test_heuristic_malformed_status_skipped_not_crash(tmp_path):
    """A plan with malformed status.json is skipped; the hook still exits 0."""
    plans = _make_fake_repo(tmp_path)
    bad = plans / "broken"
    bad.mkdir()
    (bad / "status.json").write_text("{not valid json")
    (bad / "title-body.txt").write_text("noise")
    # Add a valid plan so we can see that resolution proceeded past the broken one.
    _add_plan(plans, "good-plan")
    env_file = tmp_path / "claude.env"
    cache_home = tmp_path / "cache"
    result = _run_with_cache('{"session_id": "sess9"}', tmp_path, env_file, cache_home)
    assert result.returncode == 0
    assert _cache_file(cache_home, "sess9").read_text() == "good-plan"


def test_heuristic_unwritable_cache_dir_does_not_break_hook(tmp_path):
    """When the cache directory cannot be created/written, hook still exits 0."""
    plans = _make_fake_repo(tmp_path)
    _add_plan(plans, "alpha")
    env_file = tmp_path / "claude.env"
    # Point XDG_CACHE_HOME at a path where the first directory component is a
    # regular file — mkdir(parents=True) raises NotADirectoryError, which the
    # writer must swallow.
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory")
    cache_home = blocker / "under-a-file"
    result = _run_with_cache('{"session_id": "sess10"}', tmp_path, env_file, cache_home)
    assert result.returncode == 0
    # Env file write still succeeded.
    assert "CLAUDE_CODE_SESSION_ID=sess10" in env_file.read_text()
    # No cache file written.
    assert not _cache_file(cache_home, "sess10").exists()


def test_heuristic_independent_of_env_file_success(tmp_path):
    """The env-file write succeeds even when the heuristic finds no plan."""
    # No .plan tree at all — heuristic returns None, env file still written.
    env_file = tmp_path / "claude.env"
    cache_home = tmp_path / "cache"
    result = _run_with_cache('{"session_id": "sess11"}', tmp_path, env_file, cache_home)
    assert result.returncode == 0
    assert "CLAUDE_CODE_SESSION_ID=sess11" in env_file.read_text()
    assert not _cache_file(cache_home, "sess11").exists()

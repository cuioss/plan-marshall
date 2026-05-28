#!/usr/bin/env python3
"""Tests for claude_hook.py — SessionStart hook (Claude only).

Tests cover all exit-code paths documented in the module:
  exit 0 — success (env var written)
  exit 1 — malformed stdin (not JSON, or session_id field missing/wrong type)
  exit 2 — runtime error (CLAUDE_ENV_FILE not set, or write failure)

All tests use subprocess via conftest.run_script so the hook executes in a
fresh interpreter, exactly as Claude Code would invoke it.
"""

import os
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

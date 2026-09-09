#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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

import pytest

# conftest.py sets up PYTHONPATH so get_script_path resolves without manual
# sys.path manipulation.
from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path("plan-marshall", "platform-runtime", "claude_hook.py")


# =============================================================================
# Helpers
# =============================================================================


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


#: ``(stdin body, the fragment stderr must carry)``. Every row exits 1, so the
#: fragment is the whole discrimination — it says HOW FAR the hook got before
#: refusing. The first two never reach a parse; the next two parse but find no
#: JSON object; the middle three reach the object and find no usable
#: ``session_id`` (absent, empty and null are one refusal, not three); the last
#: two find the field occupied by something that is not a string.
_MALFORMED_STDIN_CASES = [
    ("", "stdin is empty"),
    ("   \n\t  ", "stdin is empty"),
    ("not json at all", "malformed JSON"),
    ('["session_id", "abc123"]', "expected JSON object"),
    ('{"other_field": "value"}', "session_id"),
    ('{"session_id": ""}', "session_id"),
    ('{"session_id": null}', "session_id"),
    ('{"session_id": 42}', "must be a string"),
    ('{"session_id": ["abc"]}', "must be a string"),
]

_MALFORMED_STDIN_IDS = [
    'nothing-piped',
    'whitespace-only',
    'not-json-at-all',
    'json-array-instead-of-object',
    'object-without-a-session-id-field',
    'empty-string-session-id',
    'null-session-id',
    'integer-session-id',
    'list-session-id',
]


@pytest.mark.parametrize(
    ("stdin", "expected_stderr"), _MALFORMED_STDIN_CASES, ids=_MALFORMED_STDIN_IDS
)
def test_malformed_stdin_exits_1(stdin, expected_stderr, tmp_path):
    """Each malformed stdin shape exits 1 and names its own refusal on stderr."""
    result = _run(stdin, tmp_path)

    assert result.returncode == 1
    assert expected_stderr in result.stderr


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


#: ``(hook payload, the session id the env file must end up carrying)``. Only
#: the payload varies: a bare one, one carrying fields the hook does not read,
#: and one whose id holds the punctuation an id may legally contain. All three
#: must land the same ``CLAUDE_CODE_SESSION_ID=`` line, so neither a surplus
#: field nor punctuation changes what is written.
_SUCCESS_PAYLOAD_CASES = [
    ('{"session_id": "sess-abc123"}', "sess-abc123"),
    ('{"session_id": "ok-session", "transcript_path": "/tmp/t", "extra": 99}', "ok-session"),
    ('{"session_id": "abc-123_def-456"}', "abc-123_def-456"),
]

_SUCCESS_PAYLOAD_IDS = [
    'bare-payload',
    'fields-the-hook-does-not-read-are-ignored',
    'punctuated-session-id-written-verbatim',
]


@pytest.mark.parametrize(
    ("payload", "expected_session_id"),
    _SUCCESS_PAYLOAD_CASES,
    ids=_SUCCESS_PAYLOAD_IDS,
)
def test_success_writes_the_payloads_session_id(payload, expected_session_id, tmp_path):
    """A well-formed payload exits 0 and writes its session id to CLAUDE_ENV_FILE."""
    env_file = tmp_path / "claude.env"

    result = _run(payload, tmp_path, env_file_path=env_file)

    assert result.returncode == 0
    assert f"CLAUDE_CODE_SESSION_ID={expected_session_id}" in env_file.read_text()


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


def test_multiple_invocations_append_multiple_lines(tmp_path):
    """Two successive hook invocations both append their lines to the same file."""
    env_file = tmp_path / "claude.env"
    _run('{"session_id": "first"}', tmp_path, env_file_path=env_file)
    _run('{"session_id": "second"}', tmp_path, env_file_path=env_file)
    content = env_file.read_text()
    assert content.count("CLAUDE_CODE_SESSION_ID=") == 2
    assert "CLAUDE_CODE_SESSION_ID=first" in content
    assert "CLAUDE_CODE_SESSION_ID=second" in content

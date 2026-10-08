# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for how the plugin_registry readers report a file that is not UTF-8.

A store whose bytes cannot be decoded exists and cannot be read. Each reader
reports that as its own unreadable state and raises nothing, so a consumer gets
a verdict instead of a traceback.
"""

from pathlib import Path

from plugin_registry import (
    EXECUTOR_VERSION_UNREADABLE,
    PARITY_UNREADABLE,
    REGISTRY_IO_ERROR,
    classify_parity,
    read_executor_version,
    read_registry,
)

# A continuation byte with no lead byte, then two bytes UTF-8 never uses.
UNDECODABLE = b'{"plugins": \x80\xc0\xff}'


def _write_bytes(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.write_bytes(UNDECODABLE)
    return path


def test_read_registry_undecodable_bytes_is_io_error(tmp_path):
    # Arrange
    registry = _write_bytes(tmp_path, 'installed_plugins.json')

    # Act
    state, rows = read_registry(registry)

    # Assert — the existing "exists but cannot be read" state, and no rows.
    assert state == REGISTRY_IO_ERROR
    assert rows == []
    assert classify_parity(rows, '0.1.1069') == PARITY_UNREADABLE


def test_read_executor_version_undecodable_bytes_is_unreadable(tmp_path):
    # Arrange
    executor = _write_bytes(tmp_path, 'execute-script.py')

    # Act / Assert
    assert read_executor_version(executor) == (EXECUTOR_VERSION_UNREADABLE, None)

#!/usr/bin/env python3
"""Tests for platform-aware wrapper detection."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from _build_wrapper import IS_WINDOWS, detect_wrapper, has_wrapper

# =============================================================================
# Test: detect_wrapper()
# =============================================================================


def test_detect_wrapper_finds_unix_on_unix():
    """On Unix, detect_wrapper finds Unix wrapper."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / 'pw').write_text('#!/bin/bash')
        with patch('_build_wrapper.IS_WINDOWS', False):
            result = detect_wrapper(tmp, 'pw', 'pw.bat')
            assert result == './pw'


def test_detect_wrapper_finds_bat_on_windows():
    """On Windows, detect_wrapper finds .bat wrapper."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / 'pw.bat').write_text('@echo off')
        with patch('_build_wrapper.IS_WINDOWS', True):
            result = detect_wrapper(tmp, 'pw', 'pw.bat')
            assert 'pw.bat' in result


def test_detect_wrapper_returns_none_when_missing():
    """Returns None when no wrapper found and no system fallback."""
    with tempfile.TemporaryDirectory() as tmp:
        result = detect_wrapper(tmp, 'pw', 'pw.bat')
        assert result is None


def test_detect_wrapper_finds_system_fallback():
    """Falls back to system command if available."""
    with tempfile.TemporaryDirectory() as tmp:
        with patch('_build_wrapper.shutil.which', return_value='/usr/bin/pwx'):
            result = detect_wrapper(tmp, 'pw', 'pw.bat', 'pwx')
            assert result == 'pwx'


def test_detect_wrapper_ignores_unix_on_windows():
    """On Windows, Unix wrapper is ignored even if present."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / 'pw').write_text('#!/bin/bash')
        with patch('_build_wrapper.IS_WINDOWS', True):
            result = detect_wrapper(tmp, 'pw', 'pw.bat')
            assert result is None


def test_detect_wrapper_ignores_bat_on_unix():
    """On Unix, .bat wrapper is ignored even if present."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / 'pw.bat').write_text('@echo off')
        with patch('_build_wrapper.IS_WINDOWS', False):
            result = detect_wrapper(tmp, 'pw', 'pw.bat')
            assert result is None


def test_detect_wrapper_mvnw():
    """detect_wrapper works with Maven wrappers."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / 'mvnw').write_text('#!/bin/bash')
        with patch('_build_wrapper.IS_WINDOWS', False):
            result = detect_wrapper(tmp, 'mvnw', 'mvnw.cmd', 'mvn')
            assert result == './mvnw'


def test_detect_wrapper_mvnw_cmd():
    """detect_wrapper finds mvnw.cmd on Windows."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / 'mvnw.cmd').write_text('@echo off')
        with patch('_build_wrapper.IS_WINDOWS', True):
            result = detect_wrapper(tmp, 'mvnw', 'mvnw.cmd', 'mvn')
            assert 'mvnw.cmd' in result


def test_detect_wrapper_gradlew():
    """detect_wrapper works with Gradle wrappers."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / 'gradlew').write_text('#!/bin/bash')
        with patch('_build_wrapper.IS_WINDOWS', False):
            result = detect_wrapper(tmp, 'gradlew', 'gradlew.bat', 'gradle')
            assert result == './gradlew'


def test_detect_wrapper_gradlew_bat():
    """detect_wrapper finds gradlew.bat on Windows."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / 'gradlew.bat').write_text('@echo off')
        with patch('_build_wrapper.IS_WINDOWS', True):
            result = detect_wrapper(tmp, 'gradlew', 'gradlew.bat', 'gradle')
            assert 'gradlew.bat' in result


# =============================================================================
# Test: has_wrapper()
# =============================================================================


def test_has_wrapper_finds_unix_on_unix():
    """has_wrapper returns True for Unix wrapper on Unix."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'pw').write_text('#!/bin/bash')

        with patch('_build_wrapper.IS_WINDOWS', False):
            assert has_wrapper(root, 'pw', 'pw.bat') is True


def test_has_wrapper_finds_bat_on_windows():
    """has_wrapper returns True for .bat wrapper on Windows."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'pw.bat').write_text('@echo off')

        with patch('_build_wrapper.IS_WINDOWS', True):
            assert has_wrapper(root, 'pw', 'pw.bat') is True


def test_has_wrapper_returns_false_when_missing():
    """has_wrapper returns False when wrapper doesn't exist."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        assert has_wrapper(root, 'pw', 'pw.bat') is False


def test_has_wrapper_ignores_wrong_platform():
    """has_wrapper checks only the correct platform wrapper."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'pw').write_text('#!/bin/bash')

        # Unix wrapper exists but we're on Windows - should return False
        with patch('_build_wrapper.IS_WINDOWS', True):
            assert has_wrapper(root, 'pw', 'pw.bat') is False

        # Now check with Unix - should return True
        with patch('_build_wrapper.IS_WINDOWS', False):
            assert has_wrapper(root, 'pw', 'pw.bat') is True


# =============================================================================
# Test: IS_WINDOWS constant
# =============================================================================


def test_is_windows_is_bool():
    """IS_WINDOWS is a boolean."""
    assert isinstance(IS_WINDOWS, bool)

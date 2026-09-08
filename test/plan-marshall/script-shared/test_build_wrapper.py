#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for platform-aware wrapper detection."""

from pathlib import Path
from unittest.mock import patch

import pytest
from _build_execute import IS_WINDOWS, detect_wrapper, has_wrapper

#: ``(unix wrapper, windows wrapper, system fallback)`` — the three wrapper
#: families the shared detector serves. Each is driven on both platforms, so a
#: detector that special-cased one family would fail on the other two.
_WRAPPER_FAMILIES = [
    ('pw', 'pw.bat', None),
    ('mvnw', 'mvnw.cmd', 'mvn'),
    ('gradlew', 'gradlew.bat', 'gradle'),
]

_WRAPPER_FAMILY_IDS = ['pyprojectx', 'maven', 'gradle']


@pytest.mark.parametrize('unix,windows,system', _WRAPPER_FAMILIES, ids=_WRAPPER_FAMILY_IDS)
def test_detect_wrapper_returns_the_unix_wrapper_on_unix(
    tmp_path: Path, unix: str, windows: str, system: str | None
):
    """On Unix, detect_wrapper returns the project-relative Unix wrapper."""
    (tmp_path / unix).write_text('#!/bin/bash')

    with patch('_build_execute.IS_WINDOWS', False):
        assert detect_wrapper(str(tmp_path), unix, windows, system) == f'./{unix}'


@pytest.mark.parametrize('unix,windows,system', _WRAPPER_FAMILIES, ids=_WRAPPER_FAMILY_IDS)
def test_detect_wrapper_returns_the_windows_wrapper_on_windows(
    tmp_path: Path, unix: str, windows: str, system: str | None
):
    """On Windows, detect_wrapper returns a path naming the Windows wrapper."""
    (tmp_path / windows).write_text('@echo off')

    with patch('_build_execute.IS_WINDOWS', True):
        assert windows in detect_wrapper(str(tmp_path), unix, windows, system)


#: ``(the wrapper file present, whether the run is on Windows)`` — the three
#: shapes that must find nothing. The two cross-platform rows are what keep the
#: platform check from degenerating into "any wrapper file will do".
_NO_WRAPPER_CASES = [(None, False), ('pw', True), ('pw.bat', False)]

_NO_WRAPPER_IDS = [
    'no-wrapper-file-at-all',
    'unix-wrapper-on-windows',
    'bat-wrapper-on-unix',
]


@pytest.mark.parametrize('present,is_windows', _NO_WRAPPER_CASES, ids=_NO_WRAPPER_IDS)
def test_detect_wrapper_returns_none_when_the_platform_wrapper_is_absent(
    tmp_path: Path, present: str | None, is_windows: bool
):
    if present is not None:
        (tmp_path / present).write_text('#!/bin/bash')

    with patch('_build_execute.IS_WINDOWS', is_windows):
        assert detect_wrapper(str(tmp_path), 'pw', 'pw.bat') is None


def test_detect_wrapper_finds_system_fallback(tmp_path: Path):
    """Falls back to system command if available."""
    with patch('_build_execute.shutil.which', return_value='/usr/bin/pwx'):
        assert detect_wrapper(str(tmp_path), 'pw', 'pw.bat', 'pwx') == 'pwx'


#: ``(the wrapper file present, whether the run is on Windows, has_wrapper's
#: verdict)``. ``has_wrapper`` answers the same platform question as
#: ``detect_wrapper`` but as a boolean, so the same four shapes apply.
_HAS_WRAPPER_CASES = [
    ('pw', False, True),
    ('pw.bat', True, True),
    (None, False, False),
    ('pw', True, False),
]

_HAS_WRAPPER_IDS = [
    'unix-wrapper-on-unix',
    'bat-wrapper-on-windows',
    'no-wrapper-file-at-all',
    'unix-wrapper-on-windows-does-not-count',
]


@pytest.mark.parametrize('present,is_windows,expected', _HAS_WRAPPER_CASES, ids=_HAS_WRAPPER_IDS)
def test_has_wrapper(tmp_path: Path, present: str | None, is_windows: bool, expected: bool):
    if present is not None:
        (tmp_path / present).write_text('#!/bin/bash')

    with patch('_build_execute.IS_WINDOWS', is_windows):
        assert has_wrapper(tmp_path, 'pw', 'pw.bat') is expected


def test_is_windows_is_bool():
    """IS_WINDOWS is a boolean."""
    assert isinstance(IS_WINDOWS, bool)

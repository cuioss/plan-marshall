#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Localized merge-tree regression tests for PLAN-211 D1/D4/D6.

Covers the delivery-breaking defect where localized merge-tree prose was
filed as conflict paths: informational lines after the blank separator must
never count as conflicts, --no-messages must be passed, and git locale must
be pinned to C for deterministic parsing.
"""

from __future__ import annotations

from conftest import load_script_module

_mod = load_script_module(
    'plan-marshall',
    'workflow-integration-git',
    '_cmd_baseline_reconcile.py',
    '_cmd_baseline_reconcile_localized_under_test',
    register=False,
)

_provider_mod = load_script_module(
    'plan-marshall',
    'workflow-integration-git',
    'git_provider.py',
    '_git_provider_localized_under_test',
    register=False,
)


def _patch_run_git(monkeypatch, stdout, rc=1, stderr=""):
    seen = {}

    def _fake(args):
        seen['args'] = list(args)
        return rc, stdout, stderr

    monkeypatch.setattr(_mod, 'run_git', _fake)
    return seen


def test_german_messages_after_separator_ignored(monkeypatch):
    stdout = (
        "cbefafdbf4f90932864db95e9412f89c2046c3ab\n"
        "shared.txt\n"
        "\n"
        "automatischer Merge von shared.txt\n"
        "KONFLIKT (Inhalt): Merge-Konflikt in shared.txt\n"
    )
    seen = _patch_run_git(monkeypatch, stdout)
    files, err = _mod._detect_merge_conflicts("/tmp", "main")
    assert err is None
    assert files == ["shared.txt"]
    assert "--no-messages" in seen["args"]


def test_english_messages_after_separator_ignored(monkeypatch):
    stdout = (
        "cbefafdbf4f90932864db95e9412f89c2046c3ab\n"
        "shared.txt\n"
        "\n"
        "Auto-merging shared.txt\n"
        "CONFLICT (content): Merge conflict in shared.txt\n"
    )
    _patch_run_git(monkeypatch, stdout)
    files, err = _mod._detect_merge_conflicts("/tmp", "main")
    assert err is None
    assert files == ["shared.txt"]


def test_no_messages_flag_suppresses_section_but_separator_still_guards(monkeypatch):
    stdout = "abc123\nshared.txt\n"
    seen = _patch_run_git(monkeypatch, stdout)
    files, err = _mod._detect_merge_conflicts("/tmp", "main")
    assert err is None
    assert files == ["shared.txt"]
    assert "--no-messages" in seen["args"]


def test_fallback_when_no_messages_unsupported(monkeypatch):
    calls = []

    def _fake(args):
        calls.append(list(args))
        if "--no-messages" in args:
            return 129, "", "error: unknown option `no-messages'"
        return 1, "abc123\nshared.txt\n\nAuto-merging x\n", ""

    monkeypatch.setattr(_mod, 'run_git', _fake)
    files, err = _mod._detect_merge_conflicts("/tmp", "main")
    assert err is None
    assert files == ["shared.txt"]
    assert len(calls) == 2


def test_run_git_pins_locale_to_c(monkeypatch):
    import subprocess

    captured = {}

    class _R:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(cmd, capture_output=None, text=None, timeout=None, cwd=None, env=None):
        captured["env"] = dict(env or {})
        return _R()

    monkeypatch.setattr(subprocess, 'run', _fake_run)
    _provider_mod.run_git(["--version"])
    env = captured.get("env", {})
    assert env.get("LC_ALL") == "C"
    assert env.get("LANG") == "C"
    assert env.get("LANGUAGE") == "C"

#!/usr/bin/env python3
"""Structural drift guard: python-verify.yml push allowlist == marshal.json allowlist.

Pins the CI push-trigger branch allowlist in
``.github/workflows/python-verify.yml`` (``on.push.branches``) to the canonical
``project.branch_naming.ci_allowlist`` read through the Deliverable-1 accessor
(``read_branch_naming``), which falls back to ``DEFAULT_CI_BRANCH_ALLOWLIST`` from
``constants`` when the project ``marshal.json`` (or the key) is absent — so the
test pins workflow-file <-> marshal.json consistency with marshal.json as the
source of truth, and still runs deterministically in a checkout that has not
been initialised.

Lesson ``2026-05-21-18-002`` / PR #441: a PR whose branch prefix falls outside
the closed CI allowlist silently receives no ``verify / verify`` status check and
is structurally unmergeable. Any drift of the workflow allowlist (an entry
added, removed, or reordered) fails this test, forcing a deliberate, lockstep
update of ``project.branch_naming.ci_allowlist`` in marshal.json (and the
constants fallback). ``docs/`` is explicitly retired and asserted absent.
"""

# ruff: noqa: I001, E402

import importlib.util
import json
import re
import sys
from pathlib import Path

# repo_root/test/plan-marshall/manage-config/test_branch_prefix_allowlist.py
#                                          ^ parents[3] == repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW_PATH = _REPO_ROOT / '.github' / 'workflows' / 'python-verify.yml'
_MARSHAL_PATH = _REPO_ROOT / '.plan' / 'marshal.json'

_SCRIPTS_DIR = (
    _REPO_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_system_plan_mod = _load_module(
    '_cmd_system_plan_for_branch_prefix_allowlist_test', '_cmd_system_plan.py'
)


def _load_project_config() -> dict:
    """Load the repo's marshal.json if present, else an empty config.

    The empty-config path drives ``read_branch_naming`` to its fail-closed
    default (``DEFAULT_CI_BRANCH_ALLOWLIST`` via ``DEFAULT_PROJECT``), keeping the
    test deterministic in a fresh checkout where ``.plan/marshal.json`` does not
    exist (e.g. a CI runner before ``/marshall-steward``).
    """
    try:
        return json.loads(_MARSHAL_PATH.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _expected_allowlist() -> list[str]:
    """The canonical CI allowlist read through the single source-of-truth accessor."""
    block = _cmd_system_plan_mod.read_branch_naming(_load_project_config())
    return list(block['ci_allowlist'])


def _parse_push_branches() -> list[str]:
    """Extract ``on.push.branches`` from python-verify.yml.

    Prefers ``yaml.safe_load`` (handling the YAML 1.1 truthy-key quirk where the
    bare ``on:`` key parses to the boolean ``True``); falls back to a precise
    regex anchored on the ``push:`` block when ``pyyaml`` is unavailable.
    """
    text = _WORKFLOW_PATH.read_text(encoding='utf-8')

    if importlib.util.find_spec('yaml') is not None:
        import yaml

        data = yaml.safe_load(text)
        # YAML 1.1: a bare ``on:`` key is parsed as the boolean True, not 'on'.
        on_section = data.get('on')
        if on_section is None:
            on_section = data.get(True)
        branches = on_section['push']['branches']
        return list(branches)

    # Regex fallback — anchor on the push block's branches list so the
    # pull_request.branches list is never matched.
    match = re.search(r'push:\s*\n\s*branches:\s*\[([^\]]*)\]', text)
    assert match, f'Could not locate on.push.branches in {_WORKFLOW_PATH}'
    raw_entries = match.group(1).split(',')
    return [entry.strip().strip('"').strip("'") for entry in raw_entries if entry.strip()]


def test_workflow_push_allowlist_equals_marshal_allowlist():
    """python-verify.yml's on.push.branches must equal the marshal.json ci_allowlist."""
    # Arrange
    expected = _expected_allowlist()

    # Act
    actual = _parse_push_branches()

    # Assert — exact equality (including order) so any drift fails CI
    assert actual == expected, (
        'python-verify.yml on.push.branches drifted from '
        'project.branch_naming.ci_allowlist (marshal.json source of truth, '
        'constants fallback). Update both in lockstep — see lesson '
        f'2026-05-21-18-002 / CLAUDE.md Branch Naming.\n  workflow: {actual}\n  expected: {expected}'
    )


def test_workflow_push_allowlist_excludes_docs_prefix():
    """The retired 'docs/' prefix must NOT appear in the workflow push allowlist."""
    # Arrange / Act
    actual = _parse_push_branches()

    # Assert — 'docs/' is explicitly retired and must never be re-admitted.
    # Anchor the match so legitimate prefixes that merely share the 'docs'
    # substring (e.g. 'documents/*') are not false-positives.
    assert not any(re.match(r'^docs(/|\*|$)', entry) for entry in actual), (
        "'docs/' is explicitly retired and must be absent from the "
        f'python-verify.yml push allowlist; found: {actual}'
    )

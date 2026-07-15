#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Structural coverage guard: every working_prefix is CI-push-triggered.

Pins the canonical working-branch prefix set in
``project.working_prefixes`` (read from the repo's ``.plan/marshal.json``, or the
``DEFAULT_PROJECT['working_prefixes']`` fail-closed default when the project
``marshal.json`` or the key is absent) against the CI push-trigger branch
allowlist in ``.github/workflows/python-verify.yml`` (``on.push.branches``).

The check is a **subset coverage** assertion, not full equality: every
``working_prefix`` MUST be covered by at least one workflow push trigger. The
workflow allowlist owns CI-only entries (``main``, ``dependabot/**``) that are
deliberately NOT working prefixes, so an equality check would be wrong — the
prefix set is the source of truth for what plans may create, and the workflow is
the source of truth for what CI runs. This test only enforces the one-way
implication that matters: a working prefix with no CI trigger.

Lesson ``2026-05-21-18-002`` / PR #441: a PR whose branch prefix falls outside
the CI push allowlist silently receives no ``verify / verify`` status check and
is structurally unmergeable. A ``working_prefix`` not covered by any workflow
trigger fails this test, forcing the workflow file (or the prefix set) to be
updated. ``docs/`` is explicitly retired and asserted absent.
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
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_config_defaults_mod = _load_module(
    '_config_defaults_for_branch_prefix_allowlist_test', '_config_defaults.py'
)


def _load_project_config() -> dict:
    """Load the repo's marshal.json if present, else an empty config.

    The empty-config path drives the prefix lookup to its fail-closed default
    (``DEFAULT_PROJECT['working_prefixes']``), keeping the test deterministic in
    a fresh checkout where ``.plan/marshal.json`` does not exist (e.g. a CI
    runner before ``/marshall-steward``).
    """
    try:
        data: dict = json.loads(_MARSHAL_PATH.read_text(encoding='utf-8'))
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _working_prefixes() -> list[str]:
    """The canonical working-branch prefix set, live block or fail-closed default."""
    config = _load_project_config()
    project = config.get('project') if isinstance(config, dict) else None
    if isinstance(project, dict) and isinstance(project.get('working_prefixes'), list):
        return list(project['working_prefixes'])
    return list(_config_defaults_mod.DEFAULT_PROJECT['working_prefixes'])


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


def _prefix_is_covered(prefix: str, triggers: list[str]) -> bool:
    """Return True when a workflow push trigger covers the working ``prefix``.

    A prefix like ``feature/`` is covered by a glob trigger ``feature/*`` (the
    canonical form) or by an exact match. The comparison strips the trailing
    ``/`` from the prefix and the trailing ``/*`` / ``/**`` from the trigger so
    ``feature/`` matches ``feature/*``.
    """
    prefix_stem = prefix.rstrip('/')
    for trigger in triggers:
        trigger_stem = re.sub(r'/\*+$', '', trigger).rstrip('/')
        if trigger_stem == prefix_stem:
            return True
    return False


def test_every_working_prefix_is_ci_push_triggered():
    """Every project.working_prefixes entry must be covered by a workflow push trigger."""
    prefixes = _working_prefixes()
    triggers = _parse_push_branches()

    uncovered = [p for p in prefixes if not _prefix_is_covered(p, triggers)]

    # subset coverage: a working prefix with no CI trigger makes its
    # PRs structurally unmergeable (no verify / verify check). See lesson
    # 2026-05-21-18-002 / CLAUDE.md Branch Naming.
    assert not uncovered, (
        'Working prefix(es) not covered by any python-verify.yml on.push.branches '
        'trigger — a PR on such a branch silently receives no verify / verify '
        'check and is structurally unmergeable. Add a matching push trigger to '
        'the workflow (or drop the prefix from project.working_prefixes).\n'
        f'  uncovered prefixes: {uncovered}\n'
        f'  working_prefixes:   {prefixes}\n'
        f'  workflow triggers:  {triggers}'
    )


def test_workflow_push_allowlist_excludes_docs_prefix():
    """The retired 'docs/' prefix must NOT appear in the workflow push allowlist."""
    actual = _parse_push_branches()

    # 'docs/' is explicitly retired and must never be re-admitted.
    # Anchor the match so legitimate prefixes that merely share the 'docs'
    # substring (e.g. 'documents/*') are not false-positives.
    assert not any(re.match(r'^docs(/|\*|$)', entry) for entry in actual), (
        "'docs/' is explicitly retired and must be absent from the "
        f'python-verify.yml push allowlist; found: {actual}'
    )


def test_docs_prefix_absent_from_working_prefixes():
    """The retired 'docs/' prefix must NOT appear in project.working_prefixes."""
    prefixes = _working_prefixes()

    # 'docs/' is explicitly retired from the working-prefix set.
    assert 'docs/' not in prefixes, (
        "'docs/' is explicitly retired and must be absent from "
        f'project.working_prefixes; found: {prefixes}'
    )

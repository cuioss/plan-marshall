#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Structural coverage guard: every working_prefix is built by CI.

Pins the canonical working-branch prefix set — the shipped
``DEFAULT_PROJECT['working_prefixes']`` — against the CI triggers in
``.github/workflows/python-verify.yml``. The set is the code's own default rather
than a read of this repository's ``.plan/marshal.json``, so a project's live
config cannot change what this guard asserts.

A branch is built in one of two ways. A ``pull_request`` trigger matches on the
**base** branch, so when it targets ``main`` a PR from any head branch gets its
``verify / verify`` check and no push trigger is needed: the cuioss-organization
default (``ci.push-builds: default-branch-only``) builds working branches that
way and leaves ``on.push.branches`` at ``main`` and ``dependabot/**``. Without
such a ``pull_request`` trigger the push allowlist (``on.push.branches``) is the
only thing that builds a branch.

The check is a **subset coverage** assertion, not full equality: every
``working_prefix`` MUST be covered by at least one of the two. The workflow owns
CI-only entries (``main``, ``dependabot/**``) that are deliberately NOT working
prefixes, so an equality check would be wrong. A ``working_prefix`` covered by
neither makes its PRs structurally unmergeable (no ``verify / verify`` check) and
fails this test, forcing the workflow file (or the prefix set) to be updated.
``docs/`` is not a working prefix and is asserted absent.
"""

import fnmatch
import importlib.util
import re

from conftest import PROJECT_ROOT, load_script_module

_WORKFLOW_PATH = PROJECT_ROOT / '.github' / 'workflows' / 'python-verify.yml'

_config_defaults_mod = load_script_module(
    'plan-marshall',
    'manage-config',
    '_config_defaults.py',
    module_name='_config_defaults_for_branch_prefix_allowlist_test',
)


def _working_prefixes() -> list[str]:
    """The canonical working-branch prefix set, from the shipped default.

    The production default is the population this guard pins: it is the set a
    fresh project receives, and it is what the workflow's push allowlist must
    cover. Reading this repository's own ``.plan/marshal.json`` would make the
    assertion depend on the live config instead of the shipped contract.
    """
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
        push = on_section.get('push') or {}
        # A pull-request-only workflow has no push trigger at all; that is an empty
        # list, not a crash, so the pull_request coverage path can still be reached.
        return [str(entry) for entry in (push.get('branches') or [])]

    # Regex fallback — anchor on the push block's branches list so the
    # pull_request.branches list is never matched.
    match = re.search(r'push:\s*\n\s*branches:\s*\[([^\]]*)\]', text)
    if not match:
        return []
    raw_entries = match.group(1).split(',')
    return [entry.strip().strip('"').strip("'") for entry in raw_entries if entry.strip()]


def _branch_is_selected(branch: str, patterns: list[str]) -> bool:
    """GitHub branch-filter semantics for one branch: ordered globs, ``!`` negates.

    A matching negative pattern after a positive one excludes the branch, and a
    glob (``m*``) matches like it does in the workflow, so a guard that only
    compared literal names would accept a filter that excludes ``main``.
    """
    selected = False
    for raw in patterns:
        pattern = str(raw)
        negate = pattern.startswith('!')
        if fnmatch.fnmatchcase(branch, pattern[1:] if negate else pattern):
            selected = not negate
    return selected


def _main_selected(branches: list[str] | None, ignored: list[str] | None) -> bool:
    """Whether a PR targeting ``main`` triggers the workflow under both filters."""
    selected = True
    if branches is not None:
        selected = selected and _branch_is_selected('main', branches)
    if ignored is not None:
        selected = selected and not _branch_is_selected('main', ignored)
    return selected


def _pull_request_builds_main() -> bool:
    """True when ``on.pull_request`` targets ``main``, so a PR from any head branch is built."""
    text = _WORKFLOW_PATH.read_text(encoding='utf-8')

    if importlib.util.find_spec('yaml') is not None:
        import yaml

        data = yaml.safe_load(text)
        on_section = data.get('on')
        if on_section is None:
            on_section = data.get(True)
        if 'pull_request' not in on_section:
            return False
        pull_request = on_section['pull_request'] or {}
        return _main_selected(pull_request.get('branches'), pull_request.get('branches-ignore'))

    # Regex fallback — anchor on the pull_request block so push.branches is never matched.
    match = re.search(r'\n  pull_request:\s*\n(?P<body>(?:    .*\n|\s*\n)*)', text)
    if not match:
        return False
    body = match.group('body')

    def _entries(key: str) -> list[str] | None:
        found = re.search(rf'{key}:\s*\[([^\]]*)\]', body)
        if found is None:
            return None
        return [entry.strip().strip('"').strip("'") for entry in found.group(1).split(',') if entry.strip()]

    return _main_selected(_entries('branches'), _entries('branches-ignore'))


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


def test_every_working_prefix_is_ci_built():
    """Every shipped default working prefix must be built by a pull_request or push trigger."""
    prefixes = _working_prefixes()
    triggers = _parse_push_branches()
    pull_request_builds_main = _pull_request_builds_main()

    # A pull_request trigger on main builds a PR from any head branch.
    uncovered = [] if pull_request_builds_main else [p for p in prefixes if not _prefix_is_covered(p, triggers)]

    # subset coverage: a working prefix with no CI trigger makes its
    # PRs structurally unmergeable (no verify / verify check).
    # See CLAUDE.md § Branch Naming.
    assert not uncovered, (
        'Working prefix(es) not built by python-verify.yml — a PR on such a branch '
        'silently receives no verify / verify check and is structurally unmergeable. '
        'Add a pull_request trigger on main, or a matching on.push.branches entry '
        "(or drop the prefix from DEFAULT_PROJECT['working_prefixes']).\n"
        f'  uncovered prefixes:    {uncovered}\n'
        f'  working_prefixes:      {prefixes}\n'
        f'  workflow push triggers: {triggers}\n'
        f'  pull_request on main:  {pull_request_builds_main}'
    )


def test_workflow_push_allowlist_excludes_docs_prefix():
    """The retired 'docs/' prefix must NOT appear in the workflow push allowlist."""
    actual = _parse_push_branches()

    # 'docs/' is explicitly retired and must never be re-admitted.
    # Anchor the match so legitimate prefixes that merely share the 'docs'
    # substring (e.g. 'documents/*') are not false-positives.
    assert not any(re.match(r'^docs(/|\*|$)', entry) for entry in actual), (
        f"'docs/' is explicitly retired and must be absent from the python-verify.yml push allowlist; found: {actual}"
    )


def test_docs_prefix_absent_from_working_prefixes():
    """The retired 'docs/' prefix must NOT appear in the shipped default prefix set."""
    prefixes = _working_prefixes()

    # 'docs/' is explicitly retired from the working-prefix set.
    assert 'docs/' not in prefixes, (
        f"'docs/' is explicitly retired and must be absent from DEFAULT_PROJECT['working_prefixes']; found: {prefixes}"
    )

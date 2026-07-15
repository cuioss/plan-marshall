#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Structural coverage guard: python-verify.yml declares a merge_group trigger.

Pins the presence of a ``merge_group`` event trigger in the ``on:`` block of
``.github/workflows/python-verify.yml``. GitHub's merge queue enqueues a PR onto
a temporary ``merge_group`` ref and dispatches ``merge_group`` (type
``checks_requested``) events; a workflow that omits the trigger never runs on the
queued ref, so the ``verify / verify`` status check the branch-protection ruleset
requires is never produced and the queued PR stalls indefinitely.

Colocated with ``test_branch_prefix_allowlist.py`` (which pins the push-trigger
allowlist), this test enforces the complementary invariant for the merge-queue
enablement: the ``on:`` block MUST declare ``merge_group`` so the reusable verify
job runs when a PR is queued.
"""

# ruff: noqa: I001, E402

import importlib.util
import re
from pathlib import Path

# repo_root/test/plan-marshall/manage-config/test_merge_group_trigger.py
#                                          ^ parents[3] == repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW_PATH = _REPO_ROOT / '.github' / 'workflows' / 'python-verify.yml'


def _parse_on_section() -> dict:
    """Return the workflow ``on:`` mapping from python-verify.yml.

    Prefers ``yaml.safe_load`` (handling the YAML 1.1 truthy-key quirk where the
    bare ``on:`` key parses to the boolean ``True``); the caller falls back to a
    regex probe when ``pyyaml`` is unavailable.
    """
    text = _WORKFLOW_PATH.read_text(encoding='utf-8')

    import yaml

    data = yaml.safe_load(text)
    # YAML 1.1: a bare ``on:`` key is parsed as the boolean True, not 'on'.
    on_section: dict = data.get('on')
    if on_section is None:
        on_section = data.get(True)
    return on_section


def _merge_group_present_via_regex() -> bool:
    """Regex fallback: detect a ``merge_group:`` event key inside the on: block.

    Scopes the search to the ``on:`` block only — from the top-level ``on:`` key
    (bare or quoted) up to but not including the next column-0 key (or end of
    file) — then anchors on a two-space-indented ``merge_group:`` key within that
    block. Without the block scoping, a two-space-indented ``merge_group:`` key
    living under some other top-level section (e.g. a ``jobs:`` entry literally
    named ``merge_group``) would false-positive-match, defeating the guard.
    Mirrors the ``push:``-block-anchored fallback in
    ``test_branch_prefix_allowlist.py::_parse_push_branches``.
    """
    text = _WORKFLOW_PATH.read_text(encoding='utf-8')
    on_block = re.search(
        r'^(?:on|["\']on["\']):[^\n]*\n(.*?)(?=^\S|\Z)',
        text,
        re.MULTILINE | re.DOTALL,
    )
    if on_block is None:
        return False
    return re.search(r'^\s{2}merge_group:', on_block.group(1), re.MULTILINE) is not None


def test_on_block_declares_merge_group_trigger():
    """The workflow on: block must declare a merge_group event trigger."""
    if importlib.util.find_spec('yaml') is not None:
        on_section = _parse_on_section()
        assert on_section is not None, (
            'python-verify.yml has no parseable on: block — the workflow cannot '
            'declare any event triggers.'
        )
        assert 'merge_group' in on_section, (
            'python-verify.yml on: block does not declare a merge_group trigger. '
            'GitHub merge queue dispatches merge_group events on the queued ref; '
            'without this trigger the reusable verify job never runs on a queued '
            'PR, so the required verify / verify check is never produced and the '
            f'PR stalls in the queue. on: keys found: {sorted(map(str, on_section))}'
        )
    else:
        assert _merge_group_present_via_regex(), (
            'python-verify.yml on: block does not declare a merge_group trigger '
            '(regex fallback; pyyaml unavailable).'
        )

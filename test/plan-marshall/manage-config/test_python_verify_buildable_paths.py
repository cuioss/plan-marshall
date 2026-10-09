#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Structural test: python-verify.yml declares extra-buildable inputs for test paths.

PLAN-LB-30 / PLAN-LB-16 (Deliverable 6):
Asserts that while ``skip-on-docs-only`` is ``true``, the ``extra-buildable`` input
is present in ``.github/workflows/python-verify.yml`` and names at minimum
``.plan/marshal.json`` and ``.claude/**``. When ``skip-on-docs-only`` is ``false``
or absent, the test passes without the input (as nothing is skipped).

Includes matched positive and negative controls to prevent regressions.
"""

from __future__ import annotations

import importlib.util
import re
from typing import Any, cast

import pytest

from conftest import PROJECT_ROOT

_WORKFLOW_PATH = PROJECT_ROOT / '.github' / 'workflows' / 'python-verify.yml'

#: Required buildable paths that must be passed when skip-on-docs-only is active.
REQUIRED_EXTRA_BUILDABLE_PATHS = frozenset(
    {
        '.plan/marshal.json',
        '.claude/**',
    }
)

#: Required markdown test paths that must be passed for doc-test safety.
REQUIRED_MARKDOWN_BUILDABLE_PATHS = frozenset(
    {
        'marketplace/**/*.md',
        'test/**/*.md',
    }
)


def _parse_verify_with_section(workflow_text: str | None = None) -> dict[str, Any]:
    """Extract the ``with:`` section of the ``verify:`` job from workflow text."""
    if workflow_text is None:
        workflow_text = _WORKFLOW_PATH.read_text(encoding='utf-8')

    if importlib.util.find_spec('yaml') is not None:
        import yaml

        data = yaml.safe_load(workflow_text)
        jobs = data.get('jobs', {})
        verify_job = jobs.get('verify', {})
        return cast(dict[str, Any], verify_job.get('with') or {})

    return _parse_verify_with_via_regex(workflow_text)


def _parse_verify_with_via_regex(workflow_text: str) -> dict[str, Any]:
    """Regex fallback to extract key-values from verify job ``with:`` block."""
    result: dict[str, Any] = {}
    with_match = re.search(
        r'^\s*verify:\s*\n(?:.*?\n)*?\s+with:\s*\n(.*?)(?=^\s{2,4}\w|\Z)',
        workflow_text,
        re.MULTILINE | re.DOTALL,
    )
    if not with_match:
        return result

    block = with_match.group(1)

    # Check skip-on-docs-only
    skip_match = re.search(r'^\s*skip-on-docs-only:\s*(true|false)', block, re.MULTILINE | re.IGNORECASE)
    if skip_match:
        result['skip-on-docs-only'] = skip_match.group(1).lower() == 'true'

    # Check extra-buildable
    extra_match = re.search(
        r'^\s*extra-buildable:\s*(?:>-\s*\n|>\s*\n|\|\s*\n)?(.*?)(?=^\s*[\w\-]+:|\Z)',
        block,
        re.MULTILINE | re.DOTALL,
    )
    if extra_match:
        lines = [
            line.strip()
            for line in extra_match.group(1).splitlines()
            if line.strip() and not line.strip().startswith('#')
        ]
        result['extra-buildable'] = ' '.join(lines)

    return result


def validate_extra_buildable_config(with_section: dict[str, Any]) -> tuple[bool, str]:
    """Validate that extra-buildable is declared correctly when skip-on-docs-only is active.

    Returns:
        (True, "") if configuration is valid.
        (False, error_reason) if invalid.
    """
    skip_on_docs_only = with_section.get('skip-on-docs-only')
    is_active = skip_on_docs_only is True or str(skip_on_docs_only).lower() == 'true'

    if not is_active:
        return True, 'skip-on-docs-only is false or absent; extra-buildable is not required'

    if 'extra-buildable' not in with_section:
        return False, 'skip-on-docs-only is true but extra-buildable input is missing'

    raw_extra = with_section['extra-buildable']
    if isinstance(raw_extra, str):
        paths = set(raw_extra.split())
    elif isinstance(raw_extra, (list, tuple, set)):
        paths = set(raw_extra)
    else:
        return False, f'unexpected extra-buildable type: {type(raw_extra)}'

    missing = REQUIRED_EXTRA_BUILDABLE_PATHS - paths
    if missing:
        return (
            False,
            f'extra-buildable is missing required test-input paths: {sorted(missing)} (found: {sorted(paths)})',
        )

    missing_markdown = REQUIRED_MARKDOWN_BUILDABLE_PATHS - paths
    if missing_markdown:
        return (
            False,
            f'extra-buildable is missing required markdown paths: {sorted(missing_markdown)} (found: {sorted(paths)})',
        )

    return True, ''


def test_python_verify_workflow_pins_extra_buildable_paths():
    """Live workflow test: python-verify.yml must pass extra-buildable when skip-on-docs-only is true."""
    assert _WORKFLOW_PATH.is_file(), f'python-verify.yml not found at {_WORKFLOW_PATH}'

    with_section = _parse_verify_with_section()
    assert with_section, 'Could not parse with: section from verify job in python-verify.yml'

    valid, reason = validate_extra_buildable_config(with_section)
    assert valid, f'python-verify.yml failed extra-buildable validation: {reason}'

    # Also assert that marketplace and test markdown paths are declared for test safety
    raw_extra = str(with_section.get('extra-buildable', ''))
    paths = set(raw_extra.split())
    missing_markdown = REQUIRED_MARKDOWN_BUILDABLE_PATHS - paths
    assert not missing_markdown, (
        f'extra-buildable missing required markdown paths: {sorted(missing_markdown)} (found: {sorted(paths)})'
    )


def test_validate_extra_buildable_passes_when_skip_on_docs_only_false():
    """Positive control: when skip-on-docs-only is false, extra-buildable is not required."""
    with_section = {'skip-on-docs-only': False}
    valid, reason = validate_extra_buildable_config(with_section)
    assert valid, f'Expected pass when skip-on-docs-only is False, got: {reason}'


def test_validate_extra_buildable_passes_when_skip_on_docs_only_absent():
    """Positive control: when skip-on-docs-only is absent, extra-buildable is not required."""
    with_section = {'pre-verify-goals': 'generate'}
    valid, reason = validate_extra_buildable_config(with_section)
    assert valid, f'Expected pass when skip-on-docs-only is absent, got: {reason}'


def test_validate_extra_buildable_fails_when_extra_buildable_missing():
    """Negative control: when skip-on-docs-only is true, missing extra-buildable must fail."""
    with_section = {'skip-on-docs-only': True}
    valid, reason = validate_extra_buildable_config(with_section)
    assert not valid, 'Expected failure when extra-buildable is missing'
    assert 'missing' in reason.lower()


def test_validate_extra_buildable_fails_when_required_path_missing():
    """Negative control: missing .plan/marshal.json or .claude/** must fail."""
    # Missing .claude/**
    with_section_1 = {
        'skip-on-docs-only': True,
        'extra-buildable': '.plan/marshal.json',
    }
    valid_1, reason_1 = validate_extra_buildable_config(with_section_1)
    assert not valid_1, 'Expected failure when .claude/** is missing'
    assert '.claude/**' in reason_1

    # Missing .plan/marshal.json
    with_section_2 = {
        'skip-on-docs-only': True,
        'extra-buildable': '.claude/**',
    }
    valid_2, reason_2 = validate_extra_buildable_config(with_section_2)
    assert not valid_2, 'Expected failure when .plan/marshal.json is missing'
    assert '.plan/marshal.json' in reason_2


def test_validate_extra_buildable_fails_when_markdown_path_has_wrong_extension():
    """Negative control: extra-buildable carrying .mdx globs instead of .md must fail."""
    with_section = {
        'skip-on-docs-only': True,
        'extra-buildable': '.plan/marshal.json .claude/** marketplace/**/*.mdx test/**/*.mdx',
    }
    valid, reason = validate_extra_buildable_config(with_section)
    assert not valid, 'Expected failure when markdown paths have .mdx extension'
    assert 'marketplace/**/*.md' in reason or 'test/**/*.md' in reason

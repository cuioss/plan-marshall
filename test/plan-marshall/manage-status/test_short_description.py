#!/usr/bin/env python3
"""Tests for ``derive_short_description`` and its integration with ``cmd_create``.

Unit scope:
    * Plain titles: spaces -> underscores, no truncation when within budget.
    * Long titles: truncated at an underscore boundary with ellipsis (U+2026).
    * Lesson-id prefix forms (``YYYY-MM-DD-NN-...`` and ``lesson-YYYY-...``)
      are stripped before deriving the slug.
    * Pure lesson-id noise with no trailing slug -> empty string.
    * Empty / whitespace titles -> empty string.

Integration scope:
    * ``cmd_create`` persists the derived ``short_description`` in ``status.json``.
"""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

from conftest import PlanContext

# =============================================================================
# Module loading (mirrors sibling tests, avoids import ambiguity across skills)
# =============================================================================

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-status'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_short = _load_module('_short_description_under_test', '_short_description.py')
_lifecycle = _load_module('_short_description_lifecycle', '_cmd_lifecycle.py')
_status_core = _load_module('_short_description_status_core', '_status_core.py')

derive_short_description = _short.derive_short_description
cmd_create = _lifecycle.cmd_create
get_status_path = _status_core.get_status_path

ELLIPSIS = '…'

# =============================================================================
# Unit tests: plain title (within budget)
# =============================================================================


def test_plain_title_replaces_spaces_with_underscores():
    """Internal spaces become underscores and the slug is returned verbatim."""
    assert derive_short_description('Fix terminal title') == 'Fix_terminal_title'


def test_plain_title_exactly_at_budget_is_preserved():
    """A slug whose length equals ``max_len`` must be returned untruncated."""
    title = 'aaaa bbbb cccc dddd'  # 19 chars, slug = 19 chars
    result = derive_short_description(title, max_len=len(title))
    assert result == 'aaaa_bbbb_cccc_dddd'
    assert ELLIPSIS not in result


def test_plain_title_collapses_internal_whitespace_runs():
    """Multiple whitespace characters collapse to a single underscore."""
    assert derive_short_description('Fix   terminal\t title') == 'Fix_terminal_title'


# =============================================================================
# Unit tests: long title (truncation with ellipsis)
# =============================================================================


def test_long_title_truncated_at_underscore_boundary():
    """Truncation falls back to the last underscore boundary within the budget."""
    title = 'Improve terminal title display for running plans everywhere'
    result = derive_short_description(title, max_len=36)
    assert result.endswith(ELLIPSIS)
    assert len(result) <= 36
    # Head must end at a word boundary (no trailing underscore before ellipsis).
    head = result[:-1]
    assert not head.endswith('_')
    # Head is a prefix of the underscore slug of the original title.
    full_slug = title.replace(' ', '_')
    assert full_slug.startswith(head)


def test_long_title_respects_default_max_len_36():
    """The default ``max_len`` of 36 is honoured when the argument is omitted."""
    title = 'Improve terminal title display for running plans everywhere'
    result = derive_short_description(title)
    assert len(result) <= 36
    assert result.endswith(ELLIPSIS)


# =============================================================================
# Unit tests: lesson-id prefix stripping
# =============================================================================


def test_lesson_id_prefix_numeric_only_is_stripped():
    """``2026-04-19-13-004-Title here`` -> ``Title_here``."""
    assert derive_short_description('2026-04-19-13-004-Title here') == 'Title_here'


def test_lesson_id_prefix_with_lesson_keyword_is_stripped():
    """``lesson-2026-04-19-13-004-Title here`` -> ``Title_here``."""
    assert derive_short_description('lesson-2026-04-19-13-004-Title here') == 'Title_here'


def test_lesson_id_prefix_only_returns_empty_string():
    """A title that is exclusively lesson-id noise produces no slug."""
    assert derive_short_description('2026-04-19-13-004') == ''
    assert derive_short_description('lesson-2026-04-19-13-004') == ''


# =============================================================================
# Unit tests: empty / whitespace / unusable inputs
# =============================================================================


def test_empty_title_returns_empty_string():
    assert derive_short_description('') == ''


def test_whitespace_only_title_returns_empty_string():
    assert derive_short_description('   \t\n ') == ''


def test_non_string_title_returns_empty_string():
    """Defensive guard: a non-string input must not raise."""
    assert derive_short_description(None) == ''  # type: ignore[arg-type]


def test_non_positive_max_len_returns_empty_string():
    """``max_len <= 0`` means "no budget" and yields an empty slug."""
    assert derive_short_description('Hello World', max_len=0) == ''
    assert derive_short_description('Hello World', max_len=-5) == ''


# =============================================================================
# Integration test: cmd_create persists short_description in status.json
# =============================================================================


def test_cmd_create_persists_short_description_in_status_json(monkeypatch):
    """cmd_create must call derive_short_description and store the result."""
    with PlanContext(plan_id='short-desc-plan') as ctx:
        # Defensive environment pinning mirrors test_manage_status.py.
        monkeypatch.setenv('HOME', str(ctx.fixture_dir))
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(ctx.fixture_dir / 'creds'))

        title = 'Improve terminal title display for running plans'
        result = cmd_create(
            Namespace(
                plan_id='short-desc-plan',
                title=title,
                phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
                force=False,
            )
        )
        assert result['status'] == 'success'

        # Load status.json directly and verify the persisted short_description
        # matches what derive_short_description would produce for the title.
        status_path = get_status_path('short-desc-plan')
        assert status_path.exists()
        payload = json.loads(status_path.read_text(encoding='utf-8'))

        expected = derive_short_description(title)
        assert 'short_description' in payload
        assert payload['short_description'] == expected
        # Sanity check: the expected slug is non-empty and within the budget.
        assert expected
        assert len(expected) <= 36


def test_cmd_create_persists_empty_short_description_for_lesson_id_only_title(monkeypatch):
    """Lesson-id-only titles still create a plan; short_description is empty."""
    with PlanContext(plan_id='lesson-id-only-plan') as ctx:
        monkeypatch.setenv('HOME', str(ctx.fixture_dir))
        monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(ctx.fixture_dir / 'creds'))

        result = cmd_create(
            Namespace(
                plan_id='lesson-id-only-plan',
                title='lesson-2026-04-19-13-004',
                phases='1-init,2-refine',
                force=False,
            )
        )
        assert result['status'] == 'success'

        status_path = get_status_path('lesson-id-only-plan')
        payload = json.loads(status_path.read_text(encoding='utf-8'))
        assert payload['short_description'] == ''

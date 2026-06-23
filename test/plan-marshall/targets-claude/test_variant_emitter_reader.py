# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression test locking the data-driven variant-emission contract for the
``execution-context-reader`` canonical agent.

The reader canonical declares ``implements:
plan-marshall:extension-api/standards/ext-point-dynamic-level-executor`` and
must auto-emit per-level variants with NO change to ``variant_emitter.py`` /
``generate.py``. This test asserts:

- the real reader canonical is role-eligible and emits one variant per level;
- emitted variants carry the restricted read-only tool surface
  (``WebSearch, WebFetch, Read, Grep`` — no Write/Edit/Bash/Skill);
- the canonical omits ``model:`` / ``effort:`` (the validate_canonical backstop
  does not raise).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from marketplace.targets.claude.variant_emitter import (
    LEVEL_TABLE,
    emit_variants_for_agent,
    is_role_eligible,
    parse_frontmatter,
    selected_levels,
    validate_canonical,
)

EXTENSION_POINT = (
    'plan-marshall:extension-api/standards/ext-point-dynamic-level-executor'
)

# Repo root: test/plan-marshall/targets-claude/<file> → up three to repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
READER_CANONICAL = (
    _REPO_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'agents'
    / 'execution-context-reader.md'
)

RESTRICTED_TOOLS = {'WebSearch', 'WebFetch', 'Read', 'Grep'}
FORBIDDEN_TOOLS = {'Write', 'Edit', 'Bash', 'Skill', 'AskUserQuestion', 'Task'}


@pytest.fixture()
def mapping_path(tmp_path: Path) -> Path:
    """Fixture mapping.json: opus accepts xhigh and fable accepts max so all
    seven levels emit."""
    path = tmp_path / 'mapping.json'
    path.write_text(
        json.dumps(
            {
                'tool_permissions': {},
                'model_map': {
                    'opus': {'id': 'claude-opus-4-7', 'supports_effort': ['medium', 'high', 'xhigh']},
                    'sonnet': {'id': 'claude-sonnet-4-6', 'supports_effort': ['medium', 'high']},
                    'haiku': {'id': 'claude-haiku-4-5', 'supports_effort': []},
                    'fable': {'id': 'claude-fable-5', 'supports_effort': ['medium', 'high', 'xhigh', 'max']},
                },
            }
        ),
        encoding='utf-8',
    )
    return path


def _read_frontmatter(text: str):
    frontmatter, _body = parse_frontmatter(text)
    return frontmatter


def _tools_set(frontmatter) -> set[str]:
    """Extract the declared tools as a set from the frontmatter raw lines.

    The emitter's Frontmatter dataclass does not type ``tools:`` (it is
    preserved verbatim in ``raw_lines``), so read it from there.
    """
    if frontmatter is None:
        return set()
    for line in frontmatter.raw_lines:
        stripped = line.strip()
        if stripped.startswith('tools:'):
            value = stripped[len('tools:') :]
            return {t.strip() for t in value.split(',') if t.strip()}
    return set()


def test_reader_canonical_exists():
    assert READER_CANONICAL.exists(), READER_CANONICAL


def test_reader_canonical_is_role_eligible():
    frontmatter = _read_frontmatter(READER_CANONICAL.read_text(encoding='utf-8'))
    assert is_role_eligible(frontmatter)


def test_reader_canonical_omits_model_and_effort():
    frontmatter = _read_frontmatter(READER_CANONICAL.read_text(encoding='utf-8'))
    assert frontmatter is not None
    assert not frontmatter.model
    assert not frontmatter.effort
    # validate_canonical is the build-time backstop — must not raise.
    validate_canonical(frontmatter, READER_CANONICAL)


def test_reader_canonical_declares_restricted_tool_surface():
    frontmatter = _read_frontmatter(READER_CANONICAL.read_text(encoding='utf-8'))
    assert frontmatter is not None
    declared = _tools_set(frontmatter)
    assert declared == RESTRICTED_TOOLS
    assert not (declared & FORBIDDEN_TOOLS)


def test_reader_emits_all_default_levels(tmp_path: Path, mapping_path: Path):
    dest = tmp_path / 'out' / 'execution-context-reader.md'
    result = emit_variants_for_agent(READER_CANONICAL, dest, mapping_path)
    assert result is not None
    assert dest.exists()  # canonical no-suffix file
    for level in LEVEL_TABLE.keys():
        assert (dest.parent / f'execution-context-reader-{level}.md').exists(), level
    assert sorted(result.variants_emitted) == sorted(LEVEL_TABLE.keys())
    assert result.variants_skipped == []


def test_reader_default_levels_match_canonical_selection(tmp_path: Path, mapping_path: Path):
    frontmatter = _read_frontmatter(READER_CANONICAL.read_text(encoding='utf-8'))
    assert frontmatter is not None
    # No levels: whitelist → all seven.
    assert selected_levels(frontmatter) == list(LEVEL_TABLE.keys())


def test_emitted_variants_carry_restricted_tool_surface(tmp_path: Path, mapping_path: Path):
    dest = tmp_path / 'out' / 'execution-context-reader.md'
    emit_variants_for_agent(READER_CANONICAL, dest, mapping_path)
    for level in LEVEL_TABLE.keys():
        variant_text = (dest.parent / f'execution-context-reader-{level}.md').read_text(encoding='utf-8')
        frontmatter = _read_frontmatter(variant_text)
        assert frontmatter is not None, level
        declared = _tools_set(frontmatter)
        assert declared == RESTRICTED_TOOLS, f"{level}: {declared}"
        assert not (declared & FORBIDDEN_TOOLS), level


def test_emitted_variant_names_match_level_suffix(tmp_path: Path, mapping_path: Path):
    dest = tmp_path / 'out' / 'execution-context-reader.md'
    emit_variants_for_agent(READER_CANONICAL, dest, mapping_path)
    for level in LEVEL_TABLE.keys():
        variant_text = (dest.parent / f'execution-context-reader-{level}.md').read_text(encoding='utf-8')
        frontmatter = _read_frontmatter(variant_text)
        assert frontmatter is not None
        assert frontmatter.name == f'execution-context-reader-{level}'


def test_emitted_canonical_strips_role_fields(tmp_path: Path, mapping_path: Path):
    dest = tmp_path / 'out' / 'execution-context-reader.md'
    emit_variants_for_agent(READER_CANONICAL, dest, mapping_path)
    canonical_text = dest.read_text(encoding='utf-8')
    assert f'implements: {EXTENSION_POINT}' not in canonical_text
    assert 'name: execution-context-reader' in canonical_text

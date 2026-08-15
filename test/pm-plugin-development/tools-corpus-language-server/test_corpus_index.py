#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the resident corpus index — cursor resolution, definition, references, hover.

Drives the underscore-prefixed helpers directly by inserting the scripts dir on
``sys.path`` (the canonical scaffolding pattern).
"""

from __future__ import annotations

import sys
from pathlib import Path

from conftest import get_scripts_dir  # type: ignore[import-not-found]

SCRIPTS_DIR = get_scripts_dir('pm-plugin-development', 'tools-corpus-language-server')
INVENTORY_SCRIPTS = get_scripts_dir('pm-plugin-development', 'tools-marketplace-inventory')
for _dir in (str(SCRIPTS_DIR), str(INVENTORY_SCRIPTS)):
    if _dir not in sys.path:
        sys.path.insert(0, _dir)

import _corpus_index as corpus_index  # noqa: E402

PLUGIN_JSON = '{"name": "%s", "version": "0.1", "skills": []}'


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def build_corpus(root: Path) -> Path:
    """A minimal two-bundle corpus: a referenced skill and a referencing one."""
    base = root / 'bundles'

    _write(base / 'alpha' / '.claude-plugin' / 'plugin.json', PLUGIN_JSON % 'alpha')
    _write(
        base / 'alpha' / 'skills' / 'target-skill' / 'SKILL.md',
        '---\nname: target-skill\ndescription: The skill under test\nmode: knowledge\n---\n\n# Target\n',
    )
    _write(base / 'alpha' / 'skills' / 'target-skill' / 'scripts' / 'target_script.py', '# target\n')

    _write(base / 'beta' / '.claude-plugin' / 'plugin.json', PLUGIN_JSON % 'beta')
    _write(
        base / 'beta' / 'skills' / 'caller' / 'SKILL.md',
        '---\nname: caller\ndescription: References the target\n---\n\n'
        '# Caller\n\nSee Skill: alpha:target-skill for details.\n',
    )
    # A sub-document edge source: the index attributes this edge to `beta:caller`
    # while the line it cites lives in this file, not in SKILL.md.
    _write(
        base / 'beta' / 'skills' / 'caller' / 'workflow' / 'step.md',
        '# Step\n\nfiller\nfiller\nRun `alpha:target-skill:target_script` here.\n',
    )
    return base


class TestNotationAt:
    """Cursor-to-token resolution — the (uri, position) half of the surface."""

    def test_resolves_two_part_notation(self) -> None:
        line = 'See Skill: alpha:target-skill for details.'
        assert corpus_index.notation_at(line, line.index('alpha') + 2) == 'alpha:target-skill'

    def test_resolves_three_part_notation(self) -> None:
        line = 'Run `alpha:target-skill:target_script` here.'
        assert corpus_index.notation_at(line, line.index('alpha') + 3) == 'alpha:target-skill:target_script'

    def test_prefers_longest_match_at_position(self) -> None:
        line = 'a:b:c'
        assert corpus_index.notation_at(line, 0) == 'a:b:c'

    def test_returns_none_outside_a_notation(self) -> None:
        assert corpus_index.notation_at('plain prose with no notation', 5) is None

    def test_returns_none_for_negative_character(self) -> None:
        assert corpus_index.notation_at('a:b', -1) is None

    def test_does_not_resolve_inside_a_url(self) -> None:
        # The lookbehind keeps a cursor in `https://host` from yielding `https:host`.
        line = 'see https://example.com/path'
        assert corpus_index.notation_at(line, line.index('https')) is None


class TestDefinition:
    def test_resolves_skill_to_its_file(self, tmp_path: Path) -> None:
        base = build_corpus(tmp_path)
        index = corpus_index.CorpusIndex(base)
        location = index.definition('alpha:target-skill')
        assert location is not None
        assert location.path.name == 'SKILL.md'
        assert location.path.parent.name == 'target-skill'
        assert location.line == 0

    def test_returns_none_for_unknown_notation(self, tmp_path: Path) -> None:
        index = corpus_index.CorpusIndex(build_corpus(tmp_path))
        assert index.definition('alpha:no-such-skill') is None

    def test_knows_reports_membership(self, tmp_path: Path) -> None:
        index = corpus_index.CorpusIndex(build_corpus(tmp_path))
        assert index.knows('alpha:target-skill')
        assert not index.knows('alpha:no-such-skill')


class TestReferences:
    def test_finds_the_inbound_skill_edge(self, tmp_path: Path) -> None:
        index = corpus_index.CorpusIndex(build_corpus(tmp_path))
        refs = index.references('alpha:target-skill')
        assert any(r.source_notation == 'beta:caller' for r in refs)

    def test_verified_reference_points_at_the_citing_line(self, tmp_path: Path) -> None:
        index = corpus_index.CorpusIndex(build_corpus(tmp_path))
        verified = [r for r in index.references('alpha:target-skill') if r.verified]
        assert verified, 'expected at least one provenance-verified reference'
        for ref in verified:
            line_text = ref.location.path.read_text(encoding='utf-8').split('\n')[ref.location.line]
            assert 'alpha:target-skill' in line_text

    def test_subdocument_edge_resolves_to_the_subdocument_not_the_owner(self, tmp_path: Path) -> None:
        """The index attributes a sub-doc edge to the owning skill.

        Without re-reading the cited line, the reference would point confidently
        at ``SKILL.md`` — the wrong file. Provenance verification is what makes
        the location land in ``workflow/step.md`` instead.
        """
        index = corpus_index.CorpusIndex(build_corpus(tmp_path))
        refs = index.references('alpha:target-skill:target_script')
        verified = [r for r in refs if r.verified]
        assert verified, 'expected the script edge to verify'
        assert any(r.location.path.name == 'step.md' for r in verified)

    def test_unknown_notation_has_no_references(self, tmp_path: Path) -> None:
        index = corpus_index.CorpusIndex(build_corpus(tmp_path))
        assert index.references('alpha:no-such-skill') == []


class TestHover:
    def test_returns_description_and_frontmatter(self, tmp_path: Path) -> None:
        index = corpus_index.CorpusIndex(build_corpus(tmp_path))
        payload = index.hover('alpha:target-skill')
        assert payload is not None
        assert payload['description'] == 'The skill under test'
        assert payload['frontmatter']['mode'] == 'knowledge'
        assert payload['kind'] == 'skill'

    def test_reports_edge_counts(self, tmp_path: Path) -> None:
        index = corpus_index.CorpusIndex(build_corpus(tmp_path))
        payload = index.hover('alpha:target-skill')
        assert payload is not None
        assert payload['inbound_edges'] >= 1

    def test_returns_none_for_unknown_notation(self, tmp_path: Path) -> None:
        index = corpus_index.CorpusIndex(build_corpus(tmp_path))
        assert index.hover('alpha:no-such-skill') is None


class TestStats:
    def test_reports_coverage_figures(self, tmp_path: Path) -> None:
        base = build_corpus(tmp_path)
        stats = corpus_index.CorpusIndex(base).stats()
        assert stats['components'] >= 3
        assert stats['forward_edges'] >= 1
        assert stats['base_path'] == str(base)

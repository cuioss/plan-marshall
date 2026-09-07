#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the resident corpus index — cursor resolution, definition, references, hover.

Drives the underscore-prefixed helpers directly, through the shared
``conftest.load_script_module`` loader.
"""

from __future__ import annotations

from pathlib import Path

# PLAIN import, deliberately: the typed assertions below rely on mypy seeing the
# real module — the shared loader returns ``Any``, which silently discards them.
import _corpus_index as corpus_index

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
    #
    # The SECOND citation is load-bearing for the per-owner-not-per-edge walk
    # test: it gives `beta:caller` two inbound edges to `alpha:target-skill`, so
    # the edge count EXCEEDS the owner count. At one edge per owner the two
    # walking strategies produce identical numbers and that test cannot tell
    # them apart — see `test_the_walk_runs_once_per_owner_not_once_per_edge`.
    _write(
        base / 'beta' / 'skills' / 'caller' / 'workflow' / 'step.md',
        '# Step\n\nfiller\nfiller\nRun `alpha:target-skill:target_script` here.\n'
        'See Skill: alpha:target-skill for details.\n',
    )
    # A relative-path edge: its citing line carries a PATH, never the notation.
    _write(
        base / 'beta' / 'skills' / 'path-citer' / 'SKILL.md',
        '---\nname: path-citer\ndescription: Cites the target by relative path\n---\n\n'
        '# Path citer\n\nSee [target](../../../alpha/skills/target-skill/SKILL.md).\n',
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
        tokens = corpus_index.expected_tokens('alpha:target-skill')
        for ref in verified:
            line_text = ref.location.path.read_text(encoding='utf-8').split('\n')[ref.location.line]
            assert any(token in line_text for token in tokens)

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


class TestExpectedTokens:
    """An edge's surface form is not always the notation — see `expected_tokens`."""

    def test_three_part_notation_yields_the_script_name(self) -> None:
        assert corpus_index.expected_tokens('a:b:c') == ['a:b:c', 'c']

    def test_two_part_notation_yields_the_skill_name(self) -> None:
        assert corpus_index.expected_tokens('a:b') == ['a:b', 'b']

    def test_colonless_token_yields_only_itself(self) -> None:
        assert corpus_index.expected_tokens('bare') == ['bare']


class TestNonNotationSurfaceFormsVerify:
    """A path edge's line carries a path, so notation-only matching would fail it.

    Verifying against the notation alone marked every ``path`` and ``import``
    edge unverified regardless of correctness, turning the flag into noise. These
    pin the behaviour that fixed it.
    """

    def test_relative_path_edge_verifies(self, tmp_path: Path) -> None:
        index = corpus_index.CorpusIndex(build_corpus(tmp_path))
        path_refs = [
            ref
            for ref in index.references('alpha:target-skill')
            if ref.dep_type == 'path' and ref.source_notation == 'beta:path-citer'
        ]
        assert path_refs, 'expected a relative-path edge from the path-citer skill'
        assert any(ref.verified for ref in path_refs)

    def test_the_verified_line_carries_no_notation_at_all(self, tmp_path: Path) -> None:
        """Guards against the test passing for the wrong reason."""
        index = corpus_index.CorpusIndex(build_corpus(tmp_path))
        for ref in index.references('alpha:target-skill'):
            if ref.dep_type != 'path' or ref.source_notation != 'beta:path-citer' or not ref.verified:
                continue
            line = ref.location.path.read_text(encoding='utf-8').split('\n')[ref.location.line]
            assert 'alpha:target-skill' not in line
            assert 'target-skill' in line
            return
        raise AssertionError('no verified path edge found')


class TestCandidateFilesAreCached:
    """Residency must actually amortise the directory walk.

    `resolve_reference_site` runs once per reverse edge, so an uncached walk made
    `references()` re-scan the same skill directory once per edge — measured at
    ~125 ms for a 443-edge component, and unchanged on repeat calls. A surface
    whose whole justification is residency must not have a hot path that never
    warms up.

    ⭐ **These count real filesystem walks.** Observing only that the cache is
    WRITTEN says nothing about the cache being READ: deleting the read left the
    whole directory green, because a re-walk produces byte-identical candidates,
    so a cache compared against a copy of itself agrees either way and a verdict
    derived from what the cache CONTAINS is derived from the write. The walk is
    counted at ``Path.rglob`` — the one call ``_candidate_files`` makes when it
    misses — so the read is what the assertions actually measure.
    """

    @staticmethod
    def _count_walks(monkeypatch) -> list[Path]:
        """Tally every ``rglob`` from this point on; returns the growing list.

        Installed AFTER the index is built, so the index construction's own walk
        is deliberately outside the tally and the numbers below are the query
        path's alone.
        """
        walks: list[Path] = []
        real_rglob = Path.rglob

        def counting_rglob(path_self, pattern, *args, **kwargs):
            walks.append(path_self)
            return real_rglob(path_self, pattern, *args, **kwargs)

        monkeypatch.setattr(Path, 'rglob', counting_rglob)
        return walks

    def test_the_walk_runs_once_across_repeat_calls(self, tmp_path: Path, monkeypatch) -> None:
        """The cache READ, asserted directly: a second call walks nothing new."""
        index = corpus_index.CorpusIndex(build_corpus(tmp_path))
        walks = self._count_walks(monkeypatch)

        index.references('alpha:target-skill')
        after_first = len(walks)
        assert after_first > 0, (
            'precondition: the first call must actually walk the filesystem, '
            'otherwise the repeat assertion below measures nothing'
        )

        index.references('alpha:target-skill')

        assert len(walks) == after_first, (
            f'the candidate cache was not read: {len(walks) - after_first} extra '
            f'filesystem walk(s) on the repeat call'
        )

    def test_the_walk_runs_once_per_owner_not_once_per_edge(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """One walk per distinct owner, however many edges that owner contributes.

        ``resolve_reference_site`` runs once per reverse edge, so the population
        this is graded against is the edge count, and it must strictly EXCEED the
        owner count. At one edge per owner the two walking strategies produce the
        same number, so the equality below holds on an uncached implementation
        too and the test stops measuring the property in its own name. Both
        counts are published so a fixture drifting back to one-edge-per-owner
        fails here, visibly, rather than passing vacuously below.
        """
        index = corpus_index.CorpusIndex(build_corpus(tmp_path))
        edges = index.index.get_reverse_deps('alpha:target-skill')
        owners = {dep.source.to_notation() for dep in edges}
        assert len(edges) > len(owners), (
            f'precondition: some owner must contribute more than one inbound edge, '
            f'otherwise per-owner and per-edge walking are indistinguishable; got '
            f'{len(edges)} edge(s) across {len(owners)} owner(s)'
        )

        walks = self._count_walks(monkeypatch)
        index.references('alpha:target-skill')

        assert len(walks) == len(owners), (
            f'expected one walk per distinct owner ({len(owners)}), got {len(walks)} '
            f'across {len(edges)} edge(s)'
        )

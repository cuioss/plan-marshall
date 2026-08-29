#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression pinning the ``delta_coverage`` fact the surface publishes per round.

The defect this closes: a scoped round whose whole delta is content the pass
surfaces nothing for re-surfaces the previous round's candidates unchanged and
returns clean. In the fields the surface published before this fact, that round
was INDISTINGUISHABLE from one that looked at the same files and genuinely found
nothing — ``surface_scope``, ``files_in_scope`` and ``scope_statement`` are all
properties of the round's INPUT, so two rounds over the same file set render them
identically no matter what either round observed.

The central case below is therefore a matched pair over ONE file set: a round
that surfaced nothing and a round that surfaced something. It asserts both that
the pre-existing scope statement fails to separate them — the reason the new
fact is needed, executed rather than claimed — and that ``delta_coverage`` does.

These tests are red-first against the pre-fix code by construction: it exports no
``_compute_delta_coverage``, ``_classify_content`` or ``CONTENT_CLASSES``, so the
module-level import fails before any assertion runs.
"""

import subprocess  # noqa: I001
from pathlib import Path

import pytest

from _self_review_detectors import (
    CONTENT_CLASSES,
    _candidate_files,
    _classify_content,
    _compute_delta_coverage,
)
from conftest import get_script_path, run_script
from self_review import _format_scope_statement

# =============================================================================
# Content classification
# =============================================================================


#: One representative path per declared content class. Kept as (path, class)
#: pairs rather than as a set of paths so the SAME data drives both the
#: per-path assertion and the reachability derivation below.
_CLASSIFIED_SAMPLES: tuple[tuple[str, str], ...] = (
    ('marketplace/bundles/b/skills/s/scripts/thing.py', 'python'),
    ('marketplace/bundles/b/skills/s/SKILL.md', 'skill_doc'),
    ('marketplace/bundles/b/skills/s/standards/rules.md', 'standards_doc'),
    ('doc/developer/build.md', 'markdown_other'),
    ('marshal.json', 'structured_config'),
    ('pyproject.toml', 'structured_config'),
    ('config/settings.yaml', 'structured_config'),
    ('config/settings.yml', 'structured_config'),
    ('README.txt', 'other'),
    ('scripts/run.sh', 'other'),
)


class TestContentClassification:
    @pytest.mark.parametrize(('path', 'expected'), _CLASSIFIED_SAMPLES)
    def test_path_lands_in_its_class(self, path, expected):
        assert _classify_content(path) == expected

    def test_every_declared_class_is_reachable(self):
        """No class is declared that the classifier can never produce.

        Derived from the sample table rather than asserted as a count: a class
        added to ``CONTENT_CLASSES`` with no classifier rule — or with a rule no
        sample reaches — fails HERE, instead of being emitted forever as a
        seeded zero that reads as "measured, none found".
        """
        produced = {expected for _, expected in _CLASSIFIED_SAMPLES}

        assert produced == set(CONTENT_CLASSES), (
            f'classes reached by the samples: {sorted(produced)}; declared: '
            f'{sorted(CONTENT_CLASSES)}. A declared class no sample reaches is '
            'either unreachable in the classifier or untested here.'
        )

    def test_a_standards_md_outside_a_standards_dir_is_not_a_standards_doc(self):
        """The class is decided by the DIRECTORY, not by a name resembling one."""
        assert _classify_content('doc/standards.md') == 'markdown_other'

    def test_skill_md_wins_over_its_directory(self):
        """A ``SKILL.md`` sitting under ``standards/`` is still the skill doc."""
        assert _classify_content('b/skills/s/standards/SKILL.md') == 'skill_doc'


# =============================================================================
# Candidate attribution — the mis-attribution guard
# =============================================================================


class TestCandidateAttribution:
    def test_singular_file_key_is_attributed(self):
        files, unattributed = _candidate_files({'regexes': [{'file': 'a.py', 'line': 1}]})

        assert files == {'a.py'}
        assert unattributed == 0

    def test_joined_files_key_credits_every_named_path(self):
        """A cross-file candidate credits ALL its declaring paths, not none.

        ``source_of_truth`` names its paths under a ``; ``-joined ``files`` and
        carries no singular ``file``. Reading only the singular key filed every
        such candidate under "produced no candidate" while it plainly produced
        one — the same mis-attribution the coverage fact exists to expose.
        """
        detected: dict[str, list] = {
            'source_of_truth': [{'name': 'X', 'files': 'a.py; b.py'}]
        }

        files, unattributed = _candidate_files(detected)

        assert files == {'a.py', 'b.py'}
        assert unattributed == 0

    def test_entry_naming_no_path_is_counted_not_dropped(self):
        """A bare-string derived-index member is reported, never absorbed."""
        detected: dict[str, list] = {
            'protected_identifiers': ['some_token'],
            'regexes': [{'line': 3}],
        }

        files, unattributed = _candidate_files(detected)

        assert files == set()
        assert unattributed == 2


# =============================================================================
# The matched pair — a silent round vs a genuinely clean one
# =============================================================================


_SCOPE = ['pkg/mod.py', 'doc/notes.md']


def _silent_round() -> dict:
    """A round that surfaced NOTHING over ``_SCOPE``."""
    return _compute_delta_coverage(_SCOPE, {'regexes': [], 'source_of_truth': []})


def _observing_round() -> dict:
    """A round over the SAME scope that surfaced a candidate for every file."""
    detected: dict[str, list] = {
        'regexes': [{'file': 'pkg/mod.py', 'line': 4}],
        'source_of_truth': [{'name': 'X', 'files': 'doc/notes.md'}],
    }
    return _compute_delta_coverage(_SCOPE, detected)


class TestSilentRoundIsDistinguishableFromACleanOne:
    def test_the_pre_existing_scope_statement_does_not_separate_them(self):
        """The matched control for the whole fact — why it had to be added.

        Both rounds searched the same file set, so every input-derived field
        renders identically. Without this half, the case below would not show
        that ``delta_coverage`` supplies a distinction nothing else did.
        """
        silent, observing = _silent_round(), _observing_round()

        assert silent['files_in_scope'] == observing['files_in_scope']
        assert _format_scope_statement('delta', silent['files_in_scope'], 'abc123') == (
            _format_scope_statement('delta', observing['files_in_scope'], 'abc123')
        )

    def test_delta_coverage_does_separate_them(self):
        silent, observing = _silent_round(), _observing_round()

        assert silent != observing
        assert silent['statement'] != observing['statement']

    def test_the_silent_round_reports_zero_reached(self):
        silent = _silent_round()

        assert silent['files_with_candidates'] == 0
        assert silent['files_without_candidates'] == len(_SCOPE)
        assert silent['classes_present_without_candidates'] == silent['classes_present']

    def test_the_observing_round_reports_full_coverage(self):
        """The matched negative control: a delta entirely in reached classes."""
        observing = _observing_round()

        assert observing['files_with_candidates'] == len(_SCOPE)
        assert observing['files_without_candidates'] == 0
        assert observing['classes_present_without_candidates'] == 0

    def test_the_silent_statement_refuses_to_read_as_a_clean_verdict(self):
        assert 'no evidence' in _silent_round()['statement']


# =============================================================================
# The fact publishes per-class COUNTS, not a flag
# =============================================================================


class TestPerClassCountsNotABoolean:
    def test_every_declared_class_is_emitted_even_when_absent(self):
        """A class with no files reports a zero rather than being omitted.

        A missing key reads as "not measured"; a zero reads as "measured, none
        found". Only the second is true of a class the round genuinely saw no
        file of.
        """
        rows = _observing_round()['by_class']

        assert [row['content_class'] for row in rows] == list(CONTENT_CLASSES)

    def test_counts_are_integers_not_flags(self):
        for row in _observing_round()['by_class']:
            for key in ('files', 'files_with_candidates', 'files_without_candidates'):
                value = row[key]
                assert isinstance(value, int) and not isinstance(value, bool), (
                    f'{row["content_class"]}.{key} is {value!r} — the fact must '
                    'publish per-class counts, not a boolean'
                )

    def test_the_class_partition_is_total_over_the_scope(self):
        """Per-class file counts sum EXACTLY to the reported denominator."""
        coverage = _observing_round()
        rows = coverage['by_class']

        assert sum(row['files'] for row in rows) == coverage['files_in_scope']

    def test_each_class_splits_its_own_files_exactly(self):
        for row in _observing_round()['by_class']:
            assert (
                row['files_with_candidates'] + row['files_without_candidates']
                == row['files']
            )

    def test_a_mixed_round_reports_the_split_per_class(self):
        """The per-class figures discriminate, rather than tracking the total."""
        coverage = _compute_delta_coverage(
            _SCOPE, {'regexes': [{'file': 'pkg/mod.py', 'line': 1}]}
        )
        by_class = {row['content_class']: row for row in coverage['by_class']}

        assert by_class['python']['files_with_candidates'] == 1
        assert by_class['markdown_other']['files_with_candidates'] == 0
        assert by_class['markdown_other']['files_without_candidates'] == 1


class TestEmptyScope:
    def test_an_empty_scope_says_it_observed_nothing_at_all(self):
        """Zero files searched is the absence of a search, not a clean result."""
        coverage = _compute_delta_coverage([], {'regexes': []})

        assert coverage['files_in_scope'] == 0
        assert coverage['classes_present'] == 0
        assert 'absence of a search' in coverage['statement']
        assert [row['content_class'] for row in coverage['by_class']] == list(
            CONTENT_CLASSES
        )


# =============================================================================
# End-to-end — the fact actually reaches the emitted surface
# =============================================================================


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ['git', '-C', str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def _fixture_repo(tmp_path: Path) -> Path:
    """A repo whose feature-branch diff carries one python and one markdown file."""
    repo = tmp_path / 'repo'
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, 'init', '--initial-branch=main')
    _git(repo, 'config', 'user.email', 'test@example.com')
    _git(repo, 'config', 'user.name', 'Test User')
    (repo / 'seed.txt').write_text('seed\n')
    _git(repo, 'add', '-A')
    _git(repo, 'commit', '-m', 'base')
    _git(repo, 'checkout', '-b', 'feature')
    (repo / 'mod.py').write_text('import re\n\nPATTERN = re.compile(r"^a+b$")\n')
    (repo / 'notes.md').write_text('# Heading\n\nProse that MUST hold.\n')
    _git(repo, 'add', '-A')
    return repo


class TestSurfaceEmitsTheFact:
    def test_the_composed_surface_publishes_delta_coverage(self, tmp_path):
        """Wiring check: the computation reaches the emitted TOON.

        Asserted against the raw stdout so the emitted SHAPE is pinned — the
        block header plus the six-row per-class table. A fact computed but never
        emitted would leave every unit case above green while the round the
        defect afflicts still published nothing.
        """
        repo = _fixture_repo(tmp_path)
        script = get_script_path(
            'pm-plugin-development', 'ext-self-review-plan-marshall', 'self_review.py'
        )

        result = run_script(
            script,
            'surface',
            '--plan-id',
            'delta-coverage-regression-plan',
            '--project-dir',
            str(repo),
            '--base-branch',
            'main',
        )

        assert result.success, f'surface failed: stderr={result.stderr}'
        assert 'delta_coverage:' in result.stdout
        assert (
            'by_class[6]{content_class,files,files_with_candidates,'
            'files_without_candidates}:' in result.stdout
        )

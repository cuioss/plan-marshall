# SPDX-License-Identifier: FSL-1.1-ALv2
"""Meta-test: the duplication instrument separates two populations.

The subject is the instrument, not a marketplace script, so this is a root-level
meta-test.

The property under test is the separation itself. A name appearing in several
modules is only a duplicate when the BODY is identical everywhere; a name
carrying more than one body is a set of same-named local helpers, and hoisting
one of those would merge two behaviours. An instrument that reports both under
one heading invites exactly that mistake, so both directions are pinned here.
"""

from __future__ import annotations

import subprocess

import pytest
from _definition_duplication import (
    DEFINITION,
    collect_definitions,
    format_report,
    main,
    partition,
    survey_refs,
)

#: Same name, same body, in two modules — a duplicate with a home.
HOMED_A = '''\
def build_plan():
    return {'id': 'p'}
'''

HOMED_B = '''\
def build_plan():
    return {'id': 'p'}


def other():
    return 2
'''

#: Same name, DIFFERENT bodies — two behaviours, not a duplicate.
FORKED_A = '''\
def seed():
    return 1
'''

FORKED_B = '''\
def seed():
    return 2
'''


def _run(repo, *args: str) -> None:
    """Run one git command in ``repo`` and fail the test on a non-zero exit."""
    result = subprocess.run(
        ['git', '-C', str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, f'git {" ".join(args)} failed: {result.stderr}'


@pytest.fixture
def planted_duplicate_repo(tmp_path):
    """A repo carrying one true duplicate and one same-name-different-body pair.

    Both populations are planted in the same commit so a single survey has to
    tell them apart rather than being asked about one at a time.
    """
    repo = tmp_path / 'repo'
    (repo / 'pkg').mkdir(parents=True)
    _run(repo.parent, 'init', str(repo))
    _run(repo, 'config', 'user.email', 'meta-test@example.invalid')
    _run(repo, 'config', 'user.name', 'meta-test')

    (repo / 'pkg' / '_alpha_fixtures.py').write_text(HOMED_A + FORKED_A, encoding='utf-8')
    (repo / 'pkg' / '_beta_fixtures.py').write_text(HOMED_B + FORKED_B, encoding='utf-8')
    _run(repo, 'add', 'pkg')
    _run(repo, 'commit', '-m', 'planted')
    _run(repo, 'branch', 'before-ref')
    return repo


def _survey(repo) -> dict:
    side: dict = survey_refs('before-ref', 'HEAD', ['pkg'], repo)['after']
    return side


def test_identical_bodies_are_reported_as_a_duplicate_with_a_home(planted_duplicate_repo):
    """A name whose body matches everywhere is safe to hoist and is named as such."""
    homed = _survey(planted_duplicate_repo)['duplicates_with_a_home']

    assert [entry['name'] for entry in homed] == ['build_plan']
    assert homed[0]['occurrences'] == 2


def test_differing_bodies_are_not_reported_as_a_duplicate(planted_duplicate_repo):
    """A name carrying two bodies is kept out of the hoistable population.

    This is the direction that causes damage when it is wrong: hoisting one of
    these would rebind the other consumer to behaviour it never had.
    """
    survey = _survey(planted_duplicate_repo)

    assert 'seed' not in [entry['name'] for entry in survey['duplicates_with_a_home']]
    assert [entry['name'] for entry in survey['multiple_bodies']] == ['seed']
    assert survey['multiple_bodies'][0]['distinct_bodies'] == 2


def test_a_name_used_once_is_in_neither_population(planted_duplicate_repo):
    """A definition appearing once is not duplication and is reported as neither."""
    survey = _survey(planted_duplicate_repo)

    reported = [entry['name'] for entry in survey['duplicates_with_a_home'] + survey['multiple_bodies']]
    assert 'other' not in reported


def test_formatting_differences_do_not_split_a_duplicate():
    """A reflowed comment and re-indentation do not make two bodies different.

    Body comparison is normalised precisely so cosmetic churn does not hide a
    real duplicate behind a formatting difference.
    """
    plain = 'def helper():\n    return 1\n'
    decorated = 'def helper():\n    # a note the other copy lacks\n\n    return  1\n'

    partitioned = partition(
        collect_definitions(plain, 'a.py') + collect_definitions(decorated, 'b.py'),
    )

    assert [entry['name'] for entry in partitioned['duplicates_with_a_home']] == ['helper']


def test_a_method_inside_a_class_is_not_a_candidate():
    """Only module-level definitions are surveyed — a method is scoped by its class."""
    source = 'class Holder:\n    def helper(self):\n        return 1\n'

    names = [occurrence.name for occurrence in collect_definitions(source, 'a.py')]

    assert names == ['Holder']


def test_report_states_the_definition_it_applied(planted_duplicate_repo):
    """The definition is printed, so two runs cannot silently mean different things."""
    rendered = format_report(survey_refs('before-ref', 'HEAD', ['pkg'], planted_duplicate_repo))

    assert DEFINITION in rendered


def test_report_states_the_paths_it_covered(planted_duplicate_repo):
    """The covered paths are printed, so a narrow survey cannot read as a wide one."""
    rendered = format_report(survey_refs('before-ref', 'HEAD', ['pkg'], planted_duplicate_repo))

    assert 'paths covered: pkg' in rendered


def test_report_carries_both_refs(planted_duplicate_repo):
    """Both sides are computed and printed — the instrument takes no baseline."""
    rendered = format_report(survey_refs('before-ref', 'HEAD', ['pkg'], planted_duplicate_repo))

    assert 'ref before-ref' in rendered
    assert 'ref HEAD' in rendered


def test_cli_prints_both_populations(planted_duplicate_repo, capsys):
    """The CLI surfaces the separation a caller has to act on."""
    exit_code = main(
        [
            '--before-ref',
            'before-ref',
            '--after-ref',
            'HEAD',
            '--paths',
            'pkg',
            '--repo',
            str(planted_duplicate_repo),
        ]
    )

    out = capsys.readouterr().out
    assert exit_code == 0
    assert 'duplicates with a home (1)' in out
    assert 'names carrying more than one body (1)' in out

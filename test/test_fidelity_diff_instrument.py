# SPDX-License-Identifier: FSL-1.1-ALv2
"""Meta-test: the fidelity-diff instrument names a planted loss.

The subject is the instrument, not a marketplace script, so this is a root-level
meta-test.

The property under test is the one that makes the instrument worth having: it
compares multisets, so a change that removes one element and adds another is
reported as a LOSS even though the totals moved by a net zero. A count
comparison cannot see that case, and it is the case a refactor actually
produces.
"""

from __future__ import annotations

import subprocess

import pytest
from _fidelity_diff import FACET_DEFINITIONS, compare_refs, format_report, has_loss, main

BEFORE_MODULE = '''\
# a comment that survives
class TestKept:
    def test_kept(self):
        assert True

    def test_removed(self):
        assert True
'''

AFTER_MODULE = '''\
# a comment that survives
class TestKept:
    def test_kept(self):
        assert True

    def test_added(self):
        assert True
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
def planted_loss_repo(tmp_path):
    """A repo whose second commit swaps one test for another.

    The swap is what makes the fixture a control rather than a demonstration:
    the test count is identical at both commits, so an instrument that compares
    counts reports nothing and only a multiset comparison finds the loss.
    """
    repo = tmp_path / 'repo'
    (repo / 'pkg').mkdir(parents=True)
    _run(repo.parent, 'init', str(repo))
    _run(repo, 'config', 'user.email', 'meta-test@example.invalid')
    _run(repo, 'config', 'user.name', 'meta-test')

    target = repo / 'pkg' / 'test_subject.py'
    target.write_text(BEFORE_MODULE, encoding='utf-8')
    _run(repo, 'add', 'pkg/test_subject.py')
    _run(repo, 'commit', '-m', 'before')
    _run(repo, 'branch', 'before-ref')

    target.write_text(AFTER_MODULE, encoding='utf-8')
    _run(repo, 'add', 'pkg/test_subject.py')
    _run(repo, 'commit', '-m', 'after')
    return repo


def test_planted_loss_is_reported_as_a_lost_identity(planted_loss_repo):
    """The removed test is named in `lost`, not absorbed by the added one."""
    report = compare_refs('before-ref', 'HEAD', ['pkg'], planted_loss_repo)

    identities = report['facets']['test_identities']
    assert [item for item in identities['lost'] if item.endswith('test_removed')]
    assert [item for item in identities['gained'] if item.endswith('test_added')]


def test_a_net_zero_delta_still_reports_the_loss(planted_loss_repo):
    """The totals match at both refs, and the instrument still reports a loss.

    This is the assertion that separates a multiset comparison from a count
    comparison: equal totals are exactly the state in which a count check
    reports success.
    """
    report = compare_refs('before-ref', 'HEAD', ['pkg'], planted_loss_repo)

    identities = report['facets']['test_identities']
    assert identities['before_total'] == identities['after_total']
    assert has_loss(report)


def test_an_unchanged_tree_reports_no_loss(planted_loss_repo):
    """Comparing a ref against itself reports nothing lost and nothing gained."""
    report = compare_refs('HEAD', 'HEAD', ['pkg'], planted_loss_repo)

    assert not has_loss(report)
    for facet in report['facets'].values():
        assert facet['lost'] == []
        assert facet['gained'] == []


def test_a_removed_comment_is_reported_as_lost(tmp_path):
    """A dropped comment is a loss — prose is a facet, not decoration."""
    repo = tmp_path / 'repo'
    (repo / 'pkg').mkdir(parents=True)
    _run(repo.parent, 'init', str(repo))
    _run(repo, 'config', 'user.email', 'meta-test@example.invalid')
    _run(repo, 'config', 'user.name', 'meta-test')
    target = repo / 'pkg' / 'test_prose.py'
    target.write_text('# the reason this exists\nVALUE = 1\n', encoding='utf-8')
    _run(repo, 'add', 'pkg/test_prose.py')
    _run(repo, 'commit', '-m', 'before')
    _run(repo, 'branch', 'before-ref')
    target.write_text('VALUE = 1\n', encoding='utf-8')
    _run(repo, 'add', 'pkg/test_prose.py')
    _run(repo, 'commit', '-m', 'after')

    report = compare_refs('before-ref', 'HEAD', ['pkg'], repo)

    assert 'the reason this exists' in report['facets']['comments']['lost']


def test_report_states_the_definition_it_applied(planted_loss_repo):
    """Every facet's definition is printed, so two runs cannot mean different things."""
    rendered = format_report(compare_refs('before-ref', 'HEAD', ['pkg'], planted_loss_repo))

    for name, definition in FACET_DEFINITIONS.items():
        assert name in rendered
        assert definition in rendered


def test_report_states_the_paths_it_covered(planted_loss_repo):
    """The covered paths are printed, so a narrow run cannot read as a whole-tree one."""
    rendered = format_report(compare_refs('before-ref', 'HEAD', ['pkg'], planted_loss_repo))

    assert 'paths covered: pkg' in rendered


def test_cli_exits_non_zero_on_a_planted_loss(planted_loss_repo, capsys):
    """The CLI reports the loss and fails, so a campaign run cannot ignore it."""
    exit_code = main(
        [
            '--before-ref',
            'before-ref',
            '--after-ref',
            'HEAD',
            '--paths',
            'pkg',
            '--repo',
            str(planted_loss_repo),
        ]
    )

    assert exit_code == 1
    assert 'test_removed' in capsys.readouterr().out


def test_cli_exits_zero_when_nothing_was_lost(planted_loss_repo, capsys):
    """The negative control: no loss means exit 0, so the failure above is meaningful."""
    exit_code = main(
        [
            '--before-ref',
            'HEAD',
            '--after-ref',
            'HEAD',
            '--paths',
            'pkg',
            '--repo',
            str(planted_loss_repo),
        ]
    )

    assert exit_code == 0
    capsys.readouterr()

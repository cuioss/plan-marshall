# SPDX-License-Identifier: FSL-1.1-ALv2
"""Meta-test: the banner-attribution instrument detects a planted misfiling.

The subject is the instrument, not a marketplace script, so this is a root-level
meta-test.

Two properties are pinned, and the second is the one that keeps the instrument
usable. The first is detection: a construct moved under a heading that
introduces a different section is reported. The second is the negative control
set — a construct correctly filed, a subject word several headings share, and a
construct claimed by two headings are each left alone. A detector that fires on
those is worse than no detector, because its output stops being read.
"""

from __future__ import annotations

import subprocess

import pytest
from _banner_attribution import (
    DEFINITION,
    collect_banners,
    compare_refs,
    distinctive_tokens,
    format_report,
    main,
    scan_module,
    tokenise,
)

#: Two sections whose subjects are distinctive, with each construct filed
#: correctly. The negative control.
CORRECTLY_FILED = '''\
# --- tokenizer ---


def tokenizer_entry():
    return 1


# --- renderer ---


def renderer_entry():
    return 2
'''

#: The same two sections with the renderer construct moved under the tokenizer
#: heading. The planted misattribution.
MISFILED = '''\
# --- tokenizer ---


def tokenizer_entry():
    return 1


def renderer_entry():
    return 2


# --- renderer ---


def renderer_other():
    return 3
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
def planted_misattribution_repo(tmp_path):
    """A repo whose second commit moves a construct under the wrong heading."""
    repo = tmp_path / 'repo'
    (repo / 'pkg').mkdir(parents=True)
    _run(repo.parent, 'init', str(repo))
    _run(repo, 'config', 'user.email', 'meta-test@example.invalid')
    _run(repo, 'config', 'user.name', 'meta-test')

    target = repo / 'pkg' / 'subject.py'
    target.write_text(CORRECTLY_FILED, encoding='utf-8')
    _run(repo, 'add', 'pkg/subject.py')
    _run(repo, 'commit', '-m', 'before')
    _run(repo, 'branch', 'before-ref')

    target.write_text(MISFILED, encoding='utf-8')
    _run(repo, 'add', 'pkg/subject.py')
    _run(repo, 'commit', '-m', 'after')
    return repo


def test_planted_misattribution_is_detected():
    """A construct under a heading naming a different subject is reported."""
    findings = scan_module(MISFILED, 'pkg/subject.py')

    assert [finding.construct for finding in findings] == ['renderer_entry']
    assert findings[0].under_banner == 'tokenizer'
    assert findings[0].belongs_under == 'renderer'


def test_a_correctly_filed_construct_is_not_reported():
    """The negative control: every construct under its own heading yields nothing."""
    assert scan_module(CORRECTLY_FILED, 'pkg/subject.py') == []


def test_a_token_shared_by_two_headings_attributes_nothing():
    """A construct matching a word several headings carry is left alone.

    A non-distinctive match is a coincidence of vocabulary rather than evidence
    of where the construct belongs, so it must not produce a finding.
    """
    source = (
        '# --- alpha store ---\n\n\ndef cache_probe():\n    return 1\n\n\n'
        '# --- beta cache ---\n\n\ndef beta_entry():\n    return 2\n\n\n'
        '# --- gamma cache ---\n\n\ndef gamma_entry():\n    return 3\n'
    )

    reported = [finding.construct for finding in scan_module(source, 'pkg/subject.py')]

    assert 'cache_probe' not in reported


def test_a_construct_claimed_by_two_headings_is_left_alone():
    """An ambiguous construct is not attributed — two claimants say no more than none."""
    source = (
        '# --- alpha ---\n\n\ndef beta_gamma_probe():\n    return 0\n\n\n'
        '# --- beta ---\n\n\ndef beta_entry():\n    return 1\n\n\n'
        '# --- gamma ---\n\n\ndef gamma_entry():\n    return 2\n'
    )

    reported = [finding.construct for finding in scan_module(source, 'pkg/subject.py')]

    assert 'beta_gamma_probe' not in reported


def test_a_framed_block_yields_only_its_first_line_as_the_heading():
    """A framed comment block is consumed whole, so its prose is not a heading.

    Without this the closing rule line reads as the opening of a new banner and
    adopts whatever comment follows, turning an ordinary sentence into a heading
    that attributes constructs by the words it happens to contain.
    """
    source = (
        '# ------------------------------\n'
        '# tokenizer\n'
        '# a sentence about the renderer that is not a heading\n'
        '# ------------------------------\n'
        'def tokenizer_entry():\n'
        '    return 1\n'
    )

    assert [banner.text for banner in collect_banners(source)] == ['tokenizer']


def test_a_two_character_rule_run_is_not_a_heading():
    """The matched control on the inline lower bound: three rules, not two.

    A two-character run is the shape of a CLI flag in ordinary prose, so a
    ``{2,}`` bound reads ``# --plan-id is forwarded ...`` as a heading. The
    positive half pins that the documented three-rule form still IS a heading,
    so the bound cannot be raised until the real form stops being recognised.
    """
    source = (
        '# --- tokenizer ---\n'
        '# --plan-id is forwarded to every child call\n'
    )

    assert [banner.text for banner in collect_banners(source)] == ['tokenizer']


def test_a_prose_flag_comment_attributes_nothing():
    """The effect control: a prose comment carrying a flag fabricates no finding.

    A spurious banner both steals enclosure from every construct beneath it and
    injects the sentence's words into the distinctive-token set, so it can
    fabricate a misattribution or destroy a real heading's distinctiveness.
    Planting one into an otherwise correctly-filed module must change nothing.
    """
    source = (
        '# --- tokenizer ---\n'
        '# --renderer is forwarded to every child invocation\n'
        '\n\ndef tokenizer_entry():\n    return 1\n\n\n'
        '# --- renderer ---\n\n\ndef renderer_entry():\n    return 2\n'
    )

    assert scan_module(source, 'pkg/subject.py') == []


def test_a_module_with_one_section_reports_nothing():
    """With fewer than two headings there is no other section to belong under."""
    source = '# --- tokenizer ---\n\n\ndef renderer_entry():\n    return 1\n'

    assert scan_module(source, 'pkg/subject.py') == []


def test_distinctive_tokens_exclude_tokens_two_headings_carry():
    """Only a token unique to one heading is allowed to attribute a construct."""
    banners = collect_banners('# --- alpha cache ---\n# --- beta cache ---\n')

    distinctive = distinctive_tokens(banners)

    assert 'cache' not in distinctive
    assert set(distinctive) == {'alpha', 'beta'}


def test_tokenise_drops_structural_vocabulary():
    """Generic section words are dropped — they attribute nothing on their own."""
    assert tokenise('public entry point') == frozenset()
    assert tokenise('tokenizer_entry') == frozenset({'tokenizer'})


def test_report_states_the_definition_and_paths(planted_misattribution_repo):
    """The definition and covered paths are printed, so a run states what it meant."""
    rendered = format_report(compare_refs('before-ref', 'HEAD', ['pkg'], planted_misattribution_repo))

    assert DEFINITION in rendered
    assert 'paths covered: pkg' in rendered


def test_introduced_names_only_what_the_change_added(planted_misattribution_repo):
    """The verdict is the delta: the misfiling appears at the after-ref only."""
    report = compare_refs('before-ref', 'HEAD', ['pkg'], planted_misattribution_repo)

    assert report['before']['findings'] == []
    assert [finding.construct for finding in report['introduced']] == ['renderer_entry']


def test_a_pre_existing_misattribution_is_not_counted_as_introduced(planted_misattribution_repo):
    """Comparing the after-ref against itself introduces nothing, though findings remain."""
    report = compare_refs('HEAD', 'HEAD', ['pkg'], planted_misattribution_repo)

    assert report['after']['findings'] != []
    assert report['introduced'] == []


def test_cli_exits_non_zero_on_an_introduced_misattribution(planted_misattribution_repo, capsys):
    """The CLI fails on a misfiling the change introduced."""
    exit_code = main(
        [
            '--before-ref',
            'before-ref',
            '--after-ref',
            'HEAD',
            '--paths',
            'pkg',
            '--repo',
            str(planted_misattribution_repo),
        ]
    )

    assert exit_code == 1
    assert 'renderer_entry' in capsys.readouterr().out


def test_cli_exits_zero_when_the_change_introduced_nothing(planted_misattribution_repo, capsys):
    """The negative control: a standing baseline alone does not fail the run."""
    exit_code = main(
        [
            '--before-ref',
            'HEAD',
            '--after-ref',
            'HEAD',
            '--paths',
            'pkg',
            '--repo',
            str(planted_misattribution_repo),
        ]
    )

    assert exit_code == 0
    capsys.readouterr()

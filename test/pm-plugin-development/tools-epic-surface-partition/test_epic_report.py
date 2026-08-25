#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the seven-section report — its sections, provenance, and report-only contract.

The corpus and the tree are built under ``tmp_path`` and reached by patching the
entry point's own store and checkout resolvers, so the real orchestrator store is
never read and never written.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pytest

from conftest import add_skill_scripts_to_path, get_script_path, load_script_module, run_script

BUNDLE = 'pm-plugin-development'
SKILL = 'tools-epic-surface-partition'

add_skill_scripts_to_path(BUNDLE, SKILL)
entry = load_script_module(BUNDLE, SKILL, 'epic-surface-partition.py', register=False)

#: Every section the report is required to render, in order.
EXPECTED_SECTIONS = (
    'partition',
    'attribution',
    'disagreements',
    'not_derivable',
    'injected_controls',
    'test_count',
    'provenance',
)


# --- scaffolding -------------------------------------------------------------


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def build_world(root: Path, specs: dict[str, str], modules: tuple[str, ...]) -> tuple[Path, Path]:
    """Return ``(epic_dir, repo_root)`` for a corpus and a tree built under ``root``."""
    repo = root / 'repo'
    (repo / 'test').mkdir(parents=True)
    (repo / 'marketplace').mkdir(parents=True)
    for rel in modules:
        write(repo / rel, 'def test_placeholder():\n    assert True\n')

    epic_dir = root / 'epic'
    for name, body in specs.items():
        write(epic_dir / 'plans' / name, body)
    return epic_dir, repo


def render(
    monkeypatch, epic_dir: Path, repo: Path, tests_before: int | None = None
) -> dict[str, Any]:
    monkeypatch.setattr(entry, 'get_store_dir', lambda *a, **k: epic_dir)
    monkeypatch.setattr(entry, 'cwd_checkout_root', lambda: str(repo))
    args = argparse.Namespace(epic='fixture-epic', budget=400, tests_before=tests_before)
    report: dict[str, Any] = entry.cmd_report(args)
    return report


#: A corpus that disagrees with itself: two plans claim the same subtree, one
#: module is claimed by nobody, and two plans claim bundle-tree paths.
DISAGREEING_SPECS = {
    'PLAN-300.md': '# PLAN-300\n\n## Expected Surface\n\n'
    '- Adds `test/alpha/**`\n- Touches `marketplace/bundles/demo/**`\n',
    'PLAN-310.md': '# PLAN-310\n\n## Expected Surface\n\n- Also adds `test/alpha/**`\n',
}
DISAGREEING_MODULES = ('test/alpha/test_one.py', 'test/orphan/test_two.py')

#: A corpus that partitions cleanly and claims nothing under the bundle tree.
CLEAN_SPECS = {'PLAN-400.md': '# PLAN-400\n\n## Expected Surface\n\n- Adds `test/alpha/**`\n'}
CLEAN_MODULES = ('test/alpha/test_one.py',)


@pytest.fixture
def disagreeing(tmp_path: Path, monkeypatch) -> dict[str, Any]:
    epic_dir, repo = build_world(tmp_path, dict(DISAGREEING_SPECS), DISAGREEING_MODULES)
    return render(monkeypatch, epic_dir, repo)


@pytest.fixture
def clean(tmp_path: Path, monkeypatch) -> dict[str, Any]:
    epic_dir, repo = build_world(tmp_path, dict(CLEAN_SPECS), CLEAN_MODULES)
    return render(monkeypatch, epic_dir, repo)


def section(report: dict[str, Any], name: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = report['sections']
    return next(row for row in rows if row['section'] == name)


# --- the seven sections ------------------------------------------------------


def test_all_seven_sections_are_rendered(disagreeing) -> None:
    assert [row['section'] for row in disagreeing['sections']] == list(EXPECTED_SECTIONS)


@pytest.mark.parametrize('name', EXPECTED_SECTIONS)
def test_every_section_carries_its_producing_command(disagreeing, name: str) -> None:
    command = section(disagreeing, name)['command']

    assert command.startswith('python3 .plan/execute-script.py')
    assert len(command) > len('python3 .plan/execute-script.py ')


@pytest.mark.parametrize('name', EXPECTED_SECTIONS)
def test_every_section_carries_a_summary(disagreeing, name: str) -> None:
    assert section(disagreeing, name)['summary'].strip()


def test_partition_tally_reports_all_four_verdicts(disagreeing) -> None:
    verdicts = [row['verdict'] for row in disagreeing['partition_tally']]

    assert verdicts == [
        'claimed',
        'unclaimed',
        'multiply_claimed',
        'not_derivable',
    ]


# --- disagreements are listed PER INSTANCE -----------------------------------


def test_disagreements_are_listed_per_instance_not_merely_counted(disagreeing) -> None:
    paths = {row['path'] for row in disagreeing['disagreements']}

    assert paths == {'test/alpha/test_one.py', 'test/orphan/test_two.py'}


def test_each_disagreement_names_its_verdict(disagreeing) -> None:
    by_path = {row['path']: row['verdict'] for row in disagreeing['disagreements']}

    assert by_path['test/alpha/test_one.py'] == 'multiply_claimed'
    assert by_path['test/orphan/test_two.py'] == 'unclaimed'


def test_multiply_claimed_disagreement_names_every_claiming_plan(disagreeing) -> None:
    row = next(r for r in disagreeing['disagreements'] if r['path'] == 'test/alpha/test_one.py')

    assert row['plans'] == 'PLAN-300,PLAN-310'


def test_clean_corpus_lists_no_disagreements(clean) -> None:
    assert clean['disagreements'] == []


# --- not-derivable is first-class --------------------------------------------


def test_not_derivable_section_is_emitted_even_when_empty(clean) -> None:
    assert section(clean, 'not_derivable') is not None
    assert clean['not_derivable_modules'] == []
    assert clean['not_derivable_specs'] == []


def test_not_derivable_section_is_present_for_a_disagreeing_corpus(disagreeing) -> None:
    assert 'not_derivable_modules' in disagreeing
    assert 'not_derivable_specs' in disagreeing


def test_unresolvable_span_is_reported_as_a_not_derivable_spec(
    tmp_path: Path, monkeypatch
) -> None:
    specs = dict(CLEAN_SPECS)
    specs['PLAN-410.md'] = '# PLAN-410\n\n## Expected Surface\n\n- Touches `test_two_*.py`\n'
    epic_dir, repo = build_world(tmp_path, specs, ('test/alpha/test_one.py', 'test/x/test_two_a.py'))

    report = render(monkeypatch, epic_dir, repo)

    assert [row['plan_id'] for row in report['not_derivable_specs']] == ['PLAN-410']
    assert [row['path'] for row in report['not_derivable_modules']] == ['test/x/test_two_a.py']


# --- provenance ---------------------------------------------------------------


def test_provenance_names_the_standard_given_locations(disagreeing) -> None:
    by_claim = {row['claim']: row['value'] for row in disagreeing['provenance_placement']}

    assert by_claim['test_mirror_location'] == 'test/{bundle}/{skill}/'
    assert (
        by_claim['script_directory_location']
        == 'marketplace/bundles/{bundle}/skills/{skill}/scripts/'
    )


@pytest.mark.parametrize(
    ('claim', 'citation_fragment'),
    [
        ('test_mirror_location', 'testing-standards.md'),
        ('script_directory_location', 'cross-skill-integration.md'),
        ('script_directory_location', 'python-implementation.md'),
    ],
    ids=['test_mirror', 'script_dir_cross_skill', 'script_dir_python_impl'],
)
def test_provenance_cites_its_source(disagreeing, claim: str, citation_fragment: str) -> None:
    citations = {
        row['claim']: row['citation'] for row in disagreeing['provenance_placement']
    }

    assert citation_fragment in citations[claim]


def test_provenance_reports_the_overlap_as_live_and_names_the_paths(disagreeing) -> None:
    assert disagreeing['provenance']['overlap_live'] is True
    assert [row['path'] for row in disagreeing['provenance_overlaps']] == [
        'marketplace/bundles/demo/**'
    ]
    assert disagreeing['provenance_overlaps'][0]['plan_id'] == 'PLAN-300'


def test_provenance_section_is_not_omitted_when_the_overlap_set_is_empty(clean) -> None:
    assert section(clean, 'provenance') is not None
    assert clean['provenance']['overlap_live'] is False
    assert clean['provenance']['overlap_count'] == 0
    assert clean['provenance_overlaps'] == []
    assert clean['provenance_placement']


def test_provenance_placement_is_reported_regardless_of_overlap(clean) -> None:
    assert len(clean['provenance_placement']) == 2


# --- injected controls and the test count ------------------------------------


def test_injected_controls_are_reported_with_their_demonstrating_control(disagreeing) -> None:
    controls = disagreeing['injected_controls']

    assert {row['control'] for row in controls} == {
        'injected_unclaimed_directory',
        'injected_double_claim',
        'clean_corpus_control',
        'injected_root_span',
        'injected_container_span',
    }
    assert all(row['demonstrated_by'].strip() for row in controls)


def test_test_count_reports_before_and_after(tmp_path: Path, monkeypatch) -> None:
    epic_dir, repo = build_world(tmp_path, dict(CLEAN_SPECS), CLEAN_MODULES)

    report = render(monkeypatch, epic_dir, repo, tests_before=7)

    assert report['test_count']['before'] == 7
    assert report['test_count']['after'] == 1


def test_test_count_states_when_the_before_figure_was_not_supplied(clean) -> None:
    assert clean['test_count']['before'] == 'not_supplied'
    assert clean['test_count']['method']


# --- the report-only contract -------------------------------------------------


def test_report_declares_itself_report_only(disagreeing) -> None:
    assert disagreeing['report_only'] is True
    assert disagreeing['gates_build'] is False


def test_disagreement_does_not_make_the_report_fail(disagreeing) -> None:
    assert disagreeing['status'] == 'success'
    assert disagreeing['disagreements']


def test_report_exits_zero_on_an_unresolvable_epic() -> None:
    script = get_script_path(BUNDLE, SKILL, 'epic-surface-partition.py')

    result = run_script(str(script), 'report', '--epic', 'no-such-epic-slug-exists')

    assert result.returncode == 0
    assert 'status: error' in result.stdout

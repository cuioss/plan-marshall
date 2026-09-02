#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the rendered report — its sections, provenance, and report-only contract.

The corpus and the tree are built under ``tmp_path`` and reached by patching the
entry point's own store and checkout resolvers, so the real orchestrator store is
never read and never written.

⛔ :data:`EXPECTED_SECTIONS` is a HAND-WRITTEN mirror of the shipped
``_SECTION_ORDER`` and must stay one. Deriving it from the tuple it checks would
make every assertion below vacuous: the test could then never disagree with the
implementation, which is the entire reason it exists.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pytest

from conftest import add_skill_scripts_to_path, get_script_path, load_script_module, run_script

BUNDLE = 'pm-plugin-development'
SKILL = 'tools-epic-surface-partition'

add_skill_scripts_to_path(BUNDLE, SKILL)
entry = load_script_module(BUNDLE, SKILL, 'epic-surface-partition.py', register=False)

#: Every section the report is required to render, in order. Hand-written on
#: purpose — see the module docstring.
EXPECTED_SECTIONS = (
    'partition',
    'attribution',
    'disagreements',
    'contested',
    'lifecycle',
    'swept',
    'not_derivable',
    'injected_controls',
    'test_count',
    'baseline_drift',
    'provenance',
)


# --- scaffolding -------------------------------------------------------------


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def build_world(
    root: Path,
    specs: dict[str, str],
    modules: tuple[str, ...],
    ledger: dict[str, str] | None = None,
) -> tuple[Path, Path]:
    """Return ``(epic_dir, repo_root)`` for a corpus and a tree built under ``root``.

    ``ledger`` is the epic's plan queue as ``plan_id -> status``. Omitting it
    leaves the epic directory with no ledger at all, which is the DEGRADED input
    state the report must state rather than absorb — so the default here is a
    fixture of that state, never a stand-in for a read one.
    """
    repo = root / 'repo'
    (repo / 'test').mkdir(parents=True)
    (repo / 'marketplace').mkdir(parents=True)
    for rel in modules:
        write(repo / rel, 'def test_placeholder():\n    assert True\n')

    epic_dir = root / 'epic'
    for name, body in specs.items():
        write(epic_dir / 'plans' / name, body)
    if ledger is not None:
        payload = {'plans': [{'id': pid, 'status': st} for pid, st in ledger.items()]}
        write(epic_dir / 'status.json', json.dumps(payload))
    return epic_dir, repo


def render(
    monkeypatch,
    epic_dir: Path,
    repo: Path,
    tests_before: int | None = None,
    baseline_findings: str | None = None,
) -> dict[str, Any]:
    monkeypatch.setattr(entry, 'get_store_dir', lambda *a, **k: epic_dir)
    monkeypatch.setattr(entry, 'cwd_checkout_root', lambda: str(repo))
    args = argparse.Namespace(
        epic='fixture-epic',
        budget=400,
        tests_before=tests_before,
        baseline_findings=baseline_findings,
    )
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


# --- the rendered sections ---------------------------------------------------


def test_every_expected_section_is_rendered_in_order(disagreeing) -> None:
    """A claim about ALL the sections, not most of them, and about their order."""
    assert [row['section'] for row in disagreeing['sections']] == list(EXPECTED_SECTIONS)


@pytest.mark.parametrize('name', EXPECTED_SECTIONS)
def test_every_section_carries_its_producing_command(disagreeing, name: str) -> None:
    command = section(disagreeing, name)['command']

    assert command.startswith('python3 .plan/execute-script.py')
    assert len(command) > len('python3 .plan/execute-script.py ')


@pytest.mark.parametrize('name', EXPECTED_SECTIONS)
def test_every_section_carries_a_summary(disagreeing, name: str) -> None:
    assert section(disagreeing, name)['summary'].strip()


def test_partition_tally_reports_every_verdict(disagreeing) -> None:
    verdicts = [row['verdict'] for row in disagreeing['partition_tally']]

    assert verdicts == [
        'claimed',
        'unclaimed',
        'contested',
        'swept',
        'not_derivable',
    ]


# --- disagreements are listed PER INSTANCE -----------------------------------


def test_disagreements_are_listed_per_instance_not_merely_counted(disagreeing) -> None:
    paths = {row['path'] for row in disagreeing['disagreements']}

    assert paths == {'test/alpha/test_one.py', 'test/orphan/test_two.py'}


def test_each_disagreement_names_its_verdict(disagreeing) -> None:
    by_path = {row['path']: row['verdict'] for row in disagreeing['disagreements']}

    assert by_path['test/alpha/test_one.py'] == 'contested'
    assert by_path['test/orphan/test_two.py'] == 'unclaimed'


def test_contested_disagreement_names_every_claiming_plan(disagreeing) -> None:
    row = next(r for r in disagreeing['disagreements'] if r['path'] == 'test/alpha/test_one.py')

    assert row['plans'] == 'PLAN-300,PLAN-310'


def test_clean_corpus_lists_no_disagreements(clean) -> None:
    assert clean['disagreements'] == []


# --- the contested, swept and drift populations ------------------------------
#
# Each is emitted even when EMPTY, so an absent population reads as measured
# rather than as missing — the same discipline the verdict tally already follows.


def test_the_contested_set_is_a_population_of_its_own(disagreeing) -> None:
    """Separate from the merged disagreement list, and enumerated per instance."""
    assert [row['path'] for row in disagreeing['contested']] == ['test/alpha/test_one.py']
    assert disagreeing['contested'][0]['plans'] == 'PLAN-300,PLAN-310'


def test_the_contested_set_is_emitted_even_when_empty(clean) -> None:
    assert section(clean, 'contested') is not None
    assert clean['contested'] == []


def test_the_sweep_populations_are_emitted_even_when_empty(clean) -> None:
    """No spec here declares itself a sweep, and the sections still render."""
    assert section(clean, 'swept') is not None
    assert clean['sweep_plans'] == []
    assert clean['sweep_crossings'] == []


def test_a_declared_sweep_is_reported_as_crossing_rather_than_owning(
    tmp_path: Path, monkeypatch
) -> None:
    specs = dict(CLEAN_SPECS)
    specs['PLAN-420.md'] = (
        '# PLAN-420\n\n## Expected Surface\n\n'
        '- Adds `test/alpha/**` — this plan crosses every slice, so its surface is the '
        'test tree entire, and it pairs with no other plan\n'
    )
    epic_dir, repo = build_world(tmp_path, specs, CLEAN_MODULES)

    report = render(monkeypatch, epic_dir, repo)

    assert report['sweep_plans'] == ['PLAN-420']
    assert [row['path'] for row in report['sweep_crossings']] == ['test/alpha/test_one.py']
    assert report['contested'] == []


def test_baseline_drift_reports_that_nothing_was_compared_without_a_baseline(clean) -> None:
    """An absent baseline is stated as unsupplied, never rendered as an empty one.

    A zero drift count published by a run that compared nothing is
    indistinguishable from a run that compared and found no drift.
    """
    drift = clean['baseline_drift']

    assert drift['baseline_supplied'] is False
    assert clean['baseline_drift_instances'] == []
    assert section(clean, 'baseline_drift')['summary']


def test_baseline_drift_is_attributed_per_instance(tmp_path: Path, monkeypatch) -> None:
    """Drift names the modules that entered and left the population."""
    epic_dir, repo = build_world(tmp_path, dict(CLEAN_SPECS), CLEAN_MODULES)
    write(repo / 'test/alpha/test_one.py', ''.join(f'# {i}\n' for i in range(500)))
    baseline = tmp_path / 'baseline.txt'
    baseline.write_text('test/alpha/test_gone.py\n', encoding='utf-8')

    report = render(monkeypatch, epic_dir, repo, baseline_findings=str(baseline))

    drift = report['baseline_drift']
    instances = {row['path']: row['drift'] for row in report['baseline_drift_instances']}
    assert drift['baseline_supplied'] is True
    assert instances == {
        'test/alpha/test_one.py': 'added',
        'test/alpha/test_gone.py': 'removed',
    }


def test_baseline_drift_does_not_make_the_report_fail(tmp_path: Path, monkeypatch) -> None:
    """Drift is a comparison result, never a failure."""
    epic_dir, repo = build_world(tmp_path, dict(CLEAN_SPECS), CLEAN_MODULES)
    baseline = tmp_path / 'baseline.txt'
    baseline.write_text('test/alpha/test_gone.py\n', encoding='utf-8')

    report = render(monkeypatch, epic_dir, repo, baseline_findings=str(baseline))

    assert report['status'] == 'success'
    assert report['baseline_drift']['removed_count'] == 1


# --- the plan-lifecycle input ------------------------------------------------
#
# The second input source, rendered as its own block so a ledger fact is never
# read as a corpus fact. Its ABSENCE is a first-class rendered state: the report
# says the ledger was unavailable and why, rather than publishing an all-plans-
# live partition that reads identically to a measured one.


def test_the_lifecycle_section_states_the_degradation_when_no_ledger_is_read(clean) -> None:
    lifecycle = clean['lifecycle']

    assert lifecycle['available'] is False
    assert lifecycle['degradation'] == 'ledger_absent'
    assert lifecycle['ledger_path'].endswith('status.json')
    assert clean['lifecycle_plans'] == []
    assert clean['lifecycle_resolved'] == []


def test_the_degraded_lifecycle_summary_names_the_reason(clean) -> None:
    """The summary a reader sees carries the reason, not only the payload block."""
    assert clean['lifecycle']['degradation'] in section(clean, 'lifecycle')['summary']


def test_a_degraded_ledger_leaves_the_contest_standing(disagreeing) -> None:
    """With no ledger read, nothing is retired and the report is what it always was."""
    assert disagreeing['lifecycle']['available'] is False
    assert [row['path'] for row in disagreeing['contested']] == ['test/alpha/test_one.py']
    assert disagreeing['contested'][0]['retired'] == ''


def test_a_read_ledger_retires_the_finished_plans_claim(tmp_path: Path, monkeypatch) -> None:
    """The same disagreeing corpus, with a ledger: the live plan owns the module."""
    epic_dir, repo = build_world(
        tmp_path,
        dict(DISAGREEING_SPECS),
        DISAGREEING_MODULES,
        ledger={'PLAN-300': 'landed', 'PLAN-310': 'staged'},
    )

    report = render(monkeypatch, epic_dir, repo)

    assert report['lifecycle']['available'] is True
    assert report['lifecycle']['degradation'] == ''
    assert report['contested'] == []
    assert report['lifecycle_resolved'] == [
        {'path': 'test/alpha/test_one.py', 'owner': 'PLAN-310', 'retired': 'PLAN-300'}
    ]


def test_the_ledger_rows_are_rendered_with_the_bucket_each_falls_in(
    tmp_path: Path, monkeypatch
) -> None:
    """The partition that drove the retirement is readable from the output itself."""
    epic_dir, repo = build_world(
        tmp_path,
        dict(DISAGREEING_SPECS),
        DISAGREEING_MODULES,
        ledger={'PLAN-300': 'landed', 'PLAN-310': 'staged'},
    )

    report = render(monkeypatch, epic_dir, repo)

    assert report['lifecycle_plans'] == [
        {'plan_id': 'PLAN-300', 'status': 'landed', 'lifecycle': 'terminal'},
        {'plan_id': 'PLAN-310', 'status': 'staged', 'lifecycle': 'active'},
    ]
    assert report['lifecycle']['terminal_count'] == 1
    assert report['lifecycle']['active_count'] == 1


def test_two_live_plans_keep_the_module_contested_in_the_report(
    tmp_path: Path, monkeypatch
) -> None:
    """⛔ The refusal, carried through to the rendered report."""
    epic_dir, repo = build_world(
        tmp_path,
        dict(DISAGREEING_SPECS),
        DISAGREEING_MODULES,
        ledger={'PLAN-300': 'running', 'PLAN-310': 'staged'},
    )

    report = render(monkeypatch, epic_dir, repo)

    assert report['lifecycle']['available'] is True
    assert [row['path'] for row in report['contested']] == ['test/alpha/test_one.py']
    assert report['contested'][0]['plans'] == 'PLAN-300,PLAN-310'
    assert report['lifecycle_resolved'] == []


@pytest.mark.parametrize('verb', ['partition', 'attribution', 'report'])
def test_an_unknown_ledger_status_is_reported_as_a_structured_error(
    tmp_path: Path, monkeypatch, verb: str
) -> None:
    """Every verb that reads the ledger refuses loudly and names the offending value.

    ``classify`` is absent from this list on purpose: it reads the spec corpus
    alone, so no ledger fault can reach it.
    """
    epic_dir, repo = build_world(
        tmp_path,
        dict(CLEAN_SPECS),
        CLEAN_MODULES,
        ledger={'PLAN-400': 'mothballed'},
    )
    monkeypatch.setattr(entry, 'get_store_dir', lambda *a, **k: epic_dir)
    monkeypatch.setattr(entry, 'cwd_checkout_root', lambda: str(repo))
    args = argparse.Namespace(
        epic='fixture-epic', budget=400, tests_before=None, baseline_findings=None
    )

    payload = getattr(entry, f'cmd_{verb}')(args)

    assert payload['status'] == 'error'
    assert payload['error'] == 'unknown_plan_status'
    assert payload['plan_id'] == 'PLAN-400'
    assert 'mothballed' in payload['plan_status']
    assert payload['known_terminal'] and payload['known_active']


def test_classify_is_unaffected_by_an_unreadable_ledger_status(
    tmp_path: Path, monkeypatch
) -> None:
    """Matched negative for the separation: the corpus verb never reads the ledger."""
    epic_dir, repo = build_world(
        tmp_path, dict(CLEAN_SPECS), CLEAN_MODULES, ledger={'PLAN-400': 'mothballed'}
    )
    monkeypatch.setattr(entry, 'get_store_dir', lambda *a, **k: epic_dir)
    monkeypatch.setattr(entry, 'cwd_checkout_root', lambda: str(repo))

    payload = entry.cmd_classify(argparse.Namespace(epic='fixture-epic'))

    assert payload['status'] == 'success'
    assert 'lifecycle' not in payload


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
        'injected_cross_plan_citation',
        'injected_terminal_claim_retired',
        'injected_active_versus_active',
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

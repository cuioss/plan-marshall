#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Every report section's cited command reproduces the figures that section renders.

The reproducibility claim is made in two places — SKILL.md's ``report`` section
and the section of ``standards/epic-surface-derivation.md`` that documents the
report's rendered sections — and it is a claim about ALL of them, not most of
them. A section whose cited command emits a different population, or measures by
a different method, is the confident-signal-hides-a-caveat defect this derivation
exists to surface, so every section is pinned against the output of the command
it names.

⛔ :data:`FIGURES` is a HAND-WRITTEN mirror of the shipped section set. Deriving
it from ``_SECTION_ORDER`` would make the completeness guard below vacuous — the
map could then never disagree with the implementation it checks.

The corpus and the tree are built under ``tmp_path`` and reached by patching the
entry point's own store and checkout resolvers, so the real orchestrator store is
never read and never written.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from conftest import add_skill_scripts_to_path, get_script_path, load_script_module, run_script

BUNDLE = 'pm-plugin-development'
SKILL = 'tools-epic-surface-partition'
SCRIPT = 'epic-surface-partition.py'

add_skill_scripts_to_path(BUNDLE, SKILL)
entry = load_script_module(BUNDLE, SKILL, SCRIPT, register=False)

#: The epic slug and line budget every verb in a run is invoked with. The budget
#: is deliberately tiny so the fixture modules are all over it and the
#: attribution section has a non-empty population to reproduce.
EPIC = 'fixture-epic'
BUDGET = 1

#: The executor notation a verb-citing section names.
NOTATION = 'pm-plugin-development:tools-epic-surface-partition:epic-surface-partition'

#: The directory holding the tests ``injected_controls`` names. Its parent is the
#: bundle whose module-tests run them, so the cited command's scope is read from
#: where the demonstrations live rather than restated here.
TEST_TREE = Path(__file__).resolve().parent

#: The module shipping the control demonstrations the ``injected_controls``
#: section names. Its ``# --- ...`` banners delimit the control groups: a group's
#: several assertions demonstrate ONE injected failure, so the GROUP — not the
#: individual test — is the unit the section is pinned against.
CONTROLS_MODULE = 'test_epic_partition_injected_failures.py'
_GROUP_BANNER = '# --- '
_TEST_DEF = 'def test_'

#: The verdicts the ``disagreements`` section selects out of a partition.
DISAGREEING_VERDICTS = ('unclaimed', 'contested')

#: The one method BOTH test-count figures declare.
TEST_COUNT_METHOD = 'static "def test_" count over the enumerated test modules'

#: A corpus that disagrees with itself AND leaves one span unresolvable, so both
#: halves of ``not_derivable`` — the modules and the specs — are populated.
#: PLAN-330 declares itself a sweep, so the ``swept`` section has a crossing to
#: reproduce; without it that population would be empty and reproduce trivially.
#:
#: ⛔ PLAN-330 declares its crossing in its OWN words rather than in the settled
#: sentence a sweep may copy. The report-level ``swept`` population therefore
#: depends on the marker reading a declaration rather than recognising a phrase,
#: so a marker that narrowed back to the copied sentence empties this section
#: here as well as failing the marker's own anti-degeneration control.
SPECS = {
    'PLAN-300.md': '# PLAN-300\n\n## Expected Surface\n\n'
    '- Adds `test/alpha/**`\n- Touches `marketplace/bundles/demo/**`\n',
    'PLAN-310.md': '# PLAN-310\n\n## Expected Surface\n\n- Also adds `test/alpha/**`\n',
    'PLAN-320.md': '# PLAN-320\n\n## Expected Surface\n\n- Touches `test_two_*.py`\n',
    'PLAN-330.md': '# PLAN-330\n\n## Expected Surface\n\n'
    '- Adds `test/alpha/**` — the sites this plan converts\n'
    '\nThis surface crosses several reduction slices deliberately; the sites it visits '
    "do not respect the epic's partition.\n",
    'PLAN-340.md': '# PLAN-340\n\n## Expected Surface\n\n- Adds `test/gamma/**`\n',
    'PLAN-350.md': '# PLAN-350\n\n## Expected Surface\n\n- Also adds `test/gamma/**`\n',
}
MODULES = (
    'test/alpha/test_one.py',
    'test/orphan/test_two_a.py',
    'test/gamma/test_three.py',
)

#: The epic's plan queue. PLAN-350 is the one FINISHED plan, so the ``lifecycle``
#: section has a real retirement to reproduce; PLAN-300 and PLAN-310 both stay
#: live, so the ``contested`` population it must not disturb survives beside it.
#: A section that reproduced only because both populations were empty would
#: reproduce trivially, which is what this fixture exists to prevent.
LEDGER = {
    'PLAN-300': 'staged',
    'PLAN-310': 'staged',
    'PLAN-320': 'staged',
    'PLAN-330': 'staged',
    'PLAN-340': 'running',
    'PLAN-350': 'landed',
}

#: A recorded baseline naming a module the current tree no longer reports, so the
#: drift section has a non-empty population to reproduce.
BASELINE_FINDINGS = ('test/alpha/test_departed.py',)


# --- scaffolding -------------------------------------------------------------


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def build_world(root: Path) -> tuple[Path, Path]:
    """Return ``(epic_dir, repo_root)`` for the corpus and tree built under ``root``."""
    repo = root / 'repo'
    (repo / 'test').mkdir(parents=True)
    (repo / 'marketplace').mkdir(parents=True)
    for rel in MODULES:
        write(repo / rel, 'def test_placeholder():\n    assert True\n')

    epic_dir = root / 'epic'
    for name, body in SPECS.items():
        write(epic_dir / 'plans' / name, body)
    write(
        epic_dir / 'status.json',
        json.dumps({'plans': [{'id': pid, 'status': st} for pid, st in LEDGER.items()]}),
    )
    return epic_dir, repo


def bind(monkeypatch, epic_dir: Path, repo: Path) -> None:
    monkeypatch.setattr(entry, 'get_store_dir', lambda *a, **k: epic_dir)
    monkeypatch.setattr(entry, 'cwd_checkout_root', lambda: str(repo))


@pytest.fixture
def run_verb(tmp_path: Path, monkeypatch) -> Callable[[str], dict[str, Any]]:
    """Run any entry-point verb against one shared corpus, tree and baseline."""
    epic_dir, repo = build_world(tmp_path)
    bind(monkeypatch, epic_dir, repo)
    baseline = tmp_path / 'baseline.txt'
    baseline.write_text('\n'.join(BASELINE_FINDINGS) + '\n', encoding='utf-8')

    def run(verb: str) -> dict[str, Any]:
        args = argparse.Namespace(
            epic=EPIC, budget=BUDGET, tests_before=None, baseline_findings=str(baseline)
        )
        handler: Any = getattr(entry, f'cmd_{verb}')
        payload: dict[str, Any] = handler(args)
        return payload

    return run


def section(report: dict[str, Any], name: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = report['sections']
    return next(row for row in rows if row['section'] == name)


def cited_verb(command: str) -> str:
    """Return the entry-point verb a section's cited command runs."""
    parts = command.split()
    assert parts[:3] == ['python3', '.plan/execute-script.py', NOTATION], command
    assert parts[4:] == ['--epic', EPIC], command
    return parts[3]


def declared_tests(source: str) -> set[str]:
    """Every test function declared at module level in ``source``."""
    return {
        line[len('def ') :].split('(', 1)[0]
        for line in source.splitlines()
        if line.startswith(_TEST_DEF)
    }


def control_groups(source: str) -> dict[str, list[str]]:
    """Map each ``# --- ...`` banner in the controls module to the tests under it."""
    groups: dict[str, list[str]] = {}
    banner: str | None = None
    for line in source.splitlines():
        if line.startswith(_GROUP_BANNER):
            banner = line[len(_GROUP_BANNER) :].strip('- ').strip()
            groups.setdefault(banner, [])
        elif line.startswith(_TEST_DEF) and banner is not None:
            groups[banner].append(line[len('def ') :].split('(', 1)[0])
    return groups


@pytest.fixture
def controls_source() -> str:
    return (TEST_TREE / CONTROLS_MODULE).read_text(encoding='utf-8')


#: Section name -> ``(the figures the section renders, the same figures read out
#: of the cited command's own payload)``. Every entry is a section citing an
#: entry-point verb; ``injected_controls`` cites the module-tests command and is
#: pinned separately below.
FIGURES: dict[str, Callable[[dict[str, Any], dict[str, Any]], tuple[Any, Any]]] = {
    'partition': lambda rep, out: (rep['partition_tally'], out['verdict_tally']),
    'attribution': lambda rep, out: (rep['attribution_buckets'], out['buckets']),
    'disagreements': lambda rep, out: (
        rep['disagreements'],
        [
            {
                'path': row['path'],
                'verdict': row['verdict'],
                'plans': row['plans'],
                'retired': row['retired'],
            }
            for row in out['modules']
            if row['verdict'] in DISAGREEING_VERDICTS
        ],
    ),
    'contested': lambda rep, out: (rep['contested'], out['contested']),
    'lifecycle': lambda rep, out: (
        (rep['lifecycle'], rep['lifecycle_plans'], rep['lifecycle_resolved']),
        (out['lifecycle'], out['lifecycle_plans'], out['lifecycle_resolved']),
    ),
    'swept': lambda rep, out: (
        (rep['sweep_plans'], rep['sweep_crossings']),
        (out['sweep_plans'], out['sweep_crossings']),
    ),
    'baseline_drift': lambda rep, out: (
        (rep['baseline_drift'], rep['baseline_drift_instances']),
        (out['baseline_drift'], out['baseline_drift_instances']),
    ),
    'not_derivable': lambda rep, out: (
        (rep['not_derivable_modules'], rep['not_derivable_specs']),
        (out['not_derivable_modules'], out['not_derivable_specs']),
    ),
    'test_count': lambda rep, out: (rep['test_count'], out['test_count']),
    'provenance': lambda rep, out: (
        (rep['provenance'], rep['provenance_placement'], rep['provenance_overlaps']),
        (out['provenance'], out['provenance_placement'], out['provenance_overlaps']),
    ),
}


# --- the claim holds for every section, not most of them ----------------------


def test_every_rendered_section_is_pinned_by_one_of_the_two_checks(run_verb) -> None:
    rendered = {row['section'] for row in run_verb('report')['sections']}

    assert set(FIGURES) | {'injected_controls'} == rendered


def test_the_fixture_corpus_populates_every_reproduced_section(run_verb) -> None:
    """An empty population reproduces trivially, so no section may be empty here."""
    report = run_verb('report')

    assert report['partition_tally'] and report['attribution_buckets']
    assert report['disagreements']
    assert report['contested']
    assert report['lifecycle']['available'] is True
    assert report['lifecycle_plans'] and report['lifecycle_resolved']
    assert report['sweep_plans'] and report['sweep_crossings']
    assert report['baseline_drift_instances']
    assert report['not_derivable_modules'] and report['not_derivable_specs']


@pytest.mark.parametrize('name', sorted(FIGURES))
def test_the_cited_command_reproduces_the_sections_figures(run_verb, name: str) -> None:
    report = run_verb('report')

    payload = run_verb(cited_verb(section(report, name)['command']))

    rendered, reproduced = FIGURES[name](report, payload)
    assert reproduced == rendered


# --- the injected-controls section cites a test command, not a verb -----------


def test_the_injected_controls_command_scopes_the_bundle_holding_the_demonstrations(
    run_verb,
) -> None:
    command = section(run_verb('report'), 'injected_controls')['command']

    assert f'module-tests {TEST_TREE.parent.name}' in command


def test_every_injected_control_names_a_test_the_cited_command_runs(run_verb) -> None:
    for row in run_verb('report')['injected_controls']:
        module_name, _, function = row['demonstrated_by'].partition('::')

        source = (TEST_TREE / module_name).read_text(encoding='utf-8')

        assert f'def {function}(' in source, row['control']


def test_the_control_group_scan_sees_every_test_the_module_declares(controls_source) -> None:
    """The reverse guard below is only as trustworthy as the scan feeding it.

    A banner-format change that made the scan return nothing would let the guard
    pass vacuously over an empty set, so the scan is pinned to account for every
    declared test rather than being trusted to have found them.
    """
    scanned = {name for names in control_groups(controls_source).values() for name in names}

    declared = declared_tests(controls_source)

    assert declared
    assert scanned == declared


def test_every_shipped_control_group_is_named_in_the_injected_controls_section(
    run_verb, controls_source
) -> None:
    """The section names every shipped demonstration, not a subset of them.

    The forward guard above walks section -> test, so it catches a RENAME or a
    REMOVAL of a named control and never an ADDITION of a shipped one the
    section does not name. This is the other direction: a control group shipped
    and unnamed makes the section present a partial set as the complete one.
    """
    named = {
        row['demonstrated_by'].partition('::')[2]
        for row in run_verb('report')['injected_controls']
    }

    groups = control_groups(controls_source)

    unnamed = {banner for banner, tests in groups.items() if tests and not named & set(tests)}
    assert unnamed == set()


# --- the test count is measured the way it says ------------------------------


def test_the_after_figure_is_the_static_count_its_method_names(tmp_path: Path, monkeypatch) -> None:
    """Collection would count the parametrized CASES; the declared method counts DECLARATIONS.

    The rewritten module below declares two tests and collects four, and every
    other fixture module declares and collects one — so the two methods disagree,
    and the figure is checked against the one the section names.
    """
    declared_in_rewritten = 2
    expected_after = declared_in_rewritten + (len(MODULES) - 1)
    epic_dir, repo = build_world(tmp_path)
    write(
        repo / MODULES[0],
        'import pytest\n\n'
        '@pytest.mark.parametrize("n", [1, 2, 3])\n'
        'def test_parametrized(n):\n    assert n\n\n'
        'def helper():\n    return 1\n\n'
        'def test_plain():\n    assert True\n',
    )
    bind(monkeypatch, epic_dir, repo)

    report = entry.cmd_report(
        argparse.Namespace(
            epic=EPIC, budget=BUDGET, tests_before=None, baseline_findings=None
        )
    )

    assert report['test_count']['after'] == expected_after
    assert report['test_count']['method'] == TEST_COUNT_METHOD


def test_the_before_flag_declares_the_same_method_as_the_after_figure() -> None:
    """Both figures name one method, so the section compares like with like."""
    script = get_script_path(BUNDLE, SKILL, SCRIPT)

    result = run_script(str(script), 'report', '--help')

    assert 'Declared-test' in result.stdout
    assert 'Collected' not in result.stdout

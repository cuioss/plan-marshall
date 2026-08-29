#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the surface partition — the four verdicts and the budget attribution.

Drives the underscore-prefixed helpers directly by inserting the scripts dir on
``sys.path`` (the canonical scaffolding pattern).

Every corpus and every test tree used here is built under ``tmp_path``; the real
orchestrator store and the real ``test/`` tree are neither read nor written.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from conftest import get_scripts_dir

SCRIPTS_DIR = get_scripts_dir('pm-plugin-development', 'tools-epic-surface-partition')
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _epic_partition as partition_mod  # noqa: E402
from epic_spec_parser import (  # noqa: E402
    KIND_DIRECTORY,
    KIND_FILE,
    KIND_FILENAME_GLOB,
    KIND_RECURSIVE_GLOB,
    classify_corpus,
)


# --- scaffolding -------------------------------------------------------------

#: The fixture corpus. PLAN-100 claims a subtree minus a carve-out; PLAN-110 and
#: PLAN-120 both claim the same directory; PLAN-130 is prose whose only span the
#: parser cannot anchor; PLAN-140 carries a bare root span.
SPECS = {
    'PLAN-100.md': '# PLAN-100\n\n## Expected Surface\n\n'
    '- Adds `test/alpha/**` excluding `test/alpha/legacy/`\n',
    'PLAN-110.md': '# PLAN-110\n\n## Expected Surface\n\n- Adds `test/beta/`\n',
    'PLAN-120.md': '# PLAN-120\n\n## Expected Surface\n\n- Adds `test/beta/`\n',
    'PLAN-130.md': '# PLAN-130\n\n## Expected Surface\n\n- Touches `test_four_*.py` modules\n',
    'PLAN-140.md': '# PLAN-140\n\n## Expected Surface\n\n- Sweeps `test/`\n',
}

#: The fixture tree, one module per verdict the corpus above produces.
MODULES = (
    'test/alpha/test_one.py',
    'test/alpha/legacy/test_old.py',
    'test/beta/test_three.py',
    'test/gamma/test_four_x.py',
    'test/delta/test_five.py',
)


def write_module(repo: Path, rel: str, lines: int = 1) -> Path:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(f'# line {index}\n' for index in range(lines)), encoding='utf-8')
    return path


def build_corpus(plans: Path, specs: dict[str, str]) -> None:
    for name, body in specs.items():
        (plans / name).write_text(body, encoding='utf-8')


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / 'repo'
    (root / 'test').mkdir(parents=True)
    for rel in MODULES:
        write_module(root, rel)
    return root


@pytest.fixture
def plans(tmp_path: Path) -> Path:
    directory = tmp_path / 'plans'
    directory.mkdir()
    build_corpus(directory, SPECS)
    return directory


@pytest.fixture
def partition(repo: Path, plans: Path) -> partition_mod.Partition:
    claims = classify_corpus(plans, repo)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)
    return partition_mod.derive_partition(claims, modules)


def verdict_of(result: partition_mod.Partition, path: str) -> str:
    return next(module.verdict for module in result.modules if module.path == path)


def plans_of(result: partition_mod.Partition, path: str) -> tuple[str, ...]:
    return next(module.plans for module in result.modules if module.path == path)


def paths_with(result: partition_mod.Partition, verdict: str) -> set[str]:
    return {module.path for module in result.with_verdict(verdict)}


# --- module enumeration ------------------------------------------------------


def test_only_test_modules_are_enumerated(repo: Path) -> None:
    write_module(repo, 'test/alpha/conftest.py')
    write_module(repo, 'test/alpha/helper.py')

    modules = partition_mod.iter_test_modules(repo / 'test', repo)

    assert set(modules) == set(MODULES)


def test_modules_are_enumerated_in_sorted_order(repo: Path) -> None:
    modules = partition_mod.iter_test_modules(repo / 'test', repo)

    assert list(modules) == sorted(modules)


def test_absent_test_root_yields_no_modules(tmp_path: Path) -> None:
    assert partition_mod.iter_test_modules(tmp_path / 'nowhere', tmp_path) == ()


# --- entry matching ----------------------------------------------------------


@pytest.mark.parametrize(
    ('entry', 'kind', 'module', 'expected'),
    [
        ('test/a/**', KIND_RECURSIVE_GLOB, 'test/a/deep/test_x.py', True),
        ('test/a/**', KIND_RECURSIVE_GLOB, 'test/b/test_x.py', False),
        ('test/a/', KIND_DIRECTORY, 'test/a/test_x.py', True),
        ('test/a/', KIND_DIRECTORY, 'test/ab/test_x.py', False),
        ('test/a/test_*.py', KIND_FILENAME_GLOB, 'test/a/test_x.py', True),
        ('test/a/test_*.py', KIND_FILENAME_GLOB, 'test/a/deep/test_x.py', False),
        ('test/a/test_x.py', KIND_FILE, 'test/a/test_x.py', True),
        ('test/a/test_x.py', KIND_FILE, 'test/a/test_y.py', False),
    ],
    ids=[
        'recursive_glob_covers_depth',
        'recursive_glob_stops_at_sibling',
        'directory_covers_child',
        'directory_does_not_prefix_match_sibling',
        'filename_glob_matches_in_place',
        'filename_glob_does_not_span_separator',
        'named_file_exact',
        'named_file_rejects_other',
    ],
)
def test_entry_matching(entry: str, kind: str, module: str, expected: bool) -> None:
    assert partition_mod.entry_matches(entry, kind, module) is expected


# --- the four verdicts -------------------------------------------------------


def test_single_claimant_module_is_claimed(partition) -> None:
    assert verdict_of(partition, 'test/alpha/test_one.py') == partition_mod.VERDICT_CLAIMED
    assert plans_of(partition, 'test/alpha/test_one.py') == ('PLAN-100',)


def test_module_no_spec_claims_is_unclaimed(partition) -> None:
    assert verdict_of(partition, 'test/delta/test_five.py') == partition_mod.VERDICT_UNCLAIMED
    assert plans_of(partition, 'test/delta/test_five.py') == ()


def test_module_two_specs_claim_is_multiply_claimed(partition) -> None:
    assert (
        verdict_of(partition, 'test/beta/test_three.py')
        == partition_mod.VERDICT_MULTIPLY_CLAIMED
    )
    assert plans_of(partition, 'test/beta/test_three.py') == ('PLAN-110', 'PLAN-120')


def test_module_named_only_by_an_unresolvable_span_is_not_derivable(partition) -> None:
    assert (
        verdict_of(partition, 'test/gamma/test_four_x.py')
        == partition_mod.VERDICT_NOT_DERIVABLE
    )
    assert plans_of(partition, 'test/gamma/test_four_x.py') == ('PLAN-130',)


def test_not_derivable_is_never_reported_as_unclaimed(partition) -> None:
    unclaimed = paths_with(partition, partition_mod.VERDICT_UNCLAIMED)
    not_derivable = paths_with(partition, partition_mod.VERDICT_NOT_DERIVABLE)

    assert 'test/gamma/test_four_x.py' not in unclaimed
    assert not unclaimed & not_derivable


def test_every_module_carries_exactly_one_verdict(partition) -> None:
    assert len(partition.modules) == len(MODULES)
    assert {module.path for module in partition.modules} == set(MODULES)


def test_tally_reports_every_verdict_even_at_zero(repo: Path, plans: Path) -> None:
    claims = classify_corpus(plans, repo)
    result = partition_mod.derive_partition(claims, ('test/alpha/test_one.py',))

    tally = result.tally()

    assert set(tally) == set(partition_mod.VERDICT_ORDER)
    assert tally[partition_mod.VERDICT_UNCLAIMED] == 0


# --- exclusions --------------------------------------------------------------


def test_exclusion_subtracts_from_the_claiming_plans_set(partition) -> None:
    assert verdict_of(partition, 'test/alpha/legacy/test_old.py') == (
        partition_mod.VERDICT_UNCLAIMED
    )


def test_exclusion_does_not_subtract_from_another_plans_claim(repo: Path, plans: Path) -> None:
    (plans / 'PLAN-150.md').write_text(
        '# PLAN-150\n\n## Expected Surface\n\n- Adds `test/alpha/legacy/`\n', encoding='utf-8'
    )
    claims = classify_corpus(plans, repo)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)

    result = partition_mod.derive_partition(claims, modules)

    assert verdict_of(result, 'test/alpha/legacy/test_old.py') == partition_mod.VERDICT_CLAIMED
    assert plans_of(result, 'test/alpha/legacy/test_old.py') == ('PLAN-150',)


# --- root spans --------------------------------------------------------------


@pytest.mark.parametrize(
    ('entry', 'kind', 'expected'),
    [
        ('test/', KIND_DIRECTORY, True),
        ('test/**', KIND_RECURSIVE_GLOB, True),
        ('test/alpha/', KIND_DIRECTORY, False),
        ('test/alpha/**', KIND_RECURSIVE_GLOB, False),
        ('test/test_x.py', KIND_FILE, False),
    ],
    ids=['bare_root', 'root_glob', 'subtree_dir', 'subtree_glob', 'named_file'],
)
def test_root_span_detection(entry: str, kind: str, expected: bool) -> None:
    assert partition_mod.is_root_span(entry, kind) is expected


def test_root_span_claims_nothing(partition) -> None:
    for module in partition.modules:
        assert 'PLAN-140' not in module.plans


def test_root_span_is_reported_rather_than_silently_dropped(partition) -> None:
    reported = {(root.plan_id, root.path) for root in partition.root_claims}

    assert ('PLAN-140', 'test/') in reported


def test_corpus_without_root_spans_reports_none(repo: Path, tmp_path: Path) -> None:
    plans = tmp_path / 'narrow'
    plans.mkdir()
    build_corpus(plans, {'PLAN-100.md': SPECS['PLAN-100.md']})
    claims = classify_corpus(plans, repo)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)

    result = partition_mod.derive_partition(claims, modules)

    assert result.root_claims == ()


# --- budget findings and attribution -----------------------------------------


def test_budget_findings_are_rederived_from_the_current_tree(repo: Path) -> None:
    write_module(repo, 'test/alpha/test_one.py', lines=12)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)

    findings = partition_mod.derive_budget_findings(modules, repo, budget=10)

    assert [(f.path, f.line_count) for f in findings] == [('test/alpha/test_one.py', 12)]


def test_module_at_the_budget_is_not_a_finding(repo: Path) -> None:
    write_module(repo, 'test/alpha/test_one.py', lines=10)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)

    assert partition_mod.derive_budget_findings(modules, repo, budget=10) == ()


def test_attribution_buckets_are_keyed_by_owning_plan(repo: Path, partition) -> None:
    write_module(repo, 'test/alpha/test_one.py', lines=12)
    findings = partition_mod.derive_budget_findings(partition_mod.iter_test_modules(
        repo / 'test', repo
    ), repo, budget=10)

    attribution = partition_mod.derive_attribution(partition, findings, budget=10)

    assert [bucket.owner for bucket in attribution.buckets] == ['PLAN-100']


def test_each_file_is_attributed_at_most_once(repo: Path, partition) -> None:
    for rel in MODULES:
        write_module(repo, rel, lines=12)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)
    findings = partition_mod.derive_budget_findings(modules, repo, budget=10)

    attribution = partition_mod.derive_attribution(partition, findings, budget=10)

    attributed = [f.path for bucket in attribution.buckets for f in bucket.findings]
    assert len(attributed) == len(set(attributed)) == len(MODULES)


@pytest.mark.parametrize(
    ('module_path', 'owner'),
    [
        ('test/delta/test_five.py', partition_mod.OWNER_UNCLAIMED),
        ('test/beta/test_three.py', partition_mod.OWNER_MULTIPLY_CLAIMED),
        ('test/gamma/test_four_x.py', partition_mod.OWNER_NOT_DERIVABLE),
    ],
    ids=['unclaimed', 'multiply_claimed', 'not_derivable'],
)
def test_ownerless_populations_get_their_own_buckets(
    repo: Path, partition, module_path: str, owner: str
) -> None:
    write_module(repo, module_path, lines=12)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)
    findings = partition_mod.derive_budget_findings(modules, repo, budget=10)

    attribution = partition_mod.derive_attribution(partition, findings, budget=10)

    owners = {bucket.owner for bucket in attribution.buckets}
    assert owner in owners


def test_attribution_reports_its_budget_and_total(repo: Path, partition) -> None:
    write_module(repo, 'test/alpha/test_one.py', lines=12)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)
    findings = partition_mod.derive_budget_findings(modules, repo, budget=10)

    attribution = partition_mod.derive_attribution(partition, findings, budget=10)

    assert attribution.budget == 10
    assert attribution.total_findings() == 1


def test_clean_tree_produces_no_attribution_buckets(repo: Path, partition) -> None:
    modules = partition_mod.iter_test_modules(repo / 'test', repo)
    findings = partition_mod.derive_budget_findings(modules, repo, budget=400)

    attribution = partition_mod.derive_attribution(partition, findings, budget=400)

    assert attribution.buckets == ()
    assert attribution.total_findings() == 0

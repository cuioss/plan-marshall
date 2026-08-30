#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Injected-failure controls for the partition — a checker never observed failing is not a checker.

Each negative control is paired with the matching positive control on the SAME
clean corpus, so a test that passes because the derivation reports nothing at all
cannot be mistaken for a test that passes because the derivation works.

Drives the underscore-prefixed helpers directly by inserting the scripts dir on
``sys.path`` (the canonical scaffolding pattern). Every corpus and tree is built
under ``tmp_path``; the real orchestrator store is never touched.
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
from epic_spec_parser import classify_corpus  # noqa: E402


# --- the clean baseline ------------------------------------------------------

#: A corpus that partitions its tree exactly: each plan claims a disjoint
#: subtree, so nothing is unclaimed and nothing is claimed twice.
CLEAN_SPECS = {
    'PLAN-200.md': '# PLAN-200\n\n## Expected Surface\n\n- Adds `test/alpha/**`\n',
    'PLAN-210.md': '# PLAN-210\n\n## Expected Surface\n\n- Adds `test/beta/**`\n',
}

CLEAN_MODULES = ('test/alpha/test_one.py', 'test/beta/test_two.py')


def write_module(repo: Path, rel: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('# test module\n', encoding='utf-8')


def build_repo(root: Path, modules: tuple[str, ...]) -> Path:
    repo = root / 'repo'
    (repo / 'test').mkdir(parents=True)
    for rel in modules:
        write_module(repo, rel)
    return repo


def build_plans(root: Path, specs: dict[str, str]) -> Path:
    plans = root / 'plans'
    plans.mkdir()
    for name, body in specs.items():
        (plans / name).write_text(body, encoding='utf-8')
    return plans


def partition_of(repo: Path, plans: Path):
    claims = classify_corpus(plans, repo)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)
    return partition_mod.derive_partition(claims, modules)


def named(result, verdict: str) -> set[str]:
    return {module.path for module in result.with_verdict(verdict)}


@pytest.fixture
def clean(tmp_path: Path):
    repo = build_repo(tmp_path, CLEAN_MODULES)
    plans = build_plans(tmp_path, dict(CLEAN_SPECS))
    return repo, plans


# --- positive controls: the clean corpus reports no disagreement --------------


def test_clean_corpus_reports_nothing_unclaimed(clean) -> None:
    repo, plans = clean

    result = partition_of(repo, plans)

    assert named(result, partition_mod.VERDICT_UNCLAIMED) == set()


def test_clean_corpus_reports_nothing_multiply_claimed(clean) -> None:
    repo, plans = clean

    result = partition_of(repo, plans)

    assert named(result, partition_mod.VERDICT_MULTIPLY_CLAIMED) == set()


def test_clean_corpus_claims_every_module_exactly_once(clean) -> None:
    repo, plans = clean

    result = partition_of(repo, plans)

    assert named(result, partition_mod.VERDICT_CLAIMED) == set(CLEAN_MODULES)


# --- negative control 1: an unclaimed directory is reported BY NAME -----------


def test_injected_unclaimed_directory_is_reported_by_name(clean) -> None:
    repo, plans = clean
    write_module(repo, 'test/orphan/test_nobody_claims_me.py')

    result = partition_of(repo, plans)

    assert named(result, partition_mod.VERDICT_UNCLAIMED) == {
        'test/orphan/test_nobody_claims_me.py'
    }


def test_injected_unclaimed_directory_does_not_disturb_the_claimed_set(clean) -> None:
    repo, plans = clean
    write_module(repo, 'test/orphan/test_nobody_claims_me.py')

    result = partition_of(repo, plans)

    assert named(result, partition_mod.VERDICT_CLAIMED) == set(CLEAN_MODULES)


# --- negative control 2: a doubly-claimed path is reported BY NAME ------------


def test_injected_double_claim_is_reported_by_name(clean) -> None:
    repo, plans = clean
    (plans / 'PLAN-220.md').write_text(
        '# PLAN-220\n\n## Expected Surface\n\n- Also adds `test/alpha/**`\n', encoding='utf-8'
    )

    result = partition_of(repo, plans)

    assert named(result, partition_mod.VERDICT_MULTIPLY_CLAIMED) == {'test/alpha/test_one.py'}


def test_injected_double_claim_names_both_claiming_plans(clean) -> None:
    repo, plans = clean
    (plans / 'PLAN-220.md').write_text(
        '# PLAN-220\n\n## Expected Surface\n\n- Also adds `test/alpha/**`\n', encoding='utf-8'
    )

    result = partition_of(repo, plans)

    owners = next(
        module.plans for module in result.modules if module.path == 'test/alpha/test_one.py'
    )
    assert owners == ('PLAN-200', 'PLAN-220')


def test_injected_double_claim_leaves_the_other_subtree_singly_claimed(clean) -> None:
    repo, plans = clean
    (plans / 'PLAN-220.md').write_text(
        '# PLAN-220\n\n## Expected Surface\n\n- Also adds `test/alpha/**`\n', encoding='utf-8'
    )

    result = partition_of(repo, plans)

    assert named(result, partition_mod.VERDICT_CLAIMED) == {'test/beta/test_two.py'}


# --- negative control 3: a root span does not mask a real disagreement --------


def test_injected_root_span_does_not_hide_an_unclaimed_module(clean) -> None:
    repo, plans = clean
    write_module(repo, 'test/orphan/test_nobody_claims_me.py')
    (plans / 'PLAN-230.md').write_text(
        '# PLAN-230\n\n## Expected Surface\n\n- Sweeps `test/**`\n', encoding='utf-8'
    )

    result = partition_of(repo, plans)

    assert named(result, partition_mod.VERDICT_UNCLAIMED) == {
        'test/orphan/test_nobody_claims_me.py'
    }
    assert ('PLAN-230', 'test/**') in {(r.plan_id, r.path) for r in result.root_claims}


# --- negative control 4: a container-shaped unresolved span is NOT unclaimed --
#
# A DIRECTORY-shaped span the parser cannot anchor names no filename, so a
# trailing-segment match against it finds nothing and every module beneath it
# falls through to ``unclaimed``. That is the one merge the derivation exists to
# prevent: coverage the parser cannot see, reported as a partition defect. Both
# container shapes are covered, and the pairing module — one nothing names at
# all — is the positive control that keeps ``unclaimed`` from simply emptying.

#: The module a directory-shaped span names, and the module nothing names.
MENTIONED_MODULE = 'test/orphanage/test_named_only_by_a_directory_span.py'
UNMENTIONED_MODULE = 'test/orphan/test_nobody_claims_me.py'


@pytest.fixture(params=['.../orphanage/', '.../orphanage/**'], ids=['directory', 'recursive_glob'])
def container_span(request, clean):
    """The clean corpus plus a prose spec whose only span is an unanchored directory."""
    repo, plans = clean
    write_module(repo, MENTIONED_MODULE)
    write_module(repo, UNMENTIONED_MODULE)
    (plans / 'PLAN-240.md').write_text(
        f'# PLAN-240\n\n## Expected Surface\n\n- Touches the modules under `{request.param}`\n',
        encoding='utf-8',
    )
    return repo, plans


def test_container_span_spec_resolves_to_no_path_entry(container_span) -> None:
    repo, plans = container_span

    claim = next(c for c in classify_corpus(plans, repo) if c.plan_id == 'PLAN-240')

    assert claim.claimed == ()
    assert claim.spec_class == 'prose'
    assert len(claim.unresolved) == 1


def test_container_span_marks_the_module_beneath_it_not_derivable(container_span) -> None:
    repo, plans = container_span

    result = partition_of(repo, plans)

    assert named(result, partition_mod.VERDICT_NOT_DERIVABLE) == {MENTIONED_MODULE}


def test_container_span_names_the_plan_the_verdict_rests_on(container_span) -> None:
    repo, plans = container_span

    result = partition_of(repo, plans)

    owners = next(module.plans for module in result.modules if module.path == MENTIONED_MODULE)
    assert owners == ('PLAN-240',)


def test_genuinely_unclaimed_module_stays_unclaimed_beside_it(container_span) -> None:
    repo, plans = container_span

    result = partition_of(repo, plans)

    assert named(result, partition_mod.VERDICT_UNCLAIMED) == {UNMENTIONED_MODULE}


def test_container_span_does_not_disturb_the_claimed_set(container_span) -> None:
    repo, plans = container_span

    result = partition_of(repo, plans)

    assert named(result, partition_mod.VERDICT_CLAIMED) == set(CLEAN_MODULES)

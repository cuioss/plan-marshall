#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Injected-failure controls for the partition — a checker never observed failing is not a checker.

Each negative control is paired with the matching positive control on the SAME
clean corpus, so a test that passes because the derivation reports nothing at all
cannot be mistaken for a test that passes because the derivation works.

Drives the underscore-prefixed helpers directly, through the shared
``conftest.load_script_module`` loader. Every corpus and tree is built
under ``tmp_path``; the real orchestrator store is never touched.
"""

from __future__ import annotations

import json
from pathlib import Path

# PLAIN import, deliberately — see the sibling suites: only a plain import gives
# mypy the real module, and the name must be bound the same way everywhere or the
# loader would register a copy beside the plainly-imported one.
import _epic_partition as partition_mod
import pytest
from epic_spec_parser import classify_corpus

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


def partition_of(repo: Path, plans: Path, terminal: frozenset[str] = frozenset()):
    claims = classify_corpus(plans, repo)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)
    return partition_mod.derive_partition(claims, modules, frozenset(), terminal)


def terminal_from_ledger(epic_dir: Path, rows: dict[str, str]) -> frozenset[str]:
    """Write a ledger and read the finished-plan set back out of it.

    Injected through the real reader rather than hand-built, so a control here
    also exercises the ledger parse the live derivation depends on.
    """
    epic_dir.mkdir(parents=True, exist_ok=True)
    payload = {'plans': [{'id': pid, 'status': st} for pid, st in rows.items()]}
    (epic_dir / 'status.json').write_text(json.dumps(payload), encoding='utf-8')
    return partition_mod.read_plan_lifecycle(epic_dir).terminal_plans()


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


def test_clean_corpus_reports_nothing_contested(clean) -> None:
    repo, plans = clean

    result = partition_of(repo, plans)

    assert named(result, partition_mod.VERDICT_CONTESTED) == set()


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
#
# Both claimants here are ordinary SLICE plans — neither declares itself a sweep
# — so this is the genuine contest the partition must still surface. The
# sweep-plan exemption is deliberately not in play; its own matched pair lives in
# ``test_epic_partition.py``.


def test_injected_double_claim_is_reported_by_name(clean) -> None:
    repo, plans = clean
    (plans / 'PLAN-220.md').write_text(
        '# PLAN-220\n\n## Expected Surface\n\n- Also adds `test/alpha/**`\n', encoding='utf-8'
    )

    result = partition_of(repo, plans)

    assert named(result, partition_mod.VERDICT_CONTESTED) == {'test/alpha/test_one.py'}


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


# --- negative control 5: a cited slice is not contested by the citing plan ----
#
# A spec whose claim CITES a sibling's surface possessively is quoting that
# sibling's ownership, not competing for it. Left unread, one such bullet makes
# the citing plan a co-owner of the cited plan's whole slice and contests it in
# full — the shape that kept the attribution collapsed into a single bucket. The
# matched positive on the same corpus is the identical span claimed outright,
# which is a real contest and must still be reported by name.

#: The two forms of the injected bullet: a citation of PLAN-200's subtree, and
#: the same span claimed outright. They differ only in the possessive citation.
CITING_BODY = (
    '# PLAN-250\n\n## Expected Surface\n\n'
    "- OBSERVED: slice `200`'s modules under `test/alpha/**` — the fidelity check\n"
)
UNCITED_BODY = (
    '# PLAN-250\n\n## Expected Surface\n\n'
    '- OBSERVED: the modules under `test/alpha/**` — the fidelity check\n'
)


def test_injected_cross_plan_citation_does_not_contest_the_cited_slice(clean) -> None:
    repo, plans = clean
    (plans / 'PLAN-250.md').write_text(CITING_BODY, encoding='utf-8')

    result = partition_of(repo, plans)

    assert named(result, partition_mod.VERDICT_CONTESTED) == set()
    assert named(result, partition_mod.VERDICT_CLAIMED) == set(CLEAN_MODULES)


def test_injected_uncited_claim_over_the_cited_slice_is_reported_by_name(clean) -> None:
    """Matched positive: the same span, the same corpus, no citation."""
    repo, plans = clean
    (plans / 'PLAN-250.md').write_text(UNCITED_BODY, encoding='utf-8')

    result = partition_of(repo, plans)

    owners = next(
        module.plans for module in result.modules if module.path == 'test/alpha/test_one.py'
    )
    assert named(result, partition_mod.VERDICT_CONTESTED) == {'test/alpha/test_one.py'}
    assert owners == ('PLAN-200', 'PLAN-250')


# --- negative control 6: a finished plan's claim no longer competes -----------
#
# The injected double claim above, with a LEDGER beside it. The corpus is
# byte-identical in both halves of this pair and only the recorded status
# differs, so the retirement is attributable to the lifecycle input alone.

#: The second claimant over PLAN-200's subtree, and the module they both cover.
DOUBLE_CLAIM_BODY = '# PLAN-220\n\n## Expected Surface\n\n- Also adds `test/alpha/**`\n'
DOUBLE_CLAIM_MODULE = 'test/alpha/test_one.py'


def test_injected_terminal_claim_is_retired_in_favour_of_the_active_plan(
    clean, tmp_path: Path
) -> None:
    """A plan whose work is finished stops competing; the live plan owns the module."""
    repo, plans = clean
    (plans / 'PLAN-220.md').write_text(DOUBLE_CLAIM_BODY, encoding='utf-8')
    terminal = terminal_from_ledger(
        tmp_path / 'epic_retired', {'PLAN-200': 'landed', 'PLAN-220': 'staged'}
    )

    result = partition_of(repo, plans, terminal)
    module = next(m for m in result.modules if m.path == DOUBLE_CLAIM_MODULE)

    assert named(result, partition_mod.VERDICT_CONTESTED) == set()
    assert module.verdict == partition_mod.VERDICT_CLAIMED
    assert module.plans == ('PLAN-220',)
    assert module.retired == ('PLAN-200',)


# --- negative control 7: two live plans are never adjudicated ----------------


def test_injected_active_versus_active_module_stays_contested(clean, tmp_path: Path) -> None:
    """⛔ The refusal: lifecycle narrows the competing set, it never picks a winner.

    The matched half of the control above — same corpus, same ledger shape, both
    plans recorded as still working. A rule that resolved this would look exactly
    like a success while inventing an ownership no plan has yet earned.
    """
    repo, plans = clean
    (plans / 'PLAN-220.md').write_text(DOUBLE_CLAIM_BODY, encoding='utf-8')
    terminal = terminal_from_ledger(
        tmp_path / 'epic_live', {'PLAN-200': 'running', 'PLAN-220': 'staged'}
    )

    result = partition_of(repo, plans, terminal)
    module = next(m for m in result.modules if m.path == DOUBLE_CLAIM_MODULE)

    assert terminal == frozenset()
    assert named(result, partition_mod.VERDICT_CONTESTED) == {DOUBLE_CLAIM_MODULE}
    assert module.plans == ('PLAN-200', 'PLAN-220')
    assert module.retired == ()

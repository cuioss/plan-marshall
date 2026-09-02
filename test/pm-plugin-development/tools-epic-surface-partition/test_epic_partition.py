#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the surface partition — every verdict and the budget attribution.

Drives the underscore-prefixed helpers directly by inserting the scripts dir on
``sys.path`` (the canonical scaffolding pattern).

Three independent rules decide whether a spec's entry carries OWNERSHIP, and
each is covered here with a matched positive and negative control, in isolation
from the others: the sweep-plan self-declaration, the lead-shaped entry stage 1
publishes, and the ``derived`` spec class. A rule that silently stopped firing
would restore the single-bucket collapse the partition exists to break, so each
is pinned on its own rather than only through their combined effect.

The closing cluster measures the three of them TOGETHER against a corpus
reproducing the residual drivers the live epic carries, as a per-driver
differential: with each driver's own wording the contest disappears, and with its
matched near-miss substituted the contest returns. That shape asserts the
headline outcome without transcribing a live-corpus figure that would go stale.

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


# --- the verdicts ------------------------------------------------------------


def test_single_claimant_module_is_claimed(partition) -> None:
    assert verdict_of(partition, 'test/alpha/test_one.py') == partition_mod.VERDICT_CLAIMED
    assert plans_of(partition, 'test/alpha/test_one.py') == ('PLAN-100',)


def test_module_no_spec_claims_is_unclaimed(partition) -> None:
    assert verdict_of(partition, 'test/delta/test_five.py') == partition_mod.VERDICT_UNCLAIMED
    assert plans_of(partition, 'test/delta/test_five.py') == ()


def test_module_two_slice_specs_claim_is_contested(partition) -> None:
    """Two SLICE plans over one module is the residual genuine disagreement."""
    assert verdict_of(partition, 'test/beta/test_three.py') == partition_mod.VERDICT_CONTESTED
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


# --- rule 1: the sweep-plan marker, in isolation -----------------------------
#
# The marker is exercised on its own text first, then through the partition, so
# a marker that stopped firing is distinguishable from a partition that stopped
# consuming it.

#: A spec that declares itself a whole-partition sweep, in the corpus's wording.
_SWEEP_BODY = (
    '# PLAN-200\n\n## Expected Surface\n\n'
    '- OBSERVED: `test/beta/` — ⛔ **the whole tree.** This plan crosses every slice, '
    "so this plan's surface is the test tree entire, and it pairs with no other "
    '`test/`-editing plan\n'
)

#: The matched negative: an equally BROAD claim with no self-declaration.
_BROAD_BODY = (
    '# PLAN-210\n\n## Expected Surface\n\n'
    '- OBSERVED: `test/beta/` — the directory this plan reduces\n'
)

#: The SAME declaration written in the plan's own words, sharing no sentence with
#: ``_SWEEP_BODY``. A plan that declares its crossing this way is exactly as much
#: a sweep as one that copies the settled sentence, and a marker that matched
#: only the copied form would be the hard-coded plan list the module forbids.
_OWN_WORDS_SWEEP_BODY = (
    '# PLAN-201\n\n## Expected Surface\n\n'
    '- OBSERVED: `test/beta/` — the sites this plan converts\n'
    '\n⚠️ **This surface crosses several reduction slices deliberately** — skip sites do '
    "not respect the epic's partition. Confirm no plan named below is in flight before "
    'starting.\n'
)

#: The near-miss: a spec ANALYSING the corpus, which QUOTES a sibling's crossing
#: declaration while claiming an ordinary slice of its own.
_QUOTING_BODY = (
    '# PLAN-211\n\n## Expected Surface\n\n'
    '- OBSERVED: `test/beta/` — this plan\'s own mirror\n'
    '\nThe table below records why each row was read as it was. One row reads '
    '"this plan crosses the whole partition by construction" and is a **genuine claim**.\n'
)


def test_the_sweep_marker_fires_on_a_self_declaring_spec() -> None:
    """Positive control for the marker alone."""
    assert partition_mod.is_sweep_declaration(_SWEEP_BODY)


def test_the_sweep_marker_fires_on_an_own_words_declaration() -> None:
    """Anti-degeneration control: the marker is not a list of settled sentences.

    This body declares the same thing as ``_SWEEP_BODY`` while sharing neither of
    its settled phrasings, so a marker that had narrowed to those two phrasings —
    which between them name a fixed pair of specs, and are therefore a plan list
    wearing a regex — fails here while every other sweep control still passes.
    """
    lowered = _OWN_WORDS_SWEEP_BODY.lower()

    assert 'tree entire' not in lowered
    assert 'pairs with no other' not in lowered
    assert partition_mod.is_sweep_declaration(_OWN_WORDS_SWEEP_BODY)


def test_the_sweep_marker_does_not_fire_on_a_spec_quoting_anothers_declaration() -> None:
    """Near-miss control: a quotation is not a declaration.

    A spec that analyses the corpus cites a sibling's crossing sentence while
    claiming an ordinary slice of its own. Reading the citation as this spec's
    own declaration would make the analysing plan a sweep and hand its tests to a
    neighbour — which is why the crossing alternative reads the epic's reduction
    SLICES rather than the phrase an analysis quotes.
    """
    assert not partition_mod.is_sweep_declaration(_QUOTING_BODY)


def test_an_own_words_sweep_does_not_contest_a_slices_ownership(
    repo: Path, tmp_path: Path
) -> None:
    """The anti-degeneration control, carried through to the partition.

    The marker firing is only half the claim: the plan it marks must also stop
    competing for ownership, which is the behaviour the single-bucket collapse
    came from.
    """
    plans = tmp_path / 'own_words'
    plans.mkdir()
    build_corpus(
        plans, {'PLAN-110.md': SPECS['PLAN-110.md'], 'PLAN-201.md': _OWN_WORDS_SWEEP_BODY}
    )
    claims = classify_corpus(plans, repo)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)
    sweeps = partition_mod.derive_sweep_plans(claims, plans)

    result = partition_mod.derive_partition(claims, modules, sweeps)

    assert sweeps == frozenset({'PLAN-201'})
    assert verdict_of(result, 'test/beta/test_three.py') == partition_mod.VERDICT_CLAIMED
    assert plans_of(result, 'test/beta/test_three.py') == ('PLAN-110',)


def test_a_quoting_spec_is_still_an_ordinary_slice(repo: Path, tmp_path: Path) -> None:
    """The near-miss carried through: the analysing plan keeps competing."""
    plans = tmp_path / 'quoting'
    plans.mkdir()
    build_corpus(plans, {'PLAN-110.md': SPECS['PLAN-110.md'], 'PLAN-211.md': _QUOTING_BODY})
    claims = classify_corpus(plans, repo)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)
    sweeps = partition_mod.derive_sweep_plans(claims, plans)

    result = partition_mod.derive_partition(claims, modules, sweeps)

    assert sweeps == frozenset()
    assert verdict_of(result, 'test/beta/test_three.py') == partition_mod.VERDICT_CONTESTED


def test_the_sweep_marker_does_not_fire_on_an_equally_broad_claim() -> None:
    """Matched negative: breadth is not a self-declaration.

    A plan claiming the same directory without declaring itself a sweep is an
    ordinary slice, and must keep contesting. A marker that keyed on breadth
    would silently hand every wide claim an exemption from ownership.
    """
    assert not partition_mod.is_sweep_declaration(_BROAD_BODY)


def test_the_sweep_marker_names_no_plan_identifier() -> None:
    """The mechanism is corpus-independent by construction.

    A hard-coded plan list here would be the same defect the derivation exists
    to close, one level down.
    """
    assert 'PLAN' not in partition_mod._SWEEP_RE.pattern.upper()


def test_a_sweep_does_not_contest_a_slices_ownership(repo: Path, tmp_path: Path) -> None:
    """One slice plus any number of sweeps: the SLICE owns the module."""
    plans = tmp_path / 'sweeps'
    plans.mkdir()
    build_corpus(plans, {'PLAN-110.md': SPECS['PLAN-110.md'], 'PLAN-200.md': _SWEEP_BODY})
    claims = classify_corpus(plans, repo)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)
    sweeps = partition_mod.derive_sweep_plans(claims, plans)

    result = partition_mod.derive_partition(claims, modules, sweeps)

    assert sweeps == frozenset({'PLAN-200'})
    assert verdict_of(result, 'test/beta/test_three.py') == partition_mod.VERDICT_CLAIMED
    assert plans_of(result, 'test/beta/test_three.py') == ('PLAN-110',)


def test_the_crossing_sweep_is_recorded_as_a_separate_fact(repo: Path, tmp_path: Path) -> None:
    """The crossing is REPORTED, never silently dropped — it is just not ownership."""
    plans = tmp_path / 'sweeps'
    plans.mkdir()
    build_corpus(plans, {'PLAN-110.md': SPECS['PLAN-110.md'], 'PLAN-200.md': _SWEEP_BODY})
    claims = classify_corpus(plans, repo)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)
    sweeps = partition_mod.derive_sweep_plans(claims, plans)

    result = partition_mod.derive_partition(claims, modules, sweeps)
    module = next(m for m in result.modules if m.path == 'test/beta/test_three.py')

    assert module.sweeps == ('PLAN-200',)


def test_a_non_declaring_broad_plan_still_contests(repo: Path, tmp_path: Path) -> None:
    """Matched negative at the PARTITION level, mirroring the marker-level one."""
    plans = tmp_path / 'broad'
    plans.mkdir()
    build_corpus(plans, {'PLAN-110.md': SPECS['PLAN-110.md'], 'PLAN-210.md': _BROAD_BODY})
    claims = classify_corpus(plans, repo)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)
    sweeps = partition_mod.derive_sweep_plans(claims, plans)

    result = partition_mod.derive_partition(claims, modules, sweeps)

    assert sweeps == frozenset()
    assert verdict_of(result, 'test/beta/test_three.py') == partition_mod.VERDICT_CONTESTED


def test_a_module_only_sweeps_cover_is_swept_with_no_owner_invented(
    repo: Path, tmp_path: Path
) -> None:
    """Zero slices and one sweep: the crossing is reported, no owner manufactured."""
    plans = tmp_path / 'sweep_only'
    plans.mkdir()
    build_corpus(plans, {'PLAN-200.md': _SWEEP_BODY})
    claims = classify_corpus(plans, repo)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)
    sweeps = partition_mod.derive_sweep_plans(claims, plans)

    result = partition_mod.derive_partition(claims, modules, sweeps)
    module = next(m for m in result.modules if m.path == 'test/beta/test_three.py')

    assert module.verdict == partition_mod.VERDICT_SWEPT
    assert module.plans == ()
    assert module.sweeps == ('PLAN-200',)


# --- rule 2: the lead-shaped entry stage 1 publishes -------------------------

#: The same path, claimed once as a LEAD and once as an ordinary claim. The two
#: bodies differ only in the marker, so the control pair isolates the shape.
_LEAD_BODY = (
    '# PLAN-220\n\n## Expected Surface\n\n'
    '- HYPOTHESIS: `test/beta/` — R1\'s output (verify-at-outline)\n'
)
_UNMARKED_BODY = '# PLAN-230\n\n## Expected Surface\n\n- OBSERVED: `test/beta/`\n'


def test_a_lead_shaped_entry_lands_in_not_derivable(repo: Path, tmp_path: Path) -> None:
    """A lead names a path without claiming it, so it cannot own the module.

    It is coverage the derivation cannot attribute — ``not_derivable`` — and
    never ``unclaimed``, which would report the parser's own limit as a
    partition defect.
    """
    plans = tmp_path / 'lead'
    plans.mkdir()
    build_corpus(plans, {'PLAN-220.md': _LEAD_BODY})
    claims = classify_corpus(plans, repo)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)

    result = partition_mod.derive_partition(claims, modules)

    assert verdict_of(result, 'test/beta/test_three.py') == partition_mod.VERDICT_NOT_DERIVABLE
    assert plans_of(result, 'test/beta/test_three.py') == ('PLAN-220',)


def test_an_unmarked_entry_with_the_same_path_still_claims(repo: Path, tmp_path: Path) -> None:
    """Matched negative for the demotion: only the SHAPE differs between the two."""
    plans = tmp_path / 'unmarked'
    plans.mkdir()
    build_corpus(plans, {'PLAN-230.md': _UNMARKED_BODY})
    claims = classify_corpus(plans, repo)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)

    result = partition_mod.derive_partition(claims, modules)

    assert verdict_of(result, 'test/beta/test_three.py') == partition_mod.VERDICT_CLAIMED
    assert plans_of(result, 'test/beta/test_three.py') == ('PLAN-230',)


def test_the_demotion_happens_here_and_not_in_the_shared_reader(
    repo: Path, tmp_path: Path
) -> None:
    """Stage 1 states the shape and demotes nothing; THIS stage demotes.

    Pins the projection half of the shared reader's contract: the lead entry is
    still a member of ``claimed`` as the reader published it, so the other
    consumer's surface is untouched, and only the partition treats it as
    non-owning.
    """
    plans = tmp_path / 'lead'
    plans.mkdir()
    build_corpus(plans, {'PLAN-220.md': _LEAD_BODY})
    claims = classify_corpus(plans, repo)

    assert [entry.path for entry in claims[0].claimed] == ['test/beta/']


# --- rule 3: a derived spec owns nothing -------------------------------------

#: A spec declaring its surface the union of other plans' — the same shape the
#: corpus's campaign-roll-up spec carries.
_DERIVED_BODY = (
    '# PLAN-240\n\n## Expected Surface\n\n'
    "- **DERIVED** — this plan's surface is the union of the slice plans' surfaces\n"
    '- OBSERVED: `test/beta/` — restating the slice that owns it\n'
)


def test_a_derived_spec_does_not_contest_a_slices_ownership(
    repo: Path, tmp_path: Path
) -> None:
    """A union of other plans' surfaces restates their claims, never competes."""
    plans = tmp_path / 'derived'
    plans.mkdir()
    build_corpus(plans, {'PLAN-110.md': SPECS['PLAN-110.md'], 'PLAN-240.md': _DERIVED_BODY})
    claims = classify_corpus(plans, repo)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)

    result = partition_mod.derive_partition(claims, modules)

    assert verdict_of(result, 'test/beta/test_three.py') == partition_mod.VERDICT_CLAIMED
    assert plans_of(result, 'test/beta/test_three.py') == ('PLAN-110',)


def test_a_derived_specs_own_coverage_is_reported_not_derivable(
    repo: Path, tmp_path: Path
) -> None:
    """Its coverage is real but unattributable, so it is stated rather than dropped."""
    plans = tmp_path / 'derived_only'
    plans.mkdir()
    build_corpus(plans, {'PLAN-240.md': _DERIVED_BODY})
    claims = classify_corpus(plans, repo)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)

    result = partition_mod.derive_partition(claims, modules)

    assert verdict_of(result, 'test/beta/test_three.py') == partition_mod.VERDICT_NOT_DERIVABLE
    assert plans_of(result, 'test/beta/test_three.py') == ('PLAN-240',)


def test_a_declarative_spec_with_the_same_entry_still_claims(
    repo: Path, tmp_path: Path
) -> None:
    """Matched negative for rule 3: only the spec CLASS differs between the two."""
    plans = tmp_path / 'declarative'
    plans.mkdir()
    build_corpus(plans, {'PLAN-230.md': _UNMARKED_BODY})
    claims = classify_corpus(plans, repo)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)

    result = partition_mod.derive_partition(claims, modules)

    assert claims[0].spec_class != 'derived'
    assert verdict_of(result, 'test/beta/test_three.py') == partition_mod.VERDICT_CLAIMED


def test_the_three_non_owning_rules_are_independent(repo: Path, tmp_path: Path) -> None:
    """Each rule fires with the other two absent.

    Guards against a collapsed implementation that demanded more than one signal
    before treating an entry as non-owning — which would pass each combined
    fixture above while leaving single-signal specs owning what they only name.
    """
    outcomes = {}
    for name, body in (
        ('sweep', _SWEEP_BODY),
        ('lead', _LEAD_BODY),
        ('derived', _DERIVED_BODY),
    ):
        plans = tmp_path / f'solo_{name}'
        plans.mkdir()
        build_corpus(plans, {'PLAN-300.md': body})
        claims = classify_corpus(plans, repo)
        modules = partition_mod.iter_test_modules(repo / 'test', repo)
        sweeps = partition_mod.derive_sweep_plans(claims, plans)
        result = partition_mod.derive_partition(claims, modules, sweeps)
        outcomes[name] = verdict_of(result, 'test/beta/test_three.py')

    assert outcomes == {
        'sweep': partition_mod.VERDICT_SWEPT,
        'lead': partition_mod.VERDICT_NOT_DERIVABLE,
        'derived': partition_mod.VERDICT_NOT_DERIVABLE,
    }


# --- the residual drivers, measured together ---------------------------------
#
# The three shapes that kept the live epic's attribution collapsed, reproduced
# over one small tree so the outcome is measurable rather than asserted against a
# figure taken from a corpus this suite cannot read. Each driver carries its own
# wording and a matched near-miss differing only in the marker, so the cluster
# reads as a differential: with the driver read, the contest disappears; with the
# near-miss substituted, it returns.

_RESIDUAL_MODULES = (
    'test/plan-marshall/alpha/test_one.py',
    'test/plan-marshall/beta/test_two.py',
    'test/pm-plugin-development/test_three.py',
)

#: The ordinary slice plans the drivers were contesting. Between them they claim
#: every module in the tree exactly once.
_SLICE_SPECS = {
    'PLAN-410.md': '# PLAN-410\n\n## Expected Surface\n\n'
    '- OBSERVED: `test/plan-marshall/alpha/`\n',
    'PLAN-420.md': '# PLAN-420\n\n## Expected Surface\n\n'
    '- OBSERVED: `test/plan-marshall/beta/`\n'
    '- OBSERVED: `test/pm-plugin-development/`\n',
}

#: Each driver as ``(spec name, its own wording, its matched near-miss)``. The
#: two bodies of a pair differ ONLY in the marker the rule reads, so a difference
#: in outcome is attributable to that rule and to nothing else.
_DRIVER_SPECS = {
    'cross_plan_reference': (
        'PLAN-430.md',
        '# PLAN-430\n\n## Expected Surface\n\n'
        "- OBSERVED: slice `410`'s two directories under `test/plan-marshall/` — the "
        'fidelity check\n',
        '# PLAN-430\n\n## Expected Surface\n\n'
        '- OBSERVED: two directories under `test/plan-marshall/` — the fidelity check\n',
    ),
    'hedged_conditional_claim': (
        'PLAN-440.md',
        '# PLAN-440\n\n## Expected Surface\n\n'
        "- OBSERVED: the tests for this plan's own production changes, under "
        '`test/plan-marshall/`. ⚠️ **Only where a seam requires its own test** — this '
        'plan does not otherwise edit `test/**`\n',
        '# PLAN-440\n\n## Expected Surface\n\n'
        "- OBSERVED: the tests for this plan's own production changes, under "
        '`test/plan-marshall/`\n',
    ),
    'own_words_sweep': (
        'PLAN-450.md',
        '# PLAN-450\n\n## Expected Surface\n\n'
        '- OBSERVED: `test/plan-marshall/alpha/` — the sites this plan converts\n'
        '\n⚠️ **This surface crosses several reduction slices deliberately** — skip sites '
        "do not respect the epic's partition.\n",
        '# PLAN-450\n\n## Expected Surface\n\n'
        '- OBSERVED: `test/plan-marshall/alpha/` — the sites this plan converts\n'
        '\nOne sibling reads "this plan crosses the whole partition by construction"; '
        'this one claims an ordinary slice.\n',
    ),
}

#: The modules each driver's near-miss returns to the contested set, and the
#: plans it returns them to. Stated per driver so a differential that collapsed
#: into "something changed" cannot pass.
_NEAR_MISS_CONTESTS = {
    'cross_plan_reference': {
        'test/plan-marshall/alpha/test_one.py': ('PLAN-410', 'PLAN-430'),
        'test/plan-marshall/beta/test_two.py': ('PLAN-420', 'PLAN-430'),
    },
    'hedged_conditional_claim': {
        'test/plan-marshall/alpha/test_one.py': ('PLAN-410', 'PLAN-440'),
        'test/plan-marshall/beta/test_two.py': ('PLAN-420', 'PLAN-440'),
    },
    'own_words_sweep': {
        'test/plan-marshall/alpha/test_one.py': ('PLAN-410', 'PLAN-450'),
    },
}


@pytest.fixture
def residual_repo(tmp_path: Path) -> Path:
    root = tmp_path / 'residual_repo'
    (root / 'test').mkdir(parents=True)
    for rel in _RESIDUAL_MODULES:
        write_module(root, rel)
    return root


def residual_partition(
    repo: Path, tmp_path: Path, near_miss: str | None, extra: dict[str, str] | None = None
) -> partition_mod.Partition:
    """Derive the residual corpus, optionally with ONE driver's near-miss substituted."""
    plans = tmp_path / f'residual_{near_miss or "all"}_{len(extra or {})}'
    plans.mkdir()
    specs = dict(_SLICE_SPECS)
    for driver, (name, own_wording, near_miss_wording) in _DRIVER_SPECS.items():
        specs[name] = near_miss_wording if driver == near_miss else own_wording
    specs.update(extra or {})
    build_corpus(plans, specs)
    claims = classify_corpus(plans, repo)
    modules = partition_mod.iter_test_modules(repo / 'test', repo)
    sweeps = partition_mod.derive_sweep_plans(claims, plans)
    return partition_mod.derive_partition(claims, modules, sweeps)


def contests_of(result: partition_mod.Partition) -> dict[str, tuple[str, ...]]:
    return {
        module.path: module.plans
        for module in result.with_verdict(partition_mod.VERDICT_CONTESTED)
    }


def test_every_driver_read_leaves_no_module_contested(
    residual_repo: Path, tmp_path: Path
) -> None:
    """The headline outcome: each module is attributed to the slice that owns it.

    None of the three drivers is an ownership claim, so with all three read the
    contested population is empty and every module carries a single owning slice
    — the state the attribution was unusable without.
    """
    result = residual_partition(residual_repo, tmp_path, near_miss=None)

    assert contests_of(result) == {}
    assert {module.path: module.plans for module in result.modules} == {
        'test/plan-marshall/alpha/test_one.py': ('PLAN-410',),
        'test/plan-marshall/beta/test_two.py': ('PLAN-420',),
        'test/pm-plugin-development/test_three.py': ('PLAN-420',),
    }


@pytest.mark.parametrize('driver', sorted(_DRIVER_SPECS), ids=sorted(_DRIVER_SPECS))
def test_each_driver_is_resolved_by_its_own_rule(
    residual_repo: Path, tmp_path: Path, driver: str
) -> None:
    """Per-driver differential: substituting the near-miss returns the contest.

    Each pair differs only in the marker its rule reads, so this attributes the
    resolved contest to that one rule rather than to the three together. A rule
    that silently stopped firing shows up here as one named driver, not as a
    changed total.
    """
    restored = residual_partition(residual_repo, tmp_path, near_miss=driver)

    assert contests_of(restored) == _NEAR_MISS_CONTESTS[driver]


def test_a_genuine_two_slice_overlap_is_still_reported_as_contested(
    residual_repo: Path, tmp_path: Path
) -> None:
    """The residual set keeps its signal: a real overlap survives every rule.

    Two slice plans claiming one directory outright, neither citing the other and
    neither withdrawing its span, is the disagreement the derivation exists to
    surface. Rules that resolved it too would have bought a clean report by
    deleting the finding.
    """
    overlap = {
        'PLAN-460.md': '# PLAN-460\n\n## Expected Surface\n\n'
        '- OBSERVED: `test/plan-marshall/alpha/`\n'
    }

    result = residual_partition(residual_repo, tmp_path, near_miss=None, extra=overlap)

    assert contests_of(result) == {
        'test/plan-marshall/alpha/test_one.py': ('PLAN-410', 'PLAN-460')
    }


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
        ('test/beta/test_three.py', partition_mod.OWNER_CONTESTED),
        ('test/gamma/test_four_x.py', partition_mod.OWNER_NOT_DERIVABLE),
    ],
    ids=['unclaimed', 'contested', 'not_derivable'],
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

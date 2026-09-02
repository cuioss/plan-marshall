#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the epic-spec parser — entry-shape resolution and the three-class verdict.

Subject: ``plan-marshall:script-shared``'s ``epic_spec_parser``, the marketplace's
SINGLE reader of the ``## Expected Surface`` grammar. Both the orchestrator's
disjointness gate and ``pm-plugin-development:tools-epic-surface-partition``
consume it, so its coverage lives with the module rather than with either
consumer.

Entry SHAPE — whether an entry is an ownership claim or a lead the spec has not
settled — is resolved per ENTRY by two marker rules, and the shape cluster below
covers each rule independently: a positive control, a negative control over the
whole-tree wording that must NOT fire, a matched negative that no spec-level
resolution could produce, and an additivity control pinning that a marked entry
keeps its membership of ``claimed``.

Markdown-notation tolerance — code-block masking, label prefixes, heading
spelling — is the sibling cluster, in ``test_epic_spec_parser_notation.py``.
Every corpus is built under ``tmp_path``: the real orchestrator store is neither
read nor written, including by the corpus-oracle cluster, which reproduces the
live corpus's wording rather than reading it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import load_script_module

#: The subject, addressed by three module-level string constants so the loader
#: call stays statically resolvable to ``test_conftest_loader_contract``'s walker.
#: ``register=False`` because only the returned module is needed here, and the
#: stem ``epic_spec_parser`` is imported plainly by the partition suites —
#: publishing under it would displace theirs and trip the collision guard.
_BUNDLE = 'plan-marshall'
_SKILL = 'script-shared'
_SCRIPT = 'epic_spec_parser.py'

spec_parser = load_script_module(_BUNDLE, _SKILL, _SCRIPT, register=False)


# --- scaffolding -------------------------------------------------------------


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repository root carrying the top-level entries the parser roots against."""
    root = tmp_path / 'repo'
    (root / 'test').mkdir(parents=True)
    (root / 'marketplace').mkdir(parents=True)
    (root / 'pyproject.toml').write_text('[tool]\n', encoding='utf-8')
    return root


@pytest.fixture
def plans(tmp_path: Path) -> Path:
    """An epic's ``plans/`` directory, empty."""
    directory = tmp_path / 'plans'
    directory.mkdir()
    return directory


def write_spec(plans_dir: Path, name: str, body: str) -> Path:
    path = plans_dir / name
    path.write_text(body, encoding='utf-8')
    return path


def claim_for(plans_dir: Path, repo_root: Path, name: str, body: str):
    return spec_parser.classify_spec(write_spec(plans_dir, name, body), repo_root)


def paths(entries) -> set[str]:
    return {entry.path for entry in entries}


# --- entry shapes ------------------------------------------------------------

SHAPES_SPEC = """# PLAN-100

## Expected Surface

- Adds `test/alpha/` and `test/alpha/**`
- Adds `test/alpha/test_one.py`, `test/alpha/test_two.py`
- Adds `test/beta/test_*.py`
- Touches `marketplace/bundles/demo/SKILL.md`
"""


@pytest.fixture
def shapes_claim(repo: Path, plans: Path):
    return claim_for(plans, repo, 'PLAN-100.md', SHAPES_SPEC)


@pytest.mark.parametrize(
    ('path', 'kind'),
    [
        ('test/alpha/', spec_parser.KIND_DIRECTORY),
        ('test/alpha/**', spec_parser.KIND_RECURSIVE_GLOB),
        ('test/alpha/test_one.py', spec_parser.KIND_FILE),
        ('test/beta/test_*.py', spec_parser.KIND_FILENAME_GLOB),
        ('marketplace/bundles/demo/SKILL.md', spec_parser.KIND_FILE),
    ],
    ids=['directory', 'recursive_glob', 'named_file', 'filename_glob', 'non_test_root'],
)
def test_entry_shape_resolves_with_its_kind(shapes_claim, path: str, kind: str) -> None:
    resolved = {entry.path: entry.kind for entry in shapes_claim.claimed}

    assert resolved[path] == kind


def test_comma_separated_entries_in_one_bullet_all_resolve(shapes_claim) -> None:
    assert {'test/alpha/test_one.py', 'test/alpha/test_two.py'} <= paths(shapes_claim.claimed)


def test_non_test_root_entry_resolves(shapes_claim) -> None:
    assert 'marketplace/bundles/demo/SKILL.md' in paths(shapes_claim.claimed)


@pytest.mark.parametrize(
    'sibling',
    ['`test_*.py`', '`.../test_*.py`'],
    ids=['bare_sibling', 'ellipsis_slash'],
)
def test_relative_entry_resolves_against_the_bullets_rooted_base(
    repo: Path, plans: Path, sibling: str
) -> None:
    body = f'# PLAN-101\n\n## Expected Surface\n\n- Adds `test/delta/**` and its {sibling} modules\n'

    claim = claim_for(plans, repo, 'PLAN-101.md', body)

    assert paths(claim.claimed) == {'test/delta/**', 'test/delta/test_*.py'}


def test_dot_slash_first_entry_leaves_its_siblings_repo_relative(
    repo: Path, plans: Path
) -> None:
    """A ``./`` prefix on the bullet's FIRST entry does not poison the base.

    The prefix normalises away before the base is taken, so later relative
    siblings resolve against the real parent. A retained ``./`` would make the
    base ``./test/delta/`` and resolve every sibling to a path no test module
    carries — an entry that silently claims nothing instead of the sibling.
    """
    body = (
        '# PLAN-103\n\n## Expected Surface\n\n'
        '- Adds `./test/delta/**` and its `test_*.py` modules\n'
    )

    claim = claim_for(plans, repo, 'PLAN-103.md', body)

    assert paths(claim.claimed) == {'test/delta/**', 'test/delta/test_*.py'}


def test_relative_entry_without_a_base_is_recorded_unresolved(repo: Path, plans: Path) -> None:
    body = (
        '# PLAN-102\n\n## Expected Surface\n\n'
        '- Adds `test/alpha/test_one.py`\n'
        '- Adds `test_orphan_*.py`\n'
    )

    claim = claim_for(plans, repo, 'PLAN-102.md', body)

    assert claim.unresolved == ('test_orphan_*.py',)
    assert paths(claim.claimed) == {'test/alpha/test_one.py'}


# --- entry shape: rule (a), the lead marker ----------------------------------
#
# A HYPOTHESIS label or the verify-at-outline deferral phrase marks a path the
# spec POINTS AT rather than claims. Every fixture in this section is free of
# rule (b)'s marker, so each assertion is about rule (a) alone.


def test_a_hypothesis_label_resolves_its_entries_to_a_lead(repo: Path, plans: Path) -> None:
    """Rule (a), the label half — positive control."""
    body = (
        '# PLAN-200\n\n## Expected Surface\n\n'
        "- HYPOTHESIS: guards across `test/omega/**` carrying a path literal — R1's output\n"
    )

    claim = claim_for(plans, repo, 'PLAN-200.md', body)
    entry = next(entry for entry in claim.claimed if entry.path == 'test/omega/**')

    assert entry.shape == spec_parser.SHAPE_LEAD


def test_the_verify_at_outline_phrase_resolves_its_entries_to_a_lead(
    repo: Path, plans: Path
) -> None:
    """Rule (a), the phrase half — positive control, and the label is OBSERVED.

    The two halves are independent signals: this bullet carries no HYPOTHESIS
    label, so a rule reading only the label would leave the entry a claim.
    """
    body = (
        '# PLAN-201\n\n## Expected Surface\n\n'
        '- OBSERVED: `test/omega/` or a sibling the tree indicates (verify-at-outline)\n'
    )

    claim = claim_for(plans, repo, 'PLAN-201.md', body)
    entry = next(entry for entry in claim.claimed if entry.path == 'test/omega/')

    assert entry.shape == spec_parser.SHAPE_LEAD


def test_an_observed_whole_tree_declaration_stays_a_claim(repo: Path, plans: Path) -> None:
    """Negative control, in the corpus's own whole-tree wording.

    A plan that deliberately crosses the entire tree declares exactly this shape.
    Marking it a lead would demote a real ownership claim and hand the whole
    tree back to the contested set — the opposite of the defect the rules exist
    to fix.
    """
    body = (
        '# PLAN-202\n\n## Expected Surface\n\n'
        "- OBSERVED: `test/` — ⛔ **the whole tree.** The rule's findings do not respect "
        "slice boundaries, so this plan's surface is the test tree entire\n"
    )

    claim = claim_for(plans, repo, 'PLAN-202.md', body)
    entry = next(entry for entry in claim.claimed if entry.path == 'test/')

    assert entry.shape == spec_parser.SHAPE_CLAIM


def test_a_lead_entry_keeps_its_membership_of_claimed(repo: Path, plans: Path) -> None:
    """Additivity control for rule (a).

    The shape is an ADDED field, never a re-partition. Were a lead routed into a
    third accumulator instead, the orchestrator's queue cell and its disjointness
    input would silently shrink, and a colliding plan would read as disjoint.
    """
    body = (
        '# PLAN-203\n\n## Expected Surface\n\n'
        '- HYPOTHESIS: sweeps across `test/omega/**` (verify-at-outline)\n'
    )

    claim = claim_for(plans, repo, 'PLAN-203.md', body)

    assert paths(claim.claimed) == {'test/omega/**'}
    assert claim.excluded == ()
    assert [entry.shape for entry in claim.claimed] == [spec_parser.SHAPE_LEAD]


def test_one_declarative_spec_carries_both_a_claim_and_a_lead(repo: Path, plans: Path) -> None:
    """Matched negative control: the OLD per-spec-class resolution cannot pass this.

    Both entries live in ONE spec, so they share one ``spec_class``. Any
    resolution that read entry shape off that class must give them the SAME
    shape and fail here; only a per-entry rule can give them different ones.
    """
    body = (
        '# PLAN-204\n\n## Expected Surface\n\n'
        '- OBSERVED: `test/alpha/test_one.py` — the module this plan rewrites\n'
        "- HYPOTHESIS: further instances across `test/omega/**` — R1's output "
        '(verify-at-outline)\n'
    )

    claim = claim_for(plans, repo, 'PLAN-204.md', body)
    shapes = {entry.path: entry.shape for entry in claim.claimed}

    assert claim.spec_class == spec_parser.CLASS_DECLARATIVE
    assert shapes == {
        'test/alpha/test_one.py': spec_parser.SHAPE_CLAIM,
        'test/omega/**': spec_parser.SHAPE_LEAD,
    }


# --- entry shape: rule (b), the collection constraint ------------------------
#
# A bullet citing pytest's ``testpaths`` key states where the runner COLLECTS
# from — a constraint the plan's own test location must satisfy, not a claim on
# that tree. Every fixture in this section is free of rule (a)'s markers, so each
# assertion is about rule (b) alone.


def test_a_testpaths_collection_constraint_resolves_its_entry_to_a_lead(
    repo: Path, plans: Path
) -> None:
    """Rule (b) — positive control, in the corpus's own wording.

    The marker sits in the bullet's trailing commentary, which contributes no
    entry of its own; the shape is still resolved from the whole bullet, so the
    head's ``test/`` is marked by it.
    """
    body = (
        '# PLAN-210\n\n## Expected Surface\n\n'
        "- OBSERVED: that script's tests, under `test/` — `pyproject.toml` sets "
        '`testpaths = ["test"]`, so a module outside that tree is never collected\n'
    )

    claim = claim_for(plans, repo, 'PLAN-210.md', body)
    entry = next(entry for entry in claim.claimed if entry.path == 'test/')

    assert entry.shape == spec_parser.SHAPE_LEAD


def test_an_observed_bullet_without_the_constraint_stays_a_claim(
    repo: Path, plans: Path
) -> None:
    """Negative control: the same entry, the same label, no collection constraint."""
    body = (
        '# PLAN-211\n\n## Expected Surface\n\n'
        "- OBSERVED: that script's tests, under `test/` — the home this plan adds them to\n"
    )

    claim = claim_for(plans, repo, 'PLAN-211.md', body)
    entry = next(entry for entry in claim.claimed if entry.path == 'test/')

    assert entry.shape == spec_parser.SHAPE_CLAIM


def test_a_collection_constraint_entry_keeps_its_membership_of_claimed(
    repo: Path, plans: Path
) -> None:
    """Additivity control for rule (b), matching rule (a)'s."""
    body = (
        '# PLAN-212\n\n## Expected Surface\n\n'
        '- OBSERVED: tests under `test/` — `testpaths` decides where they are collected\n'
    )

    claim = claim_for(plans, repo, 'PLAN-212.md', body)

    assert paths(claim.claimed) == {'test/'}
    assert claim.excluded == ()
    assert [entry.shape for entry in claim.claimed] == [spec_parser.SHAPE_LEAD]


def test_one_declarative_spec_carries_both_a_claim_and_a_collection_constraint(
    repo: Path, plans: Path
) -> None:
    """Matched negative control for rule (b), matching rule (a)'s.

    One spec, one ``spec_class``, two different entry shapes — unreachable for
    any resolution taken at spec level.
    """
    body = (
        '# PLAN-213\n\n## Expected Surface\n\n'
        '- OBSERVED: `test/alpha/test_one.py` — the module this plan adds\n'
        '- OBSERVED: it must sit under `test/` — `testpaths` decides what is collected\n'
    )

    claim = claim_for(plans, repo, 'PLAN-213.md', body)
    shapes = {entry.path: entry.shape for entry in claim.claimed}

    assert claim.spec_class == spec_parser.CLASS_DECLARATIVE
    assert shapes == {
        'test/alpha/test_one.py': spec_parser.SHAPE_CLAIM,
        'test/': spec_parser.SHAPE_LEAD,
    }


def test_the_two_rules_fire_independently_of_each_other(repo: Path, plans: Path) -> None:
    """Neither rule needs the other's marker present to fire.

    Guards against a collapsed implementation that required both signals, which
    would pass every positive control above only if each fixture happened to
    carry both markers.
    """
    lead_only = claim_for(
        plans,
        repo,
        'PLAN-214.md',
        '# PLAN-214\n\n## Expected Surface\n\n- HYPOTHESIS: `test/omega/**`\n',
    )
    constraint_only = claim_for(
        plans,
        repo,
        'PLAN-215.md',
        '# PLAN-215\n\n## Expected Surface\n\n'
        '- OBSERVED: `test/omega/` — `testpaths` decides collection\n',
    )

    assert [entry.shape for entry in lead_only.claimed] == [spec_parser.SHAPE_LEAD]
    assert [entry.shape for entry in constraint_only.claimed] == [spec_parser.SHAPE_LEAD]


# --- the corpus oracle rows --------------------------------------------------
#
# The five live-corpus entries the two rules must resolve to leads, each named by
# its spec, together with the two whole-tree claims that must SURVIVE. The
# corpus's own wording is reproduced here rather than read from the orchestrator
# store, so the assertions are about the RULES and this suite stays hermetic.

_ORACLE_CORPUS = {
    'PLAN-105.md': (
        '# PLAN-105\n\n## Expected Surface\n\n'
        '- OBSERVED: `test/pm-plugin-development/plugin-doctor/` — D3\'s tests\n'
        '- HYPOTHESIS: **~391 files across `test/` and `marketplace/bundles/`** — '
        "D7's final sweep (verify-at-outline). ⛔ **The widest surface in the plan**\n"
    ),
    'PLAN-120.md': (
        '# PLAN-120\n\n## Expected Surface\n\n'
        '- OBSERVED: `test/pm-plugin-development/` — the most likely home for this '
        "checker's tests. ⚠️ **A lead, not a decision**\n"
        "- OBSERVED: that script's tests, under `test/` — `pyproject.toml` sets "
        '`testpaths = ["test"]` and `python_files = ["test_*.py"]`, so a module '
        'outside that tree is never collected\n'
    ),
    'PLAN-130.md': (
        '# PLAN-130\n\n## Expected Surface\n\n'
        "- OBSERVED: `test/` — ⛔ **the whole tree.** The rule's 205 findings do not "
        "respect slice boundaries, so this plan's surface is the test tree entire, and "
        'it pairs with no other `test/`-editing plan\n'
    ),
    'PLAN-135.md': (
        '# PLAN-135\n\n## Expected Surface\n\n'
        "- OBSERVED: `test/` — ⛔ **the whole tree.** The rule's 110 findings do not "
        "respect slice boundaries, so this plan's surface is the test tree entire, and "
        'it pairs with no other `test/`-editing plan\n'
    ),
    'PLAN-160.md': (
        '# PLAN-160\n\n## Expected Surface\n\n'
        '- HYPOTHESIS: guards and controls across `test/**` carrying a cross-slice path '
        "literal — **R1's output** (verify-at-outline)\n"
        '- HYPOTHESIS: constant name/path lists across `test/**` mirroring a live '
        "source — **R3's output** (verify-at-outline)\n"
        '- HYPOTHESIS: `monkeypatch.delitem` / `delenv` sites with conditional teardown '
        "across `test/**` — **R4's output** (verify-at-outline)\n"
    ),
}


@pytest.fixture
def oracle(repo: Path, plans: Path):
    for name, body in _ORACLE_CORPUS.items():
        write_spec(plans, name, body)
    return {claim.plan_id: claim for claim in spec_parser.classify_corpus(plans, repo)}


def test_the_oracle_corpus_is_fully_enumerated(oracle) -> None:
    """Guards the five rows below against a vacuous pass over a corpus that lost a spec."""
    assert sorted(oracle) == ['PLAN-105', 'PLAN-120', 'PLAN-130', 'PLAN-135', 'PLAN-160']


@pytest.mark.parametrize(
    ('plan_id', 'path', 'occurrences'),
    [
        ('PLAN-105', 'test/', 1),
        ('PLAN-160', 'test/**', 3),
        ('PLAN-120', 'test/', 1),
    ],
    ids=['plan_105_lead_marker', 'plan_160_lead_marker', 'plan_120_collection_constraint'],
)
def test_the_oracle_rows_resolve_to_leads(
    oracle, plan_id: str, path: str, occurrences: int
) -> None:
    """The five rows, by name: four by rule (a) and one by rule (b)."""
    rows = [entry for entry in oracle[plan_id].claimed if entry.path == path]

    assert len(rows) == occurrences, f'{plan_id} resolved {len(rows)} {path!r} entries'
    assert [entry.shape for entry in rows] == [spec_parser.SHAPE_LEAD] * occurrences


@pytest.mark.parametrize('plan_id', ['PLAN-130', 'PLAN-135'], ids=['plan_130', 'plan_135'])
def test_the_whole_tree_declarations_survive_as_claims(oracle, plan_id: str) -> None:
    """The negative control both rules are measured against.

    These two plans cross the whole partition by construction. Neither marker
    matches their wording, so their ``test/`` entries stay claims and the specs
    stay ``declarative``.
    """
    rows = [entry for entry in oracle[plan_id].claimed if entry.path == 'test/']

    assert [entry.shape for entry in rows] == [spec_parser.SHAPE_CLAIM]
    assert oracle[plan_id].spec_class == spec_parser.CLASS_DECLARATIVE


def test_no_oracle_spec_loses_an_entry_to_its_shape(oracle) -> None:
    """Additivity across the whole oracle corpus, not just one fixture."""
    resolved = {plan_id: paths(claim.claimed) for plan_id, claim in oracle.items()}

    assert resolved['PLAN-105'] == {
        'test/pm-plugin-development/plugin-doctor/',
        'test/',
        'marketplace/bundles/',
    }
    assert resolved['PLAN-120'] == {'test/pm-plugin-development/', 'test/'}
    assert resolved['PLAN-130'] == {'test/'}
    assert resolved['PLAN-160'] == {'test/**'}


# --- exclusions --------------------------------------------------------------


def test_excluding_keyword_separates_claimed_from_excluded(repo: Path, plans: Path) -> None:
    body = '# PLAN-110\n\n## Expected Surface\n\n- Adds `test/gamma/**` excluding `test/gamma/legacy/`\n'

    claim = claim_for(plans, repo, 'PLAN-110.md', body)

    assert paths(claim.claimed) == {'test/gamma/**'}
    assert paths(claim.excluded) == {'test/gamma/legacy/'}


def test_excluding_after_the_em_dash_is_still_an_exclusion(repo: Path, plans: Path) -> None:
    body = (
        '# PLAN-111\n\n## Expected Surface\n\n'
        '- Adds `test/gamma/**` — excluding `test/gamma/legacy/`\n'
    )

    claim = claim_for(plans, repo, 'PLAN-111.md', body)

    assert paths(claim.claimed) == {'test/gamma/**'}
    assert paths(claim.excluded) == {'test/gamma/legacy/'}


def test_trailing_commentary_without_the_keyword_claims_nothing(repo: Path, plans: Path) -> None:
    body = (
        '# PLAN-112\n\n## Expected Surface\n\n'
        '- Adds `test/gamma/**` — because `test/other/test_z.py` already covers it\n'
    )

    claim = claim_for(plans, repo, 'PLAN-112.md', body)

    assert paths(claim.claimed) == {'test/gamma/**'}
    assert 'test/other/test_z.py' not in paths(claim.excluded)


def test_negative_bullet_records_its_paths_as_excluded(repo: Path, plans: Path) -> None:
    body = (
        '# PLAN-113\n\n## Expected Surface\n\n'
        '- Adds `test/alpha/test_one.py`\n'
        '- No changes to `test/epsilon/`\n'
    )

    claim = claim_for(plans, repo, 'PLAN-113.md', body)

    assert paths(claim.claimed) == {'test/alpha/test_one.py'}
    assert paths(claim.excluded) == {'test/epsilon/'}


def test_out_of_scope_section_entries_are_excluded(repo: Path, plans: Path) -> None:
    body = (
        '# PLAN-114\n\n## Expected Surface\n\n'
        '- Adds `test/alpha/test_one.py`\n\n'
        '## Out of Scope\n\n'
        '- `test/zeta/**`\n'
    )

    claim = claim_for(plans, repo, 'PLAN-114.md', body)

    assert paths(claim.claimed) == {'test/alpha/test_one.py'}
    assert paths(claim.excluded) == {'test/zeta/**'}


# --- the three-class verdict -------------------------------------------------


def test_spec_resolving_to_paths_is_declarative(shapes_claim) -> None:
    assert shapes_claim.spec_class == spec_parser.CLASS_DECLARATIVE
    assert 'test/alpha/' in shapes_claim.evidence or shapes_claim.evidence.startswith('6')


def test_declarative_evidence_names_the_resolved_count(shapes_claim) -> None:
    assert str(len(shapes_claim.claimed)) in shapes_claim.evidence


def test_explicitly_derived_surface_is_classified_derived(repo: Path, plans: Path) -> None:
    body = (
        '# PLAN-140\n\n## Expected Surface\n\n'
        "- **DERIVED** — this plan's surface is the union of what PLAN-138 and "
        'PLAN-139 claim, minus what they land.\n'
    )

    claim = claim_for(plans, repo, 'PLAN-140.md', body)

    assert claim.spec_class == spec_parser.CLASS_DERIVED
    assert 'DERIVED' in claim.evidence


def test_derived_marker_outranks_resolved_paths(repo: Path, plans: Path) -> None:
    body = (
        '# PLAN-141\n\n## Expected Surface\n\n'
        '- **DERIVED** from the sibling plans.\n'
        '- Provisionally `test/alpha/test_one.py`\n'
    )

    claim = claim_for(plans, repo, 'PLAN-141.md', body)

    assert claim.spec_class == spec_parser.CLASS_DERIVED


def test_lowercase_rederive_prose_is_not_a_derived_marker(repo: Path, plans: Path) -> None:
    body = (
        '# PLAN-142\n\n## Expected Surface\n\n'
        '- Adds `test/alpha/test_one.py` — re-derive the list when the corpus grows.\n'
    )

    claim = claim_for(plans, repo, 'PLAN-142.md', body)

    assert claim.spec_class == spec_parser.CLASS_DECLARATIVE


def test_surface_naming_no_resolvable_path_is_prose(repo: Path, plans: Path) -> None:
    body = (
        '# PLAN-150\n\n## Expected Surface\n\n'
        'This plan revises documentation prose only and names no test entry.\n'
    )

    claim = claim_for(plans, repo, 'PLAN-150.md', body)

    assert claim.spec_class == spec_parser.CLASS_PROSE
    assert claim.claimed == ()


def test_prose_class_survives_an_unresolvable_backticked_span(repo: Path, plans: Path) -> None:
    body = '# PLAN-151\n\n## Expected Surface\n\n- Touches `monkeypatch.delitem` behaviour only.\n'

    claim = claim_for(plans, repo, 'PLAN-151.md', body)

    assert claim.spec_class == spec_parser.CLASS_PROSE


# --- the halt ----------------------------------------------------------------


def test_spec_without_the_section_halts_naming_the_spec(repo: Path, plans: Path) -> None:
    body = '# PLAN-300\n\n## Summary\n\nNo surface section is present.\n'
    path = write_spec(plans, 'PLAN-300.md', body)

    with pytest.raises(spec_parser.UnclassifiableSpecError) as raised:
        spec_parser.classify_spec(path, repo)

    assert raised.value.spec == 'PLAN-300.md'
    assert 'Expected Surface' in raised.value.reason


def test_unreadable_spec_halts_rather_than_defaulting(repo: Path, plans: Path) -> None:
    unreadable = plans / 'PLAN-301.md'
    unreadable.mkdir()

    with pytest.raises(spec_parser.UnclassifiableSpecError) as raised:
        spec_parser.classify_spec(unreadable, repo)

    assert raised.value.spec == 'PLAN-301.md'
    assert 'unreadable' in raised.value.reason


def test_corpus_run_halts_on_an_unclassifiable_member(repo: Path, plans: Path) -> None:
    write_spec(plans, 'PLAN-100.md', SHAPES_SPEC)
    write_spec(plans, 'PLAN-300.md', '# PLAN-300\n\n## Summary\n\nNo surface section.\n')

    with pytest.raises(spec_parser.UnclassifiableSpecError):
        spec_parser.classify_corpus(plans, repo)


# --- corpus enumeration ------------------------------------------------------


def test_corpus_is_enumerated_by_glob_in_filename_order(repo: Path, plans: Path) -> None:
    write_spec(plans, 'PLAN-102.md', SHAPES_SPEC.replace('PLAN-100', 'PLAN-102'))
    write_spec(plans, 'PLAN-101.md', SHAPES_SPEC.replace('PLAN-100', 'PLAN-101'))

    claims = spec_parser.classify_corpus(plans, repo)

    assert [claim.plan_id for claim in claims] == ['PLAN-101', 'PLAN-102']


def test_spec_added_to_the_corpus_is_picked_up_without_editing_the_module(
    repo: Path, plans: Path
) -> None:
    write_spec(plans, 'PLAN-101.md', SHAPES_SPEC.replace('PLAN-100', 'PLAN-101'))
    before = spec_parser.classify_corpus(plans, repo)

    write_spec(plans, 'PLAN-102.md', SHAPES_SPEC.replace('PLAN-100', 'PLAN-102'))
    after = spec_parser.classify_corpus(plans, repo)

    assert [claim.plan_id for claim in before] == ['PLAN-101']
    assert [claim.plan_id for claim in after] == ['PLAN-101', 'PLAN-102']


def test_non_spec_files_are_not_enumerated(repo: Path, plans: Path) -> None:
    write_spec(plans, 'PLAN-101.md', SHAPES_SPEC.replace('PLAN-100', 'PLAN-101'))
    write_spec(plans, 'README.md', '# Not a spec\n')
    write_spec(plans, 'NOTES-1.md', '# Not a spec\n')

    claims = spec_parser.classify_corpus(plans, repo)

    assert [claim.spec for claim in claims] == ['PLAN-101.md']


def test_empty_corpus_yields_no_claims(repo: Path, plans: Path) -> None:
    assert spec_parser.classify_corpus(plans, repo) == []


def test_classification_writes_nothing_to_the_corpus(repo: Path, plans: Path) -> None:
    write_spec(plans, 'PLAN-101.md', SHAPES_SPEC.replace('PLAN-100', 'PLAN-101'))
    before = {path.name: path.read_bytes() for path in sorted(plans.iterdir())}

    spec_parser.classify_corpus(plans, repo)

    after = {path.name: path.read_bytes() for path in sorted(plans.iterdir())}
    assert after == before

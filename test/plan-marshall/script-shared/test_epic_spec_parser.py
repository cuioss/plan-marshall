#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the epic-spec parser — entry-shape resolution and the three-class verdict.

Subject: ``plan-marshall:script-shared``'s ``epic_spec_parser``, the marketplace's
SINGLE reader of the ``## Expected Surface`` grammar. Both the orchestrator's
disjointness gate and ``pm-plugin-development:tools-epic-surface-partition``
consume it, so its coverage lives with the module rather than with either
consumer.

Markdown-notation tolerance — code-block masking, label prefixes, heading
spelling — is the sibling cluster, in ``test_epic_spec_parser_notation.py``.
Every corpus is built under ``tmp_path``: the real orchestrator store is neither
read nor written.
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

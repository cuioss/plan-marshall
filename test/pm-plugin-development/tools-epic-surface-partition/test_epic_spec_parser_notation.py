#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the markdown notation the epic-spec parser tolerates.

Two clusters share this module because both answer the same question — which
lines of a spec are surface, and which are only page furniture:

- **Code-block masking** — a code sample inside ``## Expected Surface`` is a
  sample, never a claim and never a verdict. Both block forms are covered, the
  fenced block and the top-level indented block, together with the
  nested-list-item control that distinguishes an indented continuation from
  indented code.
- **Corpus notation tolerances** — bullet markers, label prefixes, heading
  spelling, and where a section body ends.

Entry-shape resolution and the three-class verdict are the sibling cluster, in
``test_epic_spec_parser.py``. Drives the underscore-prefixed helper directly by
inserting the scripts dir on ``sys.path`` (the canonical scaffolding pattern);
every corpus is built under ``tmp_path``, so the real orchestrator store is
neither read nor written.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from conftest import get_scripts_dir

SCRIPTS_DIR = get_scripts_dir('pm-plugin-development', 'tools-epic-surface-partition')
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _epic_spec_parser as spec_parser  # noqa: E402


# --- scaffolding -------------------------------------------------------------


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repository root carrying the top-level entries the parser roots against."""
    root = tmp_path / 'repo'
    (root / 'test').mkdir(parents=True)
    return root


@pytest.fixture
def plans(tmp_path: Path) -> Path:
    """An epic's ``plans/`` directory, empty."""
    directory = tmp_path / 'plans'
    directory.mkdir()
    return directory


def claim_for(plans_dir: Path, repo_root: Path, name: str, body: str):
    path = plans_dir / name
    path.write_text(body, encoding='utf-8')
    return spec_parser.classify_spec(path, repo_root)


def paths(entries) -> set[str]:
    return {entry.path for entry in entries}


# --- fenced blocks -----------------------------------------------------------


def test_fenced_block_entries_are_ignored(repo: Path, plans: Path) -> None:
    body = (
        '# PLAN-121\n\n## Expected Surface\n\n'
        '- Adds `test/theta/test_a.py`\n\n'
        '```text\n'
        '- Adds `test/never/test_b.py`\n'
        '```\n'
    )

    claim = claim_for(plans, repo, 'PLAN-121.md', body)

    assert paths(claim.claimed) == {'test/theta/test_a.py'}


def test_fenced_derived_sample_does_not_override_the_declarative_verdict(
    repo: Path, plans: Path
) -> None:
    body = (
        '# PLAN-160\n\n## Expected Surface\n\n'
        '- Adds `test/alpha/test_one.py`\n\n'
        '```toon\n'
        'spec_class: DERIVED\n'
        '```\n'
    )

    claim = claim_for(plans, repo, 'PLAN-160.md', body)

    assert claim.spec_class == spec_parser.CLASS_DECLARATIVE
    assert 'DERIVED' not in claim.evidence


# --- indented blocks ---------------------------------------------------------


def test_indented_code_sample_is_not_harvested_as_a_bullet(repo: Path, plans: Path) -> None:
    body = (
        '# PLAN-161\n\n## Expected Surface\n\n'
        '- Adds `test/alpha/test_one.py`\n\n'
        'The notation this plan retires reads:\n\n'
        '    - Adds `test/never/test_b.py`\n'
    )

    claim = claim_for(plans, repo, 'PLAN-161.md', body)

    assert paths(claim.claimed) == {'test/alpha/test_one.py'}


def test_indented_derived_sample_does_not_override_the_declarative_verdict(
    repo: Path, plans: Path
) -> None:
    body = (
        '# PLAN-162\n\n## Expected Surface\n\n'
        '- Adds `test/alpha/test_one.py`\n\n'
        'The verdict field this plan emits reads:\n\n'
        '    spec_class: DERIVED\n'
    )

    claim = claim_for(plans, repo, 'PLAN-162.md', body)

    assert claim.spec_class == spec_parser.CLASS_DECLARATIVE


def test_nested_list_item_past_the_third_column_is_a_bullet_not_code(
    repo: Path, plans: Path
) -> None:
    body = (
        '# PLAN-163\n\n## Expected Surface\n\n'
        '- Adds `test/alpha/**`\n'
        '    - and `test/alpha/test_nested.py`\n'
    )

    claim = claim_for(plans, repo, 'PLAN-163.md', body)

    assert paths(claim.claimed) == {'test/alpha/**', 'test/alpha/test_nested.py'}


# --- corpus notation tolerances ----------------------------------------------


@pytest.mark.parametrize('marker', ['-', '*', '+'], ids=['dash', 'asterisk', 'plus'])
def test_every_commonmark_bullet_marker_contributes_its_entry(
    repo: Path, plans: Path, marker: str
) -> None:
    """A marker the scanner does not admit silently under-classes the spec as prose."""
    body = f'# PLAN-124\n\n## Expected Surface\n\n{marker} Adds `test/lambda/test_a.py`\n'

    claim = claim_for(plans, repo, 'PLAN-124.md', body)

    assert paths(claim.claimed) == {'test/lambda/test_a.py'}
    assert claim.spec_class == spec_parser.CLASS_DECLARATIVE


@pytest.mark.parametrize(
    'bullet',
    [
        '- OBSERVED: adds `test/eta/test_x.py`',
        '- HYPOTHESIS: adds `test/eta/test_x.py`',
        '- OBSERVED — **re-derive; narrow scope**: adds `test/eta/test_x.py`',
    ],
    ids=['observed', 'hypothesis', 'observed_qualified'],
)
def test_label_prefix_is_stripped_before_resolution(repo: Path, plans: Path, bullet: str) -> None:
    body = f'# PLAN-120\n\n## Expected Surface\n\n{bullet}\n'

    claim = claim_for(plans, repo, 'PLAN-120.md', body)

    assert paths(claim.claimed) == {'test/eta/test_x.py'}


def test_expected_surface_heading_is_matched_case_insensitively(repo: Path, plans: Path) -> None:
    body = '# PLAN-122\n\n## expected surface\n\n- Adds `test/iota/test_a.py`\n'

    claim = claim_for(plans, repo, 'PLAN-122.md', body)

    assert paths(claim.claimed) == {'test/iota/test_a.py'}


def test_section_body_stops_at_the_next_heading(repo: Path, plans: Path) -> None:
    body = (
        '# PLAN-123\n\n## Expected Surface\n\n'
        '- Adds `test/kappa/test_a.py`\n\n'
        '## Notes\n\n'
        '- Mentions `test/outside/test_b.py`\n'
    )

    claim = claim_for(plans, repo, 'PLAN-123.md', body)

    assert paths(claim.claimed) == {'test/kappa/test_a.py'}

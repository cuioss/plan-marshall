#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the corpus-load error contracts every subcommand publishes.

``_load_corpus`` is the sole seam translating the three load failures into the
TOON payloads SKILL.md § "Step 2: Route on the TOON status" tells callers to
branch on. Renaming one of those codes, or dropping one of the branch-specific
keys, would break every documented caller silently — so each branch is pinned
here by the ``error`` code it emits AND by the keys that branch carries, and a
closing test asserts the same three literals are the ones the routing table
publishes.

The four subcommands share the seam, so every case runs against all four: the
SKILL.md claim that they share the three error shapes is the thing under test,
not an assumption.

Namespaces are built by the script's OWN parser via ``parse_ns`` and dispatched
through the handler the parser wired, so no default is hand-supplied. Every
corpus is built under ``tmp_path``; the real orchestrator store is neither read
nor written.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from conftest import add_skill_scripts_to_path, get_skill_dir, load_script_module, parse_ns

BUNDLE = 'pm-plugin-development'
SKILL = 'tools-epic-surface-partition'
SCRIPT = 'epic-surface-partition.py'

add_skill_scripts_to_path(BUNDLE, SKILL)
entry = load_script_module(BUNDLE, SKILL, SCRIPT, register=False)

#: Every subcommand routes through the same corpus-load seam.
VERBS = ('classify', 'partition', 'attribution', 'report')

#: The three error codes the seam emits, written as literals rather than
#: imported: they ARE the published caller contract, so a rename must show up
#: here as a failing assertion rather than travel silently through an import.
ERROR_INVALID_SLUG = 'invalid_epic_slug'
ERROR_CORPUS_NOT_FOUND = 'epic_corpus_not_found'
ERROR_UNCLASSIFIABLE = 'unclassifiable_spec'

#: A slug carrying traversal and separator components — rejected by the real
#: store resolver, so this branch runs against the production validator.
UNSAFE_SLUG = 'test-quality/../escape'


# --- scaffolding -------------------------------------------------------------


def invoke(verb: str, epic: str) -> dict[str, Any]:
    """Run one subcommand through the real parser and the module under test."""
    namespace = parse_ns(BUNDLE, SKILL, SCRIPT, verb, '--epic', epic, register=False)
    handler = getattr(entry, namespace.handler.__name__)
    payload: dict[str, Any] = handler(namespace)
    return payload


@pytest.fixture
def epic_dir(tmp_path: Path, monkeypatch) -> Path:
    """An epic store root the entry point resolves to, with no ``plans/`` yet."""
    root = tmp_path / 'epic'
    root.mkdir()
    repo = tmp_path / 'repo'
    (repo / 'test').mkdir(parents=True)
    monkeypatch.setattr(entry, 'get_store_dir', lambda *a, **k: root)
    monkeypatch.setattr(entry, 'cwd_checkout_root', lambda: str(repo))
    return root


@pytest.fixture
def unclassifiable(epic_dir: Path) -> Path:
    """The same store root, carrying one spec with no ``## Expected Surface``."""
    plans = epic_dir / 'plans'
    plans.mkdir()
    (plans / 'PLAN-900.md').write_text(
        '# PLAN-900\n\n## Notes\n\nNo surface section here.\n', encoding='utf-8'
    )
    return plans


# --- invalid_epic_slug --------------------------------------------------------


@pytest.mark.parametrize('verb', VERBS)
def test_unsafe_slug_reports_invalid_epic_slug(verb: str) -> None:
    payload = invoke(verb, UNSAFE_SLUG)

    assert payload['status'] == 'error'
    assert payload['error'] == ERROR_INVALID_SLUG


@pytest.mark.parametrize('verb', VERBS)
def test_invalid_epic_slug_carries_the_slug_and_a_reason(verb: str) -> None:
    payload = invoke(verb, UNSAFE_SLUG)

    assert payload['epic'] == UNSAFE_SLUG
    assert payload['reason'].strip()


# --- epic_corpus_not_found ----------------------------------------------------


@pytest.mark.parametrize('verb', VERBS)
def test_absent_plans_directory_reports_epic_corpus_not_found(verb: str, epic_dir: Path) -> None:
    payload = invoke(verb, 'fixture-epic')

    assert payload['status'] == 'error'
    assert payload['error'] == ERROR_CORPUS_NOT_FOUND


@pytest.mark.parametrize('verb', VERBS)
def test_epic_corpus_not_found_names_the_directory_it_looked_for(
    verb: str, epic_dir: Path
) -> None:
    payload = invoke(verb, 'fixture-epic')

    assert payload['epic'] == 'fixture-epic'
    assert payload['plans_dir'] == str(epic_dir / 'plans')


# --- unclassifiable_spec ------------------------------------------------------


@pytest.mark.parametrize('verb', VERBS)
def test_spec_without_a_surface_section_reports_unclassifiable_spec(
    verb: str, unclassifiable: Path
) -> None:
    payload = invoke(verb, 'fixture-epic')

    assert payload['status'] == 'error'
    assert payload['error'] == ERROR_UNCLASSIFIABLE


@pytest.mark.parametrize('verb', VERBS)
def test_unclassifiable_spec_names_the_offending_spec_and_the_cause(
    verb: str, unclassifiable: Path
) -> None:
    payload = invoke(verb, 'fixture-epic')

    assert payload['spec'] == 'PLAN-900.md'
    assert 'Expected Surface' in payload['reason']


# --- the emitted codes are the ones the routing table publishes ---------------


@pytest.mark.parametrize(
    'code', [ERROR_INVALID_SLUG, ERROR_CORPUS_NOT_FOUND, ERROR_UNCLASSIFIABLE]
)
def test_emitted_error_code_appears_in_the_documented_routing_table(code: str) -> None:
    documented = (get_skill_dir(BUNDLE, SKILL) / 'SKILL.md').read_text(encoding='utf-8')

    assert f'`{code}`' in documented

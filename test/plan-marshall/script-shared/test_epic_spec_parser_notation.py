#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the markdown notation the epic-spec parser tolerates.

Subject: ``plan-marshall:script-shared``'s ``epic_spec_parser``, the marketplace's
SINGLE reader of the ``## Expected Surface`` grammar.

Three clusters share this module because all three answer the same question —
which lines of a spec are surface, and which are only page furniture:

- **Code-block masking** — a code sample inside ``## Expected Surface`` is a
  sample, never a claim and never a verdict. Both block forms are covered, the
  fenced block and the top-level indented block, together with the
  nested-list-item control that distinguishes an indented continuation from
  indented code, and the fence-close clauses that decide where a block ENDS.
- **Corpus notation tolerances** — bullet markers, label prefixes, heading
  spelling, and where a section body ends.
- **Plan-id notation** — the three settled spec-name forms
  :data:`epic_spec_parser.PLAN_ID_SEGMENT` admits, and the fallback for a name
  matching none of them.

Entry-shape resolution and the three-class verdict are the sibling cluster, in
``test_epic_spec_parser.py``. Every corpus is built under ``tmp_path``, so the
real orchestrator store is neither read nor written.
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


# --- where a fenced block ENDS -----------------------------------------------
#
# The mask decides where a block CLOSES, and a block that closes too early stops
# masking the lines after it. A ``#`` comment among those lines then reads as a
# heading, the enclosing section is truncated there, and every entry declared
# after it disappears — so the spec resolves to ``prose`` and the disjointness
# gate reads a confident empty surface over a spec that declared files. Each
# case below is a matched pair: a positive control that the declared entries DO
# resolve past the example, and the fence shape that would swallow them.


def test_a_three_backtick_example_does_not_close_a_four_backtick_block(
    repo: Path, plans: Path
) -> None:
    """CommonMark closes only on a run AT LEAST AS LONG as the opener.

    A mask comparing only the fence CHARACTER ends the outer block at the first
    inner ``` — after which the ``#`` comment on the next line reads as a heading
    and truncates the section, dropping BOTH declared entries.
    """
    body = (
        '# PLAN-170\n\n## Expected Surface\n\n'
        '````text\n'
        '# the files this spec expects to touch\n'
        '```\n'
        '# an inner example, not the close of the outer block\n'
        '```\n'
        '````\n'
        '- Adds `test/alpha/test_one.py`\n'
        '- Adds `test/alpha/test_two.py`\n'
    )

    claim = claim_for(plans, repo, 'PLAN-170.md', body)

    assert paths(claim.claimed) == {'test/alpha/test_one.py', 'test/alpha/test_two.py'}
    assert claim.spec_class == spec_parser.CLASS_DECLARATIVE


def test_an_over_indented_delimiter_does_not_close_a_block(repo: Path, plans: Path) -> None:
    """A four-column-indented delimiter is body text, not a close.

    The matched partner of the run-length case above: the same truncation,
    reached through the indentation clause instead of the length clause.
    """
    body = (
        '# PLAN-171\n\n## Expected Surface\n\n'
        '```text\n'
        '# the files this spec expects to touch\n'
        '    ```\n'
        '# an indented delimiter is body text, not the close of this block\n'
        '```\n'
        '- Adds `test/alpha/test_one.py`\n'
        '- Adds `test/alpha/test_two.py`\n'
    )

    claim = claim_for(plans, repo, 'PLAN-171.md', body)

    assert paths(claim.claimed) == {'test/alpha/test_one.py', 'test/alpha/test_two.py'}


def test_a_matching_run_does_close_the_block(repo: Path, plans: Path) -> None:
    """Negative control: the close clauses still CLOSE.

    Without this, a mask that never closed at all would pass both cases above
    while masking the rest of every document.
    """
    body = (
        '# PLAN-172\n\n## Expected Surface\n\n'
        '```text\n'
        '- Adds `test/never/test_b.py`\n'
        '```\n'
        '- Adds `test/alpha/test_one.py`\n'
    )

    claim = claim_for(plans, repo, 'PLAN-172.md', body)

    assert paths(claim.claimed) == {'test/alpha/test_one.py'}


def test_a_backtick_fence_whose_info_string_carries_a_backtick_opens_nothing(
    repo: Path, plans: Path
) -> None:
    """A backtick fence's info string may not itself contain a backtick.

    The line is an ordinary paragraph — the shape a sentence takes when it opens
    with the fence marker and then quotes inline code. Reading it as an opener
    masks the remainder of the section and drops the entries after it.
    """
    body = (
        '# PLAN-173\n\n## Expected Surface\n\n'
        '``` see `x` for the marker\n'
        '- Adds `test/alpha/test_one.py`\n'
    )

    claim = claim_for(plans, repo, 'PLAN-173.md', body)

    assert paths(claim.claimed) == {'test/alpha/test_one.py'}


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


@pytest.mark.parametrize(
    'heading',
    ['## Expected Surface', '## expected surface', '## EXPECTED SURFACE'],
    ids=['template', 'lower', 'upper'],
)
def test_expected_surface_heading_is_matched_case_insensitively(
    repo: Path, plans: Path, heading: str
) -> None:
    """A case variant is a spelling of the same heading, not a different section.

    Treating it as absent would report a confident empty surface for a document
    that declared one — and at the gate an empty surface reads as disjoint.
    """
    body = f'# PLAN-122\n\n{heading}\n\n- Adds `test/iota/test_a.py`\n'

    claim = claim_for(plans, repo, 'PLAN-122.md', body)

    assert paths(claim.claimed) == {'test/iota/test_a.py'}


def test_a_near_miss_heading_is_not_the_addressed_section(repo: Path, plans: Path) -> None:
    """Case-blindness is not word-blindness — the matched negative control.

    A DIFFERENT heading text must still fail to open the section, or the
    case-insensitive widening went too far.
    """
    body = '# PLAN-125\n\n## Expected Surfaces\n\n- Adds `test/iota/test_a.py`\n'
    path = plans / 'PLAN-125.md'
    path.write_text(body, encoding='utf-8')

    with pytest.raises(spec_parser.UnclassifiableSpecError):
        spec_parser.classify_spec(path, repo)


def test_section_body_stops_at_the_next_heading(repo: Path, plans: Path) -> None:
    body = (
        '# PLAN-123\n\n## Expected Surface\n\n'
        '- Adds `test/kappa/test_a.py`\n\n'
        '## Notes\n\n'
        '- Mentions `test/outside/test_b.py`\n'
    )

    claim = claim_for(plans, repo, 'PLAN-123.md', body)

    assert paths(claim.claimed) == {'test/kappa/test_a.py'}


# --- plan-id notation --------------------------------------------------------


@pytest.mark.parametrize(
    ('name', 'expected'),
    [
        ('PLAN-140.md', 'PLAN-140'),
        ('PLAN-9.md', 'PLAN-9'),
        ('PLAN-01-alpha.md', 'PLAN-01'),
        ('PLAN-TRUTH-098-foo.md', 'PLAN-TRUTH-098'),
        ('CIS-060-verdict-field.md', 'CIS-060'),
        ('README.md', 'README.md'),
        ('notes-1.md', 'notes-1.md'),
    ],
    ids=[
        'numbered',
        'single_digit',
        'numbered_with_slug',
        'code_slug',
        'bare_code_slug',
        'not_a_spec',
        'lowercase_is_not_a_code_slug',
    ],
)
def test_plan_id_is_read_from_the_spec_filename(name: str, expected: str) -> None:
    """All three settled forms resolve from ONE definition, with a bare fallback.

    ``PLAN-TRUTH-098-foo.md`` is the case the retired ``^(PLAN-[0-9]+)`` pattern
    got wrong: it matched nothing, so the whole filename became the plan id and
    every code-slug spec grouped under a key of its own — silently breaking
    cross-plan grouping for that half of the corpus.
    """
    assert spec_parser.plan_id_of(name) == expected


def test_the_plan_id_segment_is_the_single_definition_of_the_form() -> None:
    """The published binding is what ``plan_id_of`` is built over.

    ``_orchestrator_inbox._SOURCE_ID_RE`` composes its pointer grammar from this
    same constant, so a drift between the two is what this pins.
    """
    assert 'PLAN-' in spec_parser.PLAN_ID_SEGMENT
    assert spec_parser._PLAN_ID_RE.pattern == f'^({spec_parser.PLAN_ID_SEGMENT})'

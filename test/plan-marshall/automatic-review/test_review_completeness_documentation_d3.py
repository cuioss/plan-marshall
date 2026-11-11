#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-144 D3 — the review-completeness documents say what the code does.

Three statements drifted from the code and are pinned here against the real
document text:

* an in-place edit is NOT a participation credit and NOT a precondition of one
  (the currency test is a pure SHA comparison);
* Branch 0 of the rate-limit recovery names every unproven REQUIRED bot, not
  only the bot that refused;
* the ``refusal_structural`` envelope's ``display_detail`` template and its field
  contract both list ``unproven_bots``.

Each check reads the shipped document, so a later edit that reintroduces the
stale claim turns this module red.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import get_skill_dir

_SKILLS = get_skill_dir('plan-marshall', 'automatic-review')
_CONTRACT = _SKILLS / 'standards' / 'bot-participation-contract.md'
_SKILL_MD = _SKILLS / 'SKILL.md'
_GITHUB_PR = get_skill_dir('plan-marshall', 'workflow-integration-github') / 'scripts' / 'github_pr.py'

_HEADING = re.compile(r'^(#{1,6})\s+(.*)$')


def _text(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def _section(text: str, title: str) -> str:
    """Return the body of the first heading starting with ``title``."""
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith('```'):
            in_fence = not in_fence
        heading = None if in_fence else _HEADING.match(line)
        if level == 0:
            if heading and heading.group(2).startswith(title):
                level = len(heading.group(1))
            continue
        if heading and len(heading.group(1)) <= level:
            break
        body.append(line)
    assert body, f'no section starts with {title!r}'
    return '\n'.join(body)


def _structural_envelope_block(text: str) -> str:
    """The ````toon`` block that carries the ``refusal_structural`` envelope."""
    match = re.search(
        r'```toon\n(?P<block>(?:(?!```).)*reason: refusal_structural(?:(?!```).)*)```',
        text,
        re.DOTALL,
    )
    assert match is not None, 'no toon block declares the refusal_structural envelope'
    return match.group('block')


# --- an edit is never a credit, nor a precondition of one ---------------------------------


def test_the_contract_never_makes_an_edit_a_credit() -> None:
    """The two stale sentences argued from an edit; the code is a pure SHA comparison."""
    contract = ' '.join(_text(_CONTRACT).split())

    assert 'an edit proves a fresh review' not in contract
    assert 'unedited, fails the test' not in contract
    assert 'an edit credits nothing' in contract
    assert 'An in-place edit alone never credits' in contract


def test_the_currency_code_comment_does_not_measure_an_edit() -> None:
    """The staged-ledger comment names the SHA comparison, not a fresh-edit measurement."""
    source = _text(_GITHUB_PR)

    assert 'measures a fresh' not in source
    assert 'never a credit test' in source


# --- Branch 0 names every unproven required bot -------------------------------------------


def test_branch_0_names_every_unproven_required_bot() -> None:
    branch_zero = _section(_text(_SKILL_MD), 'Branch 0 —')

    assert 'unproven_bots' in branch_zero
    assert 'guard_unproven_bots' in branch_zero


# --- the structural envelope lists unproven_bots in BOTH template and contract -------------


def test_the_structural_display_detail_template_names_unproven_bots() -> None:
    block = _structural_envelope_block(_text(_SKILL_MD))
    display_lines = [line for line in block.splitlines() if line.strip().startswith('display_detail:')]

    assert display_lines, block
    assert any('{unproven_bots}' in line for line in display_lines), display_lines


def test_the_structural_field_contract_lists_unproven_bots() -> None:
    text = _text(_SKILL_MD)
    start = text.index('Field contract:')
    contract = text[start:]

    assert '- `unproven_bots[]`' in contract

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""A forked finalize subagent must not run ``default:branch-cleanup``.

``standards/dispatch-inline-split.md`` carries a section explaining why the
finalize pipeline that reaches ``default:branch-cleanup`` runs in the main
context and never inside a forked subagent: the fork inherits a cwd pinned inside
the worktree, cannot re-anchor it, and ``worktree-remove`` then refuses with a
typed error that ``--force`` does not override.

The section's load-bearing claim is the refusal TOKEN it names. Prose that names
a token the script no longer emits reads as authoritative and is wrong, so the
token is never restated here: it is DERIVED from ``git-workflow.py``'s own
``cmd_worktree_remove`` source — the ``error`` value of the refusal dict returned
under the cwd-containment guard (an ``is_relative_to`` test) — and the document
must name exactly that token.

Pinned here:

(1) the forked-subagent section exists and names ``default:branch-cleanup``;
(2) the ``error:`` token it names is the one the script's cwd-containment
    refusal actually returns, and both the section and the refusal state that
    ``--force`` does not override it;
(3) ``default:branch-cleanup`` stays under ``## Inline steps`` and out of
    ``## Dispatched steps``;
(4) the section's cross-reference to ``branch-cleanup.md`` § "Worktree
    Awareness" resolves to a heading that exists.

The token extractor is pure over source text, so its mutation guards drive it
with synthetic functions: it must pick the containment refusal rather than the
sibling move-back refusal, and it must fail loudly — never return nothing — when
the containment guard is absent.
"""

from __future__ import annotations

import ast
import re

import pytest
from _dispatch_roster import parse_roster, section_lines
from conftest import MARKETPLACE_ROOT

_FINALIZE_STANDARDS = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'standards'
_ROSTER_DOC = _FINALIZE_STANDARDS / 'dispatch-inline-split.md'
_BRANCH_CLEANUP_DOC = _FINALIZE_STANDARDS / 'branch-cleanup.md'
_GIT_WORKFLOW_SCRIPT = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'workflow-integration-git' / 'scripts' / 'git-workflow.py'
)

_STEP_KEY = 'default:branch-cleanup'
_FORKED_SECTION_HEADING = f'## A forked subagent must not run `{_STEP_KEY}`'
_DISPATCHED_HEADING = '## Dispatched steps'
_INLINE_HEADING = '## Inline steps'
_WORKTREE_AWARENESS_HEADING = '## Worktree Awareness'

#: The removal verb whose refusal the section documents.
_REMOVAL_FUNCTION = 'cmd_worktree_remove'

#: The containment predicate that identifies the cwd guard inside the removal
#: verb. Matched as the called attribute name, so the extractor keys on the
#: guard's SHAPE rather than on the token it is supposed to discover.
_CONTAINMENT_ATTR = 'is_relative_to'

#: A backticked ``error: <token>`` claim in the document prose.
_DOCUMENTED_ERROR = re.compile(r'`error: ([a-z0-9_]+)`')


def _forked_section() -> str:
    """Return the forked-subagent section body, failing loudly if it is absent."""
    lines = section_lines(_ROSTER_DOC.read_text(encoding='utf-8'), _FORKED_SECTION_HEADING)
    body = '\n'.join(lines)
    assert body.strip(), (
        f'{_ROSTER_DOC.name} § {_FORKED_SECTION_HEADING!r} parsed empty — every assertion below would be vacuous.'
    )
    return body


def _containment_guard_ifs(function: ast.FunctionDef) -> list[ast.If]:
    """Every ``if`` in ``function`` whose test calls the containment predicate."""
    guards: list[ast.If] = []
    for node in ast.walk(function):
        if not isinstance(node, ast.If):
            continue
        for call in ast.walk(node.test):
            if (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == _CONTAINMENT_ATTR
            ):
                guards.append(node)
                break
    return guards


def _refusal_dicts(guard: ast.If) -> list[ast.Dict]:
    """Every dict literal in the guard's body that carries an ``error`` key."""
    found: list[ast.Dict] = []
    for statement in guard.body:
        for node in ast.walk(statement):
            if not isinstance(node, ast.Dict):
                continue
            keys = [key.value for key in node.keys if isinstance(key, ast.Constant)]
            if 'error' in keys:
                found.append(node)
    return found


def _dict_str_value(node: ast.Dict, key_name: str) -> str | None:
    """Return the string constant stored under ``key_name`` in a dict literal."""
    for key, value in zip(node.keys, node.values, strict=True):
        if (
            isinstance(key, ast.Constant)
            and key.value == key_name
            and isinstance(value, ast.Constant)
            and isinstance(value.value, str)
        ):
            return value.value
    return None


def _dict_message_text(node: ast.Dict) -> str:
    """Concatenate every string constant under the dict's ``message`` key."""
    for key, value in zip(node.keys, node.values, strict=True):
        if isinstance(key, ast.Constant) and key.value == 'message':
            return ''.join(
                part.value for part in ast.walk(value) if isinstance(part, ast.Constant) and isinstance(part.value, str)
            )
    return ''


def _containment_refusal(source: str) -> ast.Dict:
    """Return the refusal dict the removal verb returns under its cwd-containment guard.

    Pure over ``source`` so the mutation guards can drive it with synthetic
    functions. Fails loudly when the function, the guard, or a single refusal
    under it cannot be found — an empty result would make every downstream
    comparison vacuous.
    """
    tree = ast.parse(source)
    functions = [
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == _REMOVAL_FUNCTION
    ]
    assert len(functions) == 1, f'expected exactly one {_REMOVAL_FUNCTION}() definition, found {len(functions)}'
    guards = _containment_guard_ifs(functions[0])
    assert guards, (
        f'{_REMOVAL_FUNCTION}() carries no `if ...{_CONTAINMENT_ATTR}(...)` guard — the cwd-containment '
        'refusal the forked-subagent section documents could not be located'
    )
    refusals = [refusal for guard in guards for refusal in _refusal_dicts(guard)]
    assert len(refusals) == 1, (
        f'expected exactly one error-bearing refusal under the containment guard in '
        f'{_REMOVAL_FUNCTION}(), found {len(refusals)}'
    )
    return refusals[0]


def _containment_refusal_token(source: str) -> str:
    """Return the ``error`` token of the containment refusal, failing loudly if absent."""
    token = _dict_str_value(_containment_refusal(source), 'error')
    assert token, f'the containment refusal in {_REMOVAL_FUNCTION}() carries no string `error` value'
    return token


def test_forked_section_names_branch_cleanup():
    section = _forked_section()

    assert f'`{_STEP_KEY}`' in section, (
        f'the forked-subagent section must name `{_STEP_KEY}` in its body, not only in its heading'
    )
    assert '{main_checkout}' in section, (
        'the section must name the main-checkout cwd the main context can return to before removal'
    )


def test_documented_refusal_token_is_the_one_worktree_remove_emits():
    source_token = _containment_refusal_token(_GIT_WORKFLOW_SCRIPT.read_text(encoding='utf-8'))
    documented = set(_DOCUMENTED_ERROR.findall(_forked_section()))

    assert documented == {source_token}, (
        f'the forked-subagent section names error token(s) {sorted(documented)}, but '
        f'{_GIT_WORKFLOW_SCRIPT.name}::{_REMOVAL_FUNCTION}() returns {source_token!r} under its '
        'cwd-containment guard — the documented refusal must be the one the script emits'
    )


def test_force_does_not_override_the_documented_refusal():
    refusal = _containment_refusal(_GIT_WORKFLOW_SCRIPT.read_text(encoding='utf-8'))

    assert '--force' in _dict_message_text(refusal), (
        'the containment refusal message no longer states its --force behaviour, so the '
        "section's claim that --force does not override it is unanchored"
    )
    assert '`--force`' in _forked_section(), 'the section must state that `--force` does not lift the refusal'


def test_branch_cleanup_stays_in_the_inline_roster():
    text = _ROSTER_DOC.read_text(encoding='utf-8')

    inline = parse_roster(text, _INLINE_HEADING)
    dispatched = parse_roster(text, _DISPATCHED_HEADING)

    assert inline, 'the inline roster parsed empty — the membership check below would be vacuous'
    assert _STEP_KEY in inline, f'{_STEP_KEY} must stay under {_INLINE_HEADING!r}; it runs in the main context'
    assert _STEP_KEY not in dispatched, f'{_STEP_KEY} must never be classified dispatched'


def test_worktree_awareness_cross_reference_resolves():
    section = _forked_section()
    branch_cleanup_text = _BRANCH_CLEANUP_DOC.read_text(encoding='utf-8')

    assert '](branch-cleanup.md)' in section, 'the section must link branch-cleanup.md for the refusal contract'
    assert '§ "Worktree Awareness"' in section, 'the section must point at the Worktree Awareness section'
    assert _WORKTREE_AWARENESS_HEADING in branch_cleanup_text.splitlines(), (
        f'{_BRANCH_CLEANUP_DOC.name} no longer carries {_WORKTREE_AWARENESS_HEADING!r} — the cross-reference is stale'
    )


# ---------------------------------------------------------------------------
# Mutation guards for the token extractor
# ---------------------------------------------------------------------------

_SYNTHETIC_TWO_REFUSALS = """
def cmd_worktree_remove(args):
    if not moved_back(args.plan_id):
        return {'status': 'error', 'error': 'sibling_move_back_refusal'}
    cwd = current().resolve()
    if cwd.is_relative_to(target):
        return {'status': 'error', 'error': 'synthetic_containment_refusal', 'message': 'not overridable by --force'}
    return {'status': 'success'}
"""

_SYNTHETIC_NO_CONTAINMENT_GUARD = """
def cmd_worktree_remove(args):
    if not moved_back(args.plan_id):
        return {'status': 'error', 'error': 'sibling_move_back_refusal'}
    return {'status': 'success'}
"""


def test_extractor_picks_the_containment_refusal_not_its_sibling():
    token = _containment_refusal_token(_SYNTHETIC_TWO_REFUSALS)

    assert token == 'synthetic_containment_refusal', (
        f'the extractor returned {token!r}; it must key on the containment guard, not on the first '
        'error-bearing dict in the function'
    )


def test_extractor_fails_loudly_when_the_containment_guard_is_absent():
    # A silent result here would let the document name any token unchallenged.
    with pytest.raises(AssertionError, match=_CONTAINMENT_ATTR):
        _containment_refusal_token(_SYNTHETIC_NO_CONTAINMENT_GUARD)

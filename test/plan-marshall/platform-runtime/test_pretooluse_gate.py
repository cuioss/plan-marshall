#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for pretooluse_gate.py — the shared PreToolUse gate module.

pretooluse_gate is a pure-function library shipped as a sibling module of the
platform-runtime scripts. It is bound directly (not run as a subprocess) through
the shared ``conftest.load_script_module`` loader.

Coverage:
  - parse() returns {} on empty / malformed / non-object input and never raises.
  - Each accessor (sub_agent_identity, cwd, tool_name, tool_input) returns the
    field value when present and a safe default when absent.
  - context_gate() is true on a Signal-1-only payload, true on a Signal-2-only
    payload, true when both fire, and false (fail-open) when neither fires.
  - An absent Signal-1 field falls back to Signal 2 alone.
"""

from __future__ import annotations

import os
from typing import Any

# PLAIN import, deliberately: the ``Any``-typed parameters below only stay honest
# when mypy sees the real module — the shared loader returns ``Any``, which would
# make the suite's deliberate wrong-type probes untyped.
import pretooluse_gate as gate
import pytest

# =============================================================================
# Helpers
# =============================================================================


def _worktree_cwd() -> str:
    """A cwd resolving under the plan-worktree path segment (Signal 2)."""
    return os.path.join(
        '/home/dev/project',
        gate.WORKTREE_PATH_SEGMENT,
        'my-plan',
    )


def _signal1_payload() -> dict:
    """Payload where only Signal 1 fires (execution-context sub-agent identity).

    Uses the real bundle-qualified ``agent_type`` value observed in live
    PreToolUse payloads (D2 capture) — NOT a bare ``execution-context-*``.
    """
    return {gate.SUB_AGENT_IDENTITY_FIELD: 'plan-marshall:execution-context-level-3'}


def _signal2_payload() -> dict:
    """Payload where only Signal 2 fires (cwd under a plan worktree)."""
    return {gate.CWD_FIELD: _worktree_cwd()}


# =============================================================================
# parse()
# =============================================================================

#: ``(raw stdin bytes, the payload they parse to)``. Only the first row is a hook
#: payload; every other row is a way of not being one, and all of them degrade to
#: an empty dict so the accessors below always have something to index. The rows
#: walk outward from the closest miss to the furthest: nothing at all, only
#: whitespace, bytes that are not JSON, JSON that is not an object (a list, a
#: string and a number, because each decodes to a different Python type), and
#: finally an argument that is not a string at all — a defensive shape the type
#: annotation forbids but the hook boundary cannot.
_PARSE_CASES: list[tuple[Any, dict[str, Any]]] = [
    ('{"tool_name": "Bash"}', {'tool_name': 'Bash'}),
    ('', {}),
    ('   \n\t ', {}),
    ('{not valid json', {}),
    ('[1, 2, 3]', {}),
    ('"a string"', {}),
    ('42', {}),
    (None, {}),
    (123, {}),
]

_PARSE_IDS = [
    'a-well-formed-object',
    'nothing-piped',
    'whitespace-only',
    'malformed-json',
    'json-list',
    'json-string',
    'json-number',
    'a-none-argument',
    'an-integer-argument',
]

#: Raw inputs the parse must survive without raising. These are not about the
#: RESULT — the rows above pin that — but about the parse being total: a hook
#: that raised on a truncated payload would break the tool call it only watches.
_NEVER_RAISES = ['', 'null', '{', '}{', '\x00', '{"a":}', '[', 'true']

_NEVER_RAISES_IDS = [
    'empty',
    'json-null',
    'unclosed-brace',
    'reversed-braces',
    'a-nul-byte',
    'a-key-with-no-value',
    'unclosed-bracket',
    'json-true',
]


@pytest.mark.parametrize(('raw', 'expected'), _PARSE_CASES, ids=_PARSE_IDS)
def test_parse_yields_the_payload_or_an_empty_dict(raw: Any, expected: dict) -> None:
    """A hook payload parses; anything else degrades to an empty dict."""
    assert gate.parse(raw) == expected


@pytest.mark.parametrize('raw', _NEVER_RAISES, ids=_NEVER_RAISES_IDS)
def test_parse_never_raises_on_arbitrary_input(raw: str) -> None:
    """The parse is total — every input yields a dict rather than an exception."""
    assert isinstance(gate.parse(raw), dict)


# =============================================================================
# sub_agent_identity()
# =============================================================================

#: ``(payload, the identity read from it)``. The field has a primary spelling and
#: a fallback one, and both must be read — a payload carrying only the fallback
#: is the shape the harness actually sends on some events. The ``None`` rows are
#: the three ways there is no identity: the field is absent, it is present but
#: empty, or the payload is not a mapping at all.
_SUB_AGENT_IDENTITY_CASES: list[tuple[Any, str | None]] = [
    ({gate.SUB_AGENT_IDENTITY_FIELD: 'execution-context-level-1'}, 'execution-context-level-1'),
    ({gate.SUB_AGENT_IDENTITY_FALLBACK_FIELDS[0]: 'execution-context-level-2'}, 'execution-context-level-2'),
    ({'unrelated': 'x'}, None),
    ({gate.SUB_AGENT_IDENTITY_FIELD: ''}, None),
    (None, None),
    ('not a dict', None),
]

_SUB_AGENT_IDENTITY_IDS = [
    'the-primary-field',
    'the-fallback-field',
    'no-identity-field-at-all',
    'an-empty-identity-value',
    'a-payload-that-is-none',
    'a-payload-that-is-a-string',
]


@pytest.mark.parametrize(('payload', 'expected'), _SUB_AGENT_IDENTITY_CASES, ids=_SUB_AGENT_IDENTITY_IDS)
def test_sub_agent_identity_reads_the_field_or_reports_none(payload: Any, expected: str | None) -> None:
    """The identity is read from either spelling, or reported absent."""
    assert gate.sub_agent_identity(payload) == expected


# =============================================================================
# cwd()
# =============================================================================

#: ``(payload, the cwd read from it)``. Same three absence shapes as the identity
#: accessor above — absent, empty, and a payload that is not a mapping — because
#: every accessor in this module has to survive the same malformed input.
_CWD_CASES: list[tuple[Any, str | None]] = [
    ({gate.CWD_FIELD: '/home/dev/project'}, '/home/dev/project'),
    ({'unrelated': 'x'}, None),
    ({gate.CWD_FIELD: ''}, None),
    (None, None),
]

_CWD_IDS = [
    'the-cwd-field',
    'no-cwd-field-at-all',
    'an-empty-cwd-value',
    'a-payload-that-is-none',
]


@pytest.mark.parametrize(('payload', 'expected'), _CWD_CASES, ids=_CWD_IDS)
def test_cwd_reads_the_field_or_reports_none(payload: Any, expected: str | None) -> None:
    """The cwd is read when present, and reported absent otherwise."""
    assert gate.cwd(payload) == expected


# =============================================================================
# tool_name()
# =============================================================================

#: ``(payload, the tool name read from it)``.
_TOOL_NAME_CASES: list[tuple[Any, str | None]] = [
    ({gate.TOOL_NAME_FIELD: 'Bash'}, 'Bash'),
    ({'unrelated': 'x'}, None),
    (None, None),
]

_TOOL_NAME_IDS = [
    'the-tool-name-field',
    'no-tool-name-field-at-all',
    'a-payload-that-is-none',
]


@pytest.mark.parametrize(('payload', 'expected'), _TOOL_NAME_CASES, ids=_TOOL_NAME_IDS)
def test_tool_name_reads_the_field_or_reports_none(payload: Any, expected: str | None) -> None:
    """The tool name is read when present, and reported absent otherwise."""
    assert gate.tool_name(payload) == expected


# =============================================================================
# tool_input()
# =============================================================================

#: ``(payload, the tool input read from it)``. This accessor differs from the
#: three above in what it returns when there is nothing to read: an empty DICT
#: rather than ``None``, so a caller can index it without a guard. The last three
#: rows are the shapes that must still yield that empty dict — a non-mapping
#: value, an explicit null, and a payload that is not a mapping at all.
_TOOL_INPUT_CASES: list[tuple[Any, dict[str, Any]]] = [
    ({gate.TOOL_INPUT_FIELD: {'command': 'ls -la'}}, {'command': 'ls -la'}),
    ({'unrelated': 'x'}, {}),
    ({gate.TOOL_INPUT_FIELD: 'a string'}, {}),
    ({gate.TOOL_INPUT_FIELD: None}, {}),
    (None, {}),
]

_TOOL_INPUT_IDS = [
    'the-tool-input-field',
    'no-tool-input-field-at-all',
    'a-non-mapping-tool-input-value',
    'an-explicitly-null-tool-input',
    'a-payload-that-is-none',
]


@pytest.mark.parametrize(('payload', 'expected'), _TOOL_INPUT_CASES, ids=_TOOL_INPUT_IDS)
def test_tool_input_reads_the_field_or_yields_an_empty_dict(payload: Any, expected: dict) -> None:
    """The tool input is read when usable, and yields an indexable empty dict otherwise."""
    assert gate.tool_input(payload) == expected


# =============================================================================
# context_gate() — Signal1 OR Signal2, fail-open
# =============================================================================

#: ``(payload, whether the gate is satisfied)``. The gate is Signal 1 OR Signal 2
#: and fails OPEN, so the rows come in two families and every ``False`` row is a
#: near miss rather than an obviously wrong input.
#:
#: Signal 1 is the sub-agent identity, and it must carry the execution-context
#: marker: the bundle-qualified value is what live payloads actually contain (an
#: earlier ``startswith("execution-context")`` prefix match failed to gate EVERY
#: real sub-agent call whose cwd was not a worktree), the reader variant carries
#: the same marker, and an unrelated agent type does not fire it at all.
#:
#: Signal 2 is a cwd under the worktree segment, matched at a DIRECTORY boundary:
#: a path that merely contains the segment as a substring must not fire, while a
#: path that ends exactly at the segment must. The last row is the fail-open
#: case, where an ordinary main-checkout call satisfies neither signal.
_CONTEXT_GATE_CASES: list[tuple[Any, bool]] = [
    (_signal1_payload(), True),
    ({gate.SUB_AGENT_IDENTITY_FIELD: 'plan-marshall:execution-context-level-4'}, True),
    ({gate.SUB_AGENT_IDENTITY_FIELD: 'plan-marshall:execution-context-reader-level-2'}, True),
    ({gate.SUB_AGENT_IDENTITY_FIELD: 'phase-5-execute'}, False),
    (_signal2_payload(), True),
    ({gate.CWD_FIELD: f'/home/dev/project/{gate.WORKTREE_PATH_SEGMENT}/my-plan/subdir'}, True),
    ({gate.CWD_FIELD: f'/home/dev/project/{gate.WORKTREE_PATH_SEGMENT}'}, True),
    ({gate.CWD_FIELD: f'/tmp/fake-{gate.WORKTREE_PATH_SEGMENT}-extra/plans'}, False),
    ({**_signal1_payload(), **_signal2_payload()}, True),
    (
        {
            gate.SUB_AGENT_IDENTITY_FIELD: 'some-other-agent',
            gate.CWD_FIELD: '/home/dev/project',
        },
        False,
    ),
    ({}, False),
    (None, False),
]

_CONTEXT_GATE_IDS = [
    'a-bundle-qualified-level-3-identity',
    'a-bundle-qualified-level-4-identity',
    'a-bundle-qualified-reader-variant-identity',
    'an-agent-type-without-the-marker',
    'a-cwd-one-level-below-the-segment',
    'a-cwd-two-levels-below-the-segment',
    'a-cwd-ending-at-the-segment',
    'the-segment-as-a-substring-only',
    'both-signals-firing',
    'neither-signal-firing',
    'an-empty-payload',
    'a-payload-that-is-none',
]


@pytest.mark.parametrize(('payload', 'gated'), _CONTEXT_GATE_CASES, ids=_CONTEXT_GATE_IDS)
def test_context_gate_is_satisfied_by_either_signal(payload: Any, gated: bool) -> None:
    """Either signal opens the gate; neither leaves it fail-open."""
    assert gate.context_gate(payload) is gated


def test_context_gate_absent_signal1_falls_back_to_signal2() -> None:
    """Signal 2 stands alone when there is no identity field at all.

    The identity is asserted absent first: without that, the row would also pass
    on a payload whose identity happened to fire Signal 1 as well, and the
    fallback would be untested.
    """
    payload = {gate.CWD_FIELD: _worktree_cwd()}

    assert gate.sub_agent_identity(payload) is None
    assert gate.context_gate(payload) is True


# =============================================================================
# No rule-matcher logic present (enforcement stays in D3)
# =============================================================================


def test_module_exposes_no_rule_matchers() -> None:
    # The shared gate owns parse + accessors + context_gate only; the R1-R4 rule
    # matchers are enforcement-only and must not leak into this module.
    public_names = {name for name in dir(gate) if not name.startswith('_')}
    forbidden = {'match_rules', 'rule_matchers', 'deny', 'permission_decision'}
    assert forbidden.isdisjoint(public_names)

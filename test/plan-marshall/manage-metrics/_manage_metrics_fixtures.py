#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared fixtures for the ``manage-metrics`` test modules.

Every builder here produces its namespace by running ``manage-metrics.py``'s OWN
parser through :func:`conftest.parse_ns`, so the namespace carries each default
the production CLI would apply. A hand-built ``Namespace`` carries only the
attributes its author listed, which lets a test pass against a namespace the real
CLI could never produce — and lets a newly-added flag with a default break
production while breaking nothing in the suite.

Builders take keyword arguments and translate them to the command line; an
argument left at ``None`` is omitted from the command line entirely, so the
parser applies its own default rather than the test asserting one.

The optional usage arguments are keyword-only. The per-module builders these
replace did not agree on their order — ``duration_ms`` and ``tool_uses`` were
transposed between two of them — so a positional call would have carried the
right value into the wrong field. Keyword-only makes that a ``TypeError``.
"""

from argparse import Namespace

from conftest import get_script_path, parse_ns

BUNDLE = 'plan-marshall'
SKILL = 'manage-metrics'
SCRIPT = 'manage-metrics.py'


def ns(*argv: str) -> Namespace:
    """Return the namespace ``manage-metrics.py``'s parser produces for ``argv``."""
    parsed: Namespace = parse_ns(BUNDLE, SKILL, SCRIPT, *argv)
    return parsed


def _opt(flag: str, value: object) -> list[str]:
    """Render an optional flag, or nothing at all when its value is ``None``."""
    return [] if value is None else [flag, str(value)]


def _usage_flags(
    total_tokens: int | None,
    tool_uses: int | None,
    duration_ms: int | None,
    retrospective_tokens: int | None,
) -> list[str]:
    """The four usage flags shared by end-phase, phase-boundary and accumulate."""
    return (
        _opt('--total-tokens', total_tokens)
        + _opt('--tool-uses', tool_uses)
        + _opt('--duration-ms', duration_ms)
        + _opt('--retrospective-tokens', retrospective_tokens)
    )


def ns_start_phase(plan_id: str, phase: str) -> Namespace:
    """``start-phase`` — record a phase start timestamp."""
    return ns('start-phase', '--plan-id', plan_id, '--phase', phase)


def ns_end_phase(
    plan_id: str,
    phase: str,
    *,
    total_tokens: int | None = None,
    duration_ms: int | None = None,
    tool_uses: int | None = None,
    retrospective_tokens: int | None = None,
) -> Namespace:
    """``end-phase`` — close a phase, optionally carrying the agent's usage figures."""
    return ns(
        'end-phase', '--plan-id', plan_id, '--phase', phase,
        *_usage_flags(total_tokens, tool_uses, duration_ms, retrospective_tokens),
    )


def ns_generate(plan_id: str) -> Namespace:
    """``generate`` — render ``metrics.md`` from the collected data."""
    return ns('generate', '--plan-id', plan_id)


def ns_enrich(plan_id: str, session_id: str) -> Namespace:
    """``enrich`` — enrich a plan's metrics from a JSONL transcript."""
    return ns('enrich', '--plan-id', plan_id, '--session-id', session_id)


def ns_accumulate(
    plan_id: str,
    phase: str,
    *,
    total_tokens: int | None = None,
    tool_uses: int | None = None,
    duration_ms: int | None = None,
    retrospective_tokens: int | None = None,
) -> Namespace:
    """``accumulate-agent-usage`` — add a subagent's usage to the running total."""
    return ns(
        'accumulate-agent-usage', '--plan-id', plan_id, '--phase', phase,
        *_usage_flags(total_tokens, tool_uses, duration_ms, retrospective_tokens),
    )


def ns_phase_boundary(
    plan_id: str,
    prev_phase: str,
    next_phase: str,
    *,
    total_tokens: int | None = None,
    tool_uses: int | None = None,
    duration_ms: int | None = None,
    retrospective_tokens: int | None = None,
) -> Namespace:
    """``phase-boundary`` — close one phase and enter the next in a single call."""
    return ns(
        'phase-boundary', '--plan-id', plan_id,
        '--prev-phase', prev_phase, '--next-phase', next_phase,
        *_usage_flags(total_tokens, tool_uses, duration_ms, retrospective_tokens),
    )


def ns_boundary_status(
    plan_id: str, next_phase: str, *, prev_phase: str | None = None
) -> Namespace:
    """``boundary-status`` — report the boundary state when resuming into a phase."""
    return ns(
        'boundary-status', '--plan-id', plan_id, '--next-phase', next_phase,
        *_opt('--prev-phase', prev_phase),
    )


def ns_record_dispatch_boundary(
    plan_id: str,
    phase: str,
    termination_cause: str,
    *,
    total_tokens: int | None = None,
    tool_uses: int | None = None,
    duration_ms: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cache_read_input_tokens: int | None = None,
    cache_creation_input_tokens: int | None = None,
) -> Namespace:
    """``record-dispatch-boundary`` — record one dispatch's termination and usage.

    The four per-dispatch context-load fields default to ``None`` so a call site
    that omits them exercises the UNMEASURED path ``cmd_record_dispatch_boundary``
    applies for a missing flag — the column carries the ``unmeasured`` literal,
    never a ``0``.
    """
    return ns(
        'record-dispatch-boundary', '--plan-id', plan_id, '--phase', phase,
        '--termination-cause', termination_cause,
        *_opt('--total-tokens', total_tokens),
        *_opt('--tool-uses', tool_uses),
        *_opt('--duration-ms', duration_ms),
        *_opt('--input-tokens', input_tokens),
        *_opt('--output-tokens', output_tokens),
        *_opt('--cache-read-input-tokens', cache_read_input_tokens),
        *_opt('--cache-creation-input-tokens', cache_creation_input_tokens),
    )


def ns_print_phase_breakdown(plan_id: str, output_file: str | None = None) -> Namespace:
    """``print-phase-breakdown`` — render the per-phase breakdown table."""
    return ns(
        'print-phase-breakdown', '--plan-id', plan_id,
        *_opt('--output-file', output_file),
    )


def raw_ns(command: str, **fields: object) -> Namespace:
    """Build a namespace WITHOUT the parser — for handler-level rejection tests only.

    The parser rejects an out-of-vocabulary ``--phase`` or ``--termination-cause``
    with ``SystemExit`` before any handler runs, so a namespace built through
    :func:`ns` cannot reach the handler's own validation of such a value. The
    ``cmd_*`` handlers are also callable programmatically, where no parser stands
    in front of them, so that validation is a real contract and needs a test.

    This is the ONLY sanctioned hand-built namespace in this directory. Use it
    solely to assert that a handler rejects a value its parser would also reject;
    every other call site builds its namespace from the real parser.
    """
    return Namespace(command=command, **fields)


SCRIPT_PATH = get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')

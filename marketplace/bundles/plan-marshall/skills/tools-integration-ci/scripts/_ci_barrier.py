#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Provider-agnostic concurrent finalize-wait barrier coordinator.

The phase-6 finalize wait region polls three DISTINCT signals — CI checks,
review-bot comments, and the Sonar compute-engine — off ONE settled HEAD,
concurrently, proceeding per-signal as each reaches a terminal state. Each
signal's underlying WAIT reuses its own existing ratchet (the CI arm reuses
the p50-seeded ``ci wait`` terminal-state watch in ``_github_ci.py``); this
module owns only the provider-agnostic COORDINATION over those independent
waits:

* **per-signal-proceed** — report which signals have settled at the settled
  HEAD so the orchestrator can proceed past each independently, and which are
  still pending so it keeps awaiting them. Wall time approaches ``max(signal)``
  rather than ``sum(signal)`` because the arms are awaited concurrently, not in
  series.
* **bounded re-settle** — when a finding posted after barrier entry is fixed
  and pushed, HEAD advances past the settled HEAD. The AFFECTED signals (those
  last observed against the now-stale HEAD) must be re-entered against the new
  settled HEAD ONLY — never a full finalize replay. The common case converges
  in <=1-2 iterations: a re-settle re-enters only the barrier signals, and a
  clean re-entry (no new finding) settles them all at the new HEAD.

The coordinator enforces the **complete three-arm contract**: a call must
supply signals for EXACTLY ``{ci, review, sonar}`` — no fewer (a caller that
forgot an arm), no more (an unexpected/mistyped name), and no duplicate (which
would silently mask a missing arm behind a repeated one). Without this check,
an incomplete signal set could report a false ``complete``/``re_settle``
decision over fewer than the three signals the wait region actually needs
settled. See ``REQUIRED_SIGNAL_NAMES`` / ``IncompleteBarrierSignalsError``.

The coordinator is a pure state machine over ``(name, state, head)`` signal
records; it runs no subprocess and couples to no provider, so the CI router
(``ci.py``) can own it without importing the sonar/review subsystems. See
``phase-6-finalize/SKILL.md`` § "Wait-region" for the barrier narrative that
consumes this verb.
"""

from __future__ import annotations

import argparse

from toon_parser import serialize_toon

#: The three legal per-signal states. ``settled`` and ``failed`` are terminal;
#: ``pending`` means the signal's wait has not yet reached a terminal state.
VALID_SIGNAL_STATES = frozenset({'pending', 'settled', 'failed'})

#: Terminal states — a signal in one of these has finished waiting. A terminal
#: signal observed against a HEAD other than the settled HEAD is a re-settle
#: candidate (a mutation advanced HEAD past where it settled).
_TERMINAL_STATES = frozenset({'settled', 'failed'})

#: The three-arm signal-name contract the phase-6 finalize wait region
#: requires — CI checks, review-bot comments, and the Sonar compute-engine.
#: ``compute_barrier_state`` rejects any signal set whose names are not
#: EXACTLY this set (see ``IncompleteBarrierSignalsError``).
REQUIRED_SIGNAL_NAMES = frozenset({'ci', 'review', 'sonar'})


class IncompleteBarrierSignalsError(ValueError):
    """The signal set does not exactly match ``REQUIRED_SIGNAL_NAMES``.

    A ``ValueError`` subclass, so existing ``pytest.raises(ValueError)``
    callers still match; callers that need to distinguish this from a
    per-signal invalid-state error (e.g. to pick a TOON ``error:`` code)
    catch this subclass specifically, ahead of the general ``ValueError``.
    """


def _check_signal_completeness(signals: list[tuple[str, str, str]]) -> None:
    """Enforce the complete three-arm barrier contract.

    The phase-6 finalize wait region always awaits exactly
    ``REQUIRED_SIGNAL_NAMES`` — never fewer (a caller that forgot one arm),
    never more (an unexpected/mistyped name), and never a duplicate (which
    would silently mask a missing arm behind a repeated one). Without this
    check, an incomplete signal set could report a false ``complete`` or
    ``re_settle`` decision over fewer than the three signals the wait region
    actually needs settled.

    Args:
        signals: the ``(name, state, head)`` records passed to
            ``compute_barrier_state``.

    Raises:
        IncompleteBarrierSignalsError: when the signal names are missing,
            unexpected, or duplicated relative to ``REQUIRED_SIGNAL_NAMES``.
    """
    names = [name for name, _state, _head in signals]
    name_set = set(names)
    missing = sorted(REQUIRED_SIGNAL_NAMES - name_set)
    unexpected = sorted(name_set - REQUIRED_SIGNAL_NAMES)
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if not missing and not unexpected and not duplicates:
        return

    parts = []
    if missing:
        parts.append(f'missing {missing}')
    if unexpected:
        parts.append(f'unexpected {unexpected}')
    if duplicates:
        parts.append(f'duplicated {duplicates}')
    raise IncompleteBarrierSignalsError(
        f'incomplete barrier signals: {"; ".join(parts)} '
        f'(required exactly {sorted(REQUIRED_SIGNAL_NAMES)})'
    )


def compute_barrier_state(
    signals: list[tuple[str, str, str]],
    settled_head: str,
) -> dict:
    """Compute the concurrent-barrier decision from per-signal state.

    Args:
        signals: list of ``(name, state, head)`` records. ``state`` is one of
            ``VALID_SIGNAL_STATES``; ``head`` is the HEAD sha the signal was
            last observed against (empty string when never observed).
        settled_head: the one HEAD sha the barrier polls off.

    Returns:
        A result dict with ``barrier_status`` in
        ``{complete, waiting, failed, re_settle}`` plus the per-bucket signal
        name lists (``proceed`` / ``pending`` / ``failed`` / ``affected``).

    Raises:
        ValueError: when any signal carries a state outside
            ``VALID_SIGNAL_STATES``.
        IncompleteBarrierSignalsError: when the signal names are not EXACTLY
            ``REQUIRED_SIGNAL_NAMES`` — a missing, unexpected, or duplicated
            arm (a ``ValueError`` subclass; checked after per-signal state
            validation so a bad state on a partial signal set still raises
            the more specific state error first).

    Decision precedence (first match wins):

    1. ``re_settle`` — at least one terminal signal was observed against a
       stale HEAD (``head != settled_head``); HEAD advanced past where it
       settled, so the affected signals must be re-entered against the new
       settled HEAD (bounded re-settle, affected signals only).
    2. ``failed`` — no stale signals, but at least one signal terminally
       FAILED against the current settled HEAD (a real failure, not a
       re-settle).
    3. ``waiting`` — no stale/failed signals, but at least one is still
       ``pending`` (its wait has not reached a terminal state).
    4. ``complete`` — every signal settled at the current settled HEAD.
    """
    proceed: list[str] = []
    pending: list[str] = []
    failed: list[str] = []
    affected: list[str] = []

    for name, state, head in signals:
        if state not in VALID_SIGNAL_STATES:
            raise ValueError(
                f'invalid signal state {state!r} for {name!r}: '
                f'expected one of {sorted(VALID_SIGNAL_STATES)}'
            )
        if state in _TERMINAL_STATES and head != settled_head:
            # Observed against a now-stale HEAD — a HEAD advance (bounded
            # re-settle push) superseded this signal; re-enter it against the
            # new settled HEAD. This is the mutation-fixpoint's affected set.
            affected.append(name)
            continue
        if state == 'settled':
            proceed.append(name)
        elif state == 'failed':
            failed.append(name)
        else:  # pending
            pending.append(name)

    # Enforced AFTER per-signal state validation (a bad state on a partial
    # signal set raises the more specific state error above first) but
    # BEFORE the barrier_status decision — an incomplete signal set must
    # never reach a `complete`/`re_settle` verdict over fewer than the three
    # required arms.
    _check_signal_completeness(signals)

    if affected:
        barrier_status = 're_settle'
    elif failed:
        barrier_status = 'failed'
    elif pending:
        barrier_status = 'waiting'
    else:
        barrier_status = 'complete'

    return {
        'status': 'success',
        'operation': 'barrier',
        'barrier_status': barrier_status,
        'settled_head': settled_head,
        'proceed': proceed,
        'pending': pending,
        'failed': failed,
        'affected': affected,
    }


def _parse_signal(raw: str) -> tuple[str, str, str]:
    """Parse a ``NAME:STATE[:HEAD]`` ``--signal`` value into a record tuple.

    A HEAD sha never contains ``:``, so the field split is unambiguous. The
    HEAD field is optional (an unobserved signal carries an empty HEAD); the
    two-field form ``NAME:STATE`` and the trailing-empty form ``NAME:STATE:``
    both yield an empty HEAD.

    Raises:
        ValueError: when the value does not carry a NAME and a STATE.
    """
    parts = raw.split(':')
    if len(parts) == 2:
        name, state = parts
        head = ''
    elif len(parts) == 3:
        name, state, head = parts
    else:
        raise ValueError(
            f'invalid --signal {raw!r}: expected NAME:STATE or NAME:STATE:HEAD'
        )
    if not name:
        raise ValueError(f'invalid --signal {raw!r}: empty signal name')
    return name, state, head


def run_barrier_cli(argv: list[str]) -> int:
    """Entry point for the ``ci barrier`` router verb.

    Parses ``--settled-head`` and one-or-more ``--signal NAME:STATE[:HEAD]``
    flags, computes the barrier decision, and prints it as TOON. Follows the
    three-tier exit model: expected errors (a malformed signal) print a
    ``status: error`` TOON and still return 0.
    """
    parser = argparse.ArgumentParser(
        prog='ci barrier',
        allow_abbrev=False,
        description=(
            'Provider-agnostic concurrent finalize-wait barrier coordinator — '
            'per-signal-proceed + bounded re-settle over {CI, review, sonar}.'
        ),
    )
    parser.add_argument(
        '--settled-head',
        dest='settled_head',
        required=True,
        help='The single HEAD sha the barrier polls off.',
    )
    parser.add_argument(
        '--signal',
        action='append',
        required=True,
        metavar='NAME:STATE:HEAD',
        help='A barrier signal as NAME:STATE[:HEAD], where STATE is one of '
        'pending|settled|failed and HEAD is the sha it was observed against '
        '(omit for an unobserved signal). Repeatable — one per barrier signal.',
    )
    args = parser.parse_args(argv)

    signals: list[tuple[str, str, str]] = []
    for raw in args.signal:
        try:
            signals.append(_parse_signal(raw))
        except ValueError as exc:
            print(
                serialize_toon(
                    {
                        'status': 'error',
                        'operation': 'barrier',
                        'error': 'invalid_signal',
                        'message': str(exc),
                    }
                )
            )
            return 0

    try:
        result = compute_barrier_state(signals, args.settled_head)
    except IncompleteBarrierSignalsError as exc:
        # Caught ahead of the general ValueError below — a subclass, so this
        # branch must come first or the general handler would shadow it.
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'operation': 'barrier',
                    'error': 'incomplete_barrier_signals',
                    'message': str(exc),
                }
            )
        )
        return 0
    except ValueError as exc:
        print(
            serialize_toon(
                {
                    'status': 'error',
                    'operation': 'barrier',
                    'error': 'invalid_signal_state',
                    'message': str(exc),
                }
            )
        )
        return 0

    print(serialize_toon(result))
    return 0

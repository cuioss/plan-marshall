#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Consumer CLI for the ``chat extract-signal`` platform-runtime operation.

Pure consumer for the ``plan-retrospective`` chat-history aspect (Aspect 14).
It does NOT read a session transcript itself, does NOT understand transcript
format, and does NOT take a transcript path. Instead it takes a ``session_id``,
invokes the platform-runtime ``chat extract-signal`` operation (the
platform-owned transcript engine) via the executor subprocess hop, translates
the runtime's normalized record back into the aspect's Tier-1/Tier-2 contract,
and emits the TOON payload the orchestrator routes on.

The two-tier degradation path and the normative skip-reason token contract are
specified in ``references/chat-history-analysis.md`` — NOT restated here. What
follows is only what a reader of this module needs to follow the code:

- A ``session_id`` is passed to the runtime op in a subprocess hop exactly the
  way ``manage-metrics`` invokes ``metrics normalized-tokens`` (see
  :func:`_run_chat_signal_op`). The seam is :func:`_run_chat_signal_op`, a
  module-level name a test can monkeypatch so the consumer logic is testable
  without a live executor.
- The consumer owns the READ BUDGET and thus ``over_budget``. ⛔ It derives that
  decision from ``reduced_transcript_delivered_bytes`` — the size of the
  transcript THIS script emits — and never from the forwarded ``reduced_bytes``,
  which describes the runtime's own reduction rather than what reaches a
  consumer. Both figures are published; only the delivered one is a delivery
  measurement, and a budget decision is about what will actually be read. The
  runtime never makes that decision.
- The reduced transcript is opaque foreign text and crosses the TOON boundary as
  a ``BlockScalar``. Emitted as a plain multi-line ``str`` it is quoted but NOT
  escaped, so every line after the first lands at column zero and ``parse_toon``
  reads it as a sibling top-level key — a transcript line reading ``status: x``
  does not merely vanish, it overwrites the envelope's own ``status``. The
  ``key: |`` block form indents the whole body two spaces past the header, which
  is exactly what the parser strips back off, so the body round-trips verbatim
  and no payload line can be read as a key. See ``BlockScalar`` in
  ``toon_parser.py`` for the boundary contract.
- On the runtime's ``transcript_not_found`` no-op the consumer emits the same
  ``status: skipped`` / ``reason: transcript_unavailable`` fragment it emits
  for a genuine data absence — the transcript-present-but-absent distinction is
  the runtime's, surfaced to the consumer as no-op vs success, and this skill's
  downstream aggregation keys on the token, never on the runtime status.
- The runtime success record is mapped to the consumer's retained historic
  field names (e.g. runtime ``kept_raw_count`` → consumer
  ``reduced_turn_count``), so existing aggregations see the same vocabulary.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Any

from file_ops import output_toon, safe_main
from input_validation import parse_args_with_toon_errors
from toon_parser import BlockScalar, parse_toon

# Default read budget for the reduced transcript: 2 MiB. When the DELIVERED text
# exceeds this, the orchestrator falls back to the Tier-2 WARNING finding.
# Owned by the CONSUMER: the runtime reports its own reduced byte size and never
# makes this decision.
DEFAULT_READ_BUDGET_BYTES = 2 * 1024 * 1024


def _delivered_transcript(raw: Any) -> tuple[BlockScalar, int]:
    """Mark the reduced transcript for block-scalar emission and measure it.

    Returns ``(transcript, delivered_bytes)`` where ``transcript`` is the value
    this script will emit and ``delivered_bytes`` is its UTF-8 size.

    ⛔ The count is taken over the text THIS script emits, which is what makes it
    a DELIVERY measurement rather than a second copy of the runtime's
    ``reduced_bytes``. The two describe different things and diverge exactly when
    it matters: ``reduced_bytes`` is what the runtime's reduction produced, while
    a consumer's budget decision is about what will actually be read. Publishing
    only the forwarded figure made ``over_budget`` a verdict about a payload
    nobody received.

    The ``BlockScalar`` marking is what keeps the two equal in the ordinary case:
    a block scalar round-trips verbatim, so the delivered size measured here is
    the size the consumer parses back out. Both return paths go through this
    helper, so the skip path's empty transcript carries the same shape and the
    same key rather than a second, differently-serialized form.
    """
    text = raw if isinstance(raw, str) else ('' if raw is None else str(raw))
    return BlockScalar(text), len(text.encode('utf-8'))


def _run_chat_signal_op(
    session_id: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """Invoke the platform-runtime ``chat extract-signal`` operation.

    The runtime owns the entire transcript engine (transcript discovery, JSONL
    parse, reduction). This consumer never parses a transcript itself — it
    hands the op the ``session_id``, lets the runtime reduce the transcript and
    return the normalized record, then translates that record into the aspect's
    Tier-1/Tier-2 contract.

    Returns ``(record, status)`` where:

    - ``record`` is the runtime's success payload (the seven-field normalized
      record, plus ``session_id`` / ``transcript_path``) or ``None`` when the
      op did not succeed, and
    - ``status`` is the runtime op's TOON ``status`` field (``success`` /
      ``no-op`` / ``error``) or ``None`` when the op could not be invoked.
    """
    try:
        result = subprocess.run(
            [
                sys.executable,
                '.plan/execute-script.py',
                'plan-marshall:platform-runtime:platform_runtime',
                'chat',
                'extract-signal',
                '--session-id',
                session_id,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return None, None

    try:
        parsed = parse_toon(result.stdout)
    except (ValueError, KeyError):
        parsed = {}
    status = parsed.get('status') if isinstance(parsed, dict) else None

    if status != 'success':
        return None, status
    return parsed, status


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    session_id = args.session_id
    read_budget = args.read_budget_bytes

    record, status = _run_chat_signal_op(session_id)

    base = {
        'aspect': 'chat-signal-extraction',
        'session_id': session_id,
        'read_budget_bytes': read_budget,
    }

    skip_transcript, skip_delivered_bytes = _delivered_transcript('')

    if status != 'success' or record is None:
        # The runtime declined (no-op — no transcript) or errored, or could not
        # be invoked. This is the same data-absence path Tier 2 takes: emit the
        # canonical skip token. The distinction between "no transcript" and
        # "transcript withheld" is made by the RUNTIME's status; this skill
        # surfaces the genuine-absence token for both here.
        return {
            **base,
            'status': 'skipped',
            'reason': 'transcript_unavailable',
            'reduced_turn_count': 0,
            'reduced_bytes': 0,
            'no_signal': True,
            'over_budget': False,
            'raw_turn_count': 0,
            'kept_raw_count': 0,
            'dropped_turn_count': 0,
            'operator_turn_count': 0,
            'gate_decision_count': 0,
            'kept_text_chars': 0,
            'kept_text_bytes': 0,
            'signal_gate_population': 0,
            'residual_counts': {},
            'symmetric_pair_dropped': 0,
            'reduced_transcript_delivered_bytes': skip_delivered_bytes,
            'reduced_transcript': skip_transcript,
        }

    reduced_bytes = int(record.get('reduced_bytes') or 0)
    # ``no_signal`` is forwarded from the runtime, which derives it from
    # OPERATOR-AUTHORED counts, never from the survivor count.
    no_signal = bool(record.get('no_signal'))
    # ⛔ The budget is decided on what is DELIVERED, not on what the runtime
    # reduced. The two diverge precisely when the difference matters, and the
    # consumer reads the delivered payload.
    reduced_transcript, delivered_bytes = _delivered_transcript(record.get('reduced_transcript'))
    over_budget = delivered_bytes > read_budget

    return {
        **base,
        **record,
        'status': 'success',
        'transcript_path': record.get('transcript_path'),
        'reduced_turn_count': int(record.get('kept_raw_count') or 0),
        'kept_raw_count': int(record.get('kept_raw_count') or 0),
        'dropped_turn_count': int(record.get('raw_turn_count') or 0) - int(record.get('kept_raw_count') or 0),
        'operator_turn_count': int(record.get('operator_turn_count') or 0),
        'gate_decision_count': int(record.get('gate_decision_count') or 0),
        'kept_text_chars': int(record.get('kept_text_chars') or 0),
        'kept_text_bytes': int(record.get('kept_text_bytes') or 0),
        'signal_gate_population': int(record.get('signal_gate_population') or 0),
        'residual_counts': dict(record.get('residual_counts') or {}),
        'symmetric_pair_dropped': int(record.get('symmetric_pair_dropped') or 0),
        'reduced_bytes': reduced_bytes,
        'reduced_transcript_delivered_bytes': delivered_bytes,
        'no_signal': no_signal,
        'over_budget': over_budget,
        'reduced_transcript': reduced_transcript,
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Invoke the chat extract-signal runtime op for the chat-history aspect',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    run_parser = subparsers.add_parser(
        'run',
        help='Reduce a session transcript to signal-bearing turns',
        allow_abbrev=False,
    )
    run_parser.add_argument(
        '--session-id',
        required=True,
        help='Platform session identifier whose transcript is reduced',
    )
    run_parser.add_argument(
        '--read-budget-bytes',
        type=int,
        default=DEFAULT_READ_BUDGET_BYTES,
        help=(
            'Read budget in bytes for the reduced transcript '
            f'(default {DEFAULT_READ_BUDGET_BYTES}); over_budget is set when '
            'reduced_transcript_delivered_bytes -- the transcript this script '
            'emits -- exceeds this, never the forwarded reduced_bytes'
        ),
    )
    run_parser.set_defaults(func=cmd_run)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()

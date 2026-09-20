# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``extract-chat-signal`` consumer test modules.

Holds the module-level load, the session id the consumer tests drive, and
builders for the RUNTIME's normalized record — because the consumer does not
parse a transcript itself anymore. It hopped to the platform-runtime
``chat extract-signal`` operation (:func:`_run_chat_signal_op`), and these
tests drive ``cmd_run`` through a monkeypatched ``_run_chat_signal_op`` that
returns a runtime-shaped record.

It also holds what the delivery half of the contract needs, since three modules
assert against it: :data:`TRANSCRIPT_WITH_TOON_SHAPES` (the adversarial reduced
transcript), :func:`transcript_of_exactly` (a transcript sized to a stated byte
count, for the budget boundary), and :func:`emit_and_reparse` (the TOON round
trip the CLI actually prints across). Keeping the three here is what stops the
consumer modules from each growing their own near-miss of the transport.
"""

from __future__ import annotations

from toon_parser import parse_toon, serialize_toon

from conftest import load_script_module, parse_ns

# Direct module load so unit tests can poke the consumer seam.
_mod = load_script_module('plan-marshall', 'plan-retrospective', 'extract-chat-signal.py', 'extract_chat_signal')

# A real-shaped platform session id the runtime resolves to a transcript.
SESSION_ID = '22222222-2222-2222-2222-222222222201'

# A reduced transcript carrying every shape a naive scalar emission mishandles:
# a flush-left continuation line, a line reading exactly like a TOON key/value
# pair — and not just any key, but ``status``, the envelope's own — a colon
# inside indented text, and interior blank lines. Deliberately no trailing blank
# line: the body's own trailing blank and the document terminator are the same
# byte, an ambiguity ``BlockScalar``'s docstring resolves in favour of the
# terminated form, and this fixture has no business exercising that edge.
TRANSCRIPT_WITH_TOON_SHAPES = (
    'user: please revert that change\n'
    '\n'
    'operator-decision: hold the line\n'
    'status: blocked\n'
    '    indented continuation: with a colon\n'
    '\n'
    'assistant: reverted'
)


def transcript_of_exactly(n_bytes: int) -> str:
    """Build a reduced transcript whose UTF-8 size is exactly ``n_bytes``.

    Budget cases are about a boundary, so the fixture states the size it built
    rather than leaving a caller to count a literal. ASCII throughout, so one
    character is one byte and the assertion a caller writes about the size is
    the size the helper produced.
    """
    prefix = 'user: '
    assert n_bytes >= len(prefix), f'transcript floor is {len(prefix)} bytes, asked for {n_bytes}'
    text = prefix + 'x' * (n_bytes - len(prefix))
    assert len(text.encode('utf-8')) == n_bytes
    return text


def emit_and_reparse(payload: dict) -> dict:
    """Round-trip a consumer payload through the boundary the CLI prints across.

    ``main()`` emits through ``output_toon``, which is ``print(serialize_toon(…))``
    — so the document the consumer actually writes carries a terminating
    newline. ⛔ That newline is load-bearing, not cosmetic: ``serialize_toon``
    returns the document WITHOUT it, and handing the bare return to
    ``parse_toon`` costs a block-scalar body its final blank line. Reproducing
    ``print``'s newline here is what makes this helper the transport the payload
    crosses in production rather than a near-miss of it.
    """
    return parse_toon(serialize_toon(payload) + '\n')


def _runtime_record(
    *,
    raw_turn_count: int = 0,
    kept_raw_count: int = 0,
    operator_turn_count: int = 0,
    gate_decision_count: int = 0,
    reduced_bytes: int = 0,
    no_signal: bool = True,
    reduced_transcript: str = '',
    transcript_path: str = '/transcripts/project/session.jsonl',
    session_id: str = SESSION_ID,
    kept_text_chars: int = 0,
    kept_text_bytes: int = 0,
    signal_gate_population: int = 0,
    residual_counts: dict | None = None,
    symmetric_pair_dropped: int = 0,
) -> dict:
    """Build a runtime ``success`` payload exactly as the op reports it.

    The seven-field normalized record plus the ``session_id``/``transcript_path``
    the op attaches. Tests feed this to ``cmd_run`` through the mocked
    ``_run_chat_signal_op`` seam and assert the consumer's translation.
    """
    return {
        'session_id': session_id,
        'transcript_path': transcript_path,
        'reduced_transcript': reduced_transcript,
        'raw_turn_count': raw_turn_count,
        'kept_raw_count': kept_raw_count,
        'operator_turn_count': operator_turn_count,
        'gate_decision_count': gate_decision_count,
        'reduced_bytes': reduced_bytes,
        'no_signal': no_signal,
        'kept_text_chars': kept_text_chars,
        'kept_text_bytes': kept_text_bytes,
        'signal_gate_population': signal_gate_population,
        'residual_counts': dict(residual_counts) if residual_counts is not None else {},
        'symmetric_pair_dropped': symmetric_pair_dropped,
    }


def run_consumer(
    monkeypatch,
    record,
    status='success',
    *,
    read_budget=None,
    session_id: str = SESSION_ID,
) -> dict:
    """Drive ``cmd_run`` through the mocked hop seam, pinning the forwarded id.

    ``_fake`` records the session id the consumer hands to
    :func:`_run_chat_signal_op`; the returned result asserts it equals
    ``session_id``. A consumer that forwards a wrong or hardcoded id (instead
    of the CLI ``--session-id`` value) fails here — that is the hop semantics
    these modules exist to pin, and the single shared copy stops the local
    ``_run`` duplicates from drifting apart again.
    """
    seen: list[str] = []

    def _fake(sid):
        seen.append(sid)
        return record, status

    monkeypatch.setattr(_mod, '_run_chat_signal_op', _fake)
    args = parse_ns(
        'plan-marshall',
        'plan-retrospective',
        'extract-chat-signal.py',
        'run',
        '--session-id',
        session_id,
    )
    if read_budget is not None:
        args.read_budget_bytes = read_budget
    result = _mod.cmd_run(args)
    assert seen == [session_id], f'forwarded id {seen!r} != requested {session_id!r}'
    return result

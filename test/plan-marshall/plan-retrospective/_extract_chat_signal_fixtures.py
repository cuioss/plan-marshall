# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``extract-chat-signal`` consumer test modules.

Holds the module-level load, the session id the consumer tests drive, and
builders for the RUNTIME's normalized record — because the consumer does not
parse a transcript itself anymore. It hopped to the platform-runtime
``chat extract-signal`` operation (:func:`_run_chat_signal_op`), and these
tests drive ``cmd_run`` through a monkeypatched ``_run_chat_signal_op`` that
returns a runtime-shaped record.
"""

from __future__ import annotations

from conftest import load_script_module, parse_ns

# Direct module load so unit tests can poke the consumer seam.
_mod = load_script_module(
    'plan-marshall', 'plan-retrospective', 'extract-chat-signal.py', 'extract_chat_signal'
)

# A real-shaped platform session id the runtime resolves to a transcript.
SESSION_ID = '22222222-2222-2222-2222-222222222201'


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
    assert seen == [session_id], f"forwarded id {seen!r} != requested {session_id!r}"
    return result

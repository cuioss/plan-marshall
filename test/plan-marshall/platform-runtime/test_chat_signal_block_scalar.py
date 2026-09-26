# SPDX-License-Identifier: FSL-1.1-ALv2
"""The producer-side block-scalar marking on ``reduced_transcript``.

Governs the ``chat extract-signal`` record's crossing of the TOON boundary. The
reduced transcript is the one field in the record that is multi-line BY
CONSTRUCTION — two surviving turns render as two paragraphs — and an unmarked
multi-line string cannot cross that boundary: the serializer quotes it without
escaping anything, so every line after the first is read back by ``parse_toon``
as a SIBLING TOP-LEVEL KEY of the envelope.

Two distinct consequences, and they fail independently, so both are asserted
here:

- the transcript is TRUNCATED at the first interior newline, so a delivered
  transcript is not the reduced one;
- a transcript line that happens to read ``status: blocked`` OVERWRITES the
  envelope's own ``status``. A byte-count comparison alone would not catch that
  second half — the two figures can agree while the payload has been
  reassigned to a different field.

The fixture reuses ``_chat_signal_fixtures`` rather than restating a transcript
format, so a format change is made once, in the module that owns it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import _chat_signal_reducer as _mod
import pytest
from _chat_signal_fixtures import (
    OPERATOR_TEXT,
    chat_turn,
    write_jsonl,
)
from toon_parser import BlockScalar, parse_toon, serialize_toon

#: The operator correction plus a signal-bearing assistant turn that quotes a
#: TOON envelope key/value pair verbatim. The assistant turn survives only
#: because it carries a decision marker — that is the reducer's own rule, and it
#: is what puts a raw ``status:`` line at column zero of the rendered output.
ENVELOPE_LOOKING_TURN = '[ERROR] gate refused\nstatus: blocked\ndetails follow'


def _transcript(tmp_path: Path, *turn_texts: str) -> Path:
    path = tmp_path / 'session.jsonl'
    write_jsonl(
        path,
        chat_turn('user', [{'type': 'text', 'text': OPERATOR_TEXT}]),
        *(chat_turn('assistant', [{'type': 'text', 'text': text}]) for text in turn_texts),
    )
    return path


def _delivered(record: dict, envelope_status: str = 'success') -> dict:
    """Serialize the record as the operation emits it and parse it back.

    The pairing is the transport's own: ``print(serialize_toon(...))`` on the way
    out, ``parse_toon`` over the captured stdout on the way back. Handing the
    unterminated ``serialize_toon`` return straight to ``parse_toon`` instead
    would cost the body its final blank line — see ``BlockScalar`` in
    ``toon_parser.py``.
    """
    document = serialize_toon({'status': envelope_status, 'operation': 'chat extract-signal', **record})
    return parse_toon(document + '\n')


class TestProducerMarksTheField:
    def test_record_field_is_a_block_scalar(self, tmp_path: Path) -> None:
        record = _mod.reduce_chat_signal(_transcript(tmp_path, ENVELOPE_LOOKING_TURN))
        assert isinstance(record['reduced_transcript'], BlockScalar)

    def test_marking_does_not_change_the_text(self, tmp_path: Path) -> None:
        """A ``BlockScalar`` is a ``str``: in-process consumers are unaffected.

        Compared against the reducer's own rendering of the same file, so the
        assertion is about the marking rather than about the reduction.
        """
        path = _transcript(tmp_path, ENVELOPE_LOOKING_TURN)
        record = _mod.reduce_chat_signal(path)
        expected = _mod.render_reduced(_mod.reduce_transcript(_mod.read_transcript_lines(path)).turns)
        assert str(record['reduced_transcript']) == expected


class TestRoundTripIsWhole:
    """The consumer's budget figure is measured on what it actually receives."""

    def test_delivered_transcript_is_byte_identical_to_the_reduction(self, tmp_path: Path) -> None:
        record = _mod.reduce_chat_signal(_transcript(tmp_path, ENVELOPE_LOOKING_TURN))
        delivered = _delivered(record)['reduced_transcript']
        assert str(delivered) == str(record['reduced_transcript'])

    def test_reduced_bytes_equals_reduced_transcript_delivered_bytes(self, tmp_path: Path) -> None:
        """The comparison the consumer's ``over_budget`` verdict rests on.

        ``reduced_bytes`` measures the reduction; the consumer's
        ``reduced_transcript_delivered_bytes`` measures what it emits. They
        agree because a block scalar round-trips verbatim — which is the whole
        reason the marking is producer-side rather than left to the consumer.
        """
        record = _mod.reduce_chat_signal(_transcript(tmp_path, ENVELOPE_LOOKING_TURN))
        delivered = str(_delivered(record)['reduced_transcript'])
        assert len(delivered.encode('utf-8')) == record['reduced_bytes']


class TestEnvelopeIsNotCorrupted:
    """The half a byte-count assertion cannot see."""

    def test_transcript_line_does_not_overwrite_the_envelope_status(self, tmp_path: Path) -> None:
        record = _mod.reduce_chat_signal(_transcript(tmp_path, ENVELOPE_LOOKING_TURN))
        assert 'status: blocked' in str(record['reduced_transcript'])
        assert _delivered(record, envelope_status='success')['status'] == 'success'

    def test_no_payload_line_adds_or_removes_an_envelope_key(self, tmp_path: Path) -> None:
        """The corruption's signature: a payload line read as a top-level key.

        Swept over the whole record rather than over hand-picked keys, so the
        assertion is about the envelope's key SET and cannot be satisfied by
        enumerating the keys one happens to think of.
        """
        record = _mod.reduce_chat_signal(_transcript(tmp_path, ENVELOPE_LOOKING_TURN))
        envelope = {'status': 'success', 'operation': 'chat extract-signal', **record}
        assert set(_delivered(record, envelope_status='success')) == set(envelope)

    def test_no_payload_line_overwrites_any_scalar_envelope_key(self, tmp_path: Path) -> None:
        """Whatever scalar a payload line happens to name keeps the envelope's.

        Swept over every scalar key the envelope actually carries rather than
        over a hand-picked few, because the corruption is key-agnostic: the key a
        transcript line names is the key that gets overwritten, so a list written
        out by hand leaves every key not on it unguarded — and a stale list is
        worse than none, since it reads as coverage.

        Scalars only. An EMPTY map does not survive ``serialize_toon`` →
        ``parse_toon`` on its own terms (``residual_counts: {}`` reads back as an
        empty string), so including container keys here would assert against the
        serializer's own behaviour rather than against this defect. Their key
        PRESENCE is covered by the key-set case above.
        """
        record = _mod.reduce_chat_signal(_transcript(tmp_path, ENVELOPE_LOOKING_TURN))
        envelope: dict[str, Any] = {'status': 'success', 'operation': 'chat extract-signal', **record}
        scalars = {key: value for key, value in envelope.items() if isinstance(value, (str, int, float, bool))}
        assert len(scalars) >= 5, f'the sweep collected only {sorted(scalars)}; the record lost its scalar fields'

        parsed = _delivered(record, envelope_status='success')
        for key, value in scalars.items():
            assert str(parsed[key]) == str(value), f'envelope key {key!r} was rewritten by a transcript line'

    def test_the_transcript_itself_still_contains_the_looked_like_key_line(self, tmp_path: Path) -> None:
        """The line survives INSIDE the body — it must not be stripped out.

        Asserted so a future "fix" cannot pass by deleting payload lines that
        look like keys. The transcript is foreign text; it is carried, not
        sanitised.
        """
        record = _mod.reduce_chat_signal(_transcript(tmp_path, ENVELOPE_LOOKING_TURN))
        delivered = str(_delivered(record)['reduced_transcript'])
        assert 'status: blocked' in delivered
        assert delivered.count('\n') == str(record['reduced_transcript']).count('\n')


class TestSingleTurnReduction:
    """A one-turn reduction is single-line, so the hazard is absent anyway.

    Present so the suite states that the marking costs nothing on the degenerate
    case, rather than leaving a reader to wonder whether it broke it.
    """

    def test_single_surviving_turn_round_trips_and_keeps_its_bytes(self, tmp_path: Path) -> None:
        path = tmp_path / 'session.jsonl'
        write_jsonl(path, chat_turn('user', [{'type': 'text', 'text': OPERATOR_TEXT}]))
        record = _mod.reduce_chat_signal(path)
        assert '\n' not in str(record['reduced_transcript'])
        delivered = _delivered(record)['reduced_transcript']
        assert str(delivered) == str(record['reduced_transcript'])
        assert len(str(delivered).encode('utf-8')) == record['reduced_bytes']

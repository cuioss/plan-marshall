# SPDX-License-Identifier: FSL-1.1-ALv2
"""One matched POSITIVE control per producer this plan repaired.

Every deliverable in the fix set teaches a producer to WITHHOLD a figure it
cannot substantiate. Each one ships the negative case for that — the unreadable
population, the unresolvable footprint, the empty Surface B. On its own, a suite
of negative cases is satisfied by a producer that withholds unconditionally: a
script that answered ``unavailable`` to everything would pass all of them and
report nothing ever again. That failure is silent, because withholding is
exactly what the negative cases were written to reward.

These are the other halves. For each member of the fix set, the producer is
driven over a population that IS readable and must publish a real figure. The
pair — this module's positive arm against the deliverable's own negative arm —
is what shows the fix DISCRIMINATES rather than merely withholding, and each
control asserts both arms itself so the discrimination is proven inside one
case rather than inferred across two files.

The roster is one declared structure the parametrization is generated FROM, so
a control quietly dropped shrinks a published number rather than disappearing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from _analyze_logs_fixtures import _build_row
from _extract_chat_signal_fixtures import _runtime_record, transcript_of_exactly
from _extract_chat_signal_fixtures import run_consumer as _run_chat_consumer

from conftest import MARKETPLACE_ROOT, load_script_module

_SCRIPTS_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts'

_manifest_consistency = load_script_module(
    'plan-marshall', 'plan-retrospective', 'check-manifest-consistency.py', 'mc_controls', register=False
)
_analyze_logs = load_script_module(
    'plan-marshall', 'plan-retrospective', 'analyze-logs.py', 'al_controls', register=False
)
_dispatch_audit = load_script_module(
    'plan-marshall', 'plan-retrospective', 'check-dispatch-audit.py', 'da_controls', register=False
)


def _d2_readable_and_withheld(tmp_path: Path, monkeypatch) -> tuple[object, object]:
    """D2 — a RESOLVABLE footprint still yields the paths, not a degradation verdict.

    The deliverable's negative arm is the `FOOTPRINT_UNRESOLVED` sentinel, which
    must NOT reach the `raw_files_total == 0` branch. Its positive half is here:
    when a tier does answer, the loader reports the paths it resolved and says
    the evidence was available.
    """
    plan_dir = tmp_path / 'plan'
    plan_dir.mkdir()
    resolved = {'marketplace/bundles/plan-marshall/skills/demo/SKILL.md', 'test/plan-marshall/demo/test_demo.py'}

    monkeypatch.setattr(_manifest_consistency, 'resolve_footprint', lambda *_a, **_k: resolved)
    files, readable_label, readable_available = _manifest_consistency.load_diff_files(
        None, plan_dir, 'demo', None, None
    )
    assert readable_available is True, 'a resolved footprint must report its evidence as available'
    assert sorted(files) == sorted(resolved), 'the resolved paths must reach the rules, not an empty list'

    monkeypatch.setattr(_manifest_consistency, 'resolve_footprint', lambda *_a, **_k: None)
    empty, withheld_label, withheld_available = _manifest_consistency.load_diff_files(
        None, plan_dir, 'demo', None, None
    )
    assert withheld_available is False, 'an unresolvable footprint is an absence of evidence'
    assert empty == []

    return readable_label, withheld_label


def _d3_readable_and_withheld(tmp_path: Path, monkeypatch) -> tuple[object, object]:
    """D3 — a ledger carrying a real build row still publishes a real total.

    The deliverable's negative arm is the `unavailable` sentinel over a ledger
    that held no summable row. Its positive half is here: a row with a usable
    duration must produce a float, or the fix has simply stopped reporting build
    time at all.

    Both the path resolver and the reader are rebound, because they resolve
    through different modules — a bare ``read_entries()`` re-resolves through
    ``_ledger_core``'s own globals and would read the repository's live ledger.
    """

    def _summary(rows: list[dict], *, name: str) -> dict:
        ledger = tmp_path / name / 'change-ledger.jsonl'
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
        real_read = _analyze_logs.read_entries
        monkeypatch.setattr(_analyze_logs, 'resolve_ledger_path', lambda: ledger)
        monkeypatch.setattr(
            _analyze_logs, 'read_entries', lambda path=None: real_read(ledger if path is None else path)
        )
        return _analyze_logs.summarize_build_ledger('demo')

    readable = _summary([_build_row('demo', dur=9.5), _build_row('demo', dur=3.0)], name='readable')
    assert isinstance(readable['total_build_seconds'], float), (
        f'two rows carrying usable durations must sum to a real float total; got {readable["total_build_seconds"]!r}'
    )
    assert readable['total_build_seconds'] == 12.5
    assert int(readable['summed_rows']) == 2, 'the population behind the total must be published'

    # The deliverable's own negative arm, re-driven here so the pair is proven in
    # one place: every row is a suspect zero, so nothing was summed.
    withheld = _summary([_build_row('demo', dur=0)], name='withheld')
    assert withheld['total_build_seconds'] == 'unavailable'
    assert int(withheld['summed_rows']) == 0

    return readable['total_build_seconds'], withheld['total_build_seconds']


def _d4_readable_and_withheld(tmp_path: Path, monkeypatch) -> tuple[object, object]:
    """D4 — a delivered transcript still reports the bytes it delivered.

    The deliverable's negative arm is the divergence case, where the forwarded
    ``reduced_bytes`` is not what reached the consumer. Its positive half is
    here: the delivered figure must be the real size of the emitted text, and
    the skip path — which delivers nothing — must report a different figure
    rather than the same one.
    """
    transcript = transcript_of_exactly(180)
    record = _runtime_record(no_signal=False, reduced_bytes=9000, reduced_transcript=transcript)
    readable = _run_chat_consumer(monkeypatch, record, 'success')
    assert int(readable['reduced_transcript_delivered_bytes']) == 180, (
        'the delivered figure must measure the emitted transcript, not restate the forwarded reduced_bytes'
    )
    assert int(readable['reduced_bytes']) == 9000, 'the forwarded figure is published beside it, unchanged'

    withheld = _run_chat_consumer(monkeypatch, None, 'no-op')
    assert int(withheld['reduced_transcript_delivered_bytes']) == 0
    assert withheld['status'] == 'skipped'

    return readable['reduced_transcript_delivered_bytes'], withheld['reduced_transcript_delivered_bytes']


def _d5_readable_and_withheld(tmp_path: Path, monkeypatch) -> tuple[object, object]:
    """D5 — a populated Surface B still yields a real corroboration verdict.

    The deliverable's negative arm is the `not_evaluated` block over an empty
    Surface B. Its positive half is here: with resolve records to pair against,
    the block must render an actual verdict about its own strength.
    """
    seam = 'plan-marshall:manage-config'
    resolves = [{'role': 'leaf', 'caller': seam}]
    dispatches = [
        {'caller': seam, 'role': 'leaf', 'target': 'execution-context-level-3', 'workflow': 'plan-marshall:d/SKILL.md'}
    ]

    readable = _dispatch_audit.evaluate_shape_violation(resolves, dispatches)
    assert readable['status'] == 'evaluated'
    assert readable['corroboration'] == 'seam_corroborated'
    assert int(readable['foreign_caller_line_total']) == 0

    withheld = _dispatch_audit.evaluate_shape_violation([], dispatches)
    assert withheld['status'] == 'not_evaluated'
    assert withheld['corroboration'] == 'not_evaluated'

    return readable['corroboration'], withheld['corroboration']


#: One entry per member of this plan's fix set: the deliverable, the producer it
#: repaired, and the control that drives that producer over BOTH a readable and an
#: unreadable population. The parametrization is generated from this structure, so
#: a control removed shrinks :func:`test_every_fix_set_member_has_a_positive_control`'s
#: published roster size rather than vanishing without trace.
FIX_SET_CONTROLS = (
    ('D2', 'check-manifest-consistency.py', _d2_readable_and_withheld),
    ('D3', 'analyze-logs.py', _d3_readable_and_withheld),
    ('D4', 'extract-chat-signal.py', _d4_readable_and_withheld),
    ('D5', 'check-dispatch-audit.py', _d5_readable_and_withheld),
)

#: The number of producers this plan repairs. A literal is correct here because
#: the literal IS the coverage claim — deriving it from :data:`FIX_SET_CONTROLS`
#: would make the comparison below ``roster == roster`` and could never fail.
#: (Same reasoning the sibling ``_COVERED_GRADES`` declaration states.)
_FIX_SET_SIZE = 4

# ⛔ Vacuity guard at the BINDING SITE as well as in the test below, because a
# parametrized body never runs when its parameter set is empty.
assert FIX_SET_CONTROLS, 'the control roster is empty — every case below would be collected as nothing'


@pytest.mark.parametrize(('deliverable', 'producer', 'control'), FIX_SET_CONTROLS)
def test_the_repaired_producer_still_reports_when_the_population_is_readable(
    tmp_path, monkeypatch, deliverable, producer, control
):
    """The positive control, paired with its deliverable's own negative case.

    The control asserts both arms itself; this body asserts the property that
    makes them a PAIR — the two populations produce different figures. A
    producer that withheld unconditionally returns the same value twice and
    fails here even if every negative case in the plan still passes.
    """
    readable, withheld = control(tmp_path, monkeypatch)

    assert readable != withheld, (
        f'{deliverable} ({producer}): the readable and unreadable populations produced the SAME figure '
        f'({readable!r}) — the producer is withholding (or reporting) unconditionally, so its negative '
        f'case proves nothing about discrimination'
    )


def test_every_fix_set_member_has_a_positive_control():
    """⛔ Population guard — the roster size the controls were generated over.

    Publishes the roster rather than assuming it: a control deleted, or two
    entries collapsed onto one deliverable, shows up as a size mismatch instead
    of as a quietly smaller parametrization. Each named producer is also
    confirmed to exist on disk, so a renamed or removed script fails here rather
    than leaving a control pointing at nothing.
    """
    deliverables = [entry[0] for entry in FIX_SET_CONTROLS]
    producers = [entry[1] for entry in FIX_SET_CONTROLS]

    assert len(deliverables) == len(set(deliverables)), f'duplicate deliverable in the roster: {deliverables}'
    assert len(FIX_SET_CONTROLS) == _FIX_SET_SIZE, (
        f'the control roster covers {len(FIX_SET_CONTROLS)} deliverable(s) but this plan repairs '
        f'{_FIX_SET_SIZE}: {deliverables}'
    )

    missing = [name for name in producers if not (_SCRIPTS_DIR / name).is_file()]
    assert not missing, f'control roster names producer script(s) that do not exist: {missing}'

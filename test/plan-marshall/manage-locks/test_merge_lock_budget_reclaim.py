#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``merge_lock.py`` budget-aware reclaim (``budget-reclaim``).

Contract under test (the waiter-side reclaim for the orchestrator-layer
``merge_hold_budget_seconds`` bound):

* **Nothing to reclaim** — no lock file yields ``status: success``,
  ``action: nothing_to_reclaim`` (a concurrently-released lock is not an
  error).
* **Not due** — elapsed (``now - hold_start``) below budget yields
  ``status: success``, ``action: not_due``; the holder keeps its budget and
  the waiter keeps polling. The holder is NOT consulted beyond the verdict
  report.
* **Reclaims only a provably stale holder past budget** — elapsed at/past
  budget with a main-anchored-dead holder evicts through the observed-file
  sidecar arbitration (reusing the ``release --require-stale`` core) and
  dequeues the holder from the FIFO front.
* **Fail-closed on ``fresh`` past budget** — a live holder past budget is
  REFUSED (``status: refused``, ``reason: holder_not_provably_dead``) with
  NO unlink; the live-but-slow case belongs to the orchestrator's
  release + re-enqueue + escalate path, never to this verb.
* **Caller bugs refused before the lock is touched** — a non-finite or
  negative ``--hold-start`` (``invalid_hold_start``) and a non-finite or
  non-positive ``--hold-budget-seconds`` (``invalid_hold_budget``) return
  ``status: error`` and leave an existing lock intact.
* **Budget audit fields** — every branch carries ``elapsed_seconds`` and
  ``hold_budget_seconds`` so the caller can audit the budget arithmetic.
* **``--hold-start`` is POSIX epoch seconds** — at the CLI boundary the integer
  string ``date +%s`` prints is accepted and reaches the budget arithmetic,
  while an ISO-8601 timestamp is an argparse rejection (exit 2) raised before
  the handler runs, so the lock is never touched.
* **The caller binds that shape** — ``branch-cleanup.md`` § "Merge-Mutex Hold
  Window" invariant 2 binds ``{hold_start}`` as ``date +%s`` epoch seconds,
  and every other doc naming ``{hold_start}`` points at that binding instead
  of defining a shape of its own.
* **The blocked-admission reclaim passes a value bound before it is used** —
  a waiter blocked on admission was never admitted, so it has no
  ``{hold_start}``. Invariant 2 binds ``{admission_wait_start}`` (``date +%s``
  before the FIFO poll loop's first ``acquire``) and the ``budget-reclaim``
  call passes that, never ``{hold_start}``; every other site naming
  ``{admission_wait_start}`` points back at invariant 2.

Isolation mirrors ``test_merge_lock_conditional_release.py``: every test runs
against an isolated ``PLAN_BASE_DIR`` staged under ``tmp_path`` so the lock,
the FIFO queue, and holder plan dirs resolve there rather than the real
``.plan`` tree.
"""

from __future__ import annotations

import re
import sys
import time
from argparse import Namespace
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from _manage_locks_fixtures import _make_live_plan, _write_lock
from toon_parser import parse_toon

from conftest import MARKETPLACE_ROOT, load_script_module

merge_lock = load_script_module('plan-marshall', 'manage-locks', 'merge_lock.py', 'merge_lock_budget_under_test')

_BRANCH_CLEANUP_DOC: Path = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'standards' / 'branch-cleanup.md'
)
_HOLD_START_TOKEN = '{hold_start}'
_ADMISSION_WAIT_START_TOKEN = '{admission_wait_start}'


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def isolated_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage an isolated PLAN_BASE_DIR under tmp_path (main stand-in)."""
    base = tmp_path / 'main' / '.plan' / 'local'
    (base / 'plans').mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return {
        'base': base,
        'lock_path': base / 'merge.lock',
        'queue_path': base / 'merge-queue.json',
    }


@pytest.fixture(autouse=True)
def _stub_title_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the title-token seams (budget-reclaim suppresses the surface, but
    the stubs keep the unit tests off the real executor regardless)."""
    monkeypatch.setattr(merge_lock, '_set_title_token', lambda _p, _state: None)
    monkeypatch.setattr(merge_lock, '_clear_title_token', lambda _p: None)
    monkeypatch.setattr(merge_lock, '_push_title_token', lambda _p, icon=None: None)


def _reclaim(plan_id: str, hold_start: float, hold_budget_seconds: float) -> dict:
    result: dict = merge_lock.run_budget_reclaim(
        Namespace(plan_id=plan_id, hold_start=hold_start, hold_budget_seconds=hold_budget_seconds)
    )
    return result


# =============================================================================
# No lock / inside budget — no eviction
# =============================================================================


class TestBudgetReclaimNoOpBranches:
    def test_nothing_to_reclaim_when_lock_free(self, isolated_base: dict) -> None:
        result = _reclaim('waiter', time.time() - 7200.0, 3600.0)

        assert result['status'] == 'success'
        assert result['action'] == 'nothing_to_reclaim'
        assert result['hold_budget_seconds'] == 3600.0

    def test_not_due_inside_budget(self, isolated_base: dict) -> None:
        # A live holder inside its budget keeps it — the waiter keeps polling.
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        _make_live_plan(base, 'slow-holder')
        _write_lock(lock_path, 'slow-holder')

        result = _reclaim('waiter', time.time(), 3600.0)

        assert result['status'] == 'success'
        assert result['action'] == 'not_due'
        assert result['holder'] == 'slow-holder'
        assert result['elapsed_seconds'] < 3600.0
        assert lock_path.exists()


# =============================================================================
# Past budget — stale reclaims, fresh refuses
# =============================================================================


class TestBudgetReclaimPastBudget:
    def test_reclaims_stale_holder_past_budget(self, isolated_base: dict) -> None:
        # Holder dead (no plan dir anywhere) and hold 3700s past a 3600s
        # budget → evicted through the shared stale-eviction core.
        lock_path = isolated_base['lock_path']
        _write_lock(lock_path, 'dead-holder')

        result = _reclaim('waiter', time.time() - 3700.0, 3600.0)

        assert result['status'] == 'success'
        assert result['action'] == 'released'
        assert result['reclaimed_from'] == 'dead-holder'
        assert result['elapsed_seconds'] >= 3600.0
        assert result['hold_budget_seconds'] == 3600.0
        assert not lock_path.exists()

    def test_refuses_fresh_holder_past_budget(self, isolated_base: dict) -> None:
        # A LIVE holder past budget is never force-released by this verb —
        # the live-but-slow case belongs to the orchestrator's release +
        # re-enqueue + escalate path.
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        _make_live_plan(base, 'slow-live-holder')
        _write_lock(lock_path, 'slow-live-holder')

        result = _reclaim('waiter', time.time() - 7200.0, 3600.0)

        assert result['status'] == 'refused'
        assert result['reason'] == 'holder_not_provably_dead'
        assert result['elapsed_seconds'] >= 3600.0
        assert lock_path.exists()


# =============================================================================
# Caller bugs — refused before the lock is touched
# =============================================================================


class TestBudgetReclaimInvalidInput:
    def test_negative_hold_start_is_refused_and_leaves_lock_intact(self, isolated_base: dict) -> None:
        lock_path = isolated_base['lock_path']
        _write_lock(lock_path, 'dead-holder')

        result = _reclaim('waiter', -1.0, 3600.0)

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_hold_start'
        # The audit fields ride every branch, including refusals.
        assert result['elapsed_seconds'] == 0.0
        assert result['hold_budget_seconds'] == 3600.0
        assert lock_path.exists()

    def test_non_positive_budget_is_refused_and_leaves_lock_intact(self, isolated_base: dict) -> None:
        lock_path = isolated_base['lock_path']
        _write_lock(lock_path, 'dead-holder')

        result = _reclaim('waiter', time.time() - 10.0, 0.0)

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_hold_budget'
        assert result['elapsed_seconds'] >= 0.0
        assert result['hold_budget_seconds'] == 0.0
        assert lock_path.exists()


# =============================================================================
# --hold-start shape at the CLI boundary — POSIX epoch seconds, never ISO-8601
# =============================================================================


def _run_cli(monkeypatch: pytest.MonkeyPatch, hold_start: str) -> None:
    """Drive ``main()`` with a patched argv for one ``budget-reclaim`` call.

    argparse reads the process-global ``sys.argv``; ``main`` raises
    ``SystemExit`` on an argparse rejection.
    """
    argv = [
        'merge_lock.py',
        'budget-reclaim',
        '--plan-id',
        'waiter',
        '--hold-start',
        hold_start,
        '--hold-budget-seconds',
        '3600',
    ]
    monkeypatch.setattr(sys, 'argv', argv)
    merge_lock.main()


class TestHoldStartCliShape:
    def test_integer_epoch_string_reaches_budget_arithmetic(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # The `date +%s` form: an integer string, 3700s before now.
        lock_path = isolated_base['lock_path']
        _write_lock(lock_path, 'dead-holder')
        hold_start = int(time.time()) - 3700

        _run_cli(monkeypatch, str(hold_start))

        result = parse_toon(capsys.readouterr().out)
        assert result['status'] == 'success'
        assert result['action'] == 'released'
        # elapsed is measured from the parsed epoch, so it lands just past 3700s.
        assert 3700.0 <= result['elapsed_seconds'] < 3700.0 + 60.0
        assert not lock_path.exists()

    @pytest.mark.parametrize(
        'iso_form',
        [
            pytest.param(lambda now: now.isoformat(), id='isoformat-offset'),
            pytest.param(lambda now: now.strftime('%Y-%m-%dT%H:%M:%SZ'), id='zulu'),
        ],
    )
    def test_iso_8601_value_is_rejected_before_the_lock_is_touched(
        self,
        isolated_base: dict,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        iso_form: Callable[[datetime], str],
    ) -> None:
        lock_path = isolated_base['lock_path']
        _write_lock(lock_path, 'dead-holder')
        lock_before = lock_path.read_bytes()
        handler_calls: list[Namespace] = []
        monkeypatch.setattr(merge_lock, 'run_budget_reclaim', handler_calls.append)

        with pytest.raises(SystemExit) as exc:
            _run_cli(monkeypatch, iso_form(datetime.now(UTC)))

        assert exc.value.code == 2
        assert 'argument --hold-start' in capsys.readouterr().err
        assert handler_calls == []
        assert lock_path.read_bytes() == lock_before


# =============================================================================
# Caller-side binding — branch-cleanup.md owns the {hold_start} shape
# =============================================================================


def _invariant_two_paragraph(text: str) -> str:
    """Return invariant 2 of § "Merge-Mutex Hold Window" up to invariant 3."""
    section = text.split('## Merge-Mutex Hold Window', 1)[1].split('\n## ', 1)[0]
    match = re.search(r'^2\. \*\*Bounded hold.*?(?=^3\. )', section, flags=re.MULTILINE | re.DOTALL)
    assert match is not None, 'invariant 2 not found under § "Merge-Mutex Hold Window"'
    return match.group(0)


class TestHoldStartCallerBinding:
    def test_branch_cleanup_binds_hold_start_as_date_epoch_seconds(self) -> None:
        paragraph = _invariant_two_paragraph(_BRANCH_CLEANUP_DOC.read_text(encoding='utf-8'))

        assert f'`{_HOLD_START_TOKEN}` is the acquire instant as an **integer POSIX epoch in seconds**' in paragraph
        assert '`date +%s`' in paragraph
        assert 'never an ISO-8601 string' in paragraph

    def test_every_other_hold_start_site_points_at_the_binding(self) -> None:
        # Population: every marketplace doc naming {hold_start}, derived by scan.
        docs = _marketplace_docs()
        sites = {path: text for path, text in docs.items() if path != _BRANCH_CLEANUP_DOC and _HOLD_START_TOKEN in text}

        assert sites, 'no doc outside branch-cleanup.md names {hold_start} — the scan matched nothing'
        unanchored = {str(path): _unanchored_paragraphs(text, _HOLD_START_TOKEN) for path, text in sites.items()}
        assert {path: found for path, found in unanchored.items() if found} == {}

    def test_a_paragraph_defining_its_own_shape_is_flagged(self) -> None:
        anchored = 'Elapsed is `date +%s` minus `{hold_start}` (bound in `branch-cleanup.md` invariant 2).'
        competing = 'The orchestrator records the wall-clock instant of acquire as `{hold_start}`.'

        assert _unanchored_paragraphs(f'{anchored}\n\n{competing}', _HOLD_START_TOKEN) == [competing]


class TestBlockedAdmissionReclaimBinding:
    """The waiter-side reclaim passes a value a BLOCKED waiter actually has bound."""

    def test_reclaim_call_passes_admission_wait_start_not_hold_start(self) -> None:
        paragraph = _invariant_two_paragraph(_BRANCH_CLEANUP_DOC.read_text(encoding='utf-8'))
        reclaim_calls = re.findall(r'merge_lock budget-reclaim.*?--hold-budget-seconds', paragraph, flags=re.DOTALL)

        assert reclaim_calls, 'invariant 2 carries no budget-reclaim invocation — the scan matched nothing'
        assert all(f'--hold-start {_ADMISSION_WAIT_START_TOKEN}' in call for call in reclaim_calls)
        assert all(f'--hold-start {_HOLD_START_TOKEN}' not in call for call in reclaim_calls)

    def test_invariant_two_binds_admission_wait_start_as_date_epoch_seconds(self) -> None:
        paragraph = _invariant_two_paragraph(_BRANCH_CLEANUP_DOC.read_text(encoding='utf-8'))

        assert (
            f"The reclaim's `--hold-start` is therefore `{_ADMISSION_WAIT_START_TOKEN}`: the waiter's own "
            'acquire-wait start as an **integer POSIX epoch in seconds**'
        ) in paragraph
        assert f'This is the one binding of `{_ADMISSION_WAIT_START_TOKEN}`.' in paragraph
        # Bound BEFORE the first acquire, so every blocked poll that reaches the reclaim has it.
        assert 'immediately before the first `acquire` of the FIFO poll loop' in paragraph

    def test_every_other_admission_wait_start_site_points_at_the_binding(self) -> None:
        # Population: every marketplace doc naming {admission_wait_start}, derived by scan —
        # including branch-cleanup.md itself outside the invariant-2 binding.
        binding = _invariant_two_paragraph(_BRANCH_CLEANUP_DOC.read_text(encoding='utf-8'))
        sites: dict[str, list[str]] = {}
        for path, text in _marketplace_docs().items():
            if _ADMISSION_WAIT_START_TOKEN not in text:
                continue
            same_document = path == _BRANCH_CLEANUP_DOC
            remainder = text.replace(binding, '') if same_document else text
            sites[str(path)] = _unanchored_paragraphs(
                remainder, _ADMISSION_WAIT_START_TOKEN, same_document=same_document
            )

        assert str(_BRANCH_CLEANUP_DOC) in sites, 'branch-cleanup.md no longer names {admission_wait_start}'
        assert len(sites) > 1, (
            'no doc outside branch-cleanup.md names {admission_wait_start} — the scan matched nothing'
        )
        assert {path: found for path, found in sites.items() if found} == {}


def _marketplace_docs() -> dict[Path, str]:
    """Return every marketplace markdown doc keyed by path."""
    return {path: path.read_text(encoding='utf-8') for path in sorted(MARKETPLACE_ROOT.rglob('*.md'))}


def _unanchored_paragraphs(text: str, token: str, *, same_document: bool = False) -> list[str]:
    """Return every paragraph naming ``token`` without citing its binding.

    A paragraph cites the binding when it names invariant 2 — the one place the
    shape is defined — and, outside ``branch-cleanup.md`` itself, also names
    ``branch-cleanup.md``.
    """
    return [
        paragraph
        for paragraph in re.split(r'\n\s*\n', text)
        if token in paragraph
        and not ('invariant 2' in paragraph and (same_document or 'branch-cleanup.md' in paragraph))
    ]

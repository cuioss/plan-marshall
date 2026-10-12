#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc-contract tests for the archive-plan step's refusal branch.

``manage-status archive`` refuses with ``status: error`` and exit code ``0``
(``error: blocking_findings_present`` / ``error: phases_unexaminable``), so the
step body in ``archive-plan.md`` is the only thing that can tell a refused
archive from a successful one. These tests pin that the § Archive section parses
the refusal BEFORE the "Plan archived" log line, re-records the step ``failed``
over its provisional ``done`` record, and forbids the session-store sweep on the
refusal path.
"""

from pathlib import Path

from conftest import MARKETPLACE_ROOT

_ARCHIVE_PLAN_DOC: Path = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'standards' / 'archive-plan.md'
)

_ARCHIVED_LOG_MESSAGE = 'Plan archived: {plan_id}'


def _section(heading: str) -> str:
    """Return the body of the ``## {heading}`` section, up to the next ``## `` heading."""
    text = _ARCHIVE_PLAN_DOC.read_text(encoding='utf-8')
    marker = f'\n## {heading}\n'
    start = text.index(marker) + len(marker)
    end = text.find('\n## ', start)
    return text[start:] if end == -1 else text[start:end]


def _refusal_branch(archive: str) -> str:
    """Return the § Archive text that precedes the archive log line — the refusal branch."""
    return archive[: archive.index(_ARCHIVED_LOG_MESSAGE)]


def test_archive_section_carries_the_archive_log_line():
    """Anchor: the log line the refusal branch must precede is present exactly once."""
    archive = _section('Archive')

    assert archive.count(_ARCHIVED_LOG_MESSAGE) == 1


def test_both_named_refusals_are_branched_before_the_archive_log_line():
    """The blocking-findings and unexaminable-phases refusals are handled BEFORE
    anything claims the plan was archived."""
    refusal = _refusal_branch(_section('Archive'))

    assert 'blocking_findings_present' in refusal
    assert 'phases_unexaminable' in refusal
    assert 'status: error' in refusal


def test_refusal_branch_rerecords_the_step_failed():
    """The refusal branch overwrites the provisional ``done`` record with ``failed``."""
    refusal = _refusal_branch(_section('Archive'))

    assert 'mark-step-done' in refusal
    assert '--step archive-plan --outcome failed' in refusal
    assert '--display-detail "archive refused: {error}"' in refusal


def test_refusal_branch_forbids_the_log_and_the_sweep():
    """A refused archive moved nothing, so neither the archive log nor the sweep runs."""
    refusal = _refusal_branch(_section('Archive'))

    assert 'STOP' in refusal
    assert 'do NOT run "Sweep the session-binding store"' in refusal
    assert 'Do NOT emit the archive log line' in refusal


def test_refusal_branch_returns_the_refusal_payload_verbatim():
    """The dispatcher receives the refusal payload fields, not a paraphrase."""
    refusal = _refusal_branch(_section('Archive'))

    assert 'verbatim' in refusal
    for field in ('blocking_count', 'blocking_types', 'per_type', 'unexaminable'):
        assert f'`{field}`' in refusal


def test_mark_step_complete_states_the_done_record_is_provisional():
    """§ Mark Step Complete names the ``done`` record provisional until the archive succeeds."""
    mark = _section('Mark Step Complete')

    assert 'provisional' in mark
    assert 'done → failed' in mark
    assert 'still resolves' in mark

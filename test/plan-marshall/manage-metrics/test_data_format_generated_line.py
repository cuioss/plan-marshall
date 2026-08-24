# SPDX-License-Identifier: FSL-1.1-ALv2
"""``data-format.md`` documents the report's one rendered timestamp (D8).

``metrics.md`` carries exactly one absolute wall-clock value — the ``Generated:``
line — and it is the only figure in the report that passes through the
display-only timezone knob. The standard's worked example omitted it entirely, so
a reader comparing the documented report against a real one found a line the
contract never mentioned, and nothing told them that this single line is the
knob's whole reach into the report.

Every assertion here binds the DOC to the EMITTER rather than to another document.
That direction is deliberate: a doc-to-doc check is a closed loop that agrees with
itself while the code walks away from both (lesson ``2026-08-08-20-001``). The
emitter is ``manage-metrics.py``'s report builder, and its literals are read from
source here.
"""

from __future__ import annotations

import re
from pathlib import Path

# test/plan-marshall/manage-metrics/<this file>
REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = REPO_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills'
DATA_FORMAT = SKILL_ROOT / 'manage-metrics' / 'standards' / 'data-format.md'
EMITTER = SKILL_ROOT / 'manage-metrics' / 'scripts' / 'manage-metrics.py'
RUN_CONFIG_STANDARD = SKILL_ROOT / 'manage-run-config' / 'standards' / 'run-config-standard.md'

#: The rendered shape the emitter produces: the strftime pattern
#: ``%Y-%m-%d %H:%M:%S`` followed by the default ``" UTC"`` suffix.
_GENERATED_LINE_RE = re.compile(r'^Generated: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC$')


def _doc_text() -> str:
    return DATA_FORMAT.read_text(encoding='utf-8')


def _emitter_text() -> str:
    return EMITTER.read_text(encoding='utf-8')


def test_emitter_still_renders_a_generated_line_through_the_knob() -> None:
    """Precondition for every assertion below — the emitter still behaves as documented.

    If this fails, the doc is not wrong; the contract moved. Asserting it first
    means a later failure in this module points at the doc rather than sending the
    reader hunting through the emitter.
    """
    text = _emitter_text()
    assert "f'Generated: {render_timestamp(" in text, (
        'manage-metrics.py no longer builds its Generated: line through render_timestamp(...). '
        'The doc claim that this line renders through the display-only timezone is now false, '
        'and data-format.md must be corrected rather than this test relaxed.'
    )
    assert '"%Y-%m-%d %H:%M:%S", " UTC"' in text, (
        'The Generated: line no longer renders with the %Y-%m-%d %H:%M:%S / " UTC" pair the '
        'documented example shows.'
    )


def test_worked_example_shows_the_generated_line() -> None:
    """The worked example carries a ``Generated:`` line in the emitter's own shape."""
    lines = [ln.strip() for ln in _doc_text().splitlines()]
    generated = [ln for ln in lines if ln.startswith('Generated:')]

    assert generated, (
        "data-format.md's Generated Report (metrics.md) worked example shows no Generated: "
        'line, so the report it documents is missing its only absolute timestamp.'
    )
    for line in generated:
        assert _GENERATED_LINE_RE.match(line), (
            f'Documented Generated: line {line!r} does not match the shape the emitter renders '
            '(%Y-%m-%d %H:%M:%S followed by " UTC").'
        )


def test_worked_example_heading_matches_the_emitter() -> None:
    """The example's report heading is the one the emitter actually writes."""
    assert "f'# Metrics: {plan_id}'" in _emitter_text(), (
        'The emitter no longer writes a "# Metrics: {plan_id}" heading — update this test '
        'and the worked example together.'
    )
    assert '# Metrics: my-feature' in _doc_text(), (
        "The worked example's heading does not match the emitter's "
        '"# Metrics: {plan_id}" line.'
    )


def test_doc_states_the_display_timezone_semantics_and_cross_references_the_knob() -> None:
    """The doc says the line renders through the display-only zone, and where that is defined.

    Three claims, each load-bearing: that the knob is display-only, that a
    converted instant carries the ``ABBREV (UTC±HH:MM)`` label, and a pointer to
    the section that owns the knob — so the reader is not left to infer the
    boundary from the example alone.
    """
    text = _doc_text()

    assert 'display-only' in text, (
        'data-format.md does not state that the timezone the Generated: line renders through '
        'is display-only, so a reader cannot tell that storage and comparison stay UTC.'
    )
    assert 'ABBREV (UTC±HH:MM)' in text, (
        'data-format.md does not state the label a CONVERTED timestamp carries, so a reader '
        'seeing a non-UTC Generated: line cannot recover the instant.'
    )
    assert 'Display-Timezone Section' in text, (
        'data-format.md does not cross-reference run-config-standard.md § Display-Timezone '
        'Section, which owns the knob.'
    )


def test_cross_reference_target_exists() -> None:
    """The cross-referenced section is really there — a dangling xref documents nothing."""
    assert RUN_CONFIG_STANDARD.is_file(), f'{RUN_CONFIG_STANDARD} does not exist.'
    assert '## Display-Timezone Section' in RUN_CONFIG_STANDARD.read_text(encoding='utf-8'), (
        'run-config-standard.md carries no "## Display-Timezone Section" heading, so the '
        'cross-reference in data-format.md points at nothing.'
    )

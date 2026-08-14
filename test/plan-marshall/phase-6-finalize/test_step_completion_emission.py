# SPDX-License-Identifier: FSL-1.1-ALv2
"""The finalize completion marker is FUSED to the mark-step-done handshake.

``phase-6-finalize/SKILL.md`` used to pair every terminal ``mark-step-done`` with a
separately hand-written ``[STEP] … Completed step:`` emit — a convention the loop
enforced site by site, and one that could drift toward silence: the step-completion
invariant is satisfied by the handshake ALONE, so a step could record its outcome
and leave no operational-log trace. The completion line is now emitted by
``mark-step-done`` itself (``_cmd_mark_step.py::_emit_completion_marker``, scoped to
the ``6-finalize`` phase), so recording a step's outcome and emitting its line are
ONE action that cannot diverge.

This detector derives its population from the document — the Step-3 FOR-loop body,
split into its numbered item blocks (``1.``, ``4b.``, ``5d.``, ``7a.`` …) — and
pins the fusion's two structural invariants:

* **No hand-written completion emit survives.** A reintroduced
  ``--message "[STEP] … Completed step:"`` in the loop is the drift-prone
  per-handler pattern this deliverable removed; the fusion owns the emission.
* **No terminal-exit block suppresses the fused emission.** A block that records a
  terminal outcome AND then leaves the iteration (a Signal-Gate ``CONTINUE``, the
  dispatch-timeout ``continue``, the 5d ``HALT``) reaches the fused emission
  through its ``mark-step-done`` write — UNLESS it carries ``--no-completion-log``,
  which would make it record, leave, and emit nothing: the exact silent gap the
  fusion closes. ``--no-completion-log`` is legitimate ONLY on the item-5f
  ``head_at_completion`` re-stamp, which FALLS THROUGH to item 6/7 rather than
  leaving the iteration, so it is never in the terminal-exit population.

The non-degeneracy anchor pins that the enumeration still finds the known
record-then-leave sites and that the suppression flag is actually present (on the
fall-through re-stamp); the mutation guards pin that both detectors fire on their
regression shapes. Without them a segmentation typo or a dead regex would make the
sweeps vacuous.

The heading-bounded walk is the shared one in ``test/_shared/_dispatch_roster.py``
(``section_lines``); this file adds no private copy.
"""

from __future__ import annotations

import re

from _dispatch_roster import section_lines

from conftest import MARKETPLACE_ROOT

_SKILL_DOC = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'SKILL.md'
)

_STEP_3_HEADING = (
    '### Step 3: Execute Step Pipeline (Manifest-Driven, Resumable, Timeout-Wrapped)'
)
_STEP_3_STOP_PREFIXES = ('### ', '## ')

#: The FOR statement that opens the dispatch loop body.
_FOR_LOOP_RE = re.compile(r'^\s*FOR each step_id in manifest\.phase_6\.steps:')

#: An item marker inside the loop body: ``1.``, ``4b.``, ``5d.``, ``7a.`` …
#: Lettered sub-bullets (``a.``, ``b.``) deliberately do NOT match, so a sub-bullet
#: stays inside its parent item's block.
_ITEM_MARKER_RE = re.compile(r'^\s{0,6}(?P<item>\d+[a-z]?)\.\s')

#: A terminal-outcome recording for this phase.
_MARK_STEP_DONE_RE = re.compile(r'mark-step-done\b[\s\S]{0,300}?--phase\s+6-finalize\b')

#: A block leaves the iteration when it hands control away rather than falling
#: through to item 6/7.
_LEAVES_ITERATION_RE = re.compile(
    r'\b(?:CONTINUE|HALT)\s+the\s+FOR\s+loop|continue\s+the\s+FOR\s+loop'
    r'|[Cc]ontinue\s+to\s+the\s+next\s+step\s+in\s+the\s+loop',
)

#: A hand-written completion emit — the FORBIDDEN pre-fusion shape. Now that
#: ``mark-step-done`` emits the line, a hand-written one is the per-handler
#: convention the fusion replaced (and would double-emit).
_HAND_WRITTEN_COMPLETION_RE = re.compile(r'--message\s+"\[STEP\][^"]*Completed step:')

#: The suppression flag. It belongs ONLY on the item-5f re-stamp (a fall-through
#: block); on a record-then-leave block it silences the step. Matched only when it
#: sits on an actual ``mark-step-done`` command span (below), never on a prose
#: MENTION of the flag — items 7 and 7a legitimately discuss it in prose.
_NO_COMPLETION_LOG_RE = re.compile(r'--no-completion-log\b')


def _skill_text() -> str:
    text: str = _SKILL_DOC.read_text(encoding='utf-8')
    return text


def _loop_body(text: str) -> str:
    """Return the Step-3 FOR-loop body — the region the item blocks live in."""
    section = section_lines(text, _STEP_3_HEADING, _STEP_3_STOP_PREFIXES)
    for index, line in enumerate(section):
        if _FOR_LOOP_RE.match(line):
            return '\n'.join(section[index + 1 :])
    raise AssertionError('Step 3 carries no `FOR each step_id` loop body')


def _item_blocks(body: str) -> dict[str, str]:
    """Split a loop body into ``{item_marker: block_text}``, in document order."""
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for line in body.splitlines():
        match = _ITEM_MARKER_RE.match(line)
        if match:
            current = match.group('item')
            blocks.setdefault(current, [])
        if current is not None:
            blocks[current].append(line)
    return {item: '\n'.join(lines) for item, lines in blocks.items()}


def _terminal_exit_blocks(blocks: dict[str, str]) -> dict[str, str]:
    """Return the blocks that record a terminal outcome AND leave the iteration."""
    return {
        item: block
        for item, block in blocks.items()
        if _MARK_STEP_DONE_RE.search(block) and _LEAVES_ITERATION_RE.search(block)
    }


def _hand_written_completion_emits(text: str) -> list[str]:
    """Return every hand-written ``[STEP] … Completed step:`` emit line."""
    return [
        f'{index + 1}: {line.strip()!r}'
        for index, line in enumerate(text.splitlines())
        if _HAND_WRITTEN_COMPLETION_RE.search(line)
    ]


def _block_suppresses_via_mark_step_done(block: str) -> bool:
    """Whether the block passes ``--no-completion-log`` to a mark-step-done command.

    Distinguishes an actual flag on an invocation from a prose MENTION of the flag
    by requiring it to sit inside a ``mark-step-done`` command span — the
    invocation line plus its backslash-continued argument lines — carrying
    ``--phase 6-finalize``. Items 7 and 7a legitimately discuss the flag in prose;
    only a real command usage silences a step.
    """
    lines = block.splitlines()
    for index, line in enumerate(lines):
        if 'mark-step-done' not in line:
            continue
        span = [line]
        cursor = index
        while lines[cursor].rstrip().endswith('\\') and cursor + 1 < len(lines):
            cursor += 1
            span.append(lines[cursor])
        span_text = '\n'.join(span)
        if '--phase 6-finalize' in span_text and _NO_COMPLETION_LOG_RE.search(span_text):
            return True
    return False


def _blocks_using_the_suppression_flag(blocks: dict[str, str]) -> list[str]:
    """Return item markers whose block passes ``--no-completion-log`` on a command."""
    return sorted(
        item for item, block in blocks.items() if _block_suppresses_via_mark_step_done(block)
    )


def _terminal_exits_suppressing_emission(blocks: dict[str, str]) -> list[str]:
    """Return terminal-exit item markers whose command carries ``--no-completion-log``.

    A block that records a terminal outcome, leaves the iteration, AND passes the
    suppression flag to that recording records-and-leaves with no completion line —
    the silent gap the fusion exists to close.
    """
    return sorted(
        item
        for item, block in _terminal_exit_blocks(blocks).items()
        if _block_suppresses_via_mark_step_done(block)
    )


class TestPopulationIsNonDegenerate:
    """A collapsed enumeration or a dead regex would make the sweeps vacuous."""

    def test_loop_body_splits_into_item_blocks(self):
        blocks = _item_blocks(_loop_body(_skill_text()))

        assert blocks, 'The Step-3 FOR-loop body split into zero item blocks'

    def test_enumeration_finds_the_known_bypass_sites(self):
        # The two Signal-Gate skips (4b, 4c), the dispatch-timeout path (item 5,
        # which records outcome=failed and continues without reaching item 7), and
        # the post-dispatch-guard HALT (5d) are the known record-then-leave sites.
        # An enumeration that no longer sees them is not enumerating the loop.
        terminal_exit = _terminal_exit_blocks(_item_blocks(_loop_body(_skill_text())))

        for item in ('4b', '4c', '5', '5d'):
            assert item in terminal_exit, (
                f'Item {item} records a terminal outcome and leaves the iteration, but '
                f'the enumeration did not classify it as such — the completeness sweep '
                f'would silently skip it'
            )

    def test_re_stamp_uses_the_suppression_flag_and_is_not_a_terminal_exit(self):
        # The suppression flag must be present on a real command (or the suppress
        # detector is dead), and it must live ONLY on a block that FALLS THROUGH —
        # the item-5f head_at_completion re-stamp — never on a record-then-leave one.
        blocks = _item_blocks(_loop_body(_skill_text()))
        carriers = _blocks_using_the_suppression_flag(blocks)
        assert carriers, (
            'No --no-completion-log passed to a mark-step-done command in the Step-3 '
            'loop: either the re-stamp lost its suppression flag or the command-span '
            'detector went dead — the suppress sweep below would be vacuous'
        )
        # Every carrier falls through (records but does not leave the iteration), so
        # none is in the terminal-exit population.
        assert _terminal_exits_suppressing_emission(blocks) == [], (
            f'A record-then-leave block passes --no-completion-log to its recording: '
            f'{carriers}. The flag belongs only on the fall-through item-5f re-stamp.'
        )


class TestFusionInvariants:
    """The completion line rides the handshake write, and nothing silences it."""

    def test_no_hand_written_completion_emit_survives(self):
        hand_written = _hand_written_completion_emits(_loop_body(_skill_text()))

        assert not hand_written, (
            f'Hand-written `[STEP] … Completed step:` emit(s) in the phase-6-finalize '
            f'Step-3 loop: {hand_written}. The completion line is fused to '
            f'mark-step-done now; a hand-written one is the per-handler drift pattern '
            f'this deliverable removed, and it double-emits.'
        )

    def test_no_terminal_exit_block_suppresses_the_fused_emission(self):
        suppressed = _terminal_exits_suppressing_emission(
            _item_blocks(_loop_body(_skill_text()))
        )

        assert not suppressed, (
            f'Item block(s) {suppressed} record a terminal step outcome, leave the '
            f'iteration, AND carry --no-completion-log — they record-and-leave with no '
            f'completion line, the exact silent gap the fusion closes. --no-completion-log '
            f'is legitimate only on the fall-through item-5f re-stamp.'
        )


class TestDetectorsBite:
    """Mutation guards — the sweeps must fire on their regression shapes."""

    def test_hand_written_emit_detector_fires(self):
        pre_fix = (
            '  4b. Lessons-capture Signal Gate:\n'
            '      python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \\\n'
            '        work --plan-id {plan_id} --level INFO --message "[STEP] '
            '(plan-marshall:phase-6-finalize) Completed step: {step_ref}"\n'
        )

        assert _hand_written_completion_emits(pre_fix), (
            'Hand-written-emit detector failed to flag the known pre-fusion emit line '
            '— the fusion sweep would be vacuous'
        )
        # The fused-emission prose (no --message "[STEP] …") must NOT match.
        post_fix = (
            '      The `outcome=skipped` recording above already emitted this step\'s\n'
            '      `[STEP] … Completed step:` line: `mark-step-done` fuses that line.\n'
        )
        assert not _hand_written_completion_emits(post_fix)

    def test_suppress_on_terminal_exit_detector_fires(self):
        # A synthetic block that records, suppresses, AND leaves the iteration — the
        # silent-gap regression the suppress sweep exists to catch.
        offending = _item_blocks(
            '  9z. Synthetic record-then-leave with suppression:\n'
            '      python3 .plan/execute-script.py plan-marshall:manage-status:manage-status '
            'mark-step-done \\\n'
            '        --plan-id {plan_id} --phase 6-finalize --step x --outcome failed '
            '--no-completion-log\n'
            '      HALT the FOR loop.\n'
        )
        assert _terminal_exits_suppressing_emission(offending) == ['9z'], (
            'Suppress-on-terminal-exit detector failed to flag a record-then-leave '
            'block carrying --no-completion-log'
        )

        # The same block WITHOUT the flag reaches the fused emission — not flagged.
        clean = _item_blocks(
            '  9z. Synthetic record-then-leave (fused emission fires):\n'
            '      python3 .plan/execute-script.py plan-marshall:manage-status:manage-status '
            'mark-step-done \\\n'
            '        --plan-id {plan_id} --phase 6-finalize --step x --outcome failed\n'
            '      HALT the FOR loop.\n'
        )
        assert _terminal_exits_suppressing_emission(clean) == []

        # A fall-through re-stamp carrying the flag is NOT a terminal-exit, so it is
        # never flagged — the item-5f shape.
        fall_through = _item_blocks(
            '  5f. Re-stamp head_at_completion (falls through to item 6):\n'
            '      python3 .plan/execute-script.py plan-marshall:manage-status:manage-status '
            'mark-step-done \\\n'
            '        --plan-id {plan_id} --phase 6-finalize --step x --outcome done '
            '--head-at-completion {sha} --no-completion-log\n'
            '      proceed to item 6.\n'
        )
        assert _terminal_exits_suppressing_emission(fall_through) == []

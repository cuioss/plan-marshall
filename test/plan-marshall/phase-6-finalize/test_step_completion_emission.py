# SPDX-License-Identifier: FSL-1.1-ALv2
"""Per-step completion-emission detector for the phase-6-finalize dispatch loop.

``phase-6-finalize/SKILL.md`` item 7 states the pairing contract: recording a
step's terminal outcome and emitting its
``[STEP] (plan-marshall:phase-6-finalize) Completed step: {step_ref}`` line are
ONE indivisible pair. The contract is easy to state and easy to bypass — every
loop path that records an outcome and then LEAVES the iteration (a Signal-Gate
``CONTINUE``, the post-dispatch-guard ``HALT``, the per-agent-timeout
``continue``) skips past item 7, so the line is emitted at that site or never at
all. Each such bypass silently removes one step from per-step completion
coverage while the happy path stays green.

This detector derives its population from the document:

* Split the Step-3 FOR-loop body into its numbered item blocks (``1.``, ``4b.``,
  ``5d.``, ``7a.``, …) — the loop's own structure, not a hand-listed set.
* Keep the blocks that record a terminal outcome (a ``manage-status
  mark-step-done`` invocation carrying ``--phase 6-finalize``) AND then leave the
  iteration (``CONTINUE``/``HALT`` the FOR loop, or continue to the next step).
  A block that records an outcome and falls through reaches item 7's emission, so
  it is correctly not in the population.
* Require each block in that population to carry either the completion emission
  or an explicit **named exemption**. The exemption marker is read from the
  document — this file hardcodes no exempt-block list.

The non-degeneracy anchor pins that the enumeration finds the known bypass sites,
and the bites-check pins that a block with neither an emission nor an exemption
is flagged — without them a segmentation typo would make the sweep vacuous.

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

#: The completion emission the pairing contract requires.
_COMPLETION_EMISSION_RE = re.compile(
    r'\[STEP\]\s*\(plan-marshall:phase-6-finalize\)\s*Completed step:'
)

#: The explicit, named exemption a block may carry instead of the emission. The
#: marker is the contract surface — the exempt SET is whatever the document marks,
#: never a list maintained here.
_NAMED_EXEMPTION_RE = re.compile(r'\*\*Named exemption\b')

#: A block leaves the iteration when it hands control away rather than falling
#: through to item 7.
_LEAVES_ITERATION_RE = re.compile(
    r'\b(?:CONTINUE|HALT)\s+the\s+FOR\s+loop|continue\s+the\s+FOR\s+loop'
    r'|[Cc]ontinue\s+to\s+the\s+next\s+step\s+in\s+the\s+loop',
)


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


def _unpaired_blocks(blocks: dict[str, str]) -> list[str]:
    """Return the item markers whose block has neither an emission nor an exemption."""
    return sorted(
        item
        for item, block in _terminal_exit_blocks(blocks).items()
        if not _COMPLETION_EMISSION_RE.search(block)
        and not _NAMED_EXEMPTION_RE.search(block)
    )


class TestPopulationIsNonDegenerate:
    """A collapsed enumeration would make the sweep below vacuously green."""

    def test_loop_body_splits_into_item_blocks(self):
        blocks = _item_blocks(_loop_body(_skill_text()))

        assert blocks, 'The Step-3 FOR-loop body split into zero item blocks'

    def test_enumeration_finds_the_known_bypass_sites(self):
        # Anchors: the post-dispatch-guard HALT (item 5d), the dispatch-timeout
        # path (item 5, which records outcome=failed and CONTINUEs without
        # reaching item 7), and the two Signal-Gate skips (items 4b and 4c) are
        # the known record-then-leave sites. An enumeration that no longer sees
        # them is not enumerating the loop.
        terminal_exit = _terminal_exit_blocks(_item_blocks(_loop_body(_skill_text())))

        for item in ('4b', '4c', '5', '5d'):
            assert item in terminal_exit, (
                f'Item {item} records a terminal outcome and leaves the iteration, but '
                f'the enumeration did not classify it as such — the completeness sweep '
                f'would silently skip it'
            )

    def test_document_carries_at_least_one_named_exemption(self):
        # The exemption set is read from the document; if the marker regex stopped
        # matching, every exempt block would report as unpaired and the sweep's
        # green/red signal would stop meaning anything.
        assert _NAMED_EXEMPTION_RE.search(_skill_text()), (
            'No named exemption marker found in phase-6-finalize/SKILL.md — the '
            'exemption half of the contract is unreadable'
        )


class TestEveryTerminalExitSiteEmitsOrIsExempt:
    """The pairing contract holds on every record-then-leave path."""

    def test_no_terminal_exit_block_is_unpaired(self):
        unpaired = _unpaired_blocks(_item_blocks(_loop_body(_skill_text())))

        assert not unpaired, (
            f'Item block(s) {unpaired} record a terminal step outcome and then leave '
            f'the iteration WITHOUT emitting the `[STEP] (plan-marshall:phase-6-finalize) '
            f'Completed step:` line and WITHOUT carrying a named exemption. Each such '
            f'block silently drops one step from per-step completion coverage — the '
            f'retrospective reads the step as never having run.'
        )


class TestDetectorBites:
    """Mutation guards — the sweep must fail on the pre-fix shape."""

    def test_unpaired_block_is_flagged(self):
        pre_fix = _item_blocks(
            '  4b. Lessons-capture Signal Gate:\n'
            '      - Mark the step done with outcome=skipped:\n'
            '        python3 .plan/execute-script.py plan-marshall:manage-status:manage-status '
            'mark-step-done \\\n'
            '          --plan-id {plan_id} --phase 6-finalize --step lessons-capture '
            '--outcome skipped\n'
            '      - CONTINUE the FOR loop (skip item 5 dispatch entirely for this step).\n'
        )

        assert '4b' in _terminal_exit_blocks(pre_fix), (
            'The record-then-leave classifier failed to see the known pre-fix '
            'Signal-Gate skip — the sweep would be vacuous'
        )
        assert _unpaired_blocks(pre_fix) == ['4b'], (
            'The sweep failed to flag a block that records a terminal outcome and '
            'leaves the iteration with neither an emission nor an exemption'
        )

    def test_emission_and_exemption_each_clear_a_block(self):
        recorded = (
            '  9z. Synthetic item:\n'
            '      python3 .plan/execute-script.py plan-marshall:manage-status:manage-status '
            'mark-step-done --plan-id {plan_id} --phase 6-finalize --outcome failed\n'
            '      HALT the FOR loop.\n'
        )

        emitting = _item_blocks(
            recorded.replace(
                '      HALT the FOR loop.\n',
                '      --message "[STEP] (plan-marshall:phase-6-finalize) Completed step: '
                '{step_ref}"\n      HALT the FOR loop.\n',
            )
        )
        exempting = _item_blocks(
            recorded.replace(
                '      HALT the FOR loop.\n',
                '      **Named exemption — the emission already fired upstream.**\n'
                '      HALT the FOR loop.\n',
            )
        )

        assert _unpaired_blocks(_item_blocks(recorded)) == ['9z']
        assert _unpaired_blocks(emitting) == []
        assert _unpaired_blocks(exempting) == []

    def test_a_block_that_falls_through_is_not_in_the_population(self):
        # Recording an outcome without leaving the iteration reaches item 7's
        # emission, so it must NOT be demanded to emit for itself — otherwise the
        # sweep would force a double emission.
        falls_through = _item_blocks(
            '  5f. Commit instrumentation:\n'
            '      python3 .plan/execute-script.py plan-marshall:manage-status:manage-status '
            'mark-step-done --plan-id {plan_id} --phase 6-finalize --outcome done\n'
        )

        assert _terminal_exit_blocks(falls_through) == {}
        assert _unpaired_blocks(falls_through) == []

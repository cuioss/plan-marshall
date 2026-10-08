#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc-contract test: every dispatcher-written ``failed`` record parses its result.

``phase-6-finalize/SKILL.md`` has the dispatcher itself write a ``failed`` step
record on the paths where the step cannot write its own — the per-agent timeout,
the missing-terminal-record guard, and the ``wait_failed`` strict-mode
precondition. ``manage-status mark-step-done`` can refuse that write, and a
dispatcher that does not read the result continues as though the failure had been
recorded. Each such block must therefore be followed by the result parse: read
the returned ``status`` and, on anything other than ``success``, log the returned
error at ERROR and STOP.

The block population is **derived, never hardcoded**: every dispatcher-side
``mark-step-done ... --outcome failed`` instruction is located in the document at
test time, so a newly added failed-mark block is covered without editing this
file. Two guards keep the sweep honest:

* the derived count is asserted to be at least three, so an empty derivation
  cannot pass vacuously;
* the mutation guards run the same detector over a block that lacks the parse
  and expect a hit, so a detector that matches nothing fails here rather than
  reporting a clean document.
"""

from __future__ import annotations

import re

from conftest import MARKETPLACE_ROOT

_SKILL_DOC = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'SKILL.md'

_OUTCOME_FAILED = '--outcome failed'
_MARK_VERB = 'mark-step-done'

# How far above an argument-continuation line the command line naming the verb
# may sit (the verb line, then the ``--plan-id`` line carrying the outcome).
_COMMAND_LOOKBACK = 3

# How many lines after a block the parse may start within. The table-row form
# needs the most room: the rest of its table, a blank line, the parse sentence
# and the fenced log command.
_PARSE_WINDOW = 12

_PARSE_RE = re.compile(
    r'read the returned `status`.*?other than `success`.*?`error`.*?`message`.*?\bSTOP\b',
    re.IGNORECASE | re.DOTALL,
)
_ERROR_LOG_RE = re.compile(r'--level ERROR\b.*?\{error\}.*?\{message\}', re.DOTALL)


def derive_failed_mark_blocks(lines: list[str]) -> list[int]:
    """Return the 0-based index of every dispatcher-side failed-mark instruction.

    Two shapes are instructions; a prose sentence that merely mentions the call
    is neither:

    * a **command** — an argument-continuation line carrying ``--outcome failed``
      whose command line (naming ``mark-step-done``) sits just above it;
    * a **table row** — an outcome-mapping row naming both the verb and
      ``--outcome failed`` as the dispatcher action.
    """
    blocks: list[int] = []
    for index, line in enumerate(lines):
        if _OUTCOME_FAILED not in line:
            continue
        stripped = line.strip()
        if stripped.startswith('|'):
            if _MARK_VERB in line:
                blocks.append(index)
            continue
        if not stripped.startswith('--'):
            continue
        lookback = lines[max(0, index - _COMMAND_LOOKBACK) : index]
        if any(_MARK_VERB in previous and 'execute-script.py' in previous for previous in lookback):
            blocks.append(index)
    return blocks


def blocks_missing_parse(lines: list[str]) -> list[int]:
    """Return the 1-based line number of every failed-mark block lacking the parse.

    A block's window ends at the next block, so one parse cannot vouch for two
    marks.
    """
    blocks = derive_failed_mark_blocks(lines)
    missing: list[int] = []
    for position, index in enumerate(blocks):
        end = index + 1 + _PARSE_WINDOW
        if position + 1 < len(blocks):
            end = min(end, blocks[position + 1])
        window = '\n'.join(lines[index + 1 : end])
        if not (_PARSE_RE.search(window) and _ERROR_LOG_RE.search(window)):
            missing.append(index + 1)
    return missing


_MARK_COMMAND = [
    '        a. Record the violation:',
    '           python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \\',
    '             --plan-id {plan_id} --phase 6-finalize --step {step_id} --outcome failed \\',
    '             --display-detail "some detail"',
]

_PARSE_BLOCK = [
    '',
    '           **Parse the failed-record result.** Read the returned `status`. On anything',
    '           other than `success`, log the returned `error` and `message` at ERROR and STOP —',
    '           do NOT continue as though the failure had been recorded:',
    '           python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \\',
    '             work --plan-id {plan_id} --level ERROR --message "refused: {error} — {message}"',
]


def _skill_lines() -> list[str]:
    text: str = _SKILL_DOC.read_text(encoding='utf-8')
    return text.splitlines()


def test_derivation_finds_every_dispatcher_failed_mark_block():
    """The derivation is non-empty: the three known dispatcher-side blocks exist."""
    # Arrange
    lines = _skill_lines()

    # Act
    blocks = derive_failed_mark_blocks(lines)

    # Assert
    assert len(blocks) >= 3, (
        f'expected at least three dispatcher-side failed-mark blocks in {_SKILL_DOC.name}, '
        f'derived {len(blocks)} at lines {[index + 1 for index in blocks]}'
    )


def test_derivation_covers_both_instruction_shapes():
    """Both shapes are present in the document, so neither branch is dead."""
    # Arrange
    lines = _skill_lines()

    # Act
    blocks = derive_failed_mark_blocks(lines)
    table_rows = [index for index in blocks if lines[index].strip().startswith('|')]
    commands = [index for index in blocks if not lines[index].strip().startswith('|')]

    # Assert
    assert table_rows, 'no table-row failed-mark instruction derived (the strict precondition row)'
    assert len(commands) >= 2, 'expected the timeout and missing-record command blocks'


def test_every_failed_mark_block_is_followed_by_the_result_parse():
    """No dispatcher-written failed record is left unparsed."""
    # Arrange
    lines = _skill_lines()

    # Act
    missing = blocks_missing_parse(lines)

    # Assert
    assert missing == [], (
        f'{_SKILL_DOC.name}: dispatcher-side `--outcome failed` mark at line(s) {missing} is not '
        'followed by the result parse (read the returned `status`; on anything other than '
        '`success`, log the returned `error` and `message` at ERROR and STOP)'
    )


def test_detector_flags_a_command_block_without_the_parse():
    """Mutation guard: a mark block with no parse after it is a hit."""
    # Arrange
    lines = [*_MARK_COMMAND, '        b. Log the attributed error:', '        c. HALT the FOR loop.']

    # Act
    missing = blocks_missing_parse(lines)

    # Assert
    assert missing == [3]


def test_detector_accepts_a_command_block_with_the_parse():
    """The positive control for the mutation guard above."""
    # Arrange
    lines = [*_MARK_COMMAND, *_PARSE_BLOCK, '        b. Log the attributed error:']

    # Act
    missing = blocks_missing_parse(lines)

    # Assert
    assert derive_failed_mark_blocks(lines) == [2]
    assert missing == []


def test_detector_flags_a_table_row_without_the_parse():
    """Mutation guard for the table-row shape."""
    # Arrange
    lines = [
        '| `wait_failed` | `failure` | `strict` | SKIP the body and mark via '
        '`manage-status mark-step-done … --outcome failed`. |',
        '| `wait_failed` | `timeout` | `strict` | Same skip-and-mark action. |',
        '',
        '**Per-signal arm outcome mapping**',
    ]

    # Act
    missing = blocks_missing_parse(lines)

    # Assert
    assert missing == [1]


def test_detector_requires_the_error_log_not_just_the_sentence():
    """A parse sentence with no ERROR log command is still a hit."""
    # Arrange — the sentence alone, without the log command that follows it.
    lines = [*_MARK_COMMAND, *_PARSE_BLOCK[:4], '        b. Log the attributed error:']

    # Act
    missing = blocks_missing_parse(lines)

    # Assert
    assert missing == [3]


def test_one_parse_does_not_vouch_for_two_blocks():
    """A block cannot borrow the parse that follows the next block."""
    # Arrange — two marks back to back; only the second is followed by a parse.
    lines = [*_MARK_COMMAND, *_MARK_COMMAND, *_PARSE_BLOCK]

    # Act
    missing = blocks_missing_parse(lines)

    # Assert
    assert derive_failed_mark_blocks(lines) == [2, 6]
    assert missing == [3]


def test_prose_mention_is_not_derived_as_a_block():
    """A sentence that only refers to the call is not an instruction to parse after."""
    # Arrange
    lines = [
        'In addition to the `mark-step-done … --outcome failed --display-detail "x"` call above, the',
        'dispatcher persists a finding immediately after the `mark-step-done … --outcome failed` call.',
    ]

    # Act
    blocks = derive_failed_mark_blocks(lines)

    # Assert
    assert blocks == []

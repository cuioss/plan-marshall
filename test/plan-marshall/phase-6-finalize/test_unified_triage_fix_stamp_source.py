#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Where the unified-triage hook takes a task fix's commit from.

A ``fixed`` review finding is answered only once a commit is stamped on it and
that commit is on the pull request. ``phase-6-finalize`` item 7c step (0) writes
the stamp for a fix a task produced.

The stamp source is the pushed head of the branch: once the fix task is ``done``
and ``branch-sync-state`` reports ``synced``, the hook stamps the payload's
``head_sha``. The change ledger is not a source. A ``kind=change`` record is
written per deliverable and carries no task id, so a procedure that looks a fix
task's commit up there by task id matches nothing, stamps nothing, and leaves the
finding held for good.

This suite pins the document side of that procedure. Every reader and both
detectors are exercised against synthetic text first — one text that carries the
ledger lookup, one that does not — so a detector that silently finds nothing
cannot make an assertion over the real document pass.
"""

from __future__ import annotations

import re

from conftest import get_skill_dir

_FINALIZE_SKILL = get_skill_dir('plan-marshall', 'phase-6-finalize') / 'SKILL.md'
_FEEDBACK_DOC = get_skill_dir('plan-marshall', 'plan-marshall') / 'workflow' / 'verification-feedback.md'
_GITHUB_SKILL = get_skill_dir('plan-marshall', 'workflow-integration-github') / 'SKILL.md'

#: Item 7c is a numbered entry of the indented step loop, not a heading. It runs
#: from its opening line to the line that closes the loop.
_ITEM_7C_START = '  7c. Wait-region unified triage hook'
_ITEM_7C_END = '\nEND FOR'

#: Step (0) of item 7c runs up to step (1).
_STEP_0_START = '      (0) **Stamp the pushed fix commits'
_STEP_0_END = '      (1) Resolve the level-bound target'

#: The two shapes step (0) handles. The task-fix branch runs up to the inline one.
_TASK_FIX_START = '- **A finding with a `fix_task_number`** (a task fix).'
_TASK_FIX_END = '- **A finding with no `fix_task_number`** (an inline fix).'

#: The block of item 7c that commits and stamps the triage's inline edits.
_INLINE_BLOCK_START = '**(4a) On every return, before anything is routed'
_INLINE_BLOCK_END = 'This hook is dispatcher-owned and produces NO'

#: Item 5f, which reads the change ledger for a different purpose.
_ITEM_5F_START = '  5f. Commit instrumentation'
_ITEM_5F_END = '  6. Capture archive result'

_STEP_8_HEADING = '## Step 8: Respond loop'

#: The flags ``manage-findings stamp-fix-commit`` declares.
_STAMP_FLAGS = frozenset({'--plan-id', '--commit-sha', '--task-number', '--hash-id'})

#: A line that reaches for the change ledger, or for a task id recorded in it.
_LEDGER_LOOKUP = re.compile(r'manage-change-ledger|kind=change|\bledger\b|\btask_id\b', re.IGNORECASE)

_FLAG = re.compile(r'--[a-z][a-z-]*')


def _between(text: str, start: str, end: str) -> str:
    """Return ``text`` from the single ``start`` marker up to the next ``end`` marker.

    An absent marker returns the empty string, and so does a repeated ``start``
    marker: ``str.index`` would take the first copy silently.
    """
    if text.count(start) != 1:
        return ''
    begin = text.index(start)
    stop = text.find(end, begin)
    if stop == -1:
        return ''
    return text[begin:stop]


def _commands(text: str) -> list[str]:
    """Every executor call in ``text``, with its continuation lines joined.

    A call starts on a line naming ``execute-script.py`` and runs on while the
    line ends in a backslash. Runs of whitespace collapse to one space.
    """
    found: list[str] = []
    current: list[str] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if current is None:
            if 'execute-script.py' not in stripped:
                continue
            current = []
        current.append(stripped.removesuffix('\\').strip())
        if not stripped.endswith('\\'):
            found.append(' '.join(current))
            current = None
    if current is not None:
        found.append(' '.join(current))
    return found


def _ledger_lookups(text: str) -> list[str]:
    """Every line of ``text`` that names the change ledger or a task id read from it."""
    return [line.strip() for line in text.splitlines() if _LEDGER_LOOKUP.search(line)]


def _stamp_calls(text: str) -> list[str]:
    """The ``stamp-fix-commit`` calls in ``text``."""
    return [command for command in _commands(text) if ' stamp-fix-commit ' in f'{command} ']


def _item_7c() -> str:
    return _between(_FINALIZE_SKILL.read_text(encoding='utf-8'), _ITEM_7C_START, _ITEM_7C_END)


def _step_0() -> str:
    return _between(_item_7c(), _STEP_0_START, _STEP_0_END)


def _task_fix_branch() -> str:
    return _between(_step_0(), _TASK_FIX_START, _TASK_FIX_END)


def _step_8() -> str:
    text: str = _FEEDBACK_DOC.read_text(encoding='utf-8')
    assert _STEP_8_HEADING in text, f'section heading missing: {_STEP_8_HEADING}'
    start = text.index(_STEP_8_HEADING)
    end = text.find('\n## ', start + len(_STEP_8_HEADING))
    return text[start:] if end == -1 else text[start:end]


#: A task-fix branch that takes the commit from the change ledger by task id.
_SYNTHETIC_LEDGER_BRANCH = """\
- **A finding with a `fix_task_number`** (a task fix). Read the task:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks read \\
    --plan-id {plan_id} --task-number {fix_task_number}
  ```

  The commit is the `kind=change` entry whose `task_id` is `TASK-{fix_task_number}`:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-change-ledger:manage-change-ledger query \\
    --kind change
  ```

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings stamp-fix-commit \\
    --plan-id {plan_id} --commit-sha {commit_sha} --task-number {fix_task_number}
  ```

  A `done` task with no ledger entry is not stamped.
"""

#: A task-fix branch that stamps from the pushed head. It uses the words "change"
#: and "task" where they do not name the ledger.
_SYNTHETIC_HEAD_BRANCH = """\
- **A finding with a `fix_task_number`** (a task fix). Read the task:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks read \\
    --plan-id {plan_id} --task-number {fix_task_number}
  ```

  ```bash
  python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow branch-sync-state \\
    --plan-id {plan_id}
  ```

  Stamp only on `state: synced`. A reviewer may see a change that is not the fix.

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings stamp-fix-commit \\
    --plan-id {plan_id} --commit-sha {pushed_head_sha} --task-number {fix_task_number}
  ```
"""


# ---------------------------------------------------------------------------
# The readers and detectors, against synthetic text
# ---------------------------------------------------------------------------


def test_between_returns_empty_for_an_absent_or_repeated_start_marker():
    assert _between('alpha beta gamma', 'alpha', 'gamma') == 'alpha beta '
    assert _between('alpha beta gamma', 'missing', 'gamma') == ''
    assert _between('alpha alpha gamma', 'alpha', 'gamma') == ''
    assert _between('alpha beta gamma', 'alpha', 'missing') == ''


def test_command_reader_joins_continuation_lines():
    commands = _commands(_SYNTHETIC_HEAD_BRANCH)

    assert commands == [
        'python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks read'
        ' --plan-id {plan_id} --task-number {fix_task_number}',
        'python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow branch-sync-state'
        ' --plan-id {plan_id}',
        'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings stamp-fix-commit'
        ' --plan-id {plan_id} --commit-sha {pushed_head_sha} --task-number {fix_task_number}',
    ]


def test_command_reader_returns_nothing_for_prose():
    assert _commands('Stamp only on `state: synced`.') == []


def test_ledger_detector_finds_the_lookup_by_task_id():
    """Positive control: the prose, the query call and the no-entry rule are all reported."""
    found = _ledger_lookups(_SYNTHETIC_LEDGER_BRANCH)

    assert found == [
        'The commit is the `kind=change` entry whose `task_id` is `TASK-{fix_task_number}`:',
        'python3 .plan/execute-script.py plan-marshall:manage-change-ledger:manage-change-ledger query \\',
        'A `done` task with no ledger entry is not stamped.',
    ], found


def test_ledger_detector_reports_nothing_for_a_branch_that_stamps_from_the_head():
    """Negative control: "change", "task" and ``fix_task_number`` alone are not a ledger lookup."""
    assert _ledger_lookups(_SYNTHETIC_HEAD_BRANCH) == []


def test_stamp_call_reader_tells_the_two_sources_apart():
    """The reader returns the call as written, so its commit placeholder can be compared."""
    from_ledger = _stamp_calls(_SYNTHETIC_LEDGER_BRANCH)
    from_head = _stamp_calls(_SYNTHETIC_HEAD_BRANCH)

    assert len(from_ledger) == 1
    assert len(from_head) == 1
    assert '--commit-sha {commit_sha}' in from_ledger[0]
    assert '--commit-sha {pushed_head_sha}' not in from_ledger[0]
    assert '--commit-sha {pushed_head_sha}' in from_head[0]


# ---------------------------------------------------------------------------
# phase-6-finalize item 7c step (0): the real document
# ---------------------------------------------------------------------------


def test_the_hook_step_and_its_task_fix_branch_are_found():
    """Vacuity guard: every assertion below reads a slice, and an empty slice proves nothing."""
    assert _item_7c().strip(), f'item 7c not found in {_FINALIZE_SKILL}'
    assert _step_0().strip(), f'step (0) of item 7c not found in {_FINALIZE_SKILL}'
    assert _task_fix_branch().strip(), f'the task-fix branch of step (0) not found in {_FINALIZE_SKILL}'


def test_the_stamp_step_reads_nothing_from_the_change_ledger():
    """The defect: a commit looked up in the ledger by a task id the ledger does not store."""
    assert _ledger_lookups(_step_0()) == []


def test_the_ledger_detector_does_see_a_ledger_read_in_the_same_document():
    """Matched control: item 5f queries the ledger, so the absence above is about step (0)."""
    item_5f = _between(_FINALIZE_SKILL.read_text(encoding='utf-8'), _ITEM_5F_START, _ITEM_5F_END)

    assert item_5f.strip(), f'item 5f not found in {_FINALIZE_SKILL}'
    assert any('manage-change-ledger' in line for line in _ledger_lookups(item_5f))


def test_a_task_fix_is_stamped_with_the_pushed_head():
    """One stamp call, by fix task, carrying the head the parity read returned."""
    calls = _stamp_calls(_task_fix_branch())

    assert len(calls) == 1, calls
    assert '--plan-id {plan_id}' in calls[0]
    assert '--commit-sha {pushed_head_sha}' in calls[0]
    assert '--task-number {fix_task_number}' in calls[0]
    assert '--hash-id' not in calls[0]


def test_every_stamp_call_of_the_hook_uses_declared_flags_only():
    calls = _stamp_calls(_item_7c())

    assert len(calls) == 2, calls
    for call in calls:
        assert set(_FLAG.findall(call)) <= _STAMP_FLAGS, call


def test_the_pushed_head_is_read_after_the_task_is_done_and_before_the_stamp():
    """The order: read the task, read the push parity, require ``synced``, stamp."""
    branch = _task_fix_branch()
    task_read = branch.index('manage-tasks:manage-tasks read')
    parity_read = branch.index('git-workflow branch-sync-state')
    synced_rule = branch.index('Stamp only on `state: synced`')
    stamp = branch.index('manage-findings:manage-findings stamp-fix-commit')

    assert task_read < parity_read < synced_rule < stamp
    assert 'keep it only when its `status` is `done`' in branch
    assert "the payload's `head_sha` is that commit" in branch
    assert '`{pushed_head_sha}`' in branch


def test_no_other_parity_state_stamps():
    branch = _task_fix_branch()

    for state in ('`ahead`', '`remote_absent_landed`', '`remote_absent_unverified`', '`status: error`'):
        assert state in branch, f'{state} is not named among the states that stamp nothing'
    assert 'stamp nothing' in branch
    assert 'no task is stamped while the branch is not `synced`' in branch


def test_the_hook_says_the_stamped_commit_may_be_later_than_the_fix():
    branch = _task_fix_branch()

    assert (
        'The stamped commit is the pushed head at the time of stamping, '
        'which may be later than the commit that made the fix.'
    ) in branch
    assert 'names a commit as of which the fix is on the pull request' in branch


def test_the_hook_says_a_pushed_head_passes_the_ancestor_check_and_keeps_passing():
    branch = _task_fix_branch()

    assert 'as the pull request head or as an ancestor of it' in branch
    assert 'the stamped commit is an ancestor of the new head and still passes' in branch
    assert '`fix_commit_not_on_pr_head`' in branch


def test_an_inline_fix_is_still_stamped_with_the_commit_that_holds_its_edit():
    """Matched control: the reader sees the other stamp call, with the other source."""
    block = _between(_item_7c(), _INLINE_BLOCK_START, _INLINE_BLOCK_END)
    calls = _stamp_calls(block)

    assert block.strip(), f'the inline-fix block of item 7c not found in {_FINALIZE_SKILL}'
    assert len(calls) == 1, calls
    assert '--commit-sha {inline_commit_sha}' in calls[0]
    assert '--hash-id {hash_id}' in calls[0]
    assert '--task-number' not in calls[0]


# ---------------------------------------------------------------------------
# The two documents that describe the stamp to its readers
# ---------------------------------------------------------------------------


def test_the_respond_step_names_the_stamp_source_and_its_consequence():
    step_8 = _step_8()

    assert '**Which commit the hook stamps.**' in step_8
    assert 'For a task fix it is the pushed head of the branch' in step_8
    assert '`branch-sync-state` reports `synced`' in step_8
    assert 'may be later than the commit that made it' in step_8
    assert _ledger_lookups(step_8) == []


def test_the_github_verb_document_names_the_stamp_source_and_its_consequence():
    text = _GITHUB_SKILL.read_text(encoding='utf-8')

    assert 'the pushed head of the branch for a task fix' in text
    assert 'may be later than the commit that made it' in text
    assert 'because it stays an ancestor of the head' in text

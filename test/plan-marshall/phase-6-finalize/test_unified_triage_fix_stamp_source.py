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

Step (0) also writes two stamps that recover a held reply, both with the pushed
head and both only on ``synced``: it stamps an inline fix an earlier firing left
unstamped once the finding's file differs from the reviewed commit, and after its
respond pass it stamps again every finding that pass reported as
``fix_commit_not_on_pr_head``, then runs the pass once more.

This suite pins the document side of that procedure. Every reader and every
detector is exercised against synthetic text first — one text that carries the
shape it looks for, one that does not — so a detector that silently finds nothing
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

#: The inline-fix branch of step (0) runs up to the sentence that leads into the
#: respond pass.
_INLINE_FIX_END = 'These stamps are written before the respond pass'

#: The part of step (0) that stamps again, after the respond pass. It runs up to
#: the closing paragraph of step (0).
_RESTAMP_START = '**Stamp again a stamp that does not reach the pull request head.**'
_RESTAMP_END = 'A non-zero `count_deferred_until_commit` on the last respond pass of (0)'

#: The one respond call of step (0), by its second line.
_RESPOND_CALL_LINE = 'post_responses --pr-number {pr_number} --plan-id {plan_id}'

#: The comparison that decides whether an unstamped inline fix is stamped.
_DIFF_CHECK = 'git -C {worktree_path} diff --quiet {reviewed_commit_sha} {pushed_head_sha} -- {file_path}'

#: What the comparison does not show, stated in the hook and in the respond step.
_INLINE_COST = (
    'The check shows that the file changed after the reviewed commit, not that the change is the fix, '
    'so a reviewer can be told "fixed" for an edit that was lost.'
)

#: What stamping the pushed head again does not show, stated in the same two places.
_RESTAMP_LIMIT = (
    'The pushed head contains whatever the branch holds, so when the rewrite that replaced the stamped '
    'commit also dropped the fix, the reviewer is told "fixed" for a change that is not on the pull request.'
)

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


def _pushed_head_stamps_by_finding(text: str) -> list[str]:
    """The ``stamp-fix-commit`` calls in ``text`` that stamp ONE finding with the pushed head."""
    return [
        call
        for call in _stamp_calls(text)
        if '--commit-sha {pushed_head_sha}' in call and '--hash-id {hash_id}' in call and '--task-number' not in call
    ]


def _table_row(text: str, key: str) -> list[str]:
    """The cells of the single markdown table row of ``text`` whose first cell is ``key``.

    No such row returns the empty list, and so does a repeated one: taking the
    first copy would hide a second row that says something else.
    """
    rows: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith('|'):
            continue
        cells = [cell.strip() for cell in stripped.strip('|').split('|')]
        if cells and cells[0] == key:
            rows.append(cells)
    return rows[0] if len(rows) == 1 else []


def _shell_lines(text: str, command: str) -> list[str]:
    """The lines of ``text`` that are exactly ``command``, ignoring indentation."""
    return [line.strip() for line in text.splitlines() if line.strip() == command]


def _states(text: str, sentence: str) -> bool:
    """Whether ``text`` carries ``sentence``, with runs of whitespace read as one space."""
    return ' '.join(sentence.split()) in ' '.join(text.split())


def _item_7c() -> str:
    return _between(_FINALIZE_SKILL.read_text(encoding='utf-8'), _ITEM_7C_START, _ITEM_7C_END)


def _step_0() -> str:
    return _between(_item_7c(), _STEP_0_START, _STEP_0_END)


def _task_fix_branch() -> str:
    return _between(_step_0(), _TASK_FIX_START, _TASK_FIX_END)


def _inline_fix_branch() -> str:
    return _between(_step_0(), _TASK_FIX_END, _INLINE_FIX_END)


def _restamp_part() -> str:
    return _between(_step_0(), _RESTAMP_START, _RESTAMP_END)


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


#: A recovery that stamps one finding with the pushed head and tabulates what
#: each reason and each exit status leads to.
_SYNTHETIC_RECOVERY = """\
  | Row `reason` | What this step does |
  |--------------|---------------------|
  | `fix_commit_not_on_pr_head` | Stamps the finding again with `{pushed_head_sha}`. |
  | `pr_head_unreadable` | Stamps nothing. |

  ```bash
  git -C {worktree_path} diff --quiet {reviewed_commit_sha} {pushed_head_sha} -- {file_path}
  ```

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings stamp-fix-commit \\
    --plan-id {plan_id} --commit-sha {pushed_head_sha} --hash-id {hash_id}
  ```

  The check shows that the file changed after the reviewed commit,
  not that the change is the fix.
"""

#: The shapes the recovery detectors must NOT report: a row that names the reason
#: twice, a stamp with another commit, and a comparison of other operands.
_SYNTHETIC_NO_RECOVERY = """\
  | `pr_head_unreadable` | Stamps nothing. |
  | `pr_head_unreadable` | Stamps the finding again. |

  ```bash
  git -C {worktree_path} diff --quiet HEAD -- {file_path}
  ```

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings stamp-fix-commit \\
    --plan-id {plan_id} --commit-sha {inline_commit_sha} --hash-id {hash_id}
  ```

  The check shows that the file changed.
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


def test_pushed_head_stamp_reader_finds_a_stamp_of_one_finding_only():
    """Positive control, then three negatives: by task, with another commit, and prose."""
    assert len(_pushed_head_stamps_by_finding(_SYNTHETIC_RECOVERY)) == 1
    assert _pushed_head_stamps_by_finding(_SYNTHETIC_HEAD_BRANCH) == []
    assert _pushed_head_stamps_by_finding(_SYNTHETIC_NO_RECOVERY) == []
    assert _pushed_head_stamps_by_finding('Stamp the finding with `{pushed_head_sha}` by `--hash-id`.') == []


def test_table_row_reader_returns_one_row_and_nothing_for_an_absent_or_repeated_one():
    assert _table_row(_SYNTHETIC_RECOVERY, '`fix_commit_not_on_pr_head`') == [
        '`fix_commit_not_on_pr_head`',
        'Stamps the finding again with `{pushed_head_sha}`.',
    ]
    assert _table_row(_SYNTHETIC_RECOVERY, '`pr_head_unreadable`') == ['`pr_head_unreadable`', 'Stamps nothing.']
    assert _table_row(_SYNTHETIC_RECOVERY, '`fix_commit_ancestry_unreadable`') == []
    assert _table_row(_SYNTHETIC_NO_RECOVERY, '`pr_head_unreadable`') == []
    assert _table_row('`pr_head_unreadable` stamps nothing.', '`pr_head_unreadable`') == []


def test_shell_line_reader_takes_the_exact_comparison_only():
    assert _shell_lines(_SYNTHETIC_RECOVERY, _DIFF_CHECK) == [_DIFF_CHECK]
    assert _shell_lines(_SYNTHETIC_NO_RECOVERY, _DIFF_CHECK) == []
    assert _shell_lines(f'Run `{_DIFF_CHECK}` and read its exit status.', _DIFF_CHECK) == []


def test_sentence_reader_reads_across_a_line_break_and_not_across_a_missing_clause():
    sentence = 'The check shows that the file changed after the reviewed commit, not that the change is the fix.'

    assert _states(_SYNTHETIC_RECOVERY, sentence) is True
    assert _states(_SYNTHETIC_NO_RECOVERY, sentence) is False


# ---------------------------------------------------------------------------
# phase-6-finalize item 7c step (0): the real document
# ---------------------------------------------------------------------------


def test_the_hook_step_and_its_task_fix_branch_are_found():
    """Vacuity guard: every assertion below reads a slice, and an empty slice proves nothing."""
    assert _item_7c().strip(), f'item 7c not found in {_FINALIZE_SKILL}'
    assert _step_0().strip(), f'step (0) of item 7c not found in {_FINALIZE_SKILL}'
    assert _task_fix_branch().strip(), f'the task-fix branch of step (0) not found in {_FINALIZE_SKILL}'
    assert _inline_fix_branch().strip(), f'the inline-fix branch of step (0) not found in {_FINALIZE_SKILL}'
    assert _restamp_part().strip(), f'the stamp-again part of step (0) not found in {_FINALIZE_SKILL}'


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
    """Four calls: the task fix, the unstamped inline fix, the stamp-again, and (4a)."""
    calls = _stamp_calls(_item_7c())

    assert len(calls) == 4, calls
    for call in calls:
        assert set(_FLAG.findall(call)) <= _STAMP_FLAGS, call
    # Step (0) holds three of them; one is by fix task and two are by finding.
    assert len(_stamp_calls(_step_0())) == 3
    assert len(_pushed_head_stamps_by_finding(_step_0())) == 2


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
    assert _pushed_head_stamps_by_finding(block) == []
    assert 'except the ones (0) left unstamped and logged in this same firing' in block


# ---------------------------------------------------------------------------
# Step (0): an inline fix an earlier firing left unstamped
# ---------------------------------------------------------------------------


def test_an_unstamped_inline_fix_is_stamped_with_the_pushed_head_by_finding():
    """One stamp call in the branch, by finding, and only under three stated conditions."""
    branch = _inline_fix_branch()
    calls = _stamp_calls(branch)

    assert len(calls) == 1, calls
    assert _pushed_head_stamps_by_finding(branch) == calls
    assert 'only when all three of these hold' in branch
    assert 'the `branch-sync-state` read of this firing reports `state: synced`' in branch
    assert 'the finding carries a `file_path` and a `reviewed_commit_sha`' in branch
    assert 'the file differs between the reviewed commit and the pushed head' in branch
    assert 'no inline fix is stamped here' in branch


def test_the_comparison_is_one_command_read_by_its_exit_status():
    """The exact command, and one row per outcome: 1 stamps, 0 and any other do not."""
    branch = _inline_fix_branch()

    assert _shell_lines(branch, _DIFF_CHECK) == [_DIFF_CHECK]
    assert branch.index(_DIFF_CHECK) < branch.index('manage-findings:manage-findings stamp-fix-commit')
    assert _table_row(branch, '`1`')[1:] == ['The file differs between the two commits.', 'Is stamped.']
    assert _table_row(branch, '`0`')[1:] == ['The file is unchanged.', 'Is not stamped.']
    other = _table_row(branch, 'any other')
    assert len(other) == 3, other
    assert other[1].startswith('The comparison could not be made')
    assert other[2] == 'Is not stamped.'


def test_a_finding_without_a_file_path_or_a_reviewed_commit_is_not_stamped():
    branch = _inline_fix_branch()

    assert _states(
        branch,
        'A finding with no `file_path` (a `review_body` or `issue_comment` finding) or with no '
        '`reviewed_commit_sha` is not compared and is not stamped.',
    )
    assert 'is logged at WARNING, naming its `hash_id` and the ground' in branch
    assert 'and stays held' in branch


def test_the_hook_says_what_the_comparison_does_not_show():
    assert _states(_inline_fix_branch(), _INLINE_COST)


def test_the_inline_stamps_are_written_before_the_respond_pass():
    step_0 = _step_0()

    assert step_0.count(_RESPOND_CALL_LINE) == 1
    assert step_0.index(_TASK_FIX_END) < step_0.index(_INLINE_FIX_END) < step_0.index(_RESPOND_CALL_LINE)
    assert 'These stamps are written before the respond pass, so that pass sends their replies' in step_0


# ---------------------------------------------------------------------------
# Step (0): a stamp that does not reach the pull request head
# ---------------------------------------------------------------------------


def test_a_stamp_that_misses_the_head_is_stamped_again_by_finding_and_only_on_synced():
    """One stamp call, by finding, with the pushed head, after the respond pass."""
    part = _restamp_part()
    calls = _stamp_calls(part)
    step_0 = _step_0()

    assert len(calls) == 1, calls
    assert _pushed_head_stamps_by_finding(part) == calls
    assert step_0.index(_RESPOND_CALL_LINE) < step_0.index(_RESTAMP_START)
    row = _table_row(part, '`fix_commit_not_on_pr_head`')
    assert len(row) == 2, row
    assert row[1].startswith('Stamps the finding again with `{pushed_head_sha}`')
    assert 'only when the `branch-sync-state` read of this firing reports `state: synced`' in row[1]
    assert 'On any state other than `synced`' in part
    assert 'nothing is stamped again' in part
    assert 'for a task fix and for an inline fix alike' in part


def test_an_unreadable_reason_stamps_nothing():
    """The two reasons that report a failed read, each on its own row."""
    part = _restamp_part()

    assert _table_row(part, '`pr_head_unreadable`') == [
        '`pr_head_unreadable`',
        'Stamps nothing. A failed read does not show that the stamped commit was replaced.',
    ]
    assert _table_row(part, '`fix_commit_ancestry_unreadable`') == [
        '`fix_commit_ancestry_unreadable`',
        'Stamps nothing, on the same ground.',
    ]


def test_the_respond_pass_runs_once_more_only_after_a_stamp_was_written_again():
    part = _restamp_part()

    assert 'When at least one finding was stamped again, run the respond pass once more' in part
    assert 'with the same `github_pr post_responses` call as above and no added flag' in part
    assert 'When none was, the respond pass is not repeated' in part
    assert _github_respond_calls(part) == []


def test_the_hook_says_what_stamping_the_pushed_head_again_does_not_show():
    assert _states(_restamp_part(), _RESTAMP_LIMIT)


def test_the_task_fix_branch_names_this_step_as_the_one_that_stamps_again():
    branch = _task_fix_branch()

    assert 'the finding is held with `fix_commit_not_on_pr_head` until it is stamped again' in branch
    assert 'This step is the one that stamps it again, after its respond pass below' in branch


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


def test_the_respond_step_states_both_recoveries_and_what_each_does_not_show():
    step_8 = _step_8()

    assert _states(step_8, _INLINE_COST)
    assert _states(step_8, _RESTAMP_LIMIT)
    assert '`reason: fix_commit_not_on_pr_head` is stamped again with the pushed head' in step_8
    assert f'`{_DIFF_CHECK}` exits with status 1' in step_8
    assert 'Exit status 0 (the file is unchanged), any other exit status (the comparison could not be made)' in step_8
    assert 'a finding with no `file_path` and a finding with no `reviewed_commit_sha` stamp nothing' in step_8
    assert 'each only while `branch-sync-state` reports `synced`' in step_8


def test_the_respond_step_says_which_held_state_the_hook_ends():
    """One row per state; the reader returns nothing for a state named twice."""
    step_8 = _step_8()

    assert _table_row(step_8, '`no_fix_commit`, task fix')[1].startswith('Ends it')
    assert _table_row(step_8, '`no_fix_commit`, inline fix')[1].startswith('Ends it when')
    assert _table_row(step_8, '`fix_commit_not_on_pr_head`')[1].startswith('Ends it')
    assert _table_row(step_8, '`fix_commit_ancestry_unreadable`')[1].startswith('Does not end it')


def test_the_respond_step_says_when_a_discarded_inline_edit_is_answered():
    step_8 = _step_8()
    rows = [line for line in step_8.splitlines() if line.strip().startswith('| The inline edit is discarded')]

    assert len(rows) == 1, rows
    assert 'stamps the pushed head once the branch is `synced`' in rows[0]
    assert "the finding's file differs from the reviewed commit, and the reply is sent" in rows[0]
    assert 'Otherwise' in rows[0]
    assert 'No reply. The thread stays open.' in rows[0]


# ---------------------------------------------------------------------------
# Which respond call carries ``--send-unstamped-fixed``
# ---------------------------------------------------------------------------

#: The flag that sends a ``fixed`` reply with no stamped commit in the same pass.
_SEND_UNSTAMPED_FLAG = '--send-unstamped-fixed'

_GITHUB_RESPOND_CALL = 'workflow-integration-github:github_pr post_responses'

_GITHUB_SCRIPT = get_skill_dir('plan-marshall', 'workflow-integration-github') / 'scripts' / 'github_pr.py'

#: Two respond calls, one per form.
_SYNTHETIC_RESPOND_CALLS = """\
```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \\
  post_responses --pr-number {pr_number} --plan-id {plan_id}
```

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \\
  post_responses --pr-number {pr_number} --plan-id {plan_id} --send-unstamped-fixed
```

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar \\
  post_responses --plan-id {plan_id} --project {project_key}
```
"""


def _github_respond_calls(text: str) -> list[str]:
    """The GitHub ``post_responses`` calls in ``text``."""
    return [command for command in _commands(text) if _GITHUB_RESPOND_CALL in command]


def test_respond_call_reader_tells_the_two_forms_apart():
    """Both controls: the reader finds each GitHub form and leaves the Sonar call out."""
    calls = _github_respond_calls(_SYNTHETIC_RESPOND_CALLS)

    assert len(calls) == 2, calls
    assert _SEND_UNSTAMPED_FLAG not in calls[0]
    assert calls[1].endswith(_SEND_UNSTAMPED_FLAG)


def test_the_respond_step_issues_the_flag_for_every_producer_but_finalize_feedback():
    """Step 8 shows both forms and says which producer issues which."""
    step_8 = _step_8()
    calls = _github_respond_calls(step_8)

    assert len(calls) == 2, calls
    assert [_SEND_UNSTAMPED_FLAG in call for call in calls] == [False, True]
    assert '| `finalize-feedback` | WITHOUT `--send-unstamped-fixed` |' in step_8
    assert '`pr-state`, and the standalone `pr-comment` mode | WITH `--send-unstamped-fixed` |' in step_8
    assert 'No later respond pass exists for these producers' in step_8
    assert '`--send-unstamped-fixed` is a flag of the GitHub verb only' in step_8


def test_the_respond_step_says_what_the_flag_costs_the_reviewer():
    step_8 = _step_8()

    assert '**What the flag costs the reviewer.**' in step_8
    assert 'the reviewer is told "fixed"' in step_8
    assert 'the edit is in the worktree and may not be committed yet' in step_8
    assert 'names no commit' in step_8


def test_the_finalize_hook_never_passes_the_flag():
    """Item 7c runs the second respond pass itself, so its calls keep the hold."""
    item_7c = _item_7c()
    calls = _github_respond_calls(item_7c)

    assert len(calls) == 1, calls
    assert _SEND_UNSTAMPED_FLAG not in calls[0]
    # (4a) names its respond pass by reference to that one call, and adds no flag.
    assert 'with the same `github_pr post_responses` call as (0)' in item_7c
    assert _SEND_UNSTAMPED_FLAG not in item_7c


def test_the_github_verb_declares_the_flag_its_handler_reads():
    """The declared flag and the attribute the handler reads are the same name."""
    source = _GITHUB_SCRIPT.read_text(encoding='utf-8')

    assert f"'flags': ['{_SEND_UNSTAMPED_FLAG}']" in source
    assert "'dest': 'send_unstamped_fixed'" in source
    assert "getattr(args, 'send_unstamped_fixed', False)" in source


def test_the_github_verb_document_names_the_stamp_source_and_its_consequence():
    text = _GITHUB_SKILL.read_text(encoding='utf-8')

    assert 'the pushed head of the branch for a task fix' in text
    assert 'may be later than the commit that made it' in text
    assert 'because it stays an ancestor of the head' in text


def test_the_github_verb_document_names_both_recoveries_and_their_limit():
    text = _GITHUB_SKILL.read_text(encoding='utf-8')
    row = _table_row(text, '`fix_commit_not_on_pr_head`')

    assert len(row) == 2, row
    assert 'The phase-6-finalize hook stamps the finding again with the pushed head of the branch' in row[1]
    assert 'once `branch-sync-state` reports `synced`' in row[1]
    assert 'A finding this verb reports with `fix_commit_not_on_pr_head` is stamped again' in text
    assert 'its file differs between the reviewed commit and the pushed head' in text
    assert '`Fix commit:` can therefore name a commit that does not contain the fix' in text
    assert '**A held `fixed` finding that no caller stamps is never answered.**' in text

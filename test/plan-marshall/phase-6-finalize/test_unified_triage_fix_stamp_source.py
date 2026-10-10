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

Step (0) also writes two stamps that recover a held reply. Neither is the pushed
head: each is the one commit that is shown to carry the change, and both are
written only on ``synced``. An inline fix a stopped firing left unstamped is
stamped with the single commit the hook made under its inline message that
touches the finding's file after the reviewed commit. A finding the respond pass
reported as ``fix_commit_not_on_pr_head`` is stamped again with the single commit
on the branch whose patch for the finding's file equals the replaced commit's,
and the pass then runs once more. No such commit, several, a command that exits
with a non-zero status and a finding with no file path stamp nothing; the finding
is logged and stays held. ``test_fix_commit_evidence_git_commands.py`` runs both
commands against a real repository.

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

#: The message the hook commits the triage's inline edits with at (4a).
_INLINE_MESSAGE = 'fix(review): apply inline review dispositions'

#: The search that finds the commit an unstamped inline fix is stamped with.
_INLINE_SEARCH = (
    'git -C {worktree_path} log --no-merges --format=%H%x09%s --fixed-strings '
    '--grep="fix(review): apply inline review dispositions" '
    '{reviewed_commit_sha}..{pushed_head_sha} -- {file_path}'
)

#: The comparison that finds the commit a replaced stamp is written again with.
_PATCH_COMPARISON = (
    'git -C {worktree_path} log --cherry-mark --right-only --no-merges --format=%m%H '
    '{stamped_commit_sha}...{pushed_head_sha} ^{stamped_commit_sha}^ ^origin/{base_branch} -- {file_path}'
)

#: The placeholder of a commit one of the two commands found, and of the pushed head.
_EVIDENCE_COMMIT = '{evidence_commit_sha}'
_PUSHED_HEAD = '{pushed_head_sha}'

#: What the inline commit does not show, as the hook states it.
_INLINE_LIMIT = (
    "The commit shows that this hook committed inline dispositions to the finding's file after the review. "
    'It does not show which of several edits in that commit belongs to this finding, '
    'nor that a later commit kept the edit.'
)

#: The part of that statement the respond step repeats word for word.
_INLINE_UNSHOWN = (
    'It does not show which of several edits in that commit belongs to this finding, '
    'nor that a later commit kept the edit.'
)

#: What an equal patch for one file does not show, stated in the hook and in the respond step.
_RESTAMP_LIMIT = (
    "An equal patch for one file shows that this file's change is in a commit on the branch. "
    'It does not show that a later commit did not undo it, and it says nothing about other files the fix touched.'
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

#: The quoted value of a ``--grep`` option.
_GREP_VALUE = re.compile(r'--grep="([^"]*)"')


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


def _stamps_by_finding(text: str, commit: str) -> list[str]:
    """The ``stamp-fix-commit`` calls in ``text`` that stamp ONE finding with ``commit``.

    ``commit`` is the placeholder the call carries after ``--commit-sha``, so the
    same reader answers for the pushed head and for an evidence commit.
    """
    return [
        call
        for call in _stamp_calls(text)
        if f'--commit-sha {commit} ' in f'{call} ' and '--hash-id {hash_id}' in call and '--task-number' not in call
    ]


def _grep_values(command: str) -> list[str]:
    """The quoted ``--grep`` values of ``command``."""
    return _GREP_VALUE.findall(command)


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


#: A recovery that stamps one finding with an evidence commit: both commands as
#: single shell lines, one row per reason, and the stamp call.
_SYNTHETIC_RECOVERY = (
    """\
  | Row `reason` | What this step does |
  |--------------|---------------------|
  | `fix_commit_not_on_pr_head` | Stamps the finding again with the one commit that carries an equal patch. |
  | `pr_head_unreadable` | Stamps nothing. |

  ```bash
  """
    + _PATCH_COMPARISON
    + """
  ```

  ```bash
  """
    + _INLINE_SEARCH
    + """
  ```

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings stamp-fix-commit \\
    --plan-id {plan_id} --commit-sha {evidence_commit_sha} --hash-id {hash_id}
  ```

  An equal patch for one file shows that this file's change
  is in a commit on the branch.
"""
)

#: The shapes the evidence detectors must NOT report: a row that names the reason
#: twice, a comparison with no path restriction, a search for another message, a
#: stamp of the pushed head, and a sentence that lacks the clause on the file.
_SYNTHETIC_NO_RECOVERY = """\
  | `pr_head_unreadable` | Stamps nothing. |
  | `pr_head_unreadable` | Stamps the finding again. |

  ```bash
  git -C {worktree_path} log --cherry-mark --right-only {stamped_commit_sha}...{pushed_head_sha}
  ```

  ```bash
  git -C {worktree_path} log --grep="chore: other" {reviewed_commit_sha}..{pushed_head_sha} -- {file_path}
  ```

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings stamp-fix-commit \\
    --plan-id {plan_id} --commit-sha {pushed_head_sha} --hash-id {hash_id}
  ```

  An equal patch shows that the change is on the branch.
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


def test_by_finding_stamp_reader_tells_an_evidence_commit_from_the_pushed_head():
    """Each commit placeholder has a positive control and a negative one, in both directions."""
    assert len(_stamps_by_finding(_SYNTHETIC_RECOVERY, _EVIDENCE_COMMIT)) == 1
    assert _stamps_by_finding(_SYNTHETIC_RECOVERY, _PUSHED_HEAD) == []
    # A by-finding stamp of the pushed head IS seen, so a zero count over the real step means something.
    assert len(_stamps_by_finding(_SYNTHETIC_NO_RECOVERY, _PUSHED_HEAD)) == 1
    assert _stamps_by_finding(_SYNTHETIC_NO_RECOVERY, _EVIDENCE_COMMIT) == []
    # A stamp by fix task is not a stamp of one finding, and prose is not a call.
    assert _stamps_by_finding(_SYNTHETIC_HEAD_BRANCH, _PUSHED_HEAD) == []
    assert _stamps_by_finding('Stamp the finding with `{evidence_commit_sha}` by `--hash-id`.', _EVIDENCE_COMMIT) == []


def test_grep_value_reader_returns_the_quoted_message_only():
    assert _grep_values(_INLINE_SEARCH) == [_INLINE_MESSAGE]
    assert _grep_values(_PATCH_COMPARISON) == []
    assert _grep_values('git log --grep=unquoted') == []


def test_table_row_reader_returns_one_row_and_nothing_for_an_absent_or_repeated_one():
    assert _table_row(_SYNTHETIC_RECOVERY, '`fix_commit_not_on_pr_head`') == [
        '`fix_commit_not_on_pr_head`',
        'Stamps the finding again with the one commit that carries an equal patch.',
    ]
    assert _table_row(_SYNTHETIC_RECOVERY, '`pr_head_unreadable`') == ['`pr_head_unreadable`', 'Stamps nothing.']
    assert _table_row(_SYNTHETIC_RECOVERY, '`fix_commit_ancestry_unreadable`') == []
    assert _table_row(_SYNTHETIC_NO_RECOVERY, '`pr_head_unreadable`') == []
    assert _table_row('`pr_head_unreadable` stamps nothing.', '`pr_head_unreadable`') == []


def test_shell_line_reader_takes_each_exact_command_only():
    """Both commands are found as whole lines; a shortened one and one quoted in prose are not."""
    assert _shell_lines(_SYNTHETIC_RECOVERY, _PATCH_COMPARISON) == [_PATCH_COMPARISON]
    assert _shell_lines(_SYNTHETIC_RECOVERY, _INLINE_SEARCH) == [_INLINE_SEARCH]
    assert _shell_lines(_SYNTHETIC_NO_RECOVERY, _PATCH_COMPARISON) == []
    assert _shell_lines(_SYNTHETIC_NO_RECOVERY, _INLINE_SEARCH) == []
    assert _shell_lines(f'Run `{_PATCH_COMPARISON}` and read its exit status.', _PATCH_COMPARISON) == []
    assert _shell_lines(f'Run `{_INLINE_SEARCH}` and count its lines.', _INLINE_SEARCH) == []


def test_sentence_reader_reads_across_a_line_break_and_not_across_a_missing_clause():
    sentence = "An equal patch for one file shows that this file's change is in a commit on the branch."

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
    # The two by finding carry an evidence commit; no finding is stamped with the pushed head.
    assert len(_stamps_by_finding(_step_0(), _EVIDENCE_COMMIT)) == 2
    assert _stamps_by_finding(_step_0(), _PUSHED_HEAD) == []


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
    assert _stamps_by_finding(block, _PUSHED_HEAD) == []
    assert _stamps_by_finding(block, _EVIDENCE_COMMIT) == []
    assert 'except the ones (0) left unstamped and logged in this same firing' in block
    # The exclusion names what (0) stamped such a finding with: its evidence commit.
    assert 'An inline fix (0) stamped with its evidence commit carries a `fix_commit_sha`' in block
    assert 'stamped with the pushed head' not in block


def test_the_search_looks_for_the_message_the_hook_commits_inline_edits_with():
    """One literal in two places: the commit message of (4a) and the ``--grep`` value of (0)."""
    block = _between(_item_7c(), _INLINE_BLOCK_START, _INLINE_BLOCK_END)
    searches = _shell_lines(_inline_fix_branch(), _INLINE_SEARCH)

    assert f'and the message `{_INLINE_MESSAGE}`' in block
    assert len(searches) == 1, searches
    assert _grep_values(searches[0]) == [_INLINE_MESSAGE]


# ---------------------------------------------------------------------------
# Step (0): an inline fix an earlier firing left unstamped
# ---------------------------------------------------------------------------


def test_an_unstamped_inline_fix_is_stamped_with_its_evidence_commit_by_finding():
    """One stamp call in the branch, by finding, with the commit the search found — never the pushed head."""
    branch = _inline_fix_branch()
    calls = _stamp_calls(branch)

    assert len(calls) == 1, calls
    assert _stamps_by_finding(branch, _EVIDENCE_COMMIT) == calls
    assert _stamps_by_finding(branch, _PUSHED_HEAD) == []
    assert 'issued only when both of these hold' in branch
    assert 'the `branch-sync-state` read of this firing reports `state: synced`' in branch
    assert 'the finding carries a `file_path` and a `reviewed_commit_sha`' in branch
    assert 'A changed file alone is not evidence, and the pushed head is never stamped here.' in branch
    assert 'no inline fix is stamped here' in branch
    # The file-differs check is gone from the whole step, not only from this branch.
    assert 'diff --quiet' not in _step_0()


def test_the_search_is_one_command_and_only_exactly_one_counted_line_stamps():
    """The exact command, the counting rule, and one row per outcome."""
    branch = _inline_fix_branch()

    assert _shell_lines(branch, _INLINE_SEARCH) == [_INLINE_SEARCH]
    assert branch.index(_INLINE_SEARCH) < branch.index('manage-findings:manage-findings stamp-fix-commit')
    assert f'a line is counted only when the text after the tab equals `{_INLINE_MESSAGE}` exactly' in branch
    one = _table_row(branch, 'Exit status 0 and exactly one counted line')
    assert len(one) == 2, one
    assert one[1].startswith('Is stamped with that commit, `{evidence_commit_sha}`')
    assert _table_row(branch, 'Exit status 0 and no counted line')[1:] == ['Is not stamped.']
    assert _table_row(branch, 'Exit status 0 and more than one counted line')[1:] == ['Is not stamped.']
    other = _table_row(branch, 'Any other exit status')
    assert len(other) == 2, other
    assert other[1].startswith('Is not stamped. The search could not be made')


def test_a_finding_without_a_file_path_or_a_reviewed_commit_is_not_stamped():
    branch = _inline_fix_branch()

    assert _states(
        branch,
        'A finding with no `file_path` (a `review_body` or `issue_comment` finding) or with no '
        '`reviewed_commit_sha` is not searched for and is not stamped.',
    )
    assert 'is logged at WARNING, naming its `hash_id` and the reason' in branch
    assert 'the search exited with a non-zero status' in branch
    assert 'and stays held' in branch


def test_the_hook_says_what_the_inline_commit_does_not_show():
    assert _states(_inline_fix_branch(), _INLINE_LIMIT)


def test_an_uncommitted_inline_edit_is_stamped_two_firings_later():
    """The next firing commits it at (4a) and leaves it out; the one after finds the commit."""
    branch = _inline_fix_branch()

    assert 'An edit a stopped firing left uncommitted in the worktree has no such commit yet.' in branch
    assert '(4a) of the next firing commits it under the same message' in branch
    assert '(0) of the firing after that finds the commit and stamps it' in branch


def test_the_inline_stamps_are_written_before_the_respond_pass():
    step_0 = _step_0()

    assert step_0.count(_RESPOND_CALL_LINE) == 1
    assert step_0.index(_TASK_FIX_END) < step_0.index(_INLINE_FIX_END) < step_0.index(_RESPOND_CALL_LINE)
    assert 'These stamps are written before the respond pass, so that pass sends their replies' in step_0


# ---------------------------------------------------------------------------
# Step (0): a stamp that does not reach the pull request head
# ---------------------------------------------------------------------------


def test_a_stamp_that_misses_the_head_is_stamped_again_with_its_evidence_commit_and_only_on_synced():
    """One stamp call, by finding, with the commit the comparison found, after the respond pass."""
    part = _restamp_part()
    calls = _stamp_calls(part)
    step_0 = _step_0()

    assert len(calls) == 1, calls
    assert _stamps_by_finding(part, _EVIDENCE_COMMIT) == calls
    assert _stamps_by_finding(part, _PUSHED_HEAD) == []
    assert step_0.index(_RESPOND_CALL_LINE) < step_0.index(_RESTAMP_START)
    row = _table_row(part, '`fix_commit_not_on_pr_head`')
    assert len(row) == 2, row
    assert row[1].startswith(
        "Looks for the commit on the branch whose patch for the finding's file equals the replaced commit's"
    )
    assert 'stamps the finding again with that commit when exactly one is found' in row[1]
    assert 'only when the `branch-sync-state` read of this firing reports `state: synced`' in row[1]
    assert 'On any state other than `synced`' in part
    assert 'nothing is stamped again' in part
    assert 'for a task fix and for an inline fix alike' in part
    assert 'It does not show that the rewrite kept the fix, so the pushed head is not stamped.' in part


def test_the_patch_comparison_is_one_command_and_only_exactly_one_equal_line_stamps():
    """The exact command, read after the finding and before the stamp, and one row per outcome."""
    part = _restamp_part()

    assert _shell_lines(part, _PATCH_COMPARISON) == [_PATCH_COMPARISON]
    assert (
        part.index('manage-findings:manage-findings get')
        < part.index(_PATCH_COMPARISON)
        < part.index('manage-findings:manage-findings stamp-fix-commit')
    )
    assert 'The comparison is one command, with no pipe' in part
    one = _table_row(part, 'Exit status 0 and exactly one line that starts with `=`')
    assert len(one) == 2, one
    assert one[1].startswith('Is stamped again with that commit, `{evidence_commit_sha}`')
    assert _table_row(part, 'Exit status 0 and no line that starts with `=`')[1:] == ['Is not stamped again.']
    assert _table_row(part, 'Exit status 0 and more than one line that starts with `=`')[1:] == [
        'Is not stamped again.'
    ]
    other = _table_row(part, 'Any other exit status')
    assert len(other) == 2, other
    assert other[1].startswith('Is not stamped again. The comparison could not be made')


def test_the_hook_says_where_it_reads_the_base_branch_from():
    """The comparison names ``{base_branch}``, and item 7c reads it nowhere else."""
    part = _restamp_part()
    reads = [command for command in _commands(part) if 'manage-references:manage-references get' in command]

    assert len(reads) == 1, reads
    assert reads[0].endswith('--plan-id {plan_id} --field base_branch')
    assert 'Item 7c has no other read of it' in part
    assert part.index('manage-references:manage-references get') < part.index(_PATCH_COMPARISON)


def test_a_finding_without_a_file_path_or_a_readable_stamp_is_not_stamped_again():
    part = _restamp_part()

    assert _states(
        part,
        'A finding with no `file_path` (a `review_body` or `issue_comment` finding), and a finding whose '
        '`fix_commit_sha` cannot be read, is not compared and is not stamped again.',
    )
    assert 'is logged at WARNING, naming its `hash_id` and the reason' in part
    assert 'the comparison exited with a non-zero status' in part
    assert 'and stays held' in part


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


def test_the_hook_says_what_an_equal_patch_does_not_show():
    part = _restamp_part()

    assert _states(part, _RESTAMP_LIMIT)
    assert 'it stays held until it is re-resolved or stamped by hand' in part


def test_the_task_fix_branch_names_this_step_as_the_one_that_stamps_again():
    branch = _task_fix_branch()

    assert 'the finding is held with `fix_commit_not_on_pr_head` until it is stamped again' in branch
    assert (
        'This step stamps it again after its respond pass below, and only with a commit on the branch '
        "that carries the same change to the finding's file as the replaced commit did"
    ) in branch
    assert 'a finding for which no such commit is found stays held' in branch


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

    assert _states(step_8, _INLINE_UNSHOWN)
    assert 'The commit shows that the hook committed inline dispositions to that file after the review.' in step_8
    assert _states(step_8, _RESTAMP_LIMIT)
    assert 'The hook stamps an evidence commit in two further cases' in step_8
    assert 'each only while `branch-sync-state` reports `synced`' in step_8
    assert 'In neither does it stamp the pushed head' in step_8
    assert (
        "is stamped again with the one commit on the branch whose patch for the finding's file "
        "equals the replaced commit's"
    ) in step_8
    assert 'it stamps on exit status 0 with exactly one line marked `=`' in step_8
    assert 'a finding with no `file_path` and a finding with no readable `fix_commit_sha` stamp nothing' in step_8
    assert f'whose subject is exactly `{_INLINE_MESSAGE}`' in step_8
    assert 'a finding with no `file_path` and a finding with no `reviewed_commit_sha` stamp nothing' in step_8
    assert 'it stays held until it is re-resolved or stamped by hand' in step_8
    # The three stamping points name the evidence, not the pushed head, for the two recoveries.
    assert "for which it finds the one commit that holds inline edits to the finding's file" in step_8
    assert "for which it finds the one commit that carries the replaced commit's change to the finding's file" in step_8
    assert 'diff --quiet' not in step_8
    assert 'stamped again with the pushed head' not in step_8


def test_the_respond_step_says_which_held_state_the_hook_ends():
    """One row per state; the reader returns nothing for a state named twice."""
    step_8 = _step_8()
    inline = _table_row(step_8, '`no_fix_commit`, inline fix')
    rewritten = _table_row(step_8, '`fix_commit_not_on_pr_head`')

    assert _table_row(step_8, '`no_fix_commit`, task fix')[1].startswith('Ends it')
    assert len(inline) == 2, inline
    assert inline[1].startswith("Ends it when exactly one commit with the hook's inline message touches")
    assert 'Does not end it when there is no such commit or more than one' in inline[1]
    assert len(rewritten) == 2, rewritten
    assert rewritten[1].startswith('Ends it when exactly one commit on a `synced` branch carries')
    assert 'Does not end it when there is no such commit or more than one' in rewritten[1]
    assert 'the pushed head' not in inline[1]
    assert 'the pushed head' not in rewritten[1]
    assert _table_row(step_8, '`fix_commit_ancestry_unreadable`')[1].startswith('Does not end it')


def test_the_respond_step_says_when_a_discarded_inline_edit_is_answered():
    step_8 = _step_8()
    rows = [line for line in step_8.splitlines() if line.strip().startswith('| The inline edit is discarded')]

    assert len(rows) == 1, rows
    assert (
        "A reply is sent only when exactly one commit with the hook's inline message touches the finding's file "
        'after the reviewed commit'
    ) in rows[0]
    assert 'A discarded edit has no such commit: No reply. The thread stays open.' in rows[0]
    assert 'stamps the pushed head' not in rows[0]
    assert "is committed by the hook's next firing under that message" in rows[0]


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
    assert (
        'The phase-6-finalize hook stamps the finding again only with the one commit on the branch '
        "whose patch for the finding's file equals the replaced commit's"
    ) in row[1]
    assert 'once `branch-sync-state` reports `synced`' in row[1]
    assert 'When it finds no such commit, or more than one, the finding stays held.' in row[1]
    assert 'with the pushed head' not in row[1]
    assert 'The hook stamps an evidence commit in two further cases' in text
    assert 'in neither does it stamp the pushed head' in text
    assert 'A finding this verb reports with `fix_commit_not_on_pr_head` is stamped again only with' in text
    assert (
        'is stamped only with the one commit the hook made for inline dispositions '
        "that touches the finding's file after the reviewed commit"
    ) in text
    assert "For these two recoveries `Fix commit:` names a commit that carries a change to the finding's file" in text
    assert 'The line does not show that a later commit kept that change' in text
    assert '`Fix commit:` can therefore name a commit that does not contain the fix' not in text
    assert 'its file differs between the reviewed commit and the pushed head' not in text
    assert '**A held `fixed` finding that no caller stamps is never answered.**' in text
    assert 'which includes every `review_body` finding' in text

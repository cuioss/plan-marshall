#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Every exit that abandons a merge admission withdraws the plan's FIFO entry.

An exit that settles without merging while this run does not hold the merge lock
leaves the plan's entry in the FIFO admission queue unless it issues
``merge_lock dequeue``. The plan's directory still sits in its worktree, so the
dead-waiter prune keeps that entry, and every plan queued behind it waits on a
plan that has stopped trying. ``merge_lock release`` is not a substitute: it
unlinks ``merge.lock`` whenever the recorded holder equals the caller's
``plan_id``, so on a run that was never admitted it deletes a lock a concurrent
session for the same plan holds.

The contract pinned here:

* **Budget-exhaustion "Skip merge"** issues ``merge_lock dequeue`` and no
  ``merge_lock release``, before it sets ``{merge_consent} = deferred``.
* **The shared "No, skip merge" path** gives up the admission before it settles:
  ``merge_lock release`` when this run holds the lock, ``merge_lock dequeue``
  otherwise.
* **Trigger-A's ``defer`` policy and "Defer merge" selection** name
  ``merge_lock dequeue`` for the not-held case.
* **Invariant 4** prescribes ``merge_lock dequeue`` for a path that does not hold
  the lock and states no "a release there is harmless" claim.

The arm reader and the detector run against synthetic documents first, so a
reader that returns nothing, or a detector that cannot fire, cannot make the real
assertions pass.
"""

from __future__ import annotations

import re

from conftest import get_skill_dir

_STANDARDS = get_skill_dir('plan-marshall', 'phase-6-finalize') / 'standards'
_BRANCH_CLEANUP = _STANDARDS / 'branch-cleanup.md'
_REREVIEW = _STANDARDS / 'branch-cleanup-rereview.md'

_DEQUEUE = 'merge_lock dequeue'
_RELEASE = 'merge_lock release'
_DEFERRED = '`{merge_consent} = deferred`'

_SKIP_ARM = ('On **Skip merge**', 'Once `admission: admitted`')
_NO_SKIP_ARM = ('**If user selects "No, skip merge"**', '**If user selects "Yes, merge"**')
_INVARIANT_4 = ('4. **Give up the admission', '`merge_hold_budget_seconds` and `merge_hold_window` are declared')
_REREVIEW_DEFER_POLICY = ('- **`defer`**', '- **`ask`**')
_REREVIEW_DEFER_SELECTION = ('- **"Defer merge"**', '```')

#: Phrasings that call a release on a never-acquired path harmless.
_HARMLESS_RELEASE_CLAIMS = (
    re.compile(r'never acquired is a safe no-op'),
    re.compile(r'never acquired it releases harmlessly'),
    re.compile(r'no-op when the widened hold was not acquired'),
)


def _span(text: str, bounds: tuple[str, str]) -> str:
    """The text from the first ``start`` marker up to the next ``end`` marker after it."""
    start_marker, end_marker = bounds
    start = text.find(start_marker)
    if start == -1:
        return ''
    end = text.find(end_marker, start + len(start_marker))
    return text[start : end if end != -1 else len(text)]


def _executed_blocks(text: str) -> list[str]:
    """The fenced blocks in ``text`` that run the executor — the calls an arm ISSUES."""
    return [block for block in text.split('```')[1::2] if 'execute-script.py' in block]


def _abandon_arm_defects(arm: str, *, allow_release: bool) -> list[str]:
    """Every way ``arm`` fails to withdraw the FIFO entry before it settles."""
    if not arm.strip():
        return ['arm not found']
    blocks = _executed_blocks(arm)
    defects: list[str] = []
    dequeue_blocks = [block for block in blocks if _DEQUEUE in block]
    if not dequeue_blocks:
        defects.append('issues no merge_lock dequeue')
    if not allow_release and any(_RELEASE in block for block in blocks):
        defects.append('issues merge_lock release on a path that holds no lock')
    deferred_at = arm.find(_DEFERRED)
    if dequeue_blocks and deferred_at != -1 and arm.find(dequeue_blocks[0]) > deferred_at:
        defects.append('dequeues only after settling the skip')
    return defects


_PRE_FIX_SKIP_DOC = """\
On **Skip merge**, set `{merge_consent} = deferred` and follow the same skip path.

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock release \\
  --plan-id {plan_id}
```

Once `admission: admitted` is reached, merge.
"""

_LATE_DEQUEUE_DOC = """\
On **Skip merge**, set `{merge_consent} = deferred` first.

```bash
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock dequeue \\
  --plan-id {plan_id}
```

Once `admission: admitted` is reached, merge.
"""


def test_detector_fires_on_a_skip_arm_that_releases_instead_of_dequeuing():
    """Matched negative control: a release-only arm is reported on both counts."""
    arm = _span(_PRE_FIX_SKIP_DOC, _SKIP_ARM)

    assert arm.strip(), 'the synthetic arm was not read, so the control proves nothing'
    assert _abandon_arm_defects(arm, allow_release=False) == [
        'issues no merge_lock dequeue',
        'issues merge_lock release on a path that holds no lock',
    ]


def test_detector_fires_on_a_dequeue_issued_after_the_skip_settles():
    arm = _span(_LATE_DEQUEUE_DOC, _SKIP_ARM)

    assert _abandon_arm_defects(arm, allow_release=False) == ['dequeues only after settling the skip']


def test_detector_reports_an_absent_arm():
    assert _abandon_arm_defects(_span(_PRE_FIX_SKIP_DOC, ('No such marker', 'x')), allow_release=False) == [
        'arm not found'
    ]


def test_budget_exhaustion_skip_merge_dequeues_and_never_releases():
    arm = _span(_BRANCH_CLEANUP.read_text(encoding='utf-8'), _SKIP_ARM)

    assert _abandon_arm_defects(arm, allow_release=False) == []


def test_shared_no_skip_path_gives_up_the_admission_before_settling():
    """The shared skip path releases a held lock and dequeues otherwise, both before
    it sets ``{merge_consent} = deferred``."""
    arm = _span(_BRANCH_CLEANUP.read_text(encoding='utf-8'), _NO_SKIP_ARM)

    assert _abandon_arm_defects(arm, allow_release=True) == []
    release_blocks = [block for block in _executed_blocks(arm) if _RELEASE in block]
    assert release_blocks, 'the shared skip path never releases a lock this run holds'
    assert arm.find(release_blocks[0]) < arm.find(_DEFERRED)


def test_invariant_4_prescribes_dequeue_for_a_path_without_the_lock():
    invariant = _span(_BRANCH_CLEANUP.read_text(encoding='utf-8'), _INVARIANT_4)

    assert invariant.strip(), 'invariant 4 not found'
    assert _DEQUEUE in invariant
    assert 'Skip merge' in invariant


def test_no_document_calls_a_never_acquired_release_harmless():
    for document in (_BRANCH_CLEANUP, _REREVIEW):
        text = document.read_text(encoding='utf-8')
        assert not [pattern.pattern for pattern in _HARMLESS_RELEASE_CLAIMS if pattern.search(text)], document


def test_trigger_a_defer_arms_name_the_dequeue():
    text = _REREVIEW.read_text(encoding='utf-8')
    for bounds in (_REREVIEW_DEFER_POLICY, _REREVIEW_DEFER_SELECTION):
        arm = _span(text, bounds)
        assert arm.strip(), f'arm {bounds[0]!r} not found'
        assert _DEQUEUE in arm, arm

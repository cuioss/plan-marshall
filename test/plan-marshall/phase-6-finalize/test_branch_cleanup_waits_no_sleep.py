#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The waits of ``branch-cleanup`` are bounded verb calls and instruct no sleep.

Three waits are covered:

* **The merge-lock admission loops** — the early-hold acquire in § "Acquire the
  Merge Mutex" and the Pre-Merge Gate's § "FIFO poll/backoff loop". They used to
  pace ``merge_lock acquire`` polls with a standalone foreground ``sleep {interval}``
  the harness refuses, so the ``merge_queue_wait_budget_seconds`` budget was
  unreachable. The wait now lives in the script — ``merge_lock acquire
  --wait-seconds`` — and the step only re-issues that bounded call.
* **The GitHub queue-landing wait** — § "Landing poll loop". It used to poll ``pr
  view`` between standalone sleeps; it now re-issues the bounded ``pr
  wait-for-queue-settle`` call, and every settle value the verb can return has
  exactly one documented arm naming where it ends.
* **The GitLab merge-train short-circuit** — inside § "Wait for the Queue Merge to
  Land (bounded)". GitLab offers no bounded landing verb, so the step must issue
  no wait at all there and stop honestly via Branch F1.

The section reader and every detector are exercised against synthetic documents
first, so a reader that silently returns nothing — or a detector that cannot fire —
cannot make the real assertions pass.
"""

from __future__ import annotations

import re

import pytest

from conftest import get_skill_dir

_BRANCH_CLEANUP = get_skill_dir('plan-marshall', 'phase-6-finalize') / 'standards' / 'branch-cleanup.md'
_ADMISSION_LOOP_SECTIONS = ('Acquire the Merge Mutex', 'FIFO poll/backoff loop')
_LANDING_GATE_SECTION = 'Wait for the Queue Merge to Land (bounded)'
_LANDING_LOOP_SECTION = 'Landing poll loop'
_LANDING_LOOP_HEADING = '#### Landing poll loop'
_GITLAB_SHORT_CIRCUIT_MARKER = '**Short-circuit — GitLab merge train'
_GITHUB_SCOPE_MARKER = '**Applies only when'

_HEADING = re.compile(r'^(#{1,6})\s+(.*)$')
_SLEEP_INSTRUCTION = re.compile(r'\bsleep\b', re.IGNORECASE)
# One acquire invocation: from the notation up to the end of its fenced block.
_ACQUIRE_INVOCATION = re.compile(r'merge_lock acquire\b.*?(?=^```)', re.DOTALL | re.MULTILINE)

_EXECUTOR_MARKER = 'execute-script.py'
_SETTLE_VERB = 'pr wait-for-queue-settle'
_PR_VIEW_CALL = re.compile(r'\bpr view\b')

#: Every ``settle`` value ``pr wait-for-queue-settle`` can return, mapped to where
#: the landing loop must route it. ``None`` means the arm leaves the gate for the
#: post-merge tail rather than ending in a Branch F sub-path. Stated as literals so
#: the document cannot drift together with its own guard.
_EXPECTED_SETTLE_ROUTING: dict[str, str | None] = {
    'merged': None,
    'closed': 'F2',
    'dequeued': 'F2',
    'timeout': 'F1',
}

#: A landing-loop arm: a top-level bullet whose bold antecedent opens the line.
_ARM_START = re.compile(r'^- \*\*(?P<antecedent>.+?)\*\*', re.MULTILINE)
_SETTLE_IN_ANTECEDENT = re.compile(r'`settle: ([a-z]+)`')
_F_SUB_PATH = re.compile(r'\*\*(F[123])\*\*')


def _section(text: str, title: str) -> str:
    """Return the body of the first heading starting with ``title``.

    The section runs from its heading to the next heading of the same or a higher
    level. Lines inside a fenced code block are never read as headings, so a shell
    comment in an example does not cut the section short.
    """
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith('```'):
            in_fence = not in_fence
        heading = None if in_fence else _HEADING.match(line)
        if level == 0:
            if heading and heading.group(2).startswith(title):
                level = len(heading.group(1))
            continue
        if heading and len(heading.group(1)) <= level:
            break
        body.append(line)
    return '\n'.join(body)


def _acquire_invocations(section: str) -> list[str]:
    """Return every fenced ``merge_lock acquire`` invocation in ``section``."""
    return [match.group(0) for match in _ACQUIRE_INVOCATION.finditer(section)]


def _fenced_blocks(text: str) -> list[str]:
    """Every fenced code block in ``text``."""
    return text.split('```')[1::2]


def _executed_blocks(text: str) -> list[str]:
    """The fenced blocks in ``text`` that run the executor — the calls a step ISSUES."""
    return [block for block in _fenced_blocks(text) if _EXECUTOR_MARKER in block]


def _arms(section: str) -> list[tuple[str, str]]:
    """``(antecedent, body)`` for every top-level outcome bullet in ``section``.

    An arm runs from its bullet to the next bullet, or to the first non-blank line
    back at column 0 — the paragraph that closes the list. Indented continuation
    lines, including an indented fenced log call, stay inside the arm.
    """
    arms: list[tuple[str, str]] = []
    starts = list(_ARM_START.finditer(section))
    for index, match in enumerate(starts):
        limit = starts[index + 1].start() if index + 1 < len(starts) else len(section)
        lines = section[match.end() : limit].splitlines() or ['']
        body_lines = [lines[0]]
        for line in lines[1:]:
            if line and not line[0].isspace():
                break
            body_lines.append(line)
        arms.append((match.group('antecedent'), '\n'.join(body_lines)))
    return arms


def _settle_routing_defects(section: str) -> list[str]:
    """Every way ``section``'s settle arms depart from the routing contract.

    Each settle value must have exactly one TERMINAL arm, and that arm must end
    where :data:`_EXPECTED_SETTLE_ROUTING` rules — a Branch F sub-path, or the
    post-merge tail for ``merged``. ``timeout`` is the one value with a second,
    NON-terminal arm (budget left → re-issue the call); that arm must name the
    settle verb and no F sub-path, so a re-issue can never be mistaken for a stop.
    """
    defects: list[str] = []
    terminal: dict[str, list[str | None]] = {value: [] for value in _EXPECTED_SETTLE_ROUTING}
    for antecedent, body in _arms(section):
        settle = _SETTLE_IN_ANTECEDENT.search(antecedent)
        if settle is None:
            continue
        value = settle.group(1)
        if value not in terminal:
            defects.append(f'arm {antecedent!r} routes an undocumented settle value {value!r}')
            continue
        sub_paths = sorted(set(_F_SUB_PATH.findall(body)))
        if value == 'timeout' and 'budget left' in antecedent:
            if sub_paths or _SETTLE_VERB not in body:
                defects.append(f'arm {antecedent!r} must re-issue the settle call and end in no F sub-path')
            continue
        if len(sub_paths) > 1:
            defects.append(f'arm {antecedent!r} names several F sub-paths {sub_paths}')
            continue
        if not sub_paths and 'Wait for Merge CI' not in body:
            defects.append(f'arm {antecedent!r} names neither an F sub-path nor the post-merge tail')
            continue
        terminal[value].append(sub_paths[0] if sub_paths else None)
    for value, expected in _EXPECTED_SETTLE_ROUTING.items():
        routed = terminal[value]
        if len(routed) != 1:
            defects.append(f'settle {value!r} has {len(routed)} terminal arm(s), expected exactly one')
        elif routed[0] != expected:
            defects.append(f'settle {value!r} ends in {routed[0]!r}, expected {expected!r}')
    return defects


def _gitlab_short_circuit(gate: str) -> str:
    """The GitLab short-circuit text: its marker up to the GitHub-scope marker."""
    start = gate.find(_GITLAB_SHORT_CIRCUIT_MARKER)
    if start == -1:
        return ''
    end = gate.find(_GITHUB_SCOPE_MARKER, start)
    return gate[start : end if end != -1 else len(gate)]


def _gitlab_short_circuit_defects(gate: str) -> list[str]:
    """Every way the GitLab short-circuit in ``gate`` departs from its contract."""
    short_circuit = _gitlab_short_circuit(gate)
    if not short_circuit:
        return ['no GitLab merge-train short-circuit in the landing gate']
    defects: list[str] = []
    if 'provider: gitlab' not in short_circuit:
        defects.append('the short-circuit does not key on `provider: gitlab`')
    loop_at = gate.find(_LANDING_LOOP_HEADING)
    if loop_at == -1 or gate.find(_GITLAB_SHORT_CIRCUIT_MARKER) > loop_at:
        defects.append('the short-circuit does not precede the landing loop')
    if 'Landing-gate failure path' not in short_circuit:
        defects.append('the short-circuit does not route to the Landing-gate failure path')
    if 'F1' not in short_circuit:
        defects.append('the short-circuit does not end in Branch F1')
    for block in _executed_blocks(short_circuit):
        if _SETTLE_VERB in block:
            defects.append('the short-circuit issues pr wait-for-queue-settle')
        if _PR_VIEW_CALL.search(block):
            defects.append('the short-circuit issues a pr view poll')
    if _SLEEP_INSTRUCTION.search(short_circuit):
        defects.append('the short-circuit instructs a sleep')
    return defects


_SYNTHETIC_DOC = """\
## Outer

###### FIFO poll/backoff loop

Poll the lock.

```bash
# a shell comment that is not a heading
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock acquire \\
  --plan-id {plan_id} --timeout 30
```

Pace the next poll with a single standalone `sleep {interval}` call.

###### Budget-exhaustion escalation

sleep elsewhere is not this section's concern
"""

#: A pre-fix landing gate: the GitLab arm polls ``pr view`` between sleeps, and the
#: landing loop sleeps, routes ``merged`` twice and forgets ``dequeued``.
_PRE_FIX_GATE_DOC = """\
### Wait for the Queue Merge to Land (bounded)

**Short-circuit — GitLab merge train (the enqueue payload carries `provider: gitlab`)**: poll anyway.

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view --pr-number {pr_number}
```

Pace with a standalone `sleep 30` call.

**Applies only when `{merge_mechanism} == merge_queue` on GitHub**.

#### Landing poll loop

Pace successive polls with a single standalone `sleep {interval}` call.

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view --pr-number {pr_number}
```

- **`settle: merged`** → proceed to **Wait for Merge CI**.
- **`settle: merged`** → also proceed to **Wait for Merge CI**.
- **`settle: closed`** → take the failure path, ending in **F2**.
- **`settle: timeout` with budget left** → take the failure path, ending in **F1**.
- **`settle: timeout` with the budget spent** → take the failure path, ending in **F3**.

#### Landing-gate failure path

Stop.

### Wait for Merge CI
"""


def test_section_reader_returns_the_whole_section_and_stops_at_the_next_heading():
    """The reader keeps fenced lines, ignores a ``#`` comment in a fence, and stops in time."""
    section = _section(_SYNTHETIC_DOC, 'FIFO poll/backoff loop')

    assert 'Poll the lock.' in section
    assert '--timeout 30' in section
    assert 'Pace the next poll' in section
    assert 'Budget-exhaustion escalation' not in section
    assert 'sleep elsewhere' not in section


def test_detectors_fire_on_a_loop_that_sleeps_and_passes_the_removed_flag():
    """Matched negative control: the detectors find what the real loops must lack."""
    section = _section(_SYNTHETIC_DOC, 'FIFO poll/backoff loop')
    invocations = _acquire_invocations(section)

    assert _SLEEP_INSTRUCTION.search(section)
    assert len(invocations) == 1
    assert '--timeout' in invocations[0]
    assert '--wait-seconds' not in invocations[0]


def test_section_reader_returns_empty_for_an_absent_title():
    """An absent section reads as empty — the state the real assertions guard against."""
    assert _section(_SYNTHETIC_DOC, 'No such section') == ''


@pytest.mark.parametrize('title', _ADMISSION_LOOP_SECTIONS)
def test_admission_loop_names_the_bounded_acquire_and_instructs_no_sleep(title: str):
    """Each real admission loop is present, re-issues ``acquire --wait-seconds``, and
    never instructs a sleep."""
    section = _section(_BRANCH_CLEANUP.read_text(encoding='utf-8'), title)
    invocations = _acquire_invocations(section)

    assert section.strip(), f'section "{title}" not found in {_BRANCH_CLEANUP}'
    assert invocations, f'section "{title}" carries no merge_lock acquire invocation'
    assert all('--wait-seconds' in invocation for invocation in invocations), invocations
    assert not _SLEEP_INSTRUCTION.search(section)


@pytest.mark.parametrize('title', _ADMISSION_LOOP_SECTIONS)
def test_admission_loop_passes_no_removed_timeout_flag(title: str):
    """No acquire invocation, and no prose, in either loop still carries ``--timeout``."""
    section = _section(_BRANCH_CLEANUP.read_text(encoding='utf-8'), title)

    assert section.strip(), f'section "{title}" not found in {_BRANCH_CLEANUP}'
    assert '--timeout' not in section


# --------------------------------------------------------------------------- #
# The GitHub queue-landing wait
# --------------------------------------------------------------------------- #


def test_settle_routing_detector_fires_on_a_pre_fix_landing_loop():
    """Matched negative control: a doubled ``merged``, a missing ``dequeued``, a
    re-issue arm that stops, and a ``timeout`` that ends in the wrong sub-path are
    each reported."""
    loop = _section(_PRE_FIX_GATE_DOC, _LANDING_LOOP_SECTION)

    assert loop.strip(), 'the synthetic landing loop was not read, so the control proves nothing'
    assert _settle_routing_defects(loop) == [
        "arm '`settle: timeout` with budget left' must re-issue the settle call and end in no F sub-path",
        "settle 'merged' has 2 terminal arm(s), expected exactly one",
        "settle 'dequeued' has 0 terminal arm(s), expected exactly one",
        "settle 'timeout' ends in 'F3', expected 'F1'",
    ]
    assert _SLEEP_INSTRUCTION.search(loop)
    assert not any(_SETTLE_VERB in block for block in _executed_blocks(loop))


def test_landing_loop_issues_the_bounded_settle_call_by_pr_number():
    """The GitHub landing loop re-issues ``pr wait-for-queue-settle``, keyed on
    ``--pr-number`` and bounded by ``--timeout``, and issues no ``pr view`` poll."""
    loop = _section(_BRANCH_CLEANUP.read_text(encoding='utf-8'), _LANDING_LOOP_SECTION)
    calls = _executed_blocks(loop)
    settle_calls = [block for block in calls if _SETTLE_VERB in block]

    assert loop.strip(), f'section "{_LANDING_LOOP_SECTION}" not found in {_BRANCH_CLEANUP}'
    assert len(settle_calls) == 1, f'expected one settle invocation, found {len(settle_calls)}: {calls}'
    assert '--pr-number' in settle_calls[0]
    assert '--head' not in settle_calls[0]
    assert '--timeout' in settle_calls[0]
    assert not any(_PR_VIEW_CALL.search(block) for block in calls), calls


def test_landing_gate_instructs_no_sleep():
    """No part of the queue-landing gate — loop, short-circuits or failure path — sleeps."""
    gate = _section(_BRANCH_CLEANUP.read_text(encoding='utf-8'), _LANDING_GATE_SECTION)

    assert gate.strip(), f'section "{_LANDING_GATE_SECTION}" not found in {_BRANCH_CLEANUP}'
    assert not _SLEEP_INSTRUCTION.search(gate)


def test_every_settle_value_has_exactly_one_arm_naming_where_it_ends():
    """merged → post-merge tail; closed and dequeued → F2; timeout → F1, with the
    budget-left re-issue as its only non-terminal arm."""
    loop = _section(_BRANCH_CLEANUP.read_text(encoding='utf-8'), _LANDING_LOOP_SECTION)
    settle_arms = [ante for ante, _body in _arms(loop) if _SETTLE_IN_ANTECEDENT.search(ante)]

    assert len(settle_arms) >= len(_EXPECTED_SETTLE_ROUTING), (
        f'parsed {len(settle_arms)} settle arm(s) {settle_arms}, fewer than the '
        f'{len(_EXPECTED_SETTLE_ROUTING)} settle values the verb can return'
    )
    assert _settle_routing_defects(loop) == []


def test_a_settle_read_failure_ends_in_f3():
    """``status: error`` on the settle call fails closed into F3, never into a merge."""
    loop = _section(_BRANCH_CLEANUP.read_text(encoding='utf-8'), _LANDING_LOOP_SECTION)
    error_arms = [body for ante, body in _arms(loop) if '`status: error`' in ante]

    assert len(error_arms) == 1, f'expected one status: error arm, found {len(error_arms)}'
    assert _F_SUB_PATH.findall(error_arms[0]) == ['F3']


# --------------------------------------------------------------------------- #
# The GitLab merge-train short-circuit
# --------------------------------------------------------------------------- #


def test_gitlab_short_circuit_detector_fires_on_a_pre_fix_gate():
    """Matched negative control: a GitLab arm that polls ``pr view`` between sleeps
    and never routes to the failure path is reported on every count."""
    gate = _section(_PRE_FIX_GATE_DOC, _LANDING_GATE_SECTION)

    assert _gitlab_short_circuit(gate), 'the synthetic short-circuit was not read, so the control proves nothing'
    assert _gitlab_short_circuit_defects(gate) == [
        'the short-circuit does not route to the Landing-gate failure path',
        'the short-circuit does not end in Branch F1',
        'the short-circuit issues a pr view poll',
        'the short-circuit instructs a sleep',
    ]


def test_gitlab_short_circuit_detector_reports_an_absent_short_circuit():
    """A gate with no GitLab arm is a defect, not a vacuous pass."""
    without_gitlab_arm = _PRE_FIX_GATE_DOC.replace(_GITLAB_SHORT_CIRCUIT_MARKER, '**Short-circuit — other')
    gate = _section(without_gitlab_arm, _LANDING_GATE_SECTION)

    assert gate.strip(), 'the synthetic gate was not read, so the control proves nothing'
    assert _gitlab_short_circuit_defects(gate) == ['no GitLab merge-train short-circuit in the landing gate']


def test_gitlab_short_circuit_issues_no_wait_and_stops_via_f1():
    """The GitLab merge-train arm keys on ``provider: gitlab``, precedes the GitHub
    landing loop, issues no settle call, no ``pr view`` poll and no sleep, and routes
    to the Landing-gate failure path ending in Branch F1."""
    gate = _section(_BRANCH_CLEANUP.read_text(encoding='utf-8'), _LANDING_GATE_SECTION)

    assert gate.strip(), f'section "{_LANDING_GATE_SECTION}" not found in {_BRANCH_CLEANUP}'
    assert _gitlab_short_circuit_defects(gate) == []
    assert not _executed_blocks(_gitlab_short_circuit(gate)), 'the GitLab short-circuit issues a call'

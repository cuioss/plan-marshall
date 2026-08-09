#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Unit tests for the executor's dispatch-boundary non-zero-exit guard.

Background
----------
The executor (``.plan/execute-script.py``) emits a single
``[ERROR] (plan-marshall:execute-script:{exit_code})`` line to the plan's
``work.log`` every time a dispatched script exits non-zero. The emission is
implemented by ``emit_dispatch_failure_work_log`` in the executor template
and is guarded by three rules:

1. Successful dispatches (exit_code == 0) never call the function — that
   is enforced at the call site in ``main()`` and is exercised by
   ``test_execute_script.py``. These tests focus on the function's own
   behaviour.
2. Dispatching ``plan-marshall:manage-logging:manage-logging`` itself MUST
   be a no-op — otherwise a manage-logging failure that tried to log itself
   would recurse forever.
3. Exit code 2 is classified as ``argparse_rejection`` (Python's argparse
   convention) and every other non-zero exit code is classified as
   ``script_internal_failure``.

Approach
--------
The executor module is loaded via the helper from
``test_execute_script.py``. We replace ``executor.log_entry`` with a
``MagicMock`` so the function records each call without touching the file
system, then exercise the boundary function directly with synthetic
inputs (notation, exit code, stderr, args, audit-plan-id).

This keeps the tests fully hermetic — no temp directories, no subprocess,
no real plan structure — and pins down exactly which arguments
``log_entry`` would receive in production. The wider subprocess-level
behaviour is already covered by ``test_execute_script.py``;
this file is the unit-level guard around the boundary's three rules.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Import the executor-module loader from the sibling subprocess-test file.
sys.path.insert(0, str(Path(__file__).parent))
from test_execute_script import load_executor_module  # noqa: E402

# Notation used as a generic "normal" failing script in the tests below.
TEST_NOTATION = 'plan-marshall:manage-files:manage-files'

# Notation that MUST trigger the recursion guard in the boundary function.
MANAGE_LOGGING_NOTATION = 'plan-marshall:manage-logging:manage-logging'

# Stderr blob used by the happy-path failure tests. Kept short so the
# truncation rule is exercised by a dedicated test below rather than by
# every test in the file.
DEFAULT_STDERR = 'boom: something went wrong'

# Plan id forwarded as ``--plan-id`` in the dispatched-script args. Picked
# arbitrarily — the boundary function only cares that it can be extracted.
DEFAULT_PLAN_ID = 'unit-test-plan'


@pytest.fixture
def executor_with_mock_log_entry():
    """
    Load the executor module and swap out ``log_entry`` for a MagicMock.

    The fixture yields a tuple ``(executor, mock_log_entry)`` so each test
    can drive the boundary function via the real module API and then
    inspect the recorded calls without involving any disk I/O.
    """
    executor = load_executor_module()
    mock_log_entry = MagicMock()
    executor.log_entry = mock_log_entry
    return executor, mock_log_entry


def test_emit_records_script_internal_failure_for_exit_code_1(executor_with_mock_log_entry):
    """
    Exit code 1 lands a single ``log_entry`` call with
    ``failure_kind=script_internal_failure`` and the notation embedded
    verbatim into the message.
    """
    executor, mock_log_entry = executor_with_mock_log_entry

    executor.emit_dispatch_failure_work_log(
        notation=TEST_NOTATION,
        exit_code=1,
        stdout='',
        stderr=DEFAULT_STDERR,
        script_args=['read', '--plan-id', DEFAULT_PLAN_ID, '--file', 'foo.json'],
        audit_plan_id=None,
    )

    assert mock_log_entry.call_count == 1, (
        f'Expected exactly one log_entry call for exit_code=1, got {mock_log_entry.call_count}'
    )

    call_args = mock_log_entry.call_args
    positional = call_args.args
    assert positional[0] == 'work', f"Expected log_type='work', got {positional[0]!r}"
    assert positional[1] == DEFAULT_PLAN_ID, f"Expected plan_id={DEFAULT_PLAN_ID!r}, got {positional[1]!r}"
    assert positional[2] == 'ERROR', f"Expected level='ERROR', got {positional[2]!r}"

    message = positional[3]
    assert '[ERROR] (plan-marshall:execute-script:1)' in message, (
        f'Caller-prefix line did not embed exit code 1 in tag: {message!r}'
    )
    assert f'notation={TEST_NOTATION}' in message, f'Notation missing from message: {message!r}'
    assert 'exit_code=1' in message, f'exit_code=1 missing from message: {message!r}'
    assert 'failure_kind=script_internal_failure' in message, (
        f'Expected failure_kind=script_internal_failure in: {message!r}'
    )
    # With empty stdout, the detail field falls back to stderr (precedence 3).
    assert f'detail={DEFAULT_STDERR}' in message, f'stderr-derived detail missing from message: {message!r}'


def test_emit_records_script_internal_failure_for_unusual_exit_code(executor_with_mock_log_entry):
    """
    Any non-zero exit code that is NOT 2 maps to
    ``script_internal_failure``. Picks 42 as a representative non-1
    non-2 value to make sure the branch is not hard-coded to ``== 1``.
    """
    executor, mock_log_entry = executor_with_mock_log_entry

    executor.emit_dispatch_failure_work_log(
        notation=TEST_NOTATION,
        exit_code=42,
        stdout='',
        stderr=DEFAULT_STDERR,
        script_args=['--plan-id', DEFAULT_PLAN_ID],
        audit_plan_id=None,
    )

    assert mock_log_entry.call_count == 1
    message = mock_log_entry.call_args.args[3]
    assert 'exit_code=42' in message, f'exit_code=42 missing from: {message!r}'
    assert 'failure_kind=script_internal_failure' in message, (
        f'Unusual exit codes must still map to script_internal_failure: {message!r}'
    )
    assert '[ERROR] (plan-marshall:execute-script:42)' in message, (
        f'Caller-prefix line did not embed exit code 42: {message!r}'
    )


def test_emit_records_argparse_rejection_for_exit_code_2(executor_with_mock_log_entry):
    """
    Exit code 2 — Python's argparse convention for parse failures — maps
    to ``failure_kind=argparse_rejection`` and lands a single
    ``log_entry`` call with the canonical message shape.
    """
    executor, mock_log_entry = executor_with_mock_log_entry

    argparse_stderr = (
        "usage: manage-files.py [-h] ...\n"
        "manage-files.py: error: unrecognized arguments: --bogus"
    )

    executor.emit_dispatch_failure_work_log(
        notation=TEST_NOTATION,
        exit_code=2,
        stdout='',
        stderr=argparse_stderr,
        script_args=['read', '--plan-id', DEFAULT_PLAN_ID, '--bogus'],
        audit_plan_id=None,
    )

    assert mock_log_entry.call_count == 1, (
        f'Expected exactly one log_entry call for exit_code=2, got {mock_log_entry.call_count}'
    )

    positional = mock_log_entry.call_args.args
    assert positional[0] == 'work'
    assert positional[1] == DEFAULT_PLAN_ID
    assert positional[2] == 'ERROR'

    message = positional[3]
    assert 'exit_code=2' in message, f'exit_code=2 missing from message: {message!r}'
    assert 'failure_kind=argparse_rejection' in message, (
        f'Exit code 2 must classify as argparse_rejection: {message!r}'
    )
    assert '[ERROR] (plan-marshall:execute-script:2)' in message, (
        f'Caller-prefix line did not embed exit code 2: {message!r}'
    )
    # Newlines in the captured stderr must be collapsed so the work.log
    # entry stays single-line — this is part of the boundary's contract
    # and the most natural place to assert it.
    assert '\n' not in message, (
        f'Boundary message must be single-line; embedded newline found: {message!r}'
    )


def test_emit_suppresses_log_for_manage_logging_recursion_target(executor_with_mock_log_entry):
    """
    Dispatching ``plan-marshall:manage-logging:manage-logging`` itself
    with a non-zero exit code MUST NOT call ``log_entry`` — that would
    recurse into the executor and loop until the OS killed the process.

    This is the only suppression case: the notation is in
    ``_DISPATCH_FAILURE_SUPPRESS_NOTATIONS`` and the function returns
    before extracting the plan id.
    """
    executor, mock_log_entry = executor_with_mock_log_entry

    executor.emit_dispatch_failure_work_log(
        notation=MANAGE_LOGGING_NOTATION,
        exit_code=1,
        stdout='',
        stderr='manage-logging failed: bad arg',
        script_args=['work', '--plan-id', DEFAULT_PLAN_ID, '--level', 'INFO', '--message', 'x'],
        audit_plan_id=None,
    )

    assert mock_log_entry.call_count == 0, (
        f'manage-logging dispatch must NEVER call log_entry from the boundary '
        f'(recursion guard). Got {mock_log_entry.call_count} call(s).'
    )


def test_emit_suppresses_log_for_manage_logging_recursion_even_with_argparse_exit(
    executor_with_mock_log_entry,
):
    """
    The recursion guard fires independent of failure kind — exit code 2
    (argparse) on manage-logging is still suppressed. This pins the
    guard to the notation list, not to a particular exit-code class.
    """
    executor, mock_log_entry = executor_with_mock_log_entry

    executor.emit_dispatch_failure_work_log(
        notation=MANAGE_LOGGING_NOTATION,
        exit_code=2,
        stdout='',
        stderr="argparse: error",
        script_args=['work', '--plan-id', DEFAULT_PLAN_ID, '--bogus'],
        audit_plan_id=None,
    )

    assert mock_log_entry.call_count == 0, (
        f'manage-logging argparse failure must also be suppressed; got '
        f'{mock_log_entry.call_count} call(s).'
    )


def test_emit_uses_audit_plan_id_when_script_args_lack_plan_id(executor_with_mock_log_entry):
    """
    When the dispatched script's args do not carry ``--plan-id``, the
    boundary falls back to the executor's own ``--audit-plan-id`` flag.
    """
    executor, mock_log_entry = executor_with_mock_log_entry

    executor.emit_dispatch_failure_work_log(
        notation=TEST_NOTATION,
        exit_code=1,
        stdout='',
        stderr=DEFAULT_STDERR,
        script_args=['read', '--file', 'foo.json'],
        audit_plan_id='audit-fallback-plan',
    )

    assert mock_log_entry.call_count == 1
    positional = mock_log_entry.call_args.args
    assert positional[1] == 'audit-fallback-plan', (
        f"Expected audit_plan_id fallback to be used, got plan_id={positional[1]!r}"
    )


def test_emit_drops_entry_when_no_plan_id_available(executor_with_mock_log_entry):
    """
    When neither the dispatched-script args nor ``audit_plan_id`` carry
    a plan id, work.log is plan-scoped and unwritable — the entry is
    dropped silently. The script-execution.log entry (handled elsewhere
    by ``log_script_execution``) still records the failure globally.
    """
    executor, mock_log_entry = executor_with_mock_log_entry

    executor.emit_dispatch_failure_work_log(
        notation=TEST_NOTATION,
        exit_code=1,
        stdout='',
        stderr=DEFAULT_STDERR,
        script_args=['read', '--file', 'foo.json'],
        audit_plan_id=None,
    )

    assert mock_log_entry.call_count == 0, (
        f'Boundary must drop the entry when no plan_id is available; got '
        f'{mock_log_entry.call_count} call(s).'
    )


def test_emit_truncates_long_detail_to_configured_limit(executor_with_mock_log_entry):
    """
    Detail text longer than ``_DISPATCH_FAILURE_DETAIL_LIMIT`` is
    truncated with the ``...[truncated]`` sentinel so a single failed
    dispatch can't dominate the plan's work.log. Here stdout is empty, so
    the oversized stderr is the chosen detail stream (precedence 3).
    """
    executor, mock_log_entry = executor_with_mock_log_entry

    limit = executor._DISPATCH_FAILURE_DETAIL_LIMIT
    oversized = 'A' * (limit + 200)

    executor.emit_dispatch_failure_work_log(
        notation=TEST_NOTATION,
        exit_code=1,
        stdout='',
        stderr=oversized,
        script_args=['--plan-id', DEFAULT_PLAN_ID],
        audit_plan_id=None,
    )

    assert mock_log_entry.call_count == 1
    message = mock_log_entry.call_args.args[3]
    assert '...[truncated]' in message, f'Truncation sentinel missing from oversized detail: {message!r}'
    # The retained detail slice should be exactly the configured limit.
    # The message also embeds non-detail fragments (notation, exit_code, ...)
    # so we assert the slice length indirectly: the run of leading 'A's
    # preceding the sentinel equals ``limit``.
    a_run = 'A' * limit
    assert a_run in message, f'Expected exactly {limit} A characters before the truncation sentinel'
    assert ('A' * (limit + 1)) not in message, (
        f'detail appears longer than the configured limit of {limit} characters: {message!r}'
    )


# =============================================================================
# Pre-spawn rejection — the payload, the exit code, and the work.log detail
# =============================================================================
#
# The refusal deliberately reuses the boundary this file already tests rather
# than adding a parallel reporting path. These tests pin the three properties
# that reuse depends on:
#
#   1. the payload is a parseable ``status: error`` TOON carrying a NON-EMPTY
#      corrective — an unparseable or empty payload would leave the caller with
#      the same nothing it had before the feature;
#   2. the exit code is 2, which the EXISTING classifier already maps to
#      ``argparse_rejection`` — a rejection is an argparse rejection, decided
#      one layer earlier;
#   3. the work.log line carries the corrective as its ``detail=``, which the
#      boundary's stdout-TOON-message precedence yields with NO second code
#      path. That precedence is the reason no new reporting code was written,
#      so it is asserted rather than assumed.

_REJECTION_NOTATION = 'plan-marshall:manage-tasks:manage-tasks'

# Synthetic argparse-surface node shared by the pinning tests below. Mirrors
# the shape ``_resolve_invocation`` builds from a real derived surface:
# ``children`` maps verb name to its own node, ``alias_of`` maps an alias
# child name to the canonical verb it groups under.
_VERB_NODE: dict[str, dict] = {
    'children': {'get': {}, 'list': {}, 'read': {}},
    'alias_of': {'get': 'read'},
}


def _rejection_payload(executor, token: str = 'reed') -> str:
    """Render a representative refusal through the production renderer.

    The corrective is derived by calling ``_corrective_for_verb`` — the same
    function a real pre-spawn rejection calls — rather than a hand-built
    literal. A hand-built literal can drift from what the function actually
    produces for the paired token (see the ``script-call-drift`` finding this
    fixture replaced: a ``nuke``/``read`` pairing that ``_corrective_for_verb``
    never emits, because ``nuke`` falls outside the edit-distance threshold and
    takes the no-suggestion branch instead).
    """
    corrective = executor._corrective_for_verb(_REJECTION_NOTATION, [], token, _VERB_NODE)
    return str(
        executor._render_rejection_toon(
            _REJECTION_NOTATION,
            {
                'reason': 'unknown_verb',
                'token': token,
                'corrective': corrective,
                'accepted': sorted(_VERB_NODE['children']),
            },
        )
    )


def test_rejection_payload_parses_as_toon_with_status_error(executor_with_mock_log_entry):
    """The payload must be machine-readable by the project's own TOON parser."""
    executor, _mock = executor_with_mock_log_entry
    from toon_parser import parse_toon

    parsed = parse_toon(_rejection_payload(executor))

    assert parsed['status'] == 'error'
    assert parsed['error'] == 'invalid_invocation'
    assert parsed['notation'] == _REJECTION_NOTATION
    assert parsed['reason'] == 'unknown_verb'
    assert parsed['rejected'] == 'reed'


def test_rejection_payload_carries_a_non_empty_corrective(executor_with_mock_log_entry):
    """A refusal without a correction is the empty stdout this feature replaces."""
    executor, _mock = executor_with_mock_log_entry
    from toon_parser import parse_toon

    message = parse_toon(_rejection_payload(executor))['message']

    assert isinstance(message, str)
    assert message.strip(), 'the corrective must not be blank'
    assert 'read' in message, f'the corrective must name the canonical form: {message!r}'


def test_exit_code_two_classifies_as_argparse_rejection(executor_with_mock_log_entry):
    """Exit 2 routes the refusal through the EXISTING classifier, unchanged."""
    executor, _mock = executor_with_mock_log_entry

    assert executor._classify_dispatch_failure(2) == 'argparse_rejection'


def test_work_log_detail_carries_the_corrective_via_stdout_precedence(
    executor_with_mock_log_entry,
):
    """The corrective reaches work.log through the boundary's option-A precedence.

    No second reporting path: the refusal writes its TOON to stdout, and the
    boundary's existing "prefer a ``status: error`` stdout ``message``" rule
    lifts the corrective into ``detail=``. Asserting it here is what lets the
    rejection path own no reporting code of its own.
    """
    executor, mock_log_entry = executor_with_mock_log_entry
    payload = _rejection_payload(executor)

    executor.emit_dispatch_failure_work_log(
        notation=_REJECTION_NOTATION,
        exit_code=2,
        stdout=payload,
        stderr='',
        script_args=['reed', '--plan-id', DEFAULT_PLAN_ID],
        audit_plan_id=None,
    )

    assert mock_log_entry.call_count == 1
    message = mock_log_entry.call_args.args[3]
    assert 'failure_kind=argparse_rejection' in message
    assert 'detail=Use `plan-marshall:manage-tasks:manage-tasks read`' in message, (
        f'the corrective did not reach detail= via stdout precedence: {message!r}'
    )
    assert 'detail=' in message and not message.rstrip().endswith('detail='), (
        f'detail= must not be blank on a rejection: {message!r}'
    )


# =============================================================================
# ``_corrective_for_verb`` — the three documented message forms, pinned to the
# function's real output rather than transcribed by hand (SKILL.md § "Pre-spawn
# invocation rejection"). Each positive case is paired with a control so the
# pin cannot pass vacuously — the control proves the assertion actually
# discriminates between the three shapes instead of matching by coincidence.
# =============================================================================


def test_corrective_for_verb_nearest_spelling_form(executor_with_mock_log_entry):
    """A token within the edit-distance threshold, matching a NON-alias verb.

    ``reed`` is 1 edit away from ``read``, well inside
    ``max(2, len(token) // 2)`` — the documented "bare nearest spelling" form.
    """
    executor, _mock = executor_with_mock_log_entry

    corrective = executor._corrective_for_verb(_REJECTION_NOTATION, [], 'reed', _VERB_NODE)

    assert corrective == (
        "Use `plan-marshall:manage-tasks:manage-tasks read` — "
        "registered: ['get', 'list', 'read']"
    )
    # Control: this form never mentions an alias relation.
    assert 'alias of' not in corrective, f'nearest-spelling form must not phrase an alias: {corrective!r}'


def test_corrective_for_verb_alias_of_form(executor_with_mock_log_entry):
    """A token within threshold whose closest match IS a registered alias.

    ``gett`` is 1 edit away from ``get``, which ``_VERB_NODE['alias_of']``
    maps to the canonical verb ``read`` — the documented alias-of relation.
    """
    executor, _mock = executor_with_mock_log_entry

    corrective = executor._corrective_for_verb(_REJECTION_NOTATION, [], 'gett', _VERB_NODE)

    assert corrective == (
        "Use `plan-marshall:manage-tasks:manage-tasks get` (an alias of `read`) — "
        "registered: ['get', 'list', 'read']"
    )


def test_corrective_for_verb_no_suggestion_form(executor_with_mock_log_entry):
    """A token outside the edit-distance threshold for every registered verb.

    ``nuke`` is >= 4 edits from every child of ``_VERB_NODE`` (``get``,
    ``list``, ``read``), past ``max(2, len('nuke') // 2) == 2`` — the
    documented no-suggestion fallback. This is the NORMAL shape for an
    invented verb, not an omission, so it is pinned as a first-class case.
    """
    executor, _mock = executor_with_mock_log_entry

    corrective = executor._corrective_for_verb(_REJECTION_NOTATION, [], 'nuke', _VERB_NODE)

    assert corrective == (
        "Use a registered verb for `plan-marshall:manage-tasks:manage-tasks`: "
        "['get', 'list', 'read']"
    )
    # Control: unlike the other two forms, this one names no single suggested
    # verb in backticks immediately after the notation — proving the pin
    # actually distinguishes the no-suggestion branch rather than matching
    # any string that happens to list the registered verbs.
    assert '` (an alias of' not in corrective
    assert not corrective.startswith('Use `plan-marshall:manage-tasks:manage-tasks get`')
    assert not corrective.startswith('Use `plan-marshall:manage-tasks:manage-tasks read`')


def test_closest_spelling_threshold_separates_the_three_tokens(executor_with_mock_log_entry):
    """Matched control: pins the edit-distance threshold driving all three forms.

    Directly exercises ``_closest_spelling`` (the function ``_corrective_for_verb``
    delegates to) so the three correctives above are shown to diverge for the
    documented reason — a threshold crossing — and not for an unrelated one.
    """
    executor, _mock = executor_with_mock_log_entry
    children = sorted(_VERB_NODE['children'])

    assert executor._closest_spelling('reed', children) == 'read'
    assert executor._closest_spelling('gett', children) == 'get'
    assert executor._closest_spelling('nuke', children) is None


def test_validator_returns_none_when_the_notation_has_no_surface(executor_with_mock_log_entry):
    """Absent knowledge is not a rejection — the unit-level fail-open guard."""
    executor, _mock = executor_with_mock_log_entry

    assert executor._validate_invocation('bundle:skill:unmapped', ['anything']) is None


# =============================================================================
# ``unknown_flag`` — the two documented message forms (SKILL.md § "Pre-spawn
# invocation rejection"), pinned to ``_validate_invocation``'s real output the
# same way the verb correctives above are pinned. SKILL.md named only the
# fallback form before this fix; the nearest-spelling form below is the one a
# typo'd flag actually hits — the common case the feature exists for — so it
# is pinned as a first-class case, not an afterthought.
# =============================================================================

_FLAG_REJECTION_NOTATION = 'plan-marshall:manage-tasks:manage-tasks'

# Mirrors the shape a real derived surface has: a root with no flags of its
# own and one leaf (``read``) declaring the two flags the correctives below
# are computed against.
_FLAG_SURFACE_ROOT: dict = {
    'flags': [],
    'required_flags': [],
    'flag_arity': {},
    'alias_of': {},
    'flags_confident': True,
    'children_confident': True,
    'children': {
        'read': {
            'flags': ['plan-id', 'task-number'],
            'required_flags': [],
            'flag_arity': {'plan-id': 1, 'task-number': 1},
            'alias_of': {},
            'flags_confident': True,
            'children_confident': True,
            'children': {},
        },
    },
}


def _install_flag_surface(executor) -> None:
    """Point the loaded module's ``SCRIPT_SURFACES`` global at the fixture above."""
    executor.SCRIPT_SURFACES = {
        _FLAG_REJECTION_NOTATION: {
            'digest': 'test',
            'surface': {'root': _FLAG_SURFACE_ROOT},
        }
    }


def test_unknown_flag_corrective_nearest_spelling_form(executor_with_mock_log_entry):
    """A flag token within the edit-distance threshold names the nearest declared flag.

    ``--plna-id`` is 2 edits from ``plan-id``, well inside
    ``max(2, len(token) // 2) == 3`` — the undocumented form the live executor
    actually emits for a typo'd flag.
    """
    executor, _mock = executor_with_mock_log_entry
    _install_flag_surface(executor)

    rejection = executor._validate_invocation(
        _FLAG_REJECTION_NOTATION, ['read', '--plna-id', 'x']
    )

    assert rejection is not None
    assert rejection['reason'] == 'unknown_flag'
    assert rejection['corrective'] == (
        "Use `--plan-id` for `plan-marshall:manage-tasks:manage-tasks read` — "
        "declared: ['plan-id', 'task-number']"
    )
    # Control: the nearest-spelling form never falls back to the whole set.
    assert 'Use a declared flag for' not in rejection['corrective']


def test_unknown_flag_corrective_no_suggestion_form(executor_with_mock_log_entry):
    """A flag token outside the edit-distance threshold falls back to the whole declared set.

    This is the ONLY form SKILL.md documented before this fix — but it is the
    RARER branch: the nearest-spelling form above is what a real typo hits.
    """
    executor, _mock = executor_with_mock_log_entry
    _install_flag_surface(executor)

    rejection = executor._validate_invocation(
        _FLAG_REJECTION_NOTATION, ['read', '--zzzzzzzzzzzz', 'x']
    )

    assert rejection is not None
    assert rejection['reason'] == 'unknown_flag'
    assert rejection['corrective'] == (
        "Use a declared flag for `plan-marshall:manage-tasks:manage-tasks read`: "
        "['plan-id', 'task-number']"
    )
    # Control: the fallback form never names a single suggested flag.
    assert not rejection['corrective'].startswith('Use `--')


def test_unknown_flag_closest_spelling_threshold_separates_the_two_forms(
    executor_with_mock_log_entry,
):
    """Matched control: pins the edit-distance threshold driving both forms.

    Directly exercises ``_closest_spelling`` — the SAME function the verb-level
    correctives delegate to — so the two flag correctives above are shown to
    diverge for the documented reason (a threshold crossing) and not for an
    unrelated one.
    """
    executor, _mock = executor_with_mock_log_entry
    declared = ['plan-id', 'task-number']

    assert executor._closest_spelling('plna-id', declared) == 'plan-id'
    assert executor._closest_spelling('zzzzzzzzzzzz', declared) is None


# =============================================================================
# The argv walk — one pass that tokenizes and resolves together
# =============================================================================
#
# These drive ``_resolve_invocation`` directly, one property per test, because
# the subprocess-level tests in test_execute_script.py can only observe the
# walk's VERDICT (spawn / refuse). Which node the walk landed on, and how many
# tokens each flag consumed getting there, are the things that actually broke —
# and both are invisible from the verdict when a wrong node happens to accept.

_ROOT_WITH_ROUTING_FLAGS = {
    'flags': ['project-dir', 'verbose'],
    'required_flags': [],
    'flag_arity': {'project-dir': 1, 'verbose': 0},
    'alias_of': {},
    'flags_confident': True,
    'children_confident': True,
    'children': {
        'plan': {
            'flags': [],
            'required_flags': [],
            'flag_arity': {},
            'alias_of': {},
            'flags_confident': True,
            'children_confident': True,
            'children': {
                'get': {
                    'flags': ['field'],
                    'required_flags': [],
                    'flag_arity': {'field': 1},
                    'alias_of': {},
                    'flags_confident': True,
                    'children_confident': True,
                    'children': {},
                }
            },
        }
    },
}


def test_walk_steps_over_a_routing_flag_value_and_reaches_the_leaf(
    executor_with_mock_log_entry,
):
    """The headline regression, asserted on the RESOLVED NODE rather than the verdict."""
    executor, _mock = executor_with_mock_log_entry

    resolution, rejection = executor._resolve_invocation(
        'test:skill:script',
        _ROOT_WITH_ROUTING_FLAGS,
        ['--project-dir', '/x', 'plan', 'get', '--field', 'compatibility'],
    )

    assert rejection is None, rejection
    assert resolution is not None
    assert resolution['chain'] == ['plan', 'get'], (
        f"the routing flag's value swallowed the verb path; got "
        f'{resolution["chain"]!r}'
    )
    assert resolution['flags'] == ['project-dir', 'field']
    assert 'field' in resolution['inherited'], (
        'the leaf-declared flag is missing from the accept-set, so the walk '
        'resolved a shallower node than it reached'
    )


def test_walk_does_not_step_over_a_bare_switch(executor_with_mock_log_entry):
    """A zero-arity flag consumes nothing, so the next token IS the verb."""
    executor, _mock = executor_with_mock_log_entry

    resolution, rejection = executor._resolve_invocation(
        'test:skill:script', _ROOT_WITH_ROUTING_FLAGS, ['--verbose', 'plan', 'get']
    )

    assert rejection is None
    assert resolution['chain'] == ['plan', 'get'], (
        f'a bare switch consumed the verb behind it; got {resolution["chain"]!r}'
    )


def test_walk_treats_an_equals_joined_flag_as_binding_no_token(
    executor_with_mock_log_entry,
):
    executor, _mock = executor_with_mock_log_entry

    resolution, _rejection = executor._resolve_invocation(
        'test:skill:script', _ROOT_WITH_ROUTING_FLAGS, ['--project-dir=/x', 'plan', 'get']
    )

    assert resolution['chain'] == ['plan', 'get']
    assert resolution['flags'] == ['project-dir']


def test_walk_never_binds_a_following_flag_token_as_a_value(
    executor_with_mock_log_entry,
):
    """Declared arity does not override argparse's own "a flag ends a value" rule."""
    executor, _mock = executor_with_mock_log_entry

    resolution, _rejection = executor._resolve_invocation(
        'test:skill:script',
        _ROOT_WITH_ROUTING_FLAGS,
        ['--project-dir', '--verbose', 'plan', 'get'],
    )

    assert resolution['chain'] == ['plan', 'get'], (
        f'an arity-1 flag consumed the FLAG that followed it and then lost the '
        f'verb path; got {resolution["chain"]!r}'
    )
    assert resolution['flags'] == ['project-dir', 'verbose']


def test_walk_abandons_when_an_unknown_arity_flag_precedes_a_verb(
    executor_with_mock_log_entry,
):
    """Both readings resolve different nodes, so neither may be assumed.

    ``--mystery`` is on neither the derived arity map nor the structural
    allowlist, which is what makes its arity genuinely unknowable here.
    """
    executor, _mock = executor_with_mock_log_entry
    root = dict(_ROOT_WITH_ROUTING_FLAGS, flags=['mystery'], flag_arity={})

    resolution, rejection = executor._resolve_invocation(
        'test:skill:script', root, ['--mystery', 'plan', 'get']
    )

    assert (resolution, rejection) == (None, None), (
        'an unknowable arity in front of a verb must abandon the walk, not '
        f'guess: got {resolution!r} / {rejection!r}'
    )


def test_walk_resolves_an_allowlisted_flag_arity_the_surface_does_not_declare(
    executor_with_mock_log_entry,
):
    """The structural allowlist is the fallback that keeps the common shape precise.

    ``--project-dir`` is honoured on every subcommand but is frequently rendered
    in no node's help, so the derived map has no arity for it. Without the
    allowlist fallback the single most common dispatch shape in the tree would
    degrade to an unvalidated spawn — the pair with the test above is what shows
    the fallback WIDENS knowledge rather than replacing the derivation.
    """
    executor, _mock = executor_with_mock_log_entry
    root = dict(_ROOT_WITH_ROUTING_FLAGS, flag_arity={})

    resolution, rejection = executor._resolve_invocation(
        'test:skill:script', root, ['--project-dir', '/x', 'plan', 'get']
    )

    assert rejection is None
    assert resolution['chain'] == ['plan', 'get']


def test_walk_reports_an_unregistered_verb_with_the_parent_accept_set(
    executor_with_mock_log_entry,
):
    executor, _mock = executor_with_mock_log_entry

    resolution, rejection = executor._resolve_invocation(
        'test:skill:script', _ROOT_WITH_ROUTING_FLAGS, ['--project-dir', '/x', 'nuke']
    )

    assert resolution is None
    assert rejection['reason'] == 'unknown_verb'
    assert rejection['token'] == 'nuke'
    assert rejection['accepted'] == ['plan']


def test_always_accepted_flags_and_their_arity_share_one_definition(
    executor_with_mock_log_entry,
):
    """The allowlist and its arity map cannot drift apart — they are one object."""
    executor, _mock = executor_with_mock_log_entry

    assert set(executor._ALWAYS_ACCEPTED_FLAGS) == set(
        executor._ALWAYS_ACCEPTED_FLAG_ARITY
    )
    assert executor._ALWAYS_ACCEPTED_FLAG_ARITY['project-dir'] == 1
    assert executor._ALWAYS_ACCEPTED_FLAG_ARITY['help'] == 0

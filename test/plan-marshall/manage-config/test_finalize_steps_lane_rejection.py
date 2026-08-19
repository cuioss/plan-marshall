#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``finalize-steps set-lane`` rejection routes instead of dead-ending.

``set-lane`` writes a deliberately NARROW value set — the resolved operator
answers ``off`` / ``standard`` / ``full`` — while the per-element override value
space the composer READS is five wide, adding the seed values ``minimal`` and
``ask``. That narrowing is defended in the handler's own docstring and documented
as deliberate in ``doc/user/configuration.adoc``, so it stays.

What did NOT stay is the shape of the refusal. The narrowing was enforced by an
argparse ``choices=``, whose rejection is a bare *"invalid choice: 'minimal'"* at
exit 2. For a value that is genuinely not a lane value that message is fine; for
``minimal`` and ``ask`` it is actively misleading — both ARE per-element lane
values the composer honours, reachable through the generic
``step set --step-id <id> --param lane --value <value>`` verb, which writes the
``lane`` param without narrowing the value space. An operator asking for one is
using the wrong verb, not asking for something unsupported, and the old message
could not say so.

Covered here:

- Every reader-enum value this verb refuses is refused with a message NAMING the
  route that works.
- A value that is not a lane value at all is still refused, and still names the
  route (it is the answer to "then how do I set one?" either way).
- ``_READER_LANE_VALUES`` — the mirror this module's messages quote — equals the
  composer's authoritative ``_manifest_lanes.LANE_OVERRIDES``. A hand-maintained
  mirror that drifts would make every message above quote a value space nothing
  reads.
- The CLI reaches the handler at all: with an argparse ``choices=`` still in
  place, ``--lane minimal`` would die at exit 2 and no handler message could ever
  be seen.
- **The canonical-invocations block still names the writer's value set.** Removing
  ``choices=`` did not only change where the refusal comes from — it silently
  retired a live binding. The ``canonical-enum-choices-drift`` plugin-doctor rule
  reads a documented ``{a|b|c}`` enum in a skill's ``## Canonical invocations``
  block and compares it against the flag's argparse ``choices=``; with no
  ``choices=`` to resolve, that analyzer takes its fail-closed no-authority branch
  and SKIPs. It reports clean over a flag it no longer examines. This module
  replaces the lost binding directly, so the documented enum stays checked rather
  than becoming an unbound restatement — the exact defect class the plan this test
  belongs to exists to close, and ``set-lane --lane`` was that rule's own driving
  example.
"""

import re
from argparse import Namespace
from pathlib import Path

from _manage_config_fixtures import SCRIPT_PATH, create_marshal_json

from conftest import load_script_module, run_script

_cmd_mod = load_script_module(
    'plan-marshall', 'manage-config', '_cmd_finalize_steps.py', module_name='_cmd_finalize_steps'
)
cmd_finalize_steps_set_lane = _cmd_mod.cmd_finalize_steps_set_lane
_reject_lane_value = _cmd_mod._reject_lane_value
_RESOLVED_ASK_LANE_VALUES = _cmd_mod._RESOLVED_ASK_LANE_VALUES
_READER_LANE_VALUES = _cmd_mod._READER_LANE_VALUES

_lanes_mod = load_script_module(
    'plan-marshall',
    'manage-execution-manifest',
    '_manifest_lanes.py',
    module_name='_manifest_lanes',
)

#: A finalize step every discovery run knows about, used as the set-lane target.
_LANE_STEP_ID = 'plan-marshall:automatic-review'

#: The substring that IS the fix: the verb an operator should reach for instead.
_ROUTE_MARKER = 'step set'


def test_the_reader_enum_mirror_matches_the_composer_authority():
    """The quoted value space is the one the composer actually reads.

    ``_READER_LANE_VALUES`` is a mirror held in the writer module so a rejection
    can classify the refused value. Every message below quotes it, so a mirror
    that drifted from ``LANE_OVERRIDES`` would route operators toward a value
    space nothing honours — the same restated-fact defect the narrow/wide split
    already caused once.
    """
    assert set(_READER_LANE_VALUES) == set(_lanes_mod.LANE_OVERRIDES), (
        f'_cmd_finalize_steps._READER_LANE_VALUES {sorted(_READER_LANE_VALUES)} has '
        f'drifted from the composer authority _manifest_lanes.LANE_OVERRIDES '
        f'{sorted(_lanes_mod.LANE_OVERRIDES)}.'
    )


def test_the_writer_set_is_a_proper_subset_of_the_reader_set():
    """The narrowing this module is about is real, and it is a NARROWING.

    Without this, a refactor that widened the writer to the reader set would leave
    every routing message below describing a distinction that no longer exists,
    and each would still pass by asserting only on a substring.
    """
    assert set(_RESOLVED_ASK_LANE_VALUES) < set(_READER_LANE_VALUES)


def test_every_refused_reader_value_names_the_route_that_works():
    """A value the composer honours but this verb will not write routes onward."""
    refused = set(_READER_LANE_VALUES) - set(_RESOLVED_ASK_LANE_VALUES)
    assert refused, 'no reader value is refused, so this assertion is vacuous'

    for lane in sorted(refused):
        message = _reject_lane_value(lane)
        assert _ROUTE_MARKER in message, (
            f'the rejection of {lane!r} does not name the `{_ROUTE_MARKER}` route, so '
            f'it dead-ends an operator asking for a value that IS writable: {message}'
        )
        assert lane in message, f'the rejection does not name the value refused: {message}'


def test_a_non_lane_value_is_still_refused_and_still_routed():
    """A typo is refused too, and the message still answers "then how?"."""
    message = _reject_lane_value('nonsense')

    assert 'nonsense' in message
    assert _ROUTE_MARKER in message
    assert 'invalid lane' in message


def test_an_accepted_value_is_never_passed_to_the_rejection_builder():
    """Guards the branch: the builder must not describe an accepted value as refused.

    ``_reject_lane_value`` is only ever called off the failing branch, so this
    pins the classification rather than the call site — a builder that emitted the
    reader-valid text for ``off`` would mean the two branches had collapsed.
    """
    for lane in _RESOLVED_ASK_LANE_VALUES:
        assert 'not one this verb writes' in _reject_lane_value(lane), (
            f'{lane!r} is in the writer set, so if it ever reached the builder it '
            f'must take the reader-valid branch, not the invalid-value branch.'
        )


def test_handler_refuses_minimal_with_the_routed_message(plan_context):
    """End to end through the handler: the refusal an operator actually sees."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_finalize_steps_set_lane(
        Namespace(step_id=_LANE_STEP_ID, lane='minimal', plan_id=None)
    )

    assert result['status'] == 'error'
    assert _ROUTE_MARKER in result['error']


def test_cli_reaches_the_handler_instead_of_dying_at_argparse(plan_context):
    """No argparse ``choices=`` narrows ``--lane``, so the handler owns the refusal.

    This is the assertion the fix turns on. With ``choices=`` in place the CLI exits
    2 with argparse's own bare "invalid choice" text and the handler is never
    entered, so no routing message can reach the operator however well it is
    written.
    """
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(
        SCRIPT_PATH, 'finalize-steps', 'set-lane',
        '--step-id', _LANE_STEP_ID, '--lane', 'minimal',
    )

    combined = f'{result.stdout}\n{result.stderr}'
    assert 'invalid choice' not in combined, (
        f'argparse rejected --lane before the handler ran, so the routed message is '
        f'unreachable: {combined}'
    )
    # The refusal rides `status: error`, not the exit code: manage-config's `main`
    # returns 0 after printing any result, so every validation error in this script
    # signals on the TOON. Moving this check off argparse moved it onto the same
    # channel its siblings (unknown step id, uninitialized marshal) already used.
    assert 'status: error' in combined, (
        f'a refused write must not report success: {combined}'
    )
    assert _ROUTE_MARKER in combined, (
        f'the CLI refusal does not name the `{_ROUTE_MARKER}` route: {combined}'
    )


# ---------------------------------------------------------------------------
# The canonical-invocations block, bound in place of the retired analyzer check
# ---------------------------------------------------------------------------

#: The skill doc whose ``## Canonical invocations`` block documents the verb.
_MANAGE_CONFIG_SKILL = (
    Path(__file__).parents[3]
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-config' / 'SKILL.md'
)

#: The documented ``--lane {a,b,c}`` enum inside the canonical ``set-lane`` block.
_DOCUMENTED_LANE_ENUM = re.compile(r'--lane\s*\{([^}]+)\}')


def _documented_lane_values() -> list[str]:
    """The values the canonical `set-lane` invocation block documents for `--lane`.

    Anchored to the ``### finalize-steps set-lane`` section so a ``--lane`` enum
    documented for some other verb cannot be read in its place.
    """
    text = _MANAGE_CONFIG_SKILL.read_text(encoding='utf-8')
    section = re.search(
        r'^### finalize-steps set-lane$(.*?)(?=^### |\Z)', text, re.MULTILINE | re.DOTALL
    )
    assert section, (
        f'{_MANAGE_CONFIG_SKILL.name} carries no "### finalize-steps set-lane" canonical '
        f'section, so the documented enum cannot be located and this binding would be vacuous.'
    )
    match = _DOCUMENTED_LANE_ENUM.search(section.group(1))
    assert match, (
        'The canonical set-lane block documents no `--lane {…}` enum. If the enum was '
        'deliberately removed, remove this binding too — but do not leave the block naming '
        'values that nothing checks.'
    )
    return [value.strip() for value in match.group(1).split(',') if value.strip()]


def test_the_documented_enum_is_locatable():
    """Anti-vacuity: the extraction must find something for the equality to mean anything."""
    assert _documented_lane_values(), 'no values extracted from the canonical block'


def test_the_section_anchor_excludes_a_neighbouring_verbs_enum(tmp_path):
    """The extraction is section-anchored, not first-match in the file.

    Without the anchor a ``--lane`` enum documented for any other verb earlier in
    the file would be read instead, and the equality below would compare the
    writer set against an unrelated block — green or red for the wrong reason.
    """
    doc = tmp_path / 'SKILL.md'
    doc.write_text(
        '### some-other-verb\n\n```bash\nx --lane {alpha,beta}\n```\n\n'
        '### finalize-steps set-lane\n\n```bash\ny --lane {off,standard,full}\n```\n',
        encoding='utf-8',
    )
    section = re.search(
        r'^### finalize-steps set-lane$(.*?)(?=^### |\Z)',
        doc.read_text(encoding='utf-8'),
        re.MULTILINE | re.DOTALL,
    )
    assert section
    match = _DOCUMENTED_LANE_ENUM.search(section.group(1))
    assert match and match.group(1) == 'off,standard,full', (
        'the anchored extraction picked up a neighbouring verb\'s enum'
    )


def test_canonical_block_enum_equals_the_writer_set():
    """The documented `--lane` enum equals the values this verb actually writes.

    This is the assertion the ``canonical-enum-choices-drift`` analyzer used to
    make from ``choices=``. That flag no longer declares one, so the analyzer takes
    its fail-closed no-authority branch and SKIPs — leaving the documented enum
    bound to nothing, which is a hand-maintained mirror of a Python constant and
    precisely what that rule exists to catch.
    """
    documented = _documented_lane_values()

    assert documented == list(_RESOLVED_ASK_LANE_VALUES), (
        f'The canonical `finalize-steps set-lane` block documents `--lane '
        f'{{{",".join(documented)}}}` while the verb writes '
        f'{list(_RESOLVED_ASK_LANE_VALUES)}. The `## Canonical invocations` block is read as '
        f'SOURCE OF TRUTH by other consumers, so a divergence here sends a caller to a value '
        f'the handler refuses — or hides one it accepts.'
    )

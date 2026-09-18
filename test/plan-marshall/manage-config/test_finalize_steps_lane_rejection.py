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

A SECOND, independent rejection axis is covered in the closing section: an ``off``
the target element's CLASS makes inert. The first axis asks "does this verb write
that value?"; the second asks "can that value take effect on that step?". Both
channels are asserted, plus the matched positive control (a non-immune element
still accepts ``off``) and the fail-toward-permitting case (an unresolvable class
is permitted, never refused).

Test scope for that second axis — RE-DERIVED, with every divergence resolved
------------------------------------------------------------------------------

The scope was re-derived at execution time by sweeping the ``test`` category for
each changed symbol, rather than carried forward from planning. The union was:

- ``_materialize_finalize_lanes`` → ``test_sync_defaults.py``
- ``cmd_finalize_steps_set_lane`` → ``test_cmd_ceremony_policy.py``,
  ``test_cmd_finalize_steps.py``, THIS module
- ``_reject_lane_value`` → THIS module
- ``_resolve_finalize_step_lane`` → no test-category consumer (it was a private
  helper of ``_cmd_sync_defaults``; this deliverable moves it to
  ``_cmd_quality_phases`` and both writers now import it from there)
- ``_inert_off_refusal`` (new) → no consumer yet, by construction

Two divergences from the planned four-file scope, each resolved rather than
silently absorbed:

- ``test_cmd_quality_phases.py`` is IN scope but names none of those symbols. It
  mirrors ``_cmd_quality_phases``, the module that gains both the moved resolver
  and the new ``param == 'lane'`` branch of ``_cmd_step``'s set path, so the
  generic writer's refusal is asserted there.
- ``test_cmd_ceremony_policy.py`` is in the symbol union but is NOT updated. It
  calls ``cmd_finalize_steps_set_lane`` to drive ceremony-gate policy, and every
  target it writes is a ceremony owner (``pre-push-quality-gate`` /
  ``pre-submission-self-review`` / ``finalize-step-simplify`` /
  ``finalize-step-security-audit``); an ``off`` on any of them is unaffected by
  this refusal, so the file needs no change and its green run is real coverage of
  the positive direction rather than an omission.

Two further ``lane…off``-bearing files, resolved as EXCLUDED with reason:

- ``test_config_defaults.py`` — it pins the finalize-step SEED in
  ``_config_defaults.py``, which this deliverable does not edit. The seed's
  ``default_on:false → lane:off`` rule is a different rule from the
  materializer's provenance fill and is unchanged.
- ``test_manage_config_cli.py`` — it exercises the CLI plumbing of the verb
  surfaces, not lane semantics; no assertion in it depends on which values a lane
  writer accepts.
"""

import json
import re
from argparse import Namespace
from pathlib import Path

from _manage_config_fixtures import SCRIPT_PATH, create_marshal_json

from conftest import get_skill_dir, load_script_module, run_script

_cmd_mod = load_script_module(
    'plan-marshall', 'manage-config', '_cmd_finalize_steps.py', module_name='_cmd_finalize_steps'
)
cmd_finalize_steps_set_lane = _cmd_mod.cmd_finalize_steps_set_lane
_reject_lane_value = _cmd_mod._reject_lane_value
_RESOLVED_ASK_LANE_VALUES = _cmd_mod._RESOLVED_ASK_LANE_VALUES
_READER_LANE_VALUES = _cmd_mod._READER_LANE_VALUES

_quality_mod = load_script_module(
    'plan-marshall', 'manage-config', '_cmd_quality_phases.py', module_name='_cmd_quality_phases'
)
_resolve_finalize_step_lane = _quality_mod._resolve_finalize_step_lane

# ``register=False``: this module needs only the returned object — it reads
# ``LANE_OVERRIDES`` and ``_IMMUNE_TO_OFF_CLASSES``, two module-level collections,
# and nothing here depends on ``_manifest_lanes`` being reachable through
# ``sys.modules`` (no dataclass ``__module__`` lookup, no pickle round-trip).
# Registering it would publish a SECOND copy under a name a sibling test module
# (``test_lane_class_off_immunity.py``) imports plainly, which is the
# order-dependent collision ``test_no_new_shared_registration_collision`` guards.
_lanes_mod = load_script_module(
    'plan-marshall',
    'manage-execution-manifest',
    '_manifest_lanes.py',
    register=False,
)

#: A finalize step every discovery run knows about, used as the set-lane target.
_LANE_STEP_ID = 'plan-marshall:automatic-review'

#: The substring that IS the fix: the verb an operator should reach for instead.
_ROUTE_MARKER = 'step set'

#: A finalize step on the mandatory floor — its class is in
#: ``_IMMUNE_TO_OFF_CLASSES``, so the composer ignores a weakening ``off``.
_IMMUNE_STEP_ID = 'default:push'

#: A finalize step OFF the floor — its class is not immune, so an ``off`` on it
#: is a real opt-out the composer honours. The matched positive control.
_NON_IMMUNE_STEP_ID = 'default:adr-propose'

#: A finalize step whose class the resolver cannot reach (a ``bundle:skill`` id
#: with no project-local source). The fail-toward-permitting case.
_UNRESOLVABLE_CLASS_STEP_ID = _LANE_STEP_ID


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

    result = cmd_finalize_steps_set_lane(Namespace(step_id=_LANE_STEP_ID, lane='minimal', plan_id=None))

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
        SCRIPT_PATH,
        'finalize-steps',
        'set-lane',
        '--step-id',
        _LANE_STEP_ID,
        '--lane',
        'minimal',
    )

    combined = f'{result.stdout}\n{result.stderr}'
    assert 'invalid choice' not in combined, (
        f'argparse rejected --lane before the handler ran, so the routed message is unreachable: {combined}'
    )
    # The refusal rides `status: error`, not the exit code: manage-config's `main`
    # returns 0 after printing any result, so every validation error in this script
    # signals on the TOON. Moving this check off argparse moved it onto the same
    # channel its siblings (unknown step id, uninitialized marshal) already used.
    assert 'status: error' in combined, f'a refused write must not report success: {combined}'
    assert _ROUTE_MARKER in combined, f'the CLI refusal does not name the `{_ROUTE_MARKER}` route: {combined}'


# ---------------------------------------------------------------------------
# The canonical-invocations block, bound in place of the retired analyzer check
# ---------------------------------------------------------------------------

#: The skill doc whose ``## Canonical invocations`` block documents the verb.
_MANAGE_CONFIG_SKILL = get_skill_dir('plan-marshall', 'manage-config') / 'SKILL.md'

#: The documented ``--lane {a,b,c}`` enum inside the canonical ``set-lane`` block.
_DOCUMENTED_LANE_ENUM = re.compile(r'--lane\s*\{([^}]+)\}')


def _documented_lane_values() -> list[str]:
    """The values the canonical `set-lane` invocation block documents for `--lane`.

    Anchored to the ``### finalize-steps set-lane`` section so a ``--lane`` enum
    documented for some other verb cannot be read in its place.
    """
    text = _MANAGE_CONFIG_SKILL.read_text(encoding='utf-8')
    section = re.search(r'^### finalize-steps set-lane$(.*?)(?=^### |\Z)', text, re.MULTILINE | re.DOTALL)
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
        "the anchored extraction picked up a neighbouring verb's enum"
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


# ---------------------------------------------------------------------------
# The SECOND rejection axis: an `off` the target element's class makes inert
# ---------------------------------------------------------------------------
#
# The axis above is about the VALUE — which values this verb writes at all. This
# one is about the TARGET, and the two are independent: `off` is a value this
# verb writes, yet it is refused on a step whose class the composer shields from
# a weakening `off`, because storing it would record a setting the composer is
# guaranteed to ignore. The refusal is checked on BOTH channels, because a
# refusal enforced on one destination only would leave the other able to persist
# exactly the state the refusal exists to prevent.


def _status_path(plan_context, plan_id: str) -> Path:
    return Path(plan_context.plan_dir_for(plan_id)) / 'status.json'


def _seed_status(plan_context, plan_id: str) -> Path:
    """Write a minimal ``status.json`` for ``plan_id`` and return its path."""
    path = _status_path(plan_context, plan_id)
    path.write_text(json.dumps({'metadata': {}}), encoding='utf-8')
    return path


def _overrides(status_path: Path) -> dict:
    status = json.loads(status_path.read_text(encoding='utf-8'))
    overrides: dict = status.get('metadata', {}).get('finalize_step_overrides', {})
    return overrides


def test_the_three_fixture_steps_occupy_the_three_classes_this_axis_partitions():
    """Anti-vacuity: the fixtures' premises are DERIVED from the live resolver.

    Every assertion below turns on which side of the immune set a step's class
    falls on. Asserting that from a remembered class would make the whole section
    pass or fail for a reason unrelated to the refusal, so each premise is
    re-resolved here through the same resolver the writers call.
    """
    immune = _resolve_finalize_step_lane(_IMMUNE_STEP_ID)
    assert immune and immune.get('class') in _lanes_mod._IMMUNE_TO_OFF_CLASSES, (
        f'{_IMMUNE_STEP_ID} no longer resolves to an immune class ({immune}); pick another '
        f'floor step, or the refusal assertions below prove nothing.'
    )

    non_immune = _resolve_finalize_step_lane(_NON_IMMUNE_STEP_ID)
    assert non_immune and non_immune.get('class') not in _lanes_mod._IMMUNE_TO_OFF_CLASSES, (
        f'{_NON_IMMUNE_STEP_ID} no longer resolves to a NON-immune class ({non_immune}); the '
        f'positive control below would then assert nothing about the refusal being narrow.'
    )

    assert _resolve_finalize_step_lane(_UNRESOLVABLE_CLASS_STEP_ID) is None, (
        f'{_UNRESOLVABLE_CLASS_STEP_ID} now resolves a lane class, so the '
        f'fail-toward-permitting case below is no longer exercised by it.'
    )


def test_project_channel_refuses_an_off_on_an_immune_element(plan_context):
    """The project-wide write is refused, and the message names the class."""
    create_marshal_json(plan_context.fixture_dir)
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    before = marshal_path.read_bytes()

    result = cmd_finalize_steps_set_lane(Namespace(step_id=_IMMUNE_STEP_ID, lane='off', plan_id=None))

    assert result['status'] == 'error'
    assert _IMMUNE_STEP_ID in result['error']
    assert 'lane.class' in result['error']
    # The refusal names the class it found, so the operator can see WHY.
    assert _resolve_finalize_step_lane(_IMMUNE_STEP_ID)['class'] in result['error']
    # Refused means not written: marshal.json is untouched.
    assert marshal_path.read_bytes() == before


def test_plan_local_channel_refuses_the_same_off(plan_context):
    """The plan-scoped write is refused identically — one predicate, both channels."""
    create_marshal_json(plan_context.fixture_dir)
    status_path = _seed_status(plan_context, 'immune-plan-local')

    result = cmd_finalize_steps_set_lane(Namespace(step_id=_IMMUNE_STEP_ID, lane='off', plan_id='immune-plan-local'))

    assert result['status'] == 'error'
    assert 'lane.class' in result['error']
    assert _overrides(status_path) == {}


def test_a_non_immune_element_still_accepts_off_on_both_channels(plan_context):
    """MATCHED POSITIVE CONTROL: the refusal is narrow, not a blanket ban on ``off``.

    Without this, a writer that refused EVERY ``off`` would satisfy both refusal
    assertions above while destroying the real opt-out the lane contract grants
    an ``adversarial`` / ``prunable`` element.
    """
    create_marshal_json(plan_context.fixture_dir)
    status_path = _seed_status(plan_context, 'non-immune-plan-local')

    project = cmd_finalize_steps_set_lane(Namespace(step_id=_NON_IMMUNE_STEP_ID, lane='off', plan_id=None))
    assert project['status'] == 'success'
    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text(encoding='utf-8'))
    assert config['plan']['phase-6-finalize']['steps'][_NON_IMMUNE_STEP_ID]['lane'] == 'off'

    plan_local = cmd_finalize_steps_set_lane(
        Namespace(step_id=_NON_IMMUNE_STEP_ID, lane='off', plan_id='non-immune-plan-local')
    )
    assert plan_local['status'] == 'success'
    assert _overrides(status_path) == {_NON_IMMUNE_STEP_ID: {'lane': 'off'}}


def test_an_unresolvable_class_permits_the_off_rather_than_refusing_it(plan_context):
    """Fail toward PERMITTING: an unreadable class is not evidence of immunity.

    The composer keeps an element whose class it cannot read rather than pruning
    it; the writer takes the same direction rather than refusing on a class it
    never established.
    """
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_finalize_steps_set_lane(Namespace(step_id=_UNRESOLVABLE_CLASS_STEP_ID, lane='off', plan_id=None))

    assert result['status'] == 'success'
    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text(encoding='utf-8'))
    assert config['plan']['phase-6-finalize']['steps'][_UNRESOLVABLE_CLASS_STEP_ID]['lane'] == 'off'

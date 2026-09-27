# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _LANE_OVERRIDE_DECISIONS,
    _LANE_REPORT_MARSHAL_STEPS,
    _LANE_STEPS,
    _lane_keep_decision,
    _lane_report_ns,
    _lane_report_row,
    _patch_element_lane,
    _seed_lane_report_marshal,
    _seed_plan_local_lane,
    cmd_lanes_preview,
    pytest,
)


@pytest.mark.parametrize(
    'lane,posture,expected_keep',
    [
        ({'class': 'core', 'tier': 'minimal'}, 'minimal', True),  # floor runs everywhere
        ({'class': 'prunable', 'tier': 'standard'}, 'minimal', False),  # standard tier above minimal
        ({'class': 'prunable', 'tier': 'standard'}, 'standard', True),  # standard tier at standard
        ({'class': 'adversarial', 'tier': 'full'}, 'standard', False),  # full tier above standard
        ({'class': 'adversarial', 'tier': 'full'}, 'full', True),  # full tier at full
    ],
)
def test_lane_keep_decision_cutoff(lane, posture, expected_keep):
    """An element runs iff effective_tier ⊑ posture on the lattice."""
    keep, warning = _lane_keep_decision(lane, None, posture)
    assert keep is expected_keep
    assert warning is None


assert len(_LANE_OVERRIDE_DECISIONS) > 0, 'lane-override decisions must not derive empty'


@pytest.mark.parametrize(
    ('lane', 'override', 'posture', 'expected_keep', 'warning_fragments'),
    _LANE_OVERRIDE_DECISIONS,
    ids=[
        'off-override-of-derived-state-floor-is-immune-and-warns',
        'off-override-of-core-floor-is-immune-and-warns',
        'off-override-drops-non-floor-adversarial-silently',
        'off-override-drops-non-floor-prunable-silently',
        'minimal-override-force-keeps-a-full-tier-element',
    ],
)
def test_lane_keep_decision_honours_override(lane, override, posture, expected_keep, warning_fragments):
    """An operator lane override is honoured unless the element sits on the floor.

    A floor element (derived-state or core at tier minimal) is immune to `off`:
    it stays, and the neutralized override is reported rather than swallowed. Any
    other element opts out cleanly, with nothing to report.
    """
    keep, warning = _lane_keep_decision(lane, override, posture)

    assert keep is expected_keep
    if warning_fragments:
        assert warning is not None
        for fragment in warning_fragments:
            assert fragment in warning
    else:
        assert warning is None


def test_lane_report_names_an_inert_off_with_its_reason(plan_context, monkeypatch):
    """A stored ``off`` a floor class neutralizes is reported as stored AND inert.

    This is the pair the report exists for: ``declared`` still says ``off``
    (the value was accepted and persisted), ``effective`` says the element runs
    anyway at its class-default tier, ``binds`` is false, and ``reason`` carries
    the verbatim neutralization text. Reporting only ``declared`` would tell the
    operator the override is set; only ``effective`` would hide that they set one.
    """
    _patch_element_lane(monkeypatch)
    _seed_lane_report_marshal(plan_context)

    result = cmd_lanes_preview(_lane_report_ns())

    assert result is not None and result['status'] == 'success'
    row = _lane_report_row(result, 'project:finalize-step-deploy-target')
    assert row['declared'] == 'off'
    assert row['effective'] == 'minimal'
    assert row['binds'] is False
    assert 'immune' in row['reason']
    assert 'derived-state' in row['reason']


def test_lane_report_reports_binds_true_for_a_live_off(plan_context, monkeypatch):
    """A stored ``off`` on a non-immune element BINDS — and carries no reason.

    The matched positive control for the inert case above: same declared value,
    same fixture, same preview call, and the only difference is the element's lane
    class. An empty ``reason`` here is what makes the neutralization text in the
    sibling case evidence of neutralization rather than boilerplate every row
    carries.
    """
    _patch_element_lane(monkeypatch)
    _seed_lane_report_marshal(plan_context)

    result = cmd_lanes_preview(_lane_report_ns())

    assert result is not None
    row = _lane_report_row(result, 'sonar-roundtrip')
    assert row['declared'] == 'off'
    assert row['effective'] == 'off'
    assert row['binds'] is True
    assert row['reason'] == ''


def test_lane_report_distinguishes_no_declaration_from_a_neutralized_one(plan_context, monkeypatch):
    """A step nobody spoke for reports ``-``, not a fabricated value.

    Both this row and the inert-``off`` row report ``binds: false``, so ``binds``
    alone cannot tell "the operator declared nothing" from "the operator declared
    something that was overruled". ``declared`` and ``reason`` are what separate
    them, and an undeclared row must carry neither a value nor a reason.
    """
    _patch_element_lane(monkeypatch)
    _seed_lane_report_marshal(plan_context)

    result = cmd_lanes_preview(_lane_report_ns())

    assert result is not None
    row = _lane_report_row(result, 'push')
    assert row['declared'] == '-'
    assert row['effective'] == 'minimal'
    assert row['binds'] is False
    assert row['reason'] == ''


def test_lane_report_sees_a_plan_local_declaration(plan_context, monkeypatch):
    """A plan-local declaration is visible to the preview — the merged-map regression.

    ``cmd_lanes_preview`` sources its declaration map from the SAME merged
    plan-local-over-marshal read every compose-side per-element reader consults,
    so an answer stored for this plan alone is reported here too. The
    project-wide-only read of the same fixture is asserted alongside it: without
    that contrast a passing plan-scoped assertion could equally be satisfied by a
    marshal-side declaration, which is precisely the reading the regression had.
    """
    plan_id = 'lane-report-plan-local'
    _patch_element_lane(monkeypatch)
    _seed_lane_report_marshal(plan_context)
    _seed_plan_local_lane(plan_context, plan_id, {'finalize-step-security-audit': {'lane': 'off'}})

    with_plan = cmd_lanes_preview(_lane_report_ns(plan_id))
    project_only = cmd_lanes_preview(_lane_report_ns())

    assert with_plan is not None and project_only is not None
    plan_scoped_row = _lane_report_row(with_plan, 'finalize-step-security-audit')
    assert plan_scoped_row['declared'] == 'off'
    # adversarial is a non-floor class, so the plan-local off is a real opt-out.
    assert plan_scoped_row['binds'] is True
    # The project-wide channel carries no declaration for this step at all.
    assert _lane_report_row(project_only, 'finalize-step-security-audit')['declared'] == '-'


def test_lane_report_channels_covered_states_which_sweep_ran(plan_context, monkeypatch):
    """``channels_covered`` names the sweep, so one channel is never read as both.

    ``--plan-id`` is optional on this verb, and its presence widens the
    declaration source rather than merely labelling the output. A report over the
    project-wide channel alone is a narrower answer than a report over both, and
    the field is what keeps the two distinguishable at the consumer.
    """
    _patch_element_lane(monkeypatch)
    _seed_lane_report_marshal(plan_context)

    project_only = cmd_lanes_preview(_lane_report_ns())
    both = cmd_lanes_preview(_lane_report_ns('lane-report-channels'))

    assert project_only is not None and both is not None
    assert project_only['channels_covered'] == ['project']
    assert both['channels_covered'] == ['project', 'plan_local']
    # ``plan_id`` rides the payload only when one was supplied — a project-wide
    # report never carries a plan id it was not given.
    assert 'plan_id' not in project_only
    assert both['plan_id'] == 'lane-report-channels'


def test_lane_report_covers_every_lane_participating_candidate_and_no_other(plan_context, monkeypatch):
    """The report's population is the lane-participating candidates, and it says so.

    A step the resolver reaches no lane class for has no effective lane to compare
    a declaration against, so it is omitted rather than reported with an empty
    verdict — even when it carries a stored ``lane``, as the extra candidate here
    deliberately does. ``lane_report_count`` publishes the population the report
    was computed over, so a short report is countable rather than silent.
    """
    _patch_element_lane(monkeypatch)
    steps = dict(_LANE_REPORT_MARSHAL_STEPS)
    steps['default:no-lane-block-step'] = {'lane': 'off'}
    _seed_lane_report_marshal(plan_context, steps)

    result = cmd_lanes_preview(_lane_report_ns())

    assert result is not None
    reported = {row['step'] for row in result['lane_report']}
    assert reported == set(_LANE_STEPS)
    assert 'no-lane-block-step' not in reported
    assert result['lane_report_count'] == len(result['lane_report'])

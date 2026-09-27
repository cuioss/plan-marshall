#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D0/D1/D2 — prose-only corroboration, signal-resolution confidence, and the
orchestrator-spec ``plan_source`` bridge for the planning-lane router.

Context (plan 240, ``truthful-signals``): the router bought ``planning_lane=deep``
on a single fired signal — ``S7:risk_prose`` — against a resolved ``single_module``
scope, over a signal vector in which three metadata inputs and the override were
null. Three defects, three deliverables exercised here:

- **D2** — a prose-only warning must not carry the lane ALONE when a MEASUREMENT
  contradicts it. The corroboration is scoped to the non-committal middle band
  (``single_module``) reached by the ``path_count_middle_band`` rule, so it fixes the
  recorded over-route WITHOUT reopening the prior false-negative fix, which lets S7
  outrank a POSITIVELY-earned narrow band (``surgical``). A ``single_module`` band
  that counted nothing (``pathless_non_empty_body``), an unrecognised band, and a
  caller that supplies no band rule at all are all "no measurement" — S7 keeps the
  lane. ``test_prior_fix_surgical_plus_s7_alone_still_deep`` is the don't-fight
  regression; ``test_planning_lane_risk_prose.py`` keeps the original surgical
  assertions unchanged.
- **D1** — the route reports the resolved-vs-null split of the READ signals
  (``planning_lane_override`` is excluded — its absence is the normal state), and
  flags ``low_confidence`` when two or more of the four discriminating reads are
  null, so a decision resting on two unresolved inputs cannot read as a confident one.
  That split's POPULATION is derived from the reported ``signals`` mapping rather
  than mirrored into a second list, which
  ``TestTheConfidencePopulationIsDerivedNotMirrored`` pins by deriving every
  expectation from the mapping the call returns.
- **D0/S1** — ``plan_source`` is null for EVERY orchestrator-launched plan because
  phase-1-init records the spec pointer as ``request.md`` ``source_id`` but never
  seeds ``status.metadata.plan_source`` on the file-pointer branch. The router
  bridges the two at read time.

D3 coverage (each of a–d):

- ``test_d3a_recorded_vector_does_not_route_deep`` — (a) replay the exact recorded
  vector against a MEASURED middle band (``path_count_middle_band``); it must NOT
  route deep.
- ``test_d3b_orchestrator_spec_resolves_plan_source_nonnull`` — (b) an
  orchestrator-spec-sourced request resolves ``plan_source`` non-null.
- ``test_d3c_several_nulls_reported_low_confidence`` — (c) a several-nulls vector is
  reported low-confidence.
- ``test_d3d_control_deep_warranting_vector_still_routes_deep`` — (d) the CONTROL: a
  genuinely deep-warranting vector still routes deep (a router hardwired to
  ``light`` would pass every OTHER test here).

The measured-evidence bound adds four more:

- ``test_recorded_case_end_to_end_routes_light`` — a body whose 4 distinct paths
  MEASURE the middle band still routes light, end to end.
- ``test_pathless_single_module_band_does_not_suppress_s7`` — a ``single_module``
  band that counted no path suppresses nothing; the warning routes deep.
- ``test_unrecognised_noncommittal_band_does_not_suppress_s7`` — an unrecognised,
  empty or whitespace-padded band is not in the allowlist and suppresses nothing.
- ``test_post_bridge_motivating_vector_is_low_confidence`` — the motivating vector
  is still low-confidence once the bridge resolves ``plan_source``.
"""

from __future__ import annotations

import pytest
from _planning_lane_corroboration_fixtures import (
    _RECORDED_VECTOR,
    _ns_route,
    _write_marshal,
    _write_orchestrator_request,
    _write_plaintext_request,
    _write_references,
    _write_status,
    cmd_planning_lane_route,
    evaluate_signals_pure,
)

# The ONE ``band_rule`` that counts as a measurement of the non-committal middle
# band: 4-7 distinct paths counted, landing between the surgical maximum and the
# multi-module floor. Every other band rule leaves S7 uncontradicted.
_MEASURED_MIDDLE_BAND = 'path_count_middle_band'

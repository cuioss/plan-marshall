#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import Path, json

# =============================================================================
# marshal.json source-of-truth tests
#
# The composer prefers ``plan.phase-{5,6}-{execute,finalize}.steps`` from
# marshal.json over the agent-supplied ``--phase-{5,6}-steps`` CSV. This
# defends against agent-built CSVs that historically stripped ``project:`` and
# ``bundle:skill`` prefixes (producing manifests with bare names the
# phase-6-finalize dispatcher then mis-routed as built-in steps).
# =============================================================================


def _write_full_marshal(
    fixture_dir: Path,
    *,
    phase_6_steps: list[str],
    phase_5_steps: list[str] | None = None,
) -> None:
    """Write a marshal.json with the given phase-5/6 step lists.

    The phase-5 list is optional — when omitted, only ``phase-6-finalize.steps``
    is populated. The id lists are converted to the id-keyed map schema
    (``{step_id: {}, ...}`` — key insertion order is the execution order, empty
    param objects), matching the live on-disk shape ``_read_marshal_phase_steps``
    reads. Prefixes are preserved. No CI provider is declared for these fixtures.
    """
    marshal_path = fixture_dir / 'marshal.json'
    plan_block: dict = {'phase-6-finalize': {'steps': {step_id: {} for step_id in phase_6_steps}}}
    if phase_5_steps is not None:
        # phase-5-execute stores its verification step map under the
        # ``verification_steps`` key (the keyed-map schema);
        # ``_read_marshal_phase_steps`` reads ``verification_steps`` for the
        # phase-5 block. Writing the keyed map here matches the live composer
        # contract.
        plan_block['phase-5-execute'] = {'verification_steps': {step_id: {} for step_id in phase_5_steps}}
    data = {'plan': plan_block}
    marshal_path.write_text(json.dumps(data), encoding='utf-8')

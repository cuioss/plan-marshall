#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import _SCOPE_GATE_PHASE_6, Path, json


def _write_drop_review_marshal(fixture_dir: Path, *, override: bool) -> None:
    """Write a marshal.json carrying a leftover drop_review_on_scope_gate knob.

    The knob is retired — no reader consumes it. It is written here nested under
    ``phase-6-finalize.steps['default:functional-review']``, the review step a
    migrated configuration names, so a test can prove the leftover knob is INERT
    wherever an operator left it.

    The composer treats a marshal.json ``steps`` map as the AUTHORITATIVE phase-6
    candidate list (preferred over the ``--phase-6-steps`` CSV), so the seeded
    ``steps`` map carries the FULL ``_SCOPE_GATE_PHASE_6`` candidate set — every
    candidate becomes a key (ownerless steps map to ``None``), with the leftover
    knob nested onto the functional-review step. This keeps the composed
    candidate list identical to the ``_compose_ns`` CSV.
    """
    steps: dict[str, dict | None] = dict.fromkeys(_SCOPE_GATE_PHASE_6)
    steps['default:functional-review'] = {
        'drop_review_on_scope_gate': override,
    }
    marshal_path = fixture_dir / 'marshal.json'
    data = {'plan': {'phase-6-finalize': {'steps': steps}}}
    marshal_path.write_text(json.dumps(data), encoding='utf-8')

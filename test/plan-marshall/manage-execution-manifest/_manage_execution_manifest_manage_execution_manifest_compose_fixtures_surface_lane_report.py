#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import Path, json

# =============================================================================
# D6 — compose-time drop-when-no-provider for an unresolved lane:ask infra element
#
# Both adversarial infra elements (automatic-review, sonar-roundtrip) seed
# ``lane: ask``. A steward-persisted answer overwrites the override to
# off/standard/full; an effective tier still equal to ``ask`` at compose means the
# operator never answered (UNRESOLVED). When unresolved AND the corresponding
# provider is absent (no CI provider for automatic-review; no Sonar provider for
# sonar-roundtrip), the ``_apply_unresolved_ask_provider_drop`` pre-filter drops
# the element at the candidate-narrowing stage. A resolved (off/standard/full) ask
# and a provider-configured ask both survive. These compose round-trip tests
# exercise the pre-filter end-to-end through cmd_compose; the pure-function truth
# table is pinned directly in test_decision_rules.py.
# =============================================================================


def _seed_marshal_with_finalize_steps(
    steps_map: dict[str, dict],
    *,
    ci_provider: str | None = None,
    sonar_provider: bool = False,
) -> Path:
    """Seed marshal.json with a ``phase-6-finalize.steps`` keyed map + providers.

    ``steps_map`` becomes the candidate source (its keys ARE the phase-6
    candidate list) and the per-element ``lane`` override map the D6 pre-filter
    reads. ``ci_provider`` (``'github'``/``'gitlab'``/``None``) and
    ``sonar_provider`` control the ``providers[]`` list so the two provider
    readers resolve deterministically.
    """
    from file_ops import get_marshal_path

    providers: list[dict] = []
    if ci_provider:
        providers.append({'skill_name': f'plan-marshall:workflow-integration-{ci_provider}', 'category': 'ci'})
    if sonar_provider:
        providers.append({'skill_name': 'plan-marshall:workflow-integration-sonar', 'category': 'sonar'})
    marshal: dict = {'plan': {'phase-6-finalize': {'steps': steps_map}}}
    if providers:
        marshal['providers'] = providers
    marshal_path = get_marshal_path()
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(marshal, indent=2))
    return marshal_path

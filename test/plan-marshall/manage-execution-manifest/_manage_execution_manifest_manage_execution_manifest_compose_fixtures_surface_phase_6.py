#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import Path, json

# =============================================================================
# pre-push-quality-gate pre-filter tests
# =============================================================================


def _write_marshal(
    fixture_dir: Path, *, activation_globs: list[str] | None = None, include_pre_push_key: bool = True
) -> None:
    """Write a marshal.json whose pre-push activation derives from build.map.

    Pre-push-quality-gate activation now reads the per-entry globs from
    ``build.map`` (D7/D8) — there is no separate
    ``pre_push_quality_gate.activation_globs`` source. ``activation_globs`` here
    names the globs the seeded build_map should carry:

    - ``include_pre_push_key=False`` → omit the ``build.map`` block
      entirely (simulates the "absent" branch → gate dropped).
    - ``activation_globs is None`` (with the block present) → seed a build_map
      whose single entry carries no usable glob (also "absent" → gate dropped).
    - ``activation_globs == []`` → seed an empty build_map (no globs → dropped).
    - ``activation_globs == [g, ...]`` → seed one build_map entry per glob so
      ``_read_build_map_globs`` collects exactly those globs.
    """
    marshal_path = fixture_dir / 'marshal.json'
    data: dict = {'plan': {'phase-6-finalize': {}}, 'build': {}}
    if include_pre_push_key:
        globs = activation_globs if activation_globs is not None else []
        entries = [{'glob': glob, 'role': 'production', 'build_class': 'compile'} for glob in globs]
        data['build']['map'] = {'python': entries}
    marshal_path.write_text(json.dumps(data), encoding='utf-8')


def _write_marshal_with_ci(fixture_dir: Path, *, provider: str) -> None:
    """Write a marshal.json whose ``providers[]`` resolves to the given CI provider.

    ``_read_ci_provider`` maps the ``providers[]`` entry whose ``category == 'ci'``
    to a short identifier (``plan-marshall:workflow-integration-github`` ->
    ``github``, ``plan-marshall:workflow-integration-gitlab`` -> ``gitlab``). Tests
    for the github/gitlab branch must materialize this entry; the no-CI baseline
    simply omits ``providers[]``.
    """
    skill_name = f'plan-marshall:workflow-integration-{provider}'
    marshal_path = fixture_dir / 'marshal.json'
    data: dict = {
        'providers': [{'skill_name': skill_name, 'category': 'ci'}],
        'plan': {'phase-6-finalize': {}},
    }
    marshal_path.write_text(json.dumps(data), encoding='utf-8')

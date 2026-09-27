# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _RECIPE_PROVENANCE_CASES,
    _compose_ns,
    _write_status_metadata,
    cmd_compose,
    pytest,
    re,
)

assert len(_RECIPE_PROVENANCE_CASES) > 0, 'recipe-provenance cases must not derive empty'


@pytest.mark.parametrize(
    ('metadata', 'overrides', 'expected_rule'),
    _RECIPE_PROVENANCE_CASES,
    ids=[
        'plan_source-holding-a-lesson-id-fires-the-recipe-row',
        'metadata-recipe_key-fires-the-recipe-row',
        'plan_source-set-to-the-literal-recipe-fires-the-recipe-row',
        'metadata-carrying-no-provenance-key-falls-to-default',
        'no-status-json-at-all-falls-to-default',
        'an-explicit-recipe-key-fires-the-recipe-row-without-status-json',
    ],
)
def test_compose_reads_recipe_provenance(plan_context, request, metadata, overrides, expected_rule):
    """The composer reads recipe provenance from status metadata, not only from --recipe-key.

    A lesson-derived plan carries its provenance in `status.metadata` even when the
    planning agent omitted `--recipe-key`. Reading only the flag drops exactly those
    plans onto the default row, which is the drift this pins shut.
    """
    slug = re.sub(r'[^a-z0-9]+', '-', request.node.callspec.id.lower()).strip('-')
    plan_id = f'provenance-{slug}'[:60].rstrip('-')
    if metadata is not None:
        _write_status_metadata(plan_context, plan_id, metadata)

    args = {
        'change_type': 'feature',
        'scope_estimate': 'multi_module',
        'recipe_key': None,
        'affected_files_count': 4,
        **overrides,
    }
    result = cmd_compose(_compose_ns(plan_id=plan_id, **args))

    assert result is not None
    assert result['rule_fired'] == expected_rule

# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_step_params_fixtures import _denormalize_step_params_for_write

# =============================================================================
# Empty-{} suppression at the manifest write boundary + read-path coercion
# =============================================================================
#
# `_denormalize_step_params_for_write` collapses an ownerless step_params value
# (empty {} or None) to None right before serializing, so the manifest TOON never
# carries a noisy empty {} block. `_normalize_step_params_block` (the read
# boundary) coerces every per-step value that is not a non-empty dict — None, {},
# and the TOON-round-tripped '' — back to {}, so an ownerless step reads back as
# {} no matter which on-disk representation it carries.


def test_denormalize_collapses_ownerless_step_params_to_none():
    """The write boundary collapses ownerless step_params ({} / None) to None; param-owning steps keep their dict."""
    manifest = {
        'phase_5': {
            'step_params': {
                'quality-gate': {},
                'module-tests': None,
            }
        },
        'phase_6': {
            'step_params': {
                'push': {},
                'branch-cleanup': {'pr_merge_strategy': 'squash'},
            }
        },
    }

    result = _denormalize_step_params_for_write(manifest)

    # ownerless steps collapse to None (serialized as null) — no empty {} block
    assert result['phase_5']['step_params'] == {'quality-gate': None, 'module-tests': None}
    assert result['phase_6']['step_params']['push'] is None
    # param-owning step keeps its nested object
    assert result['phase_6']['step_params']['branch-cleanup'] == {'pr_merge_strategy': 'squash'}
    # the input manifest is never mutated
    assert manifest['phase_5']['step_params']['quality-gate'] == {}

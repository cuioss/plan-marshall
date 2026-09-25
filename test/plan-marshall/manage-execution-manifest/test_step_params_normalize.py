# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_step_params_fixtures import _normalize_step_params_block


def test_normalize_step_params_block_coerces_all_empty_shapes_to_empty_dict():
    """The read boundary coerces None / {} / '' per-step values back to {}; param-owning steps keep their dict."""
    manifest = {
        'phase_5': {
            'step_params': {
                'quality-gate': None,
                'module-tests': {},
                'coverage': '',
            }
        },
        'phase_6': {
            'step_params': {
                'push': None,
                'branch-cleanup': {'pr_merge_strategy': 'squash'},
            }
        },
    }

    _normalize_step_params_block(manifest)

    # every absent-or-empty representation reads back as the empty dict
    assert manifest['phase_5']['step_params'] == {
        'quality-gate': {},
        'module-tests': {},
        'coverage': {},
    }
    assert manifest['phase_6']['step_params']['push'] == {}
    # the param-owning step keeps its nested object
    assert manifest['phase_6']['step_params']['branch-cleanup'] == {'pr_merge_strategy': 'squash'}

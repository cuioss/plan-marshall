# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_config_build_map_seed_fixtures import Namespace, _cmd_init_mod, _config_core_mod, json

# =============================================================================
# normalize-keys — rewrite marshal.json to the canonical top-level key order
# =============================================================================
#
# `manage-config normalize-keys` (normalize_keys) loads the persisted config and
# re-saves it via save_config, whose key_order is the single source of truth for
# the canonical order (extension_defaults, plan, build, project, ...). A config
# written build-before-plan is rewritten so `plan` precedes `build`; the verb is
# idempotent — an already-canonical file is rewritten to the same bytes.


def test_normalize_keys_rewrites_build_before_plan_to_canonical_order(plan_context):
    """normalize-keys rewrites a build-before-plan config to the canonical order.

    Write a marshal.json whose top-level keys are deliberately out of canonical
    order (build before plan), then run normalize_keys. The re-saved file must
    list `plan` before `build` (the save_config key_order), proving the verb
    canonicalizes the persisted top-level order.
    """
    # Arrange — init, then overwrite marshal.json with build BEFORE plan.
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    out_of_order = {
        'build': {'map': {}},
        'plan': {'phase-2-refine': {'compatibility': 'breaking'}},
        'system': {'version': 1},
    }
    marshal_path.write_text(json.dumps(out_of_order, indent=2), encoding='utf-8')

    # Act
    result = _config_core_mod.normalize_keys()

    # Assert — handler reports normalized, and `plan` now precedes `build`.
    assert result['action'] == 'normalized'
    persisted_keys = list(json.loads(marshal_path.read_text(encoding='utf-8')).keys())
    assert persisted_keys.index('plan') < persisted_keys.index('build'), (
        f'normalize-keys did not canonicalize the top-level order; keys={persisted_keys}'
    )


def test_normalize_keys_is_idempotent(plan_context):
    """normalize-keys is idempotent — a second run rewrites the same bytes.

    Run normalize_keys once to canonicalize, snapshot the bytes, then run it
    again: an already-canonical file must be rewritten to byte-identical content.
    """
    # Arrange — init, write an out-of-order config, normalize once.
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    out_of_order = {
        'build': {'map': {}},
        'plan': {'phase-2-refine': {'compatibility': 'breaking'}},
        'system': {'version': 1},
    }
    marshal_path.write_text(json.dumps(out_of_order, indent=2), encoding='utf-8')
    _config_core_mod.normalize_keys()
    after_first = marshal_path.read_bytes()

    # Act — second normalization over the already-canonical file.
    second = _config_core_mod.normalize_keys()

    # Assert — idempotent: byte-identical to the first normalization.
    assert second['action'] == 'normalized'
    after_second = marshal_path.read_bytes()
    assert after_second == after_first, 'normalize-keys is not idempotent'

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tree-first PYTHONPATH ordering for the generated executor.

A single alphabetical ``sorted()`` over the executor's script dirs puts a
deployed copy (``~/.config/...``, the Claude plugin cache) ahead of the
marketplace tree (``.../git/...``), so the deployed copy of a shared module
(``_manifest_validation``) shadows the tree copy and its
``Path(__file__)``-anchored ``resolve_bundles_root`` — which only knows nested
layouts — raises ``RuntimeError`` at import time, killing every
``manage-config`` invocation. These tests pin the partition: marketplace/tree
dirs first, cache/deployed dirs second, alphabetical within each partition.
"""

import types
from pathlib import Path

from conftest import PROJECT_ROOT, load_script_module

_gen = load_script_module('plan-marshall', 'tools-script-executor', 'generate_executor.py', 'gen_executor_tree_first')

_TEMPLATE_PATH = (
    PROJECT_ROOT / 'marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template'
)

_TREE_DIR = str(PROJECT_ROOT / 'marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts')
_CACHE_DIR = '/home/oliver/.config/opencode/skills/plan-marshall-manage-execution-manifest/scripts'


def _load_template_module_with_mixed_dirs() -> types.ModuleType:
    """Render the real template with a mixed tree/cache dir family and exec it.

    Mirrors ``_load_template_module`` in ``test_generate_executor_behavior.py``,
    but carries one tree and one cache mapping (plus matching baked extra dirs)
    so the runtime ``_SCRIPT_DIRS`` partition has both families to order. The
    template's shared-module imports resolve through the root conftest's
    ``sys.path``; ``main()`` stays guarded.
    """
    source = _TEMPLATE_PATH.read_text(encoding='utf-8')
    logging_dir = str(PROJECT_ROOT / 'marketplace/bundles/plan-marshall/skills/manage-logging/scripts')
    mappings = (
        f"    'plan-marshall:manage-execution-manifest:tree-copy': '{_TREE_DIR}/_manifest_validation.py',\n"
        f"    'plan-marshall:manage-execution-manifest:cache-copy': '{_CACHE_DIR}/_manifest_validation.py',\n"
    )
    source = source.replace('{{SCRIPT_MAPPINGS}}', mappings)
    source = source.replace('{{SCRIPT_SURFACES}}', '').replace('{{SUBCOMMAND_MAPPINGS}}', '')
    source = source.replace('{{LOGGING_DIR}}', logging_dir)
    source = source.replace('{{SHARED_MODULE_DIRS}}', '# (none)')
    source = source.replace('{{CACHE_RECOVERY_ROOTS}}', '# (none)')
    source = source.replace('{{EXTRA_SCRIPT_DIRS}}', f"'{_CACHE_DIR}', '{_TREE_DIR}'")
    source = source.replace('{{PLAN_DIR_NAME}}', '.plan')
    source = source.replace('{{EXECUTOR_TARGET}}', 'claude')
    source = source.replace('{{GENERATED_VERSION}}', '')
    source = source.replace('{{MAPPINGS_FINGERPRINT}}', '')
    source = source.replace(
        '{{TARGET_AWARE_RESOLVER}}',
        'def _resolve_notation_by_target(notation):\n    return None\n',
    )
    module = types.ModuleType('executor_template_tree_first')
    module.__dict__['__file__'] = str(_TEMPLATE_PATH)
    exec(compile(source, str(_TEMPLATE_PATH), 'exec'), module.__dict__)
    return module


def test_sort_script_dirs_tree_first_mixed() -> None:
    """A mixed dir family orders every tree dir before every cache dir."""
    ordered = _gen._sort_script_dirs_tree_first(sorted({_CACHE_DIR, _TREE_DIR}))
    assert ordered == [_TREE_DIR, _CACHE_DIR]


def test_sort_script_dirs_tree_first_single_family_is_plain_sorted() -> None:
    """Single-family inputs stay byte-identical to alphabetical order."""
    assert _gen._sort_script_dirs_tree_first(sorted([_TREE_DIR])) == [_TREE_DIR]
    assert _gen._sort_script_dirs_tree_first(sorted([_CACHE_DIR])) == [_CACHE_DIR]


def test_generated_executor_script_dirs_tree_first() -> None:
    """The shipped template's runtime ``_SCRIPT_DIRS`` keeps tree dirs first."""
    module = _load_template_module_with_mixed_dirs()
    script_dirs = list(module._SCRIPT_DIRS)
    assert _TREE_DIR in script_dirs
    assert _CACHE_DIR in script_dirs
    last_tree = max(i for i, p in enumerate(script_dirs) if '/marketplace/bundles/' in p)
    first_cache = min(i for i, p in enumerate(script_dirs) if '/marketplace/bundles/' not in p)
    assert last_tree < first_cache

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_config_build_map_seed_fixtures import (
    _APPLICABLE_MODULES,
    _STUB_ROUTE_TRACKED_FILES,
    BuildExtensionBase,
    _extension_discovery_mod,
    _make_tracked_project_root,
)


def _wire_real_aggregator(
    monkeypatch,
    extension: BuildExtensionBase,
    modules: dict | None = None,
    tracked_files: list[str] | None = None,
) -> None:
    """Redirect aggregate_build_map()'s extension-set, module-discovery, and project root.

    aggregate_build_map() resolves derive_build_map_globs + discover_build_extensions
    + discover_all_extensions + discover_project_modules from the extension_discovery
    module at call time, and derives ``project_root`` from
    ``get_tracked_config_dir().parent``. The single supplied fake is wired as BOTH the
    build-extension set (route + build_class source via discover_build_extensions) AND
    the language-extension set (applicability source via discover_all_extensions) —
    each fake is a BuildExtensionBase subclass overriding classify_globs /
    get_skill_domains / applies_to_module, so it serves both roles. The discovered
    module set is patched to ``modules`` (default: one applicable module).

    The route deriver now reads the project tree to prune dead globs, so this also
    points ``project_root`` at a git-tracked fixture carrying a file for each stub
    route (``tracked_files`` defaults to the standard stub-route corpus). The
    ``PLAN_TRACKED_CONFIG_DIR`` override resolves ``get_tracked_config_dir()`` to a
    ``.plan`` subdir of that fixture, so its ``.parent`` is the tracked tree.
    """
    fake_build_entries = [{'skill': 'fake', 'path': 'fake/extension.py', 'module': extension}]
    fake_lang_entries = [{'bundle': 'fake', 'path': 'fake/extension.py', 'module': extension}]
    monkeypatch.setattr(_extension_discovery_mod, 'discover_build_extensions', lambda: fake_build_entries)
    monkeypatch.setattr(_extension_discovery_mod, 'discover_all_extensions', lambda: fake_lang_entries)
    monkeypatch.setattr(
        _extension_discovery_mod,
        'discover_project_modules',
        lambda project_root: _APPLICABLE_MODULES if modules is None else modules,
    )

    files = _STUB_ROUTE_TRACKED_FILES if tracked_files is None else tracked_files
    tracked_root = _make_tracked_project_root(files)
    # get_tracked_config_dir() returns this path; aggregate_build_map() takes its
    # .parent as project_root, so make the tracked tree the parent.
    monkeypatch.setenv('PLAN_TRACKED_CONFIG_DIR', str(tracked_root / '.plan'))

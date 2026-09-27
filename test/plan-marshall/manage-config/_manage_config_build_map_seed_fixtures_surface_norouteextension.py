#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_config_build_map_seed_fixtures import Path, subprocess, tempfile


def _make_tracked_project_root(rel_paths: list[str]) -> Path:
    """Create a git-tracked fixture tree and return its root.

    aggregate_build_map() resolves ``project_root = get_tracked_config_dir().parent``
    and the route deriver runs ``git ls-files`` under it, pruning routes whose
    pattern matches no tracked file. This builds a throwaway git repo carrying a
    file for each supplied repo-relative path so the stub routes survive the
    tree-presence filter.
    """
    root = Path(tempfile.mkdtemp(prefix='build-map-seed-tree-'))
    subprocess.run(['git', '-C', str(root), 'init', '-q'], check=True)
    subprocess.run(['git', '-C', str(root), 'config', 'user.email', 't@t'], check=True)
    subprocess.run(['git', '-C', str(root), 'config', 'user.name', 'T'], check=True)
    for rel in rel_paths:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('')
    subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True)
    return root

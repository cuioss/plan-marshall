# SPDX-License-Identifier: FSL-1.1-ALv2
"""
The single home for deployed-layout knowledge.

A marketplace tree exists in exactly TWO shapes, and three independent readers
used to model only the one that does not ship:

**Nested** — ``{root}/{bundle}/skills/{skill}/…``. The marketplace source tree
(``marketplace/bundles/{bundle}/skills/…``) and the Claude plugin cache
(``.../cache/plan-marshall/{version}/skills/…``) both have it.

**Flat** — ``{root}/skills/{bundle}-{skill}/…``, dash-namespaced so a flat
config directory needs no hierarchy. This is the shape the OpenCode and
Antigravity targets DEPLOY: the emitter writes a singular ``skill/`` tree
(``marketplace/targets/opencode/emitter.py``) and ``install.sh`` maps it to the
plural ``skills/`` at install time, so a machine running either target has the
flat tree and nothing that reads only the nested shape finds anything on it.

The two shapes also disagree on the ROOT DIRECTORY NAME — plural ``skills/`` in
the deployed tree, singular ``skill/`` in the generated tree — and that
one-character difference was re-probed at every call site, so the readers
disagreed about it too: ``bootstrap_plugin`` grew a ``plugin.json`` + plural
``skills/`` leg and, beside it, an ``opencode.json`` + singular ``skill/`` leg
that could never fire, because the deployed OpenCode root carries ``skills/``
and not ``skill/``.

This module expresses the whole distinction ONCE, as data, and answers three
questions behind one interface:

* :func:`resolve_skill_path` — where does this ``{bundle}:skills/{skill}/rest``
  subpath live in a root that deploys either shape?
* :func:`flat_script_dirs` — which script directories does a flat root deploy?
* :func:`skill_roots` — which skill-root directories does this root carry?

The NESTED shape's version-dir selection is deliberately NOT here. Choosing
among sibling version directories is a different concern from choosing a shape,
and it already has one owner: ``marketplace_bundles.select_live_version_dir``.
The flat tree is unversioned, so the two never apply to the same subtree.

This module reads the DEPLOYED tree. It does not change what any target emits:
the singular-to-plural mapping stays in ``install.sh`` where it already lives,
because the fix teaches the readers to read the tree that ships.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

#: The directory name a target's skills are published under, in probe order.
#:
#: The plural ``skills`` comes FIRST because it is the deployed shape: it is what
#: ``install.sh`` produces from the emitter's singular tree, and therefore what
#: every machine running a target actually has. The singular ``skill`` is the
#: GENERATED shape, present only in a target tree that has not been installed
#: yet. Listing both, once, is what lets one resolver serve a deployed root and a
#: freshly generated one; the previous per-call-site spellings disagreed about
#: the order and about which names counted at all.
SKILL_ROOT_NAMES: Final[tuple[str, ...]] = ('skills', 'skill')

#: The separator between the bundle and skill components of a FLAT skill
#: directory name. Named here so a caller never re-spells the join, which is the
#: re-encoding that made the two shapes look like two unrelated conventions.
FLAT_DIR_SEPARATOR: Final[str] = '-'

#: Manifests whose presence marks a directory as a target/plugin ROOT. A layout
#: fact (which files identify a root) rather than a shape fact, so it is data
#: too: ``bootstrap_plugin`` gated its two flat legs on one manifest each, and
#: the second leg could never fire because the deployed OpenCode root carries
#: plural ``skills/``, not singular ``skill/`` — see the module docstring.
TARGET_MANIFEST_NAMES: Final[tuple[str, ...]] = ('plugin.json', 'opencode.json')


def flat_skill_dir_name(bundle: str, skill: str) -> str:
    """Return the flat skill directory name for ``bundle`` and ``skill``.

    The single place the ``{bundle}-{skill}`` join is spelled.
    """
    return f'{bundle}{FLAT_DIR_SEPARATOR}{skill}'


def is_flat_skill_dir_name(dir_name: str) -> bool:
    """Return whether ``dir_name`` is shaped like a flat skill directory.

    A PREDICATE, not a splitter, and deliberately so. ``{bundle}-{skill}`` is
    genuinely ambiguous: real bundle and skill names are both kebab-case
    (``pm-plugin-development-plugin-script-architecture`` splits as
    ``('pm', 'plugin-development-plugin-script-architecture')`` on the first
    separator and ``('pm-plugin-development-plugin-script', 'architecture')`` on
    the last), so no separator position recovers the real components. Returning a
    pair would hand a caller an attribution that looks authoritative and is
    wrong; returning a bool answers the only question the enumeration actually
    has — "is this directory a flat skill, or something else in the root?" — and
    the caller that needs the components already has them: the bundle and skill
    are the inputs to :func:`resolve_skill_path`, and a directory's own name is
    not parsed to recover them.
    """
    bundle, separator, skill = dir_name.partition(FLAT_DIR_SEPARATOR)
    return bool(separator and bundle and skill)


def skill_roots(root: Path) -> list[Path]:
    """Return the skill-root directories ``root`` actually carries, in probe order.

    Both spellings are probed, and the order comes from
    :data:`SKILL_ROOT_NAMES` rather than from a call site's preference. A root
    carrying neither yields an empty list, which every caller here reads as "this
    root does not deploy the flat shape" and falls through from.
    """
    return [root / name for name in SKILL_ROOT_NAMES if (root / name).is_dir()]


def is_flat_root(root: Path) -> bool:
    """Return whether ``root`` carries a skill root, i.e. deploys the flat shape."""
    return bool(skill_roots(root))


def carries_target_manifest(root: Path) -> bool:
    """Return whether ``root`` carries one of :data:`TARGET_MANIFEST_NAMES`."""
    return any((root / name).is_file() for name in TARGET_MANIFEST_NAMES)


def skill_scripts_subpath(skill: str) -> str:
    """Return the NESTED-layout subpath addressing a skill's ``scripts/`` directory.

    A skill-relative path is addressed in ONE vocabulary, whatever layout the
    consuming root deploys: a flat root has no ``{bundle}/`` component to carry
    the skill, so it is reconstructed from this subpath by
    :func:`resolve_skill_path`, which re-joins the bundle with the
    dash-namespaced name. Spelling ``'skills/{skill}/scripts'`` at each call site
    instead is how the two spellings came to disagree.
    """
    return f'{SKILL_ROOT_NAMES[0]}/{skill}/scripts'


def split_skill_relative_path(relative_path: str) -> tuple[str, str] | None:
    """Split ``{skill-root}/{skill}/rest`` into ``(skill, rest)``.

    Returns ``None`` for any other shape, so a caller can tell a skill-anchored
    subpath from a root-anchored one (``agents/foo.md``) and handle the two
    differently instead of guessing.
    """
    parts = relative_path.split('/', 2)
    if len(parts) < 2 or parts[0] not in SKILL_ROOT_NAMES:
        return None
    return parts[1], (parts[2] if len(parts) > 2 else '')


def resolve_skill_path(root: Path, bundle: str, relative_path: str) -> Path | None:
    """Resolve a skill-anchored subpath against a flat root, or ``None``.

    ``relative_path`` is the nested-layout spelling (``skills/{skill}/rest``);
    the bundle is re-joined with the skill's flat name. Both skill-root
    spellings are probed, in :data:`SKILL_ROOT_NAMES` order.

    Returns ``None`` — never a constructed path — when the subpath is not
    skill-anchored or when no candidate exists. A caller that gets ``None`` has
    learned nothing about the filesystem and can try its next strategy, which is
    what lets this be a fallible probe rather than a second guess. The
    never-``None`` contract belongs to the callers that own a fallback
    construction (``marketplace_bundles.resolve_bundle_path``).
    """
    split = split_skill_relative_path(relative_path)
    if split is None:
        return None
    skill, rest = split
    for skills_root in skill_roots(root):
        candidate = skills_root / flat_skill_dir_name(bundle, skill)
        if rest:
            candidate = candidate / rest
        if candidate.exists():
            return candidate
    return None


def flat_skill_dirs(root: Path) -> list[Path]:
    """Return every skill directory a flat root deploys, in probe order.

    Only the FLAT shape. The nested shape is a bundle's own subtree and its
    version-dir selection belongs to
    ``marketplace_bundles.select_live_version_dir``; mixing the two here would
    put a second version-selection policy behind one name.
    """
    dirs: list[Path] = []
    for skills_root in skill_roots(root):
        for skill_dir in sorted(skills_root.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith('.'):
                continue
            if not is_flat_skill_dir_name(skill_dir.name):
                continue
            dirs.append(skill_dir)
    return dirs


def flat_script_dirs(root: Path) -> list[Path]:
    """Return every ``scripts/`` directory a flat root deploys, in probe order.

    Each flat skill directory's immediate ``scripts/`` child, for every skill
    directory :func:`flat_skill_dirs` yields. Callers that also want skill
    sub-directories (``script-shared/scripts/build/``) append those from the
    result, which is how the nested path already behaved — the difference here
    is only that the enumeration can see a flat tree at all.

    A caller that needs the script FILES rather than their directory reads
    :func:`flat_skill_dirs` and walks from there, because a flat skill's
    notation is derived from its own directory name (a dash-joined
    ``{bundle}-{skill}``), not from any single file.
    """
    dirs: list[Path] = []
    for skill_dir in flat_skill_dirs(root):
        scripts = skill_dir / 'scripts'
        if scripts.is_dir():
            dirs.append(scripts)
    return dirs

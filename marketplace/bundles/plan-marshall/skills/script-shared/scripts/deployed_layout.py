# SPDX-License-Identifier: FSL-1.1-ALv2
"""
The single home for deployed-layout knowledge.

A marketplace tree exists in exactly TWO shapes, and three independent readers
used to model only the nested one — which the flat targets (OpenCode,
Antigravity) do not ship:

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
that could never fire ON A DEPLOYED ROOT, because a deployed root carries
``skills/`` and not ``skill/``. The singular spelling is not dead — it is what
a freshly generated, not-yet-installed tree carries, and the resolver probes both
for exactly that reason.

This module expresses the whole distinction ONCE, as data, and answers four
questions behind one interface:

* :func:`resolve_skill_path` — where does this ``{bundle}:skills/{skill}/rest``
  subpath live in a root that deploys either shape?
* :func:`flat_script_dirs` — which script directories does a flat root deploy?
* :func:`skill_roots` — which skill-root directories does this root carry?
* :func:`flat_script_inventory` — which ``{bundle}:{skill}:{script}`` notations
  does a flat root deploy? Answered from the identity the emitters record in
  each ``SKILL.md`` (:func:`read_flat_skill_identity`), never by splitting a
  directory name.

The NESTED shape's version-dir selection is deliberately NOT here. Choosing
among sibling version directories is a different concern from choosing a shape,
and it already has one owner: ``marketplace_bundles.select_live_version_dir``.
The flat tree is unversioned, so the two never apply to the same subtree.

This module reads the DEPLOYED tree. It does not change what any target emits:
the singular-to-plural mapping stays in ``install.sh`` where it already lives,
because the fix teaches the readers to read the tree that ships.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Final, NamedTuple

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
#: the second leg could never fire ON A DEPLOYED ROOT, because a deployed root
#: carries plural ``skills/``, not singular ``skill/`` — see the module docstring
#: for why the singular spelling is still probed.
TARGET_MANIFEST_NAMES: Final[tuple[str, ...]] = ('plugin.json', 'opencode.json')

#: The sync's INSTALL STAMP: the ``dist-manifest.json`` a target's sync writes at
#: the deploy root, beside the target manifest. It records the version deployed
#: there, and on a flat tree it is the ONLY version witness the install holds —
#: the flat shape has no ``{bundle}/{version}/`` directory to read one from.
DIST_MANIFEST_NAME: Final[str] = 'dist-manifest.json'


# ---------------------------------------------------------------------------
# Bundle-cache roots — where each target DEPLOYS bundles
# ---------------------------------------------------------------------------
# A skill can be DISCOVERED from many roots, but a bundle is DEPLOYED to exactly
# one place per target (``marketplace/targets/sync.py``'s ``TargetSyncConfig``):
# ``~/.config/opencode`` on OpenCode, ``~/.gemini/config/plugins/plan-marshall``
# on Antigravity, and ``~/.claude/plugins/cache/plan-marshall`` on Claude. The
# per-target root TEMPLATES therefore live in ONE data file —
# ``platform-runtime/standards/deployed-layout.json`` — read here, by the
# ``layout bundle-cache-root`` op and, through the same file, by both
# enforcement guards. A discovery-only root (a directory another tool reads
# skills from) is not a deploy root and is never a candidate.

#: The deployed-layout data file's name, beside a skill's ``standards/``.
BUNDLE_CACHE_LAYOUT_NAME: Final[str] = 'deployed-layout.json'


def load_bundle_cache_layout(standards_dir: Path) -> dict[str, object]:
    """Return the parsed deployed-layout data, or ``{}`` when it cannot be read."""
    try:
        data = json.loads((standards_dir / BUNDLE_CACHE_LAYOUT_NAME).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _expand_deploy_root(template: Mapping[str, object], env: Mapping[str, str]) -> str | None:
    """Expand one root template against *env*, or ``None`` when its base is unset."""
    append = str(template.get('append') or '')
    if 'env' in template:
        base = env.get(str(template['env']), '')
        if not base:
            return None
    elif 'xdg' in template:
        home = env.get('HOME', '')
        base = env.get('XDG_CONFIG_HOME') or (str(Path(home) / '.config') if home else '')
        if not base:
            return None
    elif 'home' in template:
        base = env.get('HOME', '')
        if not base:
            return None
    else:
        return None
    return str(Path(base).joinpath(*append.split('/'))) if append else str(Path(base))


def bundle_cache_roots(target: str, standards_dir: Path, env: Mapping[str, str] | None = None) -> list[str]:
    """Return the bundle-cache root directories *target* deploys to, in probe order.

    Reads the shared ``deployed-layout.json`` data file so the resolver and the
    guards cannot disagree about a root. Absolute, expanded and deduplicated; an
    unreadable data file yields an empty list, which the guards read as "nothing
    is a deployed root" (fail closed) rather than as "trust everything".
    """
    environment = os.environ if env is None else env
    layout = load_bundle_cache_layout(standards_dir)
    targets = layout.get('targets') if isinstance(layout.get('targets'), dict) else {}
    templates = targets.get(target) if isinstance(targets, dict) else None
    if not isinstance(templates, list):
        return []
    roots: list[str] = []
    for template in templates:
        if not isinstance(template, dict):
            continue
        expanded = _expand_deploy_root(template, environment)
        if expanded is None or expanded in roots:
            continue
        roots.append(str(Path(expanded).expanduser()))
    return roots


def all_bundle_cache_roots(standards_dir: Path, env: Mapping[str, str] | None = None) -> list[str]:
    """Return every registered target's bundle-cache roots, deduplicated.

    A machine may carry more than one harness, and a deployed script under any
    of them is still a deployed script of this marketplace — so the guards, which
    serve a session that can cross harnesses, admit the union of the roots the
    resolver names for each target. A root no target names is never in the union.
    """
    layout = load_bundle_cache_layout(standards_dir)
    targets = layout.get('targets') if isinstance(layout.get('targets'), dict) else {}
    roots: list[str] = []
    for target in targets if isinstance(targets, dict) else {}:
        for root in bundle_cache_roots(str(target), standards_dir, env):
            if root not in roots:
                roots.append(root)
    return roots


def newest_version_dir(
    bundle_dir: Path, marker: str = '.claude-plugin/plugin.json', contains: str | None = None
) -> Path | None:
    """Return the NEWEST version directory of *bundle_dir* carrying *marker*.

    ``contains`` (a bundle-relative path) restricts the candidates to the version
    directories that actually carry it — the resolver's own rule
    (``bootstrap_plugin.resolve_bundle_path``), so a version that holds the bundle
    but not the requested entry is never selected. ``None`` when no child
    qualifies, so a stray directory under the bundle is never a candidate.
    """
    from marketplace_bundles import _version_sort_key  # local import: avoids an import cycle

    if not bundle_dir.is_dir():
        return None
    candidates = [
        child
        for child in bundle_dir.iterdir()
        if child.is_dir() and (child / marker).is_file() and (contains is None or (child / contains).exists())
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda child: _version_sort_key(child.name))


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


def is_bundle_skill_root(path: Path) -> bool:
    """Return whether ``path`` is a NESTED bundle's own ``skills/`` directory.

    A bundle's ``skills/`` sits beside that bundle's ``.claude-plugin/plugin.json``
    (the marketplace source and every plugin-cache version dir alike). Its
    children are bare skill names, many of them kebab-case, so reading it as a
    flat skill root would misattribute every one of them.
    """
    return (path.parent / '.claude-plugin' / 'plugin.json').is_file()


def is_flat_skill_root(path: Path) -> bool:
    """Return whether ``path`` IS a flat skill root in its own right.

    A flat skill root is a directory named by :data:`SKILL_ROOT_NAMES` whose
    parent carries no bundle marker — that is, the ``skills/`` (or generated
    ``skill/``) directory a flat deployment puts its ``{bundle}-{skill}``
    directories under. A NESTED bundle's own ``skills/`` directory is excluded
    (:func:`is_bundle_skill_root`): its children are bare skill names.

    The single spelling of the predicate. Both the root resolver
    (``marketplace_bundles.resolve_bundles_root``) and :func:`skill_roots` consult
    it, so the two cannot disagree about which directories count.
    """
    return path.name in SKILL_ROOT_NAMES and path.is_dir() and not is_bundle_skill_root(path)


def flat_deploy_root(skill_dir: Path) -> Path | None:
    """Return the deploy root a FLAT skill directory belongs to, or ``None``.

    ``{root}/skills/{bundle}-{skill}`` is a flat skill; its deploy root is the
    directory CONTAINING that skill root, which is where the sync writes its
    install stamp (:data:`DIST_MANIFEST_NAME`).

    ``None`` for a NESTED skill directory (a bundle's own ``skills/``) and for
    any path that is not a flat skill at all, so a caller falls through instead
    of reading a stamp that layout never writes.
    """
    if not skill_dir.is_dir() or not is_flat_skill_root(skill_dir.parent):
        return None
    if not is_flat_skill_dir_name(skill_dir.name):
        return None
    return skill_dir.parent.parent


def read_deploy_stamp_version(deploy_root: Path) -> str | None:
    """Return the version the deploy root's install stamp records, or ``None``.

    ``None`` covers every case a caller must not turn into a version it did not
    read: no stamp, an unreadable or non-object payload, and a payload whose
    ``version`` is absent, empty or not a string.
    """
    try:
        payload = json.loads((deploy_root / DIST_MANIFEST_NAME).read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    version = payload.get('version')
    return version if isinstance(version, str) and version else None


def skill_roots(root: Path) -> list[Path]:
    """Return the skill-root directories ``root`` actually carries, in probe order.

    ``root`` may be handed over in either of the two forms a flat deployment is
    reachable by:

    * the directory CONTAINING the skill root (``~/.config/opencode``), whose
      ``skills/`` / ``skill/`` children are probed in :data:`SKILL_ROOT_NAMES`
      order; or
    * the skill root ITSELF (``~/.config/opencode/skills``). This is the form the
      runtimes' ``layout bundle-cache-root`` op returns, so it is the base every
      cache-first consumer is actually handed. Reading only the first form found
      nothing on the base that ships.

    A NESTED bundle's own ``skills/`` directory is not a flat skill root and is
    never returned for the second form (:func:`is_flat_skill_root`). A root
    carrying neither yields an empty list, which every caller here reads as "this
    root does not deploy the flat shape" and falls through from.
    """
    roots: list[Path] = []
    if is_flat_skill_root(root):
        roots.append(root)
    roots.extend(root / name for name in SKILL_ROOT_NAMES if (root / name).is_dir())
    return roots


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


def flat_skill_paths(root: Path, bundle: str, relative_path: str) -> list[Path]:
    """Return the flat candidates a skill-anchored subpath could have, in probe order.

    The CONSTRUCTION half of :func:`resolve_skill_path`, split out so a caller that
    must REPORT a miss can name the path a flat install would carry: the resolver
    returns ``None`` on a miss and therefore carries no path to report.

    Returns an empty list for a subpath that is not skill-anchored, or for a root
    that deploys no flat shape (:func:`skill_roots`).
    """
    split = split_skill_relative_path(relative_path)
    if split is None:
        return []
    skill, rest = split
    candidates: list[Path] = []
    for skills_root in skill_roots(root):
        candidate = skills_root / flat_skill_dir_name(bundle, skill)
        if rest:
            candidate = candidate / rest
        candidates.append(candidate)
    return candidates


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
    for candidate in flat_skill_paths(root, bundle, relative_path):
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

    A caller that needs the script FILES and their notations reads
    :func:`flat_script_inventory`, which derives each notation from the identity
    the skill's ``SKILL.md`` records — never from the dash-joined directory
    name, which cannot be split.
    """
    dirs: list[Path] = []
    for skill_dir in flat_skill_dirs(root):
        scripts = skill_dir / 'scripts'
        if scripts.is_dir():
            dirs.append(scripts)
    return dirs


# ---------------------------------------------------------------------------
# Flat skill IDENTITY — the bundle a flat directory belongs to
# ---------------------------------------------------------------------------
# ``{bundle}-{skill}`` cannot be split (see :func:`is_flat_skill_dir_name`), so a
# flat directory's NAME never yields a ``{bundle}:{skill}:{script}`` notation.
# The flat-target emitters therefore RECORD the identity in the skill's own
# ``SKILL.md`` frontmatter, under the Agent Skills ``metadata`` map:
#
#     metadata:
#       bundle: plan-marshall
#       skill: manage-status
#
# and this module is the one reader of it. The identity is accepted only when it
# re-joins to the directory's own name, so a copied or renamed directory cannot
# claim a notation it does not carry.

#: The frontmatter map the identity lives under, and its two keys. The flat
#: emitters write these spellings through ``marketplace/targets/skill_identity.py``;
#: ``test_flat_skill_identity_emission.py`` pins that the emitted tree reads back
#: through :func:`read_flat_skill_identity`.
IDENTITY_METADATA_KEY: Final[str] = 'metadata'
IDENTITY_BUNDLE_KEY: Final[str] = 'bundle'
IDENTITY_SKILL_KEY: Final[str] = 'skill'


def _frontmatter_metadata(text: str) -> dict[str, str]:
    """Return the ``metadata:`` map of a SKILL.md frontmatter block, or ``{}``.

    A deliberately narrow reader (stdlib only, no YAML dependency): the block
    this reads is written by our own emitters in one fixed shape — a top-level
    ``metadata:`` key followed by indented ``key: value`` lines.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return {}
    metadata: dict[str, str] = {}
    in_metadata = False
    for line in lines[1:]:
        if line.strip() == '---':
            break
        if not line.startswith((' ', '\t')):
            in_metadata = line.rstrip() == f'{IDENTITY_METADATA_KEY}:'
            continue
        if in_metadata:
            key, separator, value = line.strip().partition(':')
            if separator:
                metadata[key.strip()] = value.strip().strip('"\'')
    return metadata


def read_flat_skill_identity(skill_dir: Path) -> tuple[str, str] | None:
    """Return the ``(bundle, skill)`` a flat skill directory records, or ``None``.

    ``None`` means UNATTRIBUTABLE: no ``SKILL.md``, no recorded identity, or an
    identity that does not re-join to the directory name. The caller reports an
    unattributable directory; it never guesses a split.
    """
    try:
        text = (skill_dir / 'SKILL.md').read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None
    metadata = _frontmatter_metadata(text)
    bundle = metadata.get(IDENTITY_BUNDLE_KEY, '')
    skill = metadata.get(IDENTITY_SKILL_KEY, '')
    if not bundle or not skill or flat_skill_dir_name(bundle, skill) != skill_dir.name:
        return None
    return bundle, skill


def script_notation(bundle: str, skill: str, script_file: Path) -> str:
    """Return the ``{bundle}:{skill}:{stem}`` notation for a script file.

    The ONE notation-derivation rule. The executor's coverage enumerator and the
    marketplace inventory scanner both build notations through it, on either
    layout, so the two sides of the coverage comparison cannot disagree about
    how a script is named.
    """
    return f'{bundle}:{skill}:{script_file.stem}'


def is_private_script(script_file: Path) -> bool:
    """Whether ``script_file`` is an internal module rather than a CLI entrypoint."""
    return script_file.name.startswith('_')


def skill_script_files(scripts_dir: Path) -> list[Path]:
    """Return every ``.sh`` / ``.py`` file under ``scripts_dir``, recursively.

    Shell files first, then Python, each sorted — the candidate order both
    discovery sides already used for the nested layout, so a colliding stem
    resolves to the same file on either side.
    """
    return sorted(scripts_dir.rglob('*.sh')) + sorted(scripts_dir.rglob('*.py'))


class FlatScript(NamedTuple):
    """One public script of an attributable flat skill."""

    bundle: str
    skill: str
    path: Path

    @property
    def notation(self) -> str:
        return script_notation(self.bundle, self.skill, self.path)


class FlatScriptInventory(NamedTuple):
    """Everything a flat root's script walk found, partitioned by disposition.

    ``unattributed`` lists the flat skill directories that carry a ``scripts/``
    directory but no readable identity: their scripts exist and cannot be named,
    so they are reported rather than silently dropped.
    """

    scripts: list[FlatScript]
    private: list[Path]
    unattributed: list[Path]


def flat_script_inventory(root: Path) -> FlatScriptInventory:
    """Walk every flat skill under ``root`` and classify its script files.

    The single flat-layout walk. Both sides of the executor's discovery-coverage
    comparison call it, so they enumerate the same population by construction.
    """
    scripts: list[FlatScript] = []
    private: list[Path] = []
    unattributed: list[Path] = []
    for skill_dir in flat_skill_dirs(root):
        scripts_dir = skill_dir / 'scripts'
        if not scripts_dir.is_dir():
            continue
        identity = read_flat_skill_identity(skill_dir)
        if identity is None:
            unattributed.append(skill_dir)
            continue
        bundle, skill = identity
        for script_file in skill_script_files(scripts_dir):
            if not script_file.is_file():
                continue
            if is_private_script(script_file):
                private.append(script_file)
                continue
            scripts.append(FlatScript(bundle, skill, script_file))
    return FlatScriptInventory(scripts, private, unattributed)

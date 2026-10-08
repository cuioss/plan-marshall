#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Single sync engine for every plan-marshall harness — the ``sync-harnesses`` command.

Pipeline:
    marketplace/bundles/  →  target/{target}/  →  the harness's own install location

One engine syncs the generated trees of all three harnesses. With no
``--target`` it runs ``claude``, ``opencode`` and ``antigravity`` in that
fixed order, attempting each one even when an earlier one failed. With
``--target X`` it runs exactly that harness's path.

Target profiles:
* **claude**: Source is ``target/claude/``. Destination is the versioned
  plugin cache ``~/.claude/plugins/cache/plan-marshall/{bundle}/{version}/``,
  mirrored per bundle with ``rsync``, plus the top-level
  ``dist-manifest.json`` at the cache root. A staleness guard refuses a
  tree that is stale relative to ``marketplace/bundles/``. The
  implementation lives in ``marketplace/targets/claude/cache_sync.py`` and
  is loaded BY FILE LOCATION — never through the ``marketplace.targets`` /
  ``claude`` packages, whose ``__init__`` modules import third-party
  dependencies — so this engine stays runnable under a bare ``python3``
  with only the stdlib and ``toon_parser``.
* **opencode**: Source layout is singular (``skill/``, ``agent/``, ``command/``).
  Destination is ``~/.config/opencode/`` with plural layout (``skills/``,
  ``agents/``, ``commands/``). Deploys ``opencode.json``.
* **antigravity**: Source layout is plural (``skills/``, ``agents/``,
  ``commands/``). Destination is ``~/.gemini/config/plugins/plan-marshall/``.
  Deploys root assets ``plugin.json``, ``install.sh`` (chmod 0o755), and ``README.adoc``.

Flags:
    --target NAME          Sync one harness only (claude, opencode, antigravity).
    --bundles NAME         Restrict every selected target to a single bundle.
    --dry-run              Report what would be synced; write nothing.
    --source PATH          Override the source root. Single-target only.
    --target-dir PATH      Override the destination of the opencode or
                           antigravity target. Single-target only.
    --from-worktree PATH   Claude path: resolve the source from
                           {PATH}/target/claude/ and compare it against
                           {PATH}/marketplace/bundles/.
    --cache-root PATH      Claude path: override the cache destination root.
    --skip-staleness-guard Claude path: bypass the staleness check
                           (reserved for tests and recovery flows).
    --registry-path PATH   Claude path: the plugin registry file the
                           registry_parity block reads (default:
                           ~/.claude/plugins/installed_plugins.json).
    --repin                Claude path: after the cache sync, repin the
                           plugin registry to the synced version (runs
                           marketplace/targets/claude/registry_pin.py in
                           its apply mode). Without it the registry is
                           only read.

Registry parity (Claude path):
    The cache sync moves the plugin CACHE forward; the plugin REGISTRY
    still names the version it was pinned at, and a restarted session
    loads what the registry names. After the cache sync the Claude leg
    therefore reads the registry and reports, as the LAST block of its
    result, whether the pin follows the version this invocation synced:

        registry_parity:
          registry_path: "<path>"          # absent when no registry was read
          registry_state: ok | absent | io_error | not_json |
                          no_plan_marshall_entry | not_read
          reason: "<why>"                  # only on an unreadable verdict
          repin: applied | failed | skipped_dry_run | skipped_registry_not_read |
                 skipped_nothing_synced    # only when --repin was given
          repin_message: "<error>"         # only when repin is failed
          entries[K]{bundle,scope,install_path_version,version,synced_version,orphan_marked}:
            plan-marshall,user,0.1.100,0.1.100,0.1.200,false
          verdict: in_parity | behind | ahead | unreadable

    One ``entries`` row per plan-marshall entry of every scope.
    ``synced_version`` is the version this invocation synced for the row's
    bundle — the reference the row is judged against, never
    ``dist-manifest.json`` — or ``not_synced`` when the bundle was not part
    of this run; such a row is shown and takes no part in the verdict.
    ``orphan_marked`` states whether the synced directory carries
    ``.orphaned_at``. The verdict is exactly one of the four values of the
    shared reader (``script-shared``'s ``plugin_registry``):

    * ``in_parity`` — every judged entry is pinned at the synced version.
    * ``behind`` — an entry is pinned older than the synced version and no
      same-invocation repin closed the gap. The Claude ``status`` becomes
      ``partial`` while ``cache_status`` stays the cache-sync outcome, the
      ``summary_message`` names the pinned version, the synced version and
      the repin command, and the exit code is 3.
    * ``ahead`` — an entry is pinned newer than the synced version.
      Reported, not red: neither ``status`` nor the exit code changes.
    * ``unreadable`` — parity could not be established (no registry, no
      entry of a synced bundle, an unknown pinned field); ``reason`` says
      why. Neither ``status`` nor the exit code changes.

    When ``--cache-root`` is overridden and ``--registry-path`` is not, no
    registry is read and the verdict is ``unreadable``: a fixture cache
    root is never judged against the machine's live registry. ``--dry-run``
    reports the verdict against the versions it would sync and writes
    nothing — no registry write happens under ``--dry-run --repin`` either.
    A staleness-guard refusal synced nothing and carries no
    ``registry_parity`` block.

Single-target output — ``--target opencode`` / ``--target antigravity``:
    status: success | error
    target: antigravity | opencode
    source: <path>
    destination: <path>
    skills_count: N
    agents_count: N
    commands_count: N
    assets_count | config_count: N
    deployed_count: N
    removed_count: M
    summary_message: "<summary>"
    dry_run: true                        # only when --dry-run
    removed[M]{kind,name}:               # only when removed_count > 0
      skills,plan-marshall-old-skill

Single-target output — ``--target claude`` (see ``cache_sync.py``):
    status: success | partial | error
    cache_status: success | partial | error
    synced_count: N
    failed_count: M
    summary_message: "<summary>"
    guard_outcome: stale | probe_failed  # only on a guard refusal
    dry_run: true                        # only when --dry-run
    synced[N]{bundle,version,status}:
    failed[M]{bundle,error}:             # only when failed_count > 0
    registry_parity:                     # absent only on a guard refusal
      <see "Registry parity" above>      # or when the leg could not start

``cache_status`` is always present and carries the outcome of the cache
sync alone; ``status`` differs from it only when a ``behind`` registry
lowered a ``success`` to ``partial``.

All-targets output (no ``--target``) — one aggregate document:
    status: success | partial | error
    targets[3]{target,status,summary_message}:
      claude,success,"synced 10 bundle(s) to ..."
      opencode,success,"deployed 164 components, ..."
      antigravity,error,"source not found: ..."
    claude:
      <the claude result block>
    opencode:
      <the opencode result block>
    antigravity:
      <the antigravity result block>

The aggregate ``status`` is ``success`` only when every target reported
``success``, ``partial`` when some did, and ``error`` when none did. The
``targets`` table keeps exactly its three columns; ``cache_status`` and
the ``registry_parity`` block live in the ``claude`` block only. A Claude
leg whose registry is ``behind`` reports ``partial``, so the aggregate is
not ``success`` and the run exits 1.

Exit codes:
    All targets:
        0 on aggregate ``status: success``
        1 on aggregate ``status: partial`` or ``status: error``
    ``--target opencode`` / ``--target antigravity``:
        0 on ``status: success``
        1 on ``status: error`` (source missing, empty source, etc.)
    ``--target claude``:
        0 on ``status: success`` or ``status: partial`` with the registry
          not ``behind``
        1 on ``status: error`` (nothing synced)
        2 on a staleness-guard refusal
        3 when the cache sync itself exited 0 and the ``registry_parity``
          verdict is ``behind``
    2 on rejected arguments (argparse).
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, TextIO

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TOON_DIR = _PROJECT_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'ref-toon-format' / 'scripts'
if _TOON_DIR.is_dir() and str(_TOON_DIR) not in sys.path:
    sys.path.insert(0, str(_TOON_DIR))

from toon_parser import serialize_toon  # noqa: E402

VERBATIM_SKILL_SUBDIRS: tuple[str, ...] = ('standards', 'references', 'templates', 'scripts')

#: The Claude target's name. Its sync path is the plugin-cache mirror in
#: ``cache_sync.py`` rather than a :class:`TargetSyncConfig` deploy.
CLAUDE_TARGET = 'claude'

#: Every harness this engine syncs, in the fixed order an all-targets run
#: attempts them.
SYNC_TARGETS: tuple[str, ...] = (CLAUDE_TARGET, 'opencode', 'antigravity')

#: Repo-relative location of the Claude cache-sync module.
CACHE_SYNC_RELPATH = Path('marketplace') / 'targets' / 'claude' / 'cache_sync.py'

#: Module name the Claude cache-sync module is loaded under. Deliberately
#: NOT ``marketplace.targets.claude.cache_sync`` — see
#: :func:`_load_cache_sync_module` for why the package path is avoided.
CACHE_SYNC_MODULE_NAME = '_sync_harnesses_claude_cache_sync'

#: Repo-relative location of the opt-in registry repin module.
REGISTRY_PIN_RELPATH = Path('marketplace') / 'targets' / 'claude' / 'registry_pin.py'
REGISTRY_PIN_MODULE_NAME = '_sync_harnesses_claude_registry_pin'

#: Repo-relative location of the shared plugin-registry reader.
PLUGIN_REGISTRY_RELPATH = (
    Path('marketplace') / 'bundles' / 'plan-marshall' / 'skills' / 'script-shared' / 'scripts' / 'plugin_registry.py'
)
PLUGIN_REGISTRY_MODULE_NAME = '_sync_harnesses_plugin_registry'

#: Exit code of a Claude sync whose cache sync succeeded while the plugin
#: registry is pinned behind the synced version.
EXIT_REGISTRY_BEHIND = 3

#: ``registry_state`` of a ``registry_parity`` block for which no registry
#: file was read at all. The other states are the shared reader's own.
REGISTRY_STATE_NOT_READ = 'not_read'

#: ``synced_version`` of a registry entry whose bundle this run did not sync.
NOT_SYNCED = 'not_synced'

#: How a registry field the reader reports as unknown is rendered in a row.
UNKNOWN = 'unknown'

#: The command that closes a ``behind`` verdict, named in the summary message.
REPIN_COMMAND = f'python3 {REGISTRY_PIN_RELPATH.as_posix()} --apply'

# ``repin`` outcomes of a ``registry_parity`` block (present only under --repin).
REPIN_APPLIED = 'applied'
REPIN_FAILED = 'failed'
REPIN_SKIPPED_DRY_RUN = 'skipped_dry_run'
REPIN_SKIPPED_REGISTRY_NOT_READ = 'skipped_registry_not_read'
REPIN_SKIPPED_NOTHING_SYNCED = 'skipped_nothing_synced'


@dataclass(frozen=True)
class TargetSyncConfig:
    name: str
    default_dest: Path
    source_skills_dir: str
    source_agents_dir: str
    source_commands_dir: str
    root_assets: tuple[tuple[str, str, bool], ...]  # (filename, kind, is_executable)
    extra_count_key: str


TARGET_CONFIGS: dict[str, TargetSyncConfig] = {
    'antigravity': TargetSyncConfig(
        name='antigravity',
        default_dest=Path.home() / '.gemini' / 'config' / 'plugins' / 'plan-marshall',
        source_skills_dir='skills',
        source_agents_dir='agents',
        source_commands_dir='commands',
        root_assets=(
            ('plugin.json', 'config', False),
            ('install.sh', 'asset', True),
            ('README.adoc', 'asset', False),
        ),
        extra_count_key='assets_count',
    ),
    'opencode': TargetSyncConfig(
        name='opencode',
        default_dest=Path.home() / '.config' / 'opencode',
        source_skills_dir='skill',
        source_agents_dir='agent',
        source_commands_dir='command',
        root_assets=(('opencode.json', 'config', False),),
        extra_count_key='config_count',
    ),
}


def _resolve_source(config: TargetSyncConfig, source_arg: Path | None) -> Path:
    if source_arg is not None:
        return source_arg.resolve()
    return (Path.cwd() / 'target' / config.name).resolve()


def _resolve_dest(config: TargetSyncConfig, target_dir_arg: Path | None) -> Path:
    if target_dir_arg is not None:
        return target_dir_arg.resolve()
    return config.default_dest.resolve()


def _enumerate_source_skills(source: Path, config: TargetSyncConfig, only_bundle: str | None) -> list[Path]:
    skills_root = source / config.source_skills_dir
    if not skills_root.is_dir():
        return []
    result = []
    prefix = f'{only_bundle}-' if only_bundle else None
    for entry in sorted(skills_root.iterdir()):
        if not entry.is_dir():
            continue
        if prefix and not (entry.name == only_bundle or entry.name.startswith(prefix)):
            continue
        if (entry / 'SKILL.md').is_file():
            result.append(entry)
    return result


def _enumerate_source_agents(source: Path, config: TargetSyncConfig) -> list[Path]:
    agents_root = source / config.source_agents_dir
    if not agents_root.is_dir():
        return []
    return sorted(entry for entry in agents_root.iterdir() if entry.is_file() and entry.suffix == '.md')


def _enumerate_source_commands(source: Path, config: TargetSyncConfig, only_bundle: str | None) -> list[Path]:
    commands_root = source / config.source_commands_dir
    if not commands_root.is_dir():
        return []
    result = []
    for entry in sorted(commands_root.iterdir()):
        if not (entry.is_file() and entry.suffix == '.md'):
            continue
        if only_bundle and not (entry.name == f'{only_bundle}.md' or entry.name.startswith(f'{only_bundle}-')):
            continue
        result.append(entry)
    return result


def _derive_synced_bundles(skills: list[Path], commands: list[Path], only_bundle: str | None) -> set[str]:
    """Derive the set of bundle names being synced.

    When ``only_bundle`` is given, it is returned directly. Otherwise:
    1. Read known bundle names from ``marketplace/bundles/`` if present.
    2. Match each source skill/command against the known bundles using
       the longest matching prefix.
    3. Fall back to first-hyphen splitting only when ``marketplace/bundles/``
       is missing or has no subdirectories (e.g. in test fixtures that isolate
       the destination directory).
    """
    if only_bundle is not None:
        return {only_bundle}

    bundles_dir = Path.cwd() / 'marketplace' / 'bundles'
    if not bundles_dir.is_dir():
        bundles_dir = _PROJECT_ROOT / 'marketplace' / 'bundles'
    if bundles_dir.is_dir():
        known_bundles = {p.name for p in bundles_dir.iterdir() if p.is_dir()}
        if known_bundles:
            matched: set[str] = set()
            for path in list(skills) + list(commands):
                name = path.name.removesuffix('.md')
                matches = [kb for kb in known_bundles if name == kb or name.startswith(f'{kb}-')]
                if matches:
                    matched.add(max(matches, key=len))
            if matched:
                return matched

    bundles: set[str] = set()
    for path in list(skills) + list(commands):
        name = path.name.removesuffix('.md')
        if '-' in name:
            bundles.add(name.split('-', 1)[0])
        elif name:
            bundles.add(name)
    return bundles


def _is_managed_skill(dir_name: str, synced_bundles: set[str]) -> bool:
    return any(dir_name == b or dir_name.startswith(f'{b}-') for b in synced_bundles)


def _is_managed_command(file_name: str, synced_bundles: set[str]) -> bool:
    if not file_name.endswith('.md'):
        return False
    stem = file_name[:-3]
    return any(stem == b or stem.startswith(f'{b}-') for b in synced_bundles)


def _prune_managed(
    dest: Path,
    source_skills: set[str],
    source_commands: set[str],
    synced_bundles: set[str],
    *,
    dry_run: bool,
) -> list[dict[str, str]]:
    removed: list[dict[str, str]] = []

    skills_dest = dest / 'skills'
    if skills_dest.is_dir():
        for entry in sorted(skills_dest.iterdir()):
            if not entry.is_dir():
                continue
            if not _is_managed_skill(entry.name, synced_bundles):
                continue
            if entry.name in source_skills:
                continue
            removed.append({'kind': 'skills', 'name': entry.name})
            if not dry_run:
                shutil.rmtree(entry)

    commands_dest = dest / 'commands'
    if commands_dest.is_dir():
        for entry in sorted(commands_dest.iterdir()):
            if not entry.is_file():
                continue
            if not _is_managed_command(entry.name, synced_bundles):
                continue
            if entry.name in source_commands:
                continue
            removed.append({'kind': 'commands', 'name': entry.name})
            if not dry_run:
                entry.unlink()

    return removed


def _deploy_skill(skill_dir: Path, dest: Path, *, dry_run: bool) -> None:
    target = dest / 'skills' / skill_dir.name
    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(skill_dir / 'SKILL.md', target / 'SKILL.md')

    for subdir_name in VERBATIM_SKILL_SUBDIRS:
        src_sub = skill_dir / subdir_name
        if src_sub.exists() and src_sub.is_dir():
            dst_sub = target / subdir_name
            if not dry_run:
                if dst_sub.exists():
                    shutil.rmtree(dst_sub)
                shutil.copytree(src_sub, dst_sub)


def _deploy_agent(agent_file: Path, dest: Path, *, dry_run: bool) -> None:
    target = dest / 'agents' / agent_file.name
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(agent_file, target)


def _deploy_command(command_file: Path, dest: Path, *, dry_run: bool) -> None:
    target = dest / 'commands' / command_file.name
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(command_file, target)


def _deploy_root_assets(source: Path, dest: Path, config: TargetSyncConfig, *, dry_run: bool) -> int:
    count = 0
    for asset_file, _kind, is_executable in config.root_assets:
        asset_src = source / asset_file
        if asset_src.is_file():
            target = dest / asset_file
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(asset_src, target)
                if is_executable:
                    target.chmod(0o755)
            count += 1
    return count


def _deploy_error(
    *,
    target: str,
    summary_message: str,
    source: Path | None = None,
    dest: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        'status': 'error',
        'target': target,
        'summary_message': summary_message,
        'removed_count': 0,
    }
    if source is not None:
        data['source'] = str(source)
    if dest is not None:
        data['destination'] = str(dest)
    if dry_run:
        data['dry_run'] = True
    return data


def _deploy_target(
    target_name: str,
    *,
    source: Path | None,
    dest: Path | None,
    only_bundle: str | None,
    dry_run: bool,
) -> tuple[int, dict[str, Any]]:
    """Deploy one generated component tree. Returns ``(exit_code, result)``."""
    if target_name not in TARGET_CONFIGS:
        msg = f'unknown target: {target_name} (valid: {", ".join(sorted(TARGET_CONFIGS.keys()))})'
        return 1, _deploy_error(target=target_name, summary_message=msg, dry_run=dry_run)

    config = TARGET_CONFIGS[target_name]
    src = _resolve_source(config, source)
    dst = _resolve_dest(config, dest)

    if not src.is_dir():
        msg = f'source not found: {src}'
        return 1, _deploy_error(target=target_name, summary_message=msg, source=src, dest=dst, dry_run=dry_run)

    skills = _enumerate_source_skills(src, config, only_bundle)
    agents = _enumerate_source_agents(src, config)
    commands = _enumerate_source_commands(src, config, only_bundle)

    has_root_assets = any((src / asset_file).is_file() for asset_file, _kind, _exec in config.root_assets)

    if not skills and not agents and not commands and not has_root_assets:
        msg = f'source contains no emit output: {src}'
        return 1, _deploy_error(target=target_name, summary_message=msg, source=src, dest=dst, dry_run=dry_run)

    synced_bundles = _derive_synced_bundles(skills, commands, only_bundle)

    removed = _prune_managed(
        dst,
        {s.name for s in skills},
        {c.name for c in commands},
        synced_bundles,
        dry_run=dry_run,
    )

    for skill_dir in skills:
        _deploy_skill(skill_dir, dst, dry_run=dry_run)

    for agent_file in agents:
        _deploy_agent(agent_file, dst, dry_run=dry_run)

    for command_file in commands:
        _deploy_command(command_file, dst, dry_run=dry_run)

    extra_count = _deploy_root_assets(src, dst, config, dry_run=dry_run)

    deployed_count = len(skills) + len(agents) + len(commands) + extra_count

    data: dict[str, Any] = {
        'status': 'success',
        'target': target_name,
        'source': str(src),
        'destination': str(dst),
        'skills_count': len(skills),
        'agents_count': len(agents),
        'commands_count': len(commands),
        config.extra_count_key: extra_count,
        'deployed_count': deployed_count,
        'removed_count': len(removed),
        'summary_message': f'deployed {deployed_count} components, removed {len(removed)} stale entries to {dst}',
    }
    if dry_run:
        data['dry_run'] = True
    if removed:
        data['removed'] = removed
    return 0, data


def sync_target(
    target_name: str,
    *,
    source: Path | None = None,
    dest: Path | None = None,
    only_bundle: str | None = None,
    dry_run: bool = False,
    stdout: TextIO | None = None,
) -> int:
    """Deploy the ``opencode`` or ``antigravity`` tree and write its result."""
    out = stdout if stdout is not None else sys.stdout
    exit_code, data = _deploy_target(target_name, source=source, dest=dest, only_bundle=only_bundle, dry_run=dry_run)
    out.write(serialize_toon(data))
    return exit_code


def _load_cache_sync_module() -> ModuleType:
    """Load the Claude cache-sync module BY FILE LOCATION, not by package path.

    ``marketplace/targets/claude/cache_sync.py`` is stdlib-only. Reaching
    it through ``marketplace.targets.claude.cache_sync`` would first
    execute ``marketplace/targets/__init__.py`` and
    ``marketplace/targets/claude/__init__.py``, which import every
    registered target and, through them, third-party dependencies
    (``yaml``) that a bare ``python3`` with no project virtualenv does not
    carry. Loading the single file executes exactly that module.

    Raises:
        ImportError: the module file is absent, has no loadable spec, or
            fails while executing.
    """
    return _load_module_by_location(CACHE_SYNC_MODULE_NAME, CACHE_SYNC_RELPATH, 'claude cache-sync module')


def _load_module_by_location(module_name: str, relpath: Path, label: str) -> ModuleType:
    """Execute the single file at ``relpath`` (repo-relative) as ``module_name``.

    The module is executed afresh on every call and is not registered in
    ``sys.modules``, so a value it derives at import time (a default path
    under the home directory) reflects the environment of this call.

    Raises:
        ImportError: the file is absent, has no loadable spec, or fails
            while executing. Every failure is normalised to ``ImportError``.
    """
    module_path = _PROJECT_ROOT / relpath
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f'no loadable module spec for {label} at {module_path}')

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # normalised to ImportError below
        raise ImportError(f'{label} at {module_path} failed to import: {exc}') from exc
    return module


def _synced_versions(cache_sync: ModuleType, synced_rows: list[dict[str, str]]) -> dict[str, str]:
    """The version this invocation synced, per bundle — the parity reference.

    A bundle whose sync failed has no synced version and is left out. Under
    ``--dry-run`` the version a bundle WOULD be synced at stands in, so the
    dry run reports the verdict the real run would start from.
    """
    counted = ('success', cache_sync.DRY_RUN_ROW_STATUS)
    return {row['bundle']: row['version'] for row in synced_rows if row['status'] in counted}


def _resolve_registry_path(args: argparse.Namespace, registry_pin: ModuleType) -> tuple[Path | None, str | None]:
    """Return ``(registry_path, reason)``; exactly one of the two is ``None``.

    An overridden ``--cache-root`` without ``--registry-path`` yields no
    path: a fixture cache root must never be judged against, or repinned
    into, the machine's live registry.
    """
    if args.registry_path is not None:
        return args.registry_path, None
    if args.cache_root is not None:
        return None, '--cache-root is overridden and --registry-path is not given, so no plugin registry was read'
    return registry_pin.DEFAULT_REGISTRY_PATH, None


def _apply_repin(
    args: argparse.Namespace,
    registry_pin: ModuleType,
    registry_path: Path | None,
    cache_root: Path,
    synced_versions: dict[str, str],
) -> dict[str, str]:
    """Carry out ``--repin`` and return the ``repin`` members of the parity block.

    Returns an empty mapping when ``--repin`` was not given. The registry is
    written only by ``registry_pin.repin`` in its apply mode, and never under
    ``--dry-run``, without a registry path, or when nothing was synced.
    """
    if not args.repin:
        return {}
    if args.dry_run:
        return {'repin': REPIN_SKIPPED_DRY_RUN}
    if registry_path is None:
        return {'repin': REPIN_SKIPPED_REGISTRY_NOT_READ}
    if not synced_versions:
        return {'repin': REPIN_SKIPPED_NOTHING_SYNCED}

    # One synced version is the normal case and is named as the target, so the
    # pin lands on what this run wrote. Bundles synced at differing versions
    # have no single target; each is then pinned to its newest cache directory.
    versions = set(synced_versions.values())
    outcome = registry_pin.repin(
        registry_path=registry_path,
        cache_root=cache_root,
        target_version=versions.pop() if len(versions) == 1 else None,
        apply=True,
    )
    if outcome['status'] == 'success':
        return {'repin': REPIN_APPLIED}
    return {'repin': REPIN_FAILED, 'repin_message': str(outcome.get('message', 'the repin reported an error'))}


def _registry_parity(
    reader: ModuleType,
    registry_pin: ModuleType,
    *,
    registry_path: Path | None,
    reason: str | None,
    cache_root: Path,
    synced_versions: dict[str, str],
    repin: dict[str, str],
) -> tuple[dict[str, Any], tuple[str, str] | None]:
    """Build the ``registry_parity`` block from the registry as it now reads.

    Returns ``(block, behind_pin)``. ``behind_pin`` is the first
    ``(pinned version, synced version)`` pair that is behind, and is set
    exactly when the verdict is ``behind``.

    Only the entries of a bundle this invocation synced are judged, each
    against that bundle's synced version; the verdicts are combined by the
    repin module's own precedence. An entry of any other bundle is listed
    with ``synced_version: not_synced`` and judged against nothing.
    """
    block: dict[str, Any] = {}
    rows: list[dict[str, str | None]] = []
    if registry_path is None:
        state = REGISTRY_STATE_NOT_READ
    else:
        block['registry_path'] = str(registry_path)
        state, rows = reader.read_registry(registry_path)
    block['registry_state'] = state

    references = {
        str(row['bundle']): synced_versions[str(row['bundle'])] for row in rows if row['bundle'] in synced_versions
    }
    behind_pin: tuple[str, str] | None = None
    if registry_path is None:
        verdict = reader.PARITY_UNREADABLE
    elif not rows:
        verdict = reader.PARITY_UNREADABLE
        reason = f'the plugin registry holds no readable plan-marshall entry (registry_state: {state})'
    elif not references:
        verdict = reader.PARITY_UNREADABLE
        reason = 'no plugin registry entry belongs to a bundle synced in this invocation'
    else:
        verdict = registry_pin.overall_parity(rows, references)
        if verdict == reader.PARITY_BEHIND:
            behind_pin = _first_behind_pin(reader, rows, references)
        elif verdict == reader.PARITY_UNREADABLE:
            reason = 'a pinned field of a judged entry is unknown or cannot be ordered against the synced version'

    if reason is not None:
        block['reason'] = reason
    block.update(repin)
    block['entries'] = [
        {
            'bundle': str(row['bundle']),
            'scope': row['scope'] or UNKNOWN,
            'install_path_version': row['install_path_version'] or UNKNOWN,
            'version': row['version'] or UNKNOWN,
            'synced_version': references.get(str(row['bundle']), NOT_SYNCED),
            'orphan_marked': str(row['bundle']) in references
            and reader.is_orphan_marked(cache_root / str(row['bundle']), references[str(row['bundle'])]),
        }
        for row in rows
    ]
    block['verdict'] = verdict
    return block, behind_pin


def _first_behind_pin(
    reader: ModuleType, rows: list[dict[str, str | None]], references: dict[str, str]
) -> tuple[str, str] | None:
    """The first ``(pinned, synced)`` pair in which the pin is older than the sync."""
    for row in rows:
        reference = references.get(str(row['bundle']))
        if reference is None:
            continue
        for pinned in (row['install_path_version'], row['version']):
            if pinned is not None and reader.version_key(pinned) < reader.version_key(reference):
                return pinned, reference
    return None


def _behind_summary(summary: str, behind_pin: tuple[str, str] | None) -> str:
    """Extend ``summary`` with the versions of a ``behind`` registry and its remedy."""
    versions = f'pinned {behind_pin[0]}, synced {behind_pin[1]}' if behind_pin is not None else 'pinned version older'
    return (
        f'{summary}; the plugin registry is behind the synced version ({versions}), so a restarted '
        f'session still loads the pinned version — run {REPIN_COMMAND}, or re-run the sync with --repin'
    )


def _sync_claude(args: argparse.Namespace) -> tuple[int, dict[str, Any], str]:
    """Run the Claude cache sync, then report registry parity.

    Returns ``(exit_code, result, rendered)``. ``rendered`` is the
    single-target document; ``result`` carries the same fields as data for
    the aggregate document.

    The cache sync runs first and is not influenced by the registry. The
    registry is then repinned when ``--repin`` asks for it, and read LAST,
    so the ``registry_parity`` block states the registry as the run leaves
    it. A staleness-guard refusal synced nothing and carries no block.
    """
    try:
        cache_sync = _load_cache_sync_module()
        reader = _load_module_by_location(
            PLUGIN_REGISTRY_MODULE_NAME, PLUGIN_REGISTRY_RELPATH, 'shared plugin-registry reader'
        )
        registry_pin = _load_module_by_location(
            REGISTRY_PIN_MODULE_NAME, REGISTRY_PIN_RELPATH, 'claude registry repin module'
        )
    except ImportError as exc:
        data: dict[str, Any] = {
            'status': 'error',
            'cache_status': 'error',
            'synced_count': 0,
            'failed_count': 0,
            'summary_message': f'claude sync could not start: {exc}',
        }
        return 1, data, serialize_toon(data) + '\n'

    cache_root = args.cache_root if args.cache_root is not None else cache_sync.DEFAULT_CACHE_ROOT
    result = cache_sync.sync_cache(
        source_root=cache_sync.resolve_source_root(args.source, args.from_worktree),
        marketplace_root=cache_sync.resolve_marketplace_root(args.from_worktree),
        cache_root=cache_root,
        only_bundle=args.bundles,
        skip_staleness_guard=args.skip_staleness_guard,
        dry_run=args.dry_run,
    )

    if result.guard_outcome is None:
        registry_path, reason = _resolve_registry_path(args, registry_pin)
        synced_versions = _synced_versions(cache_sync, result.synced)
        repin = _apply_repin(args, registry_pin, registry_path, cache_root, synced_versions)
        block, behind_pin = _registry_parity(
            reader,
            registry_pin,
            registry_path=registry_path,
            reason=reason,
            cache_root=cache_root,
            synced_versions=synced_versions,
            repin=repin,
        )
        result = result._replace(cache_status=result.status, registry_parity=block)
        if block['verdict'] == reader.PARITY_BEHIND:
            result = result._replace(
                status='partial' if result.status == 'success' else result.status,
                exit_code=EXIT_REGISTRY_BEHIND if result.exit_code == 0 else result.exit_code,
                summary_message=_behind_summary(result.summary_message, behind_pin),
            )

    return result.exit_code, cache_sync.as_dict(result), cache_sync.render(result)


def _sync_one_for_aggregate(target_name: str, args: argparse.Namespace) -> dict[str, Any]:
    """Run one target inside an all-targets run and return its result block.

    A filesystem fault raised while one target deploys is recorded as that
    target's ``error`` result rather than propagated, so the remaining
    targets are still attempted.
    """
    try:
        if target_name == CLAUDE_TARGET:
            _exit_code, data, _rendered = _sync_claude(args)
            return data
        _exit_code, data = _deploy_target(
            target_name, source=None, dest=None, only_bundle=args.bundles, dry_run=args.dry_run
        )
        return data
    except OSError as exc:
        return {
            'status': 'error',
            'summary_message': f'{target_name} sync failed: {type(exc).__name__}: {exc}',
        }


def sync_all(args: argparse.Namespace) -> int:
    """Sync every harness in :data:`SYNC_TARGETS` order and write the aggregate."""
    blocks = {target_name: _sync_one_for_aggregate(target_name, args) for target_name in SYNC_TARGETS}
    succeeded = [name for name, block in blocks.items() if block['status'] == 'success']

    if len(succeeded) == len(blocks):
        status = 'success'
    elif succeeded:
        status = 'partial'
    else:
        status = 'error'

    document: dict[str, Any] = {
        'status': status,
        'targets': [
            {'target': name, 'status': block['status'], 'summary_message': block['summary_message']}
            for name, block in blocks.items()
        ],
        **blocks,
    }
    sys.stdout.write(serialize_toon(document) + '\n')
    return 0 if status == 'success' else 1


#: Flags that configure the Claude cache path only, keyed by namespace
#: attribute. They apply to the Claude leg of an all-targets run and are
#: rejected alongside a non-Claude ``--target``.
_CLAUDE_ONLY_FLAGS: dict[str, str] = {
    'from_worktree': '--from-worktree',
    'cache_root': '--cache-root',
    'skip_staleness_guard': '--skip-staleness-guard',
    'registry_path': '--registry-path',
    'repin': '--repin',
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            'Sync the generated plan-marshall trees into every harness install: the Claude '
            'plugin cache, the OpenCode config directory and the Antigravity plugin directory. '
            'With no --target, all three run in the order claude, opencode, antigravity.'
        ),
        allow_abbrev=False,
    )
    parser.add_argument(
        '--target',
        default=None,
        choices=SYNC_TARGETS,
        help='Sync one harness only (claude, opencode, antigravity). Default: all three.',
    )
    parser.add_argument(
        '--source',
        type=Path,
        default=None,
        metavar='PATH',
        help='Override the source root (default: {cwd}/target/{target}/). Requires --target.',
    )
    parser.add_argument(
        '--target-dir',
        type=Path,
        default=None,
        metavar='PATH',
        help=(
            'Override the destination directory of the opencode or antigravity target. '
            'Requires --target; the claude destination is set with --cache-root.'
        ),
    )
    parser.add_argument(
        '--bundles',
        default=None,
        metavar='NAME',
        help='Restrict every selected target to a single bundle.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Report what would be synced without modifying the filesystem.',
    )
    parser.add_argument(
        '--from-worktree',
        type=Path,
        default=None,
        metavar='PATH',
        help='Claude path: read {PATH}/target/claude/ and compare it against {PATH}/marketplace/bundles/.',
    )
    parser.add_argument(
        '--cache-root',
        type=Path,
        default=None,
        metavar='PATH',
        help='Claude path: override the cache destination root (default: ~/.claude/plugins/cache/plan-marshall).',
    )
    parser.add_argument(
        '--skip-staleness-guard',
        action='store_true',
        help='Claude path: bypass the staleness check (reserved for tests and recovery flows).',
    )
    parser.add_argument(
        '--registry-path',
        type=Path,
        default=None,
        metavar='PATH',
        help=(
            'Claude path: the plugin registry file the registry_parity block reads '
            '(default: ~/.claude/plugins/installed_plugins.json). With --cache-root overridden '
            'and this flag absent, no registry is read and the verdict is unreadable.'
        ),
    )
    parser.add_argument(
        '--repin',
        action='store_true',
        help=(
            'Claude path: after the cache sync, repin the plugin registry to the synced version. '
            'Writes nothing under --dry-run.'
        ),
    )
    return parser


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """Reject flag combinations that would otherwise be silently ignored."""
    if args.target is None:
        for attr, flag in (('source', '--source'), ('target_dir', '--target-dir')):
            if getattr(args, attr) is not None:
                parser.error(f'{flag} is a single-target override and requires --target')
        return

    if args.target == CLAUDE_TARGET:
        if args.target_dir is not None:
            parser.error('--target-dir does not apply to --target claude; use --cache-root')
        return

    for attr, flag in _CLAUDE_ONLY_FLAGS.items():
        if getattr(args, attr):
            parser.error(f'{flag} applies to the claude target only, not to --target {args.target}')


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    _validate_args(parser, args)

    if args.target is None:
        return sync_all(args)

    if args.target == CLAUDE_TARGET:
        exit_code, _data, rendered = _sync_claude(args)
        sys.stdout.write(rendered)
        return exit_code

    return sync_target(
        args.target,
        source=args.source,
        dest=args.target_dir,
        only_bundle=args.bundles,
        dry_run=args.dry_run,
    )


if __name__ == '__main__':
    raise SystemExit(main())

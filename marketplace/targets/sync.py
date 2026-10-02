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
    synced_count: N
    failed_count: M
    summary_message: "<summary>"
    guard_outcome: stale | probe_failed  # only on a guard refusal
    dry_run: true                        # only when --dry-run
    synced[N]{bundle,version,status}:
    failed[M]{bundle,error}:             # only when failed_count > 0

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
``success``, ``partial`` when some did, and ``error`` when none did.

Exit codes:
    All targets:
        0 on aggregate ``status: success``
        1 on aggregate ``status: partial`` or ``status: error``
    ``--target opencode`` / ``--target antigravity``:
        0 on ``status: success``
        1 on ``status: error`` (source missing, empty source, etc.)
    ``--target claude``:
        0 on ``status: success`` or ``status: partial``
        1 on ``status: error`` (nothing synced)
        2 on a staleness-guard refusal
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

    The loaded module is cached in ``sys.modules`` under
    :data:`CACHE_SYNC_MODULE_NAME`.

    Raises:
        ImportError: the module file is absent, has no loadable spec, or
            fails while executing.
    """
    cached = sys.modules.get(CACHE_SYNC_MODULE_NAME)
    if cached is not None:
        return cached

    module_path = _PROJECT_ROOT / CACHE_SYNC_RELPATH
    if not module_path.is_file():
        raise ImportError(f'claude cache-sync module not found at {module_path}')

    spec = importlib.util.spec_from_file_location(CACHE_SYNC_MODULE_NAME, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f'no loadable module spec for claude cache-sync module at {module_path}')

    module = importlib.util.module_from_spec(spec)
    sys.modules[CACHE_SYNC_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # normalised to ImportError below
        sys.modules.pop(CACHE_SYNC_MODULE_NAME, None)
        raise ImportError(f'claude cache-sync module at {module_path} failed to import: {exc}') from exc
    return module


def _sync_claude(args: argparse.Namespace) -> tuple[int, dict[str, Any], str]:
    """Run the Claude cache sync. Returns ``(exit_code, result, rendered)``.

    ``rendered`` is the single-target document; ``result`` carries the
    same fields as data for the aggregate document.
    """
    try:
        cache_sync = _load_cache_sync_module()
    except ImportError as exc:
        data: dict[str, Any] = {
            'status': 'error',
            'synced_count': 0,
            'failed_count': 0,
            'summary_message': f'claude sync could not start: {exc}',
        }
        return 1, data, serialize_toon(data) + '\n'

    result = cache_sync.sync_cache(
        source_root=cache_sync.resolve_source_root(args.source, args.from_worktree),
        marketplace_root=cache_sync.resolve_marketplace_root(args.from_worktree),
        cache_root=args.cache_root if args.cache_root is not None else cache_sync.DEFAULT_CACHE_ROOT,
        only_bundle=args.bundles,
        skip_staleness_guard=args.skip_staleness_guard,
        dry_run=args.dry_run,
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


def sync_all(args: argparse.Namespace, *, stdout: TextIO | None = None) -> int:
    """Sync every harness in :data:`SYNC_TARGETS` order and write the aggregate."""
    out = stdout if stdout is not None else sys.stdout

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
    out.write(serialize_toon(document) + '\n')
    return 0 if status == 'success' else 1


#: Flags that configure the Claude cache path only, keyed by namespace
#: attribute. They apply to the Claude leg of an all-targets run and are
#: rejected alongside a non-Claude ``--target``.
_CLAUDE_ONLY_FLAGS: dict[str, str] = {
    'from_worktree': '--from-worktree',
    'cache_root': '--cache-root',
    'skip_staleness_guard': '--skip-staleness-guard',
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

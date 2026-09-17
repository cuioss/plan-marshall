#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unified deploy engine for plan-marshall distribution targets.

Pipeline:
    marketplace/bundles/  →  target/{target}/  →  platform configuration directory

Consolidates the target deployment logic for all supported targets
(currently ``antigravity`` and ``opencode``) into a single, declarative
engine alongside ``marketplace/targets/generate.py``.

Target profiles:
* **antigravity**: Source layout is plural (``skills/``, ``agents/``,
  ``commands/``). Destination is ``~/.gemini/config/plugins/plan-marshall/``.
  Deploys root assets ``plugin.json``, ``install.sh`` (chmod 0o755), and ``README.adoc``.
* **opencode**: Source layout is singular (``skill/``, ``agent/``, ``command/``).
  Destination is ``~/.config/opencode/`` with plural layout (``skills/``,
  ``agents/``, ``commands/``). Deploys ``opencode.json``.

Outputs a compact TOON document via ``toon_parser.serialize_toon``:
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

Exit codes:
    0 on status: success
    1 on status: error (source missing, empty source, invalid target, etc.)
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TOON_DIR = _PROJECT_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'ref-toon-format' / 'scripts'
if _TOON_DIR.is_dir() and str(_TOON_DIR) not in sys.path:
    sys.path.insert(0, str(_TOON_DIR))

from toon_parser import serialize_toon  # noqa: E402

VERBATIM_SKILL_SUBDIRS: tuple[str, ...] = ('standards', 'references', 'templates', 'scripts')


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
        root_assets=(
            ('opencode.json', 'config', False),
        ),
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
    if only_bundle:
        return {only_bundle}
    bundles: set[str] = set()
    for s in skills:
        parts = s.name.split('-', 1)
        if len(parts) == 2 and parts[0]:
            bundles.add(parts[0])
        elif s.name:
            bundles.add(s.name)
    for c in commands:
        stem = c.stem
        parts = stem.split('-', 1)
        if len(parts) == 2 and parts[0]:
            bundles.add(parts[0])
        elif stem:
            bundles.add(stem)
    return bundles


def _is_managed_skill(dir_name: str, synced_bundles: set[str]) -> bool:
    matching = [b for b in synced_bundles if dir_name == b or dir_name.startswith(f'{b}-')]
    return bool(matching)


def _is_managed_command(file_name: str, synced_bundles: set[str]) -> bool:
    if not file_name.endswith('.md'):
        return False
    stem = file_name[:-3]
    matching = [b for b in synced_bundles if stem == b or stem.startswith(f'{b}-')]
    return bool(matching)


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


def _emit_toon(
    *,
    status: str,
    target: str,
    source: Path,
    dest: Path,
    skills_count: int,
    agents_count: int,
    commands_count: int,
    extra_count_key: str,
    extra_count: int,
    deployed_count: int,
    removed: list[dict[str, str]],
    summary_message: str,
    dry_run: bool = False,
) -> str:
    data: dict[str, Any] = {
        'status': status,
        'target': target,
        'source': str(source),
        'destination': str(dest),
        'skills_count': skills_count,
        'agents_count': agents_count,
        'commands_count': commands_count,
        extra_count_key: extra_count,
        'deployed_count': deployed_count,
        'removed_count': len(removed),
        'summary_message': summary_message,
    }
    if dry_run:
        data['dry_run'] = True
    if removed:
        data['removed'] = removed
    return serialize_toon(data)


def _emit_error_toon(
    *,
    target: str,
    summary_message: str,
    source: Path | None = None,
    dest: Path | None = None,
    dry_run: bool = False,
) -> str:
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
    return serialize_toon(data)


def sync_target(
    target_name: str,
    *,
    source: Path | None = None,
    dest: Path | None = None,
    only_bundle: str | None = None,
    dry_run: bool = False,
    stdout: TextIO | None = None,
) -> int:
    out = stdout if stdout is not None else sys.stdout

    if target_name not in TARGET_CONFIGS:
        msg = f'unknown target: {target_name} (valid: {", ".join(sorted(TARGET_CONFIGS.keys()))})'
        out.write(_emit_error_toon(target=target_name, summary_message=msg, dry_run=dry_run))
        return 1

    config = TARGET_CONFIGS[target_name]
    src = _resolve_source(config, source)
    dst = _resolve_dest(config, dest)

    if not src.is_dir():
        msg = f'source not found: {src}'
        out.write(_emit_error_toon(target=target_name, summary_message=msg, source=src, dest=dst, dry_run=dry_run))
        return 1

    skills = _enumerate_source_skills(src, config, only_bundle)
    agents = _enumerate_source_agents(src, config)
    commands = _enumerate_source_commands(src, config, only_bundle)

    has_root_assets = any((src / asset_file).is_file() for asset_file, _kind, _exec in config.root_assets)

    if not skills and not agents and not commands and not has_root_assets:
        msg = f'source contains no emit output: {src}'
        out.write(_emit_error_toon(target=target_name, summary_message=msg, source=src, dest=dst, dry_run=dry_run))
        return 1

    synced_bundles = _derive_synced_bundles(skills, commands, only_bundle)

    source_skill_names = {s.name for s in skills}
    source_command_names = {c.name for c in commands}

    removed = _prune_managed(
        dst,
        source_skill_names,
        source_command_names,
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

    skills_count = len(skills)
    agents_count = len(agents)
    commands_count = len(commands)
    deployed_count = skills_count + agents_count + commands_count + extra_count

    msg = f'deployed {deployed_count} components, removed {len(removed)} stale entries to {dst}'

    out.write(
        _emit_toon(
            status='success',
            target=target_name,
            source=src,
            dest=dst,
            skills_count=skills_count,
            agents_count=agents_count,
            commands_count=commands_count,
            extra_count_key=config.extra_count_key,
            extra_count=extra_count,
            deployed_count=deployed_count,
            removed=removed,
            summary_message=msg,
            dry_run=dry_run,
        )
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Deploy a generated target tree into the platform configuration directory.',
        allow_abbrev=False,
    )
    parser.add_argument(
        '--target',
        required=True,
        choices=sorted(TARGET_CONFIGS.keys()),
        help='Target platform to sync (antigravity, opencode)',
    )
    parser.add_argument(
        '--source',
        type=Path,
        default=None,
        help='Override the source root (default: {cwd}/target/{target}/)',
    )
    parser.add_argument(
        '--target-dir',
        type=Path,
        default=None,
        help='Override the destination directory',
    )
    parser.add_argument(
        '--bundles',
        default=None,
        help='Restrict the sync to a single bundle',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print actions without modifying the filesystem',
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    return sync_target(
        args.target,
        source=args.source,
        dest=args.target_dir,
        only_bundle=args.bundles,
        dry_run=args.dry_run,
    )


if __name__ == '__main__':
    raise SystemExit(main())

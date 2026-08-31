#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deploy engine for the project-local ``sync-opencode`` skill.

Pipeline:

    marketplace/bundles/  →  target/opencode/  →  ~/.config/opencode/{skills,agents,commands}/

The script consumes the multi-target generator output at
``target/opencode/`` (or a supplied ``--source`` path) and copies each
emitted component into the OpenCode config directory with the
singular→plural directory rename that OpenCode expects.

Singular → plural mapping:

    skill/{bundle}-{skill}/  →  {dest}/skills/{bundle}-{skill}/
    agent/{name}.md          →  {dest}/agents/{name}.md
    command/{bundle}-{skill}.md  →  {dest}/commands/{bundle}-{skill}.md

Deletion boundary
-----------------

The destination (default ``~/.config/opencode/``) is a shared directory
where user-managed skills also live. The script removes only **managed
entries** — those whose names match the ``{bundle}-{skill}`` namespace
of the bundles being synced:

* **Managed (may be pruned):** ``skills/{bundle}-{skill}/`` and
  ``commands/{bundle}-{skill}.md`` where ``{bundle}`` is one of the
  bundles being synced.
* **Never pruned:** ``agents/`` (flat namespace, no bundle attribution),
  entries whose names do not match any synced bundle, entries under
  ``skills/`` or ``commands/`` whose names do not match any synced bundle.

With ``--bundles NAME``, unselected bundles' entries are preserved — only
the named bundle's managed entries are eligible for pruning.

Outputs a TOON document on stdout:

    status: success | partial | error
    deployed_count: N
    removed_count: M
    summary_message: "<human-readable summary>"
    dry_run: true                           # only when --dry-run
    deployed[N]{kind,name}:
      skills/plan-marshall-sync-opencode
      commands/plan-marshall-sync-opencode.md
    removed[N]{kind,name}:
      skills/plan-marshall-old-skill

Exit codes:

    0 on ``status: success`` or ``status: partial``.
    1 on ``status: error`` (source missing, source empty, etc.).

Flags:

    --source PATH       Override the source root (default: {cwd}/target/opencode/).
    --target-dir PATH   Override the destination (default: ~/.config/opencode/).
    --bundles NAME      Restrict the deploy to a single bundle.
    --dry-run           Print actions without touching the filesystem.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# Verbatim sub-directories copied alongside SKILL.md inside each skill dir.
VERBATIM_SKILL_SUBDIRS = ('standards', 'references', 'templates', 'scripts')


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Deploy the generated OpenCode tree with the singular→plural rename.',
        allow_abbrev=False,
    )
    parser.add_argument('--source', type=Path, default=None, metavar='PATH',
                        help='Source root (default: {cwd}/target/opencode/).')
    parser.add_argument('--target-dir', type=Path, default=None, metavar='PATH',
                        help='Destination directory (default: ~/.config/opencode/).')
    parser.add_argument('--bundles', type=str, default=None, metavar='NAME',
                        help='Restrict the deploy to a single bundle.')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print actions without touching the filesystem.')
    return parser


def _resolve_source(args: argparse.Namespace) -> Path:
    source: Path | None = args.source
    if source is not None:
        return source
    return Path.cwd() / 'target' / 'opencode'


def _resolve_dest(args: argparse.Namespace) -> Path:
    target_dir: Path | None = args.target_dir
    if target_dir is not None:
        return target_dir
    return Path.home() / '.config' / 'opencode'


def _is_managed_skill(name: str, synced_bundles: set[str]) -> bool:
    """Return True if a ``skills/`` entry name belongs to a synced bundle.

    An entry is managed when its name starts with ``{bundle}-`` for some
    synced bundle. Prefix matching (not first-hyphen token matching)
    handles bundle names that themselves contain hyphens (e.g.
    ``plan-marshall`` → ``plan-marshall-sync-opencode``).
    """
    for bundle in synced_bundles:
        if name.startswith(f'{bundle}-'):
            return True
    return False


def _is_managed_command(name: str, synced_bundles: set[str]) -> bool:
    """Return True if a ``commands/`` entry name belongs to a synced bundle.

    Command wrapper filenames are ``{bundle}-{skill}.md``, so strip the
    ``.md`` suffix before comparing.
    """
    stem = name.removesuffix('.md')
    if stem == name:
        return False
    return _is_managed_skill(stem, synced_bundles)


def _enumerate_source_skills(source: Path, only_bundle: str | None) -> list[Path]:
    """Return sorted skill directories under ``source/skill/``."""
    skill_dir = source / 'skill'
    if not skill_dir.is_dir():
        return []
    skills = sorted(
        p for p in skill_dir.iterdir()
        if p.is_dir() and (p / 'SKILL.md').exists()
    )
    if only_bundle is not None:
        skills = [s for s in skills if s.name.startswith(f'{only_bundle}-')]
    return skills


def _enumerate_source_agents(source: Path) -> list[Path]:
    """Return sorted agent files under ``source/agent/``."""
    agent_dir = source / 'agent'
    if not agent_dir.is_dir():
        return []
    return sorted(
        p for p in agent_dir.iterdir()
        if p.is_file() and p.suffix == '.md'
    )


def _enumerate_source_commands(source: Path, only_bundle: str | None) -> list[Path]:
    """Return sorted command files under ``source/command/``."""
    command_dir = source / 'command'
    if not command_dir.is_dir():
        return []
    commands = sorted(
        p for p in command_dir.iterdir()
        if p.is_file() and p.suffix == '.md'
    )
    if only_bundle is not None:
        commands = [c for c in commands if c.name.startswith(f'{only_bundle}-')]
    return commands


def _derive_synced_bundles(skills: list[Path], commands: list[Path], only_bundle: str | None) -> set[str]:
    """Derive the set of bundle names from skill and command entry names.

    Each skill directory is named ``{bundle}-{skill}`` and each command
    wrapper file ``{bundle}-{skill}.md``. Deriving from BOTH keeps the
    managed set populated when a run's source carries commands but no
    skills (for example after every skill was removed). The bundle token
    is the first hyphen-delimited segment of each name. With
    ``--bundles NAME``, the set is just ``{NAME}``.
    """
    if only_bundle is not None:
        return {only_bundle}
    bundles: set[str] = set()
    for path in list(skills) + list(commands):
        name = path.name.removesuffix('.md')
        if '-' in name:
            bundles.add(name.split('-', 1)[0])
    return bundles


def _deploy_skill(skill_dir: Path, dest: Path, *, dry_run: bool) -> list[dict[str, str]]:
    """Copy a skill directory to ``dest/skills/{name}/`` with verbatim sub-dirs.

    Returns a list of ``{kind, name}`` dicts for each deployed entry.
    """
    entries: list[dict[str, str]] = []
    target = dest / 'skills' / skill_dir.name
    if not dry_run:
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)

    # Copy SKILL.md
    skill_md = skill_dir / 'SKILL.md'
    if skill_md.is_file():
        if not dry_run:
            shutil.copy2(skill_md, target / 'SKILL.md')
        entries.append({'kind': 'skills', 'name': skill_dir.name})

    # Copy verbatim sub-directories
    for subdir_name in VERBATIM_SKILL_SUBDIRS:
        src_sub = skill_dir / subdir_name
        if src_sub.exists() and src_sub.is_dir():
            dst_sub = target / subdir_name
            if not dry_run:
                if dst_sub.exists():
                    shutil.rmtree(dst_sub)
                shutil.copytree(src_sub, dst_sub)
            entries.append({'kind': 'skills', 'name': f'{skill_dir.name}/{subdir_name}'})

    return entries


def _deploy_agent(agent_file: Path, dest: Path, *, dry_run: bool) -> dict[str, str]:
    """Copy an agent file to ``dest/agents/{name}.md``."""
    target = dest / 'agents' / agent_file.name
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(agent_file, target)
    return {'kind': 'agents', 'name': agent_file.name}


def _deploy_command(command_file: Path, dest: Path, *, dry_run: bool) -> dict[str, str]:
    """Copy a command file to ``dest/commands/{name}.md``."""
    target = dest / 'commands' / command_file.name
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(command_file, target)
    return {'kind': 'commands', 'name': command_file.name}


def _prune_managed(
    dest: Path,
    source_skills: set[str],
    source_commands: set[str],
    synced_bundles: set[str],
    *,
    dry_run: bool,
) -> list[dict[str, str]]:
    """Remove stale managed entries from the destination.

    An entry is stale when it belongs to a synced bundle (by name) but
    does not exist in the source. Agents are never pruned.

    Returns a list of ``{kind, name}`` dicts for each removed entry.
    """
    removed: list[dict[str, str]] = []

    # Prune stale skills
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

    # Prune stale commands
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


def _emit_toon(
    *,
    status: str,
    deployed: list[dict[str, str]],
    removed: list[dict[str, str]],
    summary_message: str,
    dry_run: bool = False,
) -> str:
    deployed_count = len(deployed)
    lines = [
        f'status: {status}',
        f'deployed_count: {deployed_count}',
        f'removed_count: {len(removed)}',
        f'summary_message: "{summary_message}"',
    ]
    if dry_run:
        lines.append('dry_run: true')
    lines.append(f'deployed[{len(deployed)}]{{kind,name}}:')
    for row in deployed:
        name = row['name'].replace('"', '\\"')
        lines.append(f'  {row["kind"]},{name}')
    lines.append(f'removed[{len(removed)}]{{kind,name}}:')
    for row in removed:
        name = row['name'].replace('"', '\\"')
        lines.append(f'  {row["kind"]},{name}')
    return '\n'.join(lines) + '\n'


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv if argv is not None else sys.argv[1:])

    source = _resolve_source(args)
    dest = _resolve_dest(args)
    only_bundle = args.bundles
    dry_run = args.dry_run

    if not source.is_dir():
        msg = f'source not found: {source}'
        sys.stdout.write(_emit_toon(status='error', deployed=[], removed=[], summary_message=msg, dry_run=dry_run))
        return 1

    skills = _enumerate_source_skills(source, only_bundle)
    agents = _enumerate_source_agents(source)
    commands = _enumerate_source_commands(source, only_bundle)

    if not skills and not agents and not commands:
        msg = f'source contains no emit output: {source}'
        sys.stdout.write(_emit_toon(status='error', deployed=[], removed=[], summary_message=msg, dry_run=dry_run))
        return 1

    synced_bundles = _derive_synced_bundles(skills, commands, only_bundle)

    # Compute the set of source skill/command names for staleness comparison.
    source_skill_names = {s.name for s in skills}
    source_command_names = {c.name for c in commands}

    # Prune stale managed entries BEFORE deploying.
    removed = _prune_managed(
        dest, source_skill_names, source_command_names, synced_bundles, dry_run=dry_run,
    )

    # Deploy
    deployed: list[dict[str, str]] = []

    for skill_dir in skills:
        entries = _deploy_skill(skill_dir, dest, dry_run=dry_run)
        deployed.extend(entries)

    for agent_file in agents:
        entry = _deploy_agent(agent_file, dest, dry_run=dry_run)
        deployed.append(entry)

    for command_file in commands:
        entry = _deploy_command(command_file, dest, dry_run=dry_run)
        deployed.append(entry)

    # Deploy opencode.json if present
    opencode_json = source / 'opencode.json'
    if opencode_json.is_file():
        target = dest / 'opencode.json'
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(opencode_json, target)
        deployed.append({'kind': 'config', 'name': 'opencode.json'})

    status = 'success'
    message = f'deployed {len(deployed)} entries, removed {len(removed)} stale entries to {dest}'
    exit_code = 0

    sys.stdout.write(
        _emit_toon(status=status, deployed=deployed, removed=removed, summary_message=message, dry_run=dry_run)
    )
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())

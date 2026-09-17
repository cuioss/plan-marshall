# SPDX-License-Identifier: FSL-1.1-ALv2
"""Antigravity emitter — walks source bundles and writes target output.

Layout written under ``output_dir``::

    output_dir/
    ├── skills/{bundle}-{skill}/SKILL.md  (+ standards/ references/ templates/ scripts/ verbatim)
    ├── agents/{agent}.md
    ├── commands/{command}.md
    └── plugin.json

Body text is emitted verbatim — body-text rewrites are owned by the
target-shared ``body_transform_engine``.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

from marketplace.targets.antigravity.frontmatter import (
    load_mapping,
    load_rules,
    parse_frontmatter,
    transform_agent_frontmatter,
    transform_command_frontmatter,
    transform_skill_frontmatter,
)
from marketplace.targets.antigravity.variant_emitter import emit_agent_variants
from marketplace.targets.component_targets import (
    EXCLUDED_DIR_NAMES,
    excluded_emission_roots,
    is_under_any,
)
from marketplace.targets.fs_safety import refuse_tree_overlap, safe_rmtree

# Path to templates used by emitter.
_TEMPLATES_DIR = Path(__file__).resolve().parent / 'templates'
_USER_INVOCABLE_TEMPLATE = _TEMPLATES_DIR / 'user-invocable-command.md'
_INSTALL_SCRIPT_TEMPLATE = _TEMPLATES_DIR / 'install.sh'

ANTIGRAVITY_TARGET_NAME = 'antigravity'

VERBATIM_SKILL_SUBDIRS = ('standards', 'references', 'templates', 'scripts')

BodyTransformer = Callable[[str, str, str], str]


def _identity_body(body: str, _bundle: str, _kind: str) -> str:
    return body


def iter_bundle_dirs(marketplace_dir: Path, bundles: list[str] | None) -> Iterator[Path]:
    """Yield bundle directories under ``marketplace_dir``."""
    if not marketplace_dir.exists():
        return
    resolved_marketplace = marketplace_dir.resolve()

    candidates: list[Path] = []
    if bundles is None:
        candidates = sorted(p for p in marketplace_dir.iterdir() if p.is_dir() and not p.name.startswith('.'))
    else:
        for name in bundles:
            if not name or '..' in name or '/' in name or '\\' in name:
                continue
            candidate = marketplace_dir / name
            if candidate.resolve().parent != resolved_marketplace:
                continue
            if candidate.is_dir():
                candidates.append(candidate)

    for candidate in candidates:
        if (candidate / '.claude-plugin' / 'plugin.json').exists():
            yield candidate


def _bundle_relative_ref(ref: str) -> str | None:
    rel = ref.removeprefix('./')
    if '..' in rel.split('/'):
        return None
    return rel


def _read_plugin_json(bundle_dir: Path) -> dict:
    plugin_json = bundle_dir / '.claude-plugin' / 'plugin.json'
    if not plugin_json.exists():
        return {}
    try:
        parsed: dict = json.loads(plugin_json.read_text(encoding='utf-8'))
        return parsed
    except (OSError, json.JSONDecodeError):
        return {}


def _copy_verbatim(
    src: Path,
    dst: Path,
    *,
    output_dir: Path,
    bundle_dir: Path,
    excluded: frozenset[Path],
    written: list[Path],
) -> None:
    """Copy ``src`` (a skill sub-directory) into ``dst``, file by file."""
    if dst.exists():
        safe_rmtree(dst, output_dir)
    dst.mkdir(parents=True, exist_ok=False)
    for source in src.rglob('*'):
        if not source.is_file():
            continue
        rel = source.relative_to(src)
        if any(part in EXCLUDED_DIR_NAMES for part in rel.parts):
            continue
        if is_under_any(source.relative_to(bundle_dir), excluded):
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        written.append(target)


def _prune_stale_outputs(output_dir: Path, written: list[Path]) -> None:
    """Remove ``skills/``, ``agents/``, ``commands/`` outputs left over from a prior emit."""
    written_set = {p.resolve() for p in written}

    for subdir in ('skills', 'agents', 'commands'):
        root = output_dir / subdir
        if not root.is_dir():
            continue
        for path in sorted(root.rglob('*')):
            if path.is_file() and path.resolve() not in written_set:
                path.unlink()
        for directory in sorted(
            (p for p in root.rglob('*') if p.is_dir()),
            key=lambda p: len(p.parts),
            reverse=True,
        ):
            if not any(directory.iterdir()):
                directory.rmdir()


def _is_user_invocable(fm: dict[str, str]) -> bool:
    raw = fm.get('user-invocable', '').strip().lower()
    return raw in {'true', 'yes', '1'}


def _render_user_invocable_template(description: str, skill_id: str) -> str:
    if not _USER_INVOCABLE_TEMPLATE.is_file():
        raise FileNotFoundError(f'Antigravity user-invocable template not found: {_USER_INVOCABLE_TEMPLATE}')
    text = _USER_INVOCABLE_TEMPLATE.read_text(encoding='utf-8')
    text = text.replace('{{description}}', description)
    text = text.replace('{{skill_id}}', skill_id)
    return text


def _emit_user_invocable_wrapper(
    *,
    bundle_name: str,
    skill_name: str,
    fm: dict[str, str],
    output_dir: Path,
    written: list[Path],
) -> None:
    description = fm.get('description', '').splitlines()[0].strip() if fm.get('description') else ''
    skill_id = f'{bundle_name}-{skill_name}'

    rendered = _render_user_invocable_template(description, skill_id)

    command_dir = output_dir / 'commands'
    command_dir.mkdir(parents=True, exist_ok=True)
    target = command_dir / f'{skill_id}.md'
    target.write_text(rendered, encoding='utf-8')
    written.append(target)


def _emit_skill(
    bundle_name: str,
    skill_dir: Path,
    output_dir: Path,
    bundle_dir: Path,
    excluded: frozenset[Path],
    rules: dict[str, list[str]],
    body_transformer: BodyTransformer,
    written: list[Path],
) -> None:
    skill_md = skill_dir / 'SKILL.md'
    if not skill_md.exists():
        return
    skill_name = skill_dir.name
    content = skill_md.read_text(encoding='utf-8')
    fm, body = parse_frontmatter(content)
    source_label = f'skills/{bundle_name}/{skill_name}/SKILL.md'

    new_fm = transform_skill_frontmatter(fm, bundle_name, skill_name, rules, source_label=source_label)
    new_body = body_transformer(body, bundle_name, 'skill')

    target_skill_dir = output_dir / 'skills' / f'{bundle_name}-{skill_name}'
    target_skill_dir.mkdir(parents=True, exist_ok=True)
    target_skill_md = target_skill_dir / 'SKILL.md'
    target_skill_md.write_text(new_fm + '\n\n' + new_body, encoding='utf-8')
    written.append(target_skill_md)

    for subdir_name in VERBATIM_SKILL_SUBDIRS:
        src_subdir = skill_dir / subdir_name
        if src_subdir.exists() and src_subdir.is_dir():
            dst_subdir = target_skill_dir / subdir_name
            _copy_verbatim(
                src_subdir,
                dst_subdir,
                output_dir=output_dir,
                bundle_dir=bundle_dir,
                excluded=excluded,
                written=written,
            )

    if _is_user_invocable(fm):
        _emit_user_invocable_wrapper(
            bundle_name=bundle_name,
            skill_name=skill_name,
            fm=fm,
            output_dir=output_dir,
            written=written,
        )


def _emit_agent(
    bundle_name: str,
    agent_md: Path,
    output_dir: Path,
    mapping: dict[str, dict],
    rules: dict[str, list[str]],
    body_transformer: BodyTransformer,
    written: list[Path],
    level_pins: dict[str, str] | None = None,
) -> None:
    if not agent_md.exists():
        return
    content = agent_md.read_text(encoding='utf-8')
    fm, body = parse_frontmatter(content)
    source_label = f'agents/{bundle_name}/{agent_md.name}'

    new_fm = transform_agent_frontmatter(fm, mapping, rules, source_label=source_label)
    new_body = body_transformer(body, bundle_name, 'agent')

    agent_dir = output_dir / 'agents'
    agent_dir.mkdir(parents=True, exist_ok=True)
    target_agent = agent_dir / agent_md.name
    target_agent.write_text(new_fm + '\n\n' + new_body, encoding='utf-8')
    written.append(target_agent)

    agent_id = agent_md.stem
    result = emit_agent_variants(
        fm,
        new_body,
        agent_id,
        agent_dir,
        mapping,
        rules,
        source_label=source_label,
        level_pins=level_pins,
    )
    if result is not None:
        for level in result.variants_emitted:
            variant_path = agent_dir / f'{agent_id}-{level}.md'
            written.append(variant_path)


def _emit_command(
    bundle_name: str,
    command_md: Path,
    output_dir: Path,
    rules: dict[str, list[str]],
    body_transformer: BodyTransformer,
    written: list[Path],
) -> None:
    if not command_md.exists():
        return
    content = command_md.read_text(encoding='utf-8')
    fm, body = parse_frontmatter(content)
    source_label = f'commands/{bundle_name}/{command_md.name}'

    new_fm = transform_command_frontmatter(fm, rules, source_label=source_label)
    new_body = body_transformer(body, bundle_name, 'command')

    command_dir = output_dir / 'commands'
    command_dir.mkdir(parents=True, exist_ok=True)
    target_command = command_dir / command_md.name
    target_command.write_text(new_fm + '\n\n' + new_body, encoding='utf-8')
    written.append(target_command)


def _resolve_skill_dirs(bundle_dir: Path, plugin_config: dict) -> list[Path]:
    refs = plugin_config.get('skills', [])
    skills: list[Path] = []
    if refs:
        for ref in refs:
            ref_str = _bundle_relative_ref(str(ref))
            if ref_str is None:
                continue
            candidate = bundle_dir / ref_str
            if candidate.is_dir():
                skills.append(candidate)
        return skills
    skills_dir = bundle_dir / 'skills'
    if skills_dir.exists():
        skills = [d for d in sorted(skills_dir.iterdir()) if d.is_dir() and (d / 'SKILL.md').exists()]
    return skills


def _resolve_md_components(bundle_dir: Path, plugin_config: dict, key: str, fallback_subdir: str) -> list[Path]:
    refs = plugin_config.get(key, [])
    paths: list[Path] = []
    if refs:
        for ref in refs:
            ref_str = _bundle_relative_ref(str(ref))
            if ref_str is None:
                continue
            candidate = bundle_dir / ref_str
            if candidate.is_file():
                paths.append(candidate)
        return paths
    fallback = bundle_dir / fallback_subdir
    if fallback.exists():
        paths = sorted(
            p for p in fallback.iterdir() if p.is_file() and p.suffix == '.md' and not p.name.startswith('.')
        )
    return paths


def _generate_plugin_json(
    output_dir: Path,
    bundle_names: list[str],
) -> Path:
    """Write Antigravity ``plugin.json`` manifest."""
    config: dict = {
        'name': 'plan-marshall',
        'description': 'Comprehensive marketplace of development standards, skills, and best practices for AI-assisted development',
        'version': '0.1.0',
        'bundles': sorted(bundle_names),
    }
    config_path = output_dir / 'plugin.json'
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    return config_path


def emit_bundles(
    marketplace_dir: Path,
    output_dir: Path,
    config_dir: Path,
    *,
    bundles: Iterable[str] | None = None,
    body_transformer: BodyTransformer | None = None,
    target_name: str = ANTIGRAVITY_TARGET_NAME,
    level_pins: dict[str, str] | None = None,
) -> list[Path]:
    """Walk source bundles and emit Antigravity output."""
    refuse_tree_overlap(output_dir, marketplace_dir)

    mapping = load_mapping(config_dir)
    rules = load_rules(config_dir)
    transform_body = body_transformer or _identity_body

    bundle_list = list(bundles) if bundles is not None else None
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    emitted_bundles: list[str] = []

    for bundle_dir in iter_bundle_dirs(marketplace_dir, bundle_list):
        bundle_name = bundle_dir.name
        excluded = excluded_emission_roots(bundle_dir, target_name)
        plugin_config = _read_plugin_json(bundle_dir)

        for skill_dir in _resolve_skill_dirs(bundle_dir, plugin_config):
            if is_under_any(skill_dir.relative_to(bundle_dir), excluded):
                continue
            _emit_skill(
                bundle_name=bundle_name,
                skill_dir=skill_dir,
                output_dir=output_dir,
                bundle_dir=bundle_dir,
                excluded=excluded,
                rules=rules,
                body_transformer=transform_body,
                written=written,
            )

        for agent_md in _resolve_md_components(bundle_dir, plugin_config, 'agents', 'agents'):
            if is_under_any(agent_md.relative_to(bundle_dir), excluded):
                continue
            _emit_agent(
                bundle_name=bundle_name,
                agent_md=agent_md,
                output_dir=output_dir,
                mapping=mapping,
                rules=rules,
                body_transformer=transform_body,
                written=written,
                level_pins=level_pins,
            )

        for command_md in _resolve_md_components(bundle_dir, plugin_config, 'commands', 'commands'):
            if is_under_any(command_md.relative_to(bundle_dir), excluded):
                continue
            _emit_command(
                bundle_name=bundle_name,
                command_md=command_md,
                output_dir=output_dir,
                rules=rules,
                body_transformer=transform_body,
                written=written,
            )

        emitted_bundles.append(bundle_name)

    manifest_path = _generate_plugin_json(output_dir, emitted_bundles)
    written.append(manifest_path)

    # Emit root installer script from template
    if _INSTALL_SCRIPT_TEMPLATE.is_file():
        install_target = output_dir / 'install.sh'
        shutil.copyfile(_INSTALL_SCRIPT_TEMPLATE, install_target)
        install_target.chmod(0o755)
        written.append(install_target)

    # Emit root README.adoc copied from doc/user/install-antigravity.adoc
    # so GitHub renders user installation guide on the dist-antigravity branch.
    repo_root = marketplace_dir.parent.parent
    doc_src = repo_root / 'doc' / 'user' / 'install-antigravity.adoc'
    if not doc_src.is_file():
        fallback_src = Path(__file__).resolve().parents[3] / 'doc' / 'user' / 'install-antigravity.adoc'
        if fallback_src.is_file():
            doc_src = fallback_src
    if doc_src.is_file():
        readme_target = output_dir / 'README.adoc'
        shutil.copyfile(doc_src, readme_target)
        written.append(readme_target)

    if bundle_list is None:
        _prune_stale_outputs(output_dir, written)

    return written


__all__ = [
    'ANTIGRAVITY_TARGET_NAME',
    'VERBATIM_SKILL_SUBDIRS',
    'emit_bundles',
    'iter_bundle_dirs',
]

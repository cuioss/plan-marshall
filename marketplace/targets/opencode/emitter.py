# SPDX-License-Identifier: FSL-1.1-ALv2
"""OpenCode emitter — walks source bundles and writes singular-layout output.

Layout written under ``output_dir``::

    output_dir/
    ├── skill/{bundle}-{skill}/SKILL.md  (+ standards/ references/ templates/ scripts/ verbatim)
    ├── agent/{agent}.md
    ├── command/{command}.md
    └── opencode.json

Body text is emitted verbatim — body-text rewrites are owned by
``body-transforms.py`` (deliverable 4). The emitter wires through any
caller-supplied ``body_transformer`` so deliverable 4 can plug in
without editing this module.

Validation contract (silent exclusion is prohibited):
  * Missing required frontmatter field → ``UnmappedFrontmatterError``
    propagates to the CLI (exit code 2).
  * Unknown agent tool → ``UnmappedToolError`` propagates to the CLI
    (exit code 2).
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

from marketplace.targets.opencode.frontmatter import (
    OPENCODE_MODEL_PREFIX,
    UnmappedFrontmatterError,
    UnmappedToolError,
    load_mapping,
    load_rules,
    parse_frontmatter,
    transform_agent_frontmatter,
    transform_command_frontmatter,
    transform_skill_frontmatter,
)
from marketplace.targets.opencode.variant_emitter import emit_agent_variants

# Path to the wrapper template used by user-invocable dual-emit.
_TEMPLATES_DIR = Path(__file__).resolve().parent / 'templates'
_USER_INVOCABLE_TEMPLATE = _TEMPLATES_DIR / 'user-invocable-command.md'

EXCLUDED_DIR_NAMES = frozenset({'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache'})

# Sub-directories that are copied verbatim alongside SKILL.md so the
# generated skill remains self-contained at runtime.
VERBATIM_SKILL_SUBDIRS = ('standards', 'references', 'templates', 'scripts')

BodyTransformer = Callable[[str, str, str], str]
"""Signature: (body, bundle, kind) -> rewritten body. ``kind`` is one of
``'skill'``, ``'agent'``, or ``'command'``."""


def _identity_body(body: str, _bundle: str, _kind: str) -> str:
    return body


def iter_bundle_dirs(marketplace_dir: Path, bundles: list[str] | None) -> Iterator[Path]:
    """Yield bundle directories under ``marketplace_dir``.

    A directory qualifies as a bundle when it contains
    ``.claude-plugin/plugin.json``. The optional ``bundles`` list scopes
    the iteration to specific bundle names (path-traversal-safe).
    """
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


def _read_plugin_json(bundle_dir: Path) -> dict:
    plugin_json = bundle_dir / '.claude-plugin' / 'plugin.json'
    if not plugin_json.exists():
        return {}
    parsed: dict = json.loads(plugin_json.read_text(encoding='utf-8'))
    return parsed


def _safe_rmtree(path: Path, output_dir: Path) -> None:
    """Remove ``path`` only when it is contained within ``output_dir``."""
    resolved = path.resolve()
    resolved_output = output_dir.resolve()
    sentinel = str(resolved_output) + '/'
    if not str(resolved).startswith(sentinel) and resolved != resolved_output:
        raise ValueError(f'Refusing to delete {resolved}: not within output directory {resolved_output}')
    shutil.rmtree(path)


def _copy_verbatim(src: Path, dst: Path, *, output_dir: Path, written: list[Path]) -> None:
    if dst.exists():
        _safe_rmtree(dst, output_dir)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*EXCLUDED_DIR_NAMES))
    for f in dst.rglob('*'):
        if f.is_file():
            written.append(f)


def _emit_skill(
    bundle_name: str,
    skill_dir: Path,
    output_dir: Path,
    mapping: dict[str, dict[str, str]],
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

    target_skill_dir = output_dir / 'skill' / f'{bundle_name}-{skill_name}'
    target_skill_dir.mkdir(parents=True, exist_ok=True)
    target_skill_md = target_skill_dir / 'SKILL.md'
    target_skill_md.write_text(new_fm + '\n\n' + new_body, encoding='utf-8')
    written.append(target_skill_md)

    # Reference the unused mapping so static checkers don't flag it; the
    # full mapping is consumed by agent transforms below.
    _ = mapping  # noqa: F841

    for subdir_name in VERBATIM_SKILL_SUBDIRS:
        src_subdir = skill_dir / subdir_name
        if src_subdir.exists() and src_subdir.is_dir():
            dst_subdir = target_skill_dir / subdir_name
            _copy_verbatim(src_subdir, dst_subdir, output_dir=output_dir, written=written)

    # Dual-emit: user-invocable: true skills also get a command wrapper.
    if _is_user_invocable(fm):
        _emit_user_invocable_wrapper(
            bundle_name=bundle_name,
            skill_name=skill_name,
            fm=fm,
            mapping=mapping,
            output_dir=output_dir,
            written=written,
        )


def _is_user_invocable(fm: dict[str, str]) -> bool:
    raw = fm.get('user-invocable', '').strip().lower()
    return raw in {'true', 'yes', '1'}


def _resolve_template_model(value: str, mapping: dict) -> str | None:
    if not value:
        return None
    model_map = mapping.get('model_map', {})
    entry = model_map.get(value)
    if entry is None:
        return value
    if not isinstance(entry, dict) or 'id' not in entry:
        return value
    return f'{OPENCODE_MODEL_PREFIX}{entry["id"]}'


def _render_user_invocable_template(description: str, model: str | None, skill_id: str) -> str:
    """Render the wrapper template with simple placeholder substitution.

    The template uses ``{{description}}``, optional
    ``{{#model}}model: {{model}}{{/model}}`` block, and ``{{skill_id}}``.
    Substitution is intentionally simple — no full Mustache parser — to
    keep the dependency surface minimal.
    """
    if not _USER_INVOCABLE_TEMPLATE.is_file():
        raise FileNotFoundError(
            f'OpenCode user-invocable template not found: {_USER_INVOCABLE_TEMPLATE}'
        )
    text = _USER_INVOCABLE_TEMPLATE.read_text(encoding='utf-8')
    if model:
        text = text.replace('{{#model}}model: {{model}}{{/model}}', f'model: {model}')
    else:
        # Strip the optional block (and the surrounding newline) when no model.
        text = text.replace('{{#model}}model: {{model}}{{/model}}\n', '')
        text = text.replace('{{#model}}model: {{model}}{{/model}}', '')
    text = text.replace('{{description}}', description)
    text = text.replace('{{skill_id}}', skill_id)
    return text


def _emit_user_invocable_wrapper(
    *,
    bundle_name: str,
    skill_name: str,
    fm: dict[str, str],
    mapping: dict[str, dict[str, str]],
    output_dir: Path,
    written: list[Path],
) -> None:
    """Write the OpenCode command wrapper for a user-invocable skill."""
    description = fm.get('description', '').splitlines()[0].strip() if fm.get('description') else ''
    model_raw = fm.get('model', '').strip()
    model = _resolve_template_model(model_raw, mapping) if model_raw else None
    skill_id = f'{bundle_name}-{skill_name}'

    rendered = _render_user_invocable_template(description, model, skill_id)

    command_dir = output_dir / 'command'
    command_dir.mkdir(parents=True, exist_ok=True)
    target = command_dir / f'{skill_id}.md'
    target.write_text(rendered, encoding='utf-8')
    written.append(target)


def _emit_agent(
    bundle_name: str,
    agent_md: Path,
    output_dir: Path,
    mapping: dict[str, dict[str, str]],
    rules: dict[str, list[str]],
    body_transformer: BodyTransformer,
    written: list[Path],
    agent_index: dict[str, dict[str, str]],
    mapping_path: Path,
) -> None:
    if not agent_md.exists():
        return
    content = agent_md.read_text(encoding='utf-8')
    fm, body = parse_frontmatter(content)
    source_label = f'agents/{bundle_name}/{agent_md.name}'

    new_fm = transform_agent_frontmatter(fm, mapping, rules, source_label=source_label)
    new_body = body_transformer(body, bundle_name, 'agent')

    agent_dir = output_dir / 'agent'
    agent_dir.mkdir(parents=True, exist_ok=True)
    target_agent = agent_dir / agent_md.name
    target_agent.write_text(new_fm + '\n\n' + new_body, encoding='utf-8')
    written.append(target_agent)

    # Record an index entry for opencode.json. Strip the .md suffix so
    # the agent identifier matches OpenCode's CLI / config conventions.
    agent_id = agent_md.stem
    agent_index[agent_id] = {'bundle': bundle_name, 'source': source_label}

    # Role-eligible agents (dynamic-level-executor extension point) also emit
    # per-level variant files alongside the canonical one, each with a concrete
    # model resolved from LEVEL_TABLE + mapping.json::model_map. Non-eligible
    # agents leave this a no-op (returns None).
    result = emit_agent_variants(
        fm,
        new_body,
        agent_id,
        agent_dir,
        mapping,
        rules,
        source_label=source_label,
        mapping_path=mapping_path,
    )
    if result is not None:
        for level in result.variants_emitted:
            variant_path = agent_dir / f'{agent_id}-{level}.md'
            written.append(variant_path)
            agent_index[f'{agent_id}-{level}'] = {
                'bundle': bundle_name,
                'source': source_label,
            }


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

    command_dir = output_dir / 'command'
    command_dir.mkdir(parents=True, exist_ok=True)
    target_command = command_dir / command_md.name
    target_command.write_text(new_fm + '\n\n' + new_body, encoding='utf-8')
    written.append(target_command)


def _resolve_skill_dirs(bundle_dir: Path, plugin_config: dict) -> list[Path]:
    refs = plugin_config.get('skills', [])
    skills: list[Path] = []
    if refs:
        for ref in refs:
            ref_str = str(ref).lstrip('./')
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
            ref_str = str(ref).lstrip('./')
            candidate = bundle_dir / ref_str
            if candidate.is_file():
                paths.append(candidate)
        return paths
    fallback = bundle_dir / fallback_subdir
    if fallback.exists():
        paths = sorted(p for p in fallback.iterdir() if p.is_file() and p.suffix == '.md' and not p.name.startswith('.'))
    return paths


def _generate_opencode_json(
    output_dir: Path,
    agent_index: dict[str, dict[str, str]],
) -> Path:
    """Write ``opencode.json`` with the provider config and per-agent stubs.

    The agent block records each emitted agent so OpenCode can apply
    permission overrides at the project level. Per-agent permissions are
    already embedded in each ``agent/{name}.md`` frontmatter; the project
    config keeps the agent map populated for discovery.

    ``instructions`` is deliberately omitted — the distributed plugin is
    a skill/agent/command bundle consumed by downstream projects, not a
    standalone project root. Project-level instructions (``AGENTS.md``)
    belong to each downstream project, not to the plugin artifact.
    """
    config: dict = {
        '$schema': 'https://opencode.ai/config.json',
        'skills': {
            'paths': ['./skill'],
        },
    }
    if agent_index:
        config['agent'] = {
            agent_id: {} for agent_id in sorted(agent_index)
        }
    config_path = output_dir / 'opencode.json'
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
) -> list[Path]:
    """Walk source bundles and emit OpenCode output.

    Args:
        marketplace_dir: Path to ``marketplace/bundles/`` (source of truth).
        output_dir: Destination root (e.g. ``target/opencode/``).
        config_dir: Directory containing ``mapping.json`` and
            ``frontmatter-rules.json`` (typically the OpenCode target's
            ``config_dir`` property).
        bundles: Optional list of bundle names. ``None`` means all bundles
            with a ``.claude-plugin/plugin.json``.
        body_transformer: Optional callable applied to every emitted body
            before it is written. Defaults to identity (verbatim body).

    Returns:
        List of generated paths (``SKILL.md`` files, agent / command files,
        verbatim resources, and ``opencode.json``).

    Raises:
        UnmappedFrontmatterError: A required frontmatter field is missing.
        UnmappedToolError: An agent declares a tool with no
            ``tool_permissions`` entry.
    """
    mapping = load_mapping(config_dir)
    rules = load_rules(config_dir)
    mapping_path = config_dir / 'mapping.json'
    transform_body = body_transformer or _identity_body

    bundle_list = list(bundles) if bundles is not None else None
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    agent_index: dict[str, dict[str, str]] = {}

    for bundle_dir in iter_bundle_dirs(marketplace_dir, bundle_list):
        plugin_config = _read_plugin_json(bundle_dir)
        bundle_name = plugin_config.get('name', bundle_dir.name)

        for skill_dir in _resolve_skill_dirs(bundle_dir, plugin_config):
            _emit_skill(bundle_name, skill_dir, output_dir, mapping, rules, transform_body, written)

        for agent_md in _resolve_md_components(bundle_dir, plugin_config, 'agents', 'agents'):
            _emit_agent(
                bundle_name,
                agent_md,
                output_dir,
                mapping,
                rules,
                transform_body,
                written,
                agent_index,
                mapping_path,
            )

        for command_md in _resolve_md_components(bundle_dir, plugin_config, 'commands', 'commands'):
            _emit_command(bundle_name, command_md, output_dir, rules, transform_body, written)

    written.append(_generate_opencode_json(output_dir, agent_index))
    return written


__all__ = [
    'BodyTransformer',
    'EXCLUDED_DIR_NAMES',
    'VERBATIM_SKILL_SUBDIRS',
    'UnmappedFrontmatterError',
    'UnmappedToolError',
    'emit_bundles',
    'iter_bundle_dirs',
]

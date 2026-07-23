#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic markdown renderers for the architecture overview / deep-dive.

Extracted verbatim from ``_cmd_client``; the facade re-exports every public
name here. Covers ``render_overview`` and ``render_module_markdown`` plus the
per-section ``_render_*`` helpers and the shared line-budget machinery.
"""

from typing import Any

from _architecture_core import (
    DataNotFoundError,
    ModuleNotFoundInProjectError,
    get_root_module,
    iter_modules,
    load_module_derived,
    load_module_enriched_or_empty,
    load_project_meta,
    merge_module_data,
)
from _cmd_client_query import (
    _build_internal_deps_map,
    _load_module_or_raise,
)

DEFAULT_OVERVIEW_BUDGET = 200


# =============================================================================
# Overview Renderer
# =============================================================================


_TRUNCATION_MARKER_PREFIX = '... (truncated to fit budget='


def _truncation_marker(budget: int, required: int) -> str:
    return f'{_TRUNCATION_MARKER_PREFIX}{budget}; full output requires --budget {required})'


def _render_project_section(meta: dict[str, Any]) -> list[str]:
    name = meta.get('name', '(unnamed project)')
    description = (meta.get('description') or '').strip()
    lines = [f'# {name}', '']
    if description:
        lines.extend([description, ''])
    return lines


def _render_modules_section(enriched_by_name: dict[str, dict[str, Any]]) -> list[str]:
    if not enriched_by_name:
        return []

    lines = ['## Modules', '', '| Module | Purpose | Responsibility |', '|---|---|---|']
    for name in sorted(enriched_by_name.keys()):
        enriched_mod = enriched_by_name[name]
        purpose = (enriched_mod.get('purpose') or '').strip() or '—'
        responsibility = (enriched_mod.get('responsibility') or '').strip()
        responsibility = responsibility.replace('\n', ' ') if responsibility else '—'
        lines.append(f'| {name} | {purpose} | {responsibility} |')
    lines.append('')
    return lines


def _render_adjacency_section(deps_map: dict[str, list[str]]) -> list[str]:
    if not deps_map:
        return []
    lines = ['## Adjacency', '', '| Module | Internal Dependencies |', '|---|---|']
    for name in sorted(deps_map.keys()):
        deps = deps_map[name]
        rendered = ', '.join(sorted(deps)) if deps else '—'
        lines.append(f'| {name} | {rendered} |')
    lines.append('')
    return lines


def _count_profile_skills(profile_data: Any) -> int:
    """Count skill entries in a single profile's value.

    The value may be either a dict (with ``defaults``/``optionals`` lists) or
    a flat list. Any other shape contributes zero. Centralised so render
    helpers and module deep-dives stay in lock-step on the count semantics.
    """
    if isinstance(profile_data, dict):
        defaults = profile_data.get('defaults', [])
        optionals = profile_data.get('optionals', [])
        return len(defaults) + len(optionals)
    if isinstance(profile_data, list):
        return len(profile_data)
    return 0


def _render_skills_by_profile_section(enriched_by_name: dict[str, dict[str, Any]]) -> list[str]:
    rows: list[tuple[str, dict[str, Any]]] = []
    for name in sorted(enriched_by_name.keys()):
        skills_by_profile = enriched_by_name[name].get('skills_by_profile', {})
        if skills_by_profile:
            rows.append((name, skills_by_profile))
    if not rows:
        return []

    lines = ['## Skills by Profile', '']
    for name, skills_by_profile in rows:
        lines.append(f'### {name}')
        lines.append('')
        for profile in sorted(skills_by_profile.keys()):
            count = _count_profile_skills(skills_by_profile[profile])
            lines.append(f'- {profile}: {count} skill{"s" if count != 1 else ""}')
        lines.append('')
    return lines


def _apply_budget(sections: list[list[str]], budget: int) -> tuple[list[str], int]:
    """Apply line budget to ordered sections, dropping trailing sections first.

    Sections are listed in priority order (most important first). When the
    concatenated output exceeds `budget` lines, drop trailing sections one at
    a time until it fits, leaving room for a single truncation marker line.

    Returns:
        (rendered_lines, required_budget) where required_budget is the line
        count that would be needed to render every section in full.
    """
    full = [line for section in sections for line in section]
    required = len(full)
    if required <= budget:
        return full, required

    # Try keeping prefixes of section list, leaving 1 line for marker.
    for keep in range(len(sections) - 1, 0, -1):
        prefix = [line for section in sections[:keep] for line in section]
        if len(prefix) + 1 <= budget:
            return [*prefix, _truncation_marker(budget, required)], required

    # Even one section won't fit. Hard-truncate the first section.
    head = sections[0][: max(budget - 1, 0)]
    return [*head, _truncation_marker(budget, required)], required


def render_overview(project_dir: str = '.', budget: int = DEFAULT_OVERVIEW_BUDGET) -> str:
    """Render deterministic markdown summary of the project architecture.

    Sections in priority order: project header > modules table > adjacency
    table > skills_by_profile summary. When the rendered output exceeds
    `budget` lines, trailing sections are dropped and a marker is appended.

    Args:
        project_dir: Project directory path
        budget: Maximum line count for the rendered markdown

    Returns:
        Markdown string. Always ends with a trailing newline so byte-identical
        repeat invocations produce identical files.
    """
    meta = load_project_meta(project_dir)
    module_names = iter_modules(project_dir)
    derived_by_name: dict[str, dict[str, Any]] = {}
    for name in module_names:
        try:
            derived_by_name[name] = load_module_derived(name, project_dir)
        except DataNotFoundError:
            derived_by_name[name] = {}
    enriched_by_name: dict[str, dict[str, Any]] = {
        name: load_module_enriched_or_empty(name, project_dir) for name in module_names
    }
    deps_map, _ = _build_internal_deps_map(
        project_dir,
        derived_by_name=derived_by_name,
        enriched_by_name=enriched_by_name,
    )

    sections = [
        _render_project_section(meta),
        _render_modules_section(enriched_by_name),
        _render_adjacency_section(deps_map),
        _render_skills_by_profile_section(enriched_by_name),
    ]
    sections = [s for s in sections if s]

    rendered, _ = _apply_budget(sections, budget)
    return '\n'.join(rendered).rstrip('\n') + '\n'


def render_module_markdown(
    module_name: str | None = None,
    project_dir: str = '.',
    budget: int = DEFAULT_OVERVIEW_BUDGET,
    *,
    merged: dict[str, Any] | None = None,
) -> str:
    """Render budgeted markdown deep-dive for a single module.

    Sections in priority order: header (name, purpose, responsibility) >
    internal dependencies > key packages > skills_by_profile > tips/insights.

    Args:
        module_name: Module name (None resolves to root module)
        project_dir: Project directory path
        budget: Maximum line count for the rendered markdown
        merged: Optional pre-loaded merged module data (derived + enriched).
            When supplied, the helper skips ``_load_module_or_raise`` /
            ``merge_module_data`` calls and trusts the caller's already-loaded
            dict. The caller is responsible for having validated the module
            name when the kwarg is non-None.

    Returns:
        Markdown string ending with a trailing newline.
    """
    if not module_name:
        module_name = get_root_module(project_dir)
        if not module_name:
            raise ModuleNotFoundInProjectError('No modules found', [])

    if merged is None:
        # Validate the module exists; raises ModuleNotFoundInProjectError otherwise
        _load_module_or_raise(module_name, project_dir)
        merged = merge_module_data(module_name, project_dir)

    purpose = merged.get('purpose', '').strip() or '—'
    responsibility = merged.get('responsibility', '').strip() or '—'
    header = [
        f'# {module_name}',
        '',
        f'**Purpose**: {purpose}',
        f'**Responsibility**: {responsibility}',
        '',
    ]

    deps_map, _ = _build_internal_deps_map(project_dir)
    deps = deps_map.get(module_name, [])
    deps_section: list[str] = []
    if deps:
        deps_section = ['## Internal Dependencies', '']
        deps_section.extend(f'- {d}' for d in deps)
        deps_section.append('')

    packages = merged.get('key_packages') or merged.get('packages') or []
    packages_section: list[str] = []
    if packages:
        packages_section = ['## Key Packages', '']
        for pkg in packages:
            if isinstance(pkg, dict):
                pkg_name = pkg.get('name') or pkg.get('package') or ''
                desc = pkg.get('description', '').strip()
                if desc:
                    packages_section.append(f'- `{pkg_name}` — {desc}')
                else:
                    packages_section.append(f'- `{pkg_name}`')
            else:
                packages_section.append(f'- `{pkg}`')
        packages_section.append('')

    skills_section: list[str] = []
    skills_by_profile = merged.get('skills_by_profile', {})
    if skills_by_profile:
        skills_section = ['## Skills by Profile', '']
        for profile in sorted(skills_by_profile.keys()):
            count = _count_profile_skills(skills_by_profile[profile])
            skills_section.append(f'- {profile}: {count} skill{"s" if count != 1 else ""}')
        skills_section.append('')

    notes_section: list[str] = []
    tips = merged.get('tips') or []
    insights = merged.get('insights') or []
    practices = merged.get('best_practices') or []
    if tips or insights or practices:
        notes_section = ['## Notes', '']
        for label, items in (('Tips', tips), ('Insights', insights), ('Best Practices', practices)):
            if items:
                notes_section.append(f'**{label}**:')
                for item in items:
                    if isinstance(item, dict):
                        text = item.get('text') or item.get('message') or item.get('description') or str(item)
                    else:
                        text = str(item)
                    notes_section.append(f'- {text}')
                notes_section.append('')

    sections = [s for s in (header, deps_section, packages_section, skills_section, notes_section) if s]
    rendered, _ = _apply_budget(sections, budget)
    return '\n'.join(rendered).rstrip('\n') + '\n'

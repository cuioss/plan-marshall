#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Persona resolution for the persona / ref / profile identity model.

The ``resolve`` verb computes the transitive closure of a persona's composition
DAG and emits one flat, deduped ``skills[]``:

1. always the base ``plan-marshall:persona-plan-marshall-agent``;
2. the persona's direct ``composes:`` frontmatter edges (ref-* and persona-*);
3. recursively, any composed persona's own composes/profiles (DAG, cycle-rejected);
4. for each profile in the persona's ``profiles:`` frontmatter, the
   ``profile x {domains}`` domain skills resolved via the Extension API.

Persona frontmatter (``profiles:`` + ``composes:``) is the binding source of
truth — there is no hardcoded persona->profile or persona->composition table,
and composed personas are flattened here, never loaded by nested skill loading.

Output is TOON via ``serialize_toon``. Stdlib-only plus the marketplace
``toon_parser`` / ``marketplace_bundles`` shared modules (PYTHONPATH set by the
executor).
"""

import argparse
import re
import sys
from pathlib import Path

# Direct imports — PYTHONPATH set by the executor (collect_script_dirs adds
# every skill scripts/ dir, including script-shared).
from marketplace_bundles import (
    resolve_bundle_path,
    resolve_bundles_root,
)
from toon_parser import serialize_toon

BASE_PERSONA = 'plan-marshall:persona-plan-marshall-agent'

# Module-resolution states carried into the resolve payload. ``not_requested`` is
# the no-module case (no qualification evidence exists), ``unreadable`` is the
# fail-closed state where the module's frameworks could not be read.
MODULE_STATUS_NOT_REQUESTED = 'not_requested'
MODULE_STATUS_RESOLVED = 'resolved'
MODULE_STATUS_UNREADABLE = 'unreadable'



def _leading_frontmatter(content: str) -> str:
    """Return the leading ``---``...``---`` YAML frontmatter block, or ''.

    Mirrors the leading-frontmatter delimiting used across the codebase: the
    block is recognized only when the first line is ``---`` and a closing
    ``---`` follows.
    """
    lines = content.split('\n')
    if not lines or lines[0].strip() != '---':
        return ''
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            return '\n'.join(lines[1:i])
    return ''


def _parse_yaml_list(frontmatter: str, field: str) -> list[str]:
    """Parse a frontmatter list field as a list of strings.

    Supports both the inline-flow form ``field: [a, b, c]`` and the block form::

        field:
          - a
          - b

    Returns an empty list when the field is absent or empty.
    """
    # Inline-flow form: field: [a, b, c]
    inline = re.search(rf'^{re.escape(field)}:\s*\[(.*?)\]\s*$', frontmatter, re.MULTILINE)
    if inline is not None:
        body = inline.group(1).strip()
        if not body:
            return []
        return [item.strip().strip('\'"') for item in body.split(',') if item.strip()]

    # Block form: field: followed by "  - value" lines.
    block = re.search(rf'^{re.escape(field)}:\s*$', frontmatter, re.MULTILINE)
    if block is None:
        return []
    items: list[str] = []
    after = frontmatter[block.end() :].split('\n')
    for line in after:
        if line.startswith((' ', '\t')) and line.lstrip().startswith('-'):
            value = line.lstrip()[1:].strip().strip('\'"')
            if value:
                items.append(value)
        elif line.strip() == '':
            continue
        else:
            break
    return items


def _resolve_persona_path(bundles_root: Path, persona_key: str) -> Path | None:
    """Resolve a ``bundle:skill`` persona key to its SKILL.md path, or None."""
    if ':' not in persona_key:
        return None
    bundle, skill = persona_key.split(':', 1)
    path = resolve_bundle_path(bundles_root, bundle, f'skills/{skill}/SKILL.md')
    return path if path.is_file() else None


def _read_persona_frontmatter(bundles_root: Path, persona_key: str) -> dict | None:
    """Read a persona's frontmatter lists, or None when the persona is absent.

    Returns ``{'profiles': [...], 'composes': [...], 'is_persona': bool}``.
    """
    path = _resolve_persona_path(bundles_root, persona_key)
    if path is None:
        return None
    try:
        content = path.read_text(encoding='utf-8')
    except OSError:
        # TOCTOU file-removal between _resolve_persona_path's is_file() check
        # and this read, a PermissionError, or a decode failure — treat as an
        # unresolvable persona so the caller maps None to its
        # persona_not_found / composed_persona_not_found discriminator and the
        # script still emits a TOON error rather than a raw traceback.
        return None
    frontmatter = _leading_frontmatter(content)
    implements = re.search(r'^implements:\s*(.+)$', frontmatter, re.MULTILINE)
    is_persona = implements is not None and implements.group(1).strip().strip('\'"') == 'persona'
    return {
        'profiles': _parse_yaml_list(frontmatter, 'profiles'),
        'composes': _parse_yaml_list(frontmatter, 'composes'),
        'is_persona': is_persona,
    }


def _skill_name(entry: object) -> str:
    """Return the ``bundle:skill`` notation of a domain skill entry."""
    if isinstance(entry, dict):
        return str(entry.get('skill') or '')
    return str(entry)


def _excluded_skills(domain: str) -> set[str]:
    """Return the repository-level skill exclusions for ``domain``.

    The exclusion list lives in ``marshal.json`` under
    ``skill_domains.{domain}.excluded_skills`` and names skills in either the
    full ``bundle:skill`` notation or the bare skill name. An exclusion always
    wins: it removes a skill the module itself would qualify for.
    """
    try:
        from _config_core import load_config
    except Exception:
        return set()
    try:
        config = load_config()
    except Exception:
        return set()
    skill_domains = config.get('skill_domains') if isinstance(config, dict) else None
    entry = skill_domains.get(domain) if isinstance(skill_domains, dict) else None
    raw = entry.get('excluded_skills') if isinstance(entry, dict) else None
    if not isinstance(raw, list):
        return set()
    return {str(item).strip() for item in raw if str(item).strip()}


def _is_excluded(skill: str, exclusions: set[str]) -> bool:
    """True when ``skill`` matches an exclusion in full or bare-name form."""
    if not exclusions:
        return False
    return skill in exclusions or skill.split(':', 1)[-1] in exclusions


def _resolve_module_data(module: str) -> tuple[dict | None, str]:
    """Resolve one module's discovery data and its readable state.

    Returns ``(module_data, MODULE_STATUS_RESOLVED)`` on success and
    ``(None, MODULE_STATUS_UNREADABLE)`` whenever discovery cannot supply the
    module — an unreadable module never degrades into "every optional is
    applicable".
    """
    if not module:
        return None, MODULE_STATUS_NOT_REQUESTED
    try:
        from extension_discovery import discover_project_modules
        from resolve_project_dir import resolve_project_dir
    except Exception:
        return None, MODULE_STATUS_UNREADABLE
    try:
        project_root = Path(resolve_project_dir(None, None))
        discovered = discover_project_modules(project_root)
    except Exception:
        return None, MODULE_STATUS_UNREADABLE
    modules = discovered.get('modules') if isinstance(discovered, dict) else None
    if not isinstance(modules, dict):
        return None, MODULE_STATUS_UNREADABLE
    module_data = modules.get(module)
    if not isinstance(module_data, dict):
        return None, MODULE_STATUS_UNREADABLE
    return module_data, MODULE_STATUS_RESOLVED


def _find_domain_extension(domain: str):
    """Return the extension module that owns ``domain``, or None."""
    try:
        from extension_discovery import discover_all_extensions
    except Exception:
        return None
    try:
        extensions = discover_all_extensions()
    except Exception:
        return None
    for ext in extensions:
        ext_module = ext.get('module')
        if ext_module is None or not hasattr(ext_module, 'applies_to_module'):
            continue
        if not hasattr(ext_module, 'get_skill_domains'):
            continue
        try:
            keys = [
                str(info.get('domain', {}).get('key', ''))
                for info in ext_module.get_skill_domains()
                if isinstance(info, dict)
            ]
        except Exception:
            continue
        if domain in keys:
            return ext_module
    return None


def _module_qualified_skills(domain: str, profile: str, module_data: dict) -> set[str] | None:
    """Return the skills the domain extension qualifies for this module/profile.

    The qualification source is the extension's existing module-level
    applicability (``applies_to_module``): the java extension, for example,
    promotes ``java-cdi`` to the profile's defaults only when the module carries
    a CDI dependency, so a module without one does not qualify. ``None`` means
    applicability could not be computed and the caller must fail closed.
    """
    extension = _find_domain_extension(domain)
    if extension is None:
        return None
    try:
        result = extension.applies_to_module(module_data)
    except Exception:
        return None
    if not isinstance(result, dict) or not result.get('applicable'):
        return set()
    cell = (result.get('skills_by_profile') or {}).get(profile)
    defaults = cell.get('defaults') if isinstance(cell, dict) else None
    if not isinstance(defaults, list):
        return set()
    return {_skill_name(entry) for entry in defaults if _skill_name(entry)}


def _resolve_profile_domain_skills(profile: str, domain: str, module: str = '') -> dict:
    """Resolve a single ``profile x domain`` cell for the task's module.

    Mirrors ``architecture resolve`` / ``resolve-recipe``: delegates to
    ``manage-config resolve-domain-skills``. The cell's ``defaults`` are always
    kept; an ``optional`` is admitted only when the task's module qualifies for
    it through the domain extension's module-level applicability, and never when
    a repository-level exclusion names it. A module that cannot be read — or a
    missing module argument — admits defaults only and reports the state instead
    of falling back to every optional. Degrades gracefully to an empty skill
    list when the domain/profile is not resolvable in the active config.
    """
    module_status = MODULE_STATUS_NOT_REQUESTED if not module else MODULE_STATUS_UNREADABLE
    empty = {'skills': [], 'module_status': module_status}

    try:
        from _cmd_skill_resolution import cmd_resolve_domain_skills
    except Exception:
        return empty

    ns = argparse.Namespace(domain=domain, profile=profile)
    try:
        result = cmd_resolve_domain_skills(ns)
    except Exception:
        return empty
    if not isinstance(result, dict) or result.get('status') != 'success':
        return empty

    defaults: list[str] = []
    optionals: list[str] = []
    for key, target in (('defaults', defaults), ('optionals', optionals)):
        block = result.get(key) or {}
        if isinstance(block, dict):
            target.extend(_skill_name(entry) for entry in block)
        elif isinstance(block, list):
            target.extend(_skill_name(entry) for entry in block)

    exclusions = _excluded_skills(domain)
    module_data, module_status = _resolve_module_data(module)

    qualified: set[str] = set()
    if module_status == MODULE_STATUS_RESOLVED:
        computed = _module_qualified_skills(domain, profile, module_data)
        if computed is None:
            module_status = MODULE_STATUS_UNREADABLE
        else:
            qualified = computed

    skills: list[str] = []
    for skill in defaults:
        if skill and not _is_excluded(skill, exclusions) and skill not in skills:
            skills.append(skill)
    for skill in optionals:
        if not skill or _is_excluded(skill, exclusions) or skill in skills:
            continue
        if skill in qualified:
            skills.append(skill)

    return {'skills': skills, 'module_status': module_status}


def _flatten(
    bundles_root: Path,
    persona_key: str,
    domains: list[str],
    ordered: list[str],
    seen: set[str],
    visiting: set[str],
    include_self_composition: bool,
    module: str = '',
    module_statuses: list[str] | None = None,
) -> str | None:
    """Walk a persona's composition DAG, appending resolved skills in order.

    Returns an error discriminator string on failure (cycle or missing composed
    persona), or None on success. ``include_self_composition`` is False for the
    top-level persona's identity skill (which is not itself a loadable skill in
    the resolved list — only its composition and profiles are), and True for
    composed personas (whose own identity skill IS merged as a lens).

    ``module`` is the task's module: profile x domain optionals are admitted
    only when that module qualifies for them. ``module_statuses`` collects each
    cell's resolution state so the top-level payload can report an unreadable
    module.
    """
    if persona_key in visiting:
        return 'composition_cycle'
    fm = _read_persona_frontmatter(bundles_root, persona_key)
    if fm is None:
        return 'composed_persona_not_found'

    visiting.add(persona_key)

    # Merge each direct composition edge.
    for edge in fm['composes']:
        bare_skill = edge.split(':', 1)[1] if ':' in edge else edge
        if bare_skill.startswith('persona-'):
            # Recurse into composed personas; their identity skill IS merged.
            err = _flatten(
                bundles_root,
                edge,
                domains,
                ordered,
                seen,
                visiting,
                include_self_composition=True,
                module=module,
                module_statuses=module_statuses,
            )
            if err is not None:
                visiting.discard(persona_key)
                return err
        else:
            # A ref-* (or any non-persona) concern: merge the skill itself.
            if edge not in seen:
                seen.add(edge)
                ordered.append(edge)

    # Merge profile x domain skills for each declared profile x each domain.
    for profile in fm['profiles']:
        for domain in domains:
            resolution = _resolve_profile_domain_skills(profile, domain, module)
            if module_statuses is not None:
                module_statuses.append(resolution['module_status'])
            for skill in resolution['skills']:
                if skill not in seen:
                    seen.add(skill)
                    ordered.append(skill)

    # A composed persona's own identity skill is merged as a lens.
    if include_self_composition and persona_key not in seen:
        seen.add(persona_key)
        ordered.append(persona_key)

    visiting.discard(persona_key)
    return None


def cmd_resolve(args) -> dict:
    """Resolve a persona's composition DAG into a flat, deduped skills[]."""
    persona_key = args.persona_key
    domains = [d.strip() for d in args.domains.split(',')] if args.domains else []
    domains = [d for d in domains if d]
    module = (getattr(args, 'module', '') or '').strip()

    try:
        bundles_root = resolve_bundles_root(Path(__file__))
    except Exception as exc:  # pragma: no cover - import-time misconfiguration
        return {'status': 'error', 'error': 'bundles_root_unresolved', 'detail': str(exc)}

    fm = _read_persona_frontmatter(bundles_root, persona_key)
    if fm is None:
        return {'status': 'error', 'error': 'persona_not_found', 'persona_key': persona_key}
    if not fm['is_persona']:
        return {'status': 'error', 'error': 'not_a_persona', 'persona_key': persona_key}

    ordered: list[str] = []
    seen: set[str] = set()
    module_statuses: list[str] = []

    # (1) Base is always included, unconditionally.
    seen.add(BASE_PERSONA)
    ordered.append(BASE_PERSONA)

    # (2)-(4) Flatten the persona's own composition + profiles (its identity
    # skill is the dispatch target, not a merged lens, so include_self=False).
    err = _flatten(
        bundles_root,
        persona_key,
        domains,
        ordered,
        seen,
        visiting=set(),
        include_self_composition=False,
        module=module,
        module_statuses=module_statuses,
    )
    if err is not None:
        return {'status': 'error', 'error': err, 'persona_key': persona_key}

    if not module:
        module_status = MODULE_STATUS_NOT_REQUESTED
    elif any(status == MODULE_STATUS_UNREADABLE for status in module_statuses):
        module_status = MODULE_STATUS_UNREADABLE
    else:
        module_status = MODULE_STATUS_RESOLVED

    return {
        'status': 'success',
        'persona_key': persona_key,
        'module': module,
        'module_status': module_status,
        'skills': ordered,
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse surface (allow_abbrev=False per the script contract)."""
    parser = argparse.ArgumentParser(
        description='Resolve a persona composition DAG into a flat deduped skills[]',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    p_resolve = subparsers.add_parser(
        'resolve',
        help='Resolve a persona composition DAG into a flat deduped skills[]',
        allow_abbrev=False,
    )
    p_resolve.add_argument(
        '--persona-key',
        required=True,
        dest='persona_key',
        help='bundle:skill notation of the persona to resolve',
    )
    p_resolve.add_argument(
        '--domains',
        default='',
        help='Comma-separated domain names whose profile x domain skills are merged',
    )
    p_resolve.add_argument(
        '--module',
        default='',
        help=(
            "Task's module name. Profile x domain optionals are admitted only when "
            'this module qualifies for them; omit it to admit defaults only.'
        ),
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == 'resolve':
        result = cmd_resolve(args)
    else:  # pragma: no cover - argparse enforces required subcommand
        parser.error(f'Unknown command: {args.command}')
        return 2

    print(serialize_toon(result))
    return 0 if result.get('status') == 'success' else 1


if __name__ == '__main__':
    sys.exit(main())

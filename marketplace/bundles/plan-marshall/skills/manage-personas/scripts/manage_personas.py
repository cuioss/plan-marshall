#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Persona resolution for the persona / ref / profile identity model.

The ``resolve`` verb computes the transitive closure of a persona's composition
DAG and emits one flat, deduped ``skills[]``:

1. always the base ``plan-marshall:persona-plan-marshall-agent`` — assembled
   unconditionally, then subject to the exclusion lists configured for the
   requested ``--domains`` like every other skill (see :func:`cmd_resolve`);
2. the persona's direct ``composes:`` frontmatter edges (ref-* and persona-*);
3. recursively, any composed persona's own composes/profiles (DAG, cycle-rejected);
4. for each profile in the persona's ``profiles:`` frontmatter, the
   ``profile x {domains}`` domain skills resolved via the Extension API.

Persona frontmatter (``profiles:`` + ``composes:``) is the binding source of
truth — there is no hardcoded persona->profile or persona->composition table,
and composed personas are flattened here, never loaded by nested skill loading.

The ``resolve-task-skills`` verb is the scripted form of that derivation for a
task whose only identity is its profile: it derives the persona (the one whose
FIRST ``profiles:`` entry equals the task's profile) and returns the same
flattened ``skills[]``, so the workflow names a call a script makes.

Output is TOON via ``serialize_toon``. Stdlib-only plus the marketplace
``toon_parser`` / ``marketplace_bundles`` shared modules (PYTHONPATH set by the
executor).
"""

import argparse
import re
import sys
from functools import lru_cache
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

    Delegates to the shared reader in ``extension_base`` so the resolver and the
    architecture path consult ONE exclusion definition rather than two copies
    that can drift.

    An unimportable shared module is NOT "no exclusions": the exclusion list is a
    prohibition, and a reader that cannot be loaded must not answer "nothing is
    forbidden" — that reading lets a forbidden skill reach the task while looking
    like a clean configuration. The failure is raised with the reader's own
    ``skill_exclusions_unreadable`` code so callers report it as such.
    """
    try:
        from extension_base import excluded_skills
    except Exception as exc:
        raise RuntimeError(
            f'skill_exclusions_unreadable: the shared exclusion reader is not importable: {exc}'
        ) from exc

    return excluded_skills(domain)


def _is_excluded(skill: str, exclusions: set[str]) -> bool:
    """True when ``skill`` matches an exclusion in full or bare-name form.

    Delegates to the shared matcher in ``extension_base`` for the same
    single-definition reason as :func:`_excluded_skills`, and fails the same way:
    an unimportable matcher is an error, never a silent "not excluded".
    """
    try:
        from extension_base import is_excluded
    except Exception as exc:
        raise RuntimeError(
            f'skill_exclusions_unreadable: the shared exclusion matcher is not importable: {exc}'
        ) from exc

    return is_excluded(skill, exclusions)


@lru_cache(maxsize=1)
def _discovered_modules() -> dict:
    """Discover and cache the project's module data for this resolver process.

    The resolver walks the project once per process rather than once per
    profile x domain cell: phase-4-plan resolves a persona once per task, and a
    repeated full discovery would dominate the cost.
    """
    from extension_discovery import discover_project_modules
    from resolve_project_dir import resolve_project_dir

    project_root = Path(resolve_project_dir(None, None))
    discovered = discover_project_modules(project_root)
    modules = discovered.get('modules') if isinstance(discovered, dict) else None
    if not isinstance(modules, dict):
        raise ValueError('module discovery returned no module map')
    return modules


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
        module_data = _discovered_modules().get(module)
    except Exception:
        return None, MODULE_STATUS_UNREADABLE
    if not isinstance(module_data, dict):
        return None, MODULE_STATUS_UNREADABLE
    return module_data, MODULE_STATUS_RESOLVED


@lru_cache(maxsize=1)
def _all_extension_modules() -> tuple:
    """Load every domain extension once for this resolver process."""
    from extension_discovery import discover_all_extensions

    return tuple(entry.get('module') for entry in discover_all_extensions() if entry.get('module') is not None)


def _find_domain_extension(domain: str):
    """Return the extension module that owns ``domain``, or None."""
    try:
        extensions = _all_extension_modules()
    except Exception:
        return None
    for ext_module in extensions:
        if not hasattr(ext_module, 'applies_to_module'):
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


def _module_qualified_skills(
    domain: str,
    profile: str,
    optionals: list[str],
    module_data: dict,
) -> set[str] | None:
    """Return the optionals the domain extension qualifies for this module/profile.

    Qualification is delegated to the extension's ``qualifies_optional`` hook —
    the module-level applicability seam. The java extension, for example,
    qualifies ``java-cdi`` only for a module carrying a CDI dependency, so a
    module without one does not receive it. ``None`` means applicability could
    not be computed and the caller must fail closed.
    """
    extension = _find_domain_extension(domain)
    if extension is None:
        # No owning extension means no module-level qualification signal: no
        # optional is admitted, which is the fail-closed direction.
        return set()
    try:
        applicable = extension.applies_to_module(module_data)
    except Exception:
        return None
    if not isinstance(applicable, dict) or not applicable.get('applicable'):
        return set()

    qualifies = getattr(extension, 'qualifies_optional', None)
    if qualifies is None:
        # An extension predating the hook carries no optional signal, and a
        # missing signal can never prove an optional applies. Fail closed to the
        # cell's defaults; ``ExtensionBase``'s own ``True`` default is what keeps
        # optionals for a domain that derives it without overriding the hook.
        return set()

    qualified: set[str] = set()
    for skill in optionals:
        try:
            if qualifies(profile, skill, module_data):
                qualified.add(skill)
        except Exception:
            return None
    return qualified


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

    skills: list[str] = []
    for skill in defaults:
        if skill and not _is_excluded(skill, exclusions) and skill not in skills:
            skills.append(skill)

    candidates: list[str] = []
    for skill in optionals:
        if skill and not _is_excluded(skill, exclusions) and skill not in skills and skill not in candidates:
            candidates.append(skill)

    qualified: set[str] = set()
    if not module:
        module_status = MODULE_STATUS_NOT_REQUESTED
    elif not candidates:
        # Nothing to qualify: no module data has to be read for this cell.
        module_status = MODULE_STATUS_RESOLVED
    else:
        module_data, module_status = _resolve_module_data(module)
        if module_status == MODULE_STATUS_RESOLVED and module_data is not None:
            computed = _module_qualified_skills(domain, profile, candidates, module_data)
            if computed is None:
                module_status = MODULE_STATUS_UNREADABLE
            else:
                qualified = computed

    for skill in candidates:
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
    """Resolve a persona's composition DAG into a flat, deduped skills[].

    Fails closed on an unreadable exclusion configuration: the prohibition is
    reported (``skill_exclusions_unreadable``) instead of being read as "no
    exclusions", which would serve a forbidden skill.
    """
    try:
        return _resolve_persona(args)
    except Exception as exc:
        if _is_exclusion_read_failure(exc):
            return {'status': 'error', 'error': 'skill_exclusions_unreadable', 'detail': str(exc)}
        raise


def _is_exclusion_read_failure(exc: Exception) -> bool:
    """Whether ``exc`` is the exclusion reader's typed failure.

    Both carriers are recognised: the shared reader's own
    :class:`SkillExclusionReadError` (``code`` attribute) and the
    ``RuntimeError`` raised when that reader cannot even be imported, which
    carries the same code in its message.
    """
    return getattr(exc, 'code', '') == 'skill_exclusions_unreadable' or str(exc).startswith(
        'skill_exclusions_unreadable'
    )


def _resolve_persona(args) -> dict:
    """The ``resolve`` implementation, without the exclusion-failure boundary."""
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

    # The veto binds the flattened result too, not only the profile x domain
    # cells: a composed ref or the always-added base can name a skill the
    # repository excludes for one of the requested domains.
    exclusions: set[str] = set()
    for domain in domains:
        exclusions |= _excluded_skills(domain)
    if exclusions:
        ordered = [skill for skill in ordered if not _is_excluded(skill, exclusions)]

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


def _iter_persona_keys(bundles_root: Path) -> list[str]:
    """Return every installed persona's ``bundle:skill`` key.

    Handles both installed layouts: the source tree's ``{bundle}/skills/`` and a
    deployed bundle's ``{bundle}/{version}/skills/``.
    """
    keys: list[str] = []
    if not bundles_root.is_dir():
        return keys
    for bundle_dir in sorted(path for path in bundles_root.iterdir() if path.is_dir()):
        candidates: list[Path] = []
        skills_root = bundle_dir / 'skills'
        if skills_root.is_dir():
            candidates.extend(sorted(skills_root.glob('persona-*')))
        if not candidates:
            for version_dir in sorted(path for path in bundle_dir.iterdir() if path.is_dir()):
                version_skills = version_dir / 'skills'
                if version_skills.is_dir():
                    candidates.extend(sorted(version_skills.glob('persona-*')))
        keys.extend(f'{bundle_dir.name}:{candidate.name}' for candidate in candidates)
    return sorted(set(keys))


def persona_for_profile(bundles_root: Path, profile: str) -> str | None:
    """Return the persona whose FIRST ``profiles:`` entry is ``profile``.

    The first-entry rule is the identity binding phase-4 used to perform by hand:
    a profile may appear in several personas' lists, and only the persona that
    claims it as its PRIMARY profile owns the task's persona shell.
    """
    if not profile:
        return None
    for key in _iter_persona_keys(bundles_root):
        frontmatter = _read_persona_frontmatter(bundles_root, key)
        if frontmatter is None or not frontmatter['is_persona']:
            continue
        profiles = frontmatter['profiles']
        if profiles and profiles[0] == profile:
            return key
    return None


def cmd_resolve_task_skills(args) -> dict:
    """Derive a task's persona from its profile and resolve its flattened skills.

    The scripted form of the phase-4-plan persona augmentation: the profile ->
    persona derivation (the first-entry reverse lookup over persona frontmatter)
    and the resolver call are one executed step, so the workflow names a call a
    script makes instead of a scan the agent is asked to perform by hand.
    """
    profile = (getattr(args, 'profile', '') or '').strip()
    if not profile:
        return {'status': 'error', 'error': 'profile_required'}

    try:
        bundles_root = resolve_bundles_root(Path(__file__))
    except Exception as exc:  # pragma: no cover - import-time misconfiguration
        return {'status': 'error', 'error': 'bundles_root_unresolved', 'detail': str(exc)}

    persona_key = persona_for_profile(bundles_root, profile)
    if persona_key is None:
        return {
            'status': 'success',
            'profile': profile,
            'persona_key': '',
            'skills': [],
            'reason': 'no_persona_for_profile',
        }

    resolved = cmd_resolve(
        argparse.Namespace(
            persona_key=persona_key,
            domains=getattr(args, 'domains', '') or '',
            module=getattr(args, 'module', '') or '',
        )
    )
    if resolved.get('status') != 'success':
        return resolved

    return {
        'status': 'success',
        'profile': profile,
        'persona_key': persona_key,
        'module': resolved['module'],
        'module_status': resolved['module_status'],
        'skills': resolved['skills'],
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

    p_task = subparsers.add_parser(
        'resolve-task-skills',
        help="Derive a task's persona from its primary profile and resolve its flattened skills",
        allow_abbrev=False,
    )
    p_task.add_argument(
        '--profile',
        required=True,
        help="The task's primary profile (implementation, module_testing, documentation, ...)",
    )
    p_task.add_argument(
        '--domains',
        default='',
        help='Comma-separated domain names whose profile x domain skills are merged',
    )
    p_task.add_argument(
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
    elif args.command == 'resolve-task-skills':
        result = cmd_resolve_task_skills(args)
    else:  # pragma: no cover - argparse enforces required subcommand
        parser.error(f'Unknown command: {args.command}')
        return 2

    print(serialize_toon(result))
    return 0 if result.get('status') == 'success' else 1


if __name__ == '__main__':
    sys.exit(main())

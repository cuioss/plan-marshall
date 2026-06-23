#!/usr/bin/env python3
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
from marketplace_bundles import (  # type: ignore[import-not-found]
    resolve_bundle_path,
    resolve_bundles_root,
)
from toon_parser import serialize_toon  # type: ignore[import-not-found]

BASE_PERSONA = 'plan-marshall:persona-plan-marshall-agent'


def _print(data: dict) -> None:
    """Serialize a result dict to TOON on stdout."""
    print(serialize_toon(data))


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
        content = path.read_text()
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


def _resolve_profile_domain_skills(profile: str, domain: str) -> list[str]:
    """Resolve a single ``profile x domain`` cell via the Extension API.

    Mirrors ``architecture resolve`` / ``resolve-recipe``: delegates to
    ``manage-config resolve-domain-skills``. Degrades gracefully to an empty
    list when the domain/profile is not resolvable in the active config (e.g. a
    profile with no domain wiring yet, or an unknown domain), so persona
    resolution still emits base + composition.
    """
    try:
        from _cmd_skill_resolution import cmd_resolve_domain_skills  # type: ignore[import-not-found]
    except Exception:
        return []

    ns = argparse.Namespace(domain=domain, profile=profile)
    try:
        result = cmd_resolve_domain_skills(ns)
    except Exception:
        return []
    if not isinstance(result, dict) or result.get('status') != 'success':
        return []
    skills: list[str] = []
    for key in ('defaults', 'optionals'):
        block = result.get(key) or {}
        if isinstance(block, dict):
            skills.extend(block.keys())
        elif isinstance(block, list):
            skills.extend(str(s) for s in block)
    return skills


def _flatten(
    bundles_root: Path,
    persona_key: str,
    domains: list[str],
    ordered: list[str],
    seen: set[str],
    visiting: set[str],
    include_self_composition: bool,
) -> str | None:
    """Walk a persona's composition DAG, appending resolved skills in order.

    Returns an error discriminator string on failure (cycle or missing composed
    persona), or None on success. ``include_self_composition`` is False for the
    top-level persona's identity skill (which is not itself a loadable skill in
    the resolved list — only its composition and profiles are), and True for
    composed personas (whose own identity skill IS merged as a lens).
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
                bundles_root, edge, domains, ordered, seen, visiting, include_self_composition=True
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
            for skill in _resolve_profile_domain_skills(profile, domain):
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
    )
    if err is not None:
        return {'status': 'error', 'error': err, 'persona_key': persona_key}

    return {'status': 'success', 'persona_key': persona_key, 'skills': ordered}


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

    _print(result)
    return 0 if result.get('status') == 'success' else 1


if __name__ == '__main__':
    sys.exit(main())

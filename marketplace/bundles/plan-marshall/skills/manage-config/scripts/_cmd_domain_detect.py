#!/usr/bin/env python3
"""Deterministic domain detector for phase-1-init Step 7.

Walks the plan's clarified-request narrative for explicit mentions of
configured skill_domains (or their bundle aliases) and returns the
single matching domain. When no domain matches OR multiple match with
no clear winner, returns ``ambiguous=true`` so the caller raises an
``AskUserQuestion`` — there is no LLM dispatch fallback here, the
multi-match case is genuinely human-input territory.

Single-domain projects auto-select regardless of narrative content (the
manage-config "configure" step only allowed that one domain in the
first place, so the answer is fixed).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from _config_core import load_config  # type: ignore[import-not-found]
from _plan_parsing import parse_document_sections  # type: ignore[import-not-found]
from file_ops import get_plan_dir  # type: ignore[import-not-found]

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]+")


def _tokenize(text: str) -> set[str]:
    """Split on non-alphanumeric boundaries (hyphens included).

    Splitting on hyphens lets compound identifiers like ``java-core`` and
    ``ext-outline-java`` match the bare-word aliases derived from bundle
    references and domain keys. Without it ``java-core`` would only match
    a literal ``java-core`` alias, which the registry rarely declares.
    """
    return {m.group(0).lower() for m in _TOKEN_RE.finditer(text or '')}


def _load_narrative(plan_id: str) -> tuple[str, str | None]:
    """Read clarified_request (or original_input fallback) from request.md."""
    plan_dir = get_plan_dir(plan_id)
    # Lesson-derived plans stage the body at lesson-{id}.md.
    for candidate in sorted(plan_dir.glob('lesson-*.md')):
        try:
            body = candidate.read_text(encoding='utf-8')
        except OSError:
            continue
        if body.strip():
            return body, f'lesson-body:{candidate.name}'

    request_path = plan_dir / 'request.md'
    if not request_path.exists():
        return '', None
    try:
        content = request_path.read_text(encoding='utf-8')
    except OSError:
        return '', None

    sections = parse_document_sections(content)
    for section in ('clarified_request', 'original_input'):
        section_body = sections.get(section)
        if isinstance(section_body, str) and section_body.strip():
            return section_body, section
    return '', None


def _collect_aliases(domain: str, domain_config: dict[str, Any]) -> set[str]:
    """Return the lowercase token set that should match this domain.

    Includes the domain key itself, any ``bundle`` reference, and any
    skill names from ``defaults``/``optionals``/``execute_task_skills``
    so users can mention specific skills (e.g., "java-core") and have
    the detector route to the right domain.
    """
    aliases: set[str] = {domain.lower()}
    bundle = domain_config.get('bundle')
    if isinstance(bundle, str) and bundle:
        aliases.add(bundle.lower())
        # Bundle references like "pm-dev-java" also surface the bare
        # domain ("java") and the "dev-{domain}" form. Splitting on
        # non-alphanumerics gives the natural shorthand set.
        for piece in re.split(r'[^A-Za-z0-9]+', bundle):
            if piece and len(piece) > 2:
                aliases.add(piece.lower())

    def _walk(obj: Any) -> None:
        if isinstance(obj, str):
            for piece in re.split(r'[^A-Za-z0-9]+', obj):
                if piece and len(piece) > 2:
                    aliases.add(piece.lower())
        elif isinstance(obj, dict):
            for value in obj.values():
                _walk(value)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    for key in ('defaults', 'optionals', 'execute_task_skills', 'project_skills'):
        if key in domain_config:
            _walk(domain_config[key])

    # Strip generic terms that would over-match every plan.
    aliases.discard('skill')
    aliases.discard('skills')
    aliases.discard('plan')
    aliases.discard('marshall')
    aliases.discard('marshal')
    aliases.discard('manage')
    aliases.discard('tools')
    aliases.discard('system')
    aliases.discard('default')
    aliases.discard('defaults')
    aliases.discard('test')
    aliases.discard('testing')
    aliases.discard('implementation')

    return aliases


def cmd_domain_detect(args) -> dict[str, Any]:
    """Run the deterministic domain detector for a plan.

    Returns ``{domain, ambiguous, candidates, source, reason}``. The
    caller (phase-1-init Step 7) uses ``ambiguous`` to decide whether
    to raise ``AskUserQuestion``; no LLM dispatch fallback applies on
    this code path.
    """
    plan_id: str = args.plan_id
    override: str | None = getattr(args, 'domain_override', None)

    plan_dir = get_plan_dir(plan_id)
    if not plan_dir.exists():
        return {
            'status': 'error',
            'error': 'plan_dir_not_found',
            'message': f'Plan directory not found: {plan_dir}',
        }

    try:
        config = load_config()
    except (FileNotFoundError, ValueError):
        return {
            'status': 'success',
            'plan_id': plan_id,
            'domain': None,
            'ambiguous': True,
            'candidates': [],
            'source': None,
            'reason': 'marshal_not_initialized',
        }

    skill_domains = config.get('skill_domains', {}) if isinstance(config, dict) else {}
    if not isinstance(skill_domains, dict) or not skill_domains:
        return {
            'status': 'success',
            'plan_id': plan_id,
            'domain': None,
            'ambiguous': True,
            'candidates': [],
            'source': None,
            'reason': 'no_skill_domains_configured',
        }

    # Filter out the synthetic ``system`` domain — Step 7 only considers
    # implementation domains.
    user_domains = {k: v for k, v in skill_domains.items() if k != 'system'}
    if not user_domains:
        return {
            'status': 'success',
            'plan_id': plan_id,
            'domain': None,
            'ambiguous': True,
            'candidates': [],
            'source': None,
            'reason': 'no_user_domains',
        }

    # Explicit override wins immediately.
    if override and override in user_domains:
        return {
            'status': 'success',
            'plan_id': plan_id,
            'domain': override,
            'ambiguous': False,
            'candidates': [{'domain': override, 'matched_aliases': []}],
            'source': 'cli_override',
            'reason': 'explicit_override',
        }

    # Single-domain auto-select (current Step 7 rule 1).
    if len(user_domains) == 1:
        only = next(iter(user_domains))
        return {
            'status': 'success',
            'plan_id': plan_id,
            'domain': only,
            'ambiguous': False,
            'candidates': [{'domain': only, 'matched_aliases': []}],
            'source': 'single_domain_configured',
            'reason': 'auto_select',
        }

    narrative, narrative_source = _load_narrative(plan_id)
    tokens = _tokenize(narrative)

    candidates: list[dict[str, Any]] = []
    for domain, domain_config in user_domains.items():
        if not isinstance(domain_config, dict):
            continue
        aliases = _collect_aliases(domain, domain_config)
        matched = sorted(aliases & tokens)
        if matched:
            candidates.append({'domain': domain, 'matched_aliases': matched})

    if len(candidates) == 1:
        return {
            'status': 'success',
            'plan_id': plan_id,
            'domain': candidates[0]['domain'],
            'ambiguous': False,
            'candidates': candidates,
            'source': narrative_source,
            'reason': 'unambiguous_narrative_match',
        }
    if len(candidates) > 1:
        return {
            'status': 'success',
            'plan_id': plan_id,
            'domain': None,
            'ambiguous': True,
            'candidates': candidates,
            'source': narrative_source,
            'reason': 'multiple_narrative_matches',
        }

    return {
        'status': 'success',
        'plan_id': plan_id,
        'domain': None,
        'ambiguous': True,
        'candidates': [],
        'source': narrative_source,
        'reason': 'no_narrative_match',
    }


_ = Path

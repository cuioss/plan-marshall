#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic domain detector for phase-1-init Step 7 and phase-2-refine.

Walks the plan's clarified-request narrative for explicit mentions of
configured skill_domains (or their bundle aliases) and returns the SET of
matching domains. The returned ``domains`` list is the unconditional union of
three legs:

- ``detector_set``    — narrative / override / single-domain resolution (ALL
  narrative matches are kept, not just a single winner).
- ``always_on_set``   — domains flagged ``always_on: true`` in skill_domains.
- ``glob_matched_set`` — domains whose ``file_globs`` match any path in the file
  signal. The file signal is ``--affected-files`` when supplied (refine passes
  the real affected_files), else path-like tokens extracted from the narrative
  the detector already reads (init, pre-module-mapping).

``ambiguous`` is ``true`` only when the detector multi-matches, OR when the
detector zero-matches AND both the always_on and glob legs are empty (there is
genuinely nothing to select — the configured non-system domains are then
surfaced as the multiSelect candidate set). A zero narrative match resolved by
the always_on / glob legs is silent (``ambiguous=false``). There is no LLM
dispatch on this path.

Single-domain projects auto-select regardless of narrative content (the
manage-config ``configure`` step only allowed that one domain in the first
place, so the answer is fixed).
"""

from __future__ import annotations

import re
from typing import Any

from _config_core import load_config
from _plan_parsing import parse_document_sections
from file_ops import get_plan_dir

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]+")

# A path-like token candidate. The character class admits '/' (separators), '.'
# (extensions), '*' (a narrative that names a glob directly), '-' and '_'.
# _extract_narrative_paths keeps only tokens that carry a '/' or a trailing
# filename extension.
_PATH_TOKEN_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./*-]*")
_EXT_RE = re.compile(r"\.[A-Za-z0-9]+$")


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
    skill names from ``defaults``, ``optionals``, and ``project_skills``
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

    for key in ('defaults', 'optionals', 'project_skills'):
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


def _extract_narrative_paths(narrative: str) -> set[str]:
    """Extract path-like tokens from the request narrative (the init file signal).

    A token qualifies as a path when it contains a separator (``/``) or ends in a
    filename extension (``.py``, ``.md``, ...). This is the best pre-module-mapping
    signal available at init; refine supplies the stronger ``--affected-files``
    list instead. Trailing sentence punctuation (a bare full stop) is stripped so
    ``foo.py.`` at the end of a sentence still surfaces as ``foo.py``.
    """
    paths: set[str] = set()
    for match in _PATH_TOKEN_RE.finditer(narrative or ''):
        token = match.group(0).rstrip('.')
        if not token:
            continue
        if '/' in token or _EXT_RE.search(token):
            paths.add(token)
    return paths


def _glob_to_regex(glob: str) -> re.Pattern[str]:
    """Translate a path glob to an anchored regex (no external deps).

    ``**/`` matches zero or more leading path segments, ``**`` matches any run
    including separators, ``*`` matches a run of non-separator characters, and
    ``?`` matches a single non-separator character. Every other character is
    matched literally.
    """
    parts: list[str] = []
    i = 0
    n = len(glob)
    while i < n:
        if glob.startswith('**/', i):
            parts.append('(?:.*/)?')
            i += 3
        elif glob.startswith('**', i):
            parts.append('.*')
            i += 2
        elif glob[i] == '*':
            parts.append('[^/]*')
            i += 1
        elif glob[i] == '?':
            parts.append('[^/]')
            i += 1
        else:
            parts.append(re.escape(glob[i]))
            i += 1
    return re.compile('^' + ''.join(parts) + '$')


def _always_on_domains(user_domains: dict[str, Any]) -> set[str]:
    """Return the set of non-system domains flagged ``always_on: true``."""
    return {
        domain
        for domain, cfg in user_domains.items()
        if isinstance(cfg, dict) and cfg.get('always_on') is True
    }


def _glob_matched_domains(user_domains: dict[str, Any], file_signal: set[str]) -> set[str]:
    """Return domains whose ``file_globs`` match any path in ``file_signal``."""
    matched: set[str] = set()
    if not file_signal:
        return matched
    for domain, cfg in user_domains.items():
        if not isinstance(cfg, dict):
            continue
        globs = cfg.get('file_globs')
        if not isinstance(globs, list):
            continue
        for glob in globs:
            if not isinstance(glob, str) or not glob:
                continue
            pattern = _glob_to_regex(glob)
            if any(pattern.match(path) for path in file_signal):
                matched.add(domain)
                break
    return matched


def _result(
    plan_id: str,
    *,
    domains: set[str],
    candidates: list[dict[str, Any]],
    always_on: set[str],
    glob_matched: set[str],
    ambiguous: bool,
    source: str | None,
    reason: str,
) -> dict[str, Any]:
    """Compose the success result in the SET return contract."""
    return {
        'status': 'success',
        'plan_id': plan_id,
        'domains': sorted(domains),
        'candidates': candidates,
        'always_on': sorted(always_on),
        'glob_matched': sorted(glob_matched),
        'ambiguous': ambiguous,
        'source': source,
        'reason': reason,
    }


def cmd_domain_detect(args) -> dict[str, Any]:
    """Run the deterministic domain detector for a plan.

    Returns the SET contract ``{domains, candidates, always_on, glob_matched,
    ambiguous, source, reason}``. The caller (phase-1-init Step 7 /
    phase-2-refine) unions ``domains`` into ``references.domains`` and uses
    ``ambiguous`` to decide whether to raise a multiSelect ``AskUserQuestion``
    over ``candidates``; no LLM dispatch fallback applies on this code path.
    """
    plan_id: str = args.plan_id
    override: str | None = getattr(args, 'domain_override', None)
    affected_files_raw: str | None = getattr(args, 'affected_files', None)

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
        return _result(
            plan_id,
            domains=set(),
            candidates=[],
            always_on=set(),
            glob_matched=set(),
            ambiguous=True,
            source=None,
            reason='marshal_not_initialized',
        )

    skill_domains = config.get('skill_domains', {}) if isinstance(config, dict) else {}
    if not isinstance(skill_domains, dict) or not skill_domains:
        return _result(
            plan_id,
            domains=set(),
            candidates=[],
            always_on=set(),
            glob_matched=set(),
            ambiguous=True,
            source=None,
            reason='no_skill_domains_configured',
        )

    # Filter out the synthetic ``system`` domain — Step 7 only considers
    # implementation domains.
    user_domains = {k: v for k, v in skill_domains.items() if k != 'system'}
    if not user_domains:
        return _result(
            plan_id,
            domains=set(),
            candidates=[],
            always_on=set(),
            glob_matched=set(),
            ambiguous=True,
            source=None,
            reason='no_user_domains',
        )

    # Resolve the file signal for the glob leg once: explicit --affected-files at
    # refine, else path-like tokens from the narrative at init.
    narrative, narrative_source = _load_narrative(plan_id)
    if affected_files_raw:
        file_signal = {p.strip() for p in affected_files_raw.split(',') if p.strip()}
    else:
        file_signal = _extract_narrative_paths(narrative)

    # The always_on / glob legs are unconditional — computed once and unioned
    # into every branch's detector result below.
    always_on_set = _always_on_domains(user_domains)
    glob_matched_set = _glob_matched_domains(user_domains, file_signal)
    inclusion_union = always_on_set | glob_matched_set

    # Explicit override resolves the detector leg immediately.
    if override and override in user_domains:
        return _result(
            plan_id,
            domains={override} | inclusion_union,
            candidates=[{'domain': override, 'matched_aliases': []}],
            always_on=always_on_set,
            glob_matched=glob_matched_set,
            ambiguous=False,
            source='cli_override',
            reason='explicit_override',
        )

    # Single-domain auto-select (Step 7 rule 1).
    if len(user_domains) == 1:
        only = next(iter(user_domains))
        return _result(
            plan_id,
            domains={only} | inclusion_union,
            candidates=[{'domain': only, 'matched_aliases': []}],
            always_on=always_on_set,
            glob_matched=glob_matched_set,
            ambiguous=False,
            source='single_domain_configured',
            reason='auto_select',
        )

    # Narrative scan — keep ALL matches (the SET contract), not a single winner.
    tokens = _tokenize(narrative)
    candidates: list[dict[str, Any]] = []
    for domain, domain_config in user_domains.items():
        if not isinstance(domain_config, dict):
            continue
        aliases = _collect_aliases(domain, domain_config)
        matched = sorted(aliases & tokens)
        if matched:
            candidates.append({'domain': domain, 'matched_aliases': matched})

    detector_set = {c['domain'] for c in candidates}

    if len(candidates) == 1:
        return _result(
            plan_id,
            domains=detector_set | inclusion_union,
            candidates=candidates,
            always_on=always_on_set,
            glob_matched=glob_matched_set,
            ambiguous=False,
            source=narrative_source,
            reason='unambiguous_narrative_match',
        )

    if len(candidates) > 1:
        return _result(
            plan_id,
            domains=detector_set | inclusion_union,
            candidates=candidates,
            always_on=always_on_set,
            glob_matched=glob_matched_set,
            ambiguous=True,
            source=narrative_source,
            reason='multiple_narrative_matches',
        )

    # Zero narrative match. When the always_on / glob legs contribute any domain
    # the plan resolves silently; otherwise it is genuinely ambiguous and the
    # configured non-system domains are surfaced as the multiSelect candidate set.
    if inclusion_union:
        return _result(
            plan_id,
            domains=inclusion_union,
            candidates=[],
            always_on=always_on_set,
            glob_matched=glob_matched_set,
            ambiguous=False,
            source=narrative_source,
            reason='inclusion_only_resolve',
        )

    prompt_candidates = [{'domain': d, 'matched_aliases': []} for d in sorted(user_domains)]
    return _result(
        plan_id,
        domains=set(),
        candidates=prompt_candidates,
        always_on=always_on_set,
        glob_matched=glob_matched_set,
        ambiguous=True,
        source=narrative_source,
        reason='no_narrative_match',
    )

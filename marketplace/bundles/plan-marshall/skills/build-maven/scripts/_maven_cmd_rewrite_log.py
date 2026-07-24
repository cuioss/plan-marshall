#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Additive OpenRewrite log-parse consumption for the Maven build output flow.

Signal B of the two-signal OpenRewrite model (see the domain-owned parser
``pm-dev-java-cui:parse-rewrite-log``). This core-side consumer reads the
captured Maven build log and folds the #118 structured WARN findings into
build-maven's output WITHOUT duplicating the WARN format — the format is owned
by the domain, and core reaches it only through the ``rewrite-log-parse`` domain
verb (resolved null-on-absent). See
``../../extension-api/standards/ext-point-domain-verb.md`` § Declaration for the
domain-verb resolution/dispatch contract — it is NOT re-copied here.

Fail-closed contract (ADR-009): a build that never reached ``rewrite:run`` is
NOT reported as ``clean``. Absence-of-evidence is a distinct third state
(``not_observed``), never a vacuous positive. A non-java-cui project (the verb
resolves to null) is likewise a first-class skip (``domain_inactive``), not a
false clean.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# Direct imports - executor sets up PYTHONPATH for cross-skill imports
from _build_parse import read_log_text

#: The domain-verb type this consumer resolves null-on-absent.
VERB_TYPE = 'rewrite-log-parse'

#: The four fail-closed verdicts. ``observed`` is the only state carrying
#: findings; ``not_observed``, ``domain_inactive``, and ``parse_error`` are
#: distinct non-clean states, never a vacuous "clean".
VERDICT_OBSERVED = 'observed'
VERDICT_NOT_OBSERVED = 'not_observed'
VERDICT_DOMAIN_INACTIVE = 'domain_inactive'
#: The dispatched parser failed (executor not found / output unparseable / not an
#: object) — findings could not be observed this run, so fail closed rather than
#: report a false ``observed`` with zero findings (ADR-009).
VERDICT_PARSE_ERROR = 'parse_error'

# Detects that the build reached the rewrite-maven-plugin ``run`` goal. Anchored
# on the Maven goal-EXECUTION banner — the ``--- `` goal opener before the plugin
# coordinate AND the ``(`` execution-id immediately after ``:run`` — so it fires
# ONLY on a real goal execution, never on advisory dryRun prose (``mvn
# rewrite:run``, backtick-quoted, "Run 'mvn rewrite:run' to apply") which carries
# neither the banner opener nor the execution-id. Matches both the fully-qualified
# form ``[INFO] --- rewrite-maven-plugin:5.42.0:run (default-cli) @ app ---`` and
# the short prefix form ``[INFO] --- rewrite:run (default-cli) @ app ---``.
REWRITE_RUN_PATTERN = re.compile(r'---\s+rewrite(?:-maven-plugin:[\w.\-]+)?:run\s+\(')


def reached_rewrite_run(log_text: str) -> bool:
    """Return True when the build log shows the rewrite-maven-plugin run goal executing."""
    return REWRITE_RUN_PATTERN.search(log_text) is not None


def resolve_domain_verb(verb_type: str = VERB_TYPE) -> str | None:
    """Resolve the notation for ``verb_type`` across configured domains, null-on-absent.

    Iterates the configured ``skill_domains`` and returns the first domain's
    ``workflow_skill_extensions[verb_type]`` notation. Core is domain-agnostic —
    it asks "which active domain provides this verb", not "does java-cui provide
    it" — so no domain key is hard-coded here. Returns ``None`` when marshal.json
    is absent/unreadable or no configured domain declares the verb (the
    null-on-absent degrade, ADR-010).

    Args:
        verb_type: The domain-verb type to resolve (default: ``rewrite-log-parse``).

    Returns:
        The resolvable ``bundle:skill`` notation, or ``None`` when no active
        domain provides the verb.
    """
    from file_ops import get_marshal_path, read_json

    marshal_path = get_marshal_path()
    if not marshal_path.exists():
        return None
    try:
        data = read_json(marshal_path, default={})
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    skill_domains = data.get('skill_domains', {})
    if not isinstance(skill_domains, dict):
        return None
    for domain_config in skill_domains.values():
        if not isinstance(domain_config, dict):
            continue
        extensions = domain_config.get('workflow_skill_extensions', {})
        if isinstance(extensions, dict):
            notation = extensions.get(verb_type)
            if notation:
                return str(notation)
    return None


def _find_executor() -> Path | None:
    """Locate the ``.plan/execute-script.py`` proxy by walking up from cwd."""
    for base in [Path.cwd(), *Path.cwd().parents]:
        candidate = base / '.plan' / 'execute-script.py'
        if candidate.is_file():
            return candidate
    return None


def dispatch_parser(notation: str, log_file: str) -> dict:
    """Dispatch the resolved parser verb against ``log_file`` via the executor proxy.

    The domain-owned script is reached only through the executor proxy — core
    never statically imports the domain bundle (the reverse dependency the
    domain-verb seam exists to break). The 2-part ``bundle:skill`` notation is
    expanded to the 3-part script notation by deriving the entry-point script
    name from the skill name (hyphens → underscores), matching the executor's
    ``{bundle}:{skill}:{script}`` convention.

    Args:
        notation: The resolved ``bundle:skill`` domain-verb notation.
        log_file: Path to the captured Maven build log.

    Returns:
        The parser's parsed JSON result dict, or a ``status: error`` dict when
        the executor cannot be located or the parser produced no parseable JSON.
    """
    # Notation must be a ``bundle:skill`` pair with a non-empty skill segment; a
    # colonless/empty notation is fail-closed here, never a ValueError crash.
    if ':' not in notation:
        return {'status': 'error', 'error': 'malformed_notation'}
    skill = notation.split(':', 1)[1]
    if not skill:
        return {'status': 'error', 'error': 'malformed_notation'}
    script = skill.replace('-', '_')
    full_notation = f'{notation}:{script}'
    executor = _find_executor()
    if executor is None:
        return {'status': 'error', 'error': 'executor_not_found'}
    # argv is a FIXED list of resolved values (no shell, notation validated above);
    # subprocess.run receives a list, so there is no OS-command-injection surface.
    proc = subprocess.run(
        [sys.executable, str(executor), full_notation, 'parse', '--log-file', log_file, '--format', 'json'],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        parsed = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {'status': 'error', 'error': 'parser_output_unparseable', 'stderr': proc.stderr}
    if not isinstance(parsed, dict):
        return {'status': 'error', 'error': 'parser_output_not_object'}
    return parsed


def consume_rewrite_log(log_file: str, *, resolve_verb=resolve_domain_verb, dispatch=dispatch_parser) -> dict:
    """Consume the Maven build log's OpenRewrite log-parse signal, fail-closed.

    Branches on the four fail-closed states:

    - The build never reached ``rewrite:run`` → ``not_observed`` (never
      ``clean``; absence-of-evidence is a distinct third state, ADR-009).
    - It reached ``rewrite:run`` but no active domain provides the
      ``rewrite-log-parse`` verb → ``domain_inactive`` (a first-class skip, not
      a false clean).
    - It reached ``rewrite:run``, the verb resolves, but the dispatched parser
      returned an error payload (or a non-dict) → ``parse_error`` (fail closed;
      findings could not be observed, never a false ``observed`` with zero
      findings).
    - It reached ``rewrite:run``, the verb resolves, and dispatch explicitly
      succeeded → surface its structured findings (``observed``).

    ``resolve_verb`` and ``dispatch`` are injectable so the orchestration is
    unit-testable without the real executor / domain parser.

    Args:
        log_file: Path to the captured Maven build log.
        resolve_verb: Callable resolving the verb notation null-on-absent.
        dispatch: Callable dispatching the resolved parser against the log.

    Returns:
        A result dict ``{'status': 'success', 'rewrite_log': {...}}`` carrying
        the ``verdict`` and, for ``observed``, the structured findings and
        newly-detected / pre-existing counts.
    """
    text = read_log_text(log_file)

    if not reached_rewrite_run(text):
        return {
            'status': 'success',
            'rewrite_log': {
                'verdict': VERDICT_NOT_OBSERVED,
                'reason': 'build did not reach rewrite:run — OpenRewrite findings were not produced this run',
                'total_findings': 0,
                'findings': [],
            },
        }

    notation = resolve_verb()
    if not notation:
        return {
            'status': 'success',
            'rewrite_log': {
                'verdict': VERDICT_DOMAIN_INACTIVE,
                'reason': 'no active domain provides the rewrite-log-parse verb — log-parse signal skipped',
                'total_findings': 0,
                'findings': [],
            },
        }

    payload = dispatch(notation, log_file)
    if not isinstance(payload, dict) or payload.get('status') != 'success':
        error = payload.get('error') if isinstance(payload, dict) else 'dispatch_returned_non_dict'
        return {
            'status': 'success',
            'rewrite_log': {
                'verdict': VERDICT_PARSE_ERROR,
                'notation': notation,
                'reason': f'log-parse dispatch failed ({error}) — findings could not be observed this run',
                'total_findings': 0,
                'findings': [],
            },
        }

    data = payload.get('data', {})
    if not isinstance(data, dict):
        data = {}
    findings = data.get('findings', []) or []
    return {
        'status': 'success',
        'rewrite_log': {
            'verdict': VERDICT_OBSERVED,
            'notation': notation,
            'total_findings': len(findings),
            'newly_detected_count': data.get('newly_detected_count', 0),
            'pre_existing_count': data.get('pre_existing_count', 0),
            'findings': findings,
        },
    }

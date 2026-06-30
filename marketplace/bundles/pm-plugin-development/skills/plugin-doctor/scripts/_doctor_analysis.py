#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Analysis functions for doctor-marketplace.

Every rule emitted from this module must have a corresponding row in
``references/rule-provenance.md``. New rule emitters require a paired
provenance entry (rule ID, class, source citation) before merge. See the
provenance contract in ``references/rule-provenance.md`` § "Provenance
contract for new rules" and the audit history at the bottom of that file.
"""

import ast
import re
from pathlib import Path
from typing import Any

# Import from analyze.py
from _analyze import (
    analyze_markdown_file,
    analyze_skill_structure,
    analyze_tool_coverage,
    analyze_verb_chains,
)
from _analyze_manage_findings_invocation import scan_skill_for_manage_findings_invocation
from _analyze_markdown import (
    check_broken_relative_link,
    check_checklist_patterns,
    check_display_detail_violations,
    check_fenced_code_no_language,
    check_forbidden_metadata,
    check_resolver_gap,
    get_bloat_classification,
)
from _analyze_notation_staleness import analyze_notation_staleness
from _analyze_phase2_refine_contract import analyze_phase2_refine_contract
from _analyze_shared import check_agent_glob_resolver_workaround
from _dep_detection import extract_frontmatter  # type: ignore[import-not-found]
from _dep_index import AstCache  # type: ignore[import-not-found]
from _doctor_shared import Finding  # type: ignore[import-not-found]

# Subdirectories that may contain markdown sub-documents
SUBDOC_DIRS = ['references', 'standards', 'workflow', 'templates']

# Regex that validates a ``quality.file-bloat`` ack tag value.
# An ack tag must start with ``ack-`` followed by at least one
# lowercase alphanumeric-or-hyphen character, providing a human-readable
# rationale slug (e.g. ``ack-validator-registry``).
_ACK_TAG_RE = re.compile(r'^ack-[a-z0-9_-]+$')

# Constructors whose calls must include allow_abbrev=False to prevent prefix
# matching of retired flags. See rule-catalog.md (argparse_safety).
_ARGPARSE_SAFETY_CONSTRUCTORS = ('ArgumentParser', 'add_parser')


def _read_file_bloat_ack_tag(content: str) -> str | None:
    """Extract the rationale slug from a ``quality.file-bloat`` frontmatter ack.

    Reads the raw YAML text returned by ``extract_frontmatter`` and looks for
    a ``quality`` block containing a ``file-bloat`` key.  When the value
    matches ``ack-<rationale-slug>``, returns the rationale slug without the
    ``ack-`` prefix (e.g. ``'validator-registry'``).  Returns ``None`` when
    the key is missing or the value does not match the expected shape.

    Supported YAML shapes::

        quality:
          file-bloat: ack-rationale-slug

    or inline (not standard but tolerated)::

        quality.file-bloat: ack-rationale-slug
    """
    _, frontmatter_text, _ = extract_frontmatter(content)
    if not frontmatter_text:
        return None

    # Match nested form: under a `quality:` block, a `file-bloat: value` line.
    nested_match = re.search(
        r'^quality\s*:\s*\n(?:[ \t]+\S.*\n)*?[ \t]+file-bloat\s*:\s*(.+)',
        frontmatter_text,
        re.MULTILINE,
    )
    if nested_match:
        value = nested_match.group(1).strip().strip('"\'')
        if _ACK_TAG_RE.match(value):
            return value[len('ack-'):]
        return None

    # Match dotted inline form: quality.file-bloat: value
    inline_match = re.search(
        r'^quality\.file-bloat\s*:\s*(.+)',
        frontmatter_text,
        re.MULTILINE,
    )
    if inline_match:
        value = inline_match.group(1).strip().strip('"\'')
        if _ACK_TAG_RE.match(value):
            return value[len('ack-'):]

    return None


def _has_file_bloat_ack(content: str) -> tuple[bool, str | None]:
    """Return ``(ack_present, ack_tag)`` for a markdown file content string.

    Returns ``(True, '<tag>')`` when a valid ``quality.file-bloat: ack-*``
    frontmatter key is present, or ``(False, None)`` otherwise.
    """
    tag = _read_file_bloat_ack_tag(content)
    return (tag is not None, tag)


def analyze_component(component: dict, active_rules: frozenset[str] | None = None) -> dict:
    """Analyze a single component and return issues.

    Per-component invariants (markdown, coverage, structure, subdoc, etc.) run
    unconditionally. Opt-in rule clusters surfaced via ``--rules`` on
    ``cmd_analyze`` are gated on ``active_rules``:

    - ``verb_chain``: skip ``analyze_verb_chains`` unless the caller opts in.

    The default ``active_rules=None`` is treated as the empty set, keeping
    behaviour for callers that have not yet propagated the opt-in flag
    (``cmd_fix`` and ``cmd_report``) consistent with ``cmd_analyze`` running
    without ``--rules``.
    """
    if active_rules is None:
        active_rules = frozenset()
    component_type = component.get('type')
    path = component.get('path')

    issues: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}

    if component_type in ('agent', 'command'):
        # Markdown analysis
        if path is not None:
            file_path = Path(path)
            if file_path.exists():
                md_analysis = analyze_markdown_file(file_path, component_type)
                analysis['markdown'] = md_analysis

                # Extract issues from analysis
                issues.extend(extract_issues_from_markdown_analysis(md_analysis, str(path), component_type))

                # Tool coverage analysis
                coverage = analyze_tool_coverage(file_path)
                if 'error' not in coverage:
                    analysis['coverage'] = coverage
                    issues.extend(extract_issues_from_coverage_analysis(coverage, str(path), component_type))

                # agent-glob-resolver-workaround: agents that declare Glob in
                # tools without `forwards_tool_capabilities: true` in their
                # YAML frontmatter.
                if component_type == 'agent':
                    try:
                        agent_content = file_path.read_text(encoding='utf-8', errors='replace')
                    except OSError:
                        agent_content = ''
                    for finding in check_agent_glob_resolver_workaround(str(path), agent_content):
                        issues.append(
                            Finding(
                                type='agent-glob-resolver-workaround',
                                file=str(path),
                                line=finding.get('line'),
                                severity='error',
                                fixable=False,
                                rule_id='agent-glob-resolver-workaround',
                                description=finding.get(
                                    'message',
                                    'Agent declares Glob without `forwards_tool_capabilities: true` '
                                    'frontmatter flag (agent-glob-resolver-workaround)',
                                ),
                                details=finding,
                            ).to_dict()
                        )

    elif component_type == 'skill':
        if path is None:
            return {'component': component, 'analysis': analysis, 'issues': issues, 'issue_count': len(issues)}
        skill_dir = Path(path)
        skill_md_path = component.get('skill_md_path')

        # Structure analysis
        structure = analyze_skill_structure(skill_dir)
        analysis['structure'] = structure

        # Skill naming convention: forbid noun-suffix directory names
        noun_suffix = structure.get('noun_suffix', {})
        if noun_suffix.get('violation'):
            directory_name = noun_suffix.get('directory_name', skill_dir.name)
            suffix = noun_suffix.get('suffix', '')
            issues.append(
                Finding(
                    type='skill-naming-noun-suffix',
                    file=str(skill_dir),
                    severity='warning',
                    fixable=False,
                    description=(
                        f'Skill directory name `{directory_name}` ends with reserved noun suffix '
                        f'`{suffix}` — use a verb-first name (skill-naming-noun-suffix)'
                    ),
                    details=noun_suffix,
                ).to_dict()
            )

        # Markdown analysis of SKILL.md
        if skill_md_path:
            md_path = Path(skill_md_path)
            if md_path.exists():
                md_analysis = analyze_markdown_file(md_path, 'skill')
                analysis['markdown'] = md_analysis
                issues.extend(extract_issues_from_markdown_analysis(md_analysis, skill_md_path, 'skill'))

                # Tool coverage analysis for skills
                coverage = analyze_tool_coverage(md_path)
                if 'error' not in coverage:
                    analysis['coverage'] = coverage
                    issues.extend(extract_issues_from_coverage_analysis(coverage, skill_md_path, 'skill'))

        # Sub-document analysis (references/, standards/, workflow/, templates/)
        subdoc_results = analyze_subdocuments(skill_dir)
        if subdoc_results:
            analysis['subdocuments'] = subdoc_results
            issues.extend(extract_issues_from_subdoc_analysis(subdoc_results, str(skill_dir)))

        # Prose verb-chain consistency scan (AST-based, per-skill scope).
        # Mirrors the argparse_safety integration pattern: lightweight static
        # analyzer whose findings merge into the main issue stream as
        # unfixable error-severity entries.
        #
        # Gated by ``active_rules`` to keep the registry/dispatch contract
        # consistent: ``verb_chain`` is registered in
        # ``_OPTIN_RULE_NAMES`` with a ``--enable-verb-chain`` alias and
        # ``--rules verb_chain`` token, so the scan only runs when the caller
        # opts in via either path. Absence keeps the cluster silent (no
        # findings) — matching the documented opt-in semantics.
        if 'verb_chain' in active_rules:
            issues.extend(analyze_verb_chains(skill_dir))

        # manage-findings-invocation-invalid: catch invalid manage-findings
        # invocation shapes (snake_case script position, invalid top-level
        # subcommands like ``list-qgate``, invalid ``qgate``/``assessment``
        # sub-verbs). Gated on ``active_rules`` mirroring the ``verb_chain``
        # opt-in semantics so the analyzer only runs when the caller opts in.
        if 'manage-findings-invocation-invalid' in active_rules:
            issues.extend(scan_skill_for_manage_findings_invocation(skill_dir))

        # refine-contract-violation: catch Edit/Write tool references in
        # phase-2-refine workflow files whose path argument is not prefixed
        # with .plan/local/ (or its worktree-substituted forms). The analyzer
        # self-filters to phase-2-refine/ files via path matching, so
        # registration at the broader ``skills`` scope is correct: invoking
        # plugin-doctor on a non-refine skill produces no findings because
        # the analyzer's _is_refine_workflow_file predicate excludes them.
        # Unconditionally active (not gated on active_rules) — the rule
        # enforces a hard refine-contract requirement that must surface on
        # every plugin-doctor run.
        issues.extend(analyze_phase2_refine_contract([skill_dir]))

        # notation-staleness: catch three-part executor notations whose third
        # segment has no matching {script}.py file under the resolved
        # bundles/{bundle}/skills/{skill}/scripts/ directory. A renamed
        # entrypoint script silently changes its public notation, so callers
        # that still use the old form resolve to `Unknown notation`.
        # Unconditionally active (not gated on active_rules) — the rule
        # guards against a half-done entrypoint rename (which silently breaks
        # the script's public notation) that must surface on every
        # plugin-doctor run.
        issues.extend(analyze_notation_staleness([skill_dir]))

    return {'component': component, 'analysis': analysis, 'issues': issues, 'issue_count': len(issues)}


def extract_issues_from_markdown_analysis(analysis: dict, file_path: str, component_type: str) -> list[dict]:
    """Extract fixable issues from markdown analysis."""
    issues = []

    # Check frontmatter
    fm = analysis.get('frontmatter', {})
    if not fm.get('present'):
        issues.append(Finding(type='missing-frontmatter', file=file_path, severity='error', fixable=True).to_dict())
    elif not fm.get('yaml_valid'):
        issues.append(Finding(type='invalid-yaml', file=file_path, severity='error', fixable=True).to_dict())
    else:
        required = fm.get('required_fields', {})
        if not required.get('name', {}).get('present'):
            issues.append(Finding(type='missing-name-field', file=file_path, severity='error', fixable=True).to_dict())
        if not required.get('description', {}).get('present'):
            issues.append(
                Finding(type='missing-description-field', file=file_path, severity='warning', fixable=True).to_dict()
            )
        if component_type in ('agent', 'command') and not required.get('tools', {}).get('present'):
            issues.append(
                Finding(type='missing-tools-field', file=file_path, severity='warning', fixable=True).to_dict()
            )

        # Skill-specific field checks
        if component_type == 'skill':
            user_inv = required.get('user_invocable', {})
            # Check for misspelled user-invokable (should be user-invocable)
            if user_inv.get('misspelled') and not user_inv.get('present'):
                issues.append(
                    Finding(
                        type='misspelled-user-invocable',
                        file=file_path,
                        severity='warning',
                        fixable=True,
                        description='Skill uses `user-invokable` (misspelled) — should be `user-invocable`',
                    ).to_dict()
                )
            # Check for missing user-invocable entirely
            elif not user_inv.get('present') and not user_inv.get('misspelled'):
                issues.append(
                    Finding(
                        type='missing-user-invocable',
                        file=file_path,
                        severity='warning',
                        fixable=True,
                        description='Skill missing required `user-invocable` field',
                    ).to_dict()
                )

            # Check for invokable value vs content-mode mismatch
            content_mode = analysis.get('content_mode', {})
            if user_inv.get('present') and user_inv.get('value') is True and content_mode.get('is_reference'):
                issues.append(
                    Finding(
                        type='skill-invokable-mismatch',
                        file=file_path,
                        severity='warning',
                        fixable=True,
                        description='Skill declares REFERENCE MODE but has `user-invocable: true` — reference skills should be `false`',
                    ).to_dict()
                )

    # Check rule violations
    rules = analysis.get('rules', {})
    if rules.get('agent_task_tool_prohibited'):
        issues.append(
            Finding(
                type='agent-task-tool-prohibited',
                file=file_path,
                severity='warning',
                fixable=True,
                description='Agent declares Task tool (agent-task-tool-prohibited)',
            ).to_dict()
        )
    if rules.get('agent_maven_restricted'):
        issues.append(
            Finding(
                type='agent-maven-restricted',
                file=file_path,
                severity='warning',
                fixable=False,
                description='Direct Maven usage outside builder (agent-maven-restricted)',
            ).to_dict()
        )
    if rules.get('workflow_hardcoded_script_path'):
        issues.append(
            Finding(
                type='workflow-hardcoded-script-path',
                file=file_path,
                severity='warning',
                fixable=False,
                description='Hardcoded script path - use executor notation instead (workflow-hardcoded-script-path)',
            ).to_dict()
        )
    if rules.get('agent_skill_tool_visibility'):
        issues.append(
            Finding(
                type='agent-skill-tool-visibility',
                file=file_path,
                severity='warning',
                fixable=True,
                description='Agent tools missing Skill — invisible to Task dispatcher (agent-skill-tool-visibility)',
            ).to_dict()
        )
    for violation in rules.get('workflow_prose_param_violations', []):
        issues.append(
            Finding(
                type='workflow-prose-parameter-inconsistency',
                file=file_path,
                severity='warning',
                fixable=False,
                description=f'Prose-parameter inconsistency: {violation.get("issue", "")}',
                details=violation,
            ).to_dict()
        )

    # mark-step-done argument validation (phase-6-finalize finalize step termination)
    _mark_step_done_descriptions = {
        'MARK_STEP_DONE_STALE_NOTATION': (
            'mark-step-done invocation uses stale underscored notation '
            '`manage-status:manage_status` instead of `manage-status:manage-status`'
        ),
        'MARK_STEP_DONE_MISSING_PHASE': 'mark-step-done invocation is missing required `--phase` argument',
        'MARK_STEP_DONE_MISSING_OUTCOME': 'mark-step-done invocation is missing required `--outcome` argument',
    }
    for violation in rules.get('mark_step_done_violations', []):
        code = violation.get('code', '')
        issues.append(
            Finding(
                type=code,
                file=file_path,
                line=violation.get('line'),
                severity='error',
                fixable=False,
                description=_mark_step_done_descriptions.get(code, f'mark-step-done defect: {code}'),
                details=violation,
            ).to_dict()
        )

    # skill-resolver-gap (warning) — LLM-Glob discovery prose without an
    # adjacent resolver call. Driven by the analyzer in _analyze_markdown.py,
    # surfaced here as standard issue dicts.
    for violation in rules.get('resolver_gap_violations', []):
        issues.append(
            Finding(
                type='skill-resolver-gap',
                file=file_path,
                line=violation.get('line'),
                severity='warning',
                fixable=False,
                rule_id='skill-resolver-gap',
                description=violation.get(
                    'message',
                    'LLM-Glob discovery prose without adjacent resolver call (skill-resolver-gap)',
                ),
                details=violation,
            ).to_dict()
        )

    # --display-detail ASCII contract validation (phase-6-finalize finalize renderer)
    _display_detail_descriptions = {
        'DISPLAY_DETAIL_NON_ASCII': '--display-detail value contains non-ASCII characters (chars > 0x7F)',
        'DISPLAY_DETAIL_TOO_LONG': '--display-detail value exceeds 80 characters',
        'DISPLAY_DETAIL_MULTILINE': '--display-detail value contains a newline (must be single-line)',
        'DISPLAY_DETAIL_TRAILING_PERIOD': '--display-detail value ends with a trailing period',
    }
    for violation in rules.get('display_detail_violations', []):
        code = violation.get('code', '')
        value = violation.get('value', '')
        base_desc = _display_detail_descriptions.get(code, f'--display-detail defect: {code}')
        issues.append(
            Finding(
                type=code,
                file=file_path,
                line=violation.get('line'),
                severity='error',
                fixable=False,
                description=f'{base_desc}: "{value}"',
                details=violation,
            ).to_dict()
        )

    # hardcoded-model-on-canonical (agent-only rule introduced by role-variants plan)
    for violation in rules.get('hardcoded_model_on_canonical_violations', []):
        issues.append(
            Finding(
                type='HARDCODED_MODEL_ON_CANONICAL',
                file=file_path,
                severity='error',
                fixable=False,
                description=violation.get('message', 'hardcoded-model-on-canonical violation'),
                details=violation,
                extra={'branch': violation.get('branch')},
            ).to_dict()
        )

    # broken-relative-link (error) — a relative markdown link whose target is
    # missing on disk. Driven by the analyzer in _analyze_markdown.py.
    for violation in rules.get('broken_relative_link_violations', []):
        issues.append(
            Finding(
                type='broken-relative-link',
                file=file_path,
                line=violation.get('line'),
                severity='error',
                fixable=False,
                rule_id='broken-relative-link',
                description=violation.get(
                    'message', 'relative link target does not resolve on disk (broken-relative-link)'
                ),
                details=violation,
            ).to_dict()
        )

    # fenced-code-no-language (warning) — a fenced code block opened without an
    # info-string (MD040). Driven by the analyzer in _analyze_markdown.py.
    for violation in rules.get('fenced_code_no_language_violations', []):
        issues.append(
            Finding(
                type='fenced-code-no-language',
                file=file_path,
                line=violation.get('line'),
                severity='warning',
                fixable=True,
                rule_id='fenced-code-no-language',
                description=violation.get(
                    'message', 'fenced code block opens with no language info-string (fenced-code-no-language)'
                ),
                details=violation,
            ).to_dict()
        )

    # Check CI rule
    ci = analysis.get('continuous_improvement_rule', {})
    if ci.get('format', {}).get('agent_lessons_via_skill'):
        issues.append(
            Finding(
                type='agent-lessons-via-skill',
                file=file_path,
                severity='warning',
                fixable=True,
                description='Agent uses self-update pattern (agent-lessons-via-skill)',
            ).to_dict()
        )

    # Check bloat — suppressed when the file carries a valid file-bloat ack tag.
    bloat = analysis.get('bloat', {}).get('classification', 'NORMAL')
    if bloat in ('CRITICAL', 'BLOATED'):
        # Read raw file content to inspect frontmatter for an ack tag.
        try:
            _raw_content = Path(file_path).read_text(encoding='utf-8', errors='replace')
        except OSError:
            _raw_content = ''
        _ack_present, _ack_tag = _has_file_bloat_ack(_raw_content)
        if not _ack_present:
            issues.append(
                Finding(
                    type='file-bloat',
                    file=file_path,
                    severity='warning' if bloat == 'BLOATED' else 'error',
                    fixable=False,
                    extra={
                        'classification': bloat,
                        'line_count': analysis.get('metrics', {}).get('line_count', 0),
                    },
                ).to_dict()
            )
        else:
            # Ack present — surface the tag in the analysis output for audit.
            analysis.setdefault('bloat_ack_tag', _ack_tag)

    # Check checklist patterns
    checklists = analysis.get('checklist_patterns', {})
    if checklists.get('has_checklists'):
        issues.append(
            Finding(
                type='checklist-pattern',
                file=file_path,
                severity='warning',
                fixable=True,
                description=f'Checkbox patterns in LLM-consumed file ({checklists["count"]} items)',
                extra={
                    'count': checklists['count'],
                    'sections': checklists.get('sections', []),
                },
            ).to_dict()
        )

    return issues


def extract_issues_from_coverage_analysis(coverage: dict, file_path: str, component_type: str = '') -> list[dict]:
    """Extract deterministic issues from tool coverage analysis.

    NOTE: This function extracts issues that can be determined structurally:
    - agent-task-tool-prohibited (Task declared in agent frontmatter)
    - agent-maven-restricted (Maven calls outside builder)
    - Backup file patterns (quality issue)

    Tool usage analysis (missing/unused) is NOT done here - that requires
    semantic understanding and runs in-line inside the `verification-feedback`
    dispatch (producer=plugin-doctor) when its scope covers tool-coverage.
    """
    issues = []

    # Only extract deterministic violations
    violations = coverage.get('critical_violations', {})

    # agent-task-tool-prohibited: Agent declares Task tool (deterministic - check frontmatter only)
    if component_type == 'agent' and violations.get('has_task_declared'):
        issues.append(
            Finding(
                type='agent-task-tool-prohibited',
                file=file_path,
                severity='warning',
                fixable=True,
                description='Agent declares Task tool (agent-task-tool-prohibited)',
            ).to_dict()
        )

    # agent-maven-restricted: Maven calls outside builder (only flag if not in builder bundle)
    maven_calls = violations.get('maven_calls', [])
    if maven_calls and 'builder' not in file_path:
        issues.append(
            Finding(
                type='agent-maven-restricted',
                file=file_path,
                severity='warning',
                fixable=False,
                description=f'Direct Maven usage (agent-maven-restricted) - {len(maven_calls)} call(s)',
                details={'maven_calls': maven_calls},
            ).to_dict()
        )

    # Backup file patterns (quality issue)
    backup_patterns = violations.get('backup_file_patterns', [])
    if backup_patterns:
        issues.append(
            Finding(
                type='backup-pattern',
                file=file_path,
                severity='info',
                fixable=False,
                description=f'Backup file patterns found - {len(backup_patterns)} occurrence(s)',
                details={'patterns': backup_patterns},
            ).to_dict()
        )

    return issues


def analyze_subdocuments(skill_dir: Path) -> list[dict]:
    """Analyze markdown sub-documents in a skill directory.

    Checks references/, standards/, workflow/, templates/ for:
    - Line count and bloat classification
    - Forbidden metadata sections
    - Hardcoded script paths
    """
    results = []

    for subdir_name in SUBDOC_DIRS:
        subdir = skill_dir / subdir_name
        if not subdir.is_dir():
            continue

        for md_file in sorted(subdir.glob('*.md')):
            try:
                content = md_file.read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue

            line_count = content.count('\n') + (1 if content and not content.endswith('\n') else 0)
            bloat_class = get_bloat_classification(line_count, 'subdoc')
            has_forbidden, forbidden_sections = check_forbidden_metadata(content)

            entry: dict = {
                'path': str(md_file),
                'relative_path': f'{subdir_name}/{md_file.name}',
                'line_count': line_count,
                'bloat': bloat_class,
            }

            issues: list[dict] = []
            if bloat_class in ('CRITICAL', 'BLOATED'):
                # Suppress when the subdoc has a valid file-bloat ack tag.
                _subdoc_ack_present, _subdoc_ack_tag = _has_file_bloat_ack(content)
                if not _subdoc_ack_present:
                    issues.append(
                        {
                            'type': 'subdoc-bloat',
                            'classification': bloat_class,
                            'line_count': line_count,
                        }
                    )
                else:
                    entry['bloat_ack_tag'] = _subdoc_ack_tag
            if has_forbidden:
                issues.append(
                    {
                        'type': 'subdoc-forbidden-metadata',
                        'sections': forbidden_sections,
                    }
                )

            # Hardcoded script paths
            if re.search(r'python3 .*/scripts/|bash .*/scripts/|\{[^}]+\}/scripts/', content):
                if not re.search(r'Skill:.*script-runner', content):
                    issues.append(
                        {
                            'type': 'subdoc-hardcoded-script-path',
                        }
                    )

            # Checklist patterns
            checklist_info = check_checklist_patterns(content, str(md_file))
            if checklist_info['has_checklists']:
                issues.append(
                    {
                        'type': 'subdoc-checklist-pattern',
                        'count': checklist_info['count'],
                        'sections': checklist_info.get('sections', []),
                    }
                )

            # skill-resolver-gap: LLM-Glob discovery prose without adjacent
            # resolver call. Restricted to standards/*.md per rule scope.
            if subdir_name == 'standards':
                resolver_gap_findings = check_resolver_gap(content, str(md_file))
                for finding in resolver_gap_findings:
                    issues.append(
                        {
                            'type': 'skill-resolver-gap',
                            'line': finding.get('line'),
                            'message': finding.get('message'),
                            'pattern': finding.get('pattern'),
                        }
                    )

            # --display-detail ASCII contract validation (phase-6-finalize finalize renderer)
            for violation in check_display_detail_violations(content):
                issues.append(
                    {
                        'type': 'subdoc-display-detail-violation',
                        'code': violation.get('code'),
                        'line': violation.get('line'),
                        'value': violation.get('value', ''),
                    }
                )

            # broken-relative-link — relative markdown link with no on-disk target.
            for violation in check_broken_relative_link(content, str(md_file)):
                issues.append(
                    {
                        'type': 'broken-relative-link',
                        'line': violation.get('line'),
                        'target': violation.get('target'),
                        'message': violation.get('message'),
                    }
                )

            # fenced-code-no-language — fenced block opened without an info-string.
            for violation in check_fenced_code_no_language(content):
                issues.append(
                    {
                        'type': 'fenced-code-no-language',
                        'line': violation.get('line'),
                        'message': violation.get('message'),
                    }
                )

            if issues:
                entry['issues'] = issues

            results.append(entry)

    return results


def extract_issues_from_subdoc_analysis(subdoc_results: list[dict], skill_path: str) -> list[dict]:
    """Extract issues from sub-document analysis into the component issue list."""
    issues = []

    for subdoc in subdoc_results:
        for issue in subdoc.get('issues', []):
            file_path = subdoc['path']

            if issue['type'] == 'subdoc-bloat':
                issues.append(
                    Finding(
                        type='subdoc-bloat',
                        file=file_path,
                        severity='warning' if issue['classification'] == 'BLOATED' else 'error',
                        fixable=False,
                        description=f'Sub-document bloat ({issue["classification"]}, {issue["line_count"]} lines)',
                        extra={
                            'classification': issue['classification'],
                            'line_count': issue['line_count'],
                        },
                    ).to_dict()
                )
            elif issue['type'] == 'subdoc-forbidden-metadata':
                issues.append(
                    Finding(
                        type='subdoc-forbidden-metadata',
                        file=file_path,
                        severity='warning',
                        fixable=True,
                        description=f'Forbidden metadata sections: {issue["sections"]}',
                    ).to_dict()
                )
            elif issue['type'] == 'subdoc-hardcoded-script-path':
                issues.append(
                    Finding(
                        type='subdoc-hardcoded-script-path',
                        file=file_path,
                        severity='warning',
                        fixable=False,
                        description='Hardcoded script path in sub-document',
                    ).to_dict()
                )
            elif issue['type'] == 'subdoc-checklist-pattern':
                issues.append(
                    Finding(
                        type='subdoc-checklist-pattern',
                        file=file_path,
                        severity='warning',
                        fixable=True,
                        description=f'Checkbox patterns in sub-document ({issue["count"]} items)',
                        extra={
                            'count': issue['count'],
                            'sections': issue.get('sections', []),
                        },
                    ).to_dict()
                )
            elif issue['type'] == 'skill-resolver-gap':
                issues.append(
                    Finding(
                        type='skill-resolver-gap',
                        file=file_path,
                        line=issue.get('line'),
                        severity='warning',
                        fixable=False,
                        rule_id='skill-resolver-gap',
                        description=issue.get(
                            'message',
                            'LLM-Glob discovery prose without adjacent resolver call (skill-resolver-gap)',
                        ),
                        details=issue,
                    ).to_dict()
                )
            elif issue['type'] == 'subdoc-display-detail-violation':
                code = issue.get('code', '')
                value = issue.get('value', '')
                issues.append(
                    Finding(
                        type=code,
                        file=file_path,
                        line=issue.get('line'),
                        severity='error',
                        fixable=False,
                        description=f'display_detail violation ({code}) at line {issue.get("line")}: "{value}"',
                    ).to_dict()
                )
            elif issue['type'] == 'broken-relative-link':
                issues.append(
                    Finding(
                        type='broken-relative-link',
                        file=file_path,
                        line=issue.get('line'),
                        severity='error',
                        fixable=False,
                        rule_id='broken-relative-link',
                        description=issue.get(
                            'message', 'relative link target does not resolve on disk (broken-relative-link)'
                        ),
                        details=issue,
                    ).to_dict()
                )
            elif issue['type'] == 'fenced-code-no-language':
                issues.append(
                    Finding(
                        type='fenced-code-no-language',
                        file=file_path,
                        line=issue.get('line'),
                        severity='warning',
                        fixable=True,
                        rule_id='fenced-code-no-language',
                        description=issue.get(
                            'message',
                            'fenced code block opens with no language info-string (fenced-code-no-language)',
                        ),
                        details=issue,
                    ).to_dict()
                )

    return issues


# =============================================================================
# Markdown-mirror rules (marketplace-wide static check)
# =============================================================================


def analyze_markdown_mirror_rules(marketplace_root: Path) -> list[dict]:
    """Scan every component markdown file for broken-relative-link / fenced-code-no-language.

    Walks ``marketplace_root/*/{skills,agents,commands}/**/*.md`` and runs the
    two markdown-mirror checks (``check_broken_relative_link`` and
    ``check_fenced_code_no_language``) directly on each file. This is a
    dedicated whole-tree helper for the two rules — distinct from the
    per-component ``analyze_component`` path that surfaces the same rules during
    ``analyze``. Both rules are **build-failing**: this helper is invoked by
    ``doctor-marketplace.py::cmd_quality_gate`` so ``broken-relative-link`` and
    ``fenced-code-no-language`` gate every build.

    Each finding is a standard issue dict carrying ``rule_id`` so the gate's
    ``_scoped`` path filter and rule summaries treat it like the other
    marketplace-wide analyzers' findings.
    """
    findings: list[dict] = []
    if not marketplace_root.is_dir():
        return findings
    try:
        bundle_dirs = sorted(marketplace_root.iterdir())
    except OSError:
        return findings
    for bundle_dir in bundle_dirs:
        if not bundle_dir.is_dir():
            continue
        for sub in ('skills', 'agents', 'commands'):
            sub_dir = bundle_dir / sub
            if not sub_dir.is_dir():
                continue
            try:
                md_files = sorted(sub_dir.rglob('*.md'))
            except OSError:
                continue
            for md_file in md_files:
                if not md_file.is_file():
                    continue
                try:
                    content = md_file.read_text(encoding='utf-8', errors='replace')
                except OSError:
                    continue
                file_path = str(md_file)
                # Pass the repo root (``marketplace_root.parent``, the .git-bearing
                # directory) as the containment boundary so the gate's whole-tree
                # pass agrees with the widened per-file boundary in
                # derive_link_boundary. Without this, the explicit marketplace_root
                # argument would override the widening and in-repo cross-tree links
                # (e.g. into doc/) would never be existence-checked.
                for violation in check_broken_relative_link(
                    content, file_path, boundary_dir=marketplace_root.parent
                ):
                    findings.append(
                        Finding(
                            type='broken-relative-link',
                            file=file_path,
                            line=violation.get('line'),
                            severity='error',
                            fixable=False,
                            rule_id='broken-relative-link',
                            description=violation.get('message'),
                            details=violation,
                        ).to_dict()
                    )
                for violation in check_fenced_code_no_language(content):
                    findings.append(
                        Finding(
                            type='fenced-code-no-language',
                            file=file_path,
                            line=violation.get('line'),
                            severity='warning',
                            fixable=True,
                            rule_id='fenced-code-no-language',
                            description=violation.get('message'),
                            details=violation,
                        ).to_dict()
                    )
    return findings


# =============================================================================
# argparse_safety rule (marketplace-wide static check)
# =============================================================================


def _is_test_path(path: Path) -> bool:
    """Return True if the path is a test file or lives under a test directory.

    Matches:
    - Any path component named ``test`` or ``tests``
    - Filenames matching ``test_*.py`` or ``*_test.py``
    """
    name = path.name
    if name.startswith('test_') or name.endswith('_test.py'):
        return True
    for part in path.parts:
        if part in ('test', 'tests'):
            return True
    return False


def _call_has_allow_abbrev_false(node: ast.Call) -> bool:
    """Return True if an ``ast.Call`` includes ``allow_abbrev=False``."""
    for kw in node.keywords:
        if kw.arg != 'allow_abbrev':
            continue
        value = kw.value
        if isinstance(value, ast.Constant) and value.value is False:
            return True
    return False


def _call_func_name(node: ast.Call) -> str | None:
    """Extract the callable's short name from an ``ast.Call``.

    Handles both ``ArgumentParser(...)`` (``ast.Name``) and
    ``argparse.ArgumentParser(...)`` / ``subparsers.add_parser(...)``
    (``ast.Attribute``) call shapes.
    """
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _scan_file_for_argparse_safety(file_path: Path, cache: AstCache | None = None) -> list[dict]:
    """Scan a single Python file for argparse calls missing ``allow_abbrev=False``.

    The AST is sourced from the parse-once ``AstCache`` (the index-substrate AST
    layer) so the file is read and parsed at most once per run. When no cache is
    supplied a fresh one is used for this single file — behaviour is identical;
    the shared-cache path is what the single-pass runner exploits.

    Returns a list of issue dicts (empty if the file has no violations, is
    unreadable, or fails to parse).
    """
    if cache is None:
        cache = AstCache()

    tree = cache.get_tree(file_path)
    if tree is None:
        return []

    issues: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_func_name(node)
        if name not in _ARGPARSE_SAFETY_CONSTRUCTORS:
            continue
        if _call_has_allow_abbrev_false(node):
            continue
        issues.append(
            Finding(
                type='argparse_safety',
                file=str(file_path),
                line=node.lineno,
                severity='error',
                fixable=False,
                description='Add allow_abbrev=False to this argparse call',
                extra={'call': name},
            ).to_dict()
        )
    return issues


def _iter_argparse_safety_targets(marketplace_root: Path) -> list[Path]:
    """Enumerate Python files subject to the argparse_safety rule.

    Scope:
    - ``<marketplace_root>/*/skills/*/scripts/**/*.py`` (marketplace bundle scripts)
    - ``<marketplace_root>/../targets/**/*.py`` (multi-target generator tree)

    Tests (files under ``test/``/``tests/`` directories, or named
    ``test_*.py`` / ``*_test.py``) are excluded — they may intentionally
    exercise argparse default behavior.
    """
    targets: list[Path] = []

    # Marketplace bundle scripts
    if marketplace_root.is_dir():
        for py_file in marketplace_root.glob('*/skills/*/scripts/**/*.py'):
            if py_file.is_file() and not _is_test_path(py_file):
                targets.append(py_file)

    # Targets tree (lives alongside bundles/)
    targets_root = marketplace_root.parent / 'targets'
    if targets_root.is_dir():
        for py_file in targets_root.rglob('*.py'):
            if py_file.is_file() and not _is_test_path(py_file):
                targets.append(py_file)

    return sorted(set(targets))


def scan_argparse_safety(marketplace_root: Path, cache: AstCache | None = None) -> list[dict]:
    """Static-scan the marketplace tree for argparse calls missing
    ``allow_abbrev=False``.

    Each finding is a dict with: ``type=argparse_safety``, ``file``,
    ``line``, ``severity=error``, ``fixable=False``, ``description``, and
    ``call`` (``ArgumentParser`` or ``add_parser``).

    See rule-catalog.md (argparse_safety) for the rationale. The check is a
    lightweight AST walk over the parse-once ``AstCache``. A shared ``cache``
    may be threaded in by the single-pass runner so the scanned files are not
    re-parsed by other AST rules; when omitted, one cache spans this scan.
    """
    if cache is None:
        cache = AstCache()
    findings: list[dict] = []
    for target in _iter_argparse_safety_targets(marketplace_root):
        findings.extend(_scan_file_for_argparse_safety(target, cache))
    return findings

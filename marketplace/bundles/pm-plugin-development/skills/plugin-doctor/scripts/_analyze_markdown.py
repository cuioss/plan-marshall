#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Markdown analysis subcommand."""

import re
from pathlib import Path

from _analyze_shared import (
    check_yaml_validity,
    detect_component_type,
    extract_frontmatter,
    read_frontmatter_disable_list,
)
from _doctor_shared import resolve_runtime_target


def check_frontmatter_fields(frontmatter: str) -> dict:
    """Check required fields in frontmatter."""
    has_name = bool(re.search(r'^name:', frontmatter, re.MULTILINE))
    has_desc = bool(re.search(r'^description:', frontmatter, re.MULTILINE))

    has_tools = False
    tools_field_type = 'none'

    if re.search(r'^tools:', frontmatter, re.MULTILINE):
        has_tools = True
        tools_field_type = 'tools'
    elif re.search(r'^allowed-tools:', frontmatter, re.MULTILINE):
        has_tools = True
        tools_field_type = 'allowed-tools'

    # Check user-invocable field (skills only, correct spelling)
    has_user_invocable = bool(re.search(r'^user-invocable:', frontmatter, re.MULTILINE))
    # Detect misspelled variant (user-invokable with 'k')
    has_user_invocable_misspelled = bool(re.search(r'^user-invokable:', frontmatter, re.MULTILINE))
    # Extract the value (true/false)
    user_invocable_value = None
    invocable_match = re.search(r'^user-invocable:\s*(\S+)', frontmatter, re.MULTILINE)
    if invocable_match:
        user_invocable_value = invocable_match.group(1).strip().lower() == 'true'

    return {
        'name': {'present': has_name},
        'description': {'present': has_desc},
        'tools': {'present': has_tools, 'field_type': tools_field_type},
        'user_invocable': {
            'present': has_user_invocable,
            'misspelled': has_user_invocable_misspelled,
            'value': user_invocable_value,
        },
    }


def check_continuous_improvement(content: str, component_type: str) -> dict:
    """Check CONTINUOUS IMPROVEMENT RULE presence and pattern."""
    ci_present = bool(re.search(r'CONTINUOUS IMPROVEMENT', content, re.IGNORECASE))
    ci_pattern = 'none'
    agent_lessons_via_skill = False

    if ci_present:
        if re.search(r'/plugin-update-command|/plugin-update-agent', content):
            ci_pattern = 'self-update'
        elif re.search(r'REPORT.*improvement|report.*to.*caller', content, re.IGNORECASE):
            ci_pattern = 'caller-reporting'

        if component_type == 'agent' and ci_pattern == 'self-update':
            agent_lessons_via_skill = True

    return {
        'present': ci_present,
        'format': {'pattern': ci_pattern, 'agent_lessons_via_skill': agent_lessons_via_skill},
    }


def get_bloat_classification(line_count: int, component_type: str) -> str:
    """Get bloat classification based on line count and component type."""
    if component_type == 'command':
        if line_count > 200:
            return 'CRITICAL'
        elif line_count > 150:
            return 'BLOATED'
        elif line_count > 100:
            return 'LARGE'
    elif component_type == 'skill':
        if line_count > 1200:
            return 'CRITICAL'
        elif line_count > 800:
            return 'BLOATED'
        elif line_count > 400:
            return 'LARGE'
    elif component_type == 'subdoc':
        if line_count > 800:
            return 'CRITICAL'
        elif line_count > 600:
            return 'BLOATED'
        elif line_count > 400:
            return 'LARGE'
    else:
        if line_count > 800:
            return 'CRITICAL'
        elif line_count > 500:
            return 'BLOATED'
        elif line_count > 300:
            return 'LARGE'

    return 'NORMAL'


def check_execution_patterns(content: str) -> dict:
    """Check for execution patterns in content."""
    return {
        'has_execution_mode': bool(re.search(r'EXECUTION MODE', content, re.IGNORECASE)),
        'has_workflow_tree': bool(re.search(r'Workflow Decision Tree', content, re.IGNORECASE)),
        'mandatory_marker_count': len(re.findall(r'\*\*MANDATORY\*\*', content)),
        'has_handoff_rules': bool(re.search(r'CRITICAL HANDOFF', content, re.IGNORECASE)),
    }


def check_explicit_script_violations(content: str) -> list:
    """Check for Rule 9 violations: workflow steps with action verbs but no explicit script calls."""
    violations = []

    action_verbs = [
        'read the',
        'write the',
        'display the',
        'check the',
        'validate the',
        'get the',
        'list the',
        'create the',
        'update the',
        'delete the',
        'read config',
        'read status',
        'read solution',
        'read task',
        'display solution',
        'display status',
        'display config',
    ]

    exempt_patterns = [
        r'Task:',
        r'Skill:',
        r'Read:',
        r'Glob:',
        r'Grep:',
        r'AskUserQuestion',
    ]

    step_pattern = re.compile(r'^###?\s+Step\s+\d+[a-z]?[:\s].*$', re.MULTILINE | re.IGNORECASE)
    step_matches = list(step_pattern.finditer(content))

    for i, match in enumerate(step_matches):
        step_header = match.group(0)
        step_start = match.end()
        step_end = step_matches[i + 1].start() if i + 1 < len(step_matches) else len(content)
        step_content = content[step_start:step_end]

        has_action_verb = False
        found_verb = None
        for verb in action_verbs:
            if verb.lower() in step_content.lower():
                has_action_verb = True
                found_verb = verb
                break

        if not has_action_verb:
            continue

        is_exempt = False
        for pattern in exempt_patterns:
            if re.search(pattern, step_content):
                is_exempt = True
                break

        if is_exempt:
            continue

        has_script_call = bool(re.search(r'execute-script\.py', step_content))

        if not has_script_call:
            violations.append(
                {
                    'step': step_header.strip(),
                    'action_verb': found_verb,
                    'issue': 'Missing explicit script call (execute-script.py) for action verb',
                }
            )

    return violations


def check_command_self_containment(content: str) -> dict:
    """Check for self-contained command definition violations (Rule 10).

    Mode A: Detect delegation patterns (parent-passed commands)
    Mode B: Verify explicit notation format (bundle:skill:script)
    Mode C: Detect script action verbs without explicit command section
    """
    violations = []

    # ============================================
    # MODE A: Delegation Pattern Detection
    # ============================================
    delegation_patterns = [
        (r'execute.*command.*from.*section', "Delegation: 'command from section'"),
        (r'fill in.*placeholders.*from.*prompt', "Delegation: 'placeholders from prompt'"),
        (r'command.*provided by.*parent', "Delegation: 'provided by parent'"),
        (r'use.*the.*command.*from', "Delegation: 'use command from'"),
        (r'logging command.*from.*section', "Delegation: 'logging command from section'"),
    ]

    for pattern, description in delegation_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            violations.append({'mode': 'delegation', 'detail': description})

    # ============================================
    # MODE B: Notation Enforcement
    # ============================================
    # Find all bash blocks containing execute-script.py
    bash_blocks = re.findall(r'```bash\s*(.*?)```', content, re.DOTALL | re.MULTILINE)

    notation_pattern = r'execute-script\.py\s+(\S+)'
    # Valid notation: bundle:skill:script (all lowercase with hyphens/underscores)
    valid_notation = r'^[a-z][a-z0-9\-]+:[a-z][a-z0-9\-]+:[a-z][a-z0-9\-_]+$'

    for block in bash_blocks:
        if 'execute-script.py' in block:
            # Extract the notation argument
            match = re.search(notation_pattern, block)
            if match:
                notation = match.group(1)
                # Verify it matches bundle:skill:script format
                if not re.match(valid_notation, notation):
                    violations.append(
                        {
                            'mode': 'notation',
                            'detail': f"Invalid notation format: '{notation}' (expected bundle:skill:script)",
                        }
                    )
            else:
                violations.append({'mode': 'notation', 'detail': 'execute-script.py without notation argument'})

    # ============================================
    # MODE C: Action Verb Without Explicit Command Section
    # ============================================
    # Script-related action verbs that require explicit command definitions
    script_actions = [
        (r'log\s+(the\s+)?assessment', 'log assessment'),
        (r'store\s+(the\s+)?finding', 'store finding'),
        (r'persist\s+(the\s+)?result', 'persist result'),
        (r'record\s+(the\s+)?(assessment|finding|result)', 'record assessment'),
        (r'save\s+(the\s+)?analysis', 'save analysis'),
        (r'log\s+(each|the|every)\s+', 'log operation'),
    ]

    # Check if component has explicit command section
    has_command_section = bool(
        re.search(r'##\s*(Logging\s+Command|Script\s+Commands?|Commands?\s+Reference)', content, re.IGNORECASE)
    )

    for action_pattern, action_name in script_actions:
        if re.search(action_pattern, content, re.IGNORECASE):
            if not has_command_section:
                violations.append(
                    {
                        'mode': 'missing_section',
                        'detail': f"Action '{action_name}' without ## Logging Command section",
                    }
                )
                break  # Only report once per file

    return {
        'command_self_containment': len(violations) > 0,
        'command_self_containments': violations,
        'containment_summary': {
            'delegation_issues': len([v for v in violations if v['mode'] == 'delegation']),
            'notation_issues': len([v for v in violations if v['mode'] == 'notation']),
            'missing_section_issues': len([v for v in violations if v['mode'] == 'missing_section']),
        },
    }


DYNAMIC_LEVEL_EXECUTOR_REF = (
    'plan-marshall:extension-api/standards/ext-point-dynamic-level-executor'
)

# Per-target build-output directory prefix. Variants emitted by the build
# target live under ``target/{target}/`` (e.g. ``target/claude/`` for the
# Claude rule-pack target), outside the doctor's source-of-truth scan path
# (``marketplace/bundles/``), so they are exempt from the
# ``hardcoded-model-on-canonical`` rule. The prefix is target-specific because
# the build-output directory is named for the target; the literal
# ``target/claude/`` is a Claude rule-pack concern, not an engine constant.
_BUILD_OUTPUT_PREFIXES = {
    'claude': 'target/claude/',
    'opencode': 'target/opencode/',
}


def _build_output_prefix() -> str:
    """Return the active target's build-output directory prefix.

    Falls back to the Claude prefix when the target is unrecognised (every
    runtime-less environment is a Claude checkout)."""
    return _BUILD_OUTPUT_PREFIXES.get(resolve_runtime_target(), 'target/claude/')


def check_hardcoded_model_on_canonical(frontmatter: str, file_path: str) -> list:
    """Check the ``hardcoded-model-on-canonical`` rule on canonical agent files.

    Two error branches:

    1. The agent declares ``model:`` or ``effort:`` AND lacks
       ``implements: <ext-point>``. Either remove the model pin (so the
       agent inherits the parent session's model) or opt into the variant
       system by adding the ``implements:`` declaration; pinning a model
       on a non-eligible canonical defeats the role-variants system.
    2. The agent declares ``implements: <ext-point>`` AND has ``model:``
       or ``effort:``. The build target sets these on emitted variants;
       silent shadowing on the canonical is prohibited.

    Variants emitted by the build target live under ``target/{target}/``
    (e.g. ``target/claude/`` for the Claude rule-pack target), outside the
    doctor's source-of-truth scan path (``marketplace/bundles/``), so they
    are exempt. The exempt prefix is resolved target-aware via
    ``_build_output_prefix``.

    Returns a list of finding dicts: ``{branch, code, message}`` — empty
    when neither branch fires.
    """
    findings: list = []

    # Build target output is exempt — the rule only fires on source-of-truth files.
    if _build_output_prefix() in file_path:
        return findings

    has_model = bool(re.search(r'^model:', frontmatter, re.MULTILINE))
    has_effort = bool(re.search(r'^effort:', frontmatter, re.MULTILINE))
    has_implements = bool(re.search(r'^implements:', frontmatter, re.MULTILINE))
    implements_value = ''
    if has_implements:
        match = re.search(r'^implements:\s*(\S+)', frontmatter, re.MULTILINE)
        if match:
            implements_value = match.group(1).strip()

    declares_role = implements_value == DYNAMIC_LEVEL_EXECUTOR_REF

    # Branch 1: model/effort without implements: ext-point.
    if (has_model or has_effort) and not declares_role:
        offenders = ', '.join(filter(None, ['model:' if has_model else '', 'effort:' if has_effort else '']))
        findings.append(
            {
                'branch': 'missing_implements',
                'code': 'HARDCODED_MODEL_ON_CANONICAL',
                'message': (
                    f"Canonical agent declares {offenders} without "
                    f"'implements: {DYNAMIC_LEVEL_EXECUTOR_REF}'. "
                    'Either remove the hardcoded pin or add the implements declaration '
                    'to opt into role-based variant emission.'
                ),
            }
        )

    # Branch 2: implements: <ext-point> AND model/effort present.
    if declares_role and (has_model or has_effort):
        offenders = ', '.join(filter(None, ['model:' if has_model else '', 'effort:' if has_effort else '']))
        findings.append(
            {
                'branch': 'shadowing_with_implements',
                'code': 'HARDCODED_MODEL_ON_CANONICAL',
                'message': (
                    f"Canonical agent declares 'implements: {DYNAMIC_LEVEL_EXECUTOR_REF}' "
                    f'AND {offenders}. The build target sets these on emitted variants; '
                    'silent shadowing on the canonical is prohibited.'
                ),
            }
        )

    return findings


def check_skill_tool_visibility(frontmatter: str, has_tools: bool) -> bool:
    """Check agent-skill-tool-visibility: Agent tools missing Skill — invisible to Task dispatcher.

    When an agent declares explicit tools but omits Skill, it becomes invisible
    to the Task tool dispatcher. If no tools are declared (inherits all), Skill
    is included implicitly, so no violation.
    """
    if not has_tools:
        return False

    # Extract tools from inline format: tools: Read, Write, Edit
    tools_match = re.search(r'^(?:tools|allowed-tools):\s*(.+)$', frontmatter, re.MULTILINE)
    if not tools_match:
        return False

    tools_str = tools_match.group(1).strip()
    # Handle both comma-separated and YAML array formats
    tools_str = tools_str.strip('[]')
    tools = [t.strip().strip('"').strip("'") for t in tools_str.split(',')]

    return 'Skill' not in tools


def check_prose_parameter_consistency(content: str) -> list:
    """Check workflow-prose-parameter-consistency near script call templates.

    Detects prose instructions adjacent to execute-script.py bash blocks that
    reference parameter values inconsistent with the actual script API.

    Currently detects:
    - 'body' referenced as a section name near manage-plan-documents calls
      (body is not a valid section for description-sourced requests;
      the correct fallback is original_input)
    """
    violations = []

    # Split into sections using ## or ### headers for context windows
    section_pattern = re.compile(r'^#{2,3}\s+.*$', re.MULTILINE)
    section_matches = list(section_pattern.finditer(content))

    # Build section boundaries
    boundaries = [m.start() for m in section_matches]
    if not boundaries or boundaries[0] != 0:
        boundaries.insert(0, 0)
    boundaries.append(len(content))

    for i in range(len(boundaries) - 1):
        section_start = boundaries[i]
        section_end = boundaries[i + 1]
        section_content = content[section_start:section_end]

        # Check if section has a manage-plan-documents bash block with --section
        # Use DOTALL because manage-plan-documents and --section may be on different lines
        if not re.search(r'manage-plan-documents.*--section', section_content, re.DOTALL):
            continue

        # Extract prose (content outside bash blocks)
        prose = re.sub(r'```(?:bash)?.*?```', '', section_content, flags=re.DOTALL)

        # Pattern: prose references "body" as a section name
        # "body" is NOT a valid section for description-sourced requests.
        # Valid sections: _header, original_input, clarified_request, context, clarifications
        body_patterns = [
            (r'fall\s*back\s+to\s+(?:the\s+)?body\b', 'fall back to body'),
            (r'otherwise\s+body\b', 'otherwise body'),
            (r'\bbody\s+section\b', 'body section'),
            (r'section\s+body\b', 'section body'),
            (r'to\s+body\s+(?:if|when)\b', 'to body if/when'),
        ]

        for pattern, description in body_patterns:
            match = re.search(pattern, prose, re.IGNORECASE)
            if match:
                # Calculate approximate line number
                lines_before_section = content[:section_start].count('\n')
                lines_in_prose = prose[: match.start()].count('\n')
                line_number = lines_before_section + lines_in_prose + 1

                violations.append(
                    {
                        'line': line_number,
                        'issue': "Prose references 'body' as section near manage-plan-documents call",
                        'detail': (
                            f"Found '{description}'. 'body' is not a valid fallback section "
                            f"for description-sourced requests. Use 'original_input' instead."
                        ),
                        'pattern': 'invalid_section_reference',
                    }
                )
                break  # One violation per section

    return violations


def check_resolver_gap(content: str, file_path: str) -> list:
    """Check skill-resolver-gap: LLM-Glob discovery prose without an adjacent resolver call.

    Scans markdown line-by-line for trigger phrases that direct an LLM to perform
    discovery via Glob. For each match, looks at the next ≤5 lines for a
    ``python3 .plan/execute-script.py`` invocation. If absent, emits a finding.

    Detection scope is enforced by the caller (only SKILL.md and standards/*.md
    files); this function inspects content unconditionally so it can be unit
    tested in isolation.

    Honors a per-file ``plugin-doctor-disable: [skill-resolver-gap]``
    frontmatter key, which suppresses every finding in that file.

    Returns a list of finding dicts: ``{line, message}``. The caller wraps these
    into the standard issue schema.
    """
    findings: list = []

    # Granularity-3 (per-file frontmatter): skip the whole file when its
    # ``plugin-doctor-disable`` list names this rule.
    if 'skill-resolver-gap' in read_frontmatter_disable_list(content):
        return findings

    # Trigger phrases — case-insensitive. These mirror the prose forms most
    # commonly used to direct an LLM to hand-roll discovery via Glob.
    trigger_patterns = [
        re.compile(r'\bUse\s+Glob\s*:', re.IGNORECASE),
        re.compile(r'\bGlob\s+pattern\s*:', re.IGNORECASE),
        re.compile(r'\bDiscover\b.*\busing\s+Glob\b', re.IGNORECASE),
        re.compile(r'\bfind\b.*\busing\s+Glob\s+patterns?\b', re.IGNORECASE),
    ]

    lines = content.split('\n')
    for idx, line in enumerate(lines):
        # Skip if any trigger fires
        matched_pattern = None
        for pattern in trigger_patterns:
            if pattern.search(line):
                matched_pattern = pattern.pattern
                break
        if matched_pattern is None:
            continue

        # Look ahead up to 5 lines (inclusive of current line) for a resolver call
        lookahead_end = min(len(lines), idx + 6)
        window = '\n'.join(lines[idx:lookahead_end])
        if 'python3 .plan/execute-script.py' in window:
            continue

        findings.append(
            {
                'line': idx + 1,  # 1-indexed
                'message': (
                    'LLM-Glob discovery prose without adjacent `python3 .plan/execute-script.py` '
                    'call within 5 lines (skill-resolver-gap)'
                ),
                'pattern': matched_pattern,
            }
        )

    return findings


def check_mark_step_done_violations(content: str) -> list:
    """Check mark-step-done invocations inside bash code fences for argument defects.

    Scans each fenced ```bash ... ``` block for lines referencing `mark-step-done`
    (typically the `plan-marshall:manage-status:...` subcommand used at phase-6-finalize
    finalize step termination). For every invocation, emits up to three distinct
    findings:

    - ``MARK_STEP_DONE_STALE_NOTATION``: the line contains the stale underscored
      notation ``manage-status:manage_status`` instead of the canonical kebab-case
      form ``manage-status:manage-status``. The underscored form no longer resolves
      via the script executor after the entrypoint-rename cutover and silently
      fails — see driving lesson that motivated this rule family.
    - ``MARK_STEP_DONE_MISSING_PHASE``: the full invocation (single line or
      backslash-continued multi-line) does not contain ``--phase``. Phase-6 step
      termination requires ``--phase`` to route the finalize status update.
    - ``MARK_STEP_DONE_MISSING_OUTCOME``: the full invocation does not contain
      ``--outcome``. Without ``--outcome``, the step cannot be terminated with a
      definitive result (done/skipped/deferred).

    Each finding is returned as a dict with ``line`` (1-indexed line number of
    the first mark-step-done line of the invocation) and ``code`` (the defect
    code).
    """
    violations = []

    # Find every ```bash (or ```sh) fenced block together with its start offset
    # so we can translate intra-block positions back to file line numbers.
    fence_pattern = re.compile(r'```(?:bash|sh)\s*\n(.*?)```', re.DOTALL)

    for fence_match in fence_pattern.finditer(content):
        block = fence_match.group(1)
        # Line number of the first content line inside the fence (1-indexed).
        block_start_line = content[: fence_match.start()].count('\n') + 2

        block_lines = block.split('\n')

        # Group lines into logical commands first, so that mark-step-done can
        # live on ANY line of a backslash-continued command (including a
        # continuation line below a `manage-status:manage_status \` prefix).
        # The previous line-walker anchored on the mark-step-done line and only
        # looked forward, which missed notation appearing on lines before it.
        logical_commands: list[list[tuple[int, str]]] = []
        current_cmd: list[tuple[int, str]] = []
        for idx, cmd_line in enumerate(block_lines):
            current_cmd.append((idx, cmd_line))
            if not cmd_line.rstrip().endswith('\\'):
                logical_commands.append(current_cmd)
                current_cmd = []
        if current_cmd:
            logical_commands.append(current_cmd)

        for cmd in logical_commands:
            # Find lines containing `mark-step-done` — anchor reporting on the
            # first occurrence for stable line numbers.
            mark_done_indices = [idx for idx, cmd_line in cmd if 'mark-step-done' in cmd_line]
            if not mark_done_indices:
                continue

            invocation_line = block_start_line + mark_done_indices[0]
            invocation_text = '\n'.join(cmd_line for _idx, cmd_line in cmd)

            # MARK_STEP_DONE_STALE_NOTATION: stale underscored notation anywhere
            # in the assembled logical command (word-bounded to avoid partial
            # matches).
            if re.search(r'\bmanage-status:manage_status\b', invocation_text):
                violations.append({'line': invocation_line, 'code': 'MARK_STEP_DONE_STALE_NOTATION'})

            # MARK_STEP_DONE_MISSING_PHASE — anchored matching prevents
            # `--phase-override` (or similar) from spoofing a present `--phase`.
            if not re.search(r'(?<![A-Za-z0-9_-])--phase(?![A-Za-z0-9_-])', invocation_text):
                violations.append({'line': invocation_line, 'code': 'MARK_STEP_DONE_MISSING_PHASE'})

            # MARK_STEP_DONE_MISSING_OUTCOME — same anchored guard.
            if not re.search(r'(?<![A-Za-z0-9_-])--outcome(?![A-Za-z0-9_-])', invocation_text):
                violations.append({'line': invocation_line, 'code': 'MARK_STEP_DONE_MISSING_OUTCOME'})

    return violations


def _extract_display_detail_value(invocation_text: str) -> str | None:
    """Extract the value passed to --display-detail in a (possibly multi-line) command string.

    Handles three forms:
    - Double-quoted: ``--display-detail "value with spaces"`` (supports ``\\\"`` escape)
    - Single-quoted: ``--display-detail 'value with spaces'``
    - Unquoted: ``--display-detail value`` (terminates at whitespace)

    Returns the raw value string (without enclosing quotes) or ``None`` when the
    flag is not present in ``invocation_text``. Multi-line quoted values keep
    their embedded newlines so the multi-line defect check can detect them.
    """
    flag_pattern = re.compile(r'(?<![A-Za-z0-9_-])--display-detail(?![A-Za-z0-9_-])\s+')
    match = flag_pattern.search(invocation_text)
    if not match:
        return None

    after = invocation_text[match.end() :]
    if not after:
        return None

    first_char = after[0]
    if first_char == '"':
        end_match = re.search(r'(?<!\\)"', after[1:])
        if not end_match:
            return None
        return after[1 : 1 + end_match.start()]
    if first_char == "'":
        end_match = re.search(r"'", after[1:])
        if not end_match:
            return None
        return after[1 : 1 + end_match.start()]
    end_match = re.search(r'\s', after)
    end = end_match.start() if end_match else len(after)
    return after[:end]


def check_display_detail_violations(content: str) -> list:
    """Check ``--display-detail`` values in ``mark-step-done`` invocations against the ASCII contract.

    Scans each fenced ``bash``/``sh`` block for ``mark-step-done`` invocations
    (single line or backslash-continued multi-line), extracts the
    ``--display-detail`` argument value, and emits one finding per defect kind:

    - ``DISPLAY_DETAIL_NON_ASCII``: value contains any character > 0x7F (e.g.,
      em dash U+2014, en dash U+2013, smart quotes).
    - ``DISPLAY_DETAIL_TOO_LONG``: value length exceeds 80 characters.
    - ``DISPLAY_DETAIL_MULTILINE``: value contains a newline (``\\n``).
    - ``DISPLAY_DETAIL_TRAILING_PERIOD``: value ends with ``.``.

    The contract is documented in ``phase-6-finalize/SKILL.md`` and
    ``phase-6-finalize/standards/output-template.md`` ("Plain ASCII - no
    unicode glyphs"). Without this rule, violations only surface in PR review
    after gemini-code-assist or other bots flag them.

    Each finding is returned as a dict with ``line`` (1-indexed line of the
    first ``mark-step-done`` line of the invocation), ``code`` (defect code),
    and ``value`` (offending substring, truncated to 80 chars for reporting).
    """
    violations = []
    fence_pattern = re.compile(r'```(?:bash|sh)\s*\n(.*?)```', re.DOTALL)

    for fence_match in fence_pattern.finditer(content):
        block = fence_match.group(1)
        block_start_line = content[: fence_match.start()].count('\n') + 2

        block_lines = block.split('\n')

        # Group lines into logical shell commands. A line continues into the
        # next when it ends with a trailing backslash OR an unclosed double-/
        # single-quoted string. The quote tracker treats ``\\X`` as an escape
        # sequence so embedded ``\\\"`` does not flip the in_double_quote flag.
        logical_commands: list[list[tuple[int, str]]] = []
        current_cmd: list[tuple[int, str]] = []
        in_double_quote = False
        in_single_quote = False
        for idx, cmd_line in enumerate(block_lines):
            current_cmd.append((idx, cmd_line))
            j = 0
            while j < len(cmd_line):
                ch = cmd_line[j]
                if ch == '\\' and j + 1 < len(cmd_line):
                    j += 2
                    continue
                if ch == '"' and not in_single_quote:
                    in_double_quote = not in_double_quote
                elif ch == "'" and not in_double_quote:
                    in_single_quote = not in_single_quote
                j += 1
            line_continues = cmd_line.rstrip().endswith('\\') or in_double_quote or in_single_quote
            if not line_continues:
                logical_commands.append(current_cmd)
                current_cmd = []
        if current_cmd:
            logical_commands.append(current_cmd)

        for cmd in logical_commands:
            mark_done_indices = [idx for idx, cmd_line in cmd if 'mark-step-done' in cmd_line]
            if not mark_done_indices:
                continue

            invocation_line = block_start_line + mark_done_indices[0]
            invocation_text = '\n'.join(cmd_line for _idx, cmd_line in cmd)

            value = _extract_display_detail_value(invocation_text)
            if value is None:
                continue

            report_value = value if len(value) <= 80 else value[:77] + '...'

            if any(ord(ch) > 0x7F for ch in value):
                violations.append({'line': invocation_line, 'code': 'DISPLAY_DETAIL_NON_ASCII', 'value': report_value})
            if len(value) > 80:
                violations.append({'line': invocation_line, 'code': 'DISPLAY_DETAIL_TOO_LONG', 'value': report_value})
            if '\n' in value:
                violations.append({'line': invocation_line, 'code': 'DISPLAY_DETAIL_MULTILINE', 'value': report_value})
            if value.endswith('.'):
                violations.append(
                    {'line': invocation_line, 'code': 'DISPLAY_DETAIL_TRAILING_PERIOD', 'value': report_value}
                )

    return violations


# Markdown inline link: ``[text](target)``. The target may carry an optional
# ``#fragment`` and an optional title. Captured loosely; structural filtering
# (scheme / anchor-only / absolute) happens in the check below.
_MD_LINK_RE = re.compile(r'\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')

# A fenced-code opening line: three-or-more backticks (or tildes) optionally
# followed by an info-string. Captures the info-string (may be empty).
_FENCE_OPEN_RE = re.compile(r'^(\s*)(`{3,}|~{3,})\s*(\S*)\s*$')

# An inline-code span: a run of one-or-more backticks, the shortest run of
# content up to a matching backtick run, then a closing backtick run of the
# same length (CommonMark inline-code delimiting). Content inside a span is
# literal text — a ``[text](path)`` / ``![](path)`` literal there is an
# illustrative example, not a real on-disk reference.
_INLINE_CODE_RE = re.compile(r'(`+)(?:.+?)\1')


def _strip_inline_code_spans(line: str) -> str:
    """Blank out inline-code spans on a line so their contents are not scanned.

    Replaces each ```...``` span (including the delimiting backticks)
    with an equal-length run of spaces, preserving the line's length and the
    column positions of any text outside the spans. A relative-link literal
    that lives inside a span is therefore invisible to the link scanner.
    """
    return _INLINE_CODE_RE.sub(lambda m: ' ' * len(m.group(0)), line)


def check_broken_relative_link(content: str, file_path: str) -> list:
    """Check broken-relative-link: a relative markdown link with no on-disk target.

    Resolves every ``[text](relative/path.md)`` link target against the linking
    file's own directory and emits a finding when the resolved target does not
    exist on disk. This catches the off-by-``../`` class of stale cross-reference.

    Out of scope (never flagged):

    - absolute URLs (``http://`` / ``https://`` / ``mailto:`` / any ``scheme:``);
    - root-absolute paths (a leading ``/``);
    - pure-anchor links (a leading ``#``);
    - links inside fenced code blocks (illustrative, not real references);
    - links inside inline-code spans (single/multi backticks — ``` `[text](p)` ```
      and ``` `![](p)` ``` literals are illustrative, not real references).

    A fragment (``path.md#section``) is stripped before resolution — only the
    file part is checked for existence. Returns a list of ``{line, target,
    message}`` dicts; the caller wraps these into the standard issue schema.
    """
    findings: list = []
    base_dir = Path(file_path).parent
    fence_map = _fenced_line_indices(content)
    lines = content.split('\n')
    for idx, line in enumerate(lines):
        if idx in fence_map:
            continue
        # Inline-code spans on this line hold literal example text — blank them
        # out (length-preserving) before scanning so a link literal inside
        # backticks is not mistaken for a real on-disk reference.
        scan_line = _strip_inline_code_spans(line)
        for match in _MD_LINK_RE.finditer(scan_line):
            target = match.group(1)
            # Scheme-bearing (URL/mailto), root-absolute, and pure-anchor links
            # are not relative on-disk references.
            if target.startswith(('#', '/')) or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                continue
            file_part = target.split('#', 1)[0]
            if not file_part:
                continue
            resolved = (base_dir / file_part)
            if resolved.exists():
                continue
            findings.append(
                {
                    'line': idx + 1,
                    'target': target,
                    'message': (
                        f'relative link target `{target}` does not resolve to a file on disk '
                        f'(broken-relative-link)'
                    ),
                }
            )
    return findings


def _fenced_line_indices(content: str) -> set:
    """Return the 0-based line indices that lie inside a fenced code block.

    Includes the opening and closing fence delimiter lines so a link or
    info-string on a delimiter line is never mistaken for body content.
    """
    inside: set = set()
    in_fence = False
    fence_marker = ''
    for idx, line in enumerate(content.split('\n')):
        match = _FENCE_OPEN_RE.match(line)
        if not in_fence:
            if match:
                in_fence = True
                fence_marker = match.group(2)[0]  # ` or ~
                inside.add(idx)
        else:
            inside.add(idx)
            stripped = line.strip()
            # A closing fence is a run of the same marker char with no info-string.
            if stripped and set(stripped) == {fence_marker} and len(stripped) >= 3:
                in_fence = False
                fence_marker = ''
    return inside


def check_fenced_code_no_language(content: str) -> list:
    """Check fenced-code-no-language: a fenced block whose opening line has no info-string.

    Flags every ```` ``` ```` (or ``~~~``) opening fence that carries no
    info-string (the MD040 "fenced code language" defect). The closing fence of
    a block legitimately carries no info-string, so only *opening* fences are
    inspected — the scanner tracks fence state to distinguish the two.

    Returns a list of ``{line, message}`` dicts; the caller wraps these into the
    standard issue schema.
    """
    findings: list = []
    in_fence = False
    fence_marker = ''
    for idx, line in enumerate(content.split('\n')):
        match = _FENCE_OPEN_RE.match(line)
        if not in_fence:
            if match:
                in_fence = True
                fence_marker = match.group(2)[0]
                info_string = match.group(3)
                if not info_string:
                    findings.append(
                        {
                            'line': idx + 1,
                            'message': (
                                'fenced code block opens with no language info-string '
                                '(fenced-code-no-language)'
                            ),
                        }
                    )
        else:
            stripped = line.strip()
            if stripped and set(stripped) == {fence_marker} and len(stripped) >= 3:
                in_fence = False
                fence_marker = ''
    return findings


def check_rule_violations(content: str, frontmatter: str, component_type: str, has_tools: bool, file_path: str) -> dict:
    """Check for rule violations."""
    agent_task_tool_prohibited = False
    if component_type == 'agent' and has_tools:
        if re.search(r'^  - Task$|Task,|Task$', frontmatter, re.MULTILINE):
            agent_task_tool_prohibited = True

    agent_maven_restricted = False
    if re.search(r'mvn |maven |./mvnw ', content):
        if 'builder-maven' not in file_path:
            pattern = r'^Bash:.*mvn|^Bash:.*maven|^Bash:.*\./mvnw|`.*mvn |`.*\./mvnw |^\s+mvn |^\s+\./mvnw '
            matches = re.findall(pattern, content, re.MULTILINE)
            for match in matches:
                if 'Rule 7' not in match and 'should use' not in match and 'instead of' not in match:
                    agent_maven_restricted = True
                    break

    workflow_hardcoded_script_path = False
    if re.search(r'python3 .*/scripts/|bash .*/scripts/|\{[^}]+\}/scripts/', content):
        if not re.search(r'Skill:.*script-runner', content):
            workflow_hardcoded_script_path = True

    workflow_explicit_script_violations = []
    if component_type == 'skill':
        workflow_explicit_script_violations = check_explicit_script_violations(content)

    # Self-contained command definition (applies to agents primarily)
    command_self_contained_violations = {}
    if component_type == 'agent':
        command_self_contained_violations = check_command_self_containment(content)

    # Agent Skill tool visibility (agents only)
    agent_skill_tool_visibility = False
    if component_type == 'agent':
        agent_skill_tool_visibility = check_skill_tool_visibility(frontmatter, has_tools)

    # Prose-parameter consistency (all component types)
    workflow_prose_param_violations = check_prose_parameter_consistency(content)

    # mark-step-done argument validation (phase-6-finalize finalize step termination)
    mark_step_done_violations = check_mark_step_done_violations(content)

    # skill-resolver-gap: LLM-Glob prose without resolver call (skills only)
    # Scope: SKILL.md and standards/*.md inside skill directories. Agents and
    # commands don't drive discovery via Glob from prose — restricting prevents
    # false positives in agent docs that legitimately list Glob as an allowed tool.
    resolver_gap_violations: list = []
    if component_type in ('skill', 'subdoc') and (file_path.endswith('SKILL.md') or '/standards/' in file_path):
        resolver_gap_violations = check_resolver_gap(content, file_path)

    # --display-detail ASCII contract validation (phase-6-finalize finalize renderer)
    display_detail_violations = check_display_detail_violations(content)

    # hardcoded-model-on-canonical rule (agents only)
    hardcoded_model_on_canonical_violations: list = []
    if component_type == 'agent':
        hardcoded_model_on_canonical_violations = check_hardcoded_model_on_canonical(frontmatter, file_path)

    # broken-relative-link + fenced-code-no-language — markdown-mirror drift
    # rules applied to every component markdown file.
    broken_relative_link_violations = check_broken_relative_link(content, file_path)
    fenced_code_no_language_violations = check_fenced_code_no_language(content)

    return {
        'agent_task_tool_prohibited': agent_task_tool_prohibited,
        'agent_maven_restricted': agent_maven_restricted,
        'workflow_hardcoded_script_path': workflow_hardcoded_script_path,
        'workflow_explicit_script_violations': workflow_explicit_script_violations,
        'command_self_contained_violations': command_self_contained_violations,
        'agent_skill_tool_visibility': agent_skill_tool_visibility,
        'workflow_prose_param_violations': workflow_prose_param_violations,
        'mark_step_done_violations': mark_step_done_violations,
        'resolver_gap_violations': resolver_gap_violations,
        'display_detail_violations': display_detail_violations,
        'hardcoded_model_on_canonical_violations': hardcoded_model_on_canonical_violations,
        'broken_relative_link_violations': broken_relative_link_violations,
        'fenced_code_no_language_violations': fenced_code_no_language_violations,
    }


def check_checklist_patterns(content: str, file_path: str) -> dict:
    """Check for checkbox patterns (- [ ] / - [x]) in LLM-consumed markdown.

    Files in /templates/ directories are exempt (rendered by GitHub).
    """
    if '/templates/' in file_path:
        return {'has_checklists': False, 'count': 0, 'sections': []}

    unchecked = re.findall(r'^- \[ \] ', content, re.MULTILINE)
    checked = re.findall(r'^- \[[xX]\] ', content, re.MULTILINE)
    count = len(unchecked) + len(checked)

    sections: list[str] = []
    if count > 0:
        current_section = None
        for line in content.splitlines():
            header_match = re.match(r'^(#{1,4})\s+(.+)', line)
            if header_match:
                current_section = header_match.group(2).strip()
            elif re.match(r'^- \[[ xX]\] ', line) and current_section and current_section not in sections:
                sections.append(current_section)

    return {'has_checklists': count > 0, 'count': count, 'sections': sections}


def check_forbidden_metadata(content: str) -> tuple[bool, str]:
    """Check for forbidden metadata sections."""
    forbidden_pattern = r'^## (Version|Version History|License|Changelog|Change Log|Author|Revision History)$'
    matches = re.findall(forbidden_pattern, content, re.MULTILINE)

    if matches:
        return True, ','.join(matches)
    return False, ''


def analyze_markdown_file(file_path: Path, component_type: str) -> dict:
    """Analyze markdown file and return results."""
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
    except OSError as e:
        return {'error': f'Failed to read file: {e}'}

    line_count = content.count('\n') + (1 if content and not content.endswith('\n') else 0)

    if component_type == 'auto':
        component_type = detect_component_type(str(file_path))

    frontmatter_present, frontmatter = extract_frontmatter(content)
    yaml_valid = check_yaml_validity(frontmatter) if frontmatter_present else False
    required_fields = (
        check_frontmatter_fields(frontmatter)
        if frontmatter_present
        else {
            'name': {'present': False},
            'description': {'present': False},
            'tools': {'present': False, 'field_type': 'none'},
            'user_invocable': {'present': False, 'misspelled': False},
        }
    )

    section_count = len(re.findall(r'^## ', content, re.MULTILINE))
    has_param_section = bool(re.search(r'^## PARAMETERS|^### Parameters', content, re.MULTILINE | re.IGNORECASE))
    ci_rule = check_continuous_improvement(content, component_type)
    bloat_class = get_bloat_classification(line_count, component_type)
    exec_patterns = check_execution_patterns(content)
    rules = check_rule_violations(
        content, frontmatter, component_type, required_fields['tools']['present'], str(file_path)
    )
    has_forbidden, forbidden_sections = check_forbidden_metadata(content)
    checklist_patterns = check_checklist_patterns(content, str(file_path))

    # Detect reference-mode pattern (skills only)
    is_reference_mode = bool(re.search(r'\*\*REFERENCE MODE\*\*|REFERENCE MODE:', content))

    return {
        'file_path': str(file_path),
        'file_type': {'type': component_type},
        'metrics': {'line_count': line_count},
        'frontmatter': {'present': frontmatter_present, 'yaml_valid': yaml_valid, 'required_fields': required_fields},
        'structure': {'section_count': section_count},
        'parameters': {'has_section': has_param_section},
        'continuous_improvement_rule': ci_rule,
        'bloat': {'classification': bloat_class},
        'execution_patterns': exec_patterns,
        'rules': rules,
        'quality': {'has_forbidden_metadata': has_forbidden, 'forbidden_sections': forbidden_sections},
        'checklist_patterns': checklist_patterns,
        'content_mode': {'is_reference': is_reference_mode},
    }


def cmd_markdown(args) -> dict:
    """Analyze markdown file structure and compliance."""
    file_path = Path(args.file)

    if not file_path.exists():
        return {'status': 'error', 'error': 'file_not_found', 'message': f'File not found: {args.file}'}

    if not file_path.is_file():
        return {'status': 'error', 'error': 'not_a_file', 'message': f'Not a file: {args.file}'}

    result = analyze_markdown_file(file_path, args.type)

    if 'error' in result:
        result['status'] = 'error'
        return result

    result['status'] = 'success'
    return result

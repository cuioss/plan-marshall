#!/usr/bin/env python3
"""
Shared utilities for manage-tasks.py modular implementation.

Contains:
- TOON parsing/formatting utilities
- Task file operations
- Validation functions
- Output formatting
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Tuple, Any

from file_ops import atomic_write_file, base_path  # type: ignore[import-not-found]


# =============================================================================
# Constants
# =============================================================================

# Domains are arbitrary strings - defined in marshal.json, not hardcoded
VALID_PHASES = ['1-init', '2-outline', '3-plan', '4-execute', '5-finalize']
# Profiles are arbitrary strings - defined in marshal.json per-domain, not hardcoded
VALID_ORIGINS = ['plan', 'fix']
# Task types per target architecture
VALID_TYPES = ['IMPL', 'FIX', 'SONAR', 'PR', 'LINT', 'SEC', 'DOC']
VALID_FILE_EXTENSIONS = [
    '.md', '.py', '.java', '.js', '.ts', '.tsx', '.jsx', '.json', '.yaml', '.yml',
    '.xml', '.sh', '.bash', '.properties', '.adoc', '.toon', '.html', '.css'
]


# =============================================================================
# Basic utilities
# =============================================================================

def now_iso() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def slugify(title: str, max_length: int = 40) -> str:
    """Convert title to kebab-case slug."""
    slug = title.lower().replace(' ', '-')
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug[:max_length]
    slug = slug.rstrip('-')
    return slug


# =============================================================================
# Validation functions
# =============================================================================

def validate_deliverables(deliverables_input) -> List[int]:
    """Validate deliverables list."""
    if deliverables_input is None or len(deliverables_input) == 0:
        raise ValueError("At least one deliverable is required")

    result = []
    for item in deliverables_input:
        if isinstance(item, int):
            if item < 1:
                raise ValueError(f"Invalid deliverable number: {item}. Must be positive integer.")
            result.append(item)
        else:
            item_str = str(item).strip()
            if not item_str:
                continue
            if item_str.isdigit():
                num = int(item_str)
                if num < 1:
                    raise ValueError(f"Invalid deliverable number: {num}. Must be positive integer.")
                result.append(num)
            else:
                raise ValueError(f"Invalid deliverable format: {item_str}. Expected positive integer.")

    if len(result) == 0:
        raise ValueError("At least one deliverable is required")

    return result


def validate_domain(domain: str) -> str:
    """Validate domain value (accepts any non-empty string).

    Domains are arbitrary keys in marshal.json. Validation happens
    at skill resolution time, not at task creation time.
    """
    if not domain or not domain.strip():
        raise ValueError("Domain cannot be empty")
    return domain.strip()


def validate_type(task_type: str) -> str:
    """Validate task type value."""
    if task_type not in VALID_TYPES:
        raise ValueError(f"Invalid type: {task_type}. Must be one of: {', '.join(VALID_TYPES)}")
    return task_type


def validate_phase(phase: str) -> str:
    """Validate phase value."""
    if phase not in VALID_PHASES:
        raise ValueError(f"Invalid phase: {phase}. Must be one of: {', '.join(VALID_PHASES)}")
    return phase


def validate_profile(profile: str) -> str:
    """Validate profile value (accepts any non-empty string).

    Profiles are arbitrary keys in marshal.json. Validation happens
    at skill resolution time, not at task creation time.
    """
    if not profile or not profile.strip():
        raise ValueError("Profile cannot be empty")
    return profile.strip()


def validate_origin(origin: str) -> str:
    """Validate origin value."""
    if origin not in VALID_ORIGINS:
        raise ValueError(f"Invalid origin: {origin}. Must be one of: {', '.join(VALID_ORIGINS)}")
    return origin


def validate_skills(skills: List[str]) -> List[str]:
    """Validate skills list format (bundle:skill)."""
    if not skills:
        return []

    validated = []
    for skill in skills:
        skill = skill.strip()
        if not skill:
            continue
        if ':' not in skill:
            raise ValueError(f"Invalid skill format: {skill}. Must be in 'bundle:skill' format.")
        validated.append(skill)

    return validated


def validate_steps_are_file_paths(steps: list[str]) -> tuple[list[str], list[str]]:
    """Validate that steps are file paths, not descriptive text."""
    errors = []
    warnings = []

    for i, step in enumerate(steps, 1):
        step = step.strip()
        has_path_separator = '/' in step
        has_valid_extension = any(step.endswith(ext) for ext in VALID_FILE_EXTENSIONS)

        if not has_path_separator and not has_valid_extension:
            errors.append(
                f"Step {i}: '{step[:50]}...' is not a file path. "
                f"Steps MUST be file paths from deliverable's Affected files section."
            )
            continue

        descriptive_patterns = [
            'update ', 'create ', 'implement ', 'add ', 'fix ', 'migrate ',
            'convert ', 'modify ', 'change ', 'remove ', 'delete ',
            ' to ', ' from ', ' with ', ' for '
        ]
        step_lower = step.lower()
        for pattern in descriptive_patterns:
            if pattern in step_lower:
                warnings.append(
                    f"Step {i}: '{step[:50]}' looks like descriptive text rather than a file path."
                )
                break

    return errors, warnings


# =============================================================================
# Dependency parsing
# =============================================================================

def parse_depends_on(depends_str: str) -> List[str]:
    """Parse depends_on field from TOON format."""
    if not depends_str or depends_str.strip().lower() == 'none':
        return []

    parts = [p.strip() for p in depends_str.split(',')]
    result = []
    for part in parts:
        if part.startswith('TASK-'):
            result.append(part)
        elif part.isdigit():
            result.append(f"TASK-{int(part)}")
    return result


def format_depends_on(deps: List[str]) -> str:
    """Format depends_on for file storage."""
    if not deps:
        return 'none'
    return ', '.join(deps)


# =============================================================================
# TOON block parsing
# =============================================================================

def parse_deliverables_block(lines: List[str], start_idx: int) -> Tuple[List[int], int]:
    """Parse deliverables block from TOON format."""
    deliverables = []
    i = start_idx + 1

    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('- '):
            try:
                deliverables.append(int(line[2:].strip()))
            except ValueError:
                pass
            i += 1
        elif line == '' or line.startswith('-'):
            i += 1
        else:
            break

    return deliverables, i


def parse_delegation_block(lines: List[str], start_idx: int) -> Tuple[dict, int]:
    """Parse delegation block from TOON format."""
    delegation = {
        'skill': '',
        'workflow': '',
        'domain': '',
        'context_skills': []
    }
    i = start_idx + 1

    while i < len(lines):
        line = lines[i]
        if not line.startswith('  '):
            break

        stripped = line.strip()
        if stripped.startswith('skill:'):
            delegation['skill'] = stripped[6:].strip()
        elif stripped.startswith('workflow:'):
            delegation['workflow'] = stripped[9:].strip()
        elif stripped.startswith('domain:'):
            delegation['domain'] = stripped[7:].strip()
        elif stripped.startswith('context_skills:'):
            i += 1
            while i < len(lines) and lines[i].startswith('  - '):
                skill = lines[i].strip()[2:].strip()
                if skill:
                    delegation['context_skills'].append(skill)
                i += 1
            continue
        i += 1

    return delegation, i


def parse_verification_block(lines: List[str], start_idx: int) -> Tuple[dict, int]:
    """Parse verification block from TOON format."""
    verification = {
        'commands': [],
        'criteria': '',
        'manual': False
    }
    i = start_idx + 1

    while i < len(lines):
        line = lines[i]
        if not line.startswith('  '):
            break

        stripped = line.strip()
        if stripped.startswith('commands['):
            i += 1
            while i < len(lines) and lines[i].startswith('  - '):
                cmd = lines[i].strip()[2:].strip()
                if cmd:
                    verification['commands'].append(cmd)
                i += 1
            continue
        elif stripped.startswith('criteria:'):
            verification['criteria'] = stripped[9:].strip()
        elif stripped.startswith('manual:'):
            val = stripped[7:].strip().lower()
            verification['manual'] = val == 'true'
        i += 1

    return verification, i


# =============================================================================
# Task file operations
# =============================================================================

def get_tasks_dir(plan_id: str) -> Path:
    """Get the tasks directory for a plan."""
    return base_path('plans', plan_id, 'tasks')


def parse_skills_block(lines: List[str], start_idx: int) -> Tuple[List[str], int]:
    """Parse skills block from TOON format."""
    skills = []
    i = start_idx + 1

    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('- '):
            skill = line[2:].strip()
            if skill:
                skills.append(skill)
            i += 1
        elif line == '':
            i += 1
        else:
            break

    return skills, i


def parse_finding_block(lines: List[str], start_idx: int) -> Tuple[dict, int]:
    """Parse finding block from TOON format (for fix tasks)."""
    finding = {
        'type': '',
        'file': '',
        'line': 0,
        'message': ''
    }
    i = start_idx + 1

    while i < len(lines):
        line = lines[i]
        if not line.startswith('  '):
            break

        stripped = line.strip()
        if stripped.startswith('type:'):
            finding['type'] = stripped[5:].strip()
        elif stripped.startswith('file:'):
            finding['file'] = stripped[5:].strip()
        elif stripped.startswith('line:'):
            try:
                finding['line'] = int(stripped[5:].strip())
            except ValueError:
                finding['line'] = 0
        elif stripped.startswith('message:'):
            finding['message'] = stripped[8:].strip()
        i += 1

    return finding, i


def parse_task_file(content: str) -> dict:
    """Parse a task TOON file into a dictionary."""
    result = {
        'steps': [],
        'deliverables': [],
        'depends_on': [],
        'domain': None,
        'profile': None,
        'type': 'IMPL',
        'skills': [],
        'origin': 'plan',
        'priority': None,
        'finding': None,
        'delegation': {
            'skill': '',
            'workflow': '',
            'domain': '',
            'context_skills': []
        },
        'verification': {
            'commands': [],
            'criteria': '',
            'manual': False
        }
    }
    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        if line.startswith('description:'):
            if line.strip() == 'description: |':
                desc_lines = []
                i += 1
                while i < len(lines):
                    if lines[i].startswith('  '):
                        desc_lines.append(lines[i][2:])
                    elif lines[i].strip() == '':
                        desc_lines.append('')
                    else:
                        break
                    i += 1
                result['description'] = '\n'.join(desc_lines).strip()
            else:
                result['description'] = line[12:].strip()
                i += 1
        elif line.startswith('deliverables['):
            result['deliverables'], i = parse_deliverables_block(lines, i)
        elif line.startswith('skills[') or line.startswith('skills:'):
            result['skills'], i = parse_skills_block(lines, i)
        elif line.startswith('finding:'):
            result['finding'], i = parse_finding_block(lines, i)
        elif line.startswith('delegation:'):
            result['delegation'], i = parse_delegation_block(lines, i)
        elif line.startswith('verification:'):
            result['verification'], i = parse_verification_block(lines, i)
        elif line.startswith('steps['):
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].startswith('current_step:') and not lines[i].startswith('verification:'):
                parts = lines[i].split(',', 2)
                if len(parts) == 3:
                    result['steps'].append({
                        'number': int(parts[0]),
                        'title': parts[1],
                        'status': parts[2]
                    })
                i += 1
        elif line.startswith('depends_on:'):
            value = line[11:].strip()
            result['depends_on'] = parse_depends_on(value)
            i += 1
        elif ':' in line and not line.startswith(' '):
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            if key in ('number', 'current_step'):
                value = int(value) if value else 1
            result[key] = value
            i += 1
        else:
            i += 1

    return result


def format_task_file(task: dict) -> str:
    """Format a task dictionary as TOON file content."""
    lines = [
        f"number: {task['number']}",
        f"title: {task['title']}",
        f"status: {task['status']}",
        f"phase: {task.get('phase', 'execute')}",
        f"domain: {task.get('domain', '')}",
        f"profile: {task.get('profile', 'implementation')}",
        f"type: {task.get('type', 'IMPL')}",
        f"origin: {task.get('origin', 'plan')}",
        f"created: {task['created']}",
        f"updated: {task['updated']}",
    ]

    # Add priority if present (for fix tasks)
    if task.get('priority'):
        lines.append(f"priority: {task['priority']}")

    lines.append("")

    # Skills array
    skills = task.get('skills', [])
    lines.append(f"skills[{len(skills)}]:")
    for skill in skills:
        lines.append(f"- {skill}")

    lines.append("")

    deliverables = task.get('deliverables', [])
    lines.append(f"deliverables[{len(deliverables)}]:")
    for d in deliverables:
        lines.append(f"- {d}")

    lines.append("")

    depends_on = task.get('depends_on', [])
    lines.append(f"depends_on: {format_depends_on(depends_on)}")

    lines.append("")

    lines.append("description: |")
    for desc_line in task.get('description', '').split('\n'):
        lines.append(f"  {desc_line}")

    lines.append("")

    # Add finding block if present (for fix tasks)
    finding = task.get('finding')
    if finding:
        lines.append("finding:")
        lines.append(f"  type: {finding.get('type', '')}")
        lines.append(f"  file: {finding.get('file', '')}")
        lines.append(f"  line: {finding.get('line', 0)}")
        lines.append(f"  message: {finding.get('message', '')}")
        lines.append("")

    delegation = task.get('delegation', {})
    lines.append("delegation:")
    lines.append(f"  skill: {delegation.get('skill', '')}")
    lines.append(f"  workflow: {delegation.get('workflow', '')}")
    lines.append(f"  domain: {delegation.get('domain', '')}")
    context_skills = delegation.get('context_skills', [])
    if context_skills:
        lines.append("  context_skills:")
        for skill in context_skills:
            lines.append(f"  - {skill}")

    lines.append("")

    steps = task.get('steps', [])
    lines.append(f"steps[{len(steps)}]{{number,title,status}}:")
    for step in steps:
        lines.append(f"{step['number']},{step['title']},{step['status']}")

    lines.append("")

    verification = task.get('verification', {})
    lines.append("verification:")
    commands = verification.get('commands', [])
    lines.append(f"  commands[{len(commands)}]:")
    for cmd in commands:
        lines.append(f"  - {cmd}")
    lines.append(f"  criteria: {verification.get('criteria', '')}")
    lines.append(f"  manual: {'true' if verification.get('manual', False) else 'false'}")

    lines.append("")
    lines.append(f"current_step: {task.get('current_step', 1)}")

    return '\n'.join(lines)


def find_task_file(task_dir: Path, number: int) -> Optional[Path]:
    """Find task file by number."""
    pattern = f"TASK-{number:03d}-*.toon"
    matches = list(task_dir.glob(pattern))
    return matches[0] if matches else None


def get_next_number(task_dir: Path) -> int:
    """Get next available task number."""
    if not task_dir.exists():
        return 1

    max_num = 0
    for f in task_dir.glob("TASK-*.toon"):
        try:
            num = int(f.name[5:8])
            max_num = max(max_num, num)
        except (ValueError, IndexError):
            pass

    return max_num + 1


def get_all_tasks(task_dir: Path) -> list:
    """Get all tasks sorted by number."""
    if not task_dir.exists():
        return []

    tasks = []
    for f in sorted(task_dir.glob("TASK-*.toon")):
        content = f.read_text(encoding='utf-8')
        task = parse_task_file(content)
        tasks.append((f, task))

    return sorted(tasks, key=lambda x: x[1].get('number', 0))


def calculate_progress(task: dict) -> Tuple[int, int]:
    """Calculate step completion progress."""
    steps = task.get('steps', [])
    completed = sum(1 for s in steps if s['status'] in ('done', 'skipped'))
    return completed, len(steps)


# =============================================================================
# Stdin parsing
# =============================================================================

def parse_stdin_task(stdin_content: str) -> dict:
    """Parse task definition from stdin TOON format."""
    result = {
        'title': '',
        'deliverables': [],
        'domain': '',
        'profile': 'implementation',
        'type': 'IMPL',
        'skills': [],
        'origin': 'plan',
        'phase': 'execute',
        'description': '',
        'steps': [],
        'depends_on': [],
        'priority': None,
        'finding': None,
        'delegation': {
            'skill': '',
            'workflow': '',
            'domain': '',
            'context_skills': []
        },
        'verification': {
            'commands': [],
            'criteria': '',
            'manual': False
        }
    }

    lines = stdin_content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        if line.startswith('title:'):
            result['title'] = line[6:].strip()
            i += 1

        elif line.startswith('deliverables:'):
            value = line[13:].strip()
            if value.startswith('[') and value.endswith(']'):
                inner = value[1:-1]
                if inner.strip():
                    result['deliverables'] = [int(x.strip()) for x in inner.split(',')]
            i += 1

        elif line.startswith('domain:'):
            result['domain'] = line[7:].strip()
            i += 1

        elif line.startswith('phase:'):
            result['phase'] = line[6:].strip()
            i += 1

        elif line.startswith('profile:'):
            result['profile'] = line[8:].strip()
            i += 1

        elif line.startswith('origin:'):
            result['origin'] = line[7:].strip()
            i += 1

        elif line.startswith('type:'):
            result['type'] = line[5:].strip()
            i += 1

        elif line.startswith('priority:'):
            result['priority'] = line[9:].strip()
            i += 1

        elif line.startswith('skills:'):
            i += 1
            while i < len(lines) and lines[i].startswith('  - '):
                skill = lines[i][4:].strip()
                if skill:
                    result['skills'].append(skill)
                i += 1

        elif line.startswith('description:'):
            rest = line[12:].strip()
            if rest == '|':
                desc_lines = []
                i += 1
                while i < len(lines):
                    if lines[i].startswith('  '):
                        desc_lines.append(lines[i][2:])
                    elif lines[i].strip() == '':
                        desc_lines.append('')
                    else:
                        break
                    i += 1
                result['description'] = '\n'.join(desc_lines).strip()
            else:
                result['description'] = rest
                i += 1

        elif line.startswith('steps:'):
            i += 1
            while i < len(lines) and lines[i].startswith('  - '):
                step_title = lines[i][4:].strip()
                if step_title:
                    result['steps'].append(step_title)
                i += 1

        elif line.startswith('depends_on:'):
            value = line[11:].strip()
            result['depends_on'] = parse_depends_on(value)
            i += 1

        elif line.startswith('delegation:'):
            i += 1
            while i < len(lines) and lines[i].startswith('  '):
                stripped = lines[i].strip()
                if stripped.startswith('skill:'):
                    result['delegation']['skill'] = stripped[6:].strip()
                elif stripped.startswith('workflow:'):
                    result['delegation']['workflow'] = stripped[9:].strip()
                elif stripped.startswith('context_skills:'):
                    i += 1
                    while i < len(lines) and lines[i].startswith('    - '):
                        skill = lines[i][6:].strip()
                        if skill:
                            result['delegation']['context_skills'].append(skill)
                        i += 1
                    continue
                i += 1

        elif line.startswith('verification:'):
            i += 1
            while i < len(lines) and lines[i].startswith('  '):
                stripped = lines[i].strip()
                if stripped.startswith('commands:'):
                    i += 1
                    while i < len(lines) and lines[i].startswith('    - '):
                        cmd = lines[i][6:].strip()
                        if cmd:
                            result['verification']['commands'].append(cmd)
                        i += 1
                    continue
                elif stripped.startswith('criteria:'):
                    result['verification']['criteria'] = stripped[9:].strip()
                elif stripped.startswith('manual:'):
                    val = stripped[7:].strip().lower()
                    result['verification']['manual'] = val == 'true'
                i += 1

        else:
            i += 1

    # Copy domain to delegation block
    if result['domain']:
        result['delegation']['domain'] = result['domain']

    # Validate required fields
    if not result['title']:
        raise ValueError("Missing required field: title")
    if not result['deliverables']:
        raise ValueError("Missing required field: deliverables")
    if not result['domain']:
        raise ValueError("Missing required field: domain")
    if not result['steps']:
        raise ValueError("Missing required field: steps (at least one step required)")

    validate_domain(result['domain'])
    validate_phase(result['phase'])
    validate_profile(result['profile'])
    validate_type(result['type'])
    validate_deliverables(result['deliverables'])
    result['skills'] = validate_skills(result['skills'])
    if result['origin']:
        validate_origin(result['origin'])

    step_errors, step_warnings = validate_steps_are_file_paths(result['steps'])
    if step_errors:
        raise ValueError(
            "Task contract violation - steps must be file paths:\n" +
            "\n".join(step_errors) +
            "\n\nContract reference: pm-workflow:manage-tasks/standards/task-contract.md"
        )

    return result


# =============================================================================
# Output formatting
# =============================================================================

def format_list_value(val) -> str:
    """Format a list value for TOON output."""
    if isinstance(val, list):
        return f"[{', '.join(str(v) for v in val)}]"
    return str(val)


def output_toon(data: dict) -> None:
    """Print TOON formatted output."""
    lines = []

    # Top-level simple fields
    for key in ['status', 'plan_id', 'file', 'renamed', 'total_tasks', 'task_number', 'step', 'phase_filter',
                'domain_filter', 'profile_filter', 'ready_count', 'in_progress_count', 'blocked_count']:
        if key in data:
            lines.append(f"{key}: {data[key]}")

    # Task/step status fields
    for key in ['task_status', 'step_status', 'step_title', 'next_step', 'next_step_title', 'message']:
        if key in data:
            val = data[key]
            if val is None:
                lines.append(f"{key}: null")
            else:
                lines.append(f"{key}: {val}")

    # Counts block
    if 'counts' in data:
        lines.append("")
        lines.append("counts:")
        for k, v in data['counts'].items():
            if isinstance(v, dict):
                lines.append(f"  {k}:")
                for k2, v2 in v.items():
                    lines.append(f"    {k2}: {v2}")
            else:
                lines.append(f"  {k}: {v}")

    # Single task block
    if 'task' in data:
        lines.append("")
        lines.append("task:")
        task = data['task']
        for key in ['number', 'title', 'domain', 'profile', 'type', 'phase', 'origin', 'status', 'current_step', 'created', 'updated', 'step_count']:
            if key in task and task[key] is not None:
                lines.append(f"  {key}: {task[key]}")
        if 'skills' in task:
            skills = task['skills']
            if skills:
                lines.append(f"  skills: {format_list_value(skills)}")
            else:
                lines.append("  skills: []")
        if 'deliverables' in task:
            lines.append(f"  deliverables: {format_list_value(task['deliverables'])}")
        if 'depends_on' in task:
            deps = task['depends_on']
            if deps:
                lines.append(f"  depends_on: {format_list_value(deps)}")
            else:
                lines.append("  depends_on: none")
        if 'description' in task:
            lines.append(f"  description: {task['description']}")
        if 'delegation' in task:
            deleg = task['delegation']
            lines.append("  delegation:")
            lines.append(f"    skill: {deleg.get('skill', '')}")
            lines.append(f"    workflow: {deleg.get('workflow', '')}")
            lines.append(f"    domain: {deleg.get('domain', '')}")
            ctx_skills = deleg.get('context_skills', [])
            if ctx_skills:
                lines.append(f"    context_skills: {format_list_value(ctx_skills)}")
        if 'steps' in task:
            steps = task['steps']
            lines.append(f"  steps[{len(steps)}]{{number,title,status}}:")
            for s in steps:
                lines.append(f"  {s['number']},{s['title']},{s['status']}")
        if 'verification' in task:
            verif = task['verification']
            lines.append("  verification:")
            cmds = verif.get('commands', [])
            lines.append(f"    commands[{len(cmds)}]:")
            for cmd in cmds:
                lines.append(f"    - {cmd}")
            lines.append(f"    criteria: {verif.get('criteria', '')}")
            lines.append(f"    manual: {'true' if verif.get('manual', False) else 'false'}")

    # Removed block
    if 'removed' in data:
        lines.append("")
        lines.append("removed:")
        rem = data['removed']
        for key in ['number', 'title', 'file']:
            if key in rem:
                lines.append(f"  {key}: {rem[key]}")

    # Blocked tasks block
    if 'blocked_tasks' in data:
        blocked = data['blocked_tasks']
        lines.append("")
        lines.append(f"blocked_tasks[{len(blocked)}]{{number,title,waiting_for}}:")
        for bt in blocked:
            waiting = bt.get('waiting_for', [])
            if isinstance(waiting, list):
                waiting = ', '.join(waiting)
            lines.append(f"{bt['number']},{bt['title']},{waiting}")

    # Ready tasks block (for next-tasks command)
    if 'ready_tasks' in data:
        ready = data['ready_tasks']
        lines.append("")
        lines.append(f"ready_tasks[{len(ready)}]{{number,title,domain,profile,progress}}:")
        for rt in ready:
            domain = rt.get('domain') or ''
            profile = rt.get('profile') or ''
            lines.append(f"{rt['number']},{rt['title']},{domain},{profile},{rt['progress']}")
            if rt.get('skills'):
                lines.append(f"  skills: {format_list_value(rt['skills'])}")
            if rt.get('deliverables'):
                lines.append(f"  deliverables: {format_list_value(rt['deliverables'])}")

    # In-progress tasks block (for next-tasks command)
    if 'in_progress_tasks' in data:
        in_prog = data['in_progress_tasks']
        lines.append("")
        lines.append(f"in_progress_tasks[{len(in_prog)}]{{number,title,domain,profile,progress}}:")
        for it in in_prog:
            domain = it.get('domain') or ''
            profile = it.get('profile') or ''
            lines.append(f"{it['number']},{it['title']},{domain},{profile},{it['progress']}")
            if it.get('skills'):
                lines.append(f"  skills: {format_list_value(it['skills'])}")

    # Next block
    if 'next' in data:
        lines.append("")
        if data['next'] is None:
            lines.append("next: null")
        else:
            lines.append("next:")
            nxt = data['next']
            for key in ['task_number', 'task_title', 'domain', 'profile', 'origin', 'phase', 'step_number', 'step_title',
                        'deliverables_found', 'deliverable_count', 'deliverables_source']:
                if key in nxt:
                    val = nxt[key]
                    if isinstance(val, bool):
                        val = 'true' if val else 'false'
                    lines.append(f"  {key}: {val}")
            if 'skills' in nxt:
                skills = nxt['skills']
                if skills:
                    lines.append("  skills:")
                    for skill in skills:
                        lines.append(f"    - {skill}")
                else:
                    lines.append("  skills: []")
            if 'deliverables' in nxt:
                lines.append(f"  deliverables: {format_list_value(nxt['deliverables'])}")

    # Context block
    if 'context' in data:
        lines.append("")
        lines.append("context:")
        ctx = data['context']
        for k, v in ctx.items():
            lines.append(f"  {k}: {v}")

    # Tasks list (tabular)
    if 'tasks_table' in data:
        tasks = data['tasks_table']
        lines.append("")
        lines.append(f"tasks[{len(tasks)}]{{number,title,domain,profile,phase,deliverables,status,progress}}:")
        for t in tasks:
            delivs = format_list_value(t.get('deliverables', []))
            domain = t.get('domain') or ''
            profile = t.get('profile') or ''
            lines.append(f"{t['number']},{t['title']},{domain},{profile},{t.get('phase', 'execute')},{delivs},{t['status']},{t['progress']}")

    print('\n'.join(lines))


def output_error(message: str) -> None:
    """Print TOON error output to stderr."""
    print(f"status: error\nmessage: {message}", file=sys.stderr)


def get_deliverable_context(deliverables: List[int]) -> dict:
    """Get deliverable details for including in task context."""
    return {
        'deliverables_found': True,
        'deliverable_count': len(deliverables),
        'deliverables': deliverables,
        'deliverables_source': f'See solution_outline.md sections: {", ".join(f"### {d}." for d in deliverables)}'
    }

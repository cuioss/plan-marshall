#!/usr/bin/env python3
"""
Shared utilities for manage-tasks.py modular implementation.

Contains:
- JSON persistence utilities (storage format)
- TOON output formatting (LLM-optimized output)
- Task file operations
- Validation functions
"""

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict, cast

from file_ops import base_path  # type: ignore[import-not-found]

# =============================================================================
# Type definitions
# =============================================================================


class VerificationDict(TypedDict, total=False):
    commands: list[str]
    criteria: str
    manual: bool


class StepDict(TypedDict):
    number: int
    title: str
    status: str


class TaskDict(TypedDict, total=False):
    number: int
    title: str
    status: str
    phase: str
    domain: str | None
    profile: str | None
    type: str
    origin: str
    created: str
    updated: str
    description: str
    steps: list[StepDict]
    deliverables: list[int]
    depends_on: list[str]
    skills: list[str]
    verification: VerificationDict
    current_step: int


# =============================================================================
# Constants
# =============================================================================

# Domains are arbitrary strings - defined in marshal.json, not hardcoded
VALID_PHASES = ['1-init', '2-refine', '3-outline', '4-plan', '5-execute', '6-verify', '7-finalize']
# Profiles are arbitrary strings - defined in marshal.json per-domain, not hardcoded
VALID_ORIGINS = ['plan', 'fix']
# Task types per target architecture
VALID_TYPES = ['IMPL', 'FIX', 'SONAR', 'PR', 'LINT', 'SEC', 'DOC']
VALID_FILE_EXTENSIONS = [
    '.md',
    '.py',
    '.java',
    '.js',
    '.ts',
    '.tsx',
    '.jsx',
    '.json',
    '.yaml',
    '.yml',
    '.xml',
    '.sh',
    '.bash',
    '.properties',
    '.adoc',
    '.toon',
    '.html',
    '.css',
]


# =============================================================================
# Basic utilities
# =============================================================================


def now_iso() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


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


def validate_deliverables(deliverables_input) -> list[int]:
    """Validate deliverables list."""
    if deliverables_input is None or len(deliverables_input) == 0:
        raise ValueError('At least one deliverable is required')

    result = []
    for item in deliverables_input:
        if isinstance(item, int):
            if item < 1:
                raise ValueError(f'Invalid deliverable number: {item}. Must be positive integer.')
            result.append(item)
        else:
            item_str = str(item).strip()
            if not item_str:
                continue
            if item_str.isdigit():
                num = int(item_str)
                if num < 1:
                    raise ValueError(f'Invalid deliverable number: {num}. Must be positive integer.')
                result.append(num)
            else:
                raise ValueError(f'Invalid deliverable format: {item_str}. Expected positive integer.')

    if len(result) == 0:
        raise ValueError('At least one deliverable is required')

    return result


def validate_domain(domain: str) -> str:
    """Validate domain value (accepts any non-empty string).

    Domains are arbitrary keys in marshal.json. Validation happens
    at skill resolution time, not at task creation time.
    """
    if not domain or not domain.strip():
        raise ValueError('Domain cannot be empty')
    return domain.strip()


def validate_type(task_type: str) -> str:
    """Validate task type value."""
    if task_type not in VALID_TYPES:
        raise ValueError(f'Invalid type: {task_type}. Must be one of: {", ".join(VALID_TYPES)}')
    return task_type


def validate_phase(phase: str) -> str:
    """Validate phase value."""
    if phase not in VALID_PHASES:
        raise ValueError(f'Invalid phase: {phase}. Must be one of: {", ".join(VALID_PHASES)}')
    return phase


def validate_profile(profile: str) -> str:
    """Validate profile value (accepts any non-empty string).

    Profiles are arbitrary keys in marshal.json. Validation happens
    at skill resolution time, not at task creation time.
    """
    if not profile or not profile.strip():
        raise ValueError('Profile cannot be empty')
    return profile.strip()


def validate_origin(origin: str) -> str:
    """Validate origin value."""
    if origin not in VALID_ORIGINS:
        raise ValueError(f'Invalid origin: {origin}. Must be one of: {", ".join(VALID_ORIGINS)}')
    return origin


def validate_skills(skills: list[str]) -> list[str]:
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
            'update ',
            'create ',
            'implement ',
            'add ',
            'fix ',
            'migrate ',
            'convert ',
            'modify ',
            'change ',
            'remove ',
            'delete ',
            ' to ',
            ' from ',
            ' with ',
            ' for ',
        ]
        step_lower = step.lower()
        for pattern in descriptive_patterns:
            if pattern in step_lower:
                warnings.append(f"Step {i}: '{step[:50]}' looks like descriptive text rather than a file path.")
                break

    return errors, warnings


# =============================================================================
# Dependency parsing
# =============================================================================


def parse_depends_on(depends_str: str) -> list[str]:
    """Parse depends_on field from TOON format."""
    if not depends_str or depends_str.strip().lower() == 'none':
        return []

    parts = [p.strip() for p in depends_str.split(',')]
    result = []
    for part in parts:
        if part.startswith('TASK-'):
            result.append(part)
        elif part.isdigit():
            result.append(f'TASK-{int(part)}')
    return result


def format_depends_on(deps: list[str]) -> str:
    """Format depends_on for file storage."""
    if not deps:
        return 'none'
    return ', '.join(deps)


# =============================================================================
# Task file operations
# =============================================================================


def get_tasks_dir(plan_id: str) -> Path:
    """Get the tasks directory for a plan."""
    return cast(Path, base_path('plans', plan_id, 'tasks'))


def parse_task_file(content: str) -> dict[str, Any]:
    """Parse a task JSON file into a dictionary.

    Uses stdlib json for robust parsing.
    """
    task: dict[str, Any] = json.loads(content)

    # Ensure required fields have defaults
    if 'steps' not in task:
        task['steps'] = []
    if 'deliverables' not in task:
        task['deliverables'] = []
    if 'depends_on' not in task:
        task['depends_on'] = []
    if 'skills' not in task:
        task['skills'] = []
    if 'verification' not in task:
        task['verification'] = {'commands': [], 'criteria': '', 'manual': False}
    if 'domain' not in task:
        task['domain'] = None
    if 'profile' not in task:
        task['profile'] = None
    if 'type' not in task:
        task['type'] = 'IMPL'
    if 'origin' not in task:
        task['origin'] = 'plan'

    return task


def format_task_file(task: dict) -> str:
    """Format a task dictionary as JSON file content.

    Uses stdlib json for robust serialization.
    """
    return json.dumps(task, indent=2, ensure_ascii=False)


def find_task_file(task_dir: Path, number: int) -> Path | None:
    """Find task file by number."""
    pattern = f'TASK-{number:03d}-*.json'
    matches = list(task_dir.glob(pattern))
    return matches[0] if matches else None


def get_next_number(task_dir: Path) -> int:
    """Get next available task number."""
    if not task_dir.exists():
        return 1

    max_num = 0
    for f in task_dir.glob('TASK-*.json'):
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
    for f in sorted(task_dir.glob('TASK-*.json')):
        content = f.read_text(encoding='utf-8')
        task = parse_task_file(content)
        tasks.append((f, task))

    return sorted(tasks, key=lambda x: x[1].get('number', 0))


def calculate_progress(task: dict) -> tuple[int, int]:
    """Calculate step completion progress."""
    steps = task.get('steps', [])
    completed = sum(1 for s in steps if s['status'] in ('done', 'skipped'))
    return completed, len(steps)


# =============================================================================
# Stdin parsing
# =============================================================================


def parse_stdin_task(stdin_content: str) -> dict[str, Any]:
    """Parse task definition from stdin TOON format."""
    # Create typed local variables for mutable fields
    deliverables: list[int] = []
    skills: list[str] = []
    steps: list[str] = []
    depends_on: list[str] = []
    verification_commands: list[str] = []

    verification: dict[str, Any] = {'commands': verification_commands, 'criteria': '', 'manual': False}

    result: dict[str, Any] = {
        'title': '',
        'deliverables': deliverables,
        'domain': '',
        'profile': 'implementation',
        'type': 'IMPL',
        'skills': skills,
        'origin': 'plan',
        'phase': 'execute',
        'description': '',
        'steps': steps,
        'depends_on': depends_on,
        'verification': verification,
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

        elif line.startswith('skills:'):
            i += 1
            while i < len(lines) and lines[i].startswith('  - '):
                skill = lines[i][4:].strip()
                if skill:
                    skills.append(skill)
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
                    steps.append(step_title)
                i += 1

        elif line.startswith('depends_on:'):
            value = line[11:].strip()
            result['depends_on'] = parse_depends_on(value)
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
                            verification_commands.append(cmd)
                        i += 1
                    continue
                elif stripped.startswith('criteria:'):
                    verification['criteria'] = stripped[9:].strip()
                elif stripped.startswith('manual:'):
                    val = stripped[7:].strip().lower()
                    verification['manual'] = val == 'true'
                i += 1

        else:
            i += 1

    # Validate required fields
    if not result['title']:
        raise ValueError('Missing required field: title')
    if not result['deliverables']:
        raise ValueError('Missing required field: deliverables')
    if not result['domain']:
        raise ValueError('Missing required field: domain')
    if not result['steps']:
        raise ValueError('Missing required field: steps (at least one step required)')

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
            'Task contract violation - steps must be file paths:\n'
            + '\n'.join(step_errors)
            + '\n\nContract reference: pm-workflow:manage-tasks/standards/task-contract.md'
        )

    return result


# =============================================================================
# Output formatting
# =============================================================================


def format_list_value(val) -> str:
    """Format a list value for TOON output."""
    if isinstance(val, list):
        return f'[{", ".join(str(v) for v in val)}]'
    return str(val)


def output_toon(data: dict) -> None:
    """Print TOON formatted output."""
    lines = []

    # Top-level simple fields
    for key in [
        'status',
        'plan_id',
        'file',
        'renamed',
        'total_tasks',
        'task_number',
        'step',
        'phase_filter',
        'domain_filter',
        'profile_filter',
        'ready_count',
        'in_progress_count',
        'blocked_count',
        'progress',
        'task_complete',
    ]:
        if key in data:
            val = data[key]
            if isinstance(val, bool):
                val = 'true' if val else 'false'
            lines.append(f'{key}: {val}')

    # Task/step status fields
    for key in ['task_status', 'step_status', 'step_title', 'next_step', 'next_step_title', 'message']:
        if key in data:
            val = data[key]
            if val is None:
                lines.append(f'{key}: null')
            else:
                lines.append(f'{key}: {val}')

    # Finalized step block (for finalize-step command)
    if 'finalized' in data:
        lines.append('')
        lines.append('finalized:')
        fin = data['finalized']
        for key in ['step_number', 'step_title', 'outcome', 'reason']:
            if key in fin:
                lines.append(f'  {key}: {fin[key]}')

    # Next step block (structured format for finalize-step)
    if 'next_step' in data and isinstance(data['next_step'], dict):
        lines.append('')
        nxt = data['next_step']
        if nxt is None:
            lines.append('next_step: null')
        else:
            lines.append('next_step:')
            for key in ['number', 'title']:
                if key in nxt:
                    lines.append(f'  {key}: {nxt[key]}')

    # Counts block
    if 'counts' in data:
        lines.append('')
        lines.append('counts:')
        for k, v in data['counts'].items():
            if isinstance(v, dict):
                lines.append(f'  {k}:')
                for k2, v2 in v.items():
                    lines.append(f'    {k2}: {v2}')
            else:
                lines.append(f'  {k}: {v}')

    # Single task block
    if 'task' in data:
        lines.append('')
        lines.append('task:')
        task = data['task']
        for key in [
            'number',
            'title',
            'domain',
            'profile',
            'type',
            'phase',
            'origin',
            'status',
            'current_step',
            'created',
            'updated',
            'step_count',
        ]:
            if key in task and task[key] is not None:
                lines.append(f'  {key}: {task[key]}')
        if 'skills' in task:
            skills = task['skills']
            if skills:
                lines.append(f'  skills: {format_list_value(skills)}')
            else:
                lines.append('  skills: []')
        if 'deliverables' in task:
            lines.append(f'  deliverables: {format_list_value(task["deliverables"])}')
        if 'depends_on' in task:
            deps = task['depends_on']
            if deps:
                lines.append(f'  depends_on: {format_list_value(deps)}')
            else:
                lines.append('  depends_on: none')
        if 'description' in task:
            lines.append(f'  description: {task["description"]}')
        if 'steps' in task:
            steps = task['steps']
            lines.append(f'  steps[{len(steps)}]{{number,title,status}}:')
            for s in steps:
                lines.append(f'  {s["number"]},{s["title"]},{s["status"]}')
        if 'verification' in task:
            verif = task['verification']
            lines.append('  verification:')
            cmds = verif.get('commands', [])
            lines.append(f'    commands[{len(cmds)}]:')
            for cmd in cmds:
                lines.append(f'    - {cmd}')
            lines.append(f'    criteria: {verif.get("criteria", "")}')
            lines.append(f'    manual: {"true" if verif.get("manual", False) else "false"}')

    # Removed block
    if 'removed' in data:
        lines.append('')
        lines.append('removed:')
        rem = data['removed']
        for key in ['number', 'title', 'file']:
            if key in rem:
                lines.append(f'  {key}: {rem[key]}')

    # Blocked tasks block
    if 'blocked_tasks' in data:
        blocked = data['blocked_tasks']
        lines.append('')
        lines.append(f'blocked_tasks[{len(blocked)}]{{number,title,waiting_for}}:')
        for bt in blocked:
            waiting = bt.get('waiting_for', [])
            if isinstance(waiting, list):
                waiting = ', '.join(waiting)
            lines.append(f'{bt["number"]},{bt["title"]},{waiting}')

    # Ready tasks block (for next-tasks command)
    if 'ready_tasks' in data:
        ready = data['ready_tasks']
        lines.append('')
        lines.append(f'ready_tasks[{len(ready)}]{{number,title,domain,profile,progress}}:')
        for rt in ready:
            domain = rt.get('domain') or ''
            profile = rt.get('profile') or ''
            lines.append(f'{rt["number"]},{rt["title"]},{domain},{profile},{rt["progress"]}')
            if rt.get('skills'):
                lines.append(f'  skills: {format_list_value(rt["skills"])}')
            if rt.get('deliverables'):
                lines.append(f'  deliverables: {format_list_value(rt["deliverables"])}')

    # In-progress tasks block (for next-tasks command)
    if 'in_progress_tasks' in data:
        in_prog = data['in_progress_tasks']
        lines.append('')
        lines.append(f'in_progress_tasks[{len(in_prog)}]{{number,title,domain,profile,progress}}:')
        for it in in_prog:
            domain = it.get('domain') or ''
            profile = it.get('profile') or ''
            lines.append(f'{it["number"]},{it["title"]},{domain},{profile},{it["progress"]}')
            if it.get('skills'):
                lines.append(f'  skills: {format_list_value(it["skills"])}')

    # Next block
    if 'next' in data:
        lines.append('')
        if data['next'] is None:
            lines.append('next: null')
        else:
            lines.append('next:')
            nxt = data['next']
            for key in [
                'task_number',
                'task_title',
                'domain',
                'profile',
                'origin',
                'phase',
                'step_number',
                'step_title',
                'deliverables_found',
                'deliverable_count',
                'deliverables_source',
            ]:
                if key in nxt:
                    val = nxt[key]
                    if isinstance(val, bool):
                        val = 'true' if val else 'false'
                    lines.append(f'  {key}: {val}')
            if 'skills' in nxt:
                skills = nxt['skills']
                if skills:
                    lines.append('  skills:')
                    for skill in skills:
                        lines.append(f'    - {skill}')
                else:
                    lines.append('  skills: []')
            if 'deliverables' in nxt:
                lines.append(f'  deliverables: {format_list_value(nxt["deliverables"])}')

    # Context block
    if 'context' in data:
        lines.append('')
        lines.append('context:')
        ctx = data['context']
        for k, v in ctx.items():
            lines.append(f'  {k}: {v}')

    # Tasks list (tabular)
    if 'tasks_table' in data:
        tasks = data['tasks_table']
        lines.append('')
        lines.append(f'tasks[{len(tasks)}]{{number,title,domain,profile,phase,deliverables,status,progress}}:')
        for t in tasks:
            delivs = format_list_value(t.get('deliverables', []))
            domain = t.get('domain') or ''
            profile = t.get('profile') or ''
            lines.append(
                f'{t["number"]},{t["title"]},{domain},{profile},{t.get("phase", "execute")},{delivs},{t["status"]},{t["progress"]}'
            )

    print('\n'.join(lines))


def output_error(message: str) -> None:
    """Print TOON error output to stderr."""
    print(f'status: error\nmessage: {message}', file=sys.stderr)


def get_deliverable_context(deliverables: list[int]) -> dict:
    """Get deliverable details for including in task context."""
    return {
        'deliverables_found': True,
        'deliverable_count': len(deliverables),
        'deliverables': deliverables,
        'deliverables_source': f'See solution_outline.md sections: {", ".join(f"### {d}." for d in deliverables)}',
    }

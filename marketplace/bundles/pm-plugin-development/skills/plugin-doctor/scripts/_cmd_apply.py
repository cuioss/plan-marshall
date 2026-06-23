#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Apply subcommand for applying fixes to component files."""

import ast
import json
import re
import shutil
from pathlib import Path

from _analyze_simplicity import _restates_signature_only
from _doctor_shared import read_json_input, resolve_runtime_target

# Target-aware agent-frontmatter emission. On Claude an agent pins its model
# with the bare alias ``model: sonnet``; on OpenCode the agent declares
# ``mode: subagent`` and a provider-qualified ``model: anthropic/<id>``. The
# active target is resolved through the platform-runtime layout op (via
# ``_doctor_shared.resolve_runtime_target``), so the fix handler emits the
# shape the active target's loader understands instead of hardcoding the
# Claude form.
_OPENCODE_AGENT_FRONTMATTER = 'tools: Read, Write, Edit\nmode: subagent\nmodel: anthropic/claude-sonnet-4\n'
_CLAUDE_AGENT_FRONTMATTER = 'tools: Read, Write, Edit\nmodel: sonnet\n'


def load_templates(script_dir: Path) -> dict:
    """Load fix templates from assets/fix-templates.json."""
    templates_path = script_dir.parent / 'assets' / 'fix-templates.json'
    if templates_path.exists():
        with open(templates_path, encoding='utf-8') as f:
            result: dict = json.load(f)
            return result
    return {}


def apply_missing_frontmatter(file_path: Path, fix: dict, templates: dict) -> dict:
    """Add frontmatter to a file that has none."""
    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    if content.strip().startswith('---'):
        return {'success': False, 'error': 'File already has frontmatter'}

    component_type = 'unknown'
    str_path = str(file_path)
    if '/agents/' in str_path:
        component_type = 'agent'
    elif '/commands/' in str_path:
        component_type = 'command'
    elif '/skills/' in str_path:
        component_type = 'skill'

    name = file_path.stem

    frontmatter = f"""---
name: {name}
description: [Description needed]
"""
    if component_type == 'agent':
        if resolve_runtime_target() == 'opencode':
            frontmatter += _OPENCODE_AGENT_FRONTMATTER
        else:
            frontmatter += _CLAUDE_AGENT_FRONTMATTER
    frontmatter += '---\n\n'

    new_content = frontmatter + content

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return {'success': True, 'changes': ['Added YAML frontmatter'], 'component_type': component_type}


def apply_array_syntax_fix(file_path: Path, fix: dict, templates: dict) -> dict:
    """Convert array syntax tools: [A, B] to comma-separated tools: A, B."""
    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    pattern = r'^(tools:\s*)\[([^\]]+)\]'
    replacement = r'\1\2'

    new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)

    if count == 0:
        return {'success': False, 'error': 'No array syntax found'}

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return {'success': True, 'changes': [f'Converted {count} array syntax to comma-separated'], 'replacements': count}


def apply_missing_field_fix(file_path: Path, fix: dict, templates: dict) -> dict:
    """Add a missing required field to frontmatter."""
    field_name = fix.get('type', '').replace('missing-', '').replace('-field', '')

    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    if not content.strip().startswith('---'):
        return {'success': False, 'error': 'No frontmatter found'}

    lines = content.split('\n')
    frontmatter_end = -1
    in_frontmatter = False

    for i, line in enumerate(lines):
        if line.strip() == '---':
            if not in_frontmatter:
                in_frontmatter = True
            else:
                frontmatter_end = i
                break

    if frontmatter_end == -1:
        return {'success': False, 'error': 'Invalid frontmatter structure'}

    defaults = {
        'name': file_path.stem,
        'description': '[Description needed]',
        'tools': 'Read',
        'user-invocable': 'false',
    }
    default_value = defaults.get(field_name, '[Value needed]')

    new_line = f'{field_name}: {default_value}'
    lines.insert(frontmatter_end, new_line)

    new_content = '\n'.join(lines)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return {'success': True, 'changes': [f'Added {field_name}: {default_value}'], 'field_added': field_name}


def apply_trailing_whitespace_fix(file_path: Path, fix: dict, templates: dict) -> dict:
    """Remove trailing whitespace from all lines."""
    with open(file_path, encoding='utf-8') as f:
        lines = f.readlines()

    fixed_count = 0
    new_lines = []
    for line in lines:
        stripped = line.rstrip() + ('\n' if line.endswith('\n') else '')
        if stripped != line:
            fixed_count += 1
        new_lines.append(stripped)

    if new_lines and not new_lines[-1].endswith('\n'):
        new_lines[-1] = new_lines[-1].rstrip()

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    return {
        'success': True,
        'changes': [f'Removed trailing whitespace from {fixed_count} lines'],
        'lines_fixed': fixed_count,
    }


def apply_task_tool_fix(file_path: Path, fix: dict, templates: dict) -> dict:
    """Remove Task tool from agent's tools declaration."""
    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    patterns = [
        (r'^(tools:.*),\s*Task\b', r'\1'),
        (r'^(tools:.*)\bTask,\s*', r'\1'),
        (r'^(tools:\s*)Task$', r'\1Read'),
    ]

    new_content = content
    changed = False
    for pattern, replacement in patterns:
        new_content, count = re.subn(pattern, replacement, new_content, flags=re.MULTILINE)
        if count > 0:
            changed = True

    if not changed:
        return {'success': False, 'error': 'Task tool not found in tools declaration'}

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return {'success': True, 'changes': ['Removed Task tool from tools declaration (agent-task-tool-prohibited)']}


def apply_skill_tool_visibility_fix(file_path: Path, fix: dict, templates: dict) -> dict:
    """Add Skill tool to agent's tools declaration (agent-skill-tool-visibility)."""
    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    # Find the tools or allowed-tools line
    match = re.search(r'^((?:tools|allowed-tools):\s*)(.+)$', content, re.MULTILINE)
    if not match:
        return {'success': False, 'error': 'No tools declaration found'}

    tools_str = match.group(2).strip()
    # Parse existing tools
    clean = tools_str.strip('[]')
    tools = [t.strip().strip('"').strip("'") for t in clean.split(',')]

    if 'Skill' in tools:
        return {'success': False, 'error': 'Skill tool already present in declaration'}

    # Append Skill to the tools line
    original_line = match.group(0)
    new_line = original_line.rstrip() + ', Skill'

    new_content = content.replace(original_line, new_line, 1)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return {'success': True, 'changes': ['Added Skill tool to tools declaration (agent-skill-tool-visibility)']}


def apply_unused_tool_fix(file_path: Path, fix: dict, templates: dict) -> dict:
    """Remove unused tools from declaration."""
    unused_tools = fix.get('details', {}).get('unused_tools', [])
    if not unused_tools:
        return {'success': False, 'error': 'No unused tools specified'}

    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    new_content = content
    removed = []
    for tool in unused_tools:
        patterns = [
            (rf',\s*{tool}\b', ''),
            (rf'\b{tool},\s*', ''),
        ]
        for pattern, replacement in patterns:
            new_content, count = re.subn(pattern, replacement, new_content, flags=re.MULTILINE)
            if count > 0:
                removed.append(tool)
                break

    if not removed:
        return {'success': False, 'error': 'Could not remove any unused tools'}

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return {'success': True, 'changes': [f'Removed unused tools: {", ".join(removed)}'], 'tools_removed': removed}


def apply_lessons_via_skill_fix(file_path: Path, fix: dict, templates: dict) -> dict:
    """Fix agent-lessons-via-skill violation by changing self-update to caller reporting."""
    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    replacements = [
        (r'/plugin-update-agent', 'report improvements to the caller'),
        (r'/plugin-update-command', 'report improvements to the caller'),
        (r'update this agent directly', 'report suggested improvements to the caller'),
        (r'Make the changes yourself', 'Let the caller decide whether to apply changes'),
    ]

    new_content = content
    changes_made = []
    for pattern, replacement in replacements:
        if re.search(pattern, new_content, re.IGNORECASE):
            new_content = re.sub(pattern, replacement, new_content, flags=re.IGNORECASE)
            changes_made.append(f"Replaced '{pattern}' with caller reporting")

    if not changes_made:
        return {'success': False, 'error': 'No agent-lessons-via-skill violations found to fix'}

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return {'success': True, 'changes': changes_made}


def apply_rename_frontmatter_field(file_path: Path, fix: dict, templates: dict) -> dict:
    """Rename a misspelled field in YAML frontmatter."""
    field_type = fix.get('type', '')
    # Map issue types to (old, new) field name pairs
    renames = {
        'misspelled-user-invocable': (r'^user-invokable:', 'user-invocable:'),
    }
    rename = renames.get(field_type)
    if not rename:
        return {'success': False, 'error': f'No rename mapping for fix type: {field_type}'}

    old_pattern, new_name = rename

    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    new_content, count = re.subn(old_pattern, new_name, content, count=1, flags=re.MULTILINE)
    if count == 0:
        return {'success': False, 'error': 'Misspelled field not found in frontmatter'}

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return {'success': True, 'changes': [f'Renamed misspelled field to {new_name}']}


def apply_invokable_mismatch_fix(file_path: Path, fix: dict, templates: dict) -> dict:
    """Change user-invocable: true to false for reference-mode skills."""
    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    new_content, count = re.subn(
        r'^(user-invocable:\s*)true', r'\1false', content, count=1, flags=re.MULTILINE | re.IGNORECASE
    )
    if count == 0:
        return {'success': False, 'error': 'user-invocable: true not found in frontmatter'}

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return {'success': True, 'changes': ['Changed user-invocable from true to false (reference-mode skill)']}


def apply_checklist_pattern_fix(file_path: Path, fix: dict, templates: dict) -> dict:
    """Remove checkbox patterns (- [ ] / - [x]) from markdown."""
    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    new_content = re.sub(r'^(- )\[ \] ', r'\1', content, flags=re.MULTILINE)
    new_content = re.sub(r'^(- )\[[xX]\] ', r'\1', new_content, flags=re.MULTILINE)

    if new_content == content:
        return {'success': False, 'error': 'No checkbox patterns found'}

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    old_lines = content.splitlines()
    new_lines = new_content.splitlines()
    changes = sum(1 for old, new in zip(old_lines, new_lines, strict=False) if old != new)

    return {'success': True, 'changes': [f'Removed {changes} checkbox patterns'], 'lines_fixed': changes}


def apply_signature_docstring_fix(file_path: Path, fix: dict, templates: dict) -> dict:
    """Delete function docstrings whose first paragraph only restates the signature.

    Mechanical removal for the ``SIMPLICITY_SIGNATURE_DOCSTRING`` rule: re-parse
    the file, find every function whose docstring matches the
    signature-restating predicate, and delete the docstring's source lines.
    Removals are applied bottom-up so earlier line numbers stay valid.
    """
    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        return {'success': False, 'error': f'Could not parse file: {exc}'}

    lines = content.split('\n')
    # Collect (start_line, end_line, sole_statement) 1-based inclusive ranges.
    # ``sole_statement`` is True when the docstring is the only statement in the
    # function body — deleting it outright would leave an empty block (a
    # SyntaxError), so the range is replaced with a ``pass`` instead.
    ranges: list[tuple[int, int, bool]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        docstring = ast.get_docstring(node, clean=False)
        if not docstring or not _restates_signature_only(docstring):
            continue
        if not node.body:
            continue
        first = node.body[0]
        if not (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)):
            continue
        end = first.end_lineno if first.end_lineno is not None else first.lineno
        sole_statement = len(node.body) == 1
        ranges.append((first.lineno, end, sole_statement))

    if not ranges:
        return {'success': False, 'error': 'No signature-restating docstrings found'}

    for start, end, sole_statement in sorted(ranges, key=lambda r: r[0], reverse=True):
        if sole_statement:
            # Preserve the docstring's indentation for the replacement ``pass``.
            indent = lines[start - 1][: len(lines[start - 1]) - len(lines[start - 1].lstrip())]
            lines[start - 1:end] = [f'{indent}pass']
        else:
            del lines[start - 1:end]

    new_content = '\n'.join(lines)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return {
        'success': True,
        'changes': [f'Removed {len(ranges)} signature-restating docstring(s)'],
        'docstrings_removed': len(ranges),
    }


FIX_HANDLERS = {
    'missing-frontmatter': apply_missing_frontmatter,
    'array-syntax-tools': apply_array_syntax_fix,
    'missing-name-field': apply_missing_field_fix,
    'missing-description-field': apply_missing_field_fix,
    'missing-tools-field': apply_missing_field_fix,
    'trailing-whitespace': apply_trailing_whitespace_fix,
    'agent-task-tool-prohibited': apply_task_tool_fix,
    'agent-skill-tool-visibility': apply_skill_tool_visibility_fix,
    'unused-tool-declared': apply_unused_tool_fix,
    'agent-lessons-via-skill': apply_lessons_via_skill_fix,
    'misspelled-user-invocable': apply_rename_frontmatter_field,
    'missing-user-invocable': apply_missing_field_fix,
    'skill-invokable-mismatch': apply_invokable_mismatch_fix,
    'checklist-pattern': apply_checklist_pattern_fix,
    'subdoc-checklist-pattern': apply_checklist_pattern_fix,
    'SIMPLICITY_SIGNATURE_DOCSTRING': apply_signature_docstring_fix,
}


def apply_single_fix(fix: dict, bundle_dir: Path, templates: dict) -> dict:
    """Apply a single fix to a component file."""
    fix_type = fix.get('type', '')
    file_path = fix.get('file', '')

    if not fix_type:
        return {'success': False, 'error': 'Missing fix type'}
    if not file_path:
        return {'success': False, 'error': 'Missing file path'}

    full_path = bundle_dir / file_path
    if not full_path.exists():
        return {'success': False, 'error': f'File not found: {full_path}'}

    backup_path = full_path.with_suffix(full_path.suffix + '.fix-backup')
    shutil.copy2(full_path, backup_path)

    handler = FIX_HANDLERS.get(fix_type)
    if not handler:
        return {'success': False, 'error': f'No handler for fix type: {fix_type}', 'backup_created': str(backup_path)}

    try:
        result = handler(full_path, fix, templates)
        result['fix_type'] = fix_type
        result['file'] = str(file_path)
        result['backup_created'] = str(backup_path)
        return result
    except Exception as e:
        shutil.copy2(backup_path, full_path)
        return {
            'success': False,
            'error': f'Fix failed: {str(e)}',
            'fix_type': fix_type,
            'file': str(file_path),
            'backup_restored': True,
        }


def cmd_apply(args) -> dict:
    """Apply a single fix to a component file."""
    data, error = read_json_input(args.fix)

    if error:
        return {'status': 'error', 'error': 'invalid_input', 'message': error, 'success': False}

    bundle_path = Path(args.bundle_dir)
    if not bundle_path.exists():
        return {
            'status': 'error',
            'error': 'not_found',
            'message': f'Bundle directory not found: {args.bundle_dir}',
            'success': False,
        }

    script_dir = Path(__file__).parent
    templates = load_templates(script_dir)

    if data is None:
        return {'status': 'error', 'error': 'no_data', 'message': 'No fix data provided', 'success': False}

    result = apply_single_fix(data, bundle_path, templates)
    result['status'] = 'success' if result.get('success') else 'error'
    return result

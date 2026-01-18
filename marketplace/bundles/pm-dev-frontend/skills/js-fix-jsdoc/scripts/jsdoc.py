#!/usr/bin/env python3
"""
JSDoc documentation analysis tool.

Subcommands:
    analyze  - Analyze JavaScript files for JSDoc compliance violations

Usage:
    jsdoc.py analyze --directory src/
    jsdoc.py analyze --file src/utils/formatter.js
    jsdoc.py analyze --directory src/ --scope missing
"""

import argparse
import json
import os
import re
import sys
from typing import Any

EXIT_SUCCESS = 0
EXIT_ERROR = 1


# =============================================================================
# ANALYZE SUBCOMMAND
# =============================================================================

# Patterns for JavaScript constructs that should have JSDoc
FUNCTION_PATTERN = re.compile(r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)', re.MULTILINE)

ARROW_FUNCTION_PATTERN = re.compile(
    r'^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>', re.MULTILINE
)

CLASS_PATTERN = re.compile(r'^(?:export\s+)?class\s+(\w+)', re.MULTILINE)

METHOD_PATTERN = re.compile(r'^\s+(?:async\s+)?(\w+)\s*\(([^)]*)\)\s*\{', re.MULTILINE)

CONSTRUCTOR_PATTERN = re.compile(r'^\s+constructor\s*\(([^)]*)\)', re.MULTILINE)

JSDOC_PATTERN = re.compile(r'/\*\*[\s\S]*?\*/', re.MULTILINE)
PARAM_TAG_PATTERN = re.compile(r'@param\s+(?:\{([^}]+)\}\s+)?(\w+)')
RETURNS_TAG_PATTERN = re.compile(r'@returns?\s+(?:\{([^}]+)\})?')
THROWS_TAG_PATTERN = re.compile(r'@throws?\s+(?:\{([^}]+)\})?')
EXAMPLE_TAG_PATTERN = re.compile(r'@example')
ASYNC_TAG_PATTERN = re.compile(r'@async')
FILEOVERVIEW_PATTERN = re.compile(r'@fileoverview')


def get_line_number(content: str, pos: int) -> int:
    """Get line number (1-based) for a position in content."""
    return content[:pos].count('\n') + 1


def find_preceding_jsdoc(content: str, pos: int) -> str | None:
    """Find JSDoc block immediately preceding a position."""
    preceding = content[:pos].rstrip()

    jsdoc_end = preceding.rfind('*/')
    if jsdoc_end == -1:
        return None

    between = preceding[jsdoc_end + 2 :]
    if between.strip():
        return None

    jsdoc_start = preceding.rfind('/**', 0, jsdoc_end)
    if jsdoc_start == -1:
        return None

    return preceding[jsdoc_start : jsdoc_end + 2]


def extract_function_params(param_str: str) -> list[str]:
    """Extract parameter names from function signature."""
    if not param_str.strip():
        return []

    params = []
    depth = 0
    current = ''

    for char in param_str:
        if char in '({[':
            depth += 1
            current += char
        elif char in ')}]':
            depth -= 1
            current += char
        elif char == ',' and depth == 0:
            param = current.strip()
            if param:
                if '=' in param:
                    param = param.split('=')[0].strip()
                if not param.startswith('{') and not param.startswith('['):
                    params.append(param)
            current = ''
        else:
            current += char

    param = current.strip()
    if param:
        if '=' in param:
            param = param.split('=')[0].strip()
        if not param.startswith('{') and not param.startswith('['):
            params.append(param)

    return params


def check_function_jsdoc(jsdoc: str, params: list[str], has_return: bool) -> list[dict]:
    """Check JSDoc block for a function, return violations."""
    violations = []

    documented_params = PARAM_TAG_PATTERN.findall(jsdoc)
    documented_param_names = [p[1] for p in documented_params]

    for param in params:
        if param not in documented_param_names:
            violations.append(
                {
                    'type': 'missing_param',
                    'severity': 'WARNING',
                    'message': f"@param tag missing for parameter '{param}'",
                    'fix_suggestion': f'Add @param {{type}} {param} - Description',
                }
            )

    for param_type, param_name in documented_params:
        if not param_type:
            violations.append(
                {
                    'type': 'missing_param_type',
                    'severity': 'WARNING',
                    'message': f'Type annotation missing for @param {param_name}',
                    'fix_suggestion': f'Add type: @param {{Type}} {param_name}',
                }
            )

    if has_return and not RETURNS_TAG_PATTERN.search(jsdoc):
        violations.append(
            {
                'type': 'missing_returns',
                'severity': 'WARNING',
                'message': '@returns tag missing for function that returns a value',
                'fix_suggestion': 'Add @returns {Type} Description',
            }
        )

    return violations


def analyze_file(file_path: str, scope: str) -> list[dict]:
    """Analyze a single file for JSDoc violations."""
    violations = []

    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return [
            {
                'file': file_path,
                'line': 0,
                'type': 'file_error',
                'severity': 'CRITICAL',
                'message': f'Failed to read file: {e}',
            }
        ]

    # Check for @fileoverview
    if scope in ('all', 'syntax'):
        first_jsdoc = JSDOC_PATTERN.search(content)
        if not first_jsdoc or not FILEOVERVIEW_PATTERN.search(first_jsdoc.group()):
            violations.append(
                {
                    'file': file_path,
                    'line': 1,
                    'type': 'missing_fileoverview',
                    'severity': 'SUGGESTION',
                    'target': 'file',
                    'message': 'Missing @fileoverview tag at file level',
                    'fix_suggestion': 'Add @fileoverview describing the module purpose',
                }
            )

    # Find all functions
    for match in FUNCTION_PATTERN.finditer(content):
        func_name = match.group(1)
        params_str = match.group(2)
        line_num = get_line_number(content, match.start())
        is_exported = 'export' in content[max(0, match.start() - 20) : match.start()]

        jsdoc = find_preceding_jsdoc(content, match.start())

        if scope in ('all', 'missing'):
            if not jsdoc:
                severity = 'CRITICAL' if is_exported else 'WARNING'
                violations.append(
                    {
                        'file': file_path,
                        'line': line_num,
                        'type': 'missing_jsdoc',
                        'severity': severity,
                        'target': f'function {func_name}',
                        'message': f"{'Exported f' if is_exported else 'F'}unction '{func_name}' missing JSDoc documentation",
                        'fix_suggestion': 'Add JSDoc block with @param and @returns tags',
                    }
                )

        if scope in ('all', 'syntax') and jsdoc:
            params = extract_function_params(params_str)
            func_end = content.find('{', match.end())
            if func_end != -1:
                brace_count = 1
                pos = func_end + 1
                has_return = False
                while pos < len(content) and brace_count > 0:
                    if content[pos] == '{':
                        brace_count += 1
                    elif content[pos] == '}':
                        brace_count -= 1
                    elif content[pos : pos + 6] == 'return' and brace_count == 1:
                        if pos == 0 or not content[pos - 1].isalnum():
                            has_return = True
                    pos += 1

                func_violations = check_function_jsdoc(jsdoc, params, has_return)
                for v in func_violations:
                    v['file'] = file_path
                    v['line'] = line_num
                    v['target'] = f'function {func_name}'
                    violations.append(v)

    # Find all arrow functions
    for match in ARROW_FUNCTION_PATTERN.finditer(content):
        func_name = match.group(1)
        line_num = get_line_number(content, match.start())
        is_exported = 'export' in content[max(0, match.start() - 20) : match.start()]

        jsdoc = find_preceding_jsdoc(content, match.start())

        if scope in ('all', 'missing') and not jsdoc:
            severity = 'CRITICAL' if is_exported else 'WARNING'
            violations.append(
                {
                    'file': file_path,
                    'line': line_num,
                    'type': 'missing_jsdoc',
                    'severity': severity,
                    'target': f'arrow function {func_name}',
                    'message': f"{'Exported a' if is_exported else 'A'}rrow function '{func_name}' missing JSDoc documentation",
                    'fix_suggestion': 'Add JSDoc block with @param and @returns tags',
                }
            )

    # Find all classes
    for match in CLASS_PATTERN.finditer(content):
        class_name = match.group(1)
        line_num = get_line_number(content, match.start())
        is_exported = 'export' in content[max(0, match.start() - 20) : match.start()]

        jsdoc = find_preceding_jsdoc(content, match.start())

        if scope in ('all', 'missing') and not jsdoc:
            violations.append(
                {
                    'file': file_path,
                    'line': line_num,
                    'type': 'missing_class_doc',
                    'severity': 'CRITICAL',
                    'target': f'class {class_name}',
                    'message': f"Class '{class_name}' is missing JSDoc documentation",
                    'fix_suggestion': 'Add JSDoc block describing the class purpose',
                }
            )

    # Find constructors
    for match in CONSTRUCTOR_PATTERN.finditer(content):
        params_str = match.group(1)
        line_num = get_line_number(content, match.start())

        jsdoc = find_preceding_jsdoc(content, match.start())

        if scope in ('all', 'missing') and not jsdoc and params_str.strip():
            violations.append(
                {
                    'file': file_path,
                    'line': line_num,
                    'type': 'missing_constructor_doc',
                    'severity': 'CRITICAL',
                    'target': 'constructor',
                    'message': 'Constructor with parameters is missing JSDoc documentation',
                    'fix_suggestion': 'Add JSDoc block with @param tags for constructor parameters',
                }
            )

    return violations


def find_js_files(directory: str) -> list[str]:
    """Find all JavaScript files in directory."""
    js_files = []

    for root, _, files in os.walk(directory):
        if 'node_modules' in root or 'dist' in root or 'build' in root:
            continue

        for file in files:
            if file.endswith('.js') or file.endswith('.mjs'):
                js_files.append(os.path.join(root, file))

    return js_files


def analyze_jsdoc(target: str, is_directory: bool, scope: str) -> dict[str, Any]:
    """Main analysis function."""
    if is_directory:
        if not os.path.isdir(target):
            return {'status': 'error', 'error': 'DIRECTORY_NOT_FOUND', 'message': f'Directory not found: {target}'}
        files = find_js_files(target)
    else:
        if not os.path.exists(target):
            return {'status': 'error', 'error': 'FILE_NOT_FOUND', 'message': f'File not found: {target}'}
        files = [target]

    if not files:
        return {
            'status': 'success',
            'data': {'violations': [], 'files_analyzed': 0},
            'metrics': {
                'total_files': 0,
                'files_with_violations': 0,
                'critical': 0,
                'warnings': 0,
                'suggestions': 0,
                'total_violations': 0,
            },
        }

    all_violations = []
    files_with_violations = set()

    for file_path in files:
        violations = analyze_file(file_path, scope)
        all_violations.extend(violations)
        if violations:
            files_with_violations.add(file_path)

    critical = sum(1 for v in all_violations if v.get('severity') == 'CRITICAL')
    warnings = sum(1 for v in all_violations if v.get('severity') == 'WARNING')
    suggestions = sum(1 for v in all_violations if v.get('severity') == 'SUGGESTION')

    status = 'violations_found' if all_violations else 'clean'

    return {
        'status': status,
        'data': {'violations': all_violations, 'files_analyzed': files},
        'metrics': {
            'total_files': len(files),
            'files_with_violations': len(files_with_violations),
            'critical': critical,
            'warnings': warnings,
            'suggestions': suggestions,
            'total_violations': len(all_violations),
        },
    }


def cmd_analyze(args) -> int:
    """Handle analyze subcommand."""
    if args.directory:
        result = analyze_jsdoc(args.directory, is_directory=True, scope=args.scope)
    else:
        result = analyze_jsdoc(args.file, is_directory=False, scope=args.scope)

    print(json.dumps(result, indent=2))

    if result.get('status') == 'error':
        return EXIT_ERROR
    return EXIT_SUCCESS


# =============================================================================
# MAIN
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description='JSDoc documentation analysis tool', formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # analyze subcommand
    analyze_parser = subparsers.add_parser('analyze', help='Analyze JavaScript files for JSDoc compliance violations')
    group = analyze_parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--directory', help='Directory to scan for JavaScript files')
    group.add_argument('--file', help='Single JavaScript file to analyze')
    analyze_parser.add_argument(
        '--scope',
        choices=['all', 'missing', 'syntax'],
        default='all',
        help='Analysis scope: all (default), missing, or syntax',
    )
    analyze_parser.set_defaults(func=cmd_analyze)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == '__main__':
    sys.exit(main())

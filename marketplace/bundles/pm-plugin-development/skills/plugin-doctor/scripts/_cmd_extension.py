#!/usr/bin/env python3
"""Extension validation subcommand.

Validates extension.py files in plan-marshall-plugin skills.
Checks contract compliance and extension API consistency.

Validation includes:
- Required function presence and signatures
- get_skill_domains() return value structure
- Skill reference existence (bundle:skill paths)
- Required canonical command coverage for build bundles

Output: JSON to stdout.
"""

import ast
import importlib.util
from pathlib import Path
from typing import Any

# Script-relative path discovery (works regardless of cwd)
# Script is at: marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/
# So marketplace directory is 5 levels up from script
SCRIPT_DIR = Path(__file__).resolve().parent
_MARKETPLACE_FROM_SCRIPT = SCRIPT_DIR.parent.parent.parent.parent.parent

# Required methods for Extension class (self is implicit, not listed)
# Only get_skill_domains is required as an abstract method
REQUIRED_METHODS = {
    'get_skill_domains': {'args': [], 'return_type': 'dict', 'description': 'Return domain metadata for skill loading'}
}

# Optional methods with defaults provided by ExtensionBase
OPTIONAL_METHODS = {
    'discover_modules': {
        'args': ['project_root'],
        'return_type': 'list',
        'description': 'Discover modules with metadata and commands',
    },
    'provides_triage': {'args': [], 'return_type': 'str | None', 'description': 'Return triage skill reference'},
    'provides_outline_skill': {
        'args': [],
        'return_type': 'str | None',
        'description': 'Return domain-specific outline skill reference',
    },
}

# get_skill_domains is a required function (part of REQUIRED_FUNCTIONS)
# Moved to REQUIRED_FUNCTIONS for simplicity

# Valid profile categories for get_skill_domains()
VALID_PROFILE_CATEGORIES = [
    'core',
    'implementation',
    'module_testing',
    'integration_testing',
    'quality',
    'documentation',
]

# Required canonical commands for bundles that provide build systems (static mappings only)
# NOTE: Profile-based commands (integration-tests, coverage, quality-gate, performance)
# are NOT required in static mappings - they are generated from detected profiles
REQUIRED_CANONICAL_COMMANDS = ['module-tests', 'verify']


# =============================================================================
# Skill Reference Validation
# =============================================================================


def get_marketplace_root(extension_path: Path) -> Path | None:
    """Find marketplace root from extension path."""
    # Walk up to find marketplace/bundles
    current = extension_path.parent
    for _ in range(10):
        if current.name == 'bundles' and (current.parent / 'bundles').exists():
            return current.parent
        if (current / 'marketplace' / 'bundles').exists():
            return current / 'marketplace'
        current = current.parent
        if current == current.parent:
            break
    return None


def skill_exists(skill_ref, marketplace_root: Path) -> bool:
    """Check if a skill reference (bundle:skill or {skill: bundle:skill}) exists."""
    # Handle dict format: {'skill': 'bundle:skill', 'description': '...'}
    if isinstance(skill_ref, dict):
        skill_ref = skill_ref.get('skill', '')
    if not isinstance(skill_ref, str) or ':' not in skill_ref:
        return False

    bundle, skill = skill_ref.split(':', 1)
    skill_path = marketplace_root / 'bundles' / bundle / 'skills' / skill

    # Check for SKILL.md (primary) or at least skill directory with content
    return skill_path.is_dir() and (
        (skill_path / 'SKILL.md').exists()
        or len(list(skill_path.glob('*.md'))) > 0
        or len(list(skill_path.glob('scripts/*.py'))) > 0
    )


def validate_skill_references(domains: dict, marketplace_root: Path) -> list:
    """Validate that all skill references in profiles actually exist."""
    issues = []

    profiles = domains.get('profiles', {})

    for category, config in profiles.items():
        if not isinstance(config, dict):
            continue

        # Check defaults
        for skill_ref in config.get('defaults', []):
            if not skill_exists(skill_ref, marketplace_root):
                issues.append(
                    {
                        'type': 'missing_skill',
                        'skill': skill_ref,
                        'location': f'profiles.{category}.defaults',
                        'message': f"Skill reference '{skill_ref}' does not exist",
                    }
                )

        # Check optionals
        for skill_ref in config.get('optionals', []):
            if not skill_exists(skill_ref, marketplace_root):
                issues.append(
                    {
                        'type': 'missing_skill',
                        'skill': skill_ref,
                        'location': f'profiles.{category}.optionals',
                        'message': f"Skill reference '{skill_ref}' does not exist",
                    }
                )

    return issues


def agent_exists(agent_ref: str, marketplace_root: Path) -> bool:
    """Check if an agent reference (bundle:agent) exists."""
    if ':' not in agent_ref:
        return False

    bundle, agent = agent_ref.split(':', 1)
    agent_path = marketplace_root / 'bundles' / bundle / 'agents' / f'{agent}.md'

    return agent_path.is_file()


def validate_triage_and_outline_skill(module, marketplace_root: Path) -> list:
    """Validate provides_triage() and provides_outline_skill() return valid refs."""
    issues = []

    if hasattr(module, 'provides_triage'):
        try:
            triage = module.provides_triage()
            if triage is not None:
                if not isinstance(triage, str):
                    issues.append({'type': 'invalid_triage', 'message': 'provides_triage() must return str or None'})
                elif not skill_exists(triage, marketplace_root):
                    issues.append(
                        {
                            'type': 'missing_skill',
                            'skill': triage,
                            'location': 'provides_triage()',
                            'message': f"Triage skill '{triage}' does not exist",
                        }
                    )
        except Exception as e:
            issues.append({'type': 'triage_error', 'message': f'provides_triage() raised: {e}'})

    if hasattr(module, 'provides_outline_skill'):
        try:
            outline_skill = module.provides_outline_skill()
            if outline_skill is not None:
                if not isinstance(outline_skill, str):
                    issues.append(
                        {
                            'type': 'invalid_outline_skill',
                            'message': 'provides_outline_skill() must return str or None',
                        }
                    )
                elif not skill_exists(outline_skill, marketplace_root):
                    issues.append(
                        {
                            'type': 'missing_skill',
                            'skill': outline_skill,
                            'location': 'provides_outline_skill()',
                            'message': f"Outline skill '{outline_skill}' does not exist",
                        }
                    )
        except Exception as e:
            issues.append({'type': 'outline_skill_error', 'message': f'provides_outline_skill() raised: {e}'})

    return issues


# =============================================================================
# Domain Structure Validation
# =============================================================================


def validate_skill_domains_structure(domains: dict) -> list:
    """Validate the structure of get_skill_domains() return value."""
    issues = []

    # Must have 'domain' key
    if 'domain' not in domains:
        issues.append({'type': 'missing_domain', 'message': "get_skill_domains() missing 'domain' key"})
        return issues

    domain = domains['domain']

    # Domain must have key and name
    if not isinstance(domain, dict):
        issues.append({'type': 'invalid_domain', 'message': f'domain must be a dict, got {type(domain).__name__}'})
        return issues

    if 'key' not in domain:
        issues.append({'type': 'missing_domain_key', 'message': "domain missing 'key'"})
    elif not isinstance(domain['key'], str) or not domain['key']:
        issues.append({'type': 'invalid_domain_key', 'message': 'domain.key must be non-empty string'})

    if 'name' not in domain:
        issues.append({'type': 'missing_domain_name', 'message': "domain missing 'name'"})
    elif not isinstance(domain['name'], str) or not domain['name']:
        issues.append({'type': 'invalid_domain_name', 'message': 'domain.name must be non-empty string'})

    # Must have 'profiles' key
    if 'profiles' not in domains:
        issues.append({'type': 'missing_profiles', 'message': "get_skill_domains() missing 'profiles' key"})
        return issues

    profiles = domains['profiles']

    if not isinstance(profiles, dict):
        issues.append(
            {'type': 'invalid_profiles', 'message': f'profiles must be a dict, got {type(profiles).__name__}'}
        )
        return issues

    # Validate each profile category
    for category, config in profiles.items():
        if category not in VALID_PROFILE_CATEGORIES:
            issues.append(
                {
                    'type': 'unknown_category',
                    'category': category,
                    'severity': 'warning',
                    'message': f"Unknown profile category '{category}'",
                }
            )
            continue

        if not isinstance(config, dict):
            issues.append(
                {
                    'type': 'invalid_category_config',
                    'category': category,
                    'message': f'profiles.{category} must be a dict',
                }
            )
            continue

        # Must have defaults and optionals
        if 'defaults' not in config:
            issues.append(
                {'type': 'missing_defaults', 'category': category, 'message': f"profiles.{category} missing 'defaults'"}
            )
        elif not isinstance(config['defaults'], list):
            issues.append(
                {
                    'type': 'invalid_defaults',
                    'category': category,
                    'message': f'profiles.{category}.defaults must be a list',
                }
            )

        if 'optionals' not in config:
            issues.append(
                {
                    'type': 'missing_optionals',
                    'category': category,
                    'message': f"profiles.{category} missing 'optionals'",
                }
            )
        elif not isinstance(config['optionals'], list):
            issues.append(
                {
                    'type': 'invalid_optionals',
                    'category': category,
                    'message': f'profiles.{category}.optionals must be a list',
                }
            )

    return issues


# =============================================================================
# Command Mapping Validation
# =============================================================================


def validate_command_mappings(mappings: dict[str, Any], build_systems: list[str]) -> list[dict[str, Any]]:
    """Validate command mappings cover required canonicals."""
    issues: list[dict[str, Any]] = []

    if not build_systems:
        # Non-build bundles should return empty mappings (not an error)
        return issues

    for build_system in build_systems:
        if build_system not in mappings:
            issues.append(
                {
                    'type': 'missing_build_system',
                    'build_system': build_system,
                    'message': f"Missing command mappings for '{build_system}'",
                }
            )
            continue

        system_mappings = mappings[build_system]

        # Check required canonical commands
        for canonical in REQUIRED_CANONICAL_COMMANDS:
            if canonical not in system_mappings:
                issues.append(
                    {
                        'type': 'missing_canonical',
                        'build_system': build_system,
                        'canonical': canonical,
                        'message': f"Missing required canonical command '{canonical}' for {build_system}",
                    }
                )

        # Validate command format
        for canonical, template in system_mappings.items():
            if not isinstance(template, str):
                issues.append(
                    {
                        'type': 'invalid_template',
                        'canonical': canonical,
                        'message': f'Command template for {canonical} must be string',
                    }
                )
                continue

            # Should use execute-script.py pattern
            if 'python3 .plan/execute-script.py' not in template:
                issues.append(
                    {
                        'type': 'non_standard_template',
                        'canonical': canonical,
                        'severity': 'warning',
                        'message': f"Command '{canonical}' should use execute-script.py pattern",
                    }
                )

    return issues


def parse_extension_file(extension_path: Path) -> tuple[bool, list[dict[str, Any]], dict[str, Any], bool]:
    """Parse extension.py file and extract method info from Extension class.

    Returns:
        (success, errors, methods, has_extension_class)
    """
    errors: list[dict[str, Any]] = []
    methods: dict[str, Any] = {}
    has_extension_class = False

    try:
        content = extension_path.read_text(encoding='utf-8')
    except OSError as e:
        return False, [{'type': 'read_error', 'message': str(e)}], {}, False

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        return False, [{'type': 'syntax_error', 'message': str(e), 'line': e.lineno}], {}, False

    # Look for Extension class
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'Extension':
            has_extension_class = True

            # Extract methods from Extension class
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    method_name = item.name
                    args = [arg.arg for arg in item.args.args]

                    # Remove 'self' from args for comparison
                    if args and args[0] == 'self':
                        args = args[1:]

                    # Try to extract return type annotation
                    return_type = None
                    if item.returns:
                        if isinstance(item.returns, ast.Name):
                            return_type = item.returns.id
                        elif isinstance(item.returns, ast.Constant):
                            return_type = str(item.returns.value)
                        elif isinstance(item.returns, ast.BinOp):
                            # Handle union types like str | None
                            return_type = ast.unparse(item.returns)

                    methods[method_name] = {'args': args, 'return_type': return_type, 'lineno': item.lineno}

            break

    return True, errors, methods, has_extension_class


def load_extension_module(extension_path: Path) -> Any:
    """Load an extension.py module and return Extension instance."""
    try:
        spec = importlib.util.spec_from_file_location(
            f'extension_{extension_path.parent.parent.parent.name}', extension_path
        )
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Return Extension instance if class exists
        if hasattr(module, 'Extension'):
            return module.Extension()
        return module
    except Exception:
        return None


def validate_extension(extension_path: Path, deep: bool = True) -> dict[str, Any]:
    """Validate a single extension.py file.

    Args:
        extension_path: Path to extension.py
        deep: If True, also validate return values by executing methods
    """
    issues: list[dict[str, Any]] = []
    methods: dict[str, Any] = {}
    result: dict[str, Any] = {'path': str(extension_path), 'valid': True, 'issues': issues, 'methods': methods}

    if not extension_path.exists():
        result['valid'] = False
        issues.append({'type': 'file_missing', 'message': f'Extension file not found: {extension_path}'})
        return result

    success, errors, parsed_methods, has_extension_class = parse_extension_file(extension_path)

    if not success:
        result['valid'] = False
        issues.extend(errors)
        return result

    if not has_extension_class:
        result['valid'] = False
        issues.append(
            {
                'type': 'missing_class',
                'message': 'Extension class not found. Extensions must define class Extension(ExtensionBase).',
            }
        )
        return result

    result['methods'] = parsed_methods

    # Check required methods
    for method_name, spec in REQUIRED_METHODS.items():
        if method_name not in parsed_methods:
            result['valid'] = False
            issues.append(
                {
                    'type': 'missing_method',
                    'method': method_name,
                    'message': f'Missing required method: {method_name}() - {spec["description"]}',
                }
            )
            continue

        method_info = parsed_methods[method_name]

        # Check arguments (self already removed by parser)
        expected_args = spec['args']
        actual_args = method_info['args']
        if actual_args != expected_args:
            issues.append(
                {
                    'type': 'wrong_args',
                    'method': method_name,
                    'expected': expected_args,
                    'actual': actual_args,
                    'severity': 'warning',
                    'message': f'{method_name}() has args {actual_args}, expected {expected_args}',
                }
            )

    # Deep validation: execute functions and validate return values
    if deep and result['valid']:
        module = load_extension_module(extension_path)
        if module:
            marketplace_root = get_marketplace_root(extension_path)

            # Validate get_skill_domains() structure and skill references
            if hasattr(module, 'get_skill_domains'):
                try:
                    all_domains = module.get_skill_domains()

                    for domains in all_domains:
                        # Validate structure
                        structure_issues = validate_skill_domains_structure(domains)
                        for issue in structure_issues:
                            if issue.get('severity') != 'warning':
                                result['valid'] = False
                        issues.extend(structure_issues)

                        # Validate skill references
                        if marketplace_root:
                            ref_issues = validate_skill_references(domains, marketplace_root)
                            if ref_issues:
                                result['valid'] = False
                            issues.extend(ref_issues)

                except Exception as e:
                    issues.append(
                        {
                            'type': 'execution_error',
                            'function': 'get_skill_domains',
                            'message': f'get_skill_domains() raised: {e}',
                        }
                    )

            # Validate provides_triage() and provides_outline_skill() references
            if marketplace_root:
                triage_outline_issues = validate_triage_and_outline_skill(module, marketplace_root)
                if triage_outline_issues:
                    result['valid'] = False
                issues.extend(triage_outline_issues)

    return result


def validate_bundle_consistency(bundle_path: Path) -> dict[str, Any]:
    """Validate consistency between extension.py and bundle structure."""
    issues: list[dict[str, Any]] = []
    result: dict[str, Any] = {'bundle': bundle_path.name, 'valid': True, 'issues': issues}

    extension_path = bundle_path / 'skills' / 'plan-marshall-plugin' / 'extension.py'

    if not extension_path.exists():
        # No extension - not an error, just skip
        result['has_extension'] = False
        return result

    result['has_extension'] = True

    # Parse extension to check for Extension class
    success, _, methods, has_extension_class = parse_extension_file(extension_path)

    if not success:
        result['valid'] = False
        issues.append({'type': 'parse_error', 'message': 'Failed to parse extension.py'})
        return result

    if not has_extension_class:
        result['valid'] = False
        issues.append({'type': 'missing_class', 'message': 'Extension class not found'})
        return result

    # Check if bundle provides build systems, it should have plan-marshall-plugin skill
    if 'provides_build_systems' in methods:
        # We can't easily determine what the function returns without executing it
        # So just check if plan-marshall-plugin skill exists
        build_ops_path = bundle_path / 'skills' / 'plan-marshall-plugin'

        # Only check for bundles that might have build systems
        # (pm-dev-java, pm-dev-frontend, etc.)
        if bundle_path.name in ['pm-dev-java', 'pm-dev-frontend']:
            if not build_ops_path.is_dir():
                issues.append(
                    {
                        'type': 'missing_build_operations',
                        'severity': 'warning',
                        'message': f'Bundle {bundle_path.name} may provide build systems but lacks plan-marshall-plugin skill',
                    }
                )

    return result


def scan_extensions(marketplace_root: Path) -> dict[str, Any]:
    """Scan all bundles for extension.py files."""
    bundles_path = marketplace_root / 'bundles'

    if not bundles_path.is_dir():
        return {'error': f'Bundles directory not found: {bundles_path}'}

    extensions: list[dict[str, Any]] = []
    summary: dict[str, int] = {'total_bundles': 0, 'with_extension': 0, 'valid': 0, 'invalid': 0, 'issues': 0}
    results: dict[str, Any] = {'extensions': extensions, 'summary': summary}

    for bundle_dir in sorted(bundles_path.iterdir()):
        if not bundle_dir.is_dir():
            continue
        if bundle_dir.name.startswith('.'):
            continue

        summary['total_bundles'] += 1

        extension_path = bundle_dir / 'skills' / 'plan-marshall-plugin' / 'extension.py'

        if extension_path.exists():
            summary['with_extension'] += 1
            ext_result = validate_extension(extension_path)
            ext_result['bundle'] = bundle_dir.name

            # Also check bundle consistency
            consistency = validate_bundle_consistency(bundle_dir)
            ext_result['consistency'] = consistency

            if ext_result['valid'] and consistency['valid']:
                summary['valid'] += 1
            else:
                summary['invalid'] += 1

            summary['issues'] += len(ext_result['issues'])
            summary['issues'] += len(consistency.get('issues', []))

            extensions.append(ext_result)

    return results


# =============================================================================
# Extension Point Contract Validation (EC-* rules)
# =============================================================================


def _parse_frontmatter(skill_path: Path) -> dict[str, str]:
    """Parse YAML frontmatter from a SKILL.md file."""
    try:
        content = skill_path.read_text(encoding='utf-8')
    except OSError:
        return {}

    if not content.startswith('---'):
        return {}

    end = content.find('---', 3)
    if end == -1:
        return {}

    frontmatter: dict[str, str] = {}
    for line in content[3:end].strip().split('\n'):
        if ':' in line:
            key, _, value = line.partition(':')
            frontmatter[key.strip()] = value.strip()
    return frontmatter


def _has_section(file_path: Path, section_heading: str) -> bool:
    """Check if a markdown file contains a specific heading."""
    try:
        content = file_path.read_text(encoding='utf-8')
    except OSError:
        return False
    return f'## {section_heading}' in content


def validate_extension_contracts(marketplace_root: Path, extension_type: str | None = None,
                                  skill_filter: str | None = None) -> dict[str, Any]:
    """Validate extension point contract compliance across all implementors.

    Rules:
        EC-01: implements field present for ext-*/recipe-* skills (Warning)
        EC-02: implements target file exists (Error)
        EC-03: implements value uses correct format: bundle:skill/path (Error)
        EC-04: Contract document has required sections (Error)
        EC-10: Triage skills: contains ## Suppression Syntax (Error)
        EC-11: Triage skills: contains ## Severity Guidelines (Error)
        EC-12: Triage skills: contains ## Acceptable to Accept (Error)
        EC-20: Outline skills: standards/change-types.md exists (Error)
        EC-40: Build skills: implements ExecuteConfig (Warning)
        EC-50: Provider scripts: get_provider_declarations() exists (Error)
    """
    bundles_path = marketplace_root / 'bundles'
    errors: list[dict[str, str]] = []
    total_checked = 0
    passed = 0
    failed = 0

    # Collect all implementor SKILL.md files
    implementors: list[tuple[Path, str]] = []  # (skill_path, detected_type)

    for bundle_dir in sorted(bundles_path.iterdir()):
        if not bundle_dir.is_dir() or bundle_dir.name.startswith('.'):
            continue

        skills_dir = bundle_dir / 'skills'
        if not skills_dir.is_dir():
            continue

        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue

            skill_md = skill_dir / 'SKILL.md'
            skill_name = skill_dir.name

            # Detect extension type from naming convention
            ext_type = None
            if skill_name.startswith('ext-triage-'):
                ext_type = 'triage'
            elif skill_name.startswith('ext-outline-'):
                ext_type = 'outline'
            elif skill_name.startswith('recipe-'):
                ext_type = 'recipe'
            elif skill_name.startswith('build-'):
                ext_type = 'build'

            if ext_type is None:
                continue

            # Apply filters
            if extension_type and ext_type != extension_type:
                continue
            if skill_filter:
                full_name = f'{bundle_dir.name}:{skill_name}'
                if skill_filter != full_name and skill_filter != skill_name:
                    continue

            if skill_md.exists():
                implementors.append((skill_md, ext_type))

    # Also check provider extensions
    if not extension_type or extension_type == 'provider':
        for bundle_dir in sorted(bundles_path.iterdir()):
            if not bundle_dir.is_dir() or bundle_dir.name.startswith('.'):
                continue
            for prov_path in bundle_dir.glob('skills/*/scripts/*_provider.py'):
                if skill_filter:
                    skill_name = prov_path.parent.parent.name
                    full_name = f'{bundle_dir.name}:{skill_name}'
                    if skill_filter != full_name and skill_filter != skill_name:
                        continue
                implementors.append((prov_path, 'provider'))

    # Validate each implementor
    for impl_path, ext_type in implementors:
        total_checked += 1
        impl_errors: list[dict[str, str]] = []

        if ext_type == 'provider':
            # EC-50: provider scripts must have get_provider_declarations()
            try:
                content = impl_path.read_text(encoding='utf-8')
                if 'def get_provider_declarations' not in content:
                    impl_errors.append({
                        'skill': str(impl_path.relative_to(bundles_path)),
                        'rule': 'EC-50',
                        'message': "Missing 'get_provider_declarations()' function",
                    })
            except OSError:
                impl_errors.append({
                    'skill': str(impl_path),
                    'rule': 'EC-50',
                    'message': 'Cannot read provider extension file',
                })
        else:
            # Parse frontmatter
            fm = _parse_frontmatter(impl_path)
            skill_name = impl_path.parent.name
            bundle_name = impl_path.parent.parent.parent.name
            skill_ref = f'{bundle_name}:{skill_name}'

            # EC-01: implements field present
            if 'implements' not in fm:
                impl_errors.append({
                    'skill': skill_ref,
                    'rule': 'EC-01',
                    'message': "Missing 'implements' field in frontmatter",
                })
            else:
                impl_value = fm['implements']

                # EC-03: format check
                if ':' not in impl_value or '/' not in impl_value:
                    impl_errors.append({
                        'skill': skill_ref,
                        'rule': 'EC-03',
                        'message': f"Invalid implements format: '{impl_value}' (expected bundle:skill/path)",
                    })
                else:
                    # EC-02: target file exists
                    ref_bundle, ref_path = impl_value.split(':', 1)
                    target_path = bundles_path / ref_bundle / 'skills' / (ref_path + '.md')
                    if not target_path.exists():
                        impl_errors.append({
                            'skill': skill_ref,
                            'rule': 'EC-02',
                            'message': f"Implements target not found: {impl_value}",
                        })
                    else:
                        # EC-04: contract doc has required sections
                        for section in ['Parameters', 'Pre-Conditions', 'Post-Conditions']:
                            if not _has_section(target_path, section):
                                impl_errors.append({
                                    'skill': skill_ref,
                                    'rule': 'EC-04',
                                    'message': f"Contract doc missing '## {section}' section",
                                })

            # Type-specific checks
            if ext_type == 'triage':
                # EC-10, EC-11, EC-12: check for required content in SKILL.md or standards/ files
                skill_dir = impl_path.parent
                for rule_id, patterns in [
                    ('EC-10', ['Suppression Syntax', 'Suppression Methods', 'suppression']),
                    ('EC-11', ['Severity Guidelines', 'Severity', 'severity']),
                    ('EC-12', ['Acceptable to Accept']),
                ]:
                    found = False
                    # Check SKILL.md for section headings (any heading level)
                    try:
                        content = impl_path.read_text(encoding='utf-8')
                        for pattern in patterns:
                            if f'# {pattern}' in content or f'## {pattern}' in content or f'### {pattern}' in content:
                                found = True
                                break
                    except OSError:
                        pass
                    # Check standards/ directory for matching files
                    if not found:
                        standards_dir = skill_dir / 'standards'
                        if standards_dir.is_dir():
                            for std_file in standards_dir.glob('*.md'):
                                for pattern in patterns:
                                    if pattern.lower() in std_file.name.lower():
                                        found = True
                                        break
                                    try:
                                        std_content = std_file.read_text(encoding='utf-8')
                                        if f'# {pattern}' in std_content or f'## {pattern}' in std_content:
                                            found = True
                                            break
                                    except OSError:
                                        pass
                                if found:
                                    break
                    if not found:
                        impl_errors.append({
                            'skill': skill_ref,
                            'rule': rule_id,
                            'message': f"Missing suppression/severity/accept content (checked '{patterns[0]}')",
                        })

            elif ext_type == 'outline':
                # EC-20: standards/change-types.md exists
                change_types_path = impl_path.parent / 'standards' / 'change-types.md'
                if not change_types_path.exists():
                    impl_errors.append({
                        'skill': skill_ref,
                        'rule': 'EC-20',
                        'message': "Missing 'standards/change-types.md' file",
                    })

            elif ext_type == 'build':
                # EC-40: check for ExecuteConfig reference
                # Look in scripts directory for ExecuteConfig usage
                scripts_dir = impl_path.parent / 'scripts'
                has_execute_config = False
                if scripts_dir.is_dir():
                    for py_file in scripts_dir.glob('*.py'):
                        try:
                            content = py_file.read_text(encoding='utf-8')
                            if 'ExecuteConfig' in content:
                                has_execute_config = True
                                break
                        except OSError:
                            pass
                if not has_execute_config:
                    impl_errors.append({
                        'skill': skill_ref,
                        'rule': 'EC-40',
                        'message': "No ExecuteConfig usage found in scripts",
                    })

        if impl_errors:
            failed += 1
            errors.extend(impl_errors)
        else:
            passed += 1

    return {
        'status': 'success' if failed == 0 else 'error',
        'total_checked': total_checked,
        'passed': passed,
        'failed': failed,
        'errors': errors,
    }


def cmd_extension(args) -> dict:
    """Validate extension.py files."""
    if args.extension_path:
        # Single extension validation
        extension_path = Path(args.extension_path)
        result = validate_extension(extension_path)
        result['status'] = 'success' if result['valid'] else 'error'
        return result

    elif args.bundle_path:
        # Bundle consistency check
        bundle_path = Path(args.bundle_path)
        consistency = validate_bundle_consistency(bundle_path)

        if consistency.get('has_extension'):
            extension_path = bundle_path / 'skills' / 'plan-marshall-plugin' / 'extension.py'
            ext_result = validate_extension(extension_path)
            result = {'extension': ext_result, 'consistency': consistency}
        else:
            result = consistency

        result['status'] = 'success' if consistency['valid'] else 'error'
        return result

    elif args.marketplace_path:
        # Scan all extensions
        marketplace_path = Path(args.marketplace_path)
        result = scan_extensions(marketplace_path)

        if 'error' in result:
            result['status'] = 'error'
        else:
            result['status'] = 'success' if result['summary']['invalid'] == 0 else 'error'
        return result

    else:
        # Default: scan from cwd first (supports test fixtures), then script-relative
        marketplace_path = Path.cwd() / 'marketplace'
        if marketplace_path.is_dir():
            pass  # use marketplace_path
        elif Path.cwd().is_dir() and (Path.cwd() / 'bundles').is_dir():
            marketplace_path = Path.cwd()
        elif _MARKETPLACE_FROM_SCRIPT.is_dir():
            marketplace_path = _MARKETPLACE_FROM_SCRIPT
        else:
            marketplace_path = Path.cwd()

        result = scan_extensions(marketplace_path)

        if 'error' in result:
            result['status'] = 'error'
        else:
            result['status'] = 'success' if result['summary']['invalid'] == 0 else 'error'
        return result

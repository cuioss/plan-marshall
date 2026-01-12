#!/usr/bin/env python3
"""Shared test helpers for plan-marshall-config tests.

Provides common fixtures and utilities used across all test modules.
"""

import json
import sys
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import run_script, TestRunner, get_script_path, PlanTestContext

# Script under test
SCRIPT_PATH = get_script_path('plan-marshall', 'plan-marshall-config', 'plan-marshall-config.py')


def create_run_config(fixture_dir: Path, config: dict = None) -> Path:
    """Create run-configuration.json in fixture directory.

    Args:
        fixture_dir: Directory to create file in
        config: Optional config dict (uses default if not provided)

    Returns:
        Path to created file
    """
    if config is None:
        config = {
            "version": 1,
            "commands": {},
            "ci": {
                "git_present": True,
                "authenticated_tools": ["git", "gh"],
                "verified_at": "2025-01-15T10:30:00Z"
            }
        }
    run_config_path = fixture_dir / 'run-configuration.json'
    run_config_path.write_text(json.dumps(config, indent=2))
    return run_config_path


def create_marshal_json(fixture_dir: Path, config: dict = None) -> Path:
    """Create marshal.json in fixture directory with module_config structure.

    Also creates raw-project-data.json with module facts (source of truth for modules).
    """
    if config is None:
        config = {
            "skill_domains": {
                "java": {
                    "defaults": ["pm-dev-java:java-core"],
                    "optionals": ["pm-dev-java:java-cdi"]
                },
                "java-testing": {
                    "defaults": ["pm-dev-java:junit-core"],
                    "optionals": []
                }
            },
            "module_config": {
                "default": {
                    "commands": {
                        "test": "python3 .plan/execute-script.py plan-marshall:build-operations:maven run --targets \"clean test\"",
                        "verify": "python3 .plan/execute-script.py plan-marshall:build-operations:maven run --targets \"clean verify\""
                    }
                },
                "my-ui": {
                    "commands": {
                        "test": "python3 .plan/execute-script.py plan-marshall:build-operations:npm execute --command \"run test\"",
                        "build": "python3 .plan/execute-script.py plan-marshall:build-operations:npm execute --command \"run build\""
                    }
                }
            },
            "system": {
                "retention": {
                    "logs_days": 1,
                    "archived_plans_days": 5,
                    "memory_days": 5,
                    "temp_on_maintenance": True
                }
            },
            "plan": {
                "defaults": {
                    "compatibility": "deprecations",
                    "commit_strategy": "phase-specific",
                    "create_pr": False,
                    "verification_required": True,
                    "branch_strategy": "direct"
                }
            },
            "ci": {
                "repo_url": "https://github.com/test/repo",
                "provider": "github",
                "detected_at": "2025-01-15T10:30:00Z"
            }
        }
    marshal_path = fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))

    # Also create raw-project-data.json with module facts (source of truth)
    raw_data = {
        "project": {"name": "test-project"},
        "modules": [
            {"name": "my-core", "path": "my-core", "parent": None, "build_systems": ["maven"], "packaging": "jar"},
            {"name": "my-ui", "path": "my-ui", "parent": None, "build_systems": ["maven", "npm"], "packaging": "war"}
        ]
    }
    raw_data_path = fixture_dir / 'raw-project-data.json'
    raw_data_path.write_text(json.dumps(raw_data, indent=2))

    return marshal_path


def create_nested_marshal_json(fixture_dir: Path) -> Path:
    """Create marshal.json with nested skill_domains structure.

    Uses 5-phase model: init, outline, plan, execute, finalize.
    System domain contains workflow_skills.
    Domain-specific domains contain workflow_skill_extensions and profiles.
    """
    config = {
        "skill_domains": {
            "system": {
                "defaults": ["plan-marshall:general-development-rules"],
                "optionals": ["plan-marshall:diagnostic-patterns"],
                "workflow_skills": {
                    "init": "pm-workflow:phase-init",
                    "outline": "pm-workflow:phase-refine-outline",
                    "plan": "pm-workflow:phase-refine-plan",
                    "execute": "pm-workflow:phase-execute",
                    "finalize": "pm-workflow:phase-finalize"
                }
            },
            "java": {
                "workflow_skill_extensions": {
                    "outline": "pm-dev-java:java-outline-ext",
                    "triage": "pm-dev-java:java-triage"
                },
                "core": {
                    "defaults": ["pm-dev-java:java-core"],
                    "optionals": ["pm-dev-java:java-null-safety", "pm-dev-java:java-lombok"]
                },
                "implementation": {
                    "defaults": [],
                    "optionals": ["pm-dev-java:java-cdi", "pm-dev-java:java-maintenance"]
                },
                "testing": {
                    "defaults": ["pm-dev-java:junit-core"],
                    "optionals": ["pm-dev-java:junit-integration"]
                },
                "quality": {
                    "defaults": ["pm-dev-java:javadoc"],
                    "optionals": []
                }
            },
            "javascript": {
                "workflow_skill_extensions": {
                    "outline": "pm-dev-frontend:js-outline-ext"
                },
                "core": {
                    "defaults": ["pm-dev-frontend:cui-javascript"],
                    "optionals": ["pm-dev-frontend:cui-jsdoc"]
                },
                "implementation": {
                    "defaults": [],
                    "optionals": ["pm-dev-frontend:cui-javascript-linting"]
                },
                "testing": {
                    "defaults": ["pm-dev-frontend:cui-javascript-unit-testing"],
                    "optionals": ["pm-dev-frontend:cui-cypress"]
                },
                "quality": {
                    "defaults": [],
                    "optionals": []
                }
            },
            "plan-marshall-plugin-dev": {
                "workflow_skill_extensions": {
                    "outline": "pm-plugin-development:plugin-outline-ext",
                    "triage": "pm-plugin-development:plugin-triage"
                },
                "core": {
                    "defaults": ["pm-plugin-development:plugin-architecture"],
                    "optionals": []
                },
                "implementation": {
                    "defaults": [],
                    "optionals": []
                },
                "testing": {
                    "defaults": [],
                    "optionals": []
                },
                "quality": {
                    "defaults": [],
                    "optionals": []
                }
            }
        },
        "modules": {},
        "system": {
            "retention": {
                "logs_days": 1,
                "archived_plans_days": 5,
                "memory_days": 5,
                "temp_on_maintenance": True
            }
        },
        "plan": {
            "defaults": {
                "compatibility": "breaking",
                "commit_strategy": "phase-specific",
                "create_pr": False,
                "verification_required": True,
                "branch_strategy": "direct"
            }
        },
        "ci": {
            "repo_url": None,
            "provider": "unknown",
            "detected_at": None
        }
    }
    marshal_path = fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))
    return marshal_path


def parse_toon_output(output: str) -> dict:
    """Parse TOON output to dict (simplified parser for tests)."""
    result = {}
    lines = output.strip().split('\n')
    for line in lines:
        if ':' in line and not line.endswith(':'):
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            # Try to parse as JSON for lists/bools/numbers
            try:
                result[key] = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                result[key] = value
        elif line.startswith('- '):
            # Array item
            if 'items' not in result:
                result['items'] = []
            result['items'].append(line[2:].strip())
    return result

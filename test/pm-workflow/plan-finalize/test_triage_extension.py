#!/usr/bin/env python3
"""Tests for triage extension loading via plan-marshall-config API.

Tests the resolve-workflow-skill-extension command for triage extensions.
"""

import json
import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import run_script, get_script_path, PlanTestContext

# Get script path for plan-marshall-config
SCRIPT_PATH = get_script_path('plan-marshall', 'plan-marshall-config', 'plan-marshall-config.py')

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]


def create_marshal_json(fixture_dir: Path, config: dict):
    """Create marshal.json in the fixture directory."""
    marshal_path = fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))


# =============================================================================
# Test: Triage Extension Resolution
# =============================================================================

def test_resolve_triage_extension_java():
    """Test resolving triage extension for Java domain."""
    with PlanTestContext(plan_id='triage-java') as ctx:
        # Initialize with Java domain
        create_marshal_json(ctx.fixture_dir, {
            "skill_domains": {
                "system": {
                    "defaults": ["plan-marshall:general-development-rules"],
                    "workflow_skills": {
                        "init": "pm-workflow:plan-init",
                        "outline": "pm-workflow:phase-refine-outline",
                        "plan": "pm-workflow:task-plan",
                        "execute": "pm-workflow:task-execute",
                        "finalize": "pm-workflow:plan-finalize"
                    }
                },
                "java": {
                    "workflow_skill_extensions": {
                        "outline": "pm-dev-java:java-outline-ext",
                        "triage": "pm-dev-java:java-triage"
                    },
                    "core": {
                        "defaults": ["pm-dev-java:java-core"],
                        "optionals": []
                    }
                }
            }
        })

        result = run_script(SCRIPT_PATH,
            'resolve-workflow-skill-extension',
            '--domain', 'java',
            '--type', 'triage'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['domain'] == 'java'
        assert data['type'] == 'triage'
        assert data['extension'] == 'pm-dev-java:java-triage'


def test_resolve_triage_extension_javascript():
    """Test resolving triage extension for JavaScript domain."""
    with PlanTestContext(plan_id='triage-js') as ctx:
        create_marshal_json(ctx.fixture_dir, {
            "skill_domains": {
                "system": {
                    "defaults": ["plan-marshall:general-development-rules"],
                    "workflow_skills": {
                        "init": "pm-workflow:plan-init",
                        "outline": "pm-workflow:phase-refine-outline",
                        "plan": "pm-workflow:task-plan",
                        "execute": "pm-workflow:task-execute",
                        "finalize": "pm-workflow:plan-finalize"
                    }
                },
                "javascript": {
                    "workflow_skill_extensions": {
                        "outline": "pm-dev-frontend:js-outline-ext",
                        "triage": "pm-dev-frontend:javascript-triage"
                    },
                    "core": {
                        "defaults": ["pm-dev-frontend:cui-javascript"],
                        "optionals": []
                    }
                }
            }
        })

        result = run_script(SCRIPT_PATH,
            'resolve-workflow-skill-extension',
            '--domain', 'javascript',
            '--type', 'triage'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['extension'] == 'pm-dev-frontend:javascript-triage'


def test_resolve_triage_extension_plugin_dev():
    """Test resolving triage extension for plugin development domain."""
    with PlanTestContext(plan_id='triage-plugin') as ctx:
        create_marshal_json(ctx.fixture_dir, {
            "skill_domains": {
                "system": {
                    "defaults": ["plan-marshall:general-development-rules"],
                    "workflow_skills": {
                        "init": "pm-workflow:plan-init",
                        "outline": "pm-workflow:phase-refine-outline",
                        "plan": "pm-workflow:task-plan",
                        "execute": "pm-workflow:task-execute",
                        "finalize": "pm-workflow:plan-finalize"
                    }
                },
                "plan-marshall-plugin-dev": {
                    "workflow_skill_extensions": {
                        "triage": "pm-plugin-development:plugin-triage"
                    },
                    "core": {
                        "defaults": ["pm-plugin-development:plugin-architecture"],
                        "optionals": []
                    }
                }
            }
        })

        result = run_script(SCRIPT_PATH,
            'resolve-workflow-skill-extension',
            '--domain', 'plan-marshall-plugin-dev',
            '--type', 'triage'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['extension'] == 'pm-plugin-development:plugin-triage'


def test_resolve_triage_extension_null_for_missing():
    """Test that missing triage extension returns null (not error)."""
    with PlanTestContext(plan_id='triage-missing') as ctx:
        # Create domain without triage extension
        create_marshal_json(ctx.fixture_dir, {
            "skill_domains": {
                "system": {
                    "defaults": ["plan-marshall:general-development-rules"],
                    "workflow_skills": {
                        "init": "pm-workflow:plan-init",
                        "outline": "pm-workflow:phase-refine-outline",
                        "plan": "pm-workflow:task-plan",
                        "execute": "pm-workflow:task-execute",
                        "finalize": "pm-workflow:plan-finalize"
                    }
                },
                "documentation": {
                    "workflow_skill_extensions": {
                        "outline": "pm-documents:doc-outline-ext"
                        # No triage extension
                    },
                    "core": {
                        "defaults": ["pm-documents:cui-documentation"],
                        "optionals": []
                    }
                }
            }
        })

        result = run_script(SCRIPT_PATH,
            'resolve-workflow-skill-extension',
            '--domain', 'documentation',
            '--type', 'triage'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['domain'] == 'documentation'
        assert data['type'] == 'triage'
        assert data['extension'] is None  # Null, not error


def test_resolve_triage_extension_null_for_unknown_domain():
    """Test that unknown domain returns null extension (not error)."""
    with PlanTestContext(plan_id='triage-unknown') as ctx:
        create_marshal_json(ctx.fixture_dir, {
            "skill_domains": {
                "system": {
                    "defaults": ["plan-marshall:general-development-rules"],
                    "workflow_skills": {
                        "init": "pm-workflow:plan-init",
                        "outline": "pm-workflow:phase-refine-outline",
                        "plan": "pm-workflow:task-plan",
                        "execute": "pm-workflow:task-execute",
                        "finalize": "pm-workflow:plan-finalize"
                    }
                }
            }
        })

        result = run_script(SCRIPT_PATH,
            'resolve-workflow-skill-extension',
            '--domain', 'unknown-domain',
            '--type', 'triage'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['domain'] == 'unknown-domain'
        assert data['extension'] is None  # Null for unknown domain

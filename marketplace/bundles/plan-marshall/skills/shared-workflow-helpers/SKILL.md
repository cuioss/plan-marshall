---
name: shared-workflow-helpers
description: Shared Python infrastructure for workflow scripts — CLI construction, error codes, triage handlers, priority calculation, test file detection
user-invocable: false
---

# Shared Workflow Helpers

Script-only skill hosting shared Python modules used across all workflow scripts in the plan-marshall bundle.

| Module | Purpose |
|--------|---------|
| `scripts/triage_helpers.py` | CLI boilerplate, error taxonomy, TOON output helpers, priority calculation, test file detection, triage command handlers |

## Key Exports

| Export | Purpose | Primary Consumers |
|--------|---------|-------------------|
| `print_toon`, `print_error` | TOON output helpers | All workflow scripts |
| `safe_main` | Unhandled exception wrapper | All workflow scripts |
| `ErrorCode`, `make_error` | Error code taxonomy | All workflow scripts |
| `create_workflow_cli` | argparse boilerplate reduction | sonar.py, pr.py, permission_web.py, git_workflow.py |
| `calculate_priority`, `PRIORITY_LEVELS` | Priority arithmetic | sonar.py |
| `is_test_file` | Test file detection across languages | sonar.py, git_workflow.py |
| `cmd_triage_single`, `cmd_triage_batch_handler` | Triage command handlers | pr.py, sonar.py |
| `load_skill_config` | JSON config loading from standards/ | All script-bearing workflow skills |
| `compile_patterns_from_config` | Regex compilation from config | pr.py, permission_web.py |

## Import Pattern

```python
from triage_helpers import print_toon, print_error, safe_main, create_workflow_cli
from triage_helpers import ErrorCode, make_error, load_skill_config
```

The executor adds this skill's `scripts/` directory to `PYTHONPATH` at runtime.

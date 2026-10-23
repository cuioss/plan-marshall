envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:16:38Z

# Candidate lesson: manage-config domain-narrow crashed on import from the OpenCode skill tree

Source: script-failure cluster plan-marshall:manage-config:manage-config (1 occurrence, 2026-10-17T19:56:53Z, phase 3-outline)
Component (suggested): plan-marshall:manage-config / executor script resolution (foreign bundle - route to plan-marshall lessons inbox)

## What happened

`domain-narrow --plan-id plan-69-unit-frontmatter-and-types` -> exit 1 with a
Python traceback during module import:

```
File "/home/oliver/.config/opencode/skills/plan-marshall-manage-config/scripts/manage-config.py", line 21
  from _cmd_build_map import cmd_build_decision, cmd_build_map
File ".../_cmd_build_map.py", line 37
  from _config_core import ( ... )
File ".../_config_core.py", l...
```

(The log truncates the final frame.) The script was resolved from the OpenCode
skill tree (`~/.config/opencode/skills/...`) in a Claude session, and an import
from `_config_core` failed - consistent with that tree being out of step with
the current plugin version (stale sibling module). The same call succeeded at
20:20:26Z, presumably after a resync.

## Candidate rule

Executor resolution should not pick a stale OpenCode-target copy of a script in
a Claude session (or both targets must be refreshed together on upgrade). An
ImportError in a manage-* script is a provisioning fault, not an invocation
fault; it should surface as such rather than as a generic exit 1.

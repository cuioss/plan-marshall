#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Single source of the user-facing command forms emitted as instructions.

The slash-command forms are target-shaped facts: ``/marshall-steward`` is the
Claude Code slash command for the steward skill, ``/sync-plugin-cache`` the
meta-project plugin-cache sync command. Emission sites interpolate these
constants so a target-specific rename has exactly one home — a remediation
string is never spelled out at the call site.
"""

# The steward's user-facing slash command (Claude Code command palette).
STEWARD_COMMAND = '/marshall-steward'

# The meta-project plugin-cache sync slash command (a project-local skill under
# .claude/skills/, not bundle content).
SYNC_PLUGIN_CACHE_COMMAND = '/sync-plugin-cache'
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Single source of the user-facing command forms emitted as instructions.

The slash-command forms are target-shaped facts: ``/plan-marshall`` is the
Claude Code slash command for the plan lifecycle, ``/marshall-steward`` the
slash command for the steward skill, ``/sync-harnesses`` the meta-project sync
command for all harnesses. Emission sites interpolate these constants so a
target-specific rename has exactly one home — a remediation string is never
spelled out at the call site.
"""

# The plan lifecycle's user-facing slash command (Claude Code command palette).
PLAN_MARSHALL_COMMAND = '/plan-marshall'

# The steward's user-facing slash command (Claude Code command palette).
STEWARD_COMMAND = '/marshall-steward'

# The meta-project sync slash command for all harnesses (a project-local,
# meta-repo-only command file in each harness's own location, not bundle
# content).
SYNC_HARNESSES_COMMAND = '/sync-harnesses'

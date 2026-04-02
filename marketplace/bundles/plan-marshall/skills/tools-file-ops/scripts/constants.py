"""Shared constants for plan-marshall scripts.

Centralizes string literals used across multiple skills to prevent typos
and enable IDE completion. Import via: ``from constants import *`` or
``from constants import STATUS_SUCCESS, PHASES``.
"""

# ---------------------------------------------------------------------------
# Status values (TOON output)
# ---------------------------------------------------------------------------
STATUS_SUCCESS = 'success'
STATUS_ERROR = 'error'

# ---------------------------------------------------------------------------
# Phase names (ordered)
# ---------------------------------------------------------------------------
PHASES = (
    '1-init',
    '2-refine',
    '3-outline',
    '4-plan',
    '5-execute',
    '6-finalize',
)

# ---------------------------------------------------------------------------
# Phase statuses
# ---------------------------------------------------------------------------
PHASE_STATUS_PENDING = 'pending'
PHASE_STATUS_IN_PROGRESS = 'in_progress'
PHASE_STATUS_DONE = 'done'

# ---------------------------------------------------------------------------
# Storage filenames
# ---------------------------------------------------------------------------
FILE_STATUS = 'status.json'
FILE_REFERENCES = 'references.json'
FILE_ASSESSMENTS = 'assessments.jsonl'
FILE_FINDINGS = 'findings.jsonl'
FILE_METRICS = 'metrics.toon'
FILE_MARSHAL = 'marshal.json'
FILE_RUN_CONFIG = 'run-config.json'

# ---------------------------------------------------------------------------
# Assessment certainty values
# ---------------------------------------------------------------------------
CERTAINTY_INCLUDE = 'CERTAIN_INCLUDE'
CERTAINTY_EXCLUDE = 'CERTAIN_EXCLUDE'
CERTAINTY_UNCERTAIN = 'UNCERTAIN'
VALID_CERTAINTIES = (CERTAINTY_INCLUDE, CERTAINTY_EXCLUDE, CERTAINTY_UNCERTAIN)

# ---------------------------------------------------------------------------
# Finding types
# ---------------------------------------------------------------------------
FINDING_TYPES = ('quality', 'compliance', 'security', 'performance', 'maintainability')

# ---------------------------------------------------------------------------
# Finding severities
# ---------------------------------------------------------------------------
FINDING_SEVERITIES = ('critical', 'major', 'minor', 'info')

# ---------------------------------------------------------------------------
# Plan directory structure
# ---------------------------------------------------------------------------
DIR_PLANS = 'plans'
DIR_ARTIFACTS = 'artifacts'
DIR_ARCHIVED = 'archived-plans'
DIR_WORK = 'work'
DIR_LESSONS = 'lessons-learned'

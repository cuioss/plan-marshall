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

PHASE_COUNT = len(PHASES)

# Q-Gate phases (all phases except 1-init, which has no verification step)
QGATE_PHASES = PHASES[1:]  # ('2-refine', '3-outline', '4-plan', '5-execute', '6-finalize')

# ---------------------------------------------------------------------------
# Phase statuses
# ---------------------------------------------------------------------------
PHASE_STATUS_PENDING = 'pending'
PHASE_STATUS_IN_PROGRESS = 'in_progress'
PHASE_STATUS_DONE = 'done'

VALID_PHASE_STATUSES = (PHASE_STATUS_PENDING, PHASE_STATUS_IN_PROGRESS, PHASE_STATUS_DONE)

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
# Hash ID pattern (shared by findings, assessments, logging)
# All use 6-character hex hashes from hashlib.sha256().hexdigest()[:6]
# Input varies by domain: findings use (title+type), assessments use
# (file_path+certainty+confidence), logging uses (message content).
# ---------------------------------------------------------------------------
HASH_ID_LENGTH = 6

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
# Finding / Q-Gate resolution values
# ---------------------------------------------------------------------------
RESOLUTION_PENDING = 'pending'
RESOLUTION_FIXED = 'fixed'
RESOLUTION_SUPPRESSED = 'suppressed'
RESOLUTION_ACCEPTED = 'accepted'
RESOLUTION_TAKEN_INTO_ACCOUNT = 'taken_into_account'

VALID_RESOLUTIONS = (
    RESOLUTION_PENDING,
    RESOLUTION_FIXED,
    RESOLUTION_SUPPRESSED,
    RESOLUTION_ACCEPTED,
    RESOLUTION_TAKEN_INTO_ACCOUNT,
)

# ---------------------------------------------------------------------------
# Lesson categories
# ---------------------------------------------------------------------------
LESSON_CATEGORIES = ('bug', 'improvement', 'anti-pattern')

# ---------------------------------------------------------------------------
# Log levels
# ---------------------------------------------------------------------------
LOG_LEVEL_INFO = 'INFO'
LOG_LEVEL_WARN = 'WARN'
LOG_LEVEL_ERROR = 'ERROR'
VALID_LOG_LEVELS = (LOG_LEVEL_INFO, LOG_LEVEL_WARN, LOG_LEVEL_ERROR)

# ---------------------------------------------------------------------------
# Log types
# ---------------------------------------------------------------------------
LOG_TYPE_SCRIPT = 'script'
LOG_TYPE_WORK = 'work'
LOG_TYPE_DECISION = 'decision'
VALID_LOG_TYPES = (LOG_TYPE_SCRIPT, LOG_TYPE_WORK, LOG_TYPE_DECISION)

# ---------------------------------------------------------------------------
# Workflow profiles (used in deliverables, tasks, skill-domains)
# Source of truth for profile names referenced across manage-* skills.
# ---------------------------------------------------------------------------
PROFILE_IMPLEMENTATION = 'implementation'
PROFILE_MODULE_TESTING = 'module_testing'
PROFILE_INTEGRATION_TESTING = 'integration_testing'
PROFILE_VERIFICATION = 'verification'

VALID_PROFILES = (
    PROFILE_IMPLEMENTATION,
    PROFILE_MODULE_TESTING,
    PROFILE_INTEGRATION_TESTING,
    PROFILE_VERIFICATION,
)

# ---------------------------------------------------------------------------
# Plan directory structure
# ---------------------------------------------------------------------------
DIR_PLANS = 'plans'
DIR_ARTIFACTS = 'artifacts'
DIR_ARCHIVED = 'archived-plans'
DIR_WORK = 'work'
DIR_LESSONS = 'lessons-learned'
DIR_LOGS = 'logs'
DIR_TASKS = 'tasks'
DIR_MEMORIES = 'memories'

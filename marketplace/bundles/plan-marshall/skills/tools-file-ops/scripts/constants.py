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
# Branch-prefix sets (FAIL-CLOSED FALLBACK DEFAULTS ONLY)
# ---------------------------------------------------------------------------
# The authoritative source for the branch-prefix sets is `.plan/marshal.json`
# under `project.branch_naming` (read AND written through `manage-config`). The
# two tuples below are consulted SOLELY when that config key is absent or
# unreadable (e.g. a fresh checkout before `/marshall-steward` has run) — they
# are the fail-closed fallback, never the live source of truth.
#
# `_config_defaults.py` imports these names to build
# `DEFAULT_PROJECT['branch_naming']`; the literals therefore live here exactly
# once and are not duplicated elsewhere.
#
# `DEFAULT_BRANCH_PREFIX_WORKING` is the closed set of allowed working-branch
# prefixes. A plan feature branch is always a working branch (never `main` or
# `dependabot/**`); the branch-prefix validation in `marshall-steward`
# enforces this set.
#
# `DEFAULT_CI_BRANCH_ALLOWLIST` is the full CI push-trigger allowlist in glob
# form, matching `.github/workflows/python-verify.yml`'s `on.push.branches`
# list verbatim. A PR whose branch prefix falls outside this list silently
# receives no `verify / verify` check and is structurally unmergeable.
#
# `docs/` is EXPLICITLY RETIRED from both sets and must NOT be re-admitted —
# it was never CI-triggered. Use `chore/` for documentation-only changes.
DEFAULT_BRANCH_PREFIX_WORKING = ('feature/', 'fix/', 'chore/')
DEFAULT_CI_BRANCH_ALLOWLIST = ('main', 'feature/*', 'fix/*', 'chore/*', 'dependabot/**')

# `DEFAULT_SANCTIONED_CONFTEST` is the closed set of `conftest.py` paths that are
# permitted in this project's test tree. Every OTHER `conftest.py` under a skill
# or script test directory (any path matching `test/**/`) is a defect: pytest
# auto-discovers `conftest.py` and evaluates it as a fixture-collection module
# for the whole bundle, so a stray sibling silently shadows the top-level
# `test/conftest.py` and disables shared fixtures. The sanctioned set is
# project data, NOT a hard-coded marketplace literal: it is materialised into
# `DEFAULT_PROJECT['sanctioned_conftest']` and operators override it via
# `manage-config project set --field sanctioned_conftest`. The generic rule
# ("do not name a new test helper conftest.py — use `_fixtures.py`") is
# project-invariant and stays in the shipped skill prose; only this concrete
# allow-list is config-driven. The literal lives here exactly once as the
# fail-closed fallback seed.
DEFAULT_SANCTIONED_CONFTEST = ('test/conftest.py', 'test/adapters/conftest.py')

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
FILE_METRICS = 'metrics.toon'
FILE_MARSHAL = 'marshal.json'
FILE_RUN_CONFIG = 'run-config.json'

# Findings live under artifacts/findings/{type}.jsonl (per-type splitting),
# alongside qgate-{phase}.jsonl and assessments.jsonl in the same directory.
FILE_FINDINGS_DIR = 'findings'

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
# Finding types (12-type taxonomy used by manage-findings)
# ---------------------------------------------------------------------------
FINDING_TYPES = (
    # Lesson-like (knowledge)
    'bug',
    'improvement',
    'anti-pattern',
    'triage',
    'tip',
    'insight',
    'best-practice',
    # Bug-like (issues)
    'build-error',
    'test-failure',
    'lint-issue',
    'sonar-issue',
    'pr-comment',
)

# ---------------------------------------------------------------------------
# Finding severities
# ---------------------------------------------------------------------------
FINDING_SEVERITIES = ('error', 'warning', 'info')

# ---------------------------------------------------------------------------
# Q-Gate finding sources
# ---------------------------------------------------------------------------
QGATE_SOURCES = ('qgate', 'user_review')

# ---------------------------------------------------------------------------
# Finding type subsets (used for promotion routing)
# ---------------------------------------------------------------------------
# Types that default to manage-lessons promotion
LESSON_TYPES = frozenset(('bug', 'improvement', 'anti-pattern', 'triage'))

# Types that default to architecture promotion
ARCHITECTURE_TYPES = frozenset(('tip', 'insight', 'best-practice'))

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
LOG_LEVEL_WARNING = 'WARNING'
LOG_LEVEL_ERROR = 'ERROR'
VALID_LOG_LEVELS = (LOG_LEVEL_INFO, LOG_LEVEL_WARNING, LOG_LEVEL_ERROR)

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
# Note: the worktree root is intentionally NOT a constant here. It is computed
# in file_ops.get_worktree_root() as `<plan-root>/.plan/local/worktrees`, where
# `<plan-root>` is resolved by the uniform cwd rule (ADR-002), rather than a
# hard-coded literal.
DIR_PLANS = 'plans'
DIR_ARTIFACTS = 'artifacts'
DIR_ARCHIVED = 'archived-plans'
DIR_WORK = 'work'
DIR_LESSONS = 'lessons-learned'
DIR_LOGS = 'logs'
DIR_TASKS = 'tasks'
DIR_ARCHIVED_LESSONS = 'archived-lessons'
DIR_ARCHITECTURE = 'project-architecture'
DIR_TEMP = 'temp'

# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------
EXIT_SUCCESS = 0

# ---------------------------------------------------------------------------
# Task statuses (extend phase statuses with 'blocked')
# ---------------------------------------------------------------------------
TASK_STATUS_BLOCKED = 'blocked'

VALID_TASK_STATUSES = (
    PHASE_STATUS_PENDING,
    PHASE_STATUS_IN_PROGRESS,
    PHASE_STATUS_DONE,
    TASK_STATUS_BLOCKED,
)

# ---------------------------------------------------------------------------
# Step statuses (extend phase statuses with 'skipped')
# ---------------------------------------------------------------------------
STEP_STATUS_SKIPPED = 'skipped'

VALID_STEP_STATUSES = (
    PHASE_STATUS_PENDING,
    PHASE_STATUS_IN_PROGRESS,
    PHASE_STATUS_DONE,
    STEP_STATUS_SKIPPED,
)

# ---------------------------------------------------------------------------
# Step intents (required per-step existence-expectation declaration)
# Drives the intent-aware files_exist Q-Gate check:
#   read          -> existence required pre-execution
#   write-new     -> existence forbidden pre-execution (finding fires if present)
#   write-replace -> no existence check
#   delete        -> existence required pre-execution (cannot remove an absent file)
# Single source of truth, imported by manage-tasks and manage-solution-outline.
# ---------------------------------------------------------------------------
STEP_INTENT_READ = 'read'
STEP_INTENT_WRITE_NEW = 'write-new'
STEP_INTENT_WRITE_REPLACE = 'write-replace'
STEP_INTENT_DELETE = 'delete'

VALID_STEP_INTENTS = (
    STEP_INTENT_READ,
    STEP_INTENT_WRITE_NEW,
    STEP_INTENT_WRITE_REPLACE,
    STEP_INTENT_DELETE,
)

# ---------------------------------------------------------------------------
# Task origins
# ---------------------------------------------------------------------------
VALID_TASK_ORIGINS = (
    'plan',
    'fix',
    'sonar',
    'pr',
    'lint',
    'security',
    'documentation',
    'holistic',
)

# ---------------------------------------------------------------------------
# Change types (used in deliverables and change-type detection)
# ---------------------------------------------------------------------------
VALID_CHANGE_TYPES = (
    'analysis',
    'feature',
    'enhancement',
    'bug_fix',
    'tech_debt',
    'verification',
)

# ---------------------------------------------------------------------------
# Execution modes (used in deliverables)
# ---------------------------------------------------------------------------
VALID_EXECUTION_MODES = ('automated', 'manual', 'mixed')

# ---------------------------------------------------------------------------
# Warning categories (used by run-config acceptable warnings)
# ---------------------------------------------------------------------------
VALID_WARNING_CATEGORIES = (
    'transitive_dependency',
    'plugin_compatibility',
    'platform_specific',
)

# ---------------------------------------------------------------------------
# Valid source file extensions (used for step path validation)
# ---------------------------------------------------------------------------
VALID_SOURCE_EXTENSIONS = (
    '.md',
    '.py',
    '.java',
    '.js',
    '.ts',
    '.tsx',
    '.jsx',
    '.json',
    '.yaml',
    '.yml',
    '.toml',
    '.cfg',
    '.ini',
    '.jsonl',
    '.xml',
    '.sh',
    '.bash',
    '.properties',
    '.adoc',
    '.toon',
    '.html',
    '.css',
)

# ---------------------------------------------------------------------------
# Work log categories
# ---------------------------------------------------------------------------
VALID_WORK_CATEGORIES = ('ARTIFACT', 'PROGRESS', 'ERROR', 'OUTCOME', 'FINDING')

# ---------------------------------------------------------------------------
# Storage filenames (additional)
# ---------------------------------------------------------------------------
FILE_SOLUTION_OUTLINE = 'solution_outline.md'
FILE_WORK_METRICS = 'work/metrics.toon'

# ---------------------------------------------------------------------------
# Project-architecture per-module storage
# ---------------------------------------------------------------------------
# Top-level project metadata file at the root of `.plan/project-architecture/`.
# Acts as the single source of truth for "which modules exist": its `modules`
# index is what clients iterate via `iter_modules`. Per-module directory
# presence on disk is NOT a substitute for the index — half-written
# directories must be ignored.
FILE_PROJECT_META = '_project.json'

# Per-module filenames, sitting under `.plan/project-architecture/{module}/`.
# `derived.json` holds the deterministic discovery output (paths, packages,
# dependencies). `enriched.json` holds the LLM-augmented fields
# (responsibility, purpose, key_packages, skills_by_profile, …).
DIR_PER_MODULE_DERIVED = 'derived.json'
DIR_PER_MODULE_ENRICHED = 'enriched.json'

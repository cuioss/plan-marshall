#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Thin scaffolding script for the plan-orchestrator skill.

Deliberately lean, per the orchestrator's lean posture: everything that
requires judgement stays LLM-workflow; this script owns seven deterministic
operation groups against the main-anchored orchestrator store
(``.plan/local/orchestrator/{slug}/``, resolved via
``file_ops.get_store_dir('orchestrator', slug)``):

- ``scaffold --slug S`` — create the epic directory tree (idempotent).
- ``queue --slug S [--transition PLAN-NN --status X | --set-row PLAN-NN
  --field F --value V]`` — a three-way surface over the plan queue in
  ``status.json``: read the whole queue, transition one plan's ``status``,
  or set one result field (:data:`PLAN_ROW_FIELDS`) of one plan row. Both
  write forms mutate the located row inside the shared ``rmw_json``
  critical section, so no unsynchronised whole-array rewrite remains.
- ``resume-summary --slug S`` — generate the two derivable ``epic.md`` blocks
  from ``status.json`` (the machine authority) and the filesystem for the LLM to
  paste between their generated-block markers: the ``summary`` (START-HERE) block
  and the ``ordered_queue`` (Ordered Queue table) block. This is the lightweight
  render path a reconciling verb calls after a queue change; ``compact`` rewrites
  the SAME two blocks in place at ``cleanup``, sharing these renderers. Two
  detectors run on the RENDERED START-HERE block and ride the same payload:
  ``count_divergences[]`` (a claimed count that does not match its derivation)
  and ``contradictions[]`` (two mutually-exclusive claims inside one rendering).
  Both report and neither rewrites.
- ``archive --slug S`` — relocate a *closed* epic tree to
  ``.plan/local/archived-orchestrators/{slug}/`` (a mechanical, post-close
  directory move that requires no judgement; refuses a non-closed epic).
- ``compact --slug S`` — the ledger-compaction stage ``workflow/cleanup.md``
  Phase B calls: regenerate every DERIVABLE surface of ``epic.md`` in place (the
  START-HERE resume summary and the Ordered Queue table) from ``status.json``
  and the staged specs, leaving every byte OUTSIDE the ``BEGIN/END GENERATED``
  markers untouched, then verify the invariants (bidirectional queue
  reconciliation, no terminal row in the live queue, relocation-pointer
  reachability) and report every mutation and every abstention. Idempotent — a
  second run finds every block ``unchanged`` and writes nothing. Refuses a
  closed epic (``refused_closed``): compaction is a live-epic operation only.
  The narrative-versus-settled RELOCATION judgement is NOT here; it stays LLM.
- ``corpus {enumerate,cross-check,verdicts,set-verdict}`` — the epic's staged
  spec corpus: reconcile the ``status.json`` ``plans[]`` queue against the
  ``plans/PLAN-*.md`` spec files in BOTH directions, cross-check those specs
  against sibling epics and live plans for duplicate work (the arm a single
  ledger structurally cannot perform, scored on ``manage-status
  sibling-collision-check``'s two classes), and read/write the re-grounding
  verdict field defined once in
  ``persona-plan-orchestrator/standards/orchestration-model.md``
  § Re-Grounding Verdict Field. ``set-verdict`` is the group's single write
  action and the ONLY code path that formats a ``verdict:`` line; ``verdicts``
  is the only one that interprets one.
- ``cleanup restart-check --slug S`` — the restart-readiness verdict: one row
  per observed signal, each carrying its own three-valued verdict, its own
  evidence, and the population it was derived from, plus the floor over the
  participating rows and the sample instant. An unreadable or disagreeing
  observation resolves to ``indeterminate`` and never to ``not_ready``.
- ``inbox {write,amend,supersede,close-stream,validate,list,archive,
  migrate-archive,detect,landing-check}`` — the epic's plan-writable OUTBOX and
  its orchestrator-side drain: append one ``inbox/{sender_id}-{NNN}.md`` message,
  correct a filed message body in place (``amend`` — preserves ``created``,
  stamps a monotonic ``revision``), retire a message in favour of a successor
  (``supersede`` — tombstone-style), mark a sender's stream ended
  (``close-stream``), validate an existing message against the envelope schema,
  enumerate the queued messages with their validation verdicts and lifecycle,
  retire a consumed message to ``inbox/archive/{sender}/``, fold a flat archive
  into that per-sender layout (``migrate-archive``), classify a plan's
  ``source_id`` pointer as orchestrated, or report whether a landing message
  carries its required machine-readable facts (``landing-check``). Backed by
  :mod:`_orchestrator_inbox`;
  the write boundary is enforced by construction there (no caller-supplied
  output path exists).

The ``kind=orchestrator`` ``status.json`` schema is owned by
``manage-status/standards/status-lifecycle.md``; ``status.json`` is created
via ``manage-status create --store orchestrator``, never by this script.
No implementation-side capability (no build/CI/source verbs) exists here.
"""

import argparse
import re
import shutil
import subprocess
from collections import Counter
from collections.abc import Callable, Collection
from pathlib import Path
from typing import Any

from _cmd_sibling_collision import (
    _OVERLAP_JOIN,
    _extract_paths,
    _iter_active_plan_dirs,
    _read_affected_files,
    _read_request_source,
)
from _locks_core import rmw_json
from _orchestrator_inbox import (
    INBOX_SUBDIR,
    KINDS,
    RUNNING_STATUS,
    SENDER_TYPES,
    InboxCounts,
    cmd_inbox_amend,
    cmd_inbox_archive,
    cmd_inbox_close_stream,
    cmd_inbox_detect,
    cmd_inbox_landing_check,
    cmd_inbox_list,
    cmd_inbox_migrate_archive,
    cmd_inbox_supersede,
    cmd_inbox_validate,
    cmd_inbox_write,
    inbox_counts,
)
from file_ops import (
    get_archived_orchestrator_dir,
    get_store_dir,
    now_utc_iso,
    output_toon,
    read_json,
    safe_main,
)
from input_validation import validate_plan_id

ORCHESTRATOR_STORE = 'orchestrator'

# Epic subdirectories per the layout contract in
# persona-plan-orchestrator/standards/orchestration-model.md.
EPIC_SUBDIRS = ('workstreams', 'plans', 'landings', 'logs', INBOX_SUBDIR)

FILE_STATUS = 'status.json'

# The per-row RESULT fields ``queue --set-row`` may write. Deliberately narrow:
# ``status`` stays exclusive to ``--transition`` (a status change and a landing
# stamp are independent events), and ``id``/``slug``/``workstream`` are row
# identity, not result, so they are seeded by ``decompose`` and never patched.
PLAN_ROW_FIELDS = frozenset({'plan_marshall_plan_id', 'pr', 'landing'})

# Statuses at which a plan row is finished, so its result links are expected to
# be present. A terminal row missing one is the reconciliation gap the summary's
# completeness marker surfaces. Both spellings are live in the corpus:
# ``analyze`` writes ``shipped``, while archived ledgers carry ``landed``.
TERMINAL_PLAN_STATUSES = ('shipped', 'landed')

# The result links a terminal row must carry, in the fixed order the gap marker
# names them.
TERMINAL_REQUIRED_FIELDS = ('pr', 'landing')

# --- corpus group ----------------------------------------------------------

# The epic subdirectory holding the staged plan specs, and the filename shape
# the layout contract gives them (``plans/PLAN-NN-{plan_slug}.md``).
PLANS_SUBDIR = 'plans'
SPEC_GLOB = 'PLAN-*.md'

# ``RUNNING_STATUS`` — a row at this status is enumerated but carries
# ``excluded_reason`` so a caller cannot re-scope it: re-scoping a spec
# mid-execution changes the brief under a running plan (orchestration-model.md
# § Cleanup Contract, running-row exclusion). The token is defined once, in
# ``_orchestrator_inbox`` (which also needs it for the inbox deliverability
# guard), and imported above so the two modules cannot drift.

# The re-grounding verdict field. The grammar is defined ONCE, in
# ``persona-plan-orchestrator/standards/orchestration-model.md``
# § Re-Grounding Verdict Field; these constants are its only implementation.
VERDICT_KEYS = ('verdict', 'checked_at', 'by', 'rescoped', 'evidence')
VERDICT_VALUES = ('corroborated', 'contradicted', 'unverifiable')
RESCOPED_VALUES = ('yes', 'no', 'n/a')
VERDICT_SEPARATOR = ' | '
# At most four splits, so ``evidence`` is the whole remainder of the line and a
# ``' | '`` inside the evidence text survives intact.
VERDICT_MAX_SPLITS = len(VERDICT_KEYS) - 1
VERDICT_PREFIX = f'{VERDICT_KEYS[0]}:'
# The verdict reported for a bullet that does not parse. Never a fourth member of
# VERDICT_VALUES: it is a parse outcome, not a settlement. Named apart from the
# readiness vocabulary's :data:`READINESS_INDETERMINATE` even though the two share
# a spelling — they are independent vocabularies, and one binding for both would
# let a change to either silently move the other.
VERDICT_INDETERMINATE = 'indeterminate'
BLOCKING_RESCOPED = 'no'
CONTRADICTED = 'contradicted'
NOT_APPLICABLE = 'n/a'

# --- resume-summary self-validation ----------------------------------------

#: The count claims a rendered START-HERE block can assert about the plan queue,
#: each paired with the derivation it is checked against. ``row``/``plan`` are
#: the whole population; the rest are per-status tallies read from ``plans[]``.
COUNT_CLAIM_NOUNS = ('rows', 'plans', 'staged', 'shipped', 'running', 'parked', 'landed')

#: The noun alternation, DERIVED from :data:`COUNT_CLAIM_NOUNS` so that tuple is the
#: single source defining the population. A noun that is already plural (ends in
#: ``s``) contributes an optional-``s`` form matching both numbers; every other noun
#: is a status name that does not pluralise and contributes itself literally. The
#: derivation rule reads the noun's own spelling, so it introduces no second list to
#: keep in step. Deriving matters because :func:`_derive_counts` builds its keys from
#: ``COUNT_CLAIM_NOUNS`` alone: a noun present in a hand-written alternation but absent
#: from the tuple would make :func:`_count_divergences` raise ``KeyError`` at
#: ``derived[key]``.
_COUNT_CLAIM_ALTERNATION = '|'.join(
    f'{noun[:-1]}s?' if noun.endswith('s') else noun for noun in COUNT_CLAIM_NOUNS
)

#: One count claim plus the short tail that follows it. The tail is captured in a
#: LOOKAHEAD so a SCOPED claim can be recognised (see :data:`_SCOPED_CLAIM_RE`)
#: without the scan consuming it: a consuming tail would advance the cursor past
#: the next claim, so a sentence asserting two counts would only ever have its
#: first one checked.
_COUNT_CLAIM_RE = re.compile(
    r'(?<![\w.])(?P<value>\d+)\s+(?P<noun>' + _COUNT_CLAIM_ALTERNATION + r')\b'
    r'(?=(?P<tail>.{0,12}))',
    re.IGNORECASE,
)

#: A qualifier immediately after a count claim scopes it to a SUB-population, so
#: the claim is not comparable to the whole-epic derivation. This is the
#: denominator trap: "12 rows in WS-01" is correctly different from the epic's
#: 30 rows, and reporting that as a divergence is the false positive that would
#: teach every reader to ignore the detector.
#: The leading ``^\s*`` anchors at the start of the twelve-character tail
#: :data:`_COUNT_CLAIM_RE` captured mid-line, NOT at the start of a document
#: line, so it is a token separator and not an indentation rule — see the
#: markdown-line-scanner block below for the regexes that do carry one.
_SCOPED_CLAIM_RE = re.compile(r'^\s*(in|of|for|under|within|across|from)\b', re.IGNORECASE)

#: A capacity claim of the recorded ``R = N of M`` shape. Two such claims over
#: the SAME denominator that disagree on the numerator cannot both hold in one
#: rendering, and each half is individually plausible — which is why the
#: contradiction is only visible by reading the rendering as a whole.
_RATIO_CLAIM_RE = re.compile(r'R\s*=\s*(?P<numerator>\d+)\s+of\s+(?P<denominator>\d+)', re.IGNORECASE)

# --- cleanup group ---------------------------------------------------------

#: The readiness vocabulary, ordered WORST-FIRST. The order IS the floor: the
#: overall verdict is ``min`` over the participating signals under this order,
#: so a single unobservable signal degrades the report to ``indeterminate`` and
#: only a definite hazard reaches ``not_ready``. Keeping the two apart is the
#: point — collapsing an unobservable signal into a failing one is the
#: confident-signal defect this verb exists to remove.
READINESS_ORDER = ('not_ready', 'indeterminate', 'ready')
READY = 'ready'
NOT_READY = 'not_ready'
#: The readiness verdict for an arm whose surface could not be observed. Distinct
#: from :data:`VERDICT_INDETERMINATE`, which is a re-grounding PARSE outcome — the
#: two vocabularies coincide in spelling only, so each carries its own binding.
READINESS_INDETERMINATE = 'indeterminate'

#: The verdict an arm reports when the surface it would observe is owned by
#: another component. It is deliberately NOT a member of
#: :data:`READINESS_ORDER`: such an arm is neither ready nor not-ready, so it is
#: excluded from the floor — a floor over an unowned surface would let another
#: component's gap veto this one's verdict.
NOT_AVAILABLE = 'not_available'

#: The spec that owns the registry/executor parity surface. Named in the
#: ``registry_parity`` arm's evidence so the report points at the owner rather
#: than leaving a silent gap. This component observes that surface not at all.
REGISTRY_PARITY_OWNER = 'PLAN-TRUTH-059'

# --- compact stage (ledger compaction) -------------------------------------
#
# The compact stage regenerates every DERIVABLE surface of ``epic.md`` in place
# — the content between a ``BEGIN/END GENERATED`` marker pair, and nothing else.
# Everything outside the markers is narrative and is left byte-identical, which
# is what makes "a retraction survives a pass verbatim" a structural property
# rather than a test coincidence. The narrative-versus-settled RELOCATION
# judgement is NOT here — it stays with the orchestrator (``workflow/cleanup.md``
# Step 8); this stage regenerates the derivable, verifies the invariants, reports.

FILE_EPIC = 'epic.md'
FILE_SETTLED = 'settled.md'

#: The phase at which the epic is frozen. The compact stage MUTATES ``epic.md``,
#: so it refuses a closed epic — that tree is the frozen audit record ``close``
#: already sealed, and compaction is a live-epic operation only.
CLOSED_PHASE = 'closed'

#: Plan statuses whose row belongs in a landing record, not the LIVE Ordered
#: Queue. Shares :data:`TERMINAL_PLAN_STATUSES`' membership by construction so
#: the two never drift; named apart to document the queue-exclusion intent.
LIVE_QUEUE_EXCLUDED_STATUSES = TERMINAL_PLAN_STATUSES

#: The two GENERATED marker pairs the compact stage regenerates, each keyed by
#: the block name that rides in the marker comment. Order is the emission order
#: in ``templates/epic.md``. A block whose markers are ABSENT from a given
#: epic.md is reported as ``markers_absent`` and skipped — never fabricated,
#: because inserting markers into a hand-authored document is a structural edit
#: the stage has no mandate to make.
GENERATED_BLOCKS = ('resume-summary', 'ordered-queue')

#: The ``##`` section of ``templates/epic.md`` that OWNS each generated block —
#: the heading a reader would look under to find that derivable surface. Used
#: only to key a block's ``markers_absent`` outcome back onto the section the
#: compaction report names, so a section the stage COULD NOT reach is
#: distinguishable from one it deliberately left alone. Titles are matched
#: case-insensitively after stripping, since epic.md is hand-authored. A block
#: whose owning heading is absent from a given epic.md yields no abstained row at
#: all; its absence is still reported as that block's ``markers_absent`` outcome
#: in ``regenerated[]``.
GENERATED_BLOCK_OWNING_SECTION: dict[str, str] = {
    'resume-summary': 'START HERE',
    'ordered-queue': 'Ordered Queue',
}

#: The two ``abstained[]`` treatments. ``preserved_verbatim`` is a CHOICE — the
#: section carries no derivable surface, so leaving it alone is the correct
#: outcome. ``markers_absent_not_regenerated`` is a BLIND SPOT — the section
#: carries a derivable surface whose marker pair is missing, so the stage could
#: not reach it and regenerated nothing. Emitting the first for the second would
#: report a deliberate abstention the stage never made.
TREATMENT_PRESERVED = 'preserved_verbatim'
TREATMENT_UNREACHABLE = 'markers_absent_not_regenerated'

def _begin_marker(name: str) -> str:
    return f'<!-- BEGIN GENERATED: {name} -->'

def _end_marker(name: str) -> str:
    return f'<!-- END GENERATED: {name} -->'

#: A settled-narrative relocation pointer left at a section's origin in
#: ``epic.md``. It names the destination heading in ``settled.md`` in double
#: quotes, so the compact stage can verify the pointer RESOLVES — a reader
#: following the old path must land on the content, not on absence. The
#: relocation itself is the orchestrator's judgement act; this regex is only the
#: reachability check's parser.
_RELOCATION_POINTER_RE = re.compile(r'settled\.md[^"\n]*§\s*"(?P<heading>[^"]+)"')

#: Cell separator for a rendered Ordered Queue row's Surface list. A markdown
#: table cell cannot carry a bare pipe, so the joiner is a semicolon and any
#: pipe inside a path is escaped by :func:`_queue_cell` before it is emitted.
_SURFACE_JOIN = '; '

# --- markdown line scanners -------------------------------------------------
#
# The five regexes in this block are the module's COMPLETE set of markdown
# construct models, and every line-wise scan in the file runs through one of
# them against the mask :func:`_fenced_mask` builds. They are grouped here, each
# stating which CommonMark clauses it honours and which it deliberately does
# not, because three successive review rounds found the same defect class in a
# different clause of the same scanners: a line matcher that reads correctly in
# isolation while parsing a document the spec author does not see rendered.
# The module's five OTHER regexes — :data:`SPEC_POINTER_RE`,
# :data:`_CHECKED_AT_RE`, :data:`_COUNT_CLAIM_RE`, :data:`_SCOPED_CLAIM_RE` and
# :data:`_RATIO_CLAIM_RE` — match tokens WITHIN a line and model no markdown
# construct, so no block-indentation clause applies to any of them. (The
# ``^\s*`` on :data:`_SCOPED_CLAIM_RE` anchors at the start of a twelve-character
# tail captured mid-line, not at the start of a document line, so it is not an
# indentation rule either.)
#
# Honoured by EVERY scanner in this block: CommonMark bounds block-level leading
# indentation to 0-3 SPACES (spec sections 2.2, 4.2 and 4.5); a fourth column of
# indentation starts an indented code block instead, so the construct is body
# text. A tab counts as four columns under the tab-stop rule, so a tab-indented
# delimiter or heading is never one. That is why the bound below is written over
# the literal space character as ``{0,3}`` and never over ``\s``: ``\s`` would
# readmit both the fourth space and the tab.
#
# NOT honoured by ANY scanner in this block, deliberately: container context.
# The scan is line-wise and tracks no block structure, so a construct nested
# inside a block quote or carried as list-item content is not recognised at its
# container-relative column, and a setext heading (a ``===`` or ``---``
# underline beneath a paragraph) does not terminate a section. Recognising
# either requires a block parser, which this module does not carry; the
# spec-authoring convention is column-0 ATX headings and top-level fences. The
# failure direction is stated at each scanner it affects.

#: The two section headings the corpus verbs ADDRESS, and the generic ATX
#: heading that TERMINATES a section body.
#:
#: Honoured: the 0-3 space indent bound; the 1-6 character ``#`` run; the rule
#: that the run must be followed by a space, a tab, or the end of the line — so
#: ``#hashtag`` is not a heading, a seven-``#`` run is not one, and a bare
#: ``##`` line IS one; and the optional trailing closing ``#`` sequence on the
#: two addressed headings.
#: NOT honoured: setext headings, per the block note above. A setext underline
#: therefore fails to terminate a section, which OVER-extends the body rather
#: than truncating it — the direction that admits extra paths and extra claims
#: rather than silently dropping declared ones.
CLAIM_LABELS_HEADING_RE = re.compile(r'^ {0,3}##[ \t]+Claim Labels(?:[ \t]+#+)?[ \t]*$')
EXPECTED_SURFACE_HEADING_RE = re.compile(r'^ {0,3}##[ \t]+Expected Surface(?:[ \t]+#+)?[ \t]*$')
_HEADING_RE = re.compile(r'^ {0,3}#{1,6}(?:[ \t]|$)')

#: A ``- `` list bullet, with its leading whitespace captured as ``indent``.
#:
#: NOT honoured, and this is the one DELIBERATE indentation deviation in the
#: block: CommonMark's 0-3 space allowance for a top-level list item is not
#: applied, because ``indent`` here is a NESTING PROXY rather than a block
#: position. :func:`_parse_claims` reads an empty ``indent`` as "top-level
#: claim" and any non-empty one as "child of the preceding claim", under the
#: spec-authoring convention that a claim starts at column 0 and its
#: ``verdict:`` bullet is indented beneath it. Admitting a 1-3 space indent as
#: top-level would reclassify that two-space-indented ``verdict:`` child as a
#: SECOND claim, shifting every later ``--claim-index`` — strictly worse than
#: the deviation it would remove.
#: ALSO not honoured: the ``*`` and ``+`` bullet markers and ordered list items
#: (the convention is ``-``), empty list items (a ``-`` with no content carries
#: no claim), and CommonMark's content-column rule for nesting depth. The
#: marker must be followed by a space or a tab specifically, never by ``\s`` at
#: large, so a ``---`` thematic break is not read as a bullet.
_BULLET_RE = re.compile(r'^(?P<indent>[ \t]*)-[ \t]+(?P<text>.*)$')

#: A fenced-code-block delimiter line: three-or-more backticks or tildes, with
#: any info string. Group ``fence`` carries the WHOLE RUN — both the character
#: and its length — because CommonMark closes a block only on a run of the same
#: character that is AT LEAST AS LONG as the opener: a ``~~~`` line inside a
#: backtick fence is body text, and so is a three-backtick line inside a
#: four-backtick block. Group ``info`` carries whatever follows the run, because
#: only the OPENING fence may carry an info string; a delimiter with one is body
#: text, never a close.
#:
#: Honoured: the 0-3 space indent bound on BOTH the opening and the closing
#: delimiter, independently of each other (a four-space-indented delimiter
#: inside a block is body text, not a close — spec example 99); the tab
#: exclusion that follows from the same clause; the same-character rule; the
#: at-least-as-long rule; the no-info-string-on-a-close rule; the
#: trailing-whitespace-only allowance on a close; and — enforced in
#: :func:`_fenced_mask` rather than here, because it governs only an OPENING
#: backtick fence — the rule that a backtick fence's info string may not itself
#: contain a backtick.
#: NOT honoured: container context, per the block note above. The opening
#: fence's indentation is also not stripped from the body, because the mask is
#: per-line and never reproduces block content.
#:
#: Every line-wise markdown scan below runs against the mask this builds,
#: because a ``# comment`` inside a fence is not a heading and a ``- item``
#: inside one is not a bullet. This mirrors the fence suppression the sibling
#: detector in ``pm-plugin-development:ext-self-review-plan-marshall`` already
#: applies for the same reason.
_FENCE_DELIMITER_RE = re.compile(r'^ {0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$')

#: The backtick fence character, bound once so :func:`_fenced_mask` can name the
#: info-string clause it enforces instead of repeating a bare literal twice.
_BACKTICK = '`'

# --- token matchers (no markdown construct modelled) ------------------------

# The orchestrator spec pointer a launched plan's ``source_id`` carries, and the
# shape a spec uses to name a sibling spec. Normalized to the root-agnostic key
# ``{epic_slug}/plans/{spec_name}`` so the active and archived homes of the same
# epic yield the same origin id. Deliberately NARROW: a lesson path or an
# arbitrary repo file cited as background is NOT an origin pointer, which is what
# keeps "two specs citing the same lesson" a silent near-miss rather than a match.
SPEC_POINTER_RE = re.compile(
    r'\.plan/local/(?:orchestrator|archived-orchestrators)/'
    r'(?P<slug>[A-Za-z0-9_.\-]+)/plans/(?P<spec>PLAN-[A-Za-z0-9_.\-]+\.md)'
)
_CHECKED_AT_RE = re.compile(r'^[0-9a-f]{7,40}$')


def _error(slug: str, error: str, message: str, **extra: Any) -> dict[str, Any]:
    """Build the standard TOON error envelope for this script."""
    result: dict[str, Any] = {
        'status': 'error',
        'slug': slug,
        'store': ORCHESTRATOR_STORE,
        'error': error,
        'message': message,
    }
    result.update(extra)
    return result


def _validate_slug(slug: str) -> str | None:
    """Validate the epic slug (kebab-case, same shape as a plan id).

    Returns an error message string when invalid, ``None`` when valid.
    The validation is load-bearing: the slug becomes a directory name under
    the orchestrator store, so a malformed value (path separators, ``..``)
    must never reach ``get_store_dir``.
    """
    try:
        validate_plan_id(slug)
    except ValueError as exc:
        return str(exc)
    return None


def _epic_root(slug: str, allow_archived: bool = False) -> Path:
    """Resolve the epic's store root directory.

    ``allow_archived`` threads straight into
    :func:`file_ops.get_store_dir`'s read-fallback: when ``True`` and the active
    ``orchestrator/{slug}`` tree is absent, the archived home
    ``archived-orchestrators/{slug}`` is resolved instead (when it exists).
    READ verbs pass ``True``; ``scaffold``, ``queue --transition``, and the
    ``archive`` source resolution stay strict (default ``False``) so a frozen
    archived epic is never mutated at the active path.
    """
    return get_store_dir(ORCHESTRATOR_STORE, slug, allow_archived=allow_archived)


def _read_status(slug: str, allow_archived: bool = False) -> dict[str, Any]:
    """Read the epic's status.json (empty dict when absent or malformed).

    ``read_json`` degrades a missing/unreadable/unparseable file to ``{}``, but
    a status.json whose top-level JSON is valid-but-non-dict (an array, a bare
    string, ``null``) would otherwise reach ``dict(...)`` and raise. Fall back
    to ``{}`` on any non-dict parse so callers always receive a dict.

    ``allow_archived`` threads into :func:`_epic_root` so READ verbs resolve an
    archived epic transparently when its active tree is absent.
    """
    data = read_json(_epic_root(slug, allow_archived=allow_archived) / FILE_STATUS)
    if not isinstance(data, dict):
        return {}
    return dict(data)


def _set_row_field(row: dict[str, Any], field: str, value: str) -> dict[str, Any]:
    """Set one field of a plan row, returning the previous and new values."""
    previous = row.get(field, '')
    row[field] = value
    return {'previous': previous, 'new': value}


def _mutate_plan_row(
    slug: str, plan_id: str, apply: Callable[[dict[str, Any]], dict[str, Any]]
) -> dict[str, Any]:
    """Apply ``apply`` to one ``plans[]`` row inside a serialized critical section.

    The single write path for the plan queue: both ``--transition`` and
    ``--set-row`` route through here, so no unsynchronised read-modify-write of
    ``plans[]`` remains. The mutation runs against the FRESH in-lock state via
    the shared ``O_EXCL``-guarded :func:`_locks_core.rmw_json` — the same
    critical section ``manage-status update-field`` uses for this very document
    — so a concurrent orchestrator session stamping a DIFFERENT row (or a
    different field of the same row) cannot be clobbered by a last-writer-wins
    over a stale read. ``updated`` is re-stamped only when a row was located.

    Returns a dict carrying either ``result`` (the value ``apply`` returned for
    the located row) or ``available_plans`` (every queued plan id) when
    ``plan_id`` is absent from the queue.
    """
    outcome: dict[str, Any] = {}

    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        plans = state.get('plans', [])
        for row in plans:
            if row.get('id') == plan_id:
                outcome['result'] = apply(row)
                state['updated'] = now_utc_iso()
                return state
        outcome['available_plans'] = [row.get('id', '') for row in plans]
        return state

    rmw_json(_epic_root(slug) / FILE_STATUS, _mutate)
    return outcome


def cmd_scaffold(args: argparse.Namespace) -> dict[str, Any]:
    """Create the ``.plan/local/orchestrator/{slug}/`` directory tree.

    Idempotent: existing directories are left untouched, re-running against
    an already-scaffolded epic succeeds and reports ``already_existed: true``.
    Does NOT create ``status.json`` — that is
    ``manage-status create --store orchestrator``'s job.
    """
    invalid = _validate_slug(args.slug)
    if invalid:
        return _error(args.slug, 'invalid_slug', invalid)
    root = _epic_root(args.slug)
    already_existed = root.is_dir()
    root.mkdir(parents=True, exist_ok=True)
    for sub in EPIC_SUBDIRS:
        (root / sub).mkdir(exist_ok=True)
    return {
        'status': 'success',
        'operation': 'scaffold',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'root': str(root),
        'already_existed': already_existed,
        'directories': list(EPIC_SUBDIRS),
    }


def cmd_queue(args: argparse.Namespace) -> dict[str, Any]:
    """Read the plan queue, transition one plan's status, or set one row field.

    Three-way surface over ``status.json``'s ``plans[]``:

    - **read** (no write flags): returns ``phase``, ``resume_anchor``, and the
      full ``plans[]`` queue.
    - **transition** (``--transition PLAN-NN --status X``): sets that plan's
      ``status``. The status vocabulary is owned by the orchestrator workflows;
      the script stores the supplied value verbatim.
    - **set-row** (``--set-row PLAN-NN --field F --value V``): sets one result
      field of that plan's row, where ``F`` is one of :data:`PLAN_ROW_FIELDS`.
      This is the sanctioned way to stamp a landing (``pr``, ``landing``,
      ``plan_marshall_plan_id``) without re-serializing the whole array.

    The two write forms are mutually exclusive, each triple/pair must be
    supplied complete, and both mutate the located row through
    :func:`_mutate_plan_row`'s critical section.
    """
    invalid = _validate_slug(args.slug)
    if invalid:
        return _error(args.slug, 'invalid_slug', invalid)
    set_row_args = (args.set_row, args.field, args.value)
    transition_args = (args.transition, args.status)
    set_row_given = any(arg is not None for arg in set_row_args)
    transition_given = any(arg is not None for arg in transition_args)
    if set_row_given and transition_given:
        return _error(
            args.slug,
            'wrong_parameters',
            '--set-row/--field/--value are mutually exclusive with --transition/--status',
        )
    if set_row_given and not all(arg is not None for arg in set_row_args):
        return _error(
            args.slug,
            'wrong_parameters',
            '--set-row, --field and --value must be supplied together',
        )
    if (args.transition is None) != (args.status is None):
        return _error(
            args.slug,
            'wrong_parameters',
            '--transition and --status must be supplied together',
        )
    if set_row_given and args.field not in PLAN_ROW_FIELDS:
        return _error(
            args.slug,
            'invalid_field',
            f'--field must be one of {sorted(PLAN_ROW_FIELDS)}, got: {args.field}',
        )
    # Read-path resolves an archived epic transparently; both write-paths stay
    # strict so an archived epic is never mutated at the active path.
    is_read = not set_row_given and not transition_given
    status_doc = _read_status(args.slug, allow_archived=is_read)
    if not status_doc:
        return _error(
            args.slug, 'file_not_found', 'status.json not found in orchestrator store'
        )
    if is_read:
        return {
            'status': 'success',
            'operation': 'queue',
            'slug': args.slug,
            'store': ORCHESTRATOR_STORE,
            'phase': status_doc.get('phase', ''),
            'resume_anchor': status_doc.get('resume_anchor', ''),
            'plans': status_doc.get('plans', []),
        }
    plan_id = args.set_row if set_row_given else args.transition
    field = args.field if set_row_given else 'status'
    value = args.value if set_row_given else args.status
    outcome = _mutate_plan_row(
        args.slug, plan_id, lambda row: _set_row_field(row, field, value)
    )
    if 'result' not in outcome:
        return _error(
            args.slug,
            'plan_not_found',
            f'plan {plan_id!r} not found in the queue',
            available_plans=outcome['available_plans'],
        )
    result = outcome['result']
    if set_row_given:
        return {
            'status': 'success',
            'operation': 'queue-set-row',
            'slug': args.slug,
            'store': ORCHESTRATOR_STORE,
            'plan': plan_id,
            'field': field,
            'previous_value': result['previous'],
            'new_value': result['new'],
        }
    return {
        'status': 'success',
        'operation': 'queue-transition',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'plan': plan_id,
        'previous_status': result['previous'],
        'new_status': result['new'],
    }


def _format_plan_line(plan: dict[str, Any]) -> str:
    """Render one plan as a summary line, appending the non-empty link fields.

    A row whose status is in :data:`TERMINAL_PLAN_STATUSES` and that is missing
    any of :data:`TERMINAL_REQUIRED_FIELDS` also carries a deterministic ASCII
    gap marker — ``(!) missing: pr, landing`` — naming the absent fields in that
    fixed order. The marker is a TERMINAL-status signal, not a general emptiness
    signal: a staged or running row with empty links is mid-flight, not
    incomplete, and renders no marker. A fully-stamped terminal row also renders
    no marker, so correct data renders exactly as it did before the marker
    existed.
    """
    parts = [f'{plan.get("id", "?")} ({plan.get("workstream", "?")})']
    if plan.get('plan_marshall_plan_id'):
        parts.append(f'plan={plan["plan_marshall_plan_id"]}')
    if plan.get('pr'):
        parts.append(f'PR {plan["pr"]}')
    if plan.get('landing'):
        parts.append(f'landing={plan["landing"]}')
    if plan.get('status') in TERMINAL_PLAN_STATUSES:
        missing = [field for field in TERMINAL_REQUIRED_FIELDS if not plan.get(field)]
        if missing:
            parts.append(f'(!) missing: {", ".join(missing)}')
    return ' — '.join(parts)


def _format_inbox_line(counts: InboxCounts) -> str:
    """Render the derived inbox line for the START-HERE block.

    Kept a separate line from ``**Resume anchor**`` on purpose: the anchor is
    the operator's prose and the inbox line is the live filesystem count, so a
    stale narrative count sits VISIBLY BESIDE the derived one instead of
    outranking it. An absent ``inbox/`` renders that fact explicitly rather
    than rendering ``0 queued`` — the same *which zero is this* rule
    ``inbox list``'s ``inbox_state`` enforces.
    """
    if not counts.present:
        return '**Inbox (derived)**: no inbox directory (nothing to drain from)'
    return (
        f'**Inbox (derived)**: {counts.queued} queued, {counts.archived} archived'
    )


def _build_summary(status_doc: dict[str, Any], counts: InboxCounts) -> str:
    """Build the START-HERE markdown block, derived purely from status.json.

    Renders the resume anchor, the epic phase, the derived inbox counts, the
    running/parked plans, the staged queue (in ``plans[]`` order), and a
    residual per-status listing for every other status value — so no plan is
    ever invisible in the summary.

    Terminal rows that are missing a result link carry the gap marker
    :func:`_format_plan_line` appends, so an unreconciled landing is visible in
    the generated block rather than only in the raw status.json.

    ``resume_anchor`` is rendered VERBATIM. The fix for a narrative count that
    has gone stale is derivation beside the prose (the
    :func:`_format_inbox_line` line), never silent rewriting of what the
    operator wrote.

    Args:
        status_doc: The epic's parsed ``status.json`` — the machine authority.
        counts: The filesystem-derived inbox tallies from
            :func:`inbox_counts`. Passed in rather than derived here so this
            helper stays a pure renderer over already-resolved inputs.
    """
    plans = status_doc.get('plans', [])
    lines = [
        f'**Resume anchor**: {status_doc.get("resume_anchor") or "(not set)"}',
        f'**Phase**: {status_doc.get("phase", "")}',
        _format_inbox_line(counts),
    ]
    running = [p for p in plans if p.get('status') == 'running']
    parked = [p for p in plans if p.get('status') == 'parked']
    staged = [p for p in plans if p.get('status') == 'staged']
    other = [p for p in plans if p.get('status') not in ('running', 'parked', 'staged')]
    for label, group in (('Running', running), ('Parked', parked)):
        if group:
            lines.append(f'**{label}**:')
            lines.extend(f'- {_format_plan_line(plan)}' for plan in group)
    lines.append('**Queue** (staged, in order):')
    if staged:
        lines.extend(
            f'{position}. {_format_plan_line(plan)}'
            for position, plan in enumerate(staged, start=1)
        )
    else:
        lines.append('- (empty)')
    for plan in other:
        lines.append(f'- {_format_plan_line(plan)} — status: {plan.get("status", "")}')
    return '\n'.join(lines)


def _derive_counts(status_doc: dict[str, Any]) -> dict[str, int]:
    """Re-derive, from ``status.json``, every count a rendered block can claim."""
    plans = [plan for plan in status_doc.get('plans', []) if isinstance(plan, dict)]
    tally = Counter(str(plan.get('status', '')) for plan in plans)
    derived = {'rows': len(plans), 'plans': len(plans)}
    for noun in COUNT_CLAIM_NOUNS:
        if noun not in derived:
            derived[noun] = tally.get(noun, 0)
    return derived


def _claim_key(noun: str) -> str:
    """Normalize a claim noun to its derivation key (``row``/``rows`` collapse)."""
    lowered = noun.lower()
    if lowered in ('row', 'rows'):
        return 'rows'
    if lowered in ('plan', 'plans'):
        return 'plans'
    return lowered


def _count_divergences(summary: str, status_doc: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    """Compare every count the RENDERED block claims against its derivation.

    Runs on the rendering rather than on the inputs, because in every recorded
    divergence the inputs were individually fine and the rendering combined them
    wrongly — a narrated anchor sentence and the generator's own enumeration
    disagreeing inside one emission.

    Returns ``(divergences, claims_scanned)`` so a zero divergence count always
    rides with the population it was computed over.
    """
    derived = _derive_counts(status_doc)
    divergences: list[dict[str, Any]] = []
    scanned = 0
    for match in _COUNT_CLAIM_RE.finditer(summary):
        if _SCOPED_CLAIM_RE.match(match.group('tail')):
            continue
        scanned += 1
        key = _claim_key(match.group('noun'))
        narrated = int(match.group('value'))
        if narrated != derived[key]:
            divergences.append(
                {
                    'claim': f'{match.group("value")} {match.group("noun")}',
                    'narrated': narrated,
                    'derived': derived[key],
                }
            )
    return divergences, scanned


def _rendering_contradictions(summary: str) -> tuple[list[dict[str, Any]], int]:
    """Detect mutually-exclusive claims INSIDE one rendering.

    Two ``R = N of M`` claims sharing a denominator but disagreeing on the
    numerator cannot both hold, yet each is individually plausible — so the
    contradiction exists only in the rendering as a whole. Both claim sites are
    named, in the order they appear.

    Returns ``(contradictions, claims_scanned)``.
    """
    claims: list[tuple[int, int, str]] = [
        (int(match.group('denominator')), int(match.group('numerator')), match.group(0).strip())
        for match in _RATIO_CLAIM_RE.finditer(summary)
    ]
    contradictions: list[dict[str, Any]] = []
    for index, (denominator, numerator, text) in enumerate(claims):
        for other_denominator, other_numerator, other_text in claims[index + 1 :]:
            if denominator == other_denominator and numerator != other_numerator:
                contradictions.append(
                    {
                        'denominator': denominator,
                        'left': text,
                        'right': other_text,
                    }
                )
    return contradictions, len(claims)


def cmd_resume_summary(args: argparse.Namespace) -> dict[str, Any]:
    """Generate the two derivable ``epic.md`` blocks from status.json.

    The returned ``summary`` field is the START-HERE block, and ``ordered_queue``
    is the Ordered Queue table body — both markdown the LLM pastes verbatim
    between their respective ``BEGIN/END GENERATED`` markers (``resume-summary``
    and ``ordered-queue``). Both are derived purely from ``status.json`` — the
    machine authority — and the filesystem, never from the prose already in
    ``epic.md``. This is the LIGHTWEIGHT render path a reconciling verb
    (``decompose``, ``analyze``, ``lessons``) calls after a queue change; the
    ``compact`` stage rewrites the SAME two blocks in place at ``cleanup``, so a
    routine reconciliation keeps both derivable surfaces truthful without a full
    compaction, and the two paths share the renderers rather than duplicating them.

    The inbox counts are the one part NOT read out of ``status.json``: they are
    derived at render time from the epic's ``inbox/`` directory via
    :func:`inbox_counts`, and they are AUTHORITATIVE over any count sentence in
    ``resume_anchor``. ``inbox_queued`` / ``inbox_archived`` / ``inbox_state``
    ride the payload as top-level fields so a caller can reconcile them against
    ``inbox list`` without parsing the markdown block.

    Two detectors run on the RENDERED START-HERE block and ride the same payload
    beside ``summary``: ``count_divergences[]`` (a count the block claims that
    does not match its derivation from ``status.json``) and ``contradictions[]``
    (two mutually-exclusive claims inside one rendering). Both REPORT and neither
    mutates — the block is never silently rewritten, which preserves the
    existing derivation-beside-the-prose rule. Each list rides with the
    population it was computed over, so a zero states which zero it is.
    """
    invalid = _validate_slug(args.slug)
    if invalid:
        return _error(args.slug, 'invalid_slug', invalid)
    status_doc = _read_status(args.slug, allow_archived=True)
    if not status_doc:
        return _error(
            args.slug, 'file_not_found', 'status.json not found in orchestrator store'
        )
    root = _epic_root(args.slug, allow_archived=True)
    counts = inbox_counts(root / INBOX_SUBDIR)
    summary = _build_summary(status_doc, counts)
    ordered_queue = _build_ordered_queue(status_doc, root)
    divergences, count_claims_scanned = _count_divergences(summary, status_doc)
    contradictions, ratio_claims_scanned = _rendering_contradictions(summary)
    return {
        'status': 'success',
        'operation': 'resume-summary',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'inbox_queued': counts.queued,
        'inbox_archived': counts.archived,
        'inbox_state': 'present' if counts.present else 'missing',
        'count_claims_scanned': count_claims_scanned,
        'count_divergences_count': len(divergences),
        'count_divergences': divergences,
        'ratio_claims_scanned': ratio_claims_scanned,
        'contradictions_count': len(contradictions),
        'contradictions': contradictions,
        'summary': summary,
        'ordered_queue': ordered_queue,
    }


def cmd_archive(args: argparse.Namespace) -> dict[str, Any]:
    """Relocate a *closed* epic tree to ``archived-orchestrators/{slug}/``.

    A mechanical, post-close directory move (the fourth deterministic
    operation this script owns) — never a judgement call. Order of checks:

    - source absent, dest present → idempotent success (``already_archived``).
    - source absent, dest absent → ``error: not_found``.
    - source present, epic phase is not ``closed`` → ``error: not_closed`` with
      an actionable message; NO move is performed.
    - source present AND dest present → ``error: archive_conflict`` (never
      clobber the frozen audit record).
    - otherwise → create the archived parent and ``shutil.move`` the tree,
      returning ``archived_to``.
    """
    invalid = _validate_slug(args.slug)
    if invalid:
        return _error(args.slug, 'invalid_slug', invalid)
    source = _epic_root(args.slug)
    dest = get_archived_orchestrator_dir(args.slug)
    if not source.exists():
        if dest.exists():
            return {
                'status': 'success',
                'operation': 'archive',
                'slug': args.slug,
                'store': ORCHESTRATOR_STORE,
                'already_archived': True,
                'archived_to': str(dest),
            }
        return _error(
            args.slug,
            'not_found',
            f'epic {args.slug!r} has no active or archived tree to archive',
        )
    phase = _read_status(args.slug).get('phase', '')
    if phase != 'closed':
        return _error(
            args.slug,
            'not_closed',
            f'epic {args.slug} is phase={phase}; run close first, then archive',
            phase=phase,
        )
    if dest.exists():
        return _error(
            args.slug,
            'archive_conflict',
            f'epic {args.slug!r} already has an archived tree at {dest}; '
            'refusing to clobber the audit record',
            archived_to=str(dest),
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(dest))
    return {
        'status': 'success',
        'operation': 'archive',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'already_archived': False,
        'archived_to': str(dest),
    }


def _spec_paths(root: Path) -> list[Path]:
    """Enumerate the epic's staged spec files, sorted for determinism."""
    plans_dir = root / PLANS_SUBDIR
    if not plans_dir.is_dir():
        return []
    return sorted(path for path in plans_dir.glob(SPEC_GLOB) if path.is_file())


def _spec_matches_row(path: Path, plan_id: str) -> bool:
    """True when ``path`` is the spec file of the queue row ``plan_id``.

    The layout contract names specs ``plans/PLAN-NN-{plan_slug}.md`` while the
    row id is the bare ``PLAN-NN`` prefix, so the match is exact-or-prefix on the
    stem WITH the separating hyphen. The hyphen is load-bearing: without it
    ``PLAN-1`` would claim ``PLAN-10-foo.md``.
    """
    return path.stem == plan_id or path.stem.startswith(f'{plan_id}-')


def _read_spec(path: Path) -> tuple[str | None, str]:
    """Read one spec file, returning ``(text, error_code)``.

    A file that cannot be read is REPORTED, never silently dropped — the same
    report-never-skip rule ``inbox list`` applies. ``error_code`` is the empty
    string on success.
    """
    try:
        return path.read_text(encoding='utf-8'), ''
    except (OSError, UnicodeDecodeError):
        return None, 'unreadable'


#: Wall-clock budget for a single read-only git call. A hung git degrades the
#: readiness report to ``indeterminate`` rather than stalling the verb outright.
_GIT_READ_TIMEOUT_SECONDS = 30

#: The CLOSED set of read-only git operations this script may run, each mapped to
#: the exact argv it expands to. This table is the single authority: a caller
#: names an OPERATION and never supplies git arguments, so the argv reaching
#: :func:`subprocess.run` is always a constant selected from here rather than
#: anything a caller composed. That is what keeps ``cleanup restart-check`` a
#: pure readiness PROBE — an unrestricted argv seam would let a later caller
#: route a mutating command through a verb whose entire contract is that it
#: observes without writing, and no amount of care at the call sites would make
#: that unreachable. Adding a read is a one-line addition here; adding a WRITE
#: is a visible change to a table that says it holds only reads.
_GIT_READ_OPERATIONS: dict[str, tuple[str, ...]] = {
    'head-sha': ('rev-parse', 'HEAD'),
    'worktree-status': ('status', '--porcelain'),
}


def _git_read(operation: str) -> tuple[str | None, str]:
    """Run one read-only git operation BY NAME, returning ``(stdout, error)``.

    The single git seam in this script. ``operation`` selects an entry of
    :data:`_GIT_READ_OPERATIONS`; the argv is never caller-composed.
    ``(None, reason)`` is returned whenever the command could not be observed —
    git unreachable, a timeout, or a non-zero exit — and the reason names which.
    Callers translate that into an *unobservable* outcome, never into a failing
    one.

    An operation absent from the table raises :class:`KeyError` rather than
    degrading to unobservable. That is deliberate: an unknown operation is a
    defect in THIS module, and reporting it as "git is not readable" would dress
    a coding error up as an environmental one — the confident-signal-hides-a-
    caveat shape this verb exists to remove. The table is closed and its only
    callers are in this file, so no input can reach that branch.

    The timeout is what keeps "unobservable" reachable at all. Without it a hung
    git — a stale index lock, or a very large worktree — blocks forever, and
    because :func:`_worktree_signal` calls this seam twice, ``cleanup
    restart-check`` would stall with no verdict rather than degrading to
    ``indeterminate``. A hang is therefore mapped onto the existing unobservable
    path instead of being allowed to consume the caller.
    """
    argv = _GIT_READ_OPERATIONS[operation]
    try:
        completed = subprocess.run(
            ['git', *argv], capture_output=True, text=True, check=False, timeout=_GIT_READ_TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired:
        return None, f'git {" ".join(argv)} timed out after {_GIT_READ_TIMEOUT_SECONDS}s'
    except OSError as exc:
        return None, f'git could not be run ({exc.__class__.__name__})'
    if completed.returncode != 0:
        return None, f'git {" ".join(argv)} exited {completed.returncode}'
    return completed.stdout.strip(), ''


def _current_head_sha() -> str:
    """Return the current HEAD sha, or the empty string when it cannot be read.

    Used only to derive the ``stale`` flag on a parsed verdict. An unresolvable
    HEAD yields ``stale: false`` for every row and rides in the payload as an
    empty ``head_sha``, so a caller can tell "not stale" from "staleness was not
    computable" instead of reading an unqualified boolean.
    """
    output, _ = _git_read('head-sha')
    return output or ''


def _fenced_mask(lines: list[str]) -> list[bool]:
    """Return a per-line mask marking every line that belongs to a fenced block.

    Delimiter lines are masked along with the body, so a caller can test one
    index without also testing its neighbours. BOTH decisions — whether a line
    OPENS a block and whether it CLOSES one — are taken against the CommonMark
    clauses enumerated at :data:`_FENCE_DELIMITER_RE`, so the mask agrees with
    what the spec author sees rendered. A block opens only on a delimiter
    indented at most three spaces whose info string is admissible for its fence
    character, and closes only on a delimiter indented at most three spaces,
    built from the SAME character as the opener, AT LEAST AS LONG as the opener,
    and carrying no info string. The opening run's LENGTH is therefore retained,
    not just its character — a four-backtick block that contains a
    three-backtick example stays open across that example instead of ending at
    it. An unterminated fence runs to the end of the document.

    The property held here is FIDELITY to the rendered document, not a uniform
    bias toward one reading. The two are not the same, and an earlier revision
    of this docstring claimed the latter: that every branch treats text which
    may be code as code, never the reverse. That claim was false in the opening
    direction and is withdrawn — declining to CLOSE on a four-space-indented
    delimiter widens the masked run, while declining to OPEN on one narrows it,
    and both are the CommonMark reading. Both error directions are real damage:
    an over-wide mask hides a genuine heading, and an over-narrow one admits a
    fenced look-alike as one.

    Every line-wise scan in this module consumes this mask. Without it a
    ``# comment`` inside a fenced example matches :data:`_HEADING_RE` and
    truncates the enclosing section, which silently narrows a population while
    the count that rides beside it still reports the full denominator.
    """
    mask = [False] * len(lines)
    open_char = ''
    open_length = 0
    for index, line in enumerate(lines):
        match = _FENCE_DELIMITER_RE.match(line)
        if match is None:
            mask[index] = bool(open_char)
            continue
        run = match.group('fence')
        info = match.group('info')
        if open_char:
            mask[index] = True
            if run[0] == open_char and len(run) >= open_length and not info.strip():
                open_char, open_length = '', 0
            continue
        if run[0] == _BACKTICK and _BACKTICK in info:
            # Not an opening fence: a backtick fence's info string may not carry
            # a backtick, so this is an ordinary paragraph line — the shape a
            # sentence takes when it opens with the fence marker and then quotes
            # inline code. Masking it would swallow the rest of the document.
            continue
        mask[index] = True
        open_char, open_length = run[0], len(run)
    return mask


def _section_span(
    lines: list[str], heading_re: re.Pattern[str], fenced: list[bool] | None = None
) -> tuple[int, int]:
    """Return the ``[start, end)`` line span of one section's body.

    ``(-1, -1)`` when the document carries no matching heading. The body ends at
    the next heading of any level, so a subsection never leaks into the parent.

    Both heading scans — the one that OPENS the section and the one that closes
    it — skip fenced lines, per :func:`_fenced_mask`. ``fenced`` is computed from
    ``lines`` when not supplied, so a caller that already holds the mask passes
    it rather than rebuilding it.
    """
    if fenced is None:
        fenced = _fenced_mask(lines)
    start = -1
    for index, line in enumerate(lines):
        if not fenced[index] and heading_re.match(line):
            start = index + 1
            break
    if start < 0:
        return (-1, -1)
    for index in range(start, len(lines)):
        if not fenced[index] and _HEADING_RE.match(lines[index]):
            return (start, index)
    return (start, len(lines))


def _expected_surface_paths(text: str) -> set[str]:
    """Extract the file paths a spec names in its ``## Expected Surface`` section.

    This is the spec-side entry point for the file-overlap collision class: a
    staged spec carries its surface here, where a launched plan carries it in
    ``references.json`` ``affected_files``. The extraction itself is
    ``_cmd_sibling_collision``'s, unchanged — only the entry point differs.

    The section body is delimited against the fence mask, so a fenced path list
    whose first line is a ``#`` comment does not truncate the section and drop
    every path after it. Paths INSIDE the fence still count: a fenced list is the
    ordinary way a spec declares its surface.
    """
    lines = text.splitlines()
    start, end = _section_span(lines, EXPECTED_SURFACE_HEADING_RE)
    if start < 0:
        return set()
    return _extract_paths('\n'.join(lines[start:end]))


def _spec_pointers(text: str) -> set[str]:
    """Extract the normalized orchestrator spec pointers named in ``text``."""
    return {
        f'{match.group("slug")}/plans/{match.group("spec")}'
        for match in SPEC_POINTER_RE.finditer(text)
    }


def _own_pointer(slug: str, spec_name: str) -> str:
    """The root-agnostic origin id of one spec in one epic."""
    return f'{slug}/plans/{spec_name}'


def _parse_claims(lines: list[str]) -> list[dict[str, Any]]:
    """Parse the claim bullets of the ``## Claim Labels`` section.

    A claim is a TOP-LEVEL ``- `` bullet inside the section. Its verdict is the
    nested child bullet whose text begins with the literal ``verdict:`` token —
    association is by NESTING, never by ordinal position, so inserting or
    reordering a claim never re-binds an existing verdict to a different claim.

    Each returned record carries ``block_end``: the insertion point for a new
    verdict bullet, being one past the claim's own wrapped text lines and before
    any further bullet, with trailing blank lines excluded.

    Fenced lines are skipped on both scans: a ``- item`` inside a fenced example
    is not a claim, and a ``#`` comment inside one does not end the section.
    Admitting either would shift every later ``--claim-index`` and understate
    ``claims_total``.
    """
    fenced = _fenced_mask(lines)
    start, end = _section_span(lines, CLAIM_LABELS_HEADING_RE, fenced)
    if start < 0:
        return []
    claims: list[dict[str, Any]] = []
    for index in range(start, end):
        if fenced[index]:
            continue
        match = _BULLET_RE.match(lines[index])
        if match is None:
            continue
        indent = match.group('indent')
        text = match.group('text').strip()
        if not indent:
            claims.append(
                {
                    'index': len(claims),
                    'line': index,
                    'indent': indent,
                    'text': text,
                    'block_end': _claim_block_end(lines, index, end, fenced),
                    'verdict_line': -1,
                    'verdict_text': '',
                }
            )
        elif claims and text.startswith(VERDICT_PREFIX) and claims[-1]['verdict_line'] < 0:
            claims[-1]['verdict_line'] = index
            claims[-1]['verdict_text'] = text
    return claims


def _claim_block_end(
    lines: list[str], claim_line: int, section_end: int, fenced: list[bool] | None = None
) -> int:
    """One past the claim bullet's own text block — the verdict insertion point.

    The bullet/heading terminators are tested against the fence mask, so a fenced
    example nested under a claim does not end the claim's block early and place
    the verdict bullet inside the fence.
    """
    if fenced is None:
        fenced = _fenced_mask(lines)
    end = claim_line + 1
    while end < section_end:
        if not fenced[end] and (_BULLET_RE.match(lines[end]) or _HEADING_RE.match(lines[end])):
            break
        end += 1
    while end > claim_line + 1 and not lines[end - 1].strip():
        end -= 1
    return end


def _parse_verdict_text(text: str) -> dict[str, str] | None:
    """Parse one ``verdict:`` bullet body, or ``None`` when it does not conform.

    The parse rule both sides use: split on ``' | '`` with at most four splits,
    yielding five parts, so ``evidence`` is the fifth part and therefore the
    whole remainder of the line. Returning ``None`` is what makes a malformed
    bullet ``indeterminate`` at the caller instead of silently admitting it.
    """
    parts = text.split(VERDICT_SEPARATOR, VERDICT_MAX_SPLITS)
    if len(parts) != len(VERDICT_KEYS):
        return None
    parsed: dict[str, str] = {}
    for key, part in zip(VERDICT_KEYS, parts, strict=True):
        prefix = f'{key}:'
        if not part.startswith(prefix):
            return None
        parsed[key] = part[len(prefix) :].strip()
    if _invalid_verdict_values(parsed):
        return None
    return parsed


def _invalid_verdict_values(parsed: dict[str, str]) -> bool:
    """True when a parsed verdict violates the grammar's value rules."""
    return (
        parsed['verdict'] not in VERDICT_VALUES
        or parsed['rescoped'] not in RESCOPED_VALUES
        or (parsed['verdict'] != CONTRADICTED and parsed['rescoped'] != NOT_APPLICABLE)
        or not _CHECKED_AT_RE.match(parsed['checked_at'])
        or not parsed['by']
        or not parsed['evidence']
    )


def _format_verdict_line(values: dict[str, str]) -> str:
    """Format the verdict body. The ONLY formatter of this line in the tree."""
    return VERDICT_SEPARATOR.join(f'{key}: {values[key]}' for key in VERDICT_KEYS)


def _admits(verdict: str, rescoped: str) -> bool:
    """The admission predicate: block iff ``contradicted`` AND ``rescoped: no``.

    Every other settled state admits — an absent field is an open clause, and an
    ``unverifiable`` verdict is an unreached population, not a refutation.
    """
    return not (verdict == CONTRADICTED and rescoped == BLOCKING_RESCOPED)


def _verdict_row(spec_name: str, claim: dict[str, Any], line: str, head: str) -> dict[str, Any]:
    """Build one ``verdicts`` payload row for a claim carrying a verdict bullet."""
    parsed = _parse_verdict_text(str(claim['verdict_text']))
    if parsed is None:
        return {
            'spec': spec_name,
            'claim_index': claim['index'],
            'verdict': VERDICT_INDETERMINATE,
            'checked_at': '',
            'by': '',
            'rescoped': '',
            'evidence': '',
            'admits': False,
            'stale': False,
            'line': line,
        }
    return {
        'spec': spec_name,
        'claim_index': claim['index'],
        'verdict': parsed['verdict'],
        'checked_at': parsed['checked_at'],
        'by': parsed['by'],
        'rescoped': parsed['rescoped'],
        'evidence': parsed['evidence'],
        'admits': _admits(parsed['verdict'], parsed['rescoped']),
        'stale': bool(head) and not head.startswith(parsed['checked_at']),
        'line': line,
    }


def cmd_corpus_enumerate(args: argparse.Namespace) -> dict[str, Any]:
    """Reconcile the ``plans[]`` queue against the spec files, in BOTH directions.

    The enumeration authority is ``status.json``'s ``plans[]`` — never a
    ``plans/`` directory glob, which would return a different set the moment a
    spec is staged without a row (or a row recorded without a spec). The two
    directions are separate fields with separate causes: ``rows_without_spec``
    (a queue row whose spec file is absent) and ``specs_without_row`` (a spec
    file with no queue row) are never collapsed into one symmetric-difference
    count.

    Every count rides with the population it was computed over, so no figure is
    publishable without its denominator. Read-only: resolves through the
    archived read-fallback and writes nothing.
    """
    invalid = _validate_slug(args.slug)
    if invalid:
        return _error(args.slug, 'invalid_slug', invalid)
    status_doc = _read_status(args.slug, allow_archived=True)
    if not status_doc:
        return _error(
            args.slug, 'file_not_found', 'status.json not found in orchestrator store'
        )
    root = _epic_root(args.slug, allow_archived=True)
    rows = [row for row in status_doc.get('plans', []) if isinstance(row, dict)]
    specs = _spec_paths(root)
    matched: set[Path] = set()
    row_records: list[dict[str, Any]] = []
    rows_without_spec: list[dict[str, str]] = []
    for row in rows:
        plan_id = str(row.get('id', ''))
        row_status = str(row.get('status', ''))
        spec = next((path for path in specs if _spec_matches_row(path, plan_id)), None) if plan_id else None
        if spec is not None:
            matched.add(spec)
        else:
            rows_without_spec.append({'id': plan_id, 'status': row_status})
        row_records.append(
            {
                'id': plan_id,
                'status': row_status,
                'spec': spec.name if spec is not None else '',
                'excluded_reason': RUNNING_STATUS if row_status == RUNNING_STATUS else '',
            }
        )
    unreadable = [
        {'spec': spec.name, 'error': error}
        for spec, error in ((spec, _read_spec(spec)[1]) for spec in specs)
        if error
    ]
    tally = Counter(record['status'] for record in row_records)
    return {
        'status': 'success',
        'operation': 'corpus-enumerate',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'rows_total': len(rows),
        'rows_scanned': sum(1 for record in row_records if record['id']),
        'specs_total': len(specs),
        'specs_scanned': len(specs) - len(unreadable),
        'status_tally': [
            {'status': name, 'count': count} for name, count in sorted(tally.items())
        ],
        'rows': row_records,
        'rows_without_spec_count': len(rows_without_spec),
        'rows_without_spec': rows_without_spec,
        'specs_without_row_count': sum(1 for spec in specs if spec not in matched),
        'specs_without_row': [spec.name for spec in specs if spec not in matched],
        'unreadable_count': len(unreadable),
        'unreadable': unreadable,
    }


def cmd_corpus_verdicts(args: argparse.Namespace) -> dict[str, Any]:
    """Parse every re-grounding verdict bullet across the corpus. Read-only.

    The ONLY interpreter of the verdict line in the tree. One row per claim that
    carries a verdict bullet, with the five parsed keys plus the derived
    ``admits`` and ``stale`` booleans. A bullet that does not parse is returned
    with ``verdict: indeterminate``, ``admits: false`` and the offending line
    quoted verbatim — never dropped. ``specs_scanned`` and ``claims_scanned``
    ride the payload so a ``count: 0`` states which zero it is.
    """
    invalid = _validate_slug(args.slug)
    if invalid:
        return _error(args.slug, 'invalid_slug', invalid)
    root = _epic_root(args.slug, allow_archived=True)
    if not root.is_dir():
        return _error(args.slug, 'not_found', f'epic {args.slug!r} has no store tree')
    specs = _spec_paths(root)
    head = _current_head_sha()
    rows: list[dict[str, Any]] = []
    unreadable: list[dict[str, str]] = []
    specs_scanned = 0
    claims_scanned = 0
    for spec in specs:
        text, error = _read_spec(spec)
        if text is None:
            unreadable.append({'spec': spec.name, 'error': error})
            continue
        specs_scanned += 1
        lines = text.splitlines()
        claims = _parse_claims(lines)
        claims_scanned += len(claims)
        rows.extend(
            _verdict_row(spec.name, claim, lines[claim['verdict_line']].strip(), head)
            for claim in claims
            if claim['verdict_line'] >= 0
        )
    return {
        'status': 'success',
        'operation': 'corpus-verdicts',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'head_sha': head,
        'specs_total': len(specs),
        'specs_scanned': specs_scanned,
        'claims_scanned': claims_scanned,
        'count': len(rows),
        'blocking_count': sum(1 for row in rows if not row['admits']),
        'claims': rows,
        'unreadable_count': len(unreadable),
        'unreadable': unreadable,
    }


def _sibling_epic_roots(slug: str) -> list[Path]:
    """Enumerate the OTHER epics' store roots — active and archived alike.

    Mirrors the on-query store scan the read verbs document: both
    ``.plan/local/orchestrator/`` and ``.plan/local/archived-orchestrators/`` are
    walked, so an archived sibling stays visible to the duplication check. An
    epic present in both homes is yielded once.
    """
    roots: dict[str, Path] = {}
    bases = (_epic_root(slug).parent, get_archived_orchestrator_dir(slug).parent)
    for base in bases:
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if child.is_dir() and child.name != slug and child.name not in roots:
                roots[child.name] = child
    return [roots[name] for name in sorted(roots)]


def _spec_record(epic_slug: str, path: Path) -> dict[str, Any] | None:
    """Build one comparable record for a spec file, or ``None`` when unreadable."""
    text, _ = _read_spec(path)
    if text is None:
        return None
    return {
        'name': path.name,
        'pointers': _spec_pointers(text) | {_own_pointer(epic_slug, path.name)},
        'paths': _expected_surface_paths(text),
    }


def _live_plan_records() -> list[dict[str, Any]]:
    """Build one comparable record per ACTIVE plan — the cross-ledger direction.

    A single ledger structurally cannot see a duplicate held in another ledger,
    so the live plan set is enumerated through ``_cmd_sibling_collision``'s own
    active-plan walk and each plan contributes its ``source_id`` origin and its
    ``references.json`` ``affected_files`` surface.
    """
    records: list[dict[str, Any]] = []
    for plan_id, plan_dir in sorted(_iter_active_plan_dirs().items()):
        _, source_id = _read_request_source(plan_dir)
        pointers = _spec_pointers(source_id) if source_id else set()
        records.append(
            {
                'name': plan_id,
                'pointers': pointers,
                'paths': _read_affected_files(plan_dir),
            }
        )
    return records


def _collision_rows(
    spec: dict[str, Any], candidate: dict[str, Any], kind: str
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Score one spec/candidate pair on the two collision classes.

    The classes are ``_cmd_sibling_collision``'s, unchanged — a shared
    source-origin id (primary) and an exact normalized file-path overlap
    (secondary). No third similarity notion is introduced, and neither row is
    ever a bare score: each names the overlapping surface.
    """
    shared_origin = sorted(spec['pointers'] & candidate['pointers'])
    overlap = sorted(spec['paths'] & candidate['paths'])
    origin_row = (
        {
            'spec': spec['name'],
            'candidate_kind': kind,
            'candidate': candidate['name'],
            'shared_origin': _OVERLAP_JOIN.join(shared_origin),
        }
        if shared_origin
        else None
    )
    overlap_row = (
        {
            'spec': spec['name'],
            'candidate_kind': kind,
            'candidate': candidate['name'],
            'overlap_count': len(overlap),
            'overlapping_files': _OVERLAP_JOIN.join(overlap),
        }
        if overlap
        else None
    )
    return origin_row, overlap_row


def cmd_corpus_cross_check(args: argparse.Namespace) -> dict[str, Any]:
    """Cross-check this epic's specs against sibling epics and live plans.

    The arm a single ledger structurally cannot perform. Three populations are
    enumerated and each is NAMED in the payload — sibling epics (active and
    archived), the live plan set, and this epic's own corpus for the
    within-corpus direction — so a ``count: 0`` states which zero it is.

    Reports candidates and applies nothing: superseding is the workflow doc's
    inline, ledger-writing act, and no spec file is ever deleted.
    """
    invalid = _validate_slug(args.slug)
    if invalid:
        return _error(args.slug, 'invalid_slug', invalid)
    root = _epic_root(args.slug, allow_archived=True)
    if not root.is_dir():
        return _error(args.slug, 'not_found', f'epic {args.slug!r} has no store tree')
    own_paths = _spec_paths(root)
    own: list[dict[str, Any]] = []
    unreadable: list[dict[str, str]] = []
    for path in own_paths:
        record = _spec_record(args.slug, path)
        if record is None:
            unreadable.append({'spec': path.name, 'error': 'unreadable'})
        else:
            own.append(record)
    sibling_roots = _sibling_epic_roots(args.slug)
    candidates: list[tuple[str, dict[str, Any]]] = []
    for sibling_root in sibling_roots:
        for path in _spec_paths(sibling_root):
            record = _spec_record(sibling_root.name, path)
            if record is None:
                unreadable.append({'spec': f'{sibling_root.name}/{path.name}', 'error': 'unreadable'})
            else:
                candidates.append(('sibling_epic_spec', {**record, 'name': f'{sibling_root.name}/{path.name}'}))
    live = _live_plan_records()
    candidates.extend(('live_plan', record) for record in live)
    origin_matches: list[dict[str, Any]] = []
    overlap_matches: list[dict[str, Any]] = []
    for spec in own:
        pairs = [*candidates, *(('corpus_spec', other) for other in own if other['name'] != spec['name'])]
        for kind, candidate in pairs:
            origin_row, overlap_row = _collision_rows(spec, candidate, kind)
            if origin_row is not None:
                origin_matches.append(origin_row)
            if overlap_row is not None:
                overlap_matches.append(overlap_row)
    return {
        'status': 'success',
        'operation': 'corpus-cross-check',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'epics_scanned': len(sibling_roots),
        'plans_scanned': len(live),
        'specs_total': len(own_paths),
        'specs_scanned': len(own),
        'candidates_scanned': len(candidates),
        'source_origin_match_count': len(origin_matches),
        'source_origin_matches': origin_matches,
        'file_overlap_match_count': len(overlap_matches),
        'file_overlap_matches': overlap_matches,
        'collision_detected': bool(origin_matches or overlap_matches),
        'unreadable_count': len(unreadable),
        'unreadable': unreadable,
    }


def _validate_set_verdict_args(args: argparse.Namespace) -> dict[str, Any] | None:
    """Return the rejection envelope for an invalid ``set-verdict`` call, else ``None``.

    Every grammar rule is enforced HERE, at the sole emitter, so an invalid
    combination cannot reach disk. In particular ``rescoped`` must be ``n/a``
    whenever the verdict is not ``contradicted``: allowing ``no`` there would
    manufacture a blocking state out of a corroboration.
    """
    if args.verdict not in VERDICT_VALUES:
        return _error(
            args.slug,
            'invalid_verdict',
            f'--verdict must be one of {sorted(VERDICT_VALUES)}, got: {args.verdict}',
        )
    if args.rescoped not in RESCOPED_VALUES:
        return _error(
            args.slug,
            'invalid_rescoped',
            f'--rescoped must be one of {sorted(RESCOPED_VALUES)}, got: {args.rescoped}',
        )
    if args.verdict != CONTRADICTED and args.rescoped != NOT_APPLICABLE:
        return _error(
            args.slug,
            'invalid_rescoped_combination',
            f'--rescoped must be {NOT_APPLICABLE!r} when --verdict is not {CONTRADICTED!r}, '
            f'got: {args.rescoped}',
        )
    if not _CHECKED_AT_RE.match(args.checked_at):
        return _error(
            args.slug,
            'invalid_checked_at',
            f'--checked-at must be 7-40 lowercase hex characters, got: {args.checked_at}',
        )
    if not args.by.strip() or not args.evidence.strip():
        return _error(
            args.slug, 'wrong_parameters', '--by and --evidence must both be non-empty'
        )
    if VERDICT_SEPARATOR in args.by or VERDICT_SEPARATOR in args.checked_at:
        return _error(
            args.slug,
            'wrong_parameters',
            f'--by and --checked-at must not contain the {VERDICT_SEPARATOR!r} separator',
        )
    # The verdict is formatted as ONE line by ``_format_verdict_line`` and read
    # back from a single ``lines[claim['verdict_line']]`` — the grammar states
    # ``evidence`` runs "to end of line". An embedded break silently violates all
    # three: ``corpus verdicts`` would return a TRUNCATED ``evidence``, the
    # trailing fragment would become stray body text under ``## Claim Labels``,
    # and a re-stamp replacing only ``verdict_line`` would leave that fragment
    # behind — so the idempotent replace stops being idempotent. ``checked_at``
    # needs no check: ``_CHECKED_AT_RE`` already admits hex only.
    #
    # The guard is phrased as ``value.splitlines() != [value]`` so it asks the
    # SAME question the reader asks. ``cmd_corpus_verdicts`` splits the spec with
    # ``str.splitlines``, which breaks on considerably more than CR/LF — ``\v``,
    # ``\f``, ``\x1c``-``\x1e``, ``\x85``, ``\u2028``, ``\u2029``. Enumerating a
    # subset of those here would admit the rest past a guard whose whole purpose
    # is to keep the value on ONE of the reader's lines, so the guard defers to
    # the same splitter rather than maintaining a second, narrower list of what
    # counts as a break.
    if any(value.splitlines() != [value] for value in (args.by, args.evidence)):
        return _error(
            args.slug,
            'wrong_parameters',
            '--by and --evidence must not contain a line separator: the verdict is one line',
        )
    return None


def cmd_corpus_set_verdict(args: argparse.Namespace) -> dict[str, Any]:
    """Stamp one re-grounding verdict onto one claim. The group's single write.

    The ONLY formatter of the verdict line in the tree. Writes exactly one
    nested bullet under the addressed claim, REPLACING an existing one in place
    rather than appending a second — so re-stamping is idempotent by
    construction and a claim can never carry two verdicts.
    """
    invalid = _validate_slug(args.slug)
    if invalid:
        return _error(args.slug, 'invalid_slug', invalid)
    rejection = _validate_set_verdict_args(args)
    if rejection is not None:
        return rejection
    specs = _spec_paths(_epic_root(args.slug))
    spec = next((path for path in specs if _spec_matches_row(path, args.plan)), None)
    if spec is None:
        return _error(
            args.slug,
            'spec_not_found',
            f'no spec file for plan {args.plan!r} in {PLANS_SUBDIR}/',
            available_specs=[path.name for path in specs],
        )
    text, error = _read_spec(spec)
    if text is None:
        return _error(args.slug, error, f'spec {spec.name!r} could not be read', spec=spec.name)
    lines = text.splitlines()
    claims = _parse_claims(lines)
    if not 0 <= args.claim_index < len(claims):
        return _error(
            args.slug,
            'claim_index_out_of_range',
            f'--claim-index {args.claim_index} is outside the parsed claim list',
            spec=spec.name,
            claims_total=len(claims),
        )
    claim = claims[args.claim_index]
    body = _format_verdict_line(
        {
            'verdict': args.verdict,
            'checked_at': args.checked_at,
            'by': args.by,
            'rescoped': args.rescoped,
            'evidence': args.evidence,
        }
    )
    bullet = f'{claim["indent"]}  - {body}'
    replaced = claim['verdict_line'] >= 0
    previous_line = lines[claim['verdict_line']].strip() if replaced else ''
    if replaced:
        lines[claim['verdict_line']] = bullet
    else:
        lines.insert(int(claim['block_end']), bullet)
    spec.write_text('\n'.join(lines) + ('\n' if text.endswith('\n') else ''), encoding='utf-8')
    return {
        'status': 'success',
        'operation': 'corpus-set-verdict',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'plan': args.plan,
        'spec': spec.name,
        'claim_index': args.claim_index,
        'claims_total': len(claims),
        'replaced': replaced,
        'previous_line': previous_line,
        'line': bullet.strip(),
    }


def _signal(name: str, verdict: str, evidence: str, population: str) -> dict[str, Any]:
    """Build one restart-readiness signal row.

    The four-field shape is uniform across every arm on purpose: a verdict a
    reader cannot trace back to what was observed, and to how large the observed
    set was, is exactly the confident-signal shape this verb refuses to emit.
    Field values carry no commas, so each row stays one well-formed TOON record.
    """
    return {
        'signal': name,
        'verdict': verdict,
        'evidence': evidence,
        'population': population,
    }


def _readiness_floor(verdicts: list[str]) -> str:
    """The floor over the PARTICIPATING verdicts, under :data:`READINESS_ORDER`.

    An empty participating set yields ``indeterminate`` rather than ``ready``:
    nothing was observed, which is not the same as everything being fine.
    """
    if not verdicts:
        return READINESS_INDETERMINATE
    return min(verdicts, key=READINESS_ORDER.index)


def _phase_signal(status_doc: dict[str, Any]) -> dict[str, Any]:
    """The epic's own phase. Never ``not_ready`` — a phase is a fact, not a hazard."""
    phase = str(status_doc.get('phase', '')).strip()
    if not phase:
        return _signal(
            'phase',
            READINESS_INDETERMINATE,
            'status.json carries no readable phase',
            'status.json: 0 phase field read',
        )
    return _signal('phase', READY, f'phase={phase}', 'status.json: 1 phase field read')


def _running_plans_signal(status_doc: dict[str, Any]) -> dict[str, Any]:
    """In-flight plans. A restart mid-run loses the run's context, so it blocks."""
    raw = status_doc.get('plans')
    if not status_doc or not isinstance(raw, list):
        return _signal(
            'running_plans',
            READINESS_INDETERMINATE,
            'the plan queue could not be read',
            'plans[]: not readable',
        )
    rows = [row for row in raw if isinstance(row, dict)]
    population = f'plans[]: {len(rows)} row(s) scanned'
    running = sorted(
        str(row.get('id', '')) for row in rows if str(row.get('status', '')) == RUNNING_STATUS
    )
    if running:
        return _signal(
            'running_plans',
            NOT_READY,
            f'{len(running)} plan row(s) still running: {_OVERLAP_JOIN.join(running)}',
            population,
        )
    return _signal('running_plans', READY, 'no plan row is running', population)


#: The neutral outcome states of the bidirectional queue<->spec reconciliation
#: read. They are deliberately NOT the readiness vocabulary and NOT the invariant
#: vocabulary: :func:`_read_queue_spec_reconciliation` is shared by two callers
#: that grade the same facts into different words, so the shared seam names the
#: STATE and each caller owns the translation.
RECONCILE_NOT_ENUMERABLE = 'not_enumerable'
RECONCILE_UNREADABLE = 'unreadable'
RECONCILE_ORPHANED = 'orphaned'
RECONCILE_RECONCILED = 'reconciled'


def _read_queue_spec_reconciliation(slug: str) -> tuple[str, str, str]:
    """Read the bidirectional queue<->spec reconciliation as a neutral triple.

    The one branch body behind both :func:`_invariant_queue_spec` (the compact
    stage's invariant) and :func:`_corpus_signal` (the restart-check's readiness
    signal). Consumes ``corpus enumerate`` rather than re-deriving the corpus.

    The check that BITES: a count match alone passes with a mismatched pair, so
    both directions are read — no row without a spec AND no spec without a row.
    An unreadable spec OUTRANKS an orphan: a corpus that could not be fully read
    is unobservable, not reconciled-badly, so it yields
    :data:`RECONCILE_UNREADABLE` even when the readable part also reconciles
    badly.

    Returns:
        ``(state, evidence, population)``. ``state`` is one of
        :data:`RECONCILE_NOT_ENUMERABLE`, :data:`RECONCILE_UNREADABLE`,
        :data:`RECONCILE_ORPHANED` or :data:`RECONCILE_RECONCILED`; the other two
        elements are the caller-agnostic prose each caller passes through
        unchanged.
    """
    result = cmd_corpus_enumerate(argparse.Namespace(slug=slug))
    if result.get('status') != 'success':
        return (
            RECONCILE_NOT_ENUMERABLE,
            f'corpus enumerate could not run: {result.get("error", "unknown")}',
            'queue rows and spec files: not enumerable',
        )
    population = f'{result["rows_total"]} queue row(s) and {result["specs_total"]} spec file(s)'
    if result['unreadable_count']:
        return (
            RECONCILE_UNREADABLE,
            f'{result["unreadable_count"]} spec file(s) could not be read',
            population,
        )
    orphan_rows = result['rows_without_spec_count']
    orphan_specs = result['specs_without_row_count']
    if orphan_rows or orphan_specs:
        return (
            RECONCILE_ORPHANED,
            f'{orphan_rows} row(s) without a spec and {orphan_specs} spec(s) without a row',
            population,
        )
    return RECONCILE_RECONCILED, 'queue and specs reconcile both ways', population


def _corpus_signal(slug: str) -> dict[str, Any]:
    """Corpus reconciliation as a restart-readiness signal.

    Maps :func:`_read_queue_spec_reconciliation`'s neutral state into the
    readiness vocabulary: an unobservable corpus (not enumerable, or not fully
    readable) is ``indeterminate`` rather than ``not_ready`` — the *unobserved is
    not failed* rule the other readiness signals hold.
    """
    state, evidence, population = _read_queue_spec_reconciliation(slug)
    verdict = {
        RECONCILE_NOT_ENUMERABLE: READINESS_INDETERMINATE,
        RECONCILE_UNREADABLE: READINESS_INDETERMINATE,
        RECONCILE_ORPHANED: NOT_READY,
        RECONCILE_RECONCILED: READY,
    }[state]
    return _signal('corpus_reconciliation', verdict, evidence, population)


def _inbox_signal(slug: str) -> dict[str, Any]:
    """Inbox drain state, reusing :func:`inbox_counts`'s two-kinds-of-zero discriminator.

    An absent ``inbox/`` is *could not look*, not *nothing queued* — it renders
    as ``missing`` and yields ``indeterminate``, never a confident ``ready``.
    """
    counts = inbox_counts(_epic_root(slug, allow_archived=True) / INBOX_SUBDIR)
    if not counts.present:
        return _signal(
            'inbox',
            READINESS_INDETERMINATE,
            'inbox/ is absent so the queue could not be looked at',
            'inbox/: missing',
        )
    population = f'inbox/: {counts.queued} queued and {counts.archived} archived'
    if counts.queued:
        return _signal(
            'inbox', NOT_READY, f'{counts.queued} message(s) still queued', population
        )
    return _signal('inbox', READY, 'no queued message', population)


def _worktree_signal() -> dict[str, Any]:
    """Repository HEAD plus worktree cleanliness — one signal, since the sha
    without the cleanliness is not an observation a restart decision can use."""
    head, head_error = _git_read('head-sha')
    if head is None:
        return _signal('worktree', READINESS_INDETERMINATE, head_error, 'git: not readable')
    porcelain, porcelain_error = _git_read('worktree-status')
    if porcelain is None:
        return _signal(
            'worktree', READINESS_INDETERMINATE, porcelain_error, 'git: not readable'
        )
    changed = [line for line in porcelain.splitlines() if line.strip()]
    population = f'git status --porcelain: {len(changed)} changed path(s) at {head}'
    if changed:
        return _signal(
            'worktree', NOT_READY, f'{len(changed)} uncommitted path(s) at {head}', population
        )
    return _signal('worktree', READY, f'clean worktree at {head}', population)


def _registry_parity_signal() -> dict[str, Any]:
    """The one arm whose surface this component does not own.

    Reported in a three-part unowned-surface shape — the field is present, its
    value is ``not_available``, and it names the spec that owns the surface — so
    a real signal this component does not own is disclosed rather than dropped.
    Being outside :data:`READINESS_ORDER`, it never reaches the floor.
    """
    return _signal(
        'registry_parity',
        NOT_AVAILABLE,
        f'this component observes no parity surface; it is owned by {REGISTRY_PARITY_OWNER}',
        'not_applicable — the surface belongs to another component',
    )


def cmd_cleanup_restart_check(args: argparse.Namespace) -> dict[str, Any]:
    """Report whether the session is safe to restart. Read-only.

    One row per signal, each carrying its own verdict, its own evidence, and the
    population it was derived from, plus the sample instant. The overall verdict
    is the floor over the rows whose verdict is a member of
    :data:`READINESS_ORDER`; a ``not_available`` arm is excluded, so an unowned
    surface cannot veto a verdict this component CAN reach. Every unreadable or
    unobservable arm resolves to ``indeterminate`` and never to ``not_ready``.
    """
    invalid = _validate_slug(args.slug)
    if invalid:
        return _error(args.slug, 'invalid_slug', invalid)
    root = _epic_root(args.slug, allow_archived=True)
    if not root.is_dir():
        return _error(args.slug, 'not_found', f'epic {args.slug!r} has no store tree')
    status_doc = _read_status(args.slug, allow_archived=True)
    signals = [
        _phase_signal(status_doc),
        _running_plans_signal(status_doc),
        _corpus_signal(args.slug),
        _inbox_signal(args.slug),
        _worktree_signal(),
        _registry_parity_signal(),
    ]
    scored = [row['verdict'] for row in signals if row['verdict'] in READINESS_ORDER]
    return {
        'status': 'success',
        'operation': 'cleanup-restart-check',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'sampled_at': now_utc_iso(),
        'verdict': _readiness_floor(scored),
        'signals_total': len(signals),
        'signals_scored': len(scored),
        'signals': signals,
    }


def _queue_cell(value: str) -> str:
    """Escape one value for a markdown table cell.

    A bare pipe would open a spurious column and a newline would end the row, so
    both are neutralised — the pipe escaped, the newline folded to a space. File
    paths carry neither, so this only ever fires on a pathological surface entry.
    """
    return value.replace('|', r'\|').replace('\n', ' ').strip()


def _row_surface(spec: Path | None) -> str:
    """Resolve one row's Surface cell from its spec's ``## Expected Surface``.

    The Surface column is derivable — from the FILESYSTEM, not ``status.json`` —
    so it is regenerated like the rest. Each *which zero is this* case is a named
    marker rather than an empty cell: a missing spec, an unreadable one, and a
    spec with no declared surface are told apart, never collapsed to blank.
    """
    if spec is None:
        return '(spec missing)'
    text, _ = _read_spec(spec)
    if text is None:
        return '(spec unreadable)'
    paths = sorted(_expected_surface_paths(text))
    if not paths:
        return '(no expected surface)'
    return _queue_cell(_SURFACE_JOIN.join(paths))


def _build_ordered_queue(status_doc: dict[str, Any], root: Path) -> str:
    """Render the LIVE Ordered Queue table, derived from status.json + specs.

    Only non-terminal rows appear: a shipped/landed row belongs in its landing
    record, not the live queue (:data:`LIVE_QUEUE_EXCLUDED_STATUSES`). The five
    columns are all derivable — order, plan id, workstream and status from
    ``status.json``; the surface from each row's spec. Per-row narrative (a
    sequencing caveat, a park reason) is NOT here — it lives in the annotation
    zone outside the markers, which regeneration never touches.
    """
    header = '| # | Plan | Workstream | Status | Surface (expected) |'
    divider = '|---|------|------------|--------|--------------------|'
    lines = [header, divider]
    rows = [row for row in status_doc.get('plans', []) if isinstance(row, dict)]
    live = [row for row in rows if str(row.get('status', '')) not in LIVE_QUEUE_EXCLUDED_STATUSES]
    if not live:
        lines.append('| — | (empty) | — | — | — |')
        return '\n'.join(lines)
    specs = _spec_paths(root)
    for position, row in enumerate(live, start=1):
        plan_id = str(row.get('id', ''))
        spec = next((path for path in specs if plan_id and _spec_matches_row(path, plan_id)), None)
        plan_cell = _queue_cell(spec.stem if spec is not None else (plan_id or '?'))
        workstream = _queue_cell(str(row.get('workstream', '') or '?'))
        status_cell = _queue_cell(str(row.get('status', '') or '?'))
        surface = _row_surface(spec)
        lines.append(f'| {position} | {plan_cell} | {workstream} | {status_cell} | {surface} |')
    return '\n'.join(lines)


def _marker_indices(lines: list[str], name: str) -> tuple[int, int]:
    """Return the ``(begin, end)`` line indices of one GENERATED block's markers.

    ``(-1, -1)`` when either marker is absent, or the end precedes the begin. The
    match is the WHOLE stripped line equalling the marker, so a marker quoted
    mid-sentence is never mistaken for the real one.
    """
    begin = _begin_marker(name)
    end = _end_marker(name)
    begin_idx = next((index for index, line in enumerate(lines) if line.strip() == begin), -1)
    if begin_idx < 0:
        return (-1, -1)
    end_idx = next(
        (index for index in range(begin_idx + 1, len(lines)) if lines[index].strip() == end), -1
    )
    return (begin_idx, end_idx)


def _replace_block(text: str, name: str, new_body: str) -> tuple[str, str, int, int, str]:
    """Replace one GENERATED block's body in place, reporting the outcome.

    Returns ``(new_text, outcome, lines_before, lines_after, replaced_body)``.
    ``outcome`` is one of ``regenerated`` (the body changed), ``unchanged``
    (byte-identical, so a second run is a no-op), or ``markers_absent`` (the
    block's markers are not in this epic.md — reported, never fabricated, because
    inserting markers into a hand-authored document is a structural edit this
    stage has no mandate for). Splitting on ``\\n`` keeps a trailing newline as a
    trailing element, so the re-joined text is byte-identical when nothing
    changed.

    ``replaced_body`` is the PRE-WRITE between-marker text, and it is non-empty
    only for ``regenerated``. It exists because a line-count delta does not say
    WHAT was overwritten: a hand-written note someone left inside a generated
    block is legitimately replaced on the first pass (the region is the
    generator's), and reporting only ``5 -> 7 lines`` leaves the operator unable
    to tell which bytes went. The other two outcomes overwrite nothing, so both
    report ``''``.
    """
    lines = text.split('\n')
    begin_idx, end_idx = _marker_indices(lines, name)
    if begin_idx < 0 or end_idx < 0:
        return text, 'markers_absent', 0, 0, ''
    before = lines[begin_idx + 1 : end_idx]
    new_lines = new_body.split('\n')
    if before == new_lines:
        return text, 'unchanged', len(before), len(new_lines), ''
    updated = lines[: begin_idx + 1] + new_lines + lines[end_idx:]
    return '\n'.join(updated), 'regenerated', len(before), len(new_lines), '\n'.join(before)


def _invariant(name: str, verdict: str, evidence: str, population: str) -> dict[str, Any]:
    """Build one compact-stage invariant row, in the restart-check signal shape.

    ``verdict`` is ``ok`` | ``violated`` | ``indeterminate``. An unobservable
    check resolves to ``indeterminate`` and never to ``violated`` — the same
    *unobserved is not failed* rule the readiness signals hold.
    """
    return {'invariant': name, 'verdict': verdict, 'evidence': evidence, 'population': population}


def _invariant_queue_spec(slug: str) -> dict[str, Any]:
    """Bidirectional queue <-> spec reconciliation as a compact-stage invariant.

    Maps :func:`_read_queue_spec_reconciliation`'s neutral state into the
    invariant vocabulary: an unobservable corpus (not enumerable, or not fully
    readable) is ``indeterminate`` rather than ``violated`` — a corpus that could
    not be fully read is unobserved, not reconciled-badly.
    """
    state, evidence, population = _read_queue_spec_reconciliation(slug)
    verdict = {
        RECONCILE_NOT_ENUMERABLE: 'indeterminate',
        RECONCILE_UNREADABLE: 'indeterminate',
        RECONCILE_ORPHANED: 'violated',
        RECONCILE_RECONCILED: 'ok',
    }[state]
    return _invariant('queue_spec_bidirectional', verdict, evidence, population)


def _invariant_no_terminal_in_live_queue(queue_body: str) -> dict[str, Any]:
    """Assert the RENDERED live queue carries no terminal row.

    A post-condition over the generator's own output rather than over its inputs:
    the renderer excludes terminal rows by construction, and this reads the
    emitted Status column back to prove none leaked. Data rows are the ones whose
    first cell is the position integer.

    It checks the freshly-BUILT body, not the on-disk table. When the
    ``ordered-queue`` markers are absent, that body is never written, so this
    verdict speaks to what the renderer WOULD emit — the block's actual absence
    is surfaced separately as that block's ``markers_absent`` outcome, so the two
    signals together are not misleading.
    """
    statuses: list[str] = []
    for line in queue_body.split('\n'):
        cells = [cell.strip() for cell in line.split('|')]
        if len(cells) >= 7 and cells[1].isdigit():
            statuses.append(cells[4])
    population = f'{len(statuses)} live queue row(s) rendered'
    leaked = sorted({status for status in statuses if status in LIVE_QUEUE_EXCLUDED_STATUSES})
    if leaked:
        return _invariant(
            'no_terminal_in_live_queue',
            'violated',
            f'terminal status leaked into the live queue: {", ".join(leaked)}',
            population,
        )
    return _invariant(
        'no_terminal_in_live_queue', 'ok', 'no shipped/landed row in the live queue', population
    )


def _settled_headings(text: str) -> set[str]:
    """Extract the heading texts of ``settled.md``, fence-aware.

    A relocation pointer names its destination heading in double quotes; this is
    the set that pointer is resolved against.
    """
    lines = text.split('\n')
    fenced = _fenced_mask(lines)
    return {
        line.strip().strip('#').strip()
        for index, line in enumerate(lines)
        if not fenced[index] and _HEADING_RE.match(line)
    }


def _invariant_pointers_reachable(epic_text: str, root: Path) -> dict[str, Any]:
    """Assert every settled-narrative relocation pointer RESOLVES.

    A reader following the old path must land on the content, not on absence, so
    each pointer's named heading must exist in ``settled.md``. No pointer is the
    common case (nothing relocated yet) and resolves to ``ok``; a pointer whose
    target is missing is ``violated``; an unreadable ``settled.md`` is
    ``indeterminate``.
    """
    wanted = [match.group('heading') for match in _RELOCATION_POINTER_RE.finditer(epic_text)]
    population = f'{len(wanted)} relocation pointer(s) in epic.md'
    if not wanted:
        return _invariant(
            'relocated_pointer_reachable',
            'ok',
            'no settled-narrative relocation pointer to resolve',
            population,
        )
    settled_path = root / FILE_SETTLED
    if not settled_path.is_file():
        return _invariant(
            'relocated_pointer_reachable',
            'violated',
            f'{len(wanted)} pointer(s) but settled.md is absent',
            population,
        )
    settled_text, _ = _read_spec(settled_path)
    if settled_text is None:
        return _invariant(
            'relocated_pointer_reachable', 'indeterminate', 'settled.md could not be read', population
        )
    present = _settled_headings(settled_text)
    unreachable = sorted({heading for heading in wanted if heading not in present})
    if unreachable:
        return _invariant(
            'relocated_pointer_reachable',
            'violated',
            f'{len(unreachable)} pointer(s) resolve to no settled.md heading: {", ".join(unreachable)}',
            population,
        )
    return _invariant(
        'relocated_pointer_reachable',
        'ok',
        'every relocation pointer resolves to a settled.md heading',
        population,
    )


#: A top-level (``##``) section heading, used to enumerate the narrative
#: sections the compact stage abstains from. ``##`` followed by ``#`` is a
#: level-3 heading and does not match, so annotation subsections are folded into
#: their parent rather than listed apart.
_SECTION_HEADING_RE = re.compile(r'^ {0,3}##[ \t]+(?P<title>.+?)[ \t]*#*[ \t]*$')


def _abstained_sections(text: str, unreachable_blocks: Collection[str] = ()) -> list[dict[str, str]]:
    """Name every ``##`` section the stage did not rewrite, and WHY it did not.

    A silent compaction is indistinguishable from a lossy one, so the report
    names not only what changed but what was left alone. A section is listed
    unless it CONTAINS a GENERATED marker (which makes it a regenerated surface),
    and each listed section carries the treatment that says which of two very
    different things happened to it:

    - :data:`TREATMENT_PRESERVED` — a deliberate abstention. The section carries
      no derivable surface, so leaving it verbatim is the correct outcome.
    - :data:`TREATMENT_UNREACHABLE` — a blind spot. The section OWNS a block in
      ``unreachable_blocks`` (one whose :func:`_replace_block` outcome was
      ``markers_absent``), so the stage could not see the derivable surface and
      regenerated nothing there.

    That distinction is the whole point of the list — "nothing needed touching"
    versus "the stage could not see it" — and emitting the first for the second
    claims a choice the stage never made. On an ``epic.md`` scaffolded before the
    ``ordered-queue`` marker pair shipped, the second case is the ordinary output,
    not an edge case.

    Args:
        text: The ``epic.md`` content to enumerate, read BEFORE any rewrite.
        unreachable_blocks: Block names whose markers were absent this pass.
            Mapped onto their owning heading via
            :data:`GENERATED_BLOCK_OWNING_SECTION`; a name with no mapping, or a
            mapped heading absent from ``text``, contributes no row.
    """
    unreachable_titles = {
        GENERATED_BLOCK_OWNING_SECTION[name].casefold()
        for name in unreachable_blocks
        if name in GENERATED_BLOCK_OWNING_SECTION
    }
    lines = text.split('\n')
    fenced = _fenced_mask(lines)
    begins = {_begin_marker(name) for name in GENERATED_BLOCKS}
    sections: list[tuple[str, int]] = []
    for index, line in enumerate(lines):
        if not fenced[index] and (match := _SECTION_HEADING_RE.match(line)):
            sections.append((match.group('title').strip(), index))
    abstained: list[dict[str, str]] = []
    for order, (title, start) in enumerate(sections):
        end = sections[order + 1][1] if order + 1 < len(sections) else len(lines)
        has_generated = any(line.strip() in begins for line in lines[start:end])
        if has_generated:
            continue
        treatment = (
            TREATMENT_UNREACHABLE
            if title.casefold() in unreachable_titles
            else TREATMENT_PRESERVED
        )
        abstained.append({'section': title, 'treatment': treatment})
    return abstained


def cmd_compact(args: argparse.Namespace) -> dict[str, Any]:
    """Compact the epic ledger: regenerate the derivable surfaces, verify, report.

    The ledger-compaction stage ``workflow/cleanup.md`` Phase B calls. It
    regenerates every derivable GENERATED block of ``epic.md`` IN PLACE — the
    START-HERE resume summary and the Ordered Queue table — from ``status.json``
    and the staged specs, leaving every byte OUTSIDE the markers untouched. That
    boundary is the safety property: a retraction, a refutation, a
    do-not-re-derive note, or the operator-confirmed running note all sit in
    narrative and survive a pass verbatim, because the stage never reads them as
    regenerable. The narrative-versus-settled RELOCATION judgement is NOT here —
    it stays with the orchestrator; this stage only VERIFIES that whatever was
    relocated is reachable from its pointer.

    Refuses a closed epic (``refused_closed``): that tree is the frozen audit
    record, and compaction is a live-epic operation only. Resolves the store
    strictly (never the archived read-fallback), so an archived tree is never
    mutated at the active path.

    The report names every mutation and every abstention: ``regenerated[]`` (per
    block: its outcome, its line counts, and — for a ``regenerated`` block —
    ``replaced_body``, the pre-write between-marker text, so a first pass over an
    already-annotated ledger NAMES the content it overwrote rather than reporting
    only a line-count delta), ``invariants[]`` (bidirectional queue
    reconciliation, no-terminal-in-live-queue, and pointer reachability, each
    with its verdict, evidence, and population), and ``abstained[]`` (every ``##``
    section not rewritten, each carrying the treatment that says WHY).

    The two treatments are counted apart, because they mean opposite things:
    ``abstained_count`` counts :data:`TREATMENT_PRESERVED` — deliberate
    abstentions over sections carrying no derivable surface — while
    ``unreachable_count`` counts :data:`TREATMENT_UNREACHABLE`, sections whose
    derivable surface the stage COULD NOT REACH because the block's markers are
    absent. A blind spot reported as a choice would be the misleading signal this
    split exists to remove. Idempotent: a second run finds every block
    ``unchanged`` and writes nothing.
    """
    invalid = _validate_slug(args.slug)
    if invalid:
        return _error(args.slug, 'invalid_slug', invalid)
    root = _epic_root(args.slug)
    if not root.is_dir():
        return _error(args.slug, 'not_found', f'epic {args.slug!r} has no active store tree')
    epic_path = root / FILE_EPIC
    if not epic_path.is_file():
        return _error(args.slug, 'file_not_found', 'epic.md not found in orchestrator store')
    status_doc = _read_status(args.slug)
    if not status_doc:
        return _error(args.slug, 'file_not_found', 'status.json not found in orchestrator store')
    phase = str(status_doc.get('phase', '')).strip()
    if phase == CLOSED_PHASE:
        return _error(
            args.slug,
            'refused_closed',
            f'epic {args.slug} is phase=closed; compaction is a live-epic operation only — '
            'the frozen record is never mutated',
            phase=phase,
        )
    counts = inbox_counts(root / INBOX_SUBDIR)
    original = epic_path.read_text(encoding='utf-8')
    bodies = {
        'resume-summary': _build_summary(status_doc, counts),
        'ordered-queue': _build_ordered_queue(status_doc, root),
    }
    text = original
    regenerated: list[dict[str, Any]] = []
    for name in GENERATED_BLOCKS:
        text, outcome, lines_before, lines_after, replaced_body = _replace_block(
            text, name, bodies[name]
        )
        regenerated.append(
            {
                'surface': name,
                'outcome': outcome,
                'lines_before': lines_before,
                'lines_after': lines_after,
                'replaced_body': replaced_body,
            }
        )
    changed = text != original
    if changed:
        epic_path.write_text(text, encoding='utf-8')
    invariants = [
        _invariant_queue_spec(args.slug),
        _invariant_no_terminal_in_live_queue(bodies['ordered-queue']),
        _invariant_pointers_reachable(text, root),
    ]
    unreachable_blocks = [
        row['surface'] for row in regenerated if row['outcome'] == 'markers_absent'
    ]
    abstained = _abstained_sections(original, unreachable_blocks)
    return {
        'status': 'success',
        'operation': 'compact',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'relocation_target': FILE_SETTLED,
        'epic_changed': changed,
        'regenerated_count': sum(1 for row in regenerated if row['outcome'] == 'regenerated'),
        'regenerated': regenerated,
        'invariants': invariants,
        'abstained_count': sum(
            1 for row in abstained if row['treatment'] == TREATMENT_PRESERVED
        ),
        'unreachable_count': sum(
            1 for row in abstained if row['treatment'] == TREATMENT_UNREACHABLE
        ),
        'abstained': abstained,
    }


def _add_slug_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--slug', required=True, help='Epic slug (kebab-case)')


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='orchestrator',
        description=(
            'Thin scaffolding for plan-orchestrator epics: scaffold the '
            'epic tree, read/transition/stamp the plan queue, generate the '
            'START-HERE resume summary, archive a closed epic, reconcile the '
            'staged spec corpus and its re-grounding verdicts, report the '
            'restart-readiness verdict, and drive the plan-writable inbox '
            'OUTBOX and its drain.'
        ),
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    scaffold = subparsers.add_parser(
        'scaffold',
        help='Create the .plan/local/orchestrator/{slug}/ directory tree (idempotent).',
        allow_abbrev=False,
    )
    _add_slug_arg(scaffold)
    scaffold.set_defaults(handler=cmd_scaffold)

    queue = subparsers.add_parser(
        'queue',
        help=(
            'Read the plan queue from status.json, transition one plan status, '
            'or set one plan row field.'
        ),
        allow_abbrev=False,
    )
    _add_slug_arg(queue)
    queue.add_argument(
        '--transition',
        default=None,
        metavar='PLAN-NN',
        help='Plan id to transition (requires --status).',
    )
    queue.add_argument(
        '--status',
        default=None,
        metavar='STATUS',
        help='New status value for the plan named by --transition.',
    )
    queue.add_argument(
        '--set-row',
        default=None,
        metavar='PLAN-NN',
        help=(
            'Plan id whose row field to set (requires --field and --value; '
            'mutually exclusive with --transition/--status).'
        ),
    )
    queue.add_argument(
        '--field',
        default=None,
        metavar='FIELD',
        help=f'Row field to set: one of {sorted(PLAN_ROW_FIELDS)} (requires --set-row).',
    )
    queue.add_argument(
        '--value',
        default=None,
        metavar='VALUE',
        help='New value for the field named by --field (requires --set-row).',
    )
    queue.set_defaults(handler=cmd_queue)

    resume = subparsers.add_parser(
        'resume-summary',
        help='Generate the two derivable epic.md blocks (START-HERE + Ordered Queue) from status.json.',
        allow_abbrev=False,
    )
    _add_slug_arg(resume)
    resume.set_defaults(handler=cmd_resume_summary)

    archive = subparsers.add_parser(
        'archive',
        help='Relocate a closed epic tree to archived-orchestrators/{slug}/ (post-close, mechanical).',
        allow_abbrev=False,
    )
    _add_slug_arg(archive)
    archive.set_defaults(handler=cmd_archive)

    compact = subparsers.add_parser(
        'compact',
        help=(
            'Regenerate the derivable epic.md surfaces in place, verify the '
            'invariants, and report (live-epic only; refuses a closed epic).'
        ),
        allow_abbrev=False,
    )
    _add_slug_arg(compact)
    compact.set_defaults(handler=cmd_compact)

    _add_corpus_group(subparsers)
    _add_cleanup_group(subparsers)
    _add_inbox_group(subparsers)

    return parser


def _add_corpus_group(subparsers: Any) -> None:
    """Register the ``corpus`` verb group.

    Sub-verbs: ``enumerate``, ``cross-check``, ``verdicts``, ``set-verdict``.
    The first three are read-only; ``set-verdict`` is the group's single write
    action, and the only surface in the tree that formats a ``verdict:`` line.
    """
    corpus = subparsers.add_parser(
        'corpus',
        help=(
            "Epic spec corpus: reconcile the queue against the plans/ specs in both "
            'directions, and read or stamp the re-grounding verdict field.'
        ),
        allow_abbrev=False,
    )
    actions = corpus.add_subparsers(dest='corpus_action', required=True)

    enumerate_specs = actions.add_parser(
        'enumerate',
        help=(
            'Reconcile status.json plans[] against plans/PLAN-*.md in both '
            'directions, every count carrying its population (read-only).'
        ),
        allow_abbrev=False,
    )
    _add_slug_arg(enumerate_specs)
    enumerate_specs.set_defaults(handler=cmd_corpus_enumerate)

    cross_check = actions.add_parser(
        'cross-check',
        help=(
            "Cross-check this epic's specs against sibling epics and live plans "
            'for duplicate work, on the two sibling-collision-check classes (read-only).'
        ),
        allow_abbrev=False,
    )
    _add_slug_arg(cross_check)
    cross_check.set_defaults(handler=cmd_corpus_cross_check)

    verdicts = actions.add_parser(
        'verdicts',
        help='Parse every re-grounding verdict bullet across the corpus (read-only).',
        allow_abbrev=False,
    )
    _add_slug_arg(verdicts)
    verdicts.set_defaults(handler=cmd_corpus_verdicts)

    set_verdict = actions.add_parser(
        'set-verdict',
        help='Stamp one re-grounding verdict onto one claim (replaces in place).',
        allow_abbrev=False,
    )
    _add_slug_arg(set_verdict)
    set_verdict.add_argument(
        '--plan', required=True, metavar='PLAN-NN', help='Plan id whose spec carries the claim.'
    )
    set_verdict.add_argument(
        '--claim-index',
        required=True,
        type=int,
        metavar='N',
        help='Zero-based index of the claim bullet within the spec\'s ## Claim Labels section.',
    )
    set_verdict.add_argument(
        '--verdict', required=True, help=f'One of {sorted(VERDICT_VALUES)}.'
    )
    set_verdict.add_argument(
        '--checked-at', required=True, metavar='SHA', help='The 7-40 hex HEAD sha the check ran against.'
    )
    set_verdict.add_argument(
        '--by', required=True, metavar='PRODUCER', help='Producer that wrote it, as {slug}/{verb}.'
    )
    set_verdict.add_argument(
        '--rescoped',
        required=True,
        help=f'One of {sorted(RESCOPED_VALUES)}; must be {NOT_APPLICABLE!r} unless the verdict is {CONTRADICTED!r}.',
    )
    set_verdict.add_argument(
        '--evidence', required=True, metavar='TEXT', help='Non-empty evidence text (may contain the separator).'
    )
    set_verdict.set_defaults(handler=cmd_corpus_set_verdict)


def _add_cleanup_group(subparsers: Any) -> None:
    """Register the ``cleanup`` verb group.

    Sub-verb: ``restart-check``, read-only. The cleanup verb's judgement half
    lives in ``workflow/cleanup.md``; this group carries only the deterministic
    readiness enumeration that doc calls.
    """
    cleanup = subparsers.add_parser(
        'cleanup',
        help='Cleanup-stage deterministic seams: report whether the session is safe to restart.',
        allow_abbrev=False,
    )
    actions = cleanup.add_subparsers(dest='cleanup_action', required=True)

    restart_check = actions.add_parser(
        'restart-check',
        help=(
            'Report one readiness verdict per signal — each with its evidence and '
            'its population — plus the floor over them (read-only).'
        ),
        allow_abbrev=False,
    )
    _add_slug_arg(restart_check)
    restart_check.set_defaults(handler=cmd_cleanup_restart_check)


def _add_inbox_group(subparsers: Any) -> None:
    """Register the ``inbox`` verb group.

    Sub-verbs, in registration order: ``write``, ``amend``, ``supersede``,
    ``close-stream``, ``validate``, ``list``, ``archive``, ``migrate-archive``,
    ``detect``, ``landing-check``. The handlers live in
    :mod:`_orchestrator_inbox`; this function only wires argv to them. Note what the surface deliberately does NOT expose: no output
    path, no sequence number, and no inbox directory — the write and correction
    targets are derived from ``--slug`` plus ``--sender-id`` / a bare
    ``--message`` filename alone, which is what makes the ledger write-boundary
    carve-out enforced by construction. ``archive --as-name`` does not widen
    that carve-out: it is still a bare filename joined onto
    ``inbox/archive/{sender}/``, never a caller-supplied path, and it is
    additionally sender-constrained, so the archived name's sender provenance is
    preserved.
    """
    inbox = subparsers.add_parser(
        'inbox',
        help=(
            'Epic inbox OUTBOX and drain: append, correct (amend/supersede), '
            'end a sender stream, validate, list, archive or fold the archive '
            "per sender, detect a plan's orchestration context, or check a "
            "landing's required facts."
        ),
        allow_abbrev=False,
    )
    actions = inbox.add_subparsers(dest='inbox_action', required=True)

    write = actions.add_parser(
        'write',
        help='Append one inbox/{sender_id}-{NNN}.md message to the epic.',
        allow_abbrev=False,
    )
    _add_slug_arg(write)
    write.add_argument(
        '--sender-type',
        required=True,
        help=f'Sender class: one of {sorted(SENDER_TYPES)}.',
    )
    write.add_argument(
        '--sender-id',
        required=True,
        help="Sender identifier (a plan id); also the message filename's sender segment.",
    )
    write.add_argument(
        '--kind', required=True, help=f'Payload kind: one of {sorted(KINDS)}.'
    )
    write.add_argument(
        '--payload-file',
        required=True,
        help='Path to the staged markdown payload body (never inline text).',
    )
    write.add_argument(
        '--target-plan',
        required=False,
        default=None,
        help=(
            'Optional plan id the message is aimed at. When it names a plan that '
            'is currently RUNNING, the write is REFUSED as '
            'undeliverable_to_running_plan: the inbox is drained between plans, '
            'so a running plan never reads it. A non-running target does not '
            'block the write. This flag makes the undeliverability visible; it '
            'does NOT deliver a message to a plan.'
        ),
    )
    write.set_defaults(handler=cmd_inbox_write)

    amend = actions.add_parser(
        'amend',
        help='Correct a filed message body in place, preserving created, '
        'stamping amended + a monotonic revision.',
        allow_abbrev=False,
    )
    _add_slug_arg(amend)
    amend.add_argument(
        '--message',
        required=True,
        metavar='NAME',
        help='Bare message filename inside the epic inbox/ directory.',
    )
    amend.add_argument(
        '--payload-file',
        required=True,
        help='Path to the staged markdown correction body (never inline text).',
    )
    amend.set_defaults(handler=cmd_inbox_amend)

    supersede = actions.add_parser(
        'supersede',
        help='Retire a filed message in favour of a named successor '
        '(tombstone-style: stays resolvable, stops presenting as live).',
        allow_abbrev=False,
    )
    _add_slug_arg(supersede)
    supersede.add_argument(
        '--message',
        required=True,
        metavar='NAME',
        help='Bare message filename to retire, inside the epic inbox/ directory.',
    )
    supersede.add_argument(
        '--by',
        required=True,
        metavar='NAME',
        help="Bare successor message filename; must resolve in the epic inbox/ "
        'or inbox/archive/.',
    )
    supersede.set_defaults(handler=cmd_inbox_supersede)

    close_stream = actions.add_parser(
        'close-stream',
        help="File a terminal lifecycle=stream-end marker declaring the sender's "
        'stream ended.',
        allow_abbrev=False,
    )
    _add_slug_arg(close_stream)
    close_stream.add_argument(
        '--sender-type',
        default='plan',
        help=f'Sender class: one of {sorted(SENDER_TYPES)} (default: plan).',
    )
    close_stream.add_argument(
        '--sender-id',
        required=True,
        help="Sender identifier whose stream is ending; the marker's sender segment.",
    )
    close_stream.add_argument(
        '--reason',
        default=None,
        help='Optional closing note; a default sentence is used when omitted.',
    )
    close_stream.set_defaults(handler=cmd_inbox_close_stream)

    validate = actions.add_parser(
        'validate',
        help='Validate one existing inbox message against the envelope schema.',
        allow_abbrev=False,
    )
    _add_slug_arg(validate)
    validate.add_argument(
        '--message',
        required=True,
        metavar='NAME',
        help='Bare message filename inside the epic inbox/ directory.',
    )
    validate.set_defaults(handler=cmd_inbox_validate)

    list_messages = actions.add_parser(
        'list',
        help='Enumerate the queued inbox messages with their validation verdicts.',
        allow_abbrev=False,
    )
    _add_slug_arg(list_messages)
    list_messages.set_defaults(handler=cmd_inbox_list)

    archive_message = actions.add_parser(
        'archive',
        help='Retire one consumed message to inbox/archive/ (idempotent).',
        allow_abbrev=False,
    )
    _add_slug_arg(archive_message)
    archive_message.add_argument(
        '--message',
        required=True,
        metavar='NAME',
        help='Bare message filename inside the epic inbox/ directory.',
    )
    archive_message.add_argument(
        '--as-name',
        default=None,
        metavar='NAME',
        help=(
            'Recovery override for the archived destination filename, for a '
            'message stranded by a pre-fix sequence collision. Must still '
            "match {sender_id}-* for the source message's sender, or the "
            'call is refused with as_name_sender_mismatch.'
        ),
    )
    archive_message.set_defaults(handler=cmd_inbox_archive)

    migrate_archive = actions.add_parser(
        'migrate-archive',
        help='Fold a flat inbox/archive/ into per-sender subdirectories, '
        'reporting the count moved per sender.',
        allow_abbrev=False,
    )
    _add_slug_arg(migrate_archive)
    migrate_archive.set_defaults(handler=cmd_inbox_migrate_archive)

    detect = actions.add_parser(
        'detect',
        help="Classify a plan's request source_id as an orchestrated plan pointer.",
        allow_abbrev=False,
    )
    detect.add_argument(
        '--source-id',
        required=True,
        help="The request.md source_id value recorded by phase-1-init.",
    )
    detect.set_defaults(handler=cmd_inbox_detect)

    landing_check = actions.add_parser(
        'landing-check',
        help='Report whether a landing message carries the required '
        'machine-readable facts (the drain-completeness check).',
        allow_abbrev=False,
    )
    _add_slug_arg(landing_check)
    landing_check.add_argument(
        '--message',
        required=True,
        metavar='NAME',
        help='Bare landing message filename inside the epic inbox/ directory.',
    )
    landing_check.set_defaults(handler=cmd_inbox_landing_check)


@safe_main
def main() -> int:
    args = _build_arg_parser().parse_args()
    output_toon(args.handler(args))
    return 0


if __name__ == '__main__':
    main()

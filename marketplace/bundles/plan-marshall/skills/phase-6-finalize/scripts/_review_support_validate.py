#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Verdict grading for ``review_support validate`` — internal module, not an entry point.

Checks a review author's verdict against the return schema documented in
``review_support.py`` and grades every finding on the blocking line stated in
``phase-6-finalize/standards/review-rubric.md`` (§ 2 functional, § 3 code,
§ 4 evidence, § 5 citation forms). The rubric is the single statement of those
rules; this module applies them and restates none of the reasoning.

Imported as ``from _review_support_validate import ...`` by ``review_support.py``.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from _criteria_snapshot import SPEC_MISSING

KIND_FUNCTIONAL = 'functional'
KIND_CODE = 'code'

FUNCTIONAL_VERDICTS = ('met', 'met_with_residuals', 'not_met', 'superseded')
#: The verdicts that claim the deliverable's value is delivered, so must evidence a criterion.
DELIVERED_VERDICTS = ('met', 'met_with_residuals')
CRITERION_STATUSES = ('met', 'unevidenced', 'not_met')
FIX_KIND_IMPLEMENTATION = 'implementation'
FIX_KIND_CORRECTION = 'correction'
FIX_KINDS = (FIX_KIND_IMPLEMENTATION, FIX_KIND_CORRECTION)
CITATION_FORMS = ('pack_rule', 'spine_category', 'convention', 'adr')
#: The failure classes review-rubric.md § 3 grades blocking; ``none`` is advisory.
BLOCKING_FAILURE_CLASSES = ('wrong_result', 'lost_data', 'fail_open', 'broken_contract')
FAILURE_CLASSES = (*BLOCKING_FAILURE_CLASSES, 'none')

SEVERITY_BLOCKING = 'blocking'
SEVERITY_ADVISORY = 'advisory'

#: The authorship marker the review's own script verb stamps onto a verdict file.
AUTHORED_KEY = 'authored'
AUTHORSHIP_SCHEMA = 'review-verdict-authorship/1'
AUTHORSHIP_VERB = 'review_support author-verdict'

#: A criterion whose Done-when is a run against the PRE-fix tree.
PRE_FIX_CRITERION_RE = re.compile(
    r'(?i)(pre-?fix|fails?\s+(?:at|on|against)\s+(?:the\s+)?`?[0-9a-f]{7,40}`?|fails?\s+before\s+the\s+fix)'
)
#: Evidence that names a failing run against the pre-fix tree (a SHA-bearing failure).
PRE_FIX_EVIDENCE_RE = re.compile(r'(?i)(pre-?fix|before\s+the\s+fix)')
FAILURE_TOKEN_RE = re.compile(r'(?i)\bfail(?:s|ed|ing)?\b')
SHA_RE = re.compile(r'[0-9a-f]{7,40}')
#: An evidence entry that cites a repository path (optionally ``:line`` and ``::name``).
#:
#: The path component excludes ``:`` deliberately. ``\S+`` used to swallow the
#: ``::`` separator too, so a class-scoped citation
#: (``test/test_parser.py::TestClass.test_method``) resolved to the WHOLE string
#: as its path, failed the existence check, and reported a valid citation as
#: absent at the graded head — the false refusal this pattern exists to avoid.
EVIDENCE_PATH_RE = re.compile(r'^([^:\s]+\.\w+)(?::\d+(?:-\d+)?)?(?:::(\S+))?$')

#: The facts a valid functional verdict records, before the two shared counts.
FUNCTIONAL_FACT_KEYS = (
    'deliverables_reviewed',
    'criteria_checked',
    'files_read',
    'deliverables_met',
    'deliverables_met_with_residuals',
    'deliverables_not_met',
    'deliverables_superseded',
    'criteria_unevidenced',
    'unrequested_changes',
    'false_self_reports',
)
#: The facts a valid code verdict records, before the two shared counts.
CODE_FACT_KEYS = ('domains_reviewed', 'files_read', 'rules_cited')
#: The counts both kinds record once the findings are graded.
SHARED_FACT_KEYS = ('blocking_count', 'advisory_count')

VERIFIER_ABSENT = 'absent'
VERIFIER_ACCEPTED = 'accepted'
VERIFIER_DECLINED = 'declined'
VERIFIER_MALFORMED = 'malformed'

_LOCATION_RE = re.compile(r'^\S[^:]*:\d+(?:-\d+)?$')
_DELIVERABLE_ID_RE = re.compile(r'(\d+)\s*$')


def deliverable_number(raw: Any) -> int | None:
    """Return the deliverable number a free-form id ends in (``3``, ``'D3'``), or ``None``."""
    match = _DELIVERABLE_ID_RE.search(str(raw if raw is not None else ''))
    return int(match.group(1)) if match else None


def read_json_object(path: str) -> tuple[dict[str, Any] | None, str]:
    """Return ``(object, '')``, or ``(None, problem)`` when the file is unreadable or not an object."""
    try:
        parsed = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        return None, str(exc)
    if not isinstance(parsed, dict):
        return None, f'top-level JSON value is {type(parsed).__name__}, not an object'
    return parsed, ''


def canonical_digest(payload: dict[str, Any]) -> str:
    """Return the SHA-256 of a verdict's content, independent of key order and whitespace.

    The digest covers the verdict WITHOUT its authorship marker, so re-serialising
    the same verdict anywhere (a different JSON indentation, a different key
    order) reproduces it, while any edit to a graded value does not.
    """
    body = {key: value for key, value in payload.items() if key != AUTHORED_KEY}
    encoded = json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def seal_verdict(payload: dict[str, Any], kind: str) -> dict[str, Any]:
    """Return ``payload`` carrying its authorship marker (the marker last)."""
    sealed = {key: value for key, value in payload.items() if key != AUTHORED_KEY}
    sealed[AUTHORED_KEY] = {
        'schema': AUTHORSHIP_SCHEMA,
        'kind': kind,
        'verb': AUTHORSHIP_VERB,
        'digest': canonical_digest(payload),
    }
    return sealed


def authorship_problem(verdict: dict[str, Any]) -> str | None:
    """Return why the verdict does not match the reviewer's recorded output, or ``None``.

    A verdict the review's own script verb did not write has no marker; a verdict
    edited after the verb wrote it has a marker whose digest no longer matches
    the content. Both are refusals at the finalize step gate — the failure is
    ``python3 -c`` editing the verdict file in place, and a rewritten criterion
    graded in the author's own words reads as clean without this check.
    """
    marker = verdict.get(AUTHORED_KEY)
    if not isinstance(marker, dict) or marker.get('schema') != AUTHORSHIP_SCHEMA:
        return f'the verdict was not written by {AUTHORSHIP_VERB}'
    if not isinstance(marker.get('digest'), str) or marker['digest'] != canonical_digest(verdict):
        return 'the verdict was modified after the reviewer wrote it'
    return None


def is_pre_fix_criterion(text: Any) -> bool:
    """Whether a criterion's Done-when is a run against the pre-fix tree."""
    return bool(PRE_FIX_CRITERION_RE.search(str(text or '')))


def names_pre_fix_run(evidence: list[str]) -> bool:
    """Whether any evidence entry names a FAILING run against the pre-fix tree.

    Both halves are required: a marker that the entry is about the pre-fix tree
    (or the SHA of the tree it failed against) AND a failure token. An entry that
    merely mentions the pre-fix tree — "the suite passes on the pre-fix tree" —
    names no failure, and a green run at HEAD names neither.
    """
    for item in evidence:
        text = str(item)
        if not FAILURE_TOKEN_RE.search(text):
            continue
        if PRE_FIX_EVIDENCE_RE.search(text) or SHA_RE.search(text):
            return True
    return False


def cited_evidence_path(entry: Any) -> str | None:
    """Return the repository path an evidence entry cites, or ``None``.

    Only an entry shaped like a path is a citation that must exist at the graded
    head; a free-form description of a recorded run (``module-tests at <sha>``)
    is not a path and is never existence-checked.
    """
    match = EVIDENCE_PATH_RE.match(str(entry or '').strip())
    if not match:
        return None
    return match.group(1)


def missing_evidence(evidence_root: Path, evidence: list[str]) -> list[str]:
    """Return every cited path, or cited test name, absent from ``evidence_root``.

    A path that does not exist at the graded head is a citation of something the
    change never had; a ``path::name`` whose name appears nowhere in the file is
    the PLAN-LB-40 fabrication — a cited test that exists nowhere. A dotted name
    is checked segment by segment, so a class-scoped citation counts when the
    file holds its class and its method.
    """
    missing: list[str] = []
    for entry in evidence:
        raw = str(entry).strip()
        path = cited_evidence_path(raw)
        if path is None:
            continue
        target = evidence_root / path
        if not target.is_file():
            missing.append(raw)
            continue
        _, _, name = raw.partition('::')
        if name and name.strip():
            try:
                content = target.read_text(encoding='utf-8')
            except OSError:
                missing.append(raw)
                continue
            # A dotted name is checked SEGMENT by SEGMENT: a class-scoped citation
            # names a class and a method the file holds separately, so requiring
            # the literal dotted string would refuse a real test.
            segments = [segment for segment in name.strip().split('.') if segment]
            if not segments or any(segment not in content for segment in segments):
                missing.append(raw)
    return missing


def verifier_status(path: str | None, has_blocking: bool) -> str:
    """Return ``absent`` / ``accepted`` / ``declined`` / ``malformed`` for a verifier answer.

    Acceptance follows the first rubric § 7 answer, ``grading_supported``: a
    verifier that confirms the grading accepted it. The second answer,
    ``may_close``, is ``false`` by rule whenever a blocking finding remains, so on
    a round with a blocking finding it says nothing about acceptance. On a round
    without one, a supported grading answered ``may_close: false`` is the verifier
    refusing a closure the grading permits, so it is ``declined`` too. A file that
    cannot be read or does not carry both answers as booleans is ``malformed``,
    which closes nothing.

    Args:
        path: The verifier's JSON answer file, or ``None`` when no answer was written.
        has_blocking: Whether the graded verdict holds at least one blocking finding.

    Returns:
        One of the four ``VERIFIER_*`` values.
    """
    if not path:
        return VERIFIER_ABSENT
    data, _ = read_json_object(path)
    if data is None or not all(isinstance(data.get(key), bool) for key in ('grading_supported', 'may_close')):
        return VERIFIER_MALFORMED
    if not data['grading_supported']:
        return VERIFIER_DECLINED
    return VERIFIER_ACCEPTED if data['may_close'] or has_blocking else VERIFIER_DECLINED


class Grading:
    """Schema errors, criterion rewrites, rejected findings and graded findings of one verdict."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.findings: list[dict[str, Any]] = []
        self.rewrites: list[dict[str, Any]] = []
        self.rejected: list[dict[str, Any]] = []

    @property
    def valid(self) -> bool:
        """A verdict is valid only with no schema error and no rejected finding."""
        return not self.errors and not self.rejected

    def add(self, kind: str, ref: str, title: str, blocking: bool, fix_kind: Any, where: str) -> None:
        """Record one graded finding; a blocking one must carry a valid ``fix_kind``."""
        if fix_kind is not None and fix_kind not in FIX_KINDS:
            self.errors.append(f'{where}: fix_kind {fix_kind!r} is not one of {", ".join(FIX_KINDS)}')
            return
        if blocking and fix_kind is None:
            self.errors.append(f'{where}: a blocking finding must name its fix_kind')
            return
        self.findings.append(
            {
                'id': f'F{len(self.findings) + 1}',
                'kind': kind,
                'severity': SEVERITY_BLOCKING if blocking else SEVERITY_ADVISORY,
                'fix_kind': fix_kind or '-',
                'ref': ref,
                'title': title,
            }
        )


def _str_list(value: Any) -> list[str]:
    return [str(v).strip() for v in value if str(v).strip()] if isinstance(value, list) else []


def _list_field(verdict: dict[str, Any], key: str, grading: Grading, required: bool = True) -> list[Any]:
    value = verdict.get(key)
    if value is None and not required:
        return []
    if not isinstance(value, list):
        grading.errors.append(f'{key} must be a list')
        return []
    return value


def _grade_consequential(grading: Grading, item: Any, kind: str, ref: str, flag: str, where: str) -> bool:
    """Grade one consequence-graded item (residual, unrequested change, false claim) on ``flag``."""
    if not isinstance(item, dict) or not isinstance(item.get(flag), bool):
        grading.errors.append(f'{where}: {flag} must be true or false')
        return False
    title = str(item.get('description') or item.get('reason') or item.get('claim') or '').strip()
    grading.add(kind, ref, title or kind, item[flag], item.get('fix_kind'), where)
    return True


def _grade_criteria(
    grading: Grading,
    row: dict[str, Any],
    expected: dict[str, Any],
    facts: dict[str, int],
    evidence_root: Path | None = None,
) -> None:
    number, verdict = expected['number'], row['verdict']
    where = f'deliverable {number}'
    criteria = row.get('criteria')
    if not isinstance(criteria, list):
        grading.errors.append(f'{where}: criteria must be a list')
        return
    wanted = len(expected.get('success_criteria', []))
    if wanted and len(criteria) != wanted:
        grading.errors.append(f'{where}: {len(criteria)} criteria rows for {wanted} success criteria')
    if not criteria and verdict in DELIVERED_VERDICTS:
        # Without a parsed outline criterion the count check above is vacuous, so an
        # empty list would let a delivered verdict through with no evidence at all.
        grading.errors.append(f'{where}: a {verdict} deliverable evaluates no success criterion')
    for index, criterion in enumerate(criteria, start=1):
        status = criterion.get('status') if isinstance(criterion, dict) else None
        if status not in CRITERION_STATUSES:
            grading.errors.append(f'{where} criterion {index}: status {status!r} is not valid')
            continue
        facts['criteria_checked'] += 1
        text = str(criterion.get('criterion') or f'criterion {index}')
        evidence = _str_list(criterion.get('evidence'))
        pre_fix_gap = is_pre_fix_criterion(text) and not names_pre_fix_run(evidence)
        if status == 'met' and (not evidence or pre_fix_gap):
            grading.rewrites.append({'deliverable': number, 'criterion': index, 'from': 'met', 'to': 'unevidenced'})
            status = 'unevidenced'
        if status == 'met' and evidence_root is not None:
            # Every path and test name a criterion cites must exist at the graded
            # head: a citation of something the change never had is not evidence,
            # and grading it met is how a fabricated test name passes a review.
            for raw in missing_evidence(evidence_root, evidence):
                grading.errors.append(f'{where} criterion {index}: evidence {raw!r} does not exist at the graded head')
        if status == 'not_met' and verdict == 'met':
            grading.errors.append(f'{where} criterion {index}: a met deliverable carries a not_met criterion')
        if status == 'unevidenced':
            facts['criteria_unevidenced'] += 1
            title = f'{text} — no run against the pre-fix tree' if pre_fix_gap else text
            fix_kind = criterion.get('fix_kind') or FIX_KIND_IMPLEMENTATION
            grading.add('unevidenced_criterion', f'D{number}.C{index}', title, True, fix_kind, where)


def _grade_row(
    grading: Grading,
    row: dict[str, Any],
    expected: dict[str, Any],
    facts: dict[str, int],
    evidence_root: Path | None = None,
) -> None:
    number = expected['number']
    where = f'deliverable {number}'
    verdict = row.get('verdict')
    if verdict not in FUNCTIONAL_VERDICTS:
        grading.errors.append(f'{where}: verdict {verdict!r} is not one of {", ".join(FUNCTIONAL_VERDICTS)}')
        return
    facts['deliverables_reviewed'] += 1
    facts[f'deliverables_{verdict}'] += 1
    if verdict == 'superseded':
        if not str(row.get('superseded_by') or '').strip():
            grading.errors.append(f'{where}: superseded without a cited operator decision or refutation')
        return
    _grade_criteria(grading, row, expected, facts, evidence_root)
    if verdict == 'not_met':
        fix_kind = row.get('fix_kind') or FIX_KIND_IMPLEMENTATION
        grading.add('deliverable_not_met', f'D{number}', str(expected.get('title', '')), True, fix_kind, where)
    if verdict == 'met_with_residuals':
        residuals = row.get('residuals')
        if not isinstance(residuals, list) or not residuals:
            grading.errors.append(f'{where}: met_with_residuals names no residual')
            return
        for index, residual in enumerate(residuals, start=1):
            _grade_consequential(grading, residual, 'residual', f'D{number}.R{index}', 'consequential', where)


def grade_frozen_criteria(grading: Grading, drift: list[dict[str, Any]]) -> int:
    """Grade the frozen-criteria drift as blocking findings; return the count.

    One finding per criterion the current outline no longer carries verbatim, one
    per frozen deliverable that vanished, and one per spec deliverable whose own
    Done-when no outline criterion covers. A criterion the snapshot froze and an
    operator decision authorized is not in ``drift`` at all, so it is a pass.
    """
    for row in drift:
        kind = row.get('kind')
        if kind == SPEC_MISSING:
            grading.add(
                kind,
                str(row.get('spec_deliverable') or 'spec'),
                str(row.get('criterion')),
                True,
                FIX_KIND_IMPLEMENTATION,
                'spec deliverable',
            )
            continue
        number = row.get('deliverable')
        if kind == 'rewritten':
            graded_kind, title = 'criterion_rewritten', f'{row.get("criterion")} -> {row.get("current")}'
        else:
            graded_kind, title = 'criterion_deleted', str(row.get('criterion'))
        grading.add(graded_kind, f'D{number}', title, True, FIX_KIND_IMPLEMENTATION, f'deliverable {number}')
    return len(drift)


def validate_functional(
    verdict: dict[str, Any],
    deliverables: list[dict[str, Any]],
    grading: Grading,
    evidence_root: Path | None = None,
) -> dict[str, int]:
    """Grade a functional verdict against the outline; return its facts (meaningful only when valid).

    Requires exactly one row per outline deliverable. Each ``deliverables``
    entry of ``deliverables`` carries ``number``, ``title`` and
    ``success_criteria`` (the outline's criterion bullets). When
    ``evidence_root`` is given, every path and test name a ``met`` criterion
    cites is checked against the tree at the graded head.
    """
    facts = dict.fromkeys(FUNCTIONAL_FACT_KEYS, 0)
    by_number: dict[int, dict[str, Any]] = {}
    for index, row in enumerate(_list_field(verdict, 'deliverables', grading), start=1):
        number = deliverable_number(row.get('number')) if isinstance(row, dict) else None
        if number is None or number in by_number:
            grading.errors.append(f'deliverables row {index}: missing or duplicate deliverable number')
            continue
        by_number[number] = row
    expected = {d['number']: d for d in deliverables}
    for number in sorted(set(expected) - set(by_number)):
        grading.errors.append(f'deliverable {number}: no verdict row')
    for number in sorted(set(by_number) - set(expected)):
        grading.errors.append(f'deliverable {number}: not an outline deliverable')
    for number in sorted(set(expected) & set(by_number)):
        _grade_row(grading, by_number[number], expected[number], facts, evidence_root)

    for index, change in enumerate(_list_field(verdict, 'unrequested_changes', grading, False), start=1):
        path = str(change.get('path') or '').strip() if isinstance(change, dict) else ''
        if not path:
            grading.errors.append(f'unrequested change {index}: path is required')
        elif _grade_consequential(grading, change, 'unrequested_change', path, 'consequential', f'unrequested {path}'):
            facts['unrequested_changes'] += 1
    for index, report in enumerate(_list_field(verdict, 'self_reports', grading, False), start=1):
        where = f'self report {index}'
        if not isinstance(report, dict) or not isinstance(report.get('holds'), bool):
            grading.errors.append(f'{where}: holds must be true or false')
            continue
        if report['holds']:
            continue
        source = str(report.get('source') or where)
        if _grade_consequential(grading, report, 'false_self_report', source, 'reader_acts_on', where):
            facts['false_self_reports'] += 1
    facts['files_read'] = len(_str_list(_list_field(verdict, 'files_read', grading)))
    return facts


def validate_code(verdict: dict[str, Any], grading: Grading) -> dict[str, int]:
    """Grade a code-review findings list; a finding without rule, location or scenario is rejected."""
    cited: set[tuple[str, str]] = set()
    for index, raw in enumerate(_list_field(verdict, 'findings', grading), start=1):
        finding = raw if isinstance(raw, dict) else {}
        raw_rule = finding.get('rule')
        rule: dict[str, Any] = raw_rule if isinstance(raw_rule, dict) else {}
        form, ref = str(rule.get('form') or ''), str(rule.get('ref') or '').strip()
        location = str(finding.get('location') or '').strip()
        scenario = str(finding.get('failure_scenario') or '').strip()
        checks = (
            ('rule', form in CITATION_FORMS and bool(ref)),
            ('location', bool(_LOCATION_RE.match(location))),
            ('failure_scenario', bool(scenario)),
        )
        missing = [name for name, ok in checks if not ok]
        if missing:
            grading.rejected.append({'finding': index, 'missing': ' '.join(missing)})
            continue
        failure_class = finding.get('failure_class')
        if failure_class not in FAILURE_CLASSES:
            grading.errors.append(f'finding {index}: failure_class {failure_class!r} is not valid')
            continue
        cited.add((form, ref))
        blocking = failure_class in BLOCKING_FAILURE_CLASSES
        title = str(finding.get('title') or scenario)
        grading.add('code_finding', location, title, blocking, finding.get('fix_kind'), f'finding {index}')
    return {
        'domains_reviewed': len(_str_list(_list_field(verdict, 'domains_reviewed', grading))),
        'files_read': len(_str_list(_list_field(verdict, 'files_read', grading))),
        'rules_cited': len(cited),
    }


__all__ = [
    'AUTHORED_KEY',
    'AUTHORSHIP_SCHEMA',
    'BLOCKING_FAILURE_CLASSES',
    'CITATION_FORMS',
    'CODE_FACT_KEYS',
    'CRITERION_STATUSES',
    'DELIVERED_VERDICTS',
    'FAILURE_CLASSES',
    'FIX_KINDS',
    'FIX_KIND_CORRECTION',
    'FIX_KIND_IMPLEMENTATION',
    'FUNCTIONAL_FACT_KEYS',
    'FUNCTIONAL_VERDICTS',
    'Grading',
    'KIND_CODE',
    'KIND_FUNCTIONAL',
    'SEVERITY_ADVISORY',
    'SEVERITY_BLOCKING',
    'SHARED_FACT_KEYS',
    'VERIFIER_ABSENT',
    'VERIFIER_ACCEPTED',
    'VERIFIER_DECLINED',
    'VERIFIER_MALFORMED',
    'authorship_problem',
    'canonical_digest',
    'cited_evidence_path',
    'deliverable_number',
    'grade_frozen_criteria',
    'is_pre_fix_criterion',
    'missing_evidence',
    'names_pre_fix_run',
    'read_json_object',
    'seal_verdict',
    'validate_code',
    'validate_functional',
    'verifier_status',
]

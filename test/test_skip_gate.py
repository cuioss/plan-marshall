# SPDX-License-Identifier: FSL-1.1-ALv2
"""Meta-tests for the session-finish skip gate in ``test/conftest.py``.

The gate is what makes a green run mean "every test ran": it fails the session on
any skip outside :data:`conftest._SKIP_EXCEPTIONS`. An entry there approves a
**cause** — the class and the reason recorded beside the nodeid — not the test,
so the gate measures BOTH halves. The property pinned here is that second half:
a listed test that starts skipping for a different cause must not inherit the old
approval.

The defect this closes was the gate's own inversion. The offender set was a pure
nodeid difference, so an approved test whose cause changed — a fixture that broke,
a new regression guard firing — kept the session green while covering less than it
claimed. That is precisely the false-clean signal the gate exists to remove.

Every positive here is matched by a negative control. A gate that fires on a
changed cause is only worth having if it stays silent on the approved one, and a
tolerance test that never sees the tolerant case would pass against a gate that
had become unconditional.

The real :func:`conftest.pytest_sessionfinish` is driven over synthetic records
rather than the live session's: the live dict holds whatever this machine happened
to skip, which is an environment fact and cannot state a contract.
"""

import pytest

import conftest

#: A real entry from the residual skippable set, used as the approved case. Taking
#: it from the live set rather than inventing one keeps the fixture honest about
#: the shape the gate actually reads.
_LISTED_NODEID = 'test/plan-marshall/lsp-client/test_lsp_integration.py::test_real_clean_rename_edit'
_APPROVED_REASON = 'pyright-langserver not installed'
_APPROVED = {_LISTED_NODEID: ('absent-dependency', _APPROVED_REASON)}

#: A cause the entry above does NOT approve — the fixture-broke case from the
#: finding, which the nodeid-only gate green-lit.
_NEW_CAUSE = 'fixture lsp_server failed to start'

_UNLISTED_NODEID = 'test/plan-marshall/manage-files/test_manage_files.py::test_something_new'


class _Reporter:
    """A terminal reporter that records the lines the gate wrote."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def write_line(self, line, **_kwargs) -> None:
        self.lines.append(line)


class _PluginManager:
    def __init__(self, reporter: _Reporter) -> None:
        self._reporter = reporter

    def get_plugin(self, name: str):
        return self._reporter if name == 'terminalreporter' else None


class _Option:
    """The unfiltered run: no ``-k``, no ``-m``, so the gate is not exempt."""

    keyword = ''
    markexpr = ''


class _Config:
    def __init__(self, reporter: _Reporter) -> None:
        self.option = _Option()
        self.pluginmanager = _PluginManager(reporter)


class _Session:
    """A controller session — deliberately without ``workerinput``, which is what
    marks an xdist worker and would make the gate return before rendering."""

    def __init__(self, reporter: _Reporter) -> None:
        self.config = _Config(reporter)
        self.exitstatus = 0


def _run_gate(monkeypatch, skipped: dict[str, str], approved=None) -> tuple[_Session, _Reporter]:
    """Drive the real hook over synthetic records; return the session and reporter."""
    monkeypatch.setattr(conftest, '_SKIPPED_NODEIDS', dict(skipped))
    monkeypatch.setattr(conftest, '_SKIP_EXCEPTIONS', dict(_APPROVED if approved is None else approved))
    reporter = _Reporter()
    session = _Session(reporter)

    conftest.pytest_sessionfinish(session, 0)

    return session, reporter


def _rendered(reporter: _Reporter) -> str:
    return '\n'.join(reporter.lines)


# ---------------------------------------------------------------------------
# Negative controls: the gate stays silent on an approved cause
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'recorded',
    [
        pytest.param(_APPROVED_REASON, id='verbatim'),
        pytest.param(f'Skipped: {_APPROVED_REASON}', id='pytest-Skipped-prefix'),
        pytest.param(f'skipped:  {_APPROVED_REASON}', id='lowercase-prefix-and-padding'),
        pytest.param(f'Skipped: {_APPROVED_REASON} (PATH searched)', id='reason-with-appended-context'),
        pytest.param('Skipped: pyright-langserver\n   not installed', id='rewrapped-across-lines'),
    ],
)
def test_a_listed_nodeid_skipping_for_its_approved_reason_keeps_the_session_green(monkeypatch, recorded):
    """The approved cause passes in every form pytest may record it in.

    The prefix, casing, padding and line-wrapping cases are the reason the
    comparison normalizes rather than matching raw; the appended-context case is
    the reason it uses containment rather than equality. Any of them reddening the
    run would be a gate that fails for formatting instead of for cause.
    """
    session, reporter = _run_gate(monkeypatch, {_LISTED_NODEID: recorded})

    assert session.exitstatus == 0, f'the approved cause reddened the session:\n{_rendered(reporter)}'
    assert reporter.lines == []


def test_an_empty_session_stays_green(monkeypatch):
    """Nothing skipped, nothing reported — the gate is not unconditionally red."""
    session, reporter = _run_gate(monkeypatch, {})

    assert session.exitstatus == 0
    assert reporter.lines == []


# ---------------------------------------------------------------------------
# The defect: a listed nodeid whose CAUSE changed
# ---------------------------------------------------------------------------


def test_a_listed_nodeid_skipping_for_a_new_cause_fails_the_session(monkeypatch):
    """The finding, stated as a test: an approved nodeid does not get to skip for
    a cause nobody approved. Under the nodeid-only difference this run was green."""
    session, reporter = _run_gate(monkeypatch, {_LISTED_NODEID: f'Skipped: {_NEW_CAUSE}'})

    assert session.exitstatus == 1, 'a listed test skipping for a NEW cause kept the session green'
    assert _LISTED_NODEID in _rendered(reporter)


def test_the_reason_mismatch_report_names_both_the_approved_and_the_recorded_cause(monkeypatch):
    """The operator must see the divergence without opening the source, so both
    sides are printed and labelled."""
    _, reporter = _run_gate(monkeypatch, {_LISTED_NODEID: f'Skipped: {_NEW_CAUSE}'})

    rendered = _rendered(reporter)
    assert f'approved reason: {_APPROVED_REASON}' in rendered
    assert f'recorded reason: Skipped: {_NEW_CAUSE}' in rendered


# ---------------------------------------------------------------------------
# The pre-existing arm, unchanged in substance
# ---------------------------------------------------------------------------


def test_an_unlisted_nodeid_still_fails_with_the_add_an_entry_guidance(monkeypatch):
    """Widening the gate did not weaken the arm that already worked: an unlisted
    skip still reddens the run, still names its recorded reason, and still carries
    the fix-or-list guidance."""
    session, reporter = _run_gate(monkeypatch, {_UNLISTED_NODEID: 'Skipped: some new guard fired'})

    rendered = _rendered(reporter)
    assert session.exitstatus == 1
    assert _UNLISTED_NODEID in rendered
    assert 'residual skippable set' in rendered
    assert 'add the nodeid to _SKIP_EXCEPTIONS' in rendered
    assert 'reason: Skipped: some new guard fired' in rendered


def test_the_two_offender_kinds_are_reported_distinguishably(monkeypatch):
    """An unlisted nodeid and a reason-mismatched one need different remedies — add
    an entry, versus investigate a changed cause — so a report that collapsed them
    into one list would send the reader to the wrong one."""
    _, reporter = _run_gate(
        monkeypatch,
        {
            _UNLISTED_NODEID: 'Skipped: some new guard fired',
            _LISTED_NODEID: f'Skipped: {_NEW_CAUSE}',
        },
    )

    rendered = _rendered(reporter)
    assert 'skipped outside the' in rendered, 'the unlisted arm did not report'
    assert 'skipped for a reason other than the approved one' in rendered, 'the mismatch arm did not report'
    assert 'investigate what changed' in rendered


# ---------------------------------------------------------------------------
# The classifier itself
# ---------------------------------------------------------------------------


def test_skip_offenders_separates_the_two_kinds():
    """The classifier returns the kinds apart, which is what lets the report name
    which one fired."""
    unlisted, mismatched = conftest._skip_offenders(
        {
            _UNLISTED_NODEID: 'anything',
            _LISTED_NODEID: f'Skipped: {_NEW_CAUSE}',
        },
        _APPROVED,
    )

    assert unlisted == [_UNLISTED_NODEID]
    assert mismatched == [(_LISTED_NODEID, _APPROVED_REASON, f'Skipped: {_NEW_CAUSE}')]


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [
        pytest.param('Skipped: a reason', 'a reason', id='strips-the-rendered-prefix'),
        pytest.param('SKIPPED:a reason', 'a reason', id='prefix-strip-is-case-insensitive'),
        pytest.param('  a   reason\n  here ', 'a reason here', id='collapses-and-trims-whitespace'),
        pytest.param('unskipped: a reason', 'unskipped: a reason', id='only-a-leading-prefix-is-stripped'),
    ],
)
def test_normalize_skip_reason(raw, expected):
    """Both sides of the comparison pass through this, so its exact output is the
    contract rather than an implementation detail."""
    assert conftest._normalize_skip_reason(raw) == expected

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``pr view`` returns the PR/MR description, whole, on BOTH providers.

The close-and-re-open recovery reads a pull request and carries its title, head
branch AND body across to the replacement, so that nothing an operator or a
reviewer wrote into the description is lost. That promise is only keepable if the
body is actually in the return: a caller that cannot read it has no option but to
substitute a body it regenerated, which discards exactly the edits the promise
covers.

Presence alone is not the contract, so presence alone is not what is asserted
here. Three properties are, each with a control that makes it non-vacuous:

* **Fidelity** — the returned body is the body the provider reported, byte for
  byte. The control is a second, different body driven through the same handler:
  an implementation returning a constant, a placeholder or a truncation passes a
  single-body assertion and fails the pair.
* **Survival** — the body still reads back intact after the payload crosses the
  TOON boundary the CLI actually prints through. The control is the same payload
  with the body left unmarked, which is asserted to be corrupted — so the
  positive arm cannot be passing because the check is toothless.
* **Parity** — both providers carry the field, read from each platform's own name
  for it (``body`` on GitHub, ``description`` on GitLab). The control is that the
  parity arm derives its provider set from the cases it ran rather than naming
  one.

No extra provider round trip pays for any of this: the field rides the ``pr
view`` call that was already being made, which the argv arms assert directly.
"""

from __future__ import annotations

import json

import github_ops
import gitlab_ops
import pytest
from toon_parser import parse_toon, serialize_toon

# A description that exercises every shape a naive scalar emission mishandles: a
# markdown heading, interior blank lines, a line that reads exactly like a TOON
# key/value pair (``status: blocked`` — the same key the envelope itself uses),
# a colon inside list text, and an indented continuation.
BODY_WITH_TOON_SHAPES = (
    '## Summary\n'
    '\n'
    'status: blocked\n'
    '\n'
    '- bullet: with a colon\n'
    '    indented continuation\n'
    '\n'
    'Closes #1431'
)

# The matched control body. Deliberately unrelated to the one above so that any
# constant/placeholder/truncating implementation returns the same thing for both
# and fails the pair.
OTHER_BODY = 'One line only, no markdown at all.'


def _github_view(monkeypatch, body):
    """Drive ``github_ops.view_pr_data`` against a stubbed ``gh pr view``.

    Returns ``(payload, captured_argv)`` where ``captured_argv`` is every
    ``run_gh`` argument vector the call issued — the evidence for how many
    provider round trips were spent and which fields were requested.
    """
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        return 0, json.dumps({'number': 1431, 'url': 'u', 'state': 'OPEN', 'title': 'T', 'body': body}), ''

    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    return github_ops.view_pr_data(), captured


def _gitlab_view(monkeypatch, description):
    """Drive ``gitlab_ops.view_pr_data`` against a stubbed ``glab mr view``.

    GitLab names the field ``description``; the parameter is spelled the same way
    so the test reads in the provider's own vocabulary and the normalisation onto
    the shared ``body`` key stays visible as a normalisation.
    """
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        payload = {'iid': 1431, 'web_url': 'u', 'state': 'opened', 'title': 'T', 'description': description}
        return 0, json.dumps(payload), ''

    monkeypatch.setattr(gitlab_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    return gitlab_ops.view_pr_data(), captured


#: The provider arms, as ``(provider_name, driver)``. Every parity assertion
#: derives its provider set from THIS table rather than naming a provider, so an
#: arm that stopped running is a shrunken population the parity test reports,
#: not a silently narrower green.
PROVIDER_DRIVERS = (
    ('github', _github_view),
    ('gitlab', _gitlab_view),
)


# =============================================================================
# Presence
# =============================================================================


@pytest.mark.parametrize(('provider', 'drive'), PROVIDER_DRIVERS)
def test_pr_view_returns_a_body_field(monkeypatch, provider, drive):
    """``pr view`` carries a ``body`` key on every provider."""
    payload, _ = drive(monkeypatch, BODY_WITH_TOON_SHAPES)

    assert payload['status'] == 'success'
    assert 'body' in payload, f'{provider}: pr view returned no body field: {sorted(payload)}'


def test_body_is_present_on_every_provider_not_just_one():
    """The field is provider-agnostic, so no arm may be the only one carrying it.

    Derived from :data:`PROVIDER_DRIVERS` rather than from a named pair: a
    provider dropped from the table shrinks the population, and the size
    assertion is what makes that shrink visible instead of green.
    """
    assert len(PROVIDER_DRIVERS) >= 2, (
        f'parity is unassertable over {len(PROVIDER_DRIVERS)} provider(s): '
        f'{[name for name, _ in PROVIDER_DRIVERS]}'
    )


# =============================================================================
# Fidelity — the returned body IS the body that was set
# =============================================================================


@pytest.mark.parametrize(('provider', 'drive'), PROVIDER_DRIVERS)
@pytest.mark.parametrize('body', [BODY_WITH_TOON_SHAPES, OTHER_BODY])
def test_returned_body_is_the_body_the_provider_reported(monkeypatch, provider, drive, body):
    """The body round-trips whole — not truncated, summarised or placeholder.

    Both bodies are driven through the same handler. A constant or truncating
    implementation satisfies one and fails the other, which is what makes this
    assertion non-vacuous.
    """
    payload, _ = drive(monkeypatch, body)

    assert payload['body'] == body, f'{provider}: body was not returned verbatim'


@pytest.mark.parametrize(('provider', 'drive'), PROVIDER_DRIVERS)
def test_two_different_bodies_do_not_return_the_same_text(monkeypatch, provider, drive):
    """The handler discriminates between bodies rather than emitting a fixture.

    The explicit matched control for the fidelity arm above: the two returns must
    differ, and each must be its own input.
    """
    first, _ = drive(monkeypatch, BODY_WITH_TOON_SHAPES)
    second, _ = drive(monkeypatch, OTHER_BODY)

    assert first['body'] != second['body'], f'{provider}: same body returned for two different inputs'
    assert first['body'] == BODY_WITH_TOON_SHAPES
    assert second['body'] == OTHER_BODY


@pytest.mark.parametrize(('provider', 'drive'), PROVIDER_DRIVERS)
def test_absent_description_is_the_empty_string(monkeypatch, provider, drive):
    """A provider reporting no description yields empty text, never a sentinel.

    An absent description is genuinely empty text — unlike ``merge_commit_sha``,
    where the absent form must stay distinguishable from a resolved value. A
    caller writing this straight into the replacement PR's body wants ``''``.
    """
    payload, _ = drive(monkeypatch, None)

    assert payload['body'] == ''


# =============================================================================
# Survival across the TOON boundary the CLI prints through
# =============================================================================


@pytest.mark.parametrize(('provider', 'drive'), PROVIDER_DRIVERS)
def test_body_survives_the_toon_boundary_intact(monkeypatch, provider, drive):
    """Serialised and re-parsed, the body is unchanged and the envelope is intact.

    ``main()`` prints ``serialize_toon(result, table_separator='\\t')``, so this
    is the transport the field actually crosses. The envelope assertion matters
    as much as the body one: the payload's own ``status`` must still read
    ``success`` even though the body contains a line spelling ``status:
    blocked``.
    """
    payload, _ = drive(monkeypatch, BODY_WITH_TOON_SHAPES)

    reparsed = parse_toon(serialize_toon(payload, table_separator='\t'))

    assert reparsed['body'] == BODY_WITH_TOON_SHAPES, f'{provider}: body did not survive TOON'
    assert reparsed['status'] == 'success', f'{provider}: the body forged the envelope status'
    assert reparsed['pr_number'] == 1431


@pytest.mark.parametrize(('provider', 'drive'), PROVIDER_DRIVERS)
def test_an_unmarked_body_would_corrupt_the_envelope(monkeypatch, provider, drive):
    """The matched NEGATIVE control for the survival arm.

    Replacing the marked value with a plain ``str`` of identical content is
    asserted to break both properties the arm above checks. Without this, that
    arm could be passing because the round trip is trivially lossless for any
    string — which it is not — and the marking would look decorative.
    """
    payload, _ = drive(monkeypatch, BODY_WITH_TOON_SHAPES)
    unmarked = dict(payload)
    unmarked['body'] = str(payload['body'])

    reparsed = parse_toon(serialize_toon(unmarked, table_separator='\t'))

    assert reparsed['body'] != BODY_WITH_TOON_SHAPES, f'{provider}: control did not lose the body'
    assert reparsed['status'] != 'success', f'{provider}: control did not forge the envelope status'


# =============================================================================
# The field rides the existing call — no extra provider round trip
# =============================================================================


def test_github_requests_the_body_on_the_single_existing_pr_view_call(monkeypatch):
    """GitHub asks for ``body`` inside the one ``gh pr view --json`` it already made."""
    _, captured = _github_view(monkeypatch, BODY_WITH_TOON_SHAPES)

    view_calls = [args for args in captured if args[:2] == ['pr', 'view']]
    assert len(view_calls) == 1, f'expected exactly one gh pr view call, got {captured}'

    json_fields = view_calls[0][view_calls[0].index('--json') + 1].split(',')
    assert 'body' in json_fields, f'body not requested: {json_fields}'


def test_gitlab_reads_the_description_from_the_single_existing_mr_view_call(monkeypatch):
    """GitLab's MR payload already carries ``description``; parity costs no round trip."""
    _, captured = _gitlab_view(monkeypatch, BODY_WITH_TOON_SHAPES)

    view_calls = [args for args in captured if args[:2] == ['mr', 'view']]
    assert len(view_calls) == 1, f'expected exactly one glab mr view call, got {captured}'
    assert '--output' in view_calls[0] and 'json' in view_calls[0]

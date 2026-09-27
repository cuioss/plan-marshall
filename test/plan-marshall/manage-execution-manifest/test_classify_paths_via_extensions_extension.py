# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _classify_paths_via_extensions,
    _FakeExtension,
    _resolved_role,
)


def test_extension_raising_in_classify_paths_is_skipped():
    """An extension whose classify_paths raises must not abort the aggregator;
    the path falls through to unclaimed if no other extension claims it."""

    class _RaisingExt(_FakeExtension):
        def classify_paths(self, paths):
            raise RuntimeError('boom')

    bad = _RaisingExt('bad')
    good = _FakeExtension(
        'python',
        claims={
            'production': ['scripts/foo.py'],
            'test': [],
            'documentation': [],
            'config': [],
        },
    )
    bucket, _ = _classify_paths_via_extensions(['scripts/foo.py'], extensions=[bad, good])
    assert bucket == 'production_only'


def test_extension_claim_on_a_marshal_json_path_is_never_stolen_by_the_new_entry():
    """A ``marshal.json`` that a build extension claims keeps its claim.

    The residual-set ordering holds for the new basename entry exactly as it does
    for build-maven's ``application.yml``: stage 3 can only ever assign ``config``,
    so observing ``test`` proves the path never reached the stage. Its pairing with
    the positive case above — where the same basename DOES resolve to ``config``
    when nothing claims it — is what makes this a statement about ordering rather
    than about the entry simply being absent.
    """
    claimed_marshal = 'vendor/tool/marshal.json'
    claiming_ext = _FakeExtension(
        'python',
        claims={'production': [], 'test': [claimed_marshal], 'documentation': [], 'config': []},
    )

    assert _resolved_role(claimed_marshal, extensions=[claiming_ext]) == 'test'


def test_extension_claim_on_a_template_path_is_never_stolen_by_stage_3b():
    """A ``.template`` path a build extension claims in stage 2 keeps its role.

    ``test`` is the discriminator: stage 3b can only ever assign
    ``documentation`` / ``config`` / ``production``, so observing ``test`` proves
    the path never reached the stage — the residual-set-only placement held.
    """
    template_path = 'pkg/thing.py.template'
    claiming_ext = _FakeExtension(
        'python',
        claims={'production': [], 'test': [template_path], 'documentation': [], 'config': []},
    )

    assert _resolved_role(template_path, extensions=[claiming_ext]) == 'test'

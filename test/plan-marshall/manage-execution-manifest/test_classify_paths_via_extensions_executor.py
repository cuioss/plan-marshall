# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _EXECUTOR_TEMPLATE,
    _classify_paths_via_extensions,
    _real_build_extensions,
)


def test_executor_template_resolves_to_a_code_bucket_not_unknown():
    """The motivating case: the executor template stops blocking on ``unknown``.

    Asserted against the REAL discovered extension set, because the fact being
    relied on is that no SHIPPED build extension claims this path — build-pyproject's
    patterns require a literal ``scripts/`` segment and the template lives under
    ``templates/``. A fake-extension run could not establish that.
    """
    extensions = _real_build_extensions()
    assert extensions, 'discover_build_extensions() returned no build extensions'

    bucket, unclaimed = _classify_paths_via_extensions([_EXECUTOR_TEMPLATE], extensions=extensions)

    assert unclaimed == [], 'the executor template must not reach the unclaimed set'
    assert bucket == 'production_only', (
        f'the executor template must take the fail-closed production terminal, got bucket={bucket!r}'
    )

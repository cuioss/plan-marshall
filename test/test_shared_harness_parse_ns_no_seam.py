# SPDX-License-Identifier: FSL-1.1-ALv2
"""parse_ns raises its named error when no parser seam is reachable.

A script with no reachable seam raises, rather than degrading to a namespace
the helper invented.
"""

import pytest
from _shared_harness_fixtures import _NO_SEAM_CASE

from conftest import ParserSeamNotFound, parse_ns

# ⛔ Both no-seam cases below pass ``register=False``, and it is load-bearing rather
# than tidiness. ``parse_ns`` loads the script to reach its parser, and its default
# publishes what it loaded in ``sys.modules`` under the file's stem — REPLACING the
# entry. ``ci_base`` and ``platform_runtime`` are both imported plainly elsewhere in
# this suite, so registering a second copy leaves those modules holding an object no
# longer reachable by name: a ``mock.patch('platform_runtime.X')`` then patches the
# copy published here while the function under test keeps reading its own
# ``__globals__``, and ``ci_base.get_default_cwd()`` reads a ``_DEFAULT_CWD`` that
# the ``set_default_cwd`` the production code called never wrote to. Neither patch
# fails — they silently do nothing, and which copy wins is decided by run order.
# Only the namespace is wanted here, which is exactly the case ``register=False``
# exists for; see ``conftest.parse_ns`` and the collision guard in
# ``test/plan-marshall/script-shared/test_conftest_loader_contract.py``.


def test_parse_ns_raises_named_error_for_a_script_with_no_parser_seam():
    """A script with no reachable seam raises, rather than degrading."""
    with pytest.raises(ParserSeamNotFound, match='no parser seam'):
        parse_ns(*_NO_SEAM_CASE, 'anything', register=False)


def test_a_router_script_fails_loudly_rather_than_yielding_a_guess():
    """A script that dispatches before parsing raises, instead of a partial namespace.

    ``platform_runtime``'s ``main()`` resolves an operation and dispatches BEFORE it
    reaches any ``parse_args``, so the interception seam has nothing to capture.
    The contract is that this fails loudly and steers the caller to the published
    builder — never that it returns a namespace assembled from whatever was
    reachable. This pins the limitation the ``parse_ns`` docstring states, so the
    documented caveat is checked rather than merely asserted.
    """
    with pytest.raises(ParserSeamNotFound):
        parse_ns(
            'plan-marshall',
            'platform-runtime',
            'platform_runtime.py',
            'statusline',
            'render',
            register=False,
        )


def test_invalid_argv_is_not_reported_as_a_missing_seam():
    """A rejected command line raises SystemExit, not ParserSeamNotFound.

    The two are different defects — a broken test versus an unreachable script —
    and conflating them sends the reader to the wrong place. Both seams fail this
    way, so the error does not depend on which seam the script exposes.
    """
    with pytest.raises(SystemExit):
        parse_ns('plan-marshall', 'manage-findings', 'manage-findings.py', 'no-such-verb')

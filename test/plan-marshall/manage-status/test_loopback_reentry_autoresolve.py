# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_loopback_reentry_autoresolve.py: handshake."""

from _manage_status_loopback_reentry_autoresolve_fixtures import _cmds, _inv, _store, sys

# =============================================================================
# MODULE IDENTITY
# =============================================================================


def test_the_handshake_modules_are_the_instance_the_production_path_resolves():
    """The stubs in this module patch the module objects ``cmd_verify`` reads.

    Plain imports are what make that true, and the property is asserted rather
    than inferred from a green run. ``conftest.load_script_module`` would bind a
    SECOND copy under the same name: the stub would then patch an object the
    production path never consults, and every stubbed test here would pass while
    verifying nothing — a false green no ordinary assertion could distinguish
    from a real one.
    """
    assert sys.modules['_handshake_commands'] is _cmds
    assert sys.modules['_handshake_store'] is _store
    assert sys.modules['_invariants'] is _inv

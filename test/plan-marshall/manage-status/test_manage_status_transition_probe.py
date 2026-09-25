# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_manage_status_transition_fixtures import _lifecycle


def test_probe_vocabulary_separates_reaching_the_read_from_what_it_saw():
    """``MAILBOX_PROBE_DID_NOT_READ`` is derived, non-empty, and excludes ``read``.

    The set is computed by subtraction from ``MAILBOX_PROBES`` so a member added
    to the vocabulary cannot silently default into the looked-and-found-nothing
    reading. A subtraction that produced the empty set would make every
    could-not-look assertion downstream vacuously true, so its non-emptiness is
    pinned here rather than assumed — and the population it was derived from is
    named, so the guard cannot pass over an empty vocabulary either.
    """
    assert len(_lifecycle.MAILBOX_PROBES) == 3
    assert set(_lifecycle.MAILBOX_PROBES) == {
        _lifecycle.MAILBOX_PROBE_READ,
        _lifecycle.MAILBOX_PROBE_NOT_ORCHESTRATED,
        _lifecycle.MAILBOX_PROBE_UNRESOLVED,
    }
    assert _lifecycle.MAILBOX_PROBE_DID_NOT_READ
    assert _lifecycle.MAILBOX_PROBE_READ not in _lifecycle.MAILBOX_PROBE_DID_NOT_READ
    assert _lifecycle.MAILBOX_PROBE_DID_NOT_READ == frozenset(_lifecycle.MAILBOX_PROBES) - {
        _lifecycle.MAILBOX_PROBE_READ
    }

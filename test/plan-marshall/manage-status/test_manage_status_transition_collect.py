# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_manage_status_transition_fixtures import _lifecycle


def test_collect_modified_files_helper_is_removed():
    """The ``_collect_modified_files`` producer no longer exists.

    The footprint ledger was deleted in favour of the on-demand
    compute-footprint verb; the seeding helper must be gone so no code
    path can re-introduce a persisted modified_files write at transition.
    """
    assert not hasattr(_lifecycle, '_collect_modified_files'), (
        '_collect_modified_files must be deleted — the 5-execute transition '
        'no longer seeds references.modified_files (footprint is derived '
        'on-demand via manage-references compute-footprint).'
    )

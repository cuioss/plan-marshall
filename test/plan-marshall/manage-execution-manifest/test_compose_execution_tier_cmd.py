# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_compose_execution_tier_fixtures import (
    Namespace,
    SimpleNamespace,
    _clear_arch_resolve_cache,
    _mem,
)


class TestCmdComposeClearsDomainAppendedCanonicalsMemo:
    """``cmd_compose`` clears the domain-appended-canonicals ``@lru_cache(maxsize=1)`` at entry.

    ``_manifest_validation._domain_appended_canonicals`` memoizes over
    ``discover_all_extensions()``. In a long-lived process (the marshalld build
    daemon) ``cmd_compose`` runs repeatedly; if the active domains/extensions change
    between composes, a stale memo would keep the wrong domain-seeded canonical set
    and mis-filter D5 domain-seeded verify steps. ``cmd_compose`` must therefore clear
    that memo at entry, alongside the architecture-resolve memo.
    """

    def test_cmd_compose_clears_domain_canonicals_memo_at_entry(self, monkeypatch):
        """The domain memo's ``cache_clear`` fires at ``cmd_compose`` entry.

        An invalid ``change_type`` short-circuits ``cmd_compose`` immediately after the
        two entry-time cache clears, so the assertion needs no plan / marshal.json
        fixture — it observes only the entry-time clear via a spy standing in for the
        memo on the ``_manifest_validation`` module.
        """
        cleared: list[str] = []
        spy = SimpleNamespace(cache_clear=lambda: cleared.append('cleared'))
        monkeypatch.setattr(_mem._manifest_validation, '_domain_appended_canonicals', spy)

        result = _mem.cmd_compose(
            Namespace(
                plan_id='domain-canon-clear',
                change_type='__not_a_valid_change_type__',
                scope_estimate='surgical',
                track='simple',
                commit_and_push=None,
            )
        )

        # Short-circuited on the invalid change_type — but only AFTER the entry-time
        # clear fired.
        assert result is not None
        assert result['error'] == 'invalid_change_type'
        assert cleared == ['cleared']

# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_decision_rules_fixtures import (
    _read_sonar_provider,
    _restore_footprint_resolver,
    json,
)


class TestReadSonarProvider:
    """``_read_sonar_provider`` resolves the Sonar provider from marshal.json."""

    def _seed_providers(self, providers: list[dict]) -> None:
        from file_ops import get_marshal_path

        marshal = {'plan': {'phase-6-finalize': {}}, 'providers': providers}
        marshal_path = get_marshal_path()
        marshal_path.parent.mkdir(parents=True, exist_ok=True)
        marshal_path.write_text(json.dumps(marshal, indent=2))

    def test_returns_sonar_when_declared(self, plan_context):
        self._seed_providers([{'skill_name': 'plan-marshall:workflow-integration-sonar', 'category': 'sonar'}])
        assert _read_sonar_provider() == 'sonar'

    def test_returns_sonar_regardless_of_category(self, plan_context):
        # The reader keys on skill_name, not category, so a differently-categorized
        # Sonar entry still resolves.
        self._seed_providers([{'skill_name': 'plan-marshall:workflow-integration-sonar', 'category': 'quality'}])
        assert _read_sonar_provider() == 'sonar'

    def test_none_when_no_sonar_provider(self, plan_context):
        self._seed_providers([{'skill_name': 'plan-marshall:workflow-integration-github', 'category': 'ci'}])
        assert _read_sonar_provider() is None

    def test_none_when_providers_absent(self, plan_context):
        from file_ops import get_marshal_path

        marshal_path = get_marshal_path()
        marshal_path.parent.mkdir(parents=True, exist_ok=True)
        marshal_path.write_text(json.dumps({'plan': {'phase-6-finalize': {}}}, indent=2))
        assert _read_sonar_provider() is None

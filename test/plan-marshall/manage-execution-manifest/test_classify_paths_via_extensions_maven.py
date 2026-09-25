# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _classify_paths_via_extensions,
    _real_build_extensions,
)


def test_maven_production_resource_is_never_stolen_by_the_infra_fallback():
    """``src/main/resources/application.yml`` stays ``production`` via build-maven.

    The never-steal-a-claim assertion. The stage-3 rule runs only over paths no
    build extension claimed, so a Maven production resource keeps its claim even
    though it is a YAML file. Asserted against the REAL discovered extension set
    because the claim being protected is build-maven's shipped route.
    """
    extensions = _real_build_extensions()
    assert extensions, 'discover_build_extensions() returned no build extensions'

    bucket, unclaimed = _classify_paths_via_extensions(['src/main/resources/application.yml'], extensions=extensions)
    assert bucket == 'production_only'
    assert unclaimed == []

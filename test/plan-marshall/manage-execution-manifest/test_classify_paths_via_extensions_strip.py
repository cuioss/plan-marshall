# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_classify_paths_via_extensions_fixtures import _strip_template_suffix


def test_strip_template_suffix_removes_exactly_one_level():
    """The stripper is single-shot, and leaves a non-template path untouched."""
    assert _strip_template_suffix('docs/guide.md.template.template') == 'docs/guide.md.template'
    assert _strip_template_suffix('docs/guide.md.template') == 'docs/guide.md'
    assert _strip_template_suffix('docs/guide.md') == 'docs/guide.md'

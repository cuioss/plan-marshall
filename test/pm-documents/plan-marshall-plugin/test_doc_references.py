#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the doc-corpus cross-reference engine (``doc_references``, D4).

The engine reads doc files at discovery time and materializes the resolved
references as ``component_refs`` for the documentation domain's Axis-C resolver to
join over. These tests pin the two properties that matter: a genuinely-broken
reference is reported as unresolved, and a valid reference — in any of the AsciiDoc
/ Markdown spellings the corpus actually uses — is NOT falsely reported. The
second is the load-bearing one: a false "dangling reference" is the misleading
signal this whole substrate exists to avoid.
"""

from conftest import load_script_module

_doc_refs = load_script_module('pm-documents', 'plan-marshall-plugin', 'doc_references.py', 'doc_references')
build_doc_component_refs = _doc_refs.build_doc_component_refs
extract_anchors = _doc_refs.extract_anchors
extract_references = _doc_refs.extract_references


# --------------------------------------------------------------------------- #
# Reference extraction
# --------------------------------------------------------------------------- #


def test_extract_asciidoc_macros():
    refs = extract_references(
        'See xref:build.adoc[the build] and link:../user/guide.adoc[guide]\n'
        'include::shared/frag.adoc[]\n'
    )
    assert ('build.adoc', '') in refs
    assert ('../user/guide.adoc', '') in refs
    assert ('shared/frag.adoc', '') in refs


def test_extract_xref_with_anchor_splits_target_and_anchor():
    refs = extract_references('xref:concepts/x.adoc#_a_section[label]')
    assert ('concepts/x.adoc', '_a_section') in refs


def test_extract_bare_anchor_cross_reference():
    # <<anchor>> with no path is a same-file anchor reference (empty target).
    refs = extract_references('As shown in <<my-anchor>> and <<other,with label>>.')
    assert ('', 'my-anchor') in refs
    assert ('', 'other') in refs


def test_extract_pure_id_xref_is_an_anchor_not_a_file():
    # xref:execution-modes[] (no extension, no '/') is an ID reference, not a
    # file path — the exact false-file-miss the disambiguation removes.
    refs = extract_references('jump to xref:execution-modes[Execution Modes]')
    assert ('', 'execution-modes') in refs
    assert ('execution-modes', '') not in refs


def test_extract_markdown_link():
    refs = extract_references('see [the plan](../plans/010-x.md#step-2) now')
    assert ('../plans/010-x.md', 'step-2') in refs


def test_external_references_are_skipped():
    refs = extract_references(
        'link:https://example.com[site] and [ext](http://x.y) and xref:mailto:a@b[mail]'
    )
    assert refs == []


def test_fenced_code_block_references_are_skipped():
    refs = extract_references('----\nxref:should-not-count.adoc[x]\n----\n')
    assert refs == []


def test_inline_code_references_are_skipped():
    # A reference shown as inline code is documentation ABOUT a reference.
    refs = extract_references('The `<<step-configuration>>` ref and `xref:foo.adoc[]` example.')
    assert refs == []


# --------------------------------------------------------------------------- #
# Anchor extraction — every valid id form a reference might use
# --------------------------------------------------------------------------- #


def test_anchor_forms_cover_asciidoc_autoid_and_github_slug():
    anchors = extract_anchors('== Where things live\n')
    # AsciiDoc default auto-id (underscore prefix + separator).
    assert '_where_things_live' in anchors
    # GitHub-style slug (hyphenated).
    assert 'where-things-live' in anchors
    # Raw lowercased title (for natural <<Where things live>> cross-references).
    assert 'where things live' in anchors


def test_anchor_forms_cover_markdown_heading():
    anchors = extract_anchors('## Step Configuration\n')
    assert 'step-configuration' in anchors


def test_explicit_anchors_extracted_case_insensitively():
    anchors = extract_anchors('[[MyBlock]]\n[#other-id]\ntext {#md-id} more\n')
    assert 'myblock' in anchors
    assert 'other-id' in anchors
    assert 'md-id' in anchors


def test_inline_macro_and_block_attribute_anchors():
    anchors = extract_anchors('anchor:inline-id[] text\n[id="block-id"]\n== A Heading\n')
    assert 'inline-id' in anchors
    assert 'block-id' in anchors


# --------------------------------------------------------------------------- #
# build_doc_component_refs — resolution over a real temp tree
# --------------------------------------------------------------------------- #


def _write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
    return p


def test_broken_file_reference_is_reported_unresolved(tmp_path):
    _write(tmp_path, 'doc/a.adoc', 'xref:gone.adoc[missing target]\n')
    refs = build_doc_component_refs(str(tmp_path), 'doc')
    assert any(r['resolved'] is False for r in refs)


def test_valid_file_reference_is_resolved(tmp_path):
    _write(tmp_path, 'doc/a.adoc', 'xref:b.adoc[ok]\n')
    _write(tmp_path, 'doc/b.adoc', '= B\n')
    refs = build_doc_component_refs(str(tmp_path), 'doc')
    assert refs
    assert all(r['resolved'] for r in refs)


def test_broken_anchor_reported_valid_anchor_not(tmp_path):
    _write(
        tmp_path,
        'doc/target.adoc',
        '= Target\n\n== Real Heading\n\ncontent\n',
    )
    _write(
        tmp_path,
        'doc/src.adoc',
        'good: xref:target.adoc#_real_heading[ok]\n'
        'bad: xref:target.adoc#_deleted_heading[dangling]\n',
    )
    refs = build_doc_component_refs(str(tmp_path), 'doc')
    resolved_states = {r['resolved'] for r in refs}
    # Both a resolved and an unresolved reference are present, distinctly.
    assert True in resolved_states
    assert False in resolved_states


def test_same_file_anchor_resolution(tmp_path):
    _write(
        tmp_path,
        'doc/self.adoc',
        '= Self\n\n[[valid-anchor]]\ntext\n\nsee <<valid-anchor>> and <<missing-anchor>>\n',
    )
    refs = build_doc_component_refs(str(tmp_path), 'doc')
    assert any(r['resolved'] for r in refs)
    assert any(r['resolved'] is False for r in refs)


def test_component_refs_deduped_on_triple(tmp_path):
    # Two references to the same resolved target collapse to one triple.
    _write(tmp_path, 'doc/a.adoc', 'xref:b.adoc[one] then xref:b.adoc[two]\n')
    _write(tmp_path, 'doc/b.adoc', '= B\n')
    refs = build_doc_component_refs(str(tmp_path), 'doc')
    triples = {(r['target_bundle'], r['dep_type'], r['resolved']) for r in refs}
    assert len(triples) == len(refs)


def test_target_bundle_mapping_marketplace_and_doc(tmp_path):
    _write(
        tmp_path,
        'doc/a.adoc',
        'to a bundle: link:../marketplace/bundles/pm-dev-java/skills/x/SKILL.md[skill]\n'
        'to a doc: xref:b.adoc[doc]\n',
    )
    _write(tmp_path, 'doc/b.adoc', '= B\n')
    _write(tmp_path, 'marketplace/bundles/pm-dev-java/skills/x/SKILL.md', '# skill\n')
    refs = build_doc_component_refs(str(tmp_path), 'doc')
    targets = {r['target_bundle'] for r in refs}
    assert 'pm-dev-java' in targets
    assert 'documentation' in targets


def test_absent_doc_dir_yields_empty(tmp_path):
    assert build_doc_component_refs(str(tmp_path), 'doc') == []

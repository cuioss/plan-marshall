#!/usr/bin/env python3
"""Cross-file subcommand for verifying LLM cross-file analysis findings."""

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

SIMILARITY_VERIFICATION_TOLERANCE = 0.1
MIN_CONTENT_OVERLAP = 0.3


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]+`', '', text)
    text = re.sub(r'[#*_\[\]()]', '', text)
    text = re.sub(r'https?://\S+', '', text)
    return ' '.join(text.lower().split())


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two normalized texts."""
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    return SequenceMatcher(None, norm1, norm2).ratio()


def find_content_block(analysis: dict, file_path: str, section: str) -> dict | None:
    """Find a content block in the analysis by file and section."""
    for block in analysis.get('content_blocks', []):
        if block['file'] == file_path and block['section'] == section:
            result: dict = block
            return result
    return None


def verify_duplication_claim(claim: dict, analysis: dict, skill_path: Path) -> tuple[bool, str, dict]:
    """Verify a duplication claim from LLM analysis."""
    source = claim.get('source', {})
    target = claim.get('target', {})
    classification = claim.get('classification', '')

    source_block = find_content_block(analysis, source.get('file', ''), source.get('section', ''))
    target_block = find_content_block(analysis, target.get('file', ''), target.get('section', ''))

    if not source_block or not target_block:
        return (
            False,
            'content_blocks_not_found',
            {'source_found': source_block is not None, 'target_found': target_block is not None},
        )

    in_candidates = False
    reported_similarity = None

    for candidate in analysis.get('similarity_candidates', []):
        cand_source = candidate.get('source', {})
        cand_target = candidate.get('target', {})

        if (
            cand_source.get('file') == source.get('file')
            and cand_source.get('section') == source.get('section')
            and cand_target.get('file') == target.get('file')
            and cand_target.get('section') == target.get('section')
        ) or (
            cand_target.get('file') == source.get('file')
            and cand_target.get('section') == source.get('section')
            and cand_source.get('file') == target.get('file')
            and cand_source.get('section') == target.get('section')
        ):
            in_candidates = True
            reported_similarity = candidate.get('similarity')
            break

    in_exact = False
    for dup in analysis.get('exact_duplicates', []):
        files = [occ.get('file') for occ in dup.get('occurrences', [])]
        sections = [occ.get('section') for occ in dup.get('occurrences', [])]
        if (
            source.get('file') in files
            and target.get('file') in files
            and source.get('section') in sections
            and target.get('section') in sections
        ):
            in_exact = True
            break

    if classification == 'true_duplicate':
        if in_exact:
            return True, 'confirmed_exact_duplicate', {'verification_method': 'hash_match'}
        elif in_candidates and reported_similarity and reported_similarity >= 0.8:
            return (
                True,
                'confirmed_high_similarity',
                {'similarity': reported_similarity, 'verification_method': 'similarity_threshold'},
            )
        elif in_candidates:
            return (
                True,
                'confirmed_in_candidates',
                {'similarity': reported_similarity, 'note': 'LLM semantic judgment accepted'},
            )
        else:
            return False, 'not_in_analysis_candidates', {'in_exact': in_exact, 'in_similarity': in_candidates}

    elif classification == 'similar_concept':
        if in_candidates:
            return True, 'confirmed_similar_concept', {'similarity': reported_similarity}
        else:
            return False, 'pair_not_in_analysis', {}

    elif classification == 'false_positive':
        if in_candidates or in_exact:
            return True, 'false_positive_acknowledged', {'was_candidate': in_candidates, 'was_exact': in_exact}
        else:
            return False, 'not_a_candidate_to_reject', {}

    return False, 'unknown_classification', {'classification': classification}


def verify_extraction_claim(claim: dict, analysis: dict, skill_path: Path) -> tuple[bool, str, dict]:
    """Verify an extraction recommendation from LLM analysis."""
    file_path = claim.get('file', '')
    section = claim.get('section', '')
    claim_type = claim.get('type', '')
    recommendation = claim.get('recommendation', '')

    matching_candidate = None
    for candidate in analysis.get('extraction_candidates', []):
        if candidate.get('file') == file_path and candidate.get('section') == section:
            matching_candidate = candidate
            break

    if matching_candidate:
        if matching_candidate.get('type') == claim_type:
            return (
                True,
                'confirmed_extraction_candidate',
                {
                    'analysis_type': matching_candidate.get('type'),
                    'analysis_pattern': matching_candidate.get('pattern'),
                    'llm_recommendation': recommendation,
                },
            )
        else:
            return (
                True,
                'type_mismatch_but_candidate_exists',
                {'claimed_type': claim_type, 'analysis_type': matching_candidate.get('type')},
            )

    content_block = find_content_block(analysis, file_path, section)
    if content_block:
        return (
            True,
            'llm_identified_new_candidate',
            {'note': 'LLM found extraction opportunity not in script analysis', 'requires_manual_review': True},
        )

    return False, 'section_not_found', {'file': file_path, 'section': section}


def verify_terminology_claim(claim: dict, analysis: dict) -> tuple[bool, str, dict]:
    """Verify a terminology standardization claim from LLM analysis."""
    concept = claim.get('concept', '')
    standardized_term = claim.get('standardized_term', '')
    action = claim.get('action', '')

    matching_variant = None
    for variant in analysis.get('terminology_variants', []):
        if variant.get('concept', '').lower() == concept.lower():
            matching_variant = variant
            break

    if matching_variant:
        variant_terms = [v.get('term', '') for v in matching_variant.get('variants', [])]

        if action == 'standardize':
            if standardized_term.lower() in [t.lower() for t in variant_terms]:
                return (
                    True,
                    'confirmed_standardization',
                    {'available_variants': variant_terms, 'chosen_standard': standardized_term},
                )
            else:
                return (
                    True,
                    'standardization_term_not_in_variants',
                    {
                        'available_variants': variant_terms,
                        'chosen_standard': standardized_term,
                        'note': 'LLM may have chosen a better canonical form',
                    },
                )

        elif action == 'keep_variants':
            return True, 'confirmed_keep_variants', {'variants': variant_terms}

    if action == 'keep_variants':
        return True, 'no_variants_found_keeping', {}

    return False, 'concept_not_in_analysis', {'concept': concept}


def verify_findings(analysis: dict, llm_findings: dict) -> dict:
    """Main verification function that processes all LLM findings."""
    skill_path = Path(analysis.get('skill_path', ''))

    verified = []
    rejected = []
    warnings = []

    for claim in llm_findings.get('duplications', []):
        is_verified, reason, details = verify_duplication_claim(claim, analysis, skill_path)
        result = {'type': 'duplication', 'claim': claim, 'reason': reason, 'details': details}
        if is_verified:
            verified.append(result)
        else:
            rejected.append(result)

    for claim in llm_findings.get('extractions', []):
        is_verified, reason, details = verify_extraction_claim(claim, analysis, skill_path)
        result = {'type': 'extraction', 'claim': claim, 'reason': reason, 'details': details}
        if is_verified:
            verified.append(result)
            if details.get('requires_manual_review'):
                warnings.append(
                    {
                        'type': 'manual_review_needed',
                        'claim': claim,
                        'reason': 'LLM identified opportunity not in script analysis',
                    }
                )
        else:
            rejected.append(result)

    for claim in llm_findings.get('terminology', []):
        is_verified, reason, details = verify_terminology_claim(claim, analysis)
        result = {'type': 'terminology', 'claim': claim, 'reason': reason, 'details': details}
        if is_verified:
            verified.append(result)
        else:
            rejected.append(result)

    llm_addressed_pairs = set()
    for claim in llm_findings.get('duplications', []):
        source = claim.get('source', {})
        target = claim.get('target', {})
        pair = tuple(
            sorted([f'{source.get("file")}:{source.get("section")}', f'{target.get("file")}:{target.get("section")}'])
        )
        llm_addressed_pairs.add(pair)

    for candidate in analysis.get('similarity_candidates', []):
        source = candidate.get('source', {})
        target = candidate.get('target', {})
        pair = tuple(
            sorted([f'{source.get("file")}:{source.get("section")}', f'{target.get("file")}:{target.get("section")}'])
        )
        if pair not in llm_addressed_pairs:
            warnings.append(
                {
                    'type': 'unaddressed_candidate',
                    'candidate': candidate,
                    'reason': 'Similarity candidate not addressed by LLM',
                }
            )

    total_claims = (
        len(llm_findings.get('duplications', []))
        + len(llm_findings.get('extractions', []))
        + len(llm_findings.get('terminology', []))
    )

    verification_rate = len(verified) / total_claims * 100 if total_claims > 0 else 100.0

    return {
        'skill_path': str(skill_path),
        'verified': verified,
        'rejected': rejected,
        'warnings': warnings,
        'summary': {
            'total_claims': total_claims,
            'verified_count': len(verified),
            'rejected_count': len(rejected),
            'warning_count': len(warnings),
            'verification_rate': round(verification_rate, 1),
        },
    }


def cmd_cross_file(args) -> int:
    """Verify LLM cross-file analysis findings."""
    analysis_path = Path(args.analysis)
    if not analysis_path.exists():
        print(json.dumps({'error': f'Analysis file not found: {args.analysis}'}), file=sys.stderr)
        return 1

    try:
        with open(analysis_path, encoding='utf-8') as f:
            analysis = json.load(f)
    except json.JSONDecodeError as e:
        print(json.dumps({'error': f'Invalid JSON in analysis file: {str(e)}'}), file=sys.stderr)
        return 1

    if args.llm_findings:
        findings_path = Path(args.llm_findings)
        if not findings_path.exists():
            print(json.dumps({'error': f'LLM findings file not found: {args.llm_findings}'}), file=sys.stderr)
            return 1

        try:
            with open(findings_path, encoding='utf-8') as f:
                llm_findings = json.load(f)
        except json.JSONDecodeError as e:
            print(json.dumps({'error': f'Invalid JSON in LLM findings file: {str(e)}'}), file=sys.stderr)
            return 1
    else:
        try:
            llm_findings = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(json.dumps({'error': f'Invalid JSON from stdin: {str(e)}'}), file=sys.stderr)
            return 1

    try:
        result = verify_findings(analysis, llm_findings)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({'error': f'Verification failed: {str(e)}'}), file=sys.stderr)
        return 1

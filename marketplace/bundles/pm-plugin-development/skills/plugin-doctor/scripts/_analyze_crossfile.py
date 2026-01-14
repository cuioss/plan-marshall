#!/usr/bin/env python3
"""Cross-file content analysis subcommand."""

import hashlib
import json
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

# Constants
CONTENT_DIRS = ['references', 'workflows', 'templates']
DEFAULT_SIMILARITY_THRESHOLD = 0.4
EXACT_THRESHOLD = 0.95
MIN_SECTION_LENGTH = 100
MIN_PARAGRAPH_LENGTH = 50

PLACEHOLDER_PATTERNS = [
    r'\{\{[A-Z_]+\}\}',
    r'\{[a-z_]+\}',
    r'\[INSERT [A-Z]+\]',
    r'<[A-Z_]+>',
]

WORKFLOW_PATTERNS = [
    r'^###?\s+Step\s+\d+',
    r'^###?\s+Phase\s+\d+',
    r'^\d+\.\s+\*\*[^*]+\*\*:',
]

TERM_PATTERNS = {
    'definition': r'\*\*([^*]+)\*\*:',
    'header': r'^#{2,4}\s+(.+)$',
    'emphasized': r'\*([^*]+)\*',
    'backtick': r'`([^`]+)`',
}

KNOWN_SYNONYM_GROUPS = [
    {'cross-reference', 'xref', 'internal link', 'cross-ref'},
    {'workflow', 'process', 'procedure', 'protocol'},
    {'must', 'shall', 'required', 'mandatory'},
    {'should', 'recommended', 'advisable'},
    {'may', 'optional', 'can'},
    {'skill', 'plugin', 'component'},
    {'agent', 'assistant', 'bot'},
    {'command', 'slash command', 'directive'},
]


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]+`', '', text)
    text = re.sub(r'[#*_\[\]()]', '', text)
    text = re.sub(r'https?://\S+', '', text)
    return ' '.join(text.lower().split())


def compute_hash(text: str) -> str:
    """Compute SHA256 hash of normalized text."""
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]


def extract_sections(content: str, file_path: str) -> list[dict]:
    """Extract sections from markdown content."""
    sections: list[dict] = []
    lines = content.split('\n')
    current_header = '_intro'
    current_level = 0
    current_start_line = 1
    current_content_lines: list[str] = []

    for i, line in enumerate(lines, 1):
        header_match = re.match(r'^(#{2,4})\s+(.+)$', line)
        if header_match:
            if current_content_lines:
                section_text = '\n'.join(current_content_lines)
                if len(section_text.strip()) >= MIN_SECTION_LENGTH:
                    sections.append(
                        {
                            'header': current_header,
                            'level': current_level,
                            'start_line': current_start_line,
                            'end_line': i - 1,
                            'text': section_text,
                            'content_hash': compute_hash(section_text),
                            'normalized_length': len(normalize_text(section_text)),
                            'content_lines': current_content_lines,
                        }
                    )

            current_header = header_match.group(2).strip()
            current_level = len(header_match.group(1))
            current_start_line = i
            current_content_lines = []
        else:
            current_content_lines.append(line)

    if current_content_lines:
        section_text = '\n'.join(current_content_lines)
        if len(section_text.strip()) >= MIN_SECTION_LENGTH:
            sections.append(
                {
                    'header': current_header,
                    'level': current_level,
                    'start_line': current_start_line,
                    'end_line': len(lines),
                    'text': section_text,
                    'content_hash': compute_hash(section_text),
                    'normalized_length': len(normalize_text(section_text)),
                    'content_lines': current_content_lines,
                }
            )

    return sections


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two normalized texts."""
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    return SequenceMatcher(None, norm1, norm2).ratio()


def find_exact_duplicates(all_sections: list[dict]) -> list[dict]:
    """Find exact duplicates using content hashes."""
    hash_groups: dict[str, list[dict]] = defaultdict(list)

    for section in all_sections:
        content_hash = section.get('content_hash')
        if content_hash:
            hash_groups[content_hash].append(section)

    duplicates = []
    for content_hash, sections in hash_groups.items():
        if len(sections) > 1:
            duplicates.append(
                {
                    'hash': content_hash,
                    'occurrences': [
                        {'file': s['file'], 'section': s['header'], 'lines': f'{s["start_line"]}-{s["end_line"]}'}
                        for s in sections
                    ],
                    'line_count': sections[0]['end_line'] - sections[0]['start_line'] + 1,
                    'content_preview': normalize_text(sections[0]['text'])[:200] + '...',
                    'recommendation': 'consolidate',
                }
            )

    return duplicates


def find_similarity_candidates(all_sections: list[dict], threshold: float, exact_hashes: set[str]) -> list[dict]:
    """Find sections with similarity between threshold and EXACT_THRESHOLD."""
    candidates: list[dict] = []
    processed_pairs: set[tuple[str, str]] = set()

    for i, section1 in enumerate(all_sections):
        if section1.get('content_hash') in exact_hashes:
            continue

        for _j, section2 in enumerate(all_sections[i + 1 :], i + 1):
            if section1['file'] == section2['file']:
                continue

            if section2.get('content_hash') in exact_hashes:
                continue

            pair_items: list[str] = sorted(
                [f'{section1["file"]}:{section1["header"]}', f'{section2["file"]}:{section2["header"]}']
            )
            pair_id: tuple[str, str] = (pair_items[0], pair_items[1])

            if pair_id in processed_pairs:
                continue
            processed_pairs.add(pair_id)

            similarity = calculate_similarity(section1['text'], section2['text'])

            if threshold <= similarity < EXACT_THRESHOLD:
                candidates.append(
                    {
                        'source': {
                            'file': section1['file'],
                            'section': section1['header'],
                            'lines': f'{section1["start_line"]}-{section1["end_line"]}',
                        },
                        'target': {
                            'file': section2['file'],
                            'section': section2['header'],
                            'lines': f'{section2["start_line"]}-{section2["end_line"]}',
                        },
                        'similarity': round(similarity, 3),
                        'llm_analysis_required': True,
                    }
                )

    candidates.sort(key=lambda x: float(x['similarity']), reverse=True)
    return candidates


def detect_extraction_candidates(all_sections: list[dict]) -> list[dict]:
    """Detect content that should be extracted to templates or workflows."""
    candidates = []

    for section in all_sections:
        text = section.get('text', '')

        placeholders_found = []
        for pattern in PLACEHOLDER_PATTERNS:
            matches = re.findall(pattern, text)
            placeholders_found.extend(matches)

        if placeholders_found:
            candidates.append(
                {
                    'type': 'template',
                    'pattern': 'placeholder_structure',
                    'file': section['file'],
                    'section': section['header'],
                    'lines': f'{section["start_line"]}-{section["end_line"]}',
                    'detected_placeholders': list(set(placeholders_found)),
                    'recommendation': 'extract_to_templates',
                }
            )
            continue

        workflow_indicators = 0
        for pattern in WORKFLOW_PATTERNS:
            workflow_indicators += len(re.findall(pattern, text, re.MULTILINE))

        if workflow_indicators >= 3:
            candidates.append(
                {
                    'type': 'workflow',
                    'pattern': 'step_sequence',
                    'file': section['file'],
                    'section': section['header'],
                    'lines': f'{section["start_line"]}-{section["end_line"]}',
                    'step_count': workflow_indicators,
                    'recommendation': 'extract_to_workflows',
                }
            )

    return candidates


def extract_terminology(all_sections: list[dict]) -> dict[str, dict[str, int]]:
    """Extract terminology from content and group by file."""
    terms_by_file: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for section in all_sections:
        file_path = section['file']
        text = section.get('text', '')

        for _term_type, pattern in TERM_PATTERNS.items():
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                term = match.strip().lower()
                if 2 < len(term) < 50:
                    terms_by_file[file_path][term] += 1

    return terms_by_file


def find_terminology_variants(terms_by_file: dict[str, dict[str, int]]) -> list[dict]:
    """Find terminology variants using known synonym groups."""
    variants = []

    for synonym_group in KNOWN_SYNONYM_GROUPS:
        found_variants: dict[str, list[tuple[str, int]]] = defaultdict(list)

        for file_path, terms in terms_by_file.items():
            for term, count in terms.items():
                term_lower = term.lower()
                for synonym in synonym_group:
                    if synonym in term_lower or term_lower in synonym:
                        found_variants[term].append((file_path, count))
                        break

        if len(found_variants) > 1:
            variant_list: list[dict[str, object]] = []
            for term, occurrences in found_variants.items():
                files = [occ[0] for occ in occurrences]
                total_count = sum(occ[1] for occ in occurrences)
                variant_list.append({'term': term, 'files': list(set(files)), 'count': total_count})

            if variant_list:
                most_common = max(variant_list, key=lambda x: x['count'] if isinstance(x['count'], int) else 0)
                variants.append(
                    {
                        'concept': list(synonym_group)[0],
                        'variants': variant_list,
                        'recommendation': f"standardize on '{most_common['term']}'",
                    }
                )

    return variants


def analyze_cross_file(skill_path: Path, similarity_threshold: float) -> dict:
    """Main cross-file analysis function."""
    skill_name = skill_path.name
    all_sections = []
    files_analyzed = 0
    total_lines = 0

    for content_dir in CONTENT_DIRS:
        dir_path = skill_path / content_dir
        if not dir_path.exists():
            continue

        for md_file in dir_path.glob('**/*.md'):
            try:
                content = md_file.read_text(encoding='utf-8')
                rel_path = str(md_file.relative_to(skill_path))
                files_analyzed += 1
                total_lines += len(content.split('\n'))

                sections = extract_sections(content, rel_path)
                for section in sections:
                    section['file'] = rel_path
                all_sections.extend(sections)

            except OSError:
                continue

    content_blocks = [
        {
            'id': f'{s["file"]}:{s["header"]}'.replace('/', ':').replace(' ', '-').lower(),
            'file': s['file'],
            'section': s['header'],
            'lines': f'{s["start_line"]}-{s["end_line"]}',
            'content_hash': s.get('content_hash', ''),
            'normalized_length': s.get('normalized_length', 0),
        }
        for s in all_sections
    ]

    exact_duplicates = find_exact_duplicates(all_sections)
    exact_hashes = {d['hash'] for d in exact_duplicates}

    similarity_candidates = find_similarity_candidates(all_sections, similarity_threshold, exact_hashes)

    extraction_candidates = detect_extraction_candidates(all_sections)

    terms_by_file = extract_terminology(all_sections)
    terminology_variants = find_terminology_variants(terms_by_file)

    llm_review_required = (
        len(similarity_candidates) > 0 or len(extraction_candidates) > 0 or len(terminology_variants) > 0
    )

    return {
        'skill_path': str(skill_path),
        'skill_name': skill_name,
        'files_analyzed': files_analyzed,
        'total_lines': total_lines,
        'content_blocks': content_blocks,
        'exact_duplicates': exact_duplicates,
        'similarity_candidates': similarity_candidates,
        'extraction_candidates': extraction_candidates,
        'terminology_variants': terminology_variants,
        'summary': {
            'exact_duplicate_pairs': len(exact_duplicates),
            'similarity_candidates': len(similarity_candidates),
            'extraction_candidates': len(extraction_candidates),
            'terminology_issues': len(terminology_variants),
            'llm_review_required': llm_review_required,
        },
    }


def cmd_cross_file(args) -> int:
    """Analyze cross-file content in skill directory."""
    skill_path = Path(args.skill_path)

    if not skill_path.exists():
        print(json.dumps({'error': f'Skill path not found: {args.skill_path}'}), file=sys.stderr)
        return 1

    if not skill_path.is_dir():
        print(json.dumps({'error': f'Skill path is not a directory: {args.skill_path}'}), file=sys.stderr)
        return 1

    try:
        result = analyze_cross_file(skill_path, args.similarity_threshold)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({'error': f'Analysis failed: {str(e)}'}), file=sys.stderr)
        return 1

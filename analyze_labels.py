#!/usr/bin/env python3
"""
Analyze git history of OWL/TWONTO.ttl to find the top 10 rdfs:label values
that have experienced the most changes across all commits.
"""

import subprocess
import re
from collections import defaultdict


def get_commits(repo_path, file_path):
    """Get all commit hashes for the given file."""
    result = subprocess.run(
        ["git", "-C", repo_path, "log", "--format=%H", "--", file_path],
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip().split("\n")


def get_file_content(repo_path, commit_hash, file_path):
    """Get file content at a specific commit."""
    result = subprocess.run(
        ["git", "-C", repo_path, "show", f"{commit_hash}:{file_path}"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    return result.stdout


def parse_labels(content):
    """
    Parse all rdfs:label triples from a TTL file content.
    Returns a dict mapping subject_iri -> set of label values.

    Handles:
      - Full IRI subjects like <http://...#Something>
      - Prefixed subjects like :SomeThing or twonto:SomeThing
      - Multi-line label values
      - Language tags like "label"@en
    """
    subject_labels = {}  # subject_iri -> label_value (only latest label per subject)

    # We'll parse the file line by line, tracking the current subject
    current_subject = None
    lines = content.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Detect subject declarations: lines starting with < (full IRI) or :word or prefix:word
        # A new subject block starts with a line like:
        #   <http://...> rdf:type ... or
        #   :LocalName rdf:type ... or
        #   prefix:LocalName rdf:type ...
        # Also look for ### comment lines which precede subject declarations

        # Match a full IRI subject
        full_iri_match = re.match(r'^(<[^>]+>)\s+', stripped)
        # Match a prefixed/local subject (colon-prefixed, e.g. :name or prefix:name)
        prefix_match = re.match(r'^((?:[a-zA-Z_][a-zA-Z0-9_-]*)?:[a-zA-Z_][a-zA-Z0-9_#.-]*)\s+', stripped)

        if full_iri_match:
            candidate = full_iri_match.group(1)
            # It's a subject if this is not a property value line (i.e., not after a predicate)
            # We consider lines that do NOT start with whitespace as new subject declarations
            if not line.startswith((' ', '\t')):
                current_subject = candidate
        elif prefix_match and not line.startswith((' ', '\t')):
            candidate = prefix_match.group(1)
            # Exclude lines that look like they're predicates (rdf:type, rdfs:subClassOf, etc.)
            common_predicates = {
                'rdf:type', 'rdfs:subClassOf', 'rdfs:subPropertyOf',
                'rdfs:domain', 'rdfs:range', 'rdfs:label', 'rdfs:comment',
                'owl:equivalentClass', 'owl:equivalentProperty',
                'owl:inverseOf', 'owl:deprecated', 'owl:versionIRI',
                'owl:onProperty', 'owl:someValuesFrom', 'owl:allValuesFrom',
                'owl:unionOf', 'owl:intersectionOf', 'owl:complementOf',
            }
            if candidate not in common_predicates:
                current_subject = candidate

        # Look for rdfs:label on this line
        # Pattern: rdfs:label "..." or rdfs:label "..."@lang or rdfs:label "..."^^type
        label_match = re.search(r'rdfs:label\s+"((?:[^"\\]|\\.)*)"\s*(?:@[a-z]+)?\s*[;.]?\s*$', stripped)
        if not label_match:
            # Try multi-line label (triple quotes not expected but let's handle)
            label_start = re.search(r'rdfs:label\s+"((?:[^"\\]|\\.)*)"', stripped)
            if label_start:
                label_value = label_start.group(1)
                if current_subject:
                    subject_labels[current_subject] = label_value
        else:
            label_value = label_match.group(1)
            if current_subject:
                subject_labels[current_subject] = label_value

        i += 1

    return subject_labels


def analyze_label_changes(repo_path, file_path):
    """
    Analyze git history to find labels that changed the most.
    Returns a dict: subject_iri -> list of (commit_hash, label_value) tuples
    """
    commits = get_commits(repo_path, file_path)
    print(f"Found {len(commits)} commits for {file_path}")

    # commits are from newest to oldest; reverse to process oldest->newest
    commits_ordered = list(reversed(commits))

    # For each commit, get all subject->label mappings
    all_commit_labels = []
    for idx, commit in enumerate(commits_ordered):
        content = get_file_content(repo_path, commit, file_path)
        if content is None:
            print(f"  Warning: could not read {file_path} at commit {commit[:8]}")
            all_commit_labels.append((commit, {}))
            continue
        labels = parse_labels(content)
        all_commit_labels.append((commit, labels))
        if (idx + 1) % 10 == 0 or idx == 0 or idx == len(commits_ordered) - 1:
            print(f"  Processed commit {idx+1}/{len(commits_ordered)}: {commit[:8]} ({len(labels)} labels found)")

    # Track changes per subject
    # subject -> list of (from_commit, to_commit, old_label, new_label)
    subject_changes = defaultdict(list)

    for i in range(1, len(all_commit_labels)):
        prev_commit, prev_labels = all_commit_labels[i - 1]
        curr_commit, curr_labels = all_commit_labels[i]

        # Find all subjects that appear in either version
        all_subjects = set(prev_labels.keys()) | set(curr_labels.keys())

        for subject in all_subjects:
            old_label = prev_labels.get(subject)
            new_label = curr_labels.get(subject)

            if old_label != new_label:
                subject_changes[subject].append({
                    "from_commit": prev_commit[:8],
                    "to_commit": curr_commit[:8],
                    "old_label": old_label,
                    "new_label": new_label,
                })

    return subject_changes


def main():
    repo_path = "/home/user/TWONTO"
    file_path = "OWL/TWONTO.ttl"

    print("=" * 80)
    print("Analyzing rdfs:label changes in git history of OWL/TWONTO.ttl")
    print("=" * 80)
    print()

    subject_changes = analyze_label_changes(repo_path, file_path)

    print()
    print(f"Total subjects with at least one label change: {len(subject_changes)}")
    print()

    # Sort by number of changes (descending)
    sorted_subjects = sorted(subject_changes.items(), key=lambda x: len(x[1]), reverse=True)

    print("=" * 80)
    print("TOP 20 rdfs:label values that changed the most")
    print("=" * 80)

    for rank, (subject, changes) in enumerate(sorted_subjects[:20], start=1):
        print()
        print(f"Rank #{rank}: {subject}")
        print(f"  Total changes: {len(changes)}")
        print(f"  Change history (oldest to newest):")
        for ch in changes:
            old = repr(ch['old_label']) if ch['old_label'] is not None else "(not present)"
            new = repr(ch['new_label']) if ch['new_label'] is not None else "(removed)"
            print(f"    [{ch['from_commit']} -> {ch['to_commit']}]  {old}  =>  {new}")

    print()
    print("=" * 80)
    print("Summary table (top 20 subjects by number of label changes):")
    print("=" * 80)
    print(f"{'Rank':<5} {'Changes':<8} {'Subject IRI'}")
    print("-" * 80)
    for rank, (subject, changes) in enumerate(sorted_subjects[:20], start=1):
        print(f"{rank:<5} {len(changes):<8} {subject}")


if __name__ == "__main__":
    main()

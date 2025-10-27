#!/usr/bin/env python3

"""
Simple utility to check if all links in vault point to existing targets.
Parses link-mapping.txt file and reports broken links.

Usage:
python link_validator.py <link_mapping_file> <vault_path>
"""

import os
import re
import sys
from typing import Dict, List

def parse_link_mapping(link_mapping_file: str) -> List[Dict]:
    """
    Parse link mapping file to extract all links.

    Args:
        link_mapping_file: Path to link mapping file
        
    Returns:
        List[Dict]: List of link dictionaries
    """
    links = []

    try:
        with open(link_mapping_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Parse format: "SOURCE ; TARGET ; HASH"
                parts = line.split(' ; ')
                if len(parts) >= 2:
                    source_file = parts[0].strip()
                    target_file = parts[1].strip()
                    
                    links.append({
                        'source': source_file,
                        'target': target_file,
                        'line': line
                    })
    except Exception as e:
        print(f"Error reading link mapping file: {e}")
        return []

    return links


def check_links_exist(links: List[Dict], vault_path: str) -> Dict:
    """
    Check if all link targets exist in the vault.

    Args:
        links: List of link dictionaries
        vault_path: Path to the vault
        
    Returns:
        Dict: Report with statistics and broken links
    """
    existing_links = []
    broken_links = []

    for link in links:
        target_path = os.path.join(vault_path, link['target'])
        
        if os.path.exists(target_path):
            existing_links.append(link)
        else:
            broken_links.append(link)

    return {
        'total_links': len(links),
        'existing_links': len(existing_links),
        'broken_links': len(broken_links),
        'broken_details': broken_links
    }

def extract_links_from_markdown(vault_path: str) -> List[str]:
    """
    Extract all link targets from markdown files in the vault.

    Args:
        vault_path: Path to the vault
        
    Returns:
        List[str]: List of all link targets found
    """
    all_targets = set()

    for root, dirs, files in os.walk(vault_path):
        # Skip dot-prefixed directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Extract wikilinks: [[filename]] or [[filename|display]]
                        wikilinks = re.findall(r'\[\[([^\]]+)\]\]', content)
                        for link in wikilinks:
                            parts = link.split('|', 1)
                            filename = parts[0]
                            all_targets.add(filename)
                        
                        # Extract markdown links: [text](filename.md) or [text](path/filename.md)
                        markdown_links = re.findall(r'\[([^\]]*)\]\(([^)]+)\)', content)
                        for link in markdown_links:
                            all_targets.add(link)
                
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")

    return list(all_targets)


def generate_quick_report(link_mapping_file: str, vault_path: str) -> None:
    """
    Generate a quick report of link status.

    Args:
        link_mapping_file: Path to link mapping file
        vault_path: Path to the vault
    """
    print(f"Analyzing links in vault: {vault_path}")
    print(f"Using link mapping file: {link_mapping_file}")
    print("=" * 60)

    # Parse link mapping
    links = parse_link_mapping(link_mapping_file)
    if not links:
        print("No links found in mapping file")
        return

    # Check link existence
    report = check_links_exist(links, vault_path)

    # Extract links from markdown files for comparison
    markdown_targets = extract_links_from_markdown(vault_path)

    print(f"Links in mapping file: {report['total_links']}")
    print(f"Links pointing to existing files: {report['existing_links']}")
    print(f"Links pointing to missing files: {report['broken_links']}")
    print(f"Unique targets found in markdown files: {len(set(markdown_targets))}")

    if report['broken_links'] > 0:
        print("\nBROKEN LINKS:")
        for broken_link in report['broken_details']:
            print(f"  Source: {broken_link['source']}")
            print(f"  Target: {broken_link['target']}")
            print(f"  Line: {broken_link['line']}")
            print()

    # Find targets in markdown that aren't in mapping
    mapped_targets = {link['target'] for link in links}
    unmapped_targets = [target for target in set(markdown_targets) if target not in mapped_targets]

    if unmapped_targets:
        print(f"\nTARGETS IN MARKDOWN NOT IN MAPPING FILE ({len(unmapped_targets)}):")
        for target in unmapped_targets[:10]:  # Show first 10
            print(f"  {target}")
        if len(unmapped_targets) > 10:
            print(f"  ... and {len(unmapped_targets) - 10} more")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    if report['broken_links'] == 0:
        print("✓ All links in mapping file point to existing files")
    else:
        print(f"⚠ {report['broken_links']} broken links found")

    print(f"Vault contains {len(set(markdown_targets))} unique link targets")
    print(f"Mapping file contains {len(set(mapped_targets))} unique targets")


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python link_validator.py <link_mapping_file> <vault_path>")
        sys.exit(1)

    link_mapping_file = sys.argv[1]
    vault_path = sys.argv[2] if len(sys.argv) > 2 else '.'

    if not os.path.exists(link_mapping_file):
        print(f"Error: Link mapping file '{link_mapping_file}' not found")
        sys.exit(1)

    if not os.path.exists(vault_path):
        print(f"Error: Vault path '{vault_path}' not found")
        sys.exit(1)

    generate_quick_report(link_mapping_file, vault_path)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3

"""
Utility to find duplicate files based on hash codes in link mapping files.
This is part of the Obsidian vault merger toolset.
"""

import re
import sys
from collections import defaultdict
from typing import Dict, List, Tuple


def extract_hash_from_path(file_path: str) -> str:
    """
    Extract hash code from a file path.
    
    Args:
        file_path (str): File path potentially containing a hash
        
    Returns:
        str: Extracted hash code or empty string if not found
    """
    # Match patterns like .1.webp, .1.png, .abc123.jpg, etc.
    hash_match = re.search(r'\.(\w+)\.(?:webp|png|jpg|jpeg|svg|pdf|gif)$', file_path)
    if hash_match:
        return hash_match.group(1)
    
    # Match patterns like .1, .abc123 at the end of the path
    hash_match = re.search(r'\.(\w+)$', file_path)
    if hash_match:
        return hash_match.group(1)
    
    return ""


def parse_link_mapping(file_path: str) -> Dict[str, List[str]]:
    """
    Parse link mapping file and group file paths by their hash codes.
    
    Args:
        file_path (str): Path to the link mapping file
        
    Returns:
        Dict[str, List[str]]: Dictionary mapping hash codes to lists of file paths
    """
    hash_to_paths = defaultdict(list)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Split line into file path and metadata
                parts = line.split(' <- ')
                if len(parts) < 2:
                    continue
                
                file_path_part = parts[0].strip()
                hash_code = extract_hash_from_path(file_path_part)
                
                if hash_code:
                    hash_to_paths[hash_code].append(file_path_part)
                    
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        return {}
    except Exception as e:
        print(f"Error reading file: {e}")
        return {}
    
    return hash_to_paths


def find_duplicate_files(hash_to_paths: Dict[str, List[str]]) -> List[Tuple[str, List[str]]]:
    """
    Find all hash codes that have multiple file paths (duplicates).
    
    Args:
        hash_to_paths (Dict[str, List[str]]): Dictionary mapping hash codes to file paths
        
    Returns:
        List[Tuple[str, List[str]]]: List of tuples containing hash codes and their duplicate file paths
    """
    duplicates = []
    for hash_code, paths in hash_to_paths.items():
        if len(paths) > 1:
            duplicates.append((hash_code, paths))
    
    # Sort by number of duplicates (descending)
    duplicates.sort(key=lambda x: len(x[1]), reverse=True)
    
    return duplicates


def print_duplicate_report(duplicates: List[Tuple[str, List[str]]], limit: int = 20) -> None:
    """
    Print a report of duplicate files.
    
    Args:
        duplicates (List[Tuple[str, List[str]]]): List of duplicate file groups
        limit (int): Maximum number of entries to display
    """
    print(f"Found {len(duplicates)} hash codes with duplicate files:")
    print("=" * 60)
    
    for i, (hash_code, paths) in enumerate(duplicates[:limit]):
        print(f"\n{i+1}. Hash: {hash_code} ({len(paths)} duplicates)")
        for path in paths[:5]:  # Show max 5 paths per hash
            print(f"   - {path}")
        if len(paths) > 5:
            print(f"   ... and {len(paths) - 5} more")


def main():
    """Main function to find and report duplicate files."""
    if len(sys.argv) != 2:
        print("Usage: python find_duplicate_files.py <link_mapping_file>")
        sys.exit(1)
    
    link_mapping_file = sys.argv[1]
    
    print(f"Parsing link mapping file: {link_mapping_file}")
    hash_to_paths = parse_link_mapping(link_mapping_file)
    
    if not hash_to_paths:
        print("No hash codes found in the link mapping file.")
        return
    
    print(f"Found {len(hash_to_paths)} unique hash codes.")
    
    duplicates = find_duplicate_files(hash_to_paths)
    
    if not duplicates:
        print("No duplicate files found.")
        return
    
    print_duplicate_report(duplicates)
    
    # Summary
    total_duplicate_hashes = len(duplicates)
    total_duplicate_files = sum(len(paths) for _, paths in duplicates)
    total_extra_files = total_duplicate_files - total_duplicate_hashes  # Excluding one instance per hash
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Hash codes with duplicates: {total_duplicate_hashes}")
    print(f"Total duplicate file instances: {total_duplicate_files}")
    print(f"Extra file instances (duplicates): {total_extra_files}")


if __name__ == "__main__":
    main()
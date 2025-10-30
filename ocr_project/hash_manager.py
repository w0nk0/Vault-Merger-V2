"""
Hash Manager for v0.2 - Calculate and check SHA-256 hashes.

Implements hash-based duplicate detection per Issue #2 specifications.
"""

import hashlib
import os
from pathlib import Path
import re


def calculate_image_hash(image_path):
    """
    Calculate SHA-256 hash of image file.
    
    Args:
        image_path: Path to image file
        
    Returns:
        str: First 8 characters of SHA-256 hash (per RULES.md)
    """
    sha256_hash = hashlib.sha256()
    
    with open(image_path, 'rb') as f:
        # Read file in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    
    full_hash = sha256_hash.hexdigest()
    return full_hash[:8]  # First 8 characters per RULES.md


def find_hash_in_filenames(hash_value, search_directory):
    """
    Search for hash value in filenames within directory.
    
    Args:
        hash_value: 8-character hash to search for
        search_directory: Directory to search in
        
    Returns:
        list: List of files containing the hash in their filename
    """
    matching_files = []
    hash_lower = hash_value.lower()
    
    search_path = Path(search_directory)
    if not search_path.exists():
        return matching_files
    
    # Walk through all files
    for file_path in search_path.rglob('*'):
        if file_path.is_file():
            filename = file_path.name
            # Check if hash appears in filename (case-insensitive)
            if hash_lower in filename.lower():
                matching_files.append(str(file_path))
    
    return matching_files


def is_ocr_file(filename):
    """
    Check if filename matches OCR-generated file pattern.
    
    Pattern: {original_name}_OCR_{hash}.md
    
    Args:
        filename: Filename to check
        
    Returns:
        bool: True if filename matches OCR pattern
    """
    # Pattern: anything_OCR_8hexchars.md
    pattern = r'.*_OCR_[0-9a-fA-F]{8}\.md$'
    return bool(re.match(pattern, filename))


def check_duplicate(hash_value, output_directory):
    """
    Check if hash exists in existing files and determine action.
    
    Per Issue #2 logic:
    - If found in OCR file: Skip processing
    - If found in non-OCR file: Continue processing (hash collision)
    
    Args:
        hash_value: 8-character hash to check
        output_directory: Directory to search for duplicates
        
    Returns:
        dict: {
            'is_duplicate': bool,
            'found_in_ocr': bool,
            'existing_files': list of matching files,
            'action': 'skip' or 'continue'
        }
    """
    result = {
        'is_duplicate': False,
        'found_in_ocr': False,
        'existing_files': [],
        'action': 'continue'
    }
    
    matching_files = find_hash_in_filenames(hash_value, output_directory)
    
    if not matching_files:
        return result
    
    result['existing_files'] = matching_files
    result['is_duplicate'] = True
    
    # Check if any matching file is an OCR-generated file
    for file_path in matching_files:
        filename = os.path.basename(file_path)
        if is_ocr_file(filename):
            result['found_in_ocr'] = True
            result['action'] = 'skip'
            return result
    
    # Hash found but not in OCR file - continue processing
    result['action'] = 'continue'
    return result


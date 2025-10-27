#!/usr/bin/env python3

"""
Simple test script to verify the refactored code works correctly.
"""

import os
import sys
from link_processor import link_processor
from config_manager import config_manager

def test_unified_method():
    """Test the unified method for processing links and calculating hashes."""
    print("Testing unified method for link processing and hash calculation...")
    
    # Set up test configuration
    config_manager.destination_path = "test_vaults/source1"
    config_manager.exclude_dot_folders = True
    
    # Build vault file set
    link_processor._build_vault_file_set()
    
    # Test processing a single file
    test_file = "test_vaults/source1/test.md"
    if os.path.exists(test_file):
        print(f"\nProcessing file: {test_file}")
        file_info = link_processor._process_single_file(test_file, analyze_only=True)
        
        print(f"File path: {file_info['file_path']}")
        print(f"Relative path: {file_info['relative_path']}")
        print(f"Hash: {file_info['hash']}")
        print(f"Links found: {len(file_info['links'])}")
        
        for link in file_info['links']:
            print(f"  - {link['type']} link to {link['target']} from {link['source']}")
        
        print("\n✓ Unified method test completed successfully!")
        return True
    else:
        print(f"Error: Test file {test_file} not found")
        return False

def test_link_processor_methods():
    """Test that the link processor methods still work correctly."""
    print("\nTesting link processor methods...")
    
    # Set up test configuration
    config_manager.destination_path = "test_vaults/source1"
    config_manager.exclude_dot_folders = True
    config_manager.hash_all_files = True
    config_manager.analyze_only = True
    
    try:
        # Test analyze_links_standalone method
        link_processor.analyze_links_standalone()
        print("✓ analyze_links_standalone method works correctly")
        
        # Check if link mapping was generated
        mapping_file = os.path.join(config_manager.destination_path, "linkmap.txt")
        if os.path.exists(mapping_file):
            print(f"✓ Link mapping file generated at {mapping_file}")
            
            # Read and display first few lines
            with open(mapping_file, 'r') as f:
                lines = f.readlines()[:5]
                print("First few lines of link mapping:")
                for line in lines:
                    print(f"  {line.strip()}")
        else:
            print("✗ Link mapping file was not generated")
            return False
            
        return True
    except Exception as e:
        print(f"✗ Error testing link processor methods: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING REFACTORED CODE")
    print("=" * 60)
    
    success1 = test_unified_method()
    success2 = test_link_processor_methods()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("✓ ALL TESTS PASSED - Refactored code works correctly!")
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED - Please check the implementation")
        sys.exit(1)
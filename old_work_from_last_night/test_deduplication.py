#!/usr/bin/env python3

"""
Test suite for deduplication functionality.
Creates test vaults, runs merge and deduplication, and verifies results.
"""

import os
import shutil
import sys
from pathlib import Path


def create_test_vault(path: str, files: dict) -> None:
    """Create a test vault with the specified files."""
    os.makedirs(path, exist_ok=True)
    for rel_path, content in files.items():
        file_path = os.path.join(path, rel_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)


def setup_test_vaults() -> tuple:
    """Set up test vault A and B with duplicate content files."""
    
    # Clean up old test vaults
    test_dir = Path("test_deduplication_vaults")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    
    # Create test vault A
    vault_a = test_dir / "vault_a"
    vault_a_files = {
        "readme.md": "# Vault A\n\nThis is vault A.",
        "notes/project-alpha.md": "# Project Alpha\n\nThis project is important.\n\nSee [[project-beta]] for more info.",
        "notes/project-beta.md": "# Project Beta\n\nThis is a related project.\n\nSee [[project-alpha]] for more info.",
        "notes/ideas.md": "# Ideas\n\nSome great ideas here.\n\n## Idea 1\nThis is a great idea!\n\nSee [[notes/summary]]",
        "notes/summary.md": "# Summary\n\nThis is the summary.\n\nBack to [[notes/ideas]]",
        "images/logo.png": "DUMMY_IMAGE_DATA",
    }
    create_test_vault(str(vault_a), vault_a_files)
    
    # Create test vault B with DUPLICATE CONTENT files (different names)
    vault_b = test_dir / "vault_b"
    vault_b_files = {
        "readme.md": "# Vault B\n\nThis is vault B.",
        # This will have the SAME content as vault_a/notes/project-alpha.md
        "notes/project-alpha-backup.md": "# Project Alpha\n\nThis project is important.\n\nSee [[project-beta]] for more info.",
        # This will have the SAME content as vault_a/notes/ideas.md
        "notes/ideas-copy.md": "# Ideas\n\nSome great ideas here.\n\n## Idea 1\nThis is a great idea!\n\nSee [[notes/summary]]",
        "notes/other-ideas.md": "# Other Ideas\n\nDifferent content here.",
        "archive/old-meeting.md": "# Old Meeting\n\nMeeting notes.",
    }
    create_test_vault(str(vault_b), vault_b_files)
    
    # Create destination vault
    vault_dest = test_dir / "merged_vault"
    os.makedirs(str(vault_dest), exist_ok=True)
    
    print("✓ Created test vaults")
    print(f"  - Vault A: {vault_a}")
    print(f"  - Vault B: {vault_b}")
    print(f"  - Destination: {vault_dest}")
    
    return str(vault_a), str(vault_b), str(vault_dest)


def run_merge(source_a: str, source_b: str, dest: str) -> None:
    """Run the merge process with hash calculation."""
    import subprocess
    
    print("\n" + "="*60)
    print("Running Merge Process")
    print("="*60)
    
    cmd = [
        sys.executable, "main.py",
        source_a, source_b,
        "-d", dest,
        "--hash-all-files"
    ]
    
    print(f"Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("\n--- STDOUT ---")
    print(result.stdout)
    
    if result.stderr:
        print("\n--- STDERR ---")
        print(result.stderr)
    
    print(f"\nReturn code: {result.returncode}")
    
    if result.returncode != 0:
        print("ERROR: Merge failed!")
        sys.exit(1)


def run_deduplication(vault_path: str) -> None:
    """Run deduplication on the merged vault."""
    import subprocess
    
    print("\n" + "="*60)
    print("Running Deduplication")
    print("="*60)
    
    cmd = [
        sys.executable, "main.py",
        vault_path,
        "--analyze-only",
        "--deduplicate"
    ]
    
    print(f"Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("\n--- STDOUT ---")
    print(result.stdout)
    
    if result.stderr:
        print("\n--- STDERR ---")
        print(result.stderr)
    
    print(f"\nReturn code: {result.returncode}")
    
    if result.returncode != 0:
        print("ERROR: Deduplication failed!")
        sys.exit(1)


def verify_results(vault_path: str) -> None:
    """Verify that deduplication worked correctly."""
    print("\n" + "="*60)
    print("Verifying Results")
    print("="*60)
    
    issues = []
    
    # Check that duplicate files were renamed
    notes_dir = os.path.join(vault_path, "notes")
    if os.path.exists(notes_dir):
        files = os.listdir(notes_dir)
        
        # Check for renamed duplicates
        duplicate_files = [f for f in files if f.startswith("dup-")]
        if duplicate_files:
            print(f"\n✓ Found {len(duplicate_files)} renamed duplicate files:")
            for f in duplicate_files:
                print(f"  - {f}")
        else:
            issues.append("No duplicate files were renamed")
    
    # Check linkmap.txt exists
    linkmap_path = os.path.join(vault_path, "linkmap.txt")
    if not os.path.exists(linkmap_path):
        issues.append("linkmap.txt not found")
    else:
        print(f"\n✓ Found linkmap.txt")
        
        # Count entries
        with open(linkmap_path, 'r') as f:
            lines = [l.strip() for l in f if l.strip()]
            print(f"  - Total entries: {len(lines)}")
    
    # Check that files with identical content exist
    # We should have original files still present
    expected_files = [
        "readme.md",  # Should exist (no collision)
        "readme~1.md",  # From collision resolution
        "notes/project-alpha.md",  # Should be survivor
        "notes/project-alpha-backup.md",  # Should be renamed to dup-
    ]
    
    print("\n" + "="*60)
    print("File Existence Check")
    print("="*60)
    
    for expected_file in expected_files:
        full_path = os.path.join(vault_path, expected_file)
        if os.path.exists(full_path):
            print(f"✓ {expected_file}")
        else:
            # Try with dup- prefix
            dup_path = os.path.join(vault_path, f"dup-{os.path.basename(expected_file)}")
            if os.path.exists(dup_path):
                print(f"✓ {expected_file} (renamed to dup-)")
            else:
                print(f"✗ {expected_file} (NOT FOUND)")
                issues.append(f"Missing file: {expected_file}")
    
    # Summary
    print("\n" + "="*60)
    if issues:
        print("VERIFICATION FAILED")
        print("="*60)
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("VERIFICATION PASSED")
        print("="*60)
        return True


def main():
    """Run the complete test suite."""
    print("="*60)
    print("DEDUPLICATION TEST SUITE")
    print("="*60)
    
    # Step 1: Setup test vaults
    print("\nStep 1: Setting up test vaults...")
    source_a, source_b, dest = setup_test_vaults()
    
    # Step 2: Run merge
    print("\nStep 2: Running merge...")
    run_merge(source_a, source_b, dest)
    
    # Step 3: Run deduplication
    print("\nStep 3: Running deduplication...")
    run_deduplication(dest)
    
    # Step 4: Verify results
    print("\nStep 4: Verifying results...")
    success = verify_results(dest)
    
    print("\n" + "="*60)
    if success:
        print("TEST SUITE COMPLETED SUCCESSFULLY")
    else:
        print("TEST SUITE FAILED")
    print("="*60)
    
    print(f"\nTest vaults location: {os.path.abspath('test_deduplication_vaults')}")
    print("\nYou can inspect the merged vault at:")
    print(f"  {os.path.abspath(dest)}")


if __name__ == "__main__":
    main()


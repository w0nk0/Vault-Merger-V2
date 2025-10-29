#!/usr/bin/env python3

"""
Integration test for merge + deduplication workflow.
Simple test to verify the complete process works.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    print("="*60)
    print("INTEGRATION TEST: Merge + Deduplication")
    print("="*60)
    
    # Setup
    test_dir = Path("test_integration")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    
    test_dir.mkdir()
    vault_a = test_dir / "vault_a"
    vault_b = test_dir / "vault_b"  
    dest = test_dir / "merged"
    
    # Create test vault A
    (vault_a / "notes").mkdir(parents=True)
    (vault_a / "readme.md").write_text("# Vault A\n\nContent from vault A.")
    (vault_a / "notes" / "meeting.md").write_text("# Meeting\n\nSame meeting notes.")
    
    # Create test vault B with duplicate content
    (vault_b / "notes").mkdir(parents=True)
    (vault_b / "readme.md").write_text("# Vault B\n\nContent from vault B.")
    # This has SAME content as vault_a/notes/meeting.md
    (vault_b / "notes" / "meeting-backup.md").write_text("# Meeting\n\nSame meeting notes.")
    
    print("\n✓ Created test vaults:")
    print(f"  - Vault A: {vault_a}")
    print(f"  - Vault B: {vault_b}")
    print(f"  - Destination: {dest}")
    
    # Run merge
    print("\n" + "="*60)
    print("Step 1: Merging vaults")
    print("="*60)
    
    cmd_merge = [
        sys.executable, "main.py",
        str(vault_a), str(vault_b),
        "-d", str(dest),
        "--hash-all-files"
    ]
    
    print(f"\nRunning: {' '.join(cmd_merge)}\n")
    result = subprocess.run(cmd_merge, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("ERROR: Merge failed")
        print(result.stderr)
        sys.exit(1)
    
    print("✓ Merge completed")
    
    # Run deduplication
    print("\n" + "="*60)
    print("Step 2: Deduplicating")
    print("="*60)
    
    cmd_dedup = [
        sys.executable, "main.py",
        str(dest),
        "--analyze-only",
        "--deduplicate"
    ]
    
    print(f"\nRunning: {' '.join(cmd_dedup)}\n")
    result = subprocess.run(cmd_dedup, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("ERROR: Deduplication failed")
        print(result.stderr)
        sys.exit(1)
    
    print("✓ Deduplication completed")
    
    # Verify results
    print("\n" + "="*60)
    print("Step 3: Verifying Results")
    print("="*60)
    
    # Check for survivor
    meeting_md = dest / "notes" / "meeting.md"
    if meeting_md.exists():
        print("✓ Survivor 'meeting.md' exists")
    else:
        print("✗ Survivor 'meeting.md' not found")
        sys.exit(1)
    
    # Check for renamed duplicates
    notes_dir = dest / "notes"
    duplicates = [f for f in notes_dir.iterdir() if f.name.startswith("dup-")]
    
    if len(duplicates) >= 1:
        print(f"✓ Found {len(duplicates)} renamed duplicate(s):")
        for dup in duplicates:
            print(f"  - {dup.name}")
    else:
        print("✗ No duplicate files renamed")
        sys.exit(1)
    
    # Check linkmap exists
    linkmap = dest / "linkmap.txt"
    if linkmap.exists():
        print("✓ linkmap.txt exists")
        
        # Read and show entries
        with open(linkmap) as f:
            lines = [l.strip() for l in f if l.strip()]
            print(f"  - {len(lines)} entries")
    else:
        print("✗ linkmap.txt not found")
        sys.exit(1)
    
    # Summary
    print("\n" + "="*60)
    print("INTEGRATION TEST PASSED")
    print("="*60)
    print(f"\nTest results in: {os.path.abspath(dest)}")
    print("\nFiles in merged vault:")
    for root, dirs, files in os.walk(dest):
        level = root.replace(str(dest), '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f"{subindent}{file}")


if __name__ == "__main__":
    main()


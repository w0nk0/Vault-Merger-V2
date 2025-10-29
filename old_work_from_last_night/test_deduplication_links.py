#!/usr/bin/env python3

"""
Test for deduplication link updates.
Creates test vaults with files linking to duplicates and verifies links are updated.
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


def create_test_with_links() -> tuple:
    """Create test vaults with files linking to duplicates."""
    
    # Clean up
    test_dir = Path("test_link_deduplication")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    
    # Create a single vault with duplicate content and links
    vault = test_dir / "test_vault"
    
    # Content that will be duplicated
    duplicate_content = "# About\n\nThis is about our company.\n\nWe are awesome!"
    
    vault_files = {
        # Original file (will be survivor - shortest name)
        "company.md": duplicate_content,
        
        # Duplicate 1 (will be renamed to dup-)
        "company-backup-2023.md": duplicate_content,
        
        # Duplicate 2 (will be renamed to dup-)
        "company-backup-2024.md": duplicate_content,
        
        # Files that link to the duplicates
        "index.md": """# Index

Welcome to our site.

- [[company]] - About our company
- [[company-backup-2023]] - Backup info
- See [company info](company-backup-2024.md)
""",
        
        "readme.md": """# Readme

Check out [[company]] for company details.
""",
        
        "products.md": """# Products

[[company-backup-2023]] has more info.
""",
    }
    
    create_test_vault(str(vault), vault_files)
    
    # Create destination
    vault_dest = test_dir / "deduplicated_vault"
    os.makedirs(str(vault_dest), exist_ok=True)
    
    print(f"✓ Created test vault: {vault}")
    print(f"✓ Destination: {vault_dest}")
    
    return str(vault), str(vault_dest)


def run_analysis_and_dedup(vault_path: str) -> None:
    """Run hash analysis and deduplication."""
    import subprocess
    
    print("\n" + "="*60)
    print("Running Analysis and Deduplication")
    print("="*60)
    
    # First, analyze the vault to generate hash values
    cmd1 = [
        sys.executable, "main.py",
        vault_path,
        "--analyze-only"
    ]
    
    print(f"\nStep 1: Hash analysis")
    print(f"Command: {' '.join(cmd1)}")
    result1 = subprocess.run(cmd1, capture_output=True, text=True)
    print(result1.stdout)
    
    # Copy vault for deduplication
    dest = os.path.join(vault_path, "..", "deduplicated_vault")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(vault_path, dest)
    
    # Then run deduplication
    cmd2 = [
        sys.executable, "main.py",
        dest,
        "--analyze-only",
        "--deduplicate"
    ]
    
    print(f"\nStep 2: Deduplication")
    print(f"Command: {' '.join(cmd2)}")
    result2 = subprocess.run(cmd2, capture_output=True, text=True)
    print(result2.stdout)
    
    return result2.returncode == 0


def verify_links(vault_path: str) -> None:
    """Verify that links were updated correctly."""
    print("\n" + "="*60)
    print("Verifying Link Updates")
    print("="*60)
    
    issues = []
    
    # Check company.md should be survivor
    company_md = os.path.join(vault_path, "company.md")
    if not os.path.exists(company_md):
        issues.append("company.md (survivor) not found")
    else:
        print("✓ company.md exists (survivor)")
    
    # Check duplicates were renamed
    duplicate_files = []
    for f in os.listdir(vault_path):
        if f.startswith("dup-") and "company" in f:
            duplicate_files.append(f)
    
    if len(duplicate_files) >= 2:
        print(f"✓ Found {len(duplicate_files)} renamed duplicate files:")
        for f in duplicate_files:
            print(f"  - {f}")
    else:
        issues.append(f"Expected 2+ renamed duplicates, found {len(duplicate_files)}")
    
    # Check links in index.md
    index_md = os.path.join(vault_path, "index.md")
    if os.path.exists(index_md):
        with open(index_md, 'r') as f:
            content = f.read()
            
        # All links to duplicates should NOW point to "company" (survivor)
        # Check that OLD duplicate links are GONE
        if "[[company-backup-2023]]" in content:
            issues.append("Link to duplicate not updated in index.md")
            print("✗ Link to company-backup-2023 still exists in index.md")
        else:
            print("✓ Link to company-backup-2023 removed/updated")
        
        if "[[company-backup-2024]]" in content:
            issues.append("Link to duplicate not updated in index.md")
            print("✗ Link to company-backup-2024 still exists in index.md")
        else:
            print("✓ Link to company-backup-2024 removed/updated")
        
        # Check that links to the SURVIVOR exist
        if "[[company]]" in content:
            print("✓ Link to survivor (company) exists in index.md")
        else:
            issues.append("Link to survivor missing in index.md")
        
        # Check that markdown links were also updated
        if "(company-backup-2024.md)" in content:
            issues.append("Markdown link not updated")
            print("✗ Markdown link to company-backup-2024.md still exists")
        elif "(company.md)" in content or "(company)" in content:
            print("✓ Markdown link updated to point to survivor")
    
    # Check links in readme.md
    readme_md = os.path.join(vault_path, "readme.md")
    if os.path.exists(readme_md):
        with open(readme_md, 'r') as f:
            content = f.read()
        
        if "[[company-backup-2023]]" in content:
            issues.append("Link to duplicate not updated in readme.md")
        elif "[[company]]" in content:
            print("✓ Link updated in readme.md")
    
    # Summary
    print("\n" + "="*60)
    if issues:
        print("LINK VERIFICATION FAILED")
        print("="*60)
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("LINK VERIFICATION PASSED")
        print("="*60)
        return True


def main():
    """Run the link update test."""
    print("="*60)
    print("LINK UPDATE TEST")
    print("="*60)
    
    # Setup
    source, dest = create_test_with_links()
    
    # Run analysis and deduplication
    success = run_analysis_and_dedup(source)
    
    if not success:
        print("ERROR: Deduplication failed")
        sys.exit(1)
    
    # Verify
    success = verify_links(dest)
    
    print("\n" + "="*60)
    if success:
        print("LINK UPDATE TEST PASSED")
    else:
        print("LINK UPDATE TEST FAILED")
    print("="*60)
    
    print(f"\nTest vault: {os.path.abspath(dest)}")


if __name__ == "__main__":
    main()


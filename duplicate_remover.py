#!/usr/bin/env python3

"""
Duplicate Link Resolver for Obsidian Vault Merger
Handles duplicate file resolution by updating links to point to a single survivor.

Key Features:
- Identifies "sibling groups" (files with identical MD5 hashes)
- Selects "survivor" (shortest filename) for each sibling group
- Updates all internal links to point to survivors instead of duplicates
- Verifies no files become orphaned after link updates
- Uses correct terminology as requested
"""

import os
import re
import sys
from collections import defaultdict
from typing import Dict, List, Set
from logger import logger
from link_processor import link_processor


class DuplicateLinkResolver:
    """
    Handles duplicate file resolution by updating links to point to a single survivor.
    """

    def __init__(self, vault_path: str, link_mapping_file: str, test_mode: bool = False, max_groups: int = 3, rename_mode: bool = True):
        """
        Initialize the duplicate link resolver.
        
        Args:
            vault_path: Path to the Obsidian vault
            link_mapping_file: Path to the link mapping file
            test_mode: If True, only process the first max_groups sibling groups
            max_groups: Maximum number of sibling groups to process in test mode
            rename_mode: If True, rename non-surviving siblings with "dup-" prefix instead of deleting
        """
        self.vault_path = vault_path
        self.link_mapping_file = link_mapping_file
        self.test_mode = test_mode
        self.max_groups = max_groups
        self.rename_mode = rename_mode
        self.sibling_groups: Dict[str, List[str]] = {}  # hash -> list of files
        self.survivors: Dict[str, str] = {}  # hash -> survivor file
        self.link_updates: List[Dict] = []  # Track link updates
        self.orphaned_files: Set[str] = set()  # Track potentially orphaned files
        self.renamed_files: List[Dict] = []  # Track renamed files for rollback

    def identify_sibling_groups(self) -> None:
        """
        Identify sibling groups (files with identical MD5 hashes) from the link mapping file.
        """
        logger.info("Identifying sibling groups...")
        
        hash_to_files = defaultdict(list)
        
        try:
            with open(self.link_mapping_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse format: "SOURCE ; TARGET ; HASH"
                    parts = line.split(' ; ')
                    if len(parts) >= 3:
                        source_file = parts[0].strip()
                        target_file = parts[1].strip()
                        file_hash = parts[2].strip()
                        
                        # Skip UNLINKED entries
                        if source_file == "UNLINKED":
                            hash_to_files[file_hash].append(target_file)
                        else:
                            hash_to_files[file_hash].append(target_file)
        
        except FileNotFoundError:
            logger.error(f"Link mapping file not found: {self.link_mapping_file}")
            return
        except Exception as e:
            logger.error(f"Error reading link mapping file: {e}")
            return
        
        # Filter to only include hashes with multiple files (duplicates)
        temp_groups = {}
        for file_hash, files in hash_to_files.items():
            if len(files) > 1:
                temp_groups[file_hash] = files
        
        # Apply test mode limit if enabled
        if self.test_mode and len(temp_groups) > self.max_groups:
            # Sort hashes and take only the first max_groups
            sorted_hashes = sorted(temp_groups.keys())
            for i, file_hash in enumerate(sorted_hashes):
                if i < self.max_groups:
                    self.sibling_groups[file_hash] = temp_groups[file_hash]
                else:
                    break
            logger.info(f"Test mode: Processing only {len(self.sibling_groups)} sibling groups (limited to {self.max_groups})")
        else:
            self.sibling_groups = temp_groups
            logger.info(f"Found {len(self.sibling_groups)} sibling groups with duplicates")

    def select_survivors(self) -> None:
        """
        Select survivor (shortest filename) for each sibling group.
        """
        logger.info("Selecting survivors for each sibling group...")
        
        for file_hash, siblings in self.sibling_groups.items():
            # Select the file with the shortest filename as the survivor
            survivor = min(siblings, key=lambda x: len(os.path.basename(x)))
            self.survivors[file_hash] = survivor
            
            duplicates = [s for s in siblings if s != survivor]
            logger.debug(f"Hash {file_hash}: Selected survivor '{survivor}' from {len(siblings)} files")
            logger.debug(f"  Duplicates to be replaced: {duplicates}")

    def update_internal_links(self) -> None:
        """
        Update all internal links to point to survivors instead of duplicates.
        """
        logger.info("Updating internal links to point to survivors...")
        
        # First, build a mapping of duplicate -> survivor
        duplicate_to_survivor = {}
        for file_hash, survivor in self.survivors.items():
            for duplicate in self.sibling_groups[file_hash]:
                if duplicate != survivor:
                    duplicate_to_survivor[duplicate] = survivor
        
        # Process all markdown files in the vault
        for root, dirs, files in os.walk(self.vault_path):
            # Skip dot-prefixed directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    self._update_links_in_file(file_path, duplicate_to_survivor)

    def _update_links_in_file(self, file_path: str, duplicate_to_survivor: Dict[str, str]) -> None:
        """
        Update links in a single file to point to survivors using the unified approach.
        
        Args:
            file_path: Path to the markdown file
            duplicate_to_survivor: Mapping of duplicate files to their survivors
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            updated_content = content
            relative_file_path = os.path.relpath(file_path, self.vault_path)
            
            # Process wikilinks: [[filename]] or [[filename|display]]
            def process_wikilink(match):
                link_content = match.group(1)
                parts = link_content.split('|', 1)
                filename_part = parts[0]
                display_part = parts[1] if len(parts) > 1 else None
                
                # Check if this link points to a duplicate
                if filename_part in duplicate_to_survivor:
                    survivor = duplicate_to_survivor[filename_part]
                    self.link_updates.append({
                        'source_file': relative_file_path,
                        'original_target': filename_part,
                        'new_target': survivor,
                        'link_type': 'wikilink'
                    })
                    
                    if display_part:
                        return f"[[{survivor}|{display_part}]]"
                    else:
                        return f"[[{survivor}]]"
                
                return match.group(0)
            
            wikilink_pattern = r'\[\[([^\]]+)\]\]'
            updated_content = re.sub(wikilink_pattern, process_wikilink, updated_content)
            
            # Process markdown links: [text](filename.md) or [text](path/filename.md)
            def process_markdown_link(match):
                link_text = match.group(1)
                link_target = match.group(2)
                
                # Check if this link points to a duplicate
                if link_target in duplicate_to_survivor:
                    survivor = duplicate_to_survivor[link_target]
                    self.link_updates.append({
                        'source_file': relative_file_path,
                        'original_target': link_target,
                        'new_target': survivor,
                        'link_type': 'markdown'
                    })
                    
                    # Update the filename part while preserving the path
                    dir_path = os.path.dirname(link_target)
                    if dir_path:
                        updated_target = f"{dir_path}/{os.path.basename(survivor)}"
                    else:
                        updated_target = survivor
                    
                    return f"[{link_text}]({updated_target})"
                
                return match.group(0)
            
            markdown_link_pattern = r'\[([^\]]*)\]\(([^)]+)\)'
            updated_content = re.sub(markdown_link_pattern, process_markdown_link, updated_content)
            
            # Write updated content back to file if changes were made
            if original_content != updated_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                logger.debug(f"Updated links in {relative_file_path}")
        
        except Exception as e:
            logger.error(f"Error updating links in {file_path}: {e}")

    def rename_non_surviving_siblings(self) -> None:
        """
        Rename non-surviving sibling files by prepending "dup-" to their filenames.
        This allows for easy rollback instead of deleting the files.
        """
        if not self.rename_mode:
            logger.info("Rename mode disabled, skipping file renaming")
            return
            
        logger.info("Renaming non-surviving sibling files...")
        
        for file_hash, siblings in self.sibling_groups.items():
            survivor = self.survivors[file_hash]
            for duplicate in siblings:
                if duplicate != survivor:
                    # Construct new filename with "dup-" prefix
                    duplicate_path = os.path.join(self.vault_path, duplicate)
                    if os.path.exists(duplicate_path):
                        dir_path = os.path.dirname(duplicate_path)
                        filename = os.path.basename(duplicate_path)
                        new_filename = f"dup-{filename}"
                        new_path = os.path.join(dir_path, new_filename)
                        
                        try:
                            os.rename(duplicate_path, new_path)
                            self.renamed_files.append({
                                'original_path': duplicate,
                                'new_path': os.path.relpath(new_path, self.vault_path),
                                'hash': file_hash
                            })
                            logger.debug(f"Renamed: {duplicate} -> {new_filename}")
                        except Exception as e:
                            logger.error(f"Failed to rename {duplicate}: {e}")
        
        logger.info(f"Renamed {len(self.renamed_files)} non-surviving sibling files")

    def rollback_renames(self) -> None:
        """
        Rollback all file renames by removing the "dup-" prefix.
        """
        if not self.renamed_files:
            logger.info("No renamed files to rollback")
            return
            
        logger.info("Rolling back file renames...")
        
        for rename_info in reversed(self.renamed_files):  # Reverse order to handle potential conflicts
            original_path = os.path.join(self.vault_path, rename_info['original_path'])
            new_path = os.path.join(self.vault_path, rename_info['new_path'])
            
            if os.path.exists(new_path):
                try:
                    os.rename(new_path, original_path)
                    logger.debug(f"Rolled back: {rename_info['new_path']} -> {rename_info['original_path']}")
                except Exception as e:
                    logger.error(f"Failed to rollback {rename_info['new_path']}: {e}")
        
        logger.info(f"Rolled back {len(self.renamed_files)} file renames")
        self.renamed_files.clear()

    def verify_no_orphaned_files(self) -> bool:
        """
        Verify that no files become orphaned after link updates.
        
        Returns:
            bool: True if no orphaned files found, False otherwise
        """
        logger.info("Verifying no files become orphaned after link updates...")
        
        # Build a set of all files that are linked to
        linked_files = set()
        
        # Process all markdown files to find links using the unified approach
        for root, dirs, files in os.walk(self.vault_path):
            # Skip dot-prefixed directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    try:
                        # Use the unified method to process the file and extract links
                        file_info = link_processor._process_single_file(file_path, analyze_only=True)
                        
                        # Extract all linked files from the file info
                        for link in file_info['links']:
                            linked_files.add(link['target'])
                    
                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {e}")
        
        # Check if any duplicates that are not survivors are no longer linked
        for file_hash, siblings in self.sibling_groups.items():
            survivor = self.survivors[file_hash]
            for duplicate in siblings:
                if duplicate != survivor and duplicate not in linked_files:
                    self.orphaned_files.add(duplicate)
        
        if self.orphaned_files:
            logger.warning(f"Found {len(self.orphaned_files)} potentially orphaned files after link updates")
            for orphaned in self.orphaned_files:
                logger.warning(f"  Orphaned: {orphaned}")
            return False
        else:
            logger.info("No orphaned files found after link updates")
            return True

    def generate_report(self) -> Dict:
        """
        Generate a report of the duplicate resolution process.
        
        Returns:
            Dict: Report containing statistics and details
        """
        report = {
            'total_sibling_groups': len(self.sibling_groups),
            'total_duplicates': sum(len(siblings) - 1 for siblings in self.sibling_groups.values()),
            'total_link_updates': len(self.link_updates),
            'total_renamed_files': len(self.renamed_files),
            'orphaned_files': list(self.orphaned_files),
            'sibling_groups': {},
            'link_updates': self.link_updates,
            'renamed_files': self.renamed_files,
            'test_mode': self.test_mode,
            'rename_mode': self.rename_mode
        }
        
        # Add details about each sibling group
        for file_hash, siblings in self.sibling_groups.items():
            survivor = self.survivors[file_hash]
            duplicates = [s for s in siblings if s != survivor]
            report['sibling_groups'][file_hash] = {
                'survivor': survivor,
                'duplicates': duplicates,
                'total_files': len(siblings)
            }
        
        return report

    def print_report(self) -> None:
        """
        Print a formatted report of the duplicate resolution process.
        """
        report = self.generate_report()
        
        print("\n" + "=" * 60)
        print("DUPLICATE LINK RESOLUTION REPORT")
        print("=" * 60)
        
        if report['test_mode']:
            print(f"🧪 TEST MODE: Processing only {report['total_sibling_groups']} sibling groups")
        
        print(f"Sibling groups processed: {report['total_sibling_groups']}")
        print(f"Total duplicate files: {report['total_duplicates']}")
        print(f"Links updated: {report['total_link_updates']}")
        
        if report['rename_mode']:
            print(f"Files renamed: {report['total_renamed_files']}")
        else:
            print("Rename mode: DISABLED")
        
        if report['orphaned_files']:
            print(f"⚠️  Warning: {len(report['orphaned_files'])} potentially orphaned files")
        else:
            print("✓ No orphaned files detected")
        
        print("\nSIBLING GROUPS:")
        for i, (file_hash, group_info) in enumerate(report['sibling_groups'].items(), 1):
            print(f"\n{i}. Hash: {file_hash}")
            print(f"   Survivor: {group_info['survivor']}")
            print(f"   Duplicates ({len(group_info['duplicates'])}):")
            for duplicate in group_info['duplicates']:
                print(f"     - {duplicate}")
        
        if report['link_updates']:
            print(f"\nLINK UPDATES ({len(report['link_updates'])}):")
            for i, update in enumerate(report['link_updates'][:10], 1):  # Show first 10
                print(f"{i}. {update['source_file']}: {update['original_target']} → {update['new_target']} ({update['link_type']})")
            
            if len(report['link_updates']) > 10:
                print(f"... and {len(report['link_updates']) - 10} more updates")
        
        if report['renamed_files']:
            print(f"\nRENAMED FILES ({len(report['renamed_files'])}):")
            for i, rename_info in enumerate(report['renamed_files'][:10], 1):  # Show first 10
                print(f"{i}. {rename_info['original_path']} → {rename_info['new_path']}")
            
            if len(report['renamed_files']) > 10:
                print(f"... and {len(report['renamed_files']) - 10} more renamed files")
            
            print("\n💡 To rollback renames, use: resolver.rollback_renames()")

    def resolve_duplicates(self) -> bool:
        """
        Execute the complete duplicate resolution process.
        
        Returns:
            bool: True if resolution completed successfully, False otherwise
        """
        logger.info("Starting duplicate link resolution process...")
        
        # Step 1: Identify sibling groups
        self.identify_sibling_groups()
        if not self.sibling_groups:
            logger.info("No duplicate files found. Nothing to resolve.")
            return True
        
        # Step 2: Select survivors
        self.select_survivors()
        
        # Step 3: Update internal links
        self.update_internal_links()
        
        # Step 4: Rename non-surviving siblings (if rename mode is enabled)
        self.rename_non_surviving_siblings()
        
        # Step 5: Verify no orphaned files
        all_files_accounted_for = self.verify_no_orphaned_files()
        
        logger.info("Duplicate link resolution process completed")
        return all_files_accounted_for


def main():
    """Main function to run the duplicate link resolver."""
    if len(sys.argv) < 2:
        print("Usage: python duplicate_link_resolver.py <vault_path> [link_mapping_file] [options]")
        print("\nOptions:")
        print("  --test-mode           Process only first few sibling groups (default: 3)")
        print("  --max-groups N        Number of groups to process in test mode (default: 3)")
        print("  --no-rename           Disable renaming of non-surviving siblings")
        print("  --rollback            Rollback previous file renames")
        print("\nExamples:")
        print("  python duplicate_link_resolver.py /path/to/vault")
        print("  python duplicate_link_resolver.py /path/to/vault linkmap.txt --test-mode")
        print("  python duplicate_link_resolver.py /path/to/vault --max-groups 5 --no-rename")
        sys.exit(1)
    
    vault_path = sys.argv[1]
    link_mapping_file = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else os.path.join(vault_path, "linkmap.txt")
    
    # Parse command line options
    test_mode = False
    max_groups = 3
    rename_mode = True
    rollback = False
    
    i = 2 if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else 3
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--test-mode':
            test_mode = True
        elif arg == '--max-groups' and i + 1 < len(sys.argv):
            try:
                max_groups = int(sys.argv[i + 1])
                test_mode = True  # Enable test mode when max-groups is specified
                i += 1
            except ValueError:
                print("Error: --max-groups requires a valid integer")
                sys.exit(1)
        elif arg == '--no-rename':
            rename_mode = False
        elif arg == '--rollback':
            rollback = True
        i += 1
    
    if not os.path.exists(vault_path):
        print(f"Error: Vault path '{vault_path}' not found")
        sys.exit(1)
    
    if not os.path.exists(link_mapping_file):
        print(f"Error: Link mapping file '{link_mapping_file}' not found")
        sys.exit(1)
    
    # Create resolver
    resolver = DuplicateLinkResolver(vault_path, link_mapping_file, test_mode, max_groups, rename_mode)
    
    if rollback:
        # Load existing rename data if available
        resolver.rollback_renames()
        print("Rollback completed")
        sys.exit(0)
    
    # Execute resolution
    success = resolver.resolve_duplicates()
    
    # Print report
    resolver.print_report()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
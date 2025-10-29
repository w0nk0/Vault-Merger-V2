#!/usr/bin/env python3

"""
Deduplication Handler for Obsidian Vault Merger
Handles deduplication of files with identical content based on hash values.

This module:
- Identifies files with identical hashes (siblings)
- Selects survivors (files to keep)
- Updates all links to point to survivors
- Renames or deletes non-surviving files
"""

import os
import re
import hashlib
from typing import Dict, List, Set, Tuple
from collections import defaultdict
from config_manager import config_manager
from logger import logger


class DeduplicationHandler:
    """
    Handles deduplication of files with identical content based on hash values.
    """

    def __init__(self):
        self.vault_path: str = ""
        self.link_mapping_file: str = ""
        self.sibling_groups: Dict[str, List[str]] = {}  # hash -> list of files
        self.survivors: Dict[str, str] = {}  # hash -> survivor file
        self.duplicate_to_survivor: Dict[str, str] = {}  # duplicate -> survivor
        self.renamed_files: List[Dict] = []
        self.updated_links_count: int = 0
        self.link_updates: List[Dict] = []  # Detailed tracking of link updates
        self.processed: bool = False

    def initialize(self) -> None:
        """Initialize the deduplication handler with current configuration."""
        self.vault_path = config_manager.destination_path
        self.link_mapping_file = os.path.join(self.vault_path, "linkmap.txt")

        # Check if link mapping file exists
        if not os.path.exists(self.link_mapping_file):
            logger.warning(f"Link mapping file not found: {self.link_mapping_file}")
            logger.warning("Skipping deduplication. Run with --hash-all-files to generate link mapping first.")
            self.processed = True
            return

        logger.info("Deduplication handler initialized")

    def identify_sibling_groups(self) -> None:
        """
        Read link mapping file and group files with identical hashes (siblings).
        
        Format: "SOURCE ; TARGET ; HASH"
        """
        logger.info("Identifying sibling groups (files with identical hashes)...")
        
        hash_to_files = defaultdict(set)  # Use set to avoid duplicates
        
        try:
            with open(self.link_mapping_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse format: "SOURCE ; TARGET ; HASH"
                    parts = line.split(' ; ')
                    if len(parts) >= 3:
                        target_file = parts[1].strip()
                        file_hash = parts[2].strip()
                        
                        # Only process valid hashes
                        if file_hash and file_hash not in ("ERROR", "NOT_FOUND", "unknown"):
                            hash_to_files[file_hash].add(target_file)
            
            # Filter to only include hashes with multiple files (duplicates)
            for file_hash, files in hash_to_files.items():
                if len(files) > 1:
                    self.sibling_groups[file_hash] = sorted(list(files))  # Sort for consistent survivor selection
                    logger.debug(f"Sibling group {file_hash[:8]}...: {list(files)}")
            
            logger.info(f"Found {len(self.sibling_groups)} sibling groups with duplicates")
            
        except FileNotFoundError:
            logger.error(f"Link mapping file not found: {self.link_mapping_file}")
        except Exception as e:
            logger.error(f"Error reading link mapping file: {e}")

    def select_survivors(self) -> None:
        """
        Select survivors for each sibling group.
        Strategy: Choose the file with the shortest filename.
        """
        logger.info("Selecting survivors for each sibling group...")
        
        for file_hash, siblings in self.sibling_groups.items():
            # Select the file with the shortest filename as survivor
            survivor = min(siblings, key=lambda x: len(os.path.basename(x)))
            self.survivors[file_hash] = survivor
            
            # Build duplicate_to_survivor mapping
            for sibling in siblings:
                if sibling != survivor:
                    self.duplicate_to_survivor[sibling] = survivor
                    logger.debug(f"Mapping: '{sibling}' -> '{survivor}'")
            
            duplicates = [s for s in siblings if s != survivor]
            logger.debug(f"Hash {file_hash[:8]}...: Survivor='{survivor}', Duplicates={duplicates}")

    def update_internal_links(self) -> None:
        """
        Update all internal links to point to survivors instead of duplicates.
        Processes both wikilinks and markdown links.
        """
        logger.info("Updating internal links to point to survivors...")
        
        if not self.duplicate_to_survivor:
            logger.info("No duplicates to update links for")
            return
        
        logger.debug(f"duplicate_to_survivor mapping: {self.duplicate_to_survivor}")
        
        # Process all markdown files in the vault
        for root, dirs, files in os.walk(self.vault_path):
            # Skip dot-prefixed directories
            dirs[:] = [d for d in dirs if not (config_manager.exclude_dot_folders and d.startswith('.'))]
            
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    try:
                        self._update_links_in_file(file_path)
                    except Exception as e:
                        logger.error(f"Error updating links in {file_path}: {e}")
        
        logger.info(f"Updated {self.updated_links_count} links across all files")

    def _update_links_in_file(self, file_path: str) -> None:
        """
        Update links in a single file to point to survivors.
        
        Args:
            file_path: Path to the markdown file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            updated_content = content
            relative_path = os.path.relpath(file_path, self.vault_path)
            
            # Process wikilinks: [[filename]] or [[filename|display]]
            def process_wikilink(match):
                link_content = match.group(1)
                parts = link_content.split('|', 1)
                filename_part = parts[0].strip()
                display_part = parts[1] if len(parts) > 1 else None
                
                # Normalize paths - remove ../ prefix if present
                normalized_filename = filename_part
                if normalized_filename.startswith('../'):
                    normalized_filename = normalized_filename[3:]  # Remove '../'
                
                # Normalize filename_part by removing extension if present
                filename_without_ext = os.path.splitext(filename_part)[0]
                normalized_without_ext = os.path.splitext(normalized_filename)[0]
                filename_with_ext = filename_part if filename_part.endswith('.md') else filename_part + '.md'
                
                # Check if this link points to a duplicate
                # Build variations to try
                try_variations = [
                    filename_part,
                    normalized_filename,
                    filename_with_ext,
                    filename_without_ext,
                    normalized_without_ext,
                    filename_without_ext + '.md',
                ]
                
                matched_key = None
                survivor = None
                
                # Try direct key match first
                for variant in try_variations:
                    if variant in self.duplicate_to_survivor:
                        matched_key = variant
                        break
                
                # If no direct match, try basename matching
                if not matched_key:
                    for key in self.duplicate_to_survivor.keys():
                        key_basename_no_ext = os.path.splitext(os.path.basename(key))[0]
                        key_basename_with_ext = os.path.basename(key)
                        
                        # Check if filenames match (with or without extension)
                        if (filename_without_ext == key_basename_no_ext or 
                            filename_part == key_basename_with_ext or
                            filename_with_ext == key_basename_with_ext or
                            filename_without_ext == key_basename_with_ext[:-3] if key_basename_with_ext.endswith('.md') else False):
                            matched_key = key
                            break
                
                if matched_key:
                    survivor = self.duplicate_to_survivor[matched_key]
                    self.updated_links_count += 1
                    
                    # Build the updated link with proper path structure
                    if filename_part.startswith('../'):
                        # Preserve the ../ prefix and rebuild path with survivor
                        updated_link = f"../{survivor}"
                    else:
                        updated_link = survivor
                    
                    # Track the link update
                    self.link_updates.append({
                        'file': relative_path,
                        'original_link': filename_part,
                        'updated_link': updated_link,
                        'survivor': survivor,
                        'type': 'wikilink'
                    })
                    
                    logger.debug(f"Wikilink update: {relative_path}: {filename_part} -> {updated_link}")
                    
                    if display_part:
                        return f"[[{updated_link}|{display_part}]]"
                    else:
                        return f"[[{updated_link}]]"
                
                return match.group(0)
            
            wikilink_pattern = r'\[\[([^\]]+)\]\]'
            updated_content = re.sub(wikilink_pattern, process_wikilink, updated_content)
            
            # Process markdown links: [text](filename.md)
            def process_markdown_link(match):
                link_text = match.group(1)
                link_target = match.group(2).strip()
                
                # Normalize paths - remove ../ prefix if present
                normalized_target = link_target
                if normalized_target.startswith('../'):
                    normalized_target = normalized_target[3:]  # Remove '../'
                
                # Check if this link points to a duplicate
                # Match both the full path and just the filename
                base_name = os.path.basename(link_target)
                matched_key = None
                
                # First try to match the full normalized path
                if normalized_target in self.duplicate_to_survivor:
                    matched_key = normalized_target
                # Then try the original path
                elif link_target in self.duplicate_to_survivor:
                    matched_key = link_target
                # Then try just the filename
                elif base_name in self.duplicate_to_survivor:
                    matched_key = base_name
                
                if matched_key:
                    survivor = self.duplicate_to_survivor[matched_key]
                    self.updated_links_count += 1
                    
                    # Update the link target while preserving path structure
                    if link_target.startswith('../'):
                        # Preserve the ../ structure with full path
                        updated_target = f"../{survivor}"
                    else:
                        dir_path = os.path.dirname(link_target)
                        if dir_path:
                            updated_target = f"{dir_path}/{os.path.basename(survivor)}"
                        else:
                            updated_target = os.path.basename(survivor)
                    
                    # Track the link update
                    self.link_updates.append({
                        'file': relative_path,
                        'original_link': link_target,
                        'updated_link': updated_target,
                        'survivor': survivor,
                        'type': 'markdown'
                    })
                    
                    logger.debug(f"Markdown link: {relative_path}: {link_target} -> {updated_target}")
                    
                    return f"[{link_text}]({updated_target})"
                
                return match.group(0)
            
            markdown_link_pattern = r'\[([^\]]*)\]\(([^)]+)\)'
            updated_content = re.sub(markdown_link_pattern, process_markdown_link, updated_content)
            
            # Write updated content back to file if changes were made
            if original_content != updated_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                logger.debug(f"Updated links in {relative_path}")
        
        except Exception as e:
            logger.error(f"Error updating links in {file_path}: {e}")

    def rename_non_survivors(self) -> None:
        """
        Rename non-surviving files with a "dup-" prefix.
        This makes them easy to identify and can be deleted later.
        """
        if not config_manager.deduplicate_rename_mode:
            logger.info("Rename mode disabled, skipping file renaming")
            return
        
        logger.info("Renaming non-surviving duplicates...")
        
        for file_hash, siblings in self.sibling_groups.items():
            survivor = self.survivors[file_hash]
            
            for duplicate in siblings:
                if duplicate == survivor:
                    continue
                
                # Construct absolute path
                duplicate_path = os.path.join(self.vault_path, duplicate)
                
                if os.path.exists(duplicate_path):
                    # Get directory and filename
                    dir_path = os.path.dirname(duplicate_path)
                    filename = os.path.basename(duplicate_path)
                    new_filename = f"dup-{filename}"
                    new_path = os.path.join(dir_path, new_filename)
                    
                    try:
                        os.rename(duplicate_path, new_path)
                        relative_new_path = os.path.relpath(new_path, self.vault_path)
                        
                        self.renamed_files.append({
                            'original': duplicate,
                            'renamed': relative_new_path,
                            'hash': file_hash[:8] + '...'
                        })
                        
                        logger.debug(f"Renamed: {duplicate} -> {new_filename}")
                    except Exception as e:
                        logger.error(f"Failed to rename {duplicate}: {e}")
        
        logger.info(f"Renamed {len(self.renamed_files)} non-surviving files")

    def process_duplicates(self) -> bool:
        """
        Execute the complete deduplication process.
        
        Returns:
            bool: True if deduplication completed successfully
        """
        if self.processed:
            logger.info("Deduplication already processed, skipping.")
            return True
        
        if not config_manager.deduplicate_files:
            logger.info("Deduplication not enabled, skipping.")
            self.processed = True
            return True
        
        try:
            # Step 1: Identify sibling groups
            self.identify_sibling_groups()
            
            if not self.sibling_groups:
                logger.info("No duplicate files found. Nothing to deduplicate.")
                self.processed = True
                return True
            
            # Apply test mode limit if enabled
            if config_manager.deduplicate_test_mode:
                # Sort by hash and take only first max_groups
                sorted_hashes = sorted(self.sibling_groups.keys())
                limited_hashes = sorted_hashes[:config_manager.deduplicate_max_groups]
                self.sibling_groups = {h: self.sibling_groups[h] for h in limited_hashes}
                logger.info(f"Test mode: Processing only {len(self.sibling_groups)} groups")
            
            # Step 2: Select survivors
            self.select_survivors()
            
            # Step 3: Update internal links
            self.update_internal_links()
            
            # Step 4: Rename or delete non-surviving files
            if config_manager.deduplicate_delete_mode:
                self.delete_non_survivors()
            else:
                self.rename_non_survivors()
            
            self.processed = True
            logger.info("Deduplication completed successfully!")
            
            # Generate summary
            self._print_summary()
            
            # Generate HTML report
            self.generate_html_report()
            
            return True
            
        except Exception as e:
            logger.error(f"Deduplication failed: {e}")
            return False

    def _print_summary(self) -> None:
        """Print a summary of the deduplication process."""
        logger.info("=" * 60)
        logger.info("DEDUPLICATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total sibling groups: {len(self.sibling_groups)}")
        logger.info(f"Total duplicates: {sum(len(siblings) - 1 for siblings in self.sibling_groups.values())}")
        logger.info(f"Links updated: {self.updated_links_count}")
        logger.info(f"Files renamed: {len(self.renamed_files)}")
        
        if config_manager.deduplicate_test_mode:
            logger.info(f"Test mode: Limited to {config_manager.deduplicate_max_groups} groups")
        
        logger.info("=" * 60)

    def generate_report(self) -> Dict:
        """
        Generate a report of the deduplication process.
        
        Returns:
            Dict: Report containing statistics and details
        """
        report = {
            'total_sibling_groups': len(self.sibling_groups),
            'total_duplicates': sum(len(siblings) - 1 for siblings in self.sibling_groups.values()),
            'links_updated': self.updated_links_count,
            'files_renamed': len(self.renamed_files),
            'sibling_groups': {},
            'renamed_files': self.renamed_files,
            'link_updates': self.link_updates,
            'test_mode': config_manager.deduplicate_test_mode
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

    def _categorize_deduplications(self) -> Dict:
        """
        Categorize deduplicated files by whether they had incoming links.
        
        Returns:
            Dict with 'with_links' and 'without_links' categories
        """
        categorized = {
            'with_links': {},
            'without_links': {}
        }
        
        # Get all duplicates that had links updated
        linked_duplicates = set()
        for update in self.link_updates:
            # Find which duplicate this link originally pointed to
            for dup, surv in self.duplicate_to_survivor.items():
                if dup in update['original_link'] or update['original_link'].endswith(os.path.basename(dup)):
                    linked_duplicates.add(dup)
                    break
        
        # Categorize sibling groups
        for file_hash, siblings in self.sibling_groups.items():
            survivor = self.survivors[file_hash]
            duplicates = [s for s in siblings if s != survivor]
            
            # Check if any duplicate in this group had links
            has_links = any(dup in linked_duplicates for dup in duplicates)
            
            category = 'with_links' if has_links else 'without_links'
            categorized[category][file_hash] = {
                'survivor': survivor,
                'duplicates': duplicates,
                'total_files': len(siblings),
                'link_updates': [u for u in self.link_updates if any(dup in u['original_link'] for dup in duplicates)]
            }
        
        return categorized

    def generate_html_report(self) -> None:
        """
        Generate a comprehensive HTML report of the deduplication process.
        Creates a collapsible HTML report showing all deduplication details.
        """
        report = self.generate_report()
        categorized = self._categorize_deduplications()
        report_path = os.path.join(self.vault_path, "deduplication_report.html")
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Deduplication Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .collapsible {{
            background-color: #3498db;
            color: white;
            cursor: pointer;
            padding: 15px;
            width: 100%;
            border: none;
            text-align: left;
            outline: none;
            font-size: 16px;
            border-radius: 5px;
            margin-top: 10px;
        }}
        .collapsible:hover {{
            background-color: #2980b9;
        }}
        .collapsible:after {{
            content: '+';
            font-weight: bold;
            float: right;
            margin-left: 5px;
        }}
        .collapsible.active:after {{
            content: '-';
        }}
        .content {{
            display: none;
            padding: 15px;
            background-color: #f8f9fa;
            border-left: 4px solid #3498db;
            margin-bottom: 10px;
        }}
        .content.active {{
            display: block;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .survivor {{
            color: #27ae60;
            font-weight: bold;
        }}
        .duplicate {{
            color: #e74c3c;
        }}
        .link-type-wikilink {{
            background-color: #ecf0f1;
            padding: 3px 8px;
            border-radius: 3px;
            font-family: monospace;
        }}
        .link-type-markdown {{
            background-color: #e8f5e9;
            padding: 3px 8px;
            border-radius: 3px;
            font-family: monospace;
        }}
        .code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
            font-size: 0.9em;
        }}
    </style>
    <script>
        function toggleSection(element) {{
            element.classList.toggle('active');
            var content = element.nextElementSibling;
            content.classList.toggle('active');
        }}
    </script>
</head>
<body>
    <div class="container">
        <h1>🔍 Deduplication Report</h1>
        <p>Generated for: {self.vault_path}</p>
        
        <div class="summary">
            <div class="stat-card">
                <div class="stat-number">{report['total_sibling_groups']}</div>
                <div class="stat-label">Sibling Groups</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{report['total_duplicates']}</div>
                <div class="stat-label">Duplicate Files</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{report['links_updated']}</div>
                <div class="stat-label">Links Updated</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{report['files_renamed']}</div>
                <div class="stat-label">Files Renamed</div>
            </div>
        </div>
"""
        
        # Add categorized sections
        # Files WITH incoming links
        if categorized['with_links']:
            html_content += f"""
        <h2>📎 Deduplicated Files WITH Incoming Links ({len(categorized['with_links'])} groups)</h2>
        <p style="color: #7f8c8d;">These files had links pointing to them that were updated to point to survivors.</p>
"""
            for file_hash, group_data in sorted(categorized['with_links'].items()):
                html_content += f"""
        <button class="collapsible" onclick="toggleSection(this)">
            🔗 Group: {file_hash[:16]}... ({group_data['total_files']} files, {len(group_data['link_updates'])} link updates)
        </button>
        <div class="content">
            <p><strong>Hash:</strong> <code>{file_hash}</code></p>
            <p><strong>Survivor:</strong> <span class="survivor">{group_data['survivor']}</span></p>
            <p><strong>Duplicates ({len(group_data['duplicates'])}):</strong></p>
            <ul>
"""
                for dup in group_data['duplicates']:
                    html_content += f"                <li class=\"duplicate\">{dup}</li>\n"
                html_content += "            </ul>\n"
                
                if group_data['link_updates']:
                    html_content += f"""
            <p><strong>Link Updates ({len(group_data['link_updates'])}):</strong></p>
            <table style="font-size: 0.9em;">
                <tr>
                    <th>File</th>
                    <th>Original Link</th>
                    <th>Updated Link</th>
                </tr>
"""
                    for update in group_data['link_updates'][:20]:  # Limit per group
                        html_content += f"""
                <tr>
                    <td>{update['file']}</td>
                    <td class="code">{update['original_link']}</td>
                    <td class="code">{update['updated_link']}</td>
                </tr>
"""
                    if len(group_data['link_updates']) > 20:
                        html_content += f"                <tr><td colspan='3'>... and {len(group_data['link_updates']) - 20} more</td></tr>"
                    html_content += "            </table>\n"
                
                html_content += "        </div>\n"
        
        # Files WITHOUT incoming links
        if categorized['without_links']:
            html_content += f"""
        <h2>📦 Deduplicated Files WITHOUT Incoming Links ({len(categorized['without_links'])} groups)</h2>
        <p style="color: #7f8c8d;">These files had no links pointing to them (orphaned duplicates).</p>
"""
            for file_hash, group_data in sorted(categorized['without_links'].items()):
                html_content += f"""
        <button class="collapsible" onclick="toggleSection(this)">
            📁 Group: {file_hash[:16]}... ({group_data['total_files']} files)
        </button>
        <div class="content">
            <p><strong>Hash:</strong> <code>{file_hash}</code></p>
            <p><strong>Survivor:</strong> <span class="survivor">{group_data['survivor']}</span></p>
            <p><strong>Duplicates ({len(group_data['duplicates'])}):</strong></p>
            <ul>
"""
                for dup in group_data['duplicates']:
                    html_content += f"                <li class=\"duplicate\">{dup}</li>\n"
                html_content += "            </ul>\n        </div>\n"
        
        # Add link updates section
        if report['link_updates']:
            html_content += """
        <h2>🔗 Link Updates</h2>
        <button class="collapsible" onclick="toggleSection(this)">
            View All Link Updates ({len(report['link_updates'])})
        </button>
        <div class="content">
            <table>
                <tr>
                    <th>File</th>
                    <th>Link Type</th>
                    <th>Original Link</th>
                    <th>Updated Link</th>
                </tr>
"""
            for update in report['link_updates'][:100]:  # Limit to first 100
                link_type_class = "link-type-wikilink" if update['type'] == 'wikilink' else "link-type-markdown"
                html_content += f"""
                <tr>
                    <td>{update['file']}</td>
                    <td><span class="{link_type_class}">{update['type']}</span></td>
                    <td class="code">{update['original_link']}</td>
                    <td class="code">{update['updated_link']}</td>
                </tr>
"""
            if len(report['link_updates']) > 100:
                html_content += f"                <tr><td colspan='4'>... and {len(report['link_updates']) - 100} more link updates</td></tr>"
            html_content += """
            </table>
        </div>
"""
        
        # Add renamed files section
        if report['renamed_files']:
            html_content += """
        <h2>📝 Renamed Files</h2>
        <button class="collapsible" onclick="toggleSection(this)">
            View All Renamed Files ({len(report['renamed_files'])})
        </button>
        <div class="content">
            <table>
                <tr>
                    <th>Original Name</th>
                    <th>Renamed To</th>
                </tr>
"""
            for renamed in report['renamed_files']:
                html_content += f"""
                <tr>
                    <td>{renamed['original']}</td>
                    <td class="duplicate">{renamed['renamed']}</td>
                </tr>
"""
            html_content += "            </table>\n        </div>\n"
        
        html_content += """
    </div>
</body>
</html>
"""
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"Deduplication HTML report generated at {report_path}")
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")


# Global deduplication handler instance
deduplication_handler = DeduplicationHandler()

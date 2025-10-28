import os
import re
import hashlib
from typing import List, Dict, Set, Optional
from config_manager import config_manager
from collision_resolver import collision_resolver
from logger import logger

global LINKMAPFILE 
LINKMAPFILE = "linkmap.txt"

class LinkProcessor:
    """
    Processes internal links in markdown files.
    Detects wikilinks and markdown links, and updates them to reflect file renames.
    Creates comprehensive link mapping file.
    """

    def __init__(self):
        self.link_mapping: List[str] = []
        self.unresolved_links: List[str] = []
        self.vault_files: Set[str] = set()  # Set of all files in the vault

    def process_links(self) -> None:
        """
        Process all markdown files in the destination vault to update internal links.
        """
        logger.info("Starting link processing...")
        rename_log = collision_resolver.get_rename_log()
        
        # Build set of all files in vault for link validation
        self._build_vault_file_set()
        
        # Process all markdown files in destination vault
        for root, dirs, files in os.walk(config_manager.destination_path):
            # Skip dot-prefixed directories
            dirs[:] = [d for d in dirs if not (config_manager.exclude_dot_folders and d.startswith('.'))]
            
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    try:
                        self._process_file(file_path, rename_log)
                    except Exception as e:
                        logger.error(f"Failed to process links in {file_path}: {e}")
        
        # Generate link mapping file
        self.generate_link_mapping_file()
        logger.info(f"Link processing complete. Processed {len(self.link_mapping)} valid links.")

    def analyze_links_standalone(self) -> None:
        """
        Analyze links in an existing vault without merging.
        This is a standalone mode that always analyzes links and generates hash information for all files.
        """
        logger.info("Starting standalone link analysis...")
        
        # Build set of all files in vault for link validation
        self._build_vault_file_set()
        
        # Process all markdown files in the vault for link analysis
        for root, dirs, files in os.walk(config_manager.destination_path):
            # Skip dot-prefixed directories
            dirs[:] = [d for d in dirs if not (config_manager.exclude_dot_folders and d.startswith('.'))]
            
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    try:
                        self._process_single_file(file_path, analyze_only=True)
                    except Exception as e:
                        logger.error(f"Failed to analyze links in {file_path}: {e}")
        
        # Generate link mapping file with both link mappings and hashes for all files
        self.generate_link_mapping_file()
        logger.info(f"Standalone link analysis complete. Found {len(self.link_mapping)} valid links.")

    def _build_vault_file_set(self) -> None:
        """
        Build a set of all files in the vault for quick lookup.
        """
        for root, dirs, files in os.walk(config_manager.destination_path):
            # Skip dot-prefixed directories
            dirs[:] = [d for d in dirs if not (config_manager.exclude_dot_folders and d.startswith('.'))]
            
            for file in files:
                self.vault_files.add(file)
        
        logger.debug(f"Built vault file set with {len(self.vault_files)} files")

    def _is_internal_vault_link(self, filename: str) -> bool:
        """
        Check if a filename represents an internal vault link (not external URL).
        
        Args:
            filename: The filename to check
            
        Returns:
            bool: True if it's an internal vault link, False otherwise
        """
        # Check if it looks like a URL
        if filename.startswith(('http://', 'https://', 'www.')):
            return False
            
        # Check if it's an email link
        if filename.startswith('mailto:'):
            return False
            
        # Check if it's a file in our vault
        return filename in self.vault_files

    def _process_single_file(self, file_path: str, rename_log: Optional[Dict[str, str]] = None, analyze_only: bool = False) -> Dict:
        """
        Unified method to read all links and calculate hashes for a single file.
        
        Args:
            file_path: Path to the markdown file
            rename_log: Dictionary mapping original filenames to new filenames (optional)
            analyze_only: If True, only analyze links without updating them
            
        Returns:
            Dict: Information about the file including links and hash
        """
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Calculate file hash
        file_hash = self._calculate_file_hash(file_path)
        
        # Get relative path for source tracking
        source_file = os.path.relpath(file_path, config_manager.destination_path)
        
        # Extract all links from the file
        links = []
        
        # Process wikilinks: [[filename]] or [[filename|display]]
        wikilink_pattern = r'\[\[([^\]]+)\]\]'
        wikilink_matches = re.finditer(wikilink_pattern, content)
        
        for match in wikilink_matches:
            link_content = match.group(1)
            parts = link_content.split('|', 1)
            filename_part = parts[0]
            display_part = parts[1] if len(parts) > 1 else None
            
            # Add to link mapping only if it's an internal vault link
            target_filename = os.path.basename(filename_part)
            if self._is_internal_vault_link(target_filename):
                link_info = {
                    'target': filename_part,
                    'source': source_file,
                    'type': 'wikilink',
                    'display': display_part,
                    'original_match': match.group(0)
                }
                links.append(link_info)
                self.link_mapping.append(f"{filename_part} <- {source_file} (wikilink)")
        
        # Process markdown links: [text](filename.md) or [text](path/filename.md)
        markdown_link_pattern = r'\[([^\]]*)\]\(([^)]+)\)'
        markdown_link_matches = re.finditer(markdown_link_pattern, content)
        
        for match in markdown_link_matches:
            link_text = match.group(1)
            link_target = match.group(2)
            
            # Add to link mapping only if it's an internal vault link
            target_filename = os.path.basename(link_target)
            if self._is_internal_vault_link(target_filename):
                link_info = {
                    'target': link_target,
                    'source': source_file,
                    'type': 'markdown',
                    'link_text': link_text,
                    'original_match': match.group(0)
                }
                links.append(link_info)
                self.link_mapping.append(f"{link_target} <- {source_file} (markdown)")
        
        # Update links if not in analyze-only mode and rename_log is provided
        updated_content = content
        if not analyze_only and rename_log:
            # Process wikilinks for updates
            def process_wikilink(match):
                link_content = match.group(1)
                parts = link_content.split('|', 1)
                filename_part = parts[0]
                display_part = parts[1] if len(parts) > 1 else None
                
                # Check if file was renamed
                if filename_part in rename_log:
                    new_filename = rename_log[filename_part]
                    if display_part:
                        return f"[[{new_filename}|{display_part}]]"
                    else:
                        return f"[[{new_filename}]]"
                
                return match.group(0)
            
            updated_content = re.sub(wikilink_pattern, process_wikilink, updated_content)
            
            # Process markdown links for updates
            def process_markdown_link(match):
                link_text = match.group(1)
                link_target = match.group(2)
                
                # Extract filename from path
                filename = os.path.basename(link_target)
                
                # Check if file was renamed
                if filename in rename_log:
                    # Update the filename part while preserving the path
                    dir_path = os.path.dirname(link_target)
                    new_filename = rename_log[filename]
                    if dir_path:
                        updated_target = f"{dir_path}/{new_filename}"
                    else:
                        updated_target = new_filename
                    
                    return f"[{link_text}]({updated_target})"
                
                return match.group(0)
            
            updated_content = re.sub(markdown_link_pattern, process_markdown_link, updated_content)
            
            # Write updated content back to file if changes were made
            if content != updated_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                logger.debug(f"Updated links in {file_path}")
        
        # Return file information
        return {
            'file_path': file_path,
            'relative_path': source_file,
            'hash': file_hash,
            'links': links
        }

    def _process_file(self, file_path: str, rename_log: Dict[str, str]) -> None:
        """
        Process a single markdown file to update internal links.
        
        Args:
            file_path: Path to the markdown file
            rename_log: Dictionary mapping original filenames to new filenames
        """
        self._process_single_file(file_path, rename_log, analyze_only=False)

    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate MD5 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: MD5 hash of the file
        """
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return "ERROR"

    def generate_link_mapping_file(self) -> None:
        """
        Generate a link mapping file showing all internal references with file hashes.
        Always writes link mappings first, then hashes all files if hash_all_files is enabled or in analyze-only mode.
        Format: SOURCEFILE ; LINK_TO_FILE ; HASHNUMBER
        """
        mapping_file_path = os.path.join(config_manager.destination_path, LINKMAPFILE)
        try:
            with open(mapping_file_path, 'w', encoding='utf-8') as f:
                # First, write the existing link mappings
                for mapping in self.link_mapping:
                    # Parse the existing mapping format: "target <- source (type)"
                    parts = mapping.split(" <- ")
                    if len(parts) >= 2:
                        target = parts[0].strip()
                        source_and_type = parts[1].strip()
                        source_parts = source_and_type.split(" (")
                        source_file = source_parts[0].strip() if source_parts else "unknown"
                        link_type = source_parts[1].rstrip(")").strip() if len(source_parts) > 1 else "unknown"
                        
                        # Calculate hash for the target file if it exists
                        target_file_path = os.path.join(config_manager.destination_path, target)
                        file_hash = self._calculate_file_hash(target_file_path) if os.path.exists(target_file_path) else "NOT_FOUND"
                        
                        # Write in the new format: SOURCEFILE ; LINK_TO_FILE ; HASHNUMBER
                        f.write(f"{source_file} ; {target} ; {file_hash}\n")
                    else:
                        # Handle any mappings that don't match the expected format
                        f.write(f"unknown ; {mapping} ; ERROR\n")
                
                # If hash_all_files option is enabled OR we're in analyze-only mode, hash all other files in the vault
                if config_manager.hash_all_files or config_manager.analyze_only:
                    # Get all files in the vault
                    all_files = []
                    for root, dirs, files in os.walk(config_manager.destination_path):
                        # Skip dot-prefixed directories
                        dirs[:] = [d for d in dirs if not (config_manager.exclude_dot_folders and d.startswith('.'))]
                        
                        for file in files:
                            file_path = os.path.join(root, file)
                            relative_path = os.path.relpath(file_path, config_manager.destination_path)
                            all_files.append((relative_path, file_path))
                    
                    # Create a set of files that are already in the link mapping to avoid duplicates
                    linked_files = set()
                    for mapping in self.link_mapping:
                        parts = mapping.split(" <- ")
                        if len(parts) >= 1:
                            target = parts[0].strip()
                            linked_files.add(target)
                    
                    # Calculate total number of files for progress bar
                    total_files = len(all_files)
                    processed_files = 0
                    
                    # Process all files with progress indication, but skip already linked files
                    for relative_path, file_path in all_files:
                        # Skip files that are already in the link mapping
                        if relative_path not in linked_files:
                            file_hash = self._calculate_file_hash(file_path)
                            # For files that are not linked, we use "UNLINKED" as source
                            f.write(f"UNLINKED ; {relative_path} ; {file_hash}\n")
                        
                        # Update progress
                        processed_files += 1
                        if total_files > 0:
                            progress = (processed_files / total_files) * 100
                            print(f"\rHashing files: {progress:.1f}% ({processed_files}/{total_files})", end='', flush=True)
                    
                    print()  # New line after progress bar
            logger.info(f"Link mapping file generated at {mapping_file_path}")
        except Exception as e:
            logger.error(f"Failed to generate link mapping file: {e}")

    def get_link_mapping(self) -> List[str]:
        """
        Get the link mapping list.
        
        Returns:
            List[str]: List of link mappings
        """
        return self.link_mapping

    def get_unresolved_links(self) -> List[str]:
        """
        Get list of unresolved links.
        In this implementation, we're not actually checking if links resolve,
        but in a full implementation this would track broken links.
        
        Returns:
            List[str]: List of unresolved links
        """
        return self.unresolved_links


# Global link processor instance
link_processor = LinkProcessor()
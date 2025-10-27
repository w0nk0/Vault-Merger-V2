import os
import re
import hashlib
from typing import List, Dict, Tuple, Set
from config_manager import config_manager
from collision_resolver import collision_resolver
from logger import logger


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

    def _process_file(self, file_path: str, rename_log: Dict[str, str]) -> None:
        """
        Process a single markdown file to update internal links.
        
        Args:
            file_path: Path to the markdown file
            rename_log: Dictionary mapping original filenames to new filenames
        """
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        updated_content = content
        
        # Get relative path for source tracking
        source_file = os.path.relpath(file_path, config_manager.destination_path)
        
        # Process wikilinks: [[filename]] or [[filename|display]]
        wikilink_pattern = r'\[\[([^\]]+)\]\]'
        updated_content = re.sub(wikilink_pattern, 
                                lambda m: self._process_wikilink(m, rename_log, source_file), 
                                updated_content)
        
        # Process markdown links: [text](filename.md) or [text](path/filename.md)
        markdown_link_pattern = r'\[([^\]]*)\]\(([^)]+)\)'
        updated_content = re.sub(markdown_link_pattern, 
                                lambda m: self._process_markdown_link(m, rename_log, source_file), 
                                updated_content)
        
        # Write updated content back to file if changes were made
        if original_content != updated_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            logger.debug(f"Updated links in {file_path}")

    def _process_wikilink(self, match: re.Match, rename_log: Dict[str, str], source_file: str) -> str:
        """
        Process a wikilink match and update if target file was renamed.
        
        Args:
            match: Regex match object for wikilink
            rename_log: Dictionary mapping original filenames to new filenames
            source_file: The file containing this link
            
        Returns:
            str: Updated wikilink or original if no update needed
        """
        link_content = match.group(1)
        
        # Split on | to separate filename from display text
        parts = link_content.split('|', 1)
        filename_part = parts[0]
        display_part = parts[1] if len(parts) > 1 else None
        
        # Add to link mapping only if it's an internal vault link
        target_filename = os.path.basename(filename_part)
        if self._is_internal_vault_link(target_filename):
            self.link_mapping.append(f"{filename_part} <- {source_file} (wikilink)")
        
        # Check if file was renamed
        if filename_part in rename_log:
            new_filename = rename_log[filename_part]
            if display_part:
                updated_link = f"[[{new_filename}|{display_part}]]"
            else:
                updated_link = f"[[{new_filename}]]"
            logger.debug(f"Updated wikilink: {link_content} -> {new_filename}")
            return updated_link
        
        # No update needed
        return match.group(0)

    def _process_markdown_link(self, match: re.Match, rename_log: Dict[str, str], source_file: str) -> str:
        """
        Process a markdown link match and update if target file was renamed.
        
        Args:
            match: Regex match object for markdown link
            rename_log: Dictionary mapping original filenames to new filenames
            source_file: The file containing this link
            
        Returns:
            str: Updated markdown link or original if no update needed
        """
        link_text = match.group(1)
        link_target = match.group(2)
        
        # Add to link mapping only if it's an internal vault link
        target_filename = os.path.basename(link_target)
        if self._is_internal_vault_link(target_filename):
            self.link_mapping.append(f"{link_target} <- {source_file} (markdown)")
        
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
            
            updated_link = f"[{link_text}]({updated_target})"
            logger.debug(f"Updated markdown link: {link_target} -> {updated_target}")
            return updated_link
        
        # No update needed
        return match.group(0)

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
        Format: SOURCEFILE ; LINK_TO_FILE ; HASHNUMBER
        """
        mapping_file_path = os.path.join(config_manager.destination_path, "link_mapping.txt")
        try:
            with open(mapping_file_path, 'w', encoding='utf-8') as f:
                # If hash_all_files option is enabled, we need to hash all files in the vault
                if config_manager.hash_all_files:
                    # Get all files in the vault
                    all_files = []
                    for root, dirs, files in os.walk(config_manager.destination_path):
                        # Skip dot-prefixed directories
                        dirs[:] = [d for d in dirs if not (config_manager.exclude_dot_folders and d.startswith('.'))]
                        
                        for file in files:
                            file_path = os.path.join(root, file)
                            relative_path = os.path.relpath(file_path, config_manager.destination_path)
                            all_files.append((relative_path, file_path))
                    
                    # Calculate total number of files for progress bar
                    total_files = len(all_files)
                    processed_files = 0
                    
                    # Process all files with progress indication
                    for relative_path, file_path in all_files:
                        file_hash = self._calculate_file_hash(file_path)
                        # For files that are not linked, we use "UNLINKED" as source
                        f.write(f"UNLINKED ; {relative_path} ; {file_hash}\n")
                        
                        # Update progress
                        processed_files += 1
                        if total_files > 0:
                            progress = (processed_files / total_files) * 100
                            print(f"\rHashing files: {progress:.1f}% ({processed_files}/{total_files})", end='', flush=True)
                    
                    print()  # New line after progress bar
                else:
                    # Process only linked files as before
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
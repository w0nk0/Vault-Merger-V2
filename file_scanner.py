import os
from typing import List, Dict
from config_manager import config_manager
from logger import logger


class FileScanner:
    """
    Scans source vaults to build inventory of files and directories.
    Identifies dot-prefixed folders for exclusion and detects potential
    filename collisions across all vaults.
    """

    def __init__(self):
        self.file_inventory: List[Dict] = []
        self.filename_counts: Dict[str, int] = {}

    def scan_vaults(self) -> None:
        """
        Recursively scan all source vaults and build file inventory.
        """
        logger.info("Starting vault scan...")
        for source_path in config_manager.source_paths:
            logger.info(f"Scanning vault: {source_path}")
            self._scan_directory(source_path, source_path)
        logger.info(f"Scan complete. Found {len(self.file_inventory)} files.")

    def _scan_directory(self, base_path: str, current_path: str) -> None:
        """
        Recursively scan a directory and its subdirectories.
        
        Args:
            base_path: The root path of the vault being scanned
            current_path: The current directory being scanned
        """
        try:
            for item in os.listdir(current_path):
                item_path = os.path.join(current_path, item)
                
                # Skip dot-prefixed folders if configured to do so
                if config_manager.exclude_dot_folders and item.startswith('.'):
                    if os.path.isdir(item_path):
                        logger.debug(f"Skipping dot-prefixed folder: {item_path}")
                        continue
                
                if os.path.isfile(item_path):
                    # Check if file type is included
                    if self._is_included_file(item):
                        self._add_file_to_inventory(base_path, item_path)
                elif os.path.isdir(item_path):
                    # Recursively scan subdirectories
                    self._scan_directory(base_path, item_path)
        except PermissionError as e:
            logger.error(f"Permission denied when scanning {current_path}: {e}")
        except Exception as e:
            logger.error(f"Error scanning {current_path}: {e}")

    def _is_included_file(self, filename: str) -> bool:
        """
        Check if a file should be included based on file type filters.
        
        Args:
            filename: Name of the file to check
            
        Returns:
            bool: True if file should be included, False otherwise
        """
        # If no file types specified, include all files
        if not config_manager.file_types:
            return True
            
        # If file types are specified, check if file matches any of them
        for file_type in config_manager.file_types:
            if filename.endswith(file_type):
                return True
        return False

    def _add_file_to_inventory(self, base_path: str, file_path: str) -> None:
        """
        Add a file to the inventory and track filename counts for collision detection.
        
        Args:
            base_path: The root path of the vault being scanned
            file_path: Full path to the file
        """
        relative_path = os.path.relpath(file_path, base_path)
        filename = os.path.basename(file_path)
        
        # Track filename counts for collision detection
        if filename in self.filename_counts:
            self.filename_counts[filename] += 1
        else:
            self.filename_counts[filename] = 1
            
        file_info = {
            "original_path": file_path,
            "relative_path": relative_path,
            "filename": filename,
            "base_path": base_path,
            "collision_count": self.filename_counts[filename]
        }
        
        self.file_inventory.append(file_info)
        logger.debug(f"Added file to inventory: {relative_path}")

    def get_collision_candidates(self) -> List[str]:
        """
        Get list of filenames that have collisions (appear more than once).
        
        Returns:
            List[str]: List of filenames with collisions
        """
        return [filename for filename, count in self.filename_counts.items() if count > 1]

    def get_file_inventory(self) -> List[Dict]:
        """
        Get the complete file inventory.
        
        Returns:
            List[Dict]: List of file information dictionaries
        """
        return self.file_inventory


# Global file scanner instance
file_scanner = FileScanner()
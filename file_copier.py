import os
import shutil
from typing import List, Dict
from config_manager import config_manager
from collision_resolver import collision_resolver
from logger import logger


class FileCopier:
    """
    Copies files from source vaults to destination vault.
    Preserves folder structures during copying and handles file renaming.
    """

    def __init__(self):
        self.copy_log: List[Dict] = []

    def copy_files(self) -> None:
        """
        Copy files from source vaults to destination vault.
        """
        logger.info("Starting file copy process...")
        resolved_files = collision_resolver.get_resolved_files()
        
        for file_info in resolved_files:
            try:
                self._copy_file(file_info)
            except Exception as e:
                logger.error(f"Failed to copy file {file_info['original_path']}: {e}")
        
        logger.info(f"File copy complete. Copied {len(self.copy_log)} files.")

    def _copy_file(self, file_info: Dict) -> None:
        """
        Copy a single file to the destination vault.
        
        Args:
            file_info: Dictionary containing file information
        """
        source_path = file_info["original_path"]
        resolved_filename = file_info["resolved_filename"]
        
        # Determine destination path
        if config_manager.preserve_folder_structure:
            # Preserve relative folder structure
            relative_dir = os.path.dirname(file_info["relative_path"])
            dest_dir = os.path.join(config_manager.destination_path, relative_dir)
        else:
            # Flatten structure to destination root
            dest_dir = config_manager.destination_path
        
        # Create destination directory if it doesn't exist
        os.makedirs(dest_dir, exist_ok=True)
        
        # Full destination path
        dest_path = os.path.join(dest_dir, resolved_filename)
        
        # Copy file
        shutil.copy2(source_path, dest_path)
        
        # Log the copy operation
        copy_info = {
            "source_path": source_path,
            "destination_path": dest_path,
            "original_filename": file_info["filename"],
            "resolved_filename": resolved_filename,
            "renamed": file_info["needs_rename"]
        }
        self.copy_log.append(copy_info)
        
        logger.debug(f"Copied '{source_path}' to '{dest_path}'")

    def get_copy_log(self) -> List[Dict]:
        """
        Get the log of all copy operations.
        
        Returns:
            List[Dict]: List of copy operation information
        """
        return self.copy_log

    def get_renamed_files_log(self) -> List[Dict]:
        """
        Get the log of files that were renamed during copying.
        
        Returns:
            List[Dict]: List of renamed file information
        """
        return [entry for entry in self.copy_log if entry["renamed"]]


# Global file copier instance
file_copier = FileCopier()
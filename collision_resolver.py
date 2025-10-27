import os
from typing import List, Dict
from file_scanner import file_scanner
from logger import logger


class CollisionResolver:
    """
    Implements filename collision resolution strategy.
    Renames files with collisions using #1, #2, #3 pattern.
    Maintains rename log for link updating.
    """

    def __init__(self):
        self.rename_log: Dict[str, str] = {}
        self.resolved_files: List[Dict] = []

    def resolve_collisions(self) -> None:
        """
        Resolve filename collisions in the file inventory.
        """
        logger.info("Resolving filename collisions...")
        collision_candidates = file_scanner.get_collision_candidates()
        logger.info(f"Found {len(collision_candidates)} filenames with collisions")
        
        # Group files by filename
        files_by_name = {}
        for file_info in file_scanner.get_file_inventory():
            filename = file_info["filename"]
            if filename not in files_by_name:
                files_by_name[filename] = []
            files_by_name[filename].append(file_info)
        
        # Process each group of files with the same name
        for filename, files in files_by_name.items():
            if len(files) == 1:
                # No collision, keep original name
                files[0]["resolved_filename"] = filename
                files[0]["needs_rename"] = False
                self.resolved_files.append(files[0])
            else:
                # Collision detected, resolve by renaming
                self._resolve_file_group(filename, files)
        
        logger.info(f"Collision resolution complete. {len(self.rename_log)} files renamed.")

    def _resolve_file_group(self, original_filename: str, files: List[Dict]) -> None:
        """
        Resolve a group of files with the same name.
        
        Args:
            original_filename: The original filename shared by all files in the group
            files: List of file information dictionaries
        """
        # First file keeps original name
        files[0]["resolved_filename"] = original_filename
        files[0]["needs_rename"] = False
        self.resolved_files.append(files[0])
        
        # Keep track of all resolved filenames to avoid conflicts
        # We need to check against all filenames in the inventory
        all_filenames = set()
        for file_info in file_scanner.get_file_inventory():
            all_filenames.add(file_info["filename"])
        
        # Add already resolved filenames to avoid conflicts
        for resolved_file in self.resolved_files:
            all_filenames.add(resolved_file["resolved_filename"])
        
        # Subsequent files are renamed with sequential numbers
        for i, file_info in enumerate(files[1:], start=1):
            name, ext = os.path.splitext(original_filename)
            new_filename = f"{name}#{i}{ext}"
            
            # Check if the generated filename already exists and generate a unique one
            counter = 1
            while new_filename in all_filenames:
                new_filename = f"{name}#{i}_{counter}{ext}"
                counter += 1
            
            # Add the new filename to the used set
            all_filenames.add(new_filename)
            
            file_info["resolved_filename"] = new_filename
            file_info["needs_rename"] = True
            self.resolved_files.append(file_info)
            
            # Log the rename for link updating
            self.rename_log[original_filename] = new_filename
            logger.debug(f"Renamed '{original_filename}' to '{new_filename}'")

    def get_resolved_files(self) -> List[Dict]:
        """
        Get the list of files with resolved filenames.
        
        Returns:
            List[Dict]: List of file information with resolved filenames
        """
        return self.resolved_files

    def get_rename_log(self) -> Dict[str, str]:
        """
        Get the rename log mapping original filenames to new filenames.
        
        Returns:
            Dict[str, str]: Mapping of original filenames to new filenames
        """
        return self.rename_log

    def get_renamed_files_count(self) -> int:
        """
        Get the count of files that were renamed due to collisions.
        
        Returns:
            int: Number of renamed files
        """
        return len(self.rename_log)


# Global collision resolver instance
collision_resolver = CollisionResolver()
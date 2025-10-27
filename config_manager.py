import argparse
import os
from typing import List, Optional


class ConfigManager:
    """
    Manages configuration for the Obsidian Vault Merger tool.
    Handles source and destination path configuration, file type filters,
    and folder structure preferences.
    """

    def __init__(self):
        self.source_paths: List[str] = []
        self.destination_path: str = ""
        self.file_types: List[str] = []
        self.exclude_dot_folders: bool = True
        self.preserve_folder_structure: bool = True
        self.hash_all_files: bool = False

    def parse_arguments(self) -> None:
        """
        Parse command-line arguments for source paths, destination path,
        and other configuration options.
        """
        parser = argparse.ArgumentParser(
            description="Merge multiple Obsidian vaults into a single vault"
        )
        parser.add_argument(
            "source_paths",
            nargs="+",
            help="Paths to source Obsidian vaults"
        )
        parser.add_argument(
            "-d", "--destination",
            required=True,
            help="Path to destination vault"
        )
        parser.add_argument(
            "-f", "--file-types",
            nargs="*",
            default=[],
            help="File types to include (default: all files)"
        )
        parser.add_argument(
            "--flatten",
            action="store_true",
            help="Flatten directory structure instead of preserving it"
        )
        parser.add_argument(
            "--include-dot-folders",
            action="store_true",
            help="Include dot-prefixed folders (default: exclude)"
        )
        parser.add_argument(
            "--hash-all-files",
            action="store_true",
            help="Calculate hash numbers for all files in the vault and add them to the link mapping file"
        )

        args = parser.parse_args()
        self.source_paths = args.source_paths
        self.destination_path = args.destination
        self.file_types = args.file_types
        self.preserve_folder_structure = not args.flatten
        self.exclude_dot_folders = not args.include_dot_folders
        self.hash_all_files = args.hash_all_files

    def validate_paths(self) -> None:
        """
        Validate source and destination paths.
        Raises ValueError if any path is invalid.
        """
        # Validate source paths
        for path in self.source_paths:
            if not os.path.exists(path):
                raise ValueError(f"Source path does not exist: {path}")
            if not os.path.isdir(path):
                raise ValueError(f"Source path is not a directory: {path}")

        # Validate destination path
        if not self.destination_path:
            raise ValueError("Destination path is required")

        # Create destination directory if it doesn't exist
        os.makedirs(self.destination_path, exist_ok=True)

    def get_config_summary(self) -> str:
        """
        Get a summary of the current configuration.
        Returns:
            str: Configuration summary
        """
        summary = "Configuration Summary:\n"
        summary += f"  Source paths: {', '.join(self.source_paths)}\n"
        summary += f"  Destination path: {self.destination_path}\n"
        summary += f"  File types: {', '.join(self.file_types)}\n"
        summary += f"  Preserve folder structure: {self.preserve_folder_structure}\n"
        summary += f"  Exclude dot folders: {self.exclude_dot_folders}\n"
        return summary


# Global config manager instance
config_manager = ConfigManager()
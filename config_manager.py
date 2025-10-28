import argparse
import os
from typing import List


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
        self.hash_all_files: bool = True  # Default: ON
        self.analyze_only: bool = False
        self.deduplicate_files: bool = False
        self.deduplicate_test_mode: bool = False
        self.deduplicate_max_groups: int = 3
        self.deduplicate_rename_mode: bool = True
        self.deduplicate_delete_mode: bool = False

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
            required=False,
            help="Path to destination vault (not required when using --analyze-only)"
        )
        parser.add_argument(
            "-f", "--file-types",
            nargs="*",
            default=[],
            help="File types to include (default: all files)"
        )
        parser.add_argument(
            "--flatten", "-l",
            action="store_true",
            help="Flatten directory structure instead of preserving it"
        )
        parser.add_argument(
            "--include-dot-folders", "-i",
            action="store_true",
            help="Include dot-prefixed folders (default: exclude)"
        )
        parser.add_argument(
            "--hash-all-files", "-a",
            action="store_true", default=None,
            help="Calculate hash numbers for all files in the vault and add them to the link mapping file (default: enabled)"
        )
        parser.add_argument(
            "--no-hash-files",
            dest="hash_all_files",
            action="store_false",
            default=None,
            help="Disable hash calculation for all files"
        )
        parser.add_argument(
            "--analyze-only", "-o",
            action="store_true",
            help="Analyze existing vault for links and hashes without merging (requires single vault path as both source and destination)"
        )
        parser.add_argument(
            "--linkmap-only", "-L",
            action="store_true",
            help="Only generate the link mapping file. (We'll use destination or source Vault Path .)"
        )
        parser.add_argument(
            "--deduplicate", "-D",
            action="store_true",
            help="Enable deduplication of files with identical content based on hash values"
        )
        parser.add_argument(
            "--dedup-test", 
            action="store_true",
            help="Run deduplication in test mode (process only first few groups)"
        )
        parser.add_argument(
            "--dedup-max-groups",
            type=int,
            default=3,
            help="Maximum number of duplicate groups to process in test mode (default: 3)"
        )
        parser.add_argument(
            "--dedup-no-rename",
            action="store_true",
            help="Disable renaming of non-surviving duplicates"
        )
        parser.add_argument(
            "--dedup-delete",
            action="store_true",
            help="Delete duplicate files after relinking (instead of renaming with dup- prefix)"
        )

        args = parser.parse_args()
        self.only_linkmapping = args.linkmap_only

        self.source_paths = args.source_paths
        self.destination_path = args.destination
        self.file_types = args.file_types
        self.preserve_folder_structure = not args.flatten
        self.exclude_dot_folders = not args.include_dot_folders
        # hash_all_files: default True, can be overridden by --hash-all-files or --no-hash-files
        self.hash_all_files = args.hash_all_files if args.hash_all_files is not None else True
        self.analyze_only = args.analyze_only
        self.deduplicate_files = args.deduplicate
        self.deduplicate_test_mode = args.dedup_test
        self.deduplicate_max_groups = args.dedup_max_groups
        self.deduplicate_rename_mode = not args.dedup_no_rename
        self.deduplicate_delete_mode = args.dedup_delete

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

        #if self.hash_all_files and not self.destination_path:
        #    if len(self.source_paths)==1:
        #        self.destination_path = path
        
        # Validate destination path (only required if not in analyze-only mode)
        if not self.destination_path and not self.analyze_only:
            print("No destination path but not in Analyze Only mode. ")
        #    raise ValueError("Destination path is required")

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
        summary += f"  Hash all files: {self.hash_all_files}\n"
        summary += f"  Analyze only mode: {self.analyze_only}\n"
        summary += f"  Deduplicate files: {self.deduplicate_files}\n"
        if self.deduplicate_files:
            summary += f"    Test mode: {self.deduplicate_test_mode}\n"
            summary += f"    Max groups: {self.deduplicate_max_groups}\n"
            summary += f"    Rename mode: {self.deduplicate_rename_mode}\n"
        return summary


# Global config manager instance
config_manager = ConfigManager()
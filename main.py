#!/usr/bin/env python3

"""
Main entry point for the Obsidian Vault Merger tool.
Orchestrates the merging of multiple Obsidian vaults into a single vault.
"""

import os
from config_manager import config_manager
from file_scanner import file_scanner
from collision_resolver import collision_resolver
from file_copier import file_copier
from link_processor import link_processor
from report_generator import report_generator
from logger import logger


def main():
    """
    Main function that orchestrates the vault merging process.
    """
    try:
        # Parse command-line arguments
        config_manager.parse_arguments()
        
        if config_manager.only_linkmapping:
            config_manager.destination_path= config_manager.destination_path or config_manager.source_paths[0]
            link_processor.generate_link_mapping_file()
            return

        # Handle analyze-only mode
        if config_manager.analyze_only:
            # For analyze-only mode, use the first source path as both source and destination
            if len(config_manager.source_paths) != 1:
                raise ValueError("Analyze-only mode requires exactly one vault path")
            
            # Use provided destination if given, otherwise use source path
            if config_manager.destination_path:
                # Destination was provided, use it
                pass
            else:
                # Destination not provided, use source path as destination
                config_manager.destination_path = config_manager.source_paths[0]
            
            # Validate path
            if not os.path.exists(config_manager.destination_path):
                raise ValueError(f"Vault path does not exist: {config_manager.destination_path}")
            if not os.path.isdir(config_manager.destination_path):
                raise ValueError(f"Vault path is not a directory: {config_manager.destination_path}")
            
            # Log configuration summary
            logger.info(config_manager.get_config_summary())
            
            # Standalone Link Analysis
            logger.info("=== Standalone Link Analysis ===")
            link_processor.analyze_links_standalone()
            
            if config_manager.hash_all_files:
                link_processor.process_links()

            logger.info("Link analysis completed successfully!")
            return
        
        # Normal merging mode
        # Validate paths
        config_manager.validate_paths()
        
        # Log configuration summary
        logger.info(config_manager.get_config_summary())
        
        # Phase 1: Analysis
        logger.info("=== Phase 1: Analysis ===")
        file_scanner.scan_vaults()
        
        # Phase 2: Collision Resolution
        logger.info("=== Phase 2: Collision Resolution ===")
        collision_resolver.resolve_collisions()
        
        # Phase 3: File Copying
        logger.info("=== Phase 3: File Copying ===")
        file_copier.copy_files()
        
        # Phase 4: Link Processing
        logger.info("=== Phase 4: Link Processing ===")
        
        # Check if we should calculate hashes for all files (single source path without -o flag)
        if len(config_manager.source_paths) == 1 and not config_manager.analyze_only:
            # Single source path provided without analyze-only flag, treat it like analyze-only mode
            logger.info("Single vault detected, enabling hash calculation for all files...")
            config_manager.hash_all_files = True
        
        link_processor.process_links()
        
        # Phase 5: Report Generation
        logger.info("=== Phase 5: Report Generation ===")
        report_generator.generate_merge_report()
        
        logger.info("Vault merging completed successfully!")
        
    except Exception as e:
        logger.error(f"An error occurred during vault merging: {e}")
        raise


if __name__ == "__main__":
    main()

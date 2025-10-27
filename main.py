#!/usr/bin/env python3

"""
Main entry point for the Obsidian Vault Merger tool.
Orchestrates the merging of multiple Obsidian vaults into a single vault.
"""

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

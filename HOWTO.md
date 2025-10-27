# Obsidian Vault Merger - How To Use

This project provides tools for merging multiple Obsidian vaults and handling file duplicates.

## Main Components

### 1. Main Application (main.py)
- Entry point for the Obsidian vault merger
- Handles command-line arguments for source and target directories
- Coordinates the merging process

### 2. Configuration Manager (config_manager.py)
- Manages application configuration
- Handles loading and saving of settings
- Provides default configurations

### 3. File Scanner (file_scanner.py)
- Scans directories for files to be processed
- Identifies file types and metadata
- Prepares file lists for merging

### 4. File Copier (file_copier.py)
- Copies files from source to target directories
- Handles file conflicts and naming conventions
- Manages file permissions and metadata

### 5. Link Processor (link_processor.py)
- Processes and updates internal links in markdown files
- Handles link redirection after file moves
- Maintains link integrity across vaults

### 6. Collision Resolver (collision_resolver.py)
- Resolves file name conflicts during merging
- Implements renaming strategies for duplicate files
- Tracks file mappings and changes

### 7. Report Generator (report_generator.py)
- Generates detailed reports of the merging process
- Creates HTML reports with statistics and logs
- Provides summaries of file operations

### 8. Logger (logger.py)
- Implements logging functionality for the application
- Handles different log levels and output formats
- Maintains operation history

## Utility Scripts

### 1. Duplicate File Finder (find_duplicate_files.py)
- Identifies duplicate files based on hash codes
- Scans link mapping files for duplicate entries
- Excludes files without valid hash codes

### 2. Duplicate Counter (count_duplicates.py)
- Counts duplicate hash codes in link mapping files
- Provides statistics on file duplication
- Excludes entries without valid hash codes from processing

## Usage

1. Run the main application with source and target directory arguments:
   ```
   python main.py <source_directory> <target_directory>
   ```

2. Configure settings in the generated config file as needed

3. Check the generated reports in the .merge_reports directory

4. Review logs in the .merge_logs directory

## Additional Notes

- The application automatically handles file conflicts and link updates
- All operations are logged for review and debugging
- Reports provide detailed information about the merging process
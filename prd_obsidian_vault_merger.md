# Product Requirements Document: Obsidian Vault Merger

## 1. Overview

### 1.1 Purpose
This document outlines the requirements for a tool that merges multiple Obsidian vaults into a single vault while preserving file integrity and maintaining internal link consistency.

### 1.2 Scope
The tool will combine multiple Obsidian vaults, handle filename collisions, preserve folder structures, and update internal links to reflect any file renames.

## 2. Project Objectives

### 2.1 Primary Objectives
- Merge multiple Obsidian vaults into a single destination vault
- Preserve original folder structures from source vaults
- Handle filename collisions by appending sequential numbers (#1, #2, etc.) so that file.md --> file#1.md
- Map and update all internal links to reflect renamed files
- Ignore dot-prefixed folders (e.g., .git, .obsidian) during merging

### 2.2 Secondary Objectives
- Generate a mapping file of all internal links for reference
- while going through the files for generating the link list, Calculate and note down the hash values for all files as well, in order to remove duplicates later with a different tool 
- Provide configurable source and destination paths
- Support both wikilinks ([[file]]) and markdown links ([file](path/to/file))
- Maintain file metadata where possible

## 3. Technical Requirements

### 3.1 Input Requirements
- Configurable paths for multiple source Obsidian vaults
- Configurable path for destination merged vault
- Support for standard Obsidian file types (primarily .md files)
- Support for common attachment types (images, PDFs, etc.)

### 3.2 File Handling Requirements
- Traverse all subdirectories in source vaults
- Skip any folders starting with a dot (.)
- Identify all files with potential name collisions
- Rename files with collisions using #1, #2, #3 pattern
- Preserve file content and modification times where possible

### 3.3 Link Processing Requirements
- Identify all internal links in markdown files
- Create mapping of links pointing to target files
- Update links in files when target files are renamed
- Support both wikilink and markdown link formats
- Generate comprehensive link mapping file

### 3.4 Output Requirements
- Merged vault with preserved folder structures
- Link mapping file showing all internal references
- Produce a comprehensive HTML log file for each merge 
- Log of all file renames due to collisions
- Error report for any unresolved links

## 4. Implementation Approach

### 4.1 Phase 1: Analysis and Mapping
1. Scan all source vaults to identify files and folder structures
2. Identify all internal links across all markdown files
3. Create comprehensive link mapping file
4. Detect potential filename collisions

### 4.2 Phase 2: File Processing and Copying
1. Copy files from source vaults to destination vault
2. Preserve folder structures during copying
3. Handle filename collisions by renaming files
4. Log all file renames for link updating

### 4.3 Phase 3: Link Updating
1. Update internal links in all markdown files
2. Use rename log to map old filenames to new filenames
3. Validate link integrity after updates
4. Generate final report

## 5. File Collision Resolution Strategy

When two or more files have the same name (including extension):
1. The first file encountered keeps its original name
2. Subsequent files with the same name are renamed with a sequential number
3. Pattern: `filename#1.extension`, `filename#2.extension`, etc.
4. All links pointing to renamed files are updated accordingly

Example:
- Source Vault 1: `note.md`
- Source Vault 2: `note.md`
- Result: `note.md` and `note#1.md`
- All links to the second note are updated to point to `note#1.md`

## 6. Link Mapping and Updating Process

### 6.1 Link Detection
- Scan all markdown files for wikilinks: `[[filename]]` or `[[filename|display]]`
- Scan all markdown files for markdown links: `[text](filename.md)` or `[text](path/filename.md)`
- Record each link with its source file and target file

### 6.2 Link Mapping File
- Create a single file listing all links in format: `target_file.md <- source_file.md`
- One link per line for easy parsing
- This file will be used to update links when files are renamed

### 6.3 Link Updating
- After file copying and renaming, scan all markdown files again
- For each link, check if the target file was renamed
- Update links to point to new filenames using the rename log
- Preserve link display text and formatting

## 7. Excluded Items
- Dot-prefixed folders (e.g., .git, .obsidian) will not be copied
- These must be manually copied if needed in the destination vault
- Files in dot-prefixed folders will not be processed for links

## 8. Configuration Requirements
- Source vault paths (multiple)
- Destination vault path
- File types to include/exclude (configurable)
- Option to flatten directory structure or preserve hierarchy

## 9. Error Handling
- Log files that cannot be processed
- Report unresolved links after processing
- Handle permission errors gracefully
- Continue processing other files when individual files fail

## 10. Success Criteria
- All files from source vaults are present in destination vault
- No data loss from source vaults
- All internal links correctly point to their targets
- Folder structures preserved according to user preference
- Comprehensive logs of all operations
- These criteria are being checked after each vault merging and are part of the report. 
# Deduplication Architecture

## Overview

The deduplication functionality has been rebuilt from scratch in `deduplication_handler.py`. This document describes how it works.

## Process Flow

### 1. Initialization
- Reads configuration from `config_manager`
- Locates the `linkmap.txt` file (generated in Phase 4)
- Prepares for processing

### 2. Identify Sibling Groups
```python
identify_sibling_groups()
```
- Reads the linkmap.txt file
- Parses format: `SOURCE ; TARGET ; HASH`
- Groups files by hash value
- Identifies files with identical hashes (siblings)
- Stores in `self.sibling_groups` dict

**Key Logic:**
```python
# hash_to_files = defaultdict(set)
# Only keep hashes with multiple files (len > 1)
self.sibling_groups[file_hash] = sorted(list(files))
```

### 3. Select Survivors
```python
select_survivors()
```
- For each sibling group, selects the file with shortest filename
- Strategy: `min(files, key=lambda x: len(os.path.basename(x)))`
- Builds `duplicate_to_survivor` mapping for link updates

**Example:**
- Files: `["notes/old-file.md", "notes/old-file-backup.md"]`
- Survivor: `"notes/old-file.md"` (shortest filename)

### 4. Update Internal Links
```python
update_internal_links()
```
- Processes ALL markdown files in the vault
- Updates both wikilinks and markdown links
- Changes links from duplicates to survivors

**Wikilinks:**
- Pattern: `[[filename]]` or `[[filename|display]]`
- Updates filename part
- Preserves display text

**Markdown Links:**
- Pattern: `[text](path/filename.md)`
- Updates target path
- Preserves link text

**Link Update Examples:**
```markdown
# Before:
[[my-notes-2024]]
[Read more](notes/my-notes-2024.md)

# After (if my-notes-2024.md is duplicate of my-notes.md):
[[my-notes]]
[Read more](notes/my-notes.md)
```

### 5. Rename Non-Survivors
```python
rename_non_survivors()
```
- Adds "dup-" prefix to non-surviving files
- Makes them easy to identify
- Can be deleted later manually
- Respects `--dedup-no-rename` flag

**Example:**
- Original: `notes/old-file-backup.md`
- Renamed: `notes/dup-old-file-backup.md`

## Data Structures

### Core Attributes
```python
self.vault_path: str              # Path to vault
self.link_mapping_file: str      # Path to linkmap.txt
self.sibling_groups: Dict[str, List[str]]  # hash -> [files]
self.survivors: Dict[str, str]              # hash -> survivor
self.duplicate_to_survivor: Dict[str, str]  # duplicate -> survivor
self.renamed_files: List[Dict]              # Track renamed files
self.updated_links_count: int     # Count of updated links
```

## Configuration Options

### Command-Line Flags
- `--deduplicate` / `-D`: Enable deduplication
- `--dedup-test`: Test mode (limited groups)
- `--dedup-max-groups N`: Limit to N groups in test mode
- `--dedup-no-rename`: Don't rename duplicates (just update links)

### Integration with Main Workflow
```python
# In main.py Phase 6:
if config_manager.deduplicate_files:
    logger.info("=== Phase 6: Deduplication ===")
    deduplication_handler.initialize()
    deduplication_handler.process_duplicates()
```

## Key Requirements Met

✅ Groups files with identical hashes into "siblings"  
✅ Selects "survivor" for each group (shortest filename)  
✅ Updates ALL internal links to point to survivors  
✅ Handles both wikilinks and markdown links  
✅ Renames non-surviving files with "dup-" prefix  
✅ Supports test mode for safe testing  
✅ Comprehensive logging and reporting  

## Usage Examples

```bash
# Full deduplication
python main.py /path/to/vault1 /path/to/vault2 -d /path/to/merged \
    --hash-all-files --deduplicate

# Test mode (safe, limited)
python main.py /path/to/merged --analyze-only \
    --deduplicate --dedup-test --dedup-max-groups 5

# Deduplicate without renaming
python main.py /path/to/vault -d /path/to/dest \
    --hash-all-files --deduplicate --dedup-no-rename
```

## File Formats

### Input: linkmap.txt
```plaintext
source-file.md ; target-file1.md ; abc123def456...
source-file.md ; target-file2.md ; abc123def456...  # Same hash = duplicate
target-file1.md ; target-file3.md ; xyz789ghi012...
```

### Processing
1. Parse hash values
2. Group by hash: `{"abc123...": [target-file1.md, target-file2.md]}`
3. Select survivor: `target-file1.md` (shortest)
4. Update links: All links to `target-file2.md` → `target-file1.md`
5. Rename: `target-file2.md` → `dup-target-file2.md`

## Error Handling

- Missing linkmap.txt: Logs warning, skips deduplication
- Invalid hash format: Skips entries with "ERROR", "NOT_FOUND", "unknown"
- File rename failures: Logs error, continues with other files
- Link update failures: Logs error for that file, continues processing

## Performance Considerations

- Uses `set()` for hash grouping to avoid duplicate entries
- Sorts files for consistent survivor selection
- Processes all .md files in a single pass
- Tracks counts for summary reporting


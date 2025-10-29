# Obsidian Vault Merger

A tool to merge multiple Obsidian vaults into a single vault while preserving file integrity and maintaining internal link consistency.

## Features

- Merge multiple Obsidian vaults into a single destination vault
- Preserve original folder structures from source vaults
- Handle filename collisions by appending sequential numbers (file~1, file~2, etc.)
- Map and update all internal links to reflect renamed files
- Deduplicate files with identical content based on hash values
- Ignore dot-prefixed folders (e.g., .git, .obsidian) during merging
- Generate a mapping file of all internal links for reference
- Produce a comprehensive HTML log file for each merge
- Log of all file renames due to collisions
- Error report for any unresolved links

## Installation

1. Clone this repository
2. Install dependencies using uv:
   ```
   uv sync
   ```

## Web Interface

Launch a beautiful Gradio web interface:

```bash
python web_interface.py
```

Access the interface at `http://localhost:7860`

The web interface provides:
- Visual configuration of all options
- Real-time progress tracking
- Inline HTML report viewing
- User-friendly form inputs

## Common Workflows

### Basic Merge

Merge two vaults without deduplication:

```bash
python main.py /path/to/vault1 /path/to/vault2 -d /path/to/merged
```

### Merge with Deduplication

Merge vaults and deduplicate files with identical content:

```bash
python main.py /path/to/vault1 /path/to/vault2 -d /path/to/merged --deduplicate
```

**What happens:**
1. Vaults are merged
2. Hashes are calculated for all files (enabled by default)
3. Duplicate files are identified
4. Survivors are selected (shortest filename)
5. All links are updated to point to survivors
6. Duplicates are renamed with `dup-` prefix

**Note:** Hash calculation is enabled by default.

### Analyze Existing Vault

Analyze an existing vault for links and hashes:

```bash
python main.py /path/to/vault --analyze-only
```

### Deduplicate Existing Merged Vault

After merging, deduplicate the result:

```bash
# Step 1: Merge (hashes calculated by default)
python main.py vault1 vault2 -d merged

# Step 2: Deduplicate
python main.py merged --analyze-only --deduplicate
```

### Test Deduplication Safely

Test deduplication on a merged vault with limited groups:

```bash
python main.py /path/to/merged --analyze-only --deduplicate --dedup-test --dedup-max-groups 5
```

### Clean Up Deduplicated Files

After deduplication, you may want to permanently delete the duplicate files that were renamed with the `dup-` prefix. A cleanup script is provided for this purpose:

```bash
# To delete all files starting with 'dup-' in a specific vault
./delete_deduped_from_vault.sh /path/to/vault

# To delete all files starting with 'dup-' in the current directory
./delete_deduped_from_vault.sh
```

The script will ask for confirmation before deleting any files. This is useful for permanently removing duplicate files that were preserved during the deduplication process.

## Usage

```
python main.py [source_paths]... -d [destination_path] [options]
```

### Arguments

- `source_paths`: Paths to source Obsidian vaults (one or more)
- `-d, --destination`: Path to destination vault (required)

### Options

- `-f, --file-types`: File types to include (default: .md)
- `--flatten, -l`: Flatten directory structure instead of preserving it
- `--include-dot-folders, -i`: Include dot-prefixed folders (default: exclude)
- `--no-hash-files`: Disable hash calculation (enabled by default, required for deduplication)
- `--analyze-only, -o`: Analyze existing vault for links and hashes without merging (requires single vault path)
- `--deduplicate, -D`: Enable deduplication of files with identical content based on hash values
- `--dedup-test`: Run deduplication in test mode (process only first few groups)
- `--dedup-max-groups N`: Maximum number of duplicate groups to process in test mode (default: 3)
- `--dedup-no-rename`: Disable renaming of non-surviving duplicates

### Examples

Merge two vaults into a new vault:
```
python main.py /path/to/vault1 /path/to/vault2 -d /path/to/merged_vault
```

Merge vaults and include image files:
```
python main.py /path/to/vault1 /path/to/vault2 -d /path/to/merged_vault -f .md .png .jpg
```

Merge vaults and flatten directory structure:
```
python main.py /path/to/vault1 /path/to/vault2 -d /path/to/merged_vault --flatten
```

Merge vaults with deduplication enabled:
```
python main.py /path/to/vault1 /path/to/vault2 -d /path/to/merged_vault --hash-all-files --deduplicate
```

Test deduplication on a merged vault (safe mode with limited groups):
```
python main.py /path/to/merged_vault --analyze-only --deduplicate --dedup-test --dedup-max-groups 5
```

Analyze an existing vault for links and hashes (always calculates hashes for all files):
```
python main.py /path/to/existing_vault --analyze-only
```

## How It Works

1. **Configuration**: Set up source and destination paths
2. **Analysis**: Scan source vaults and identify files and folder structures
3. **Collision Detection**: Identify filename collisions across all vaults
4. **File Processing**: Copy files from source to destination with collision resolution
5. **Link Updating**: Update all internal links to reflect file renames
6. **Deduplication** (optional): Identify and remove files with identical content based on hash values
7. **Reporting**: Generate comprehensive reports of the merge operation

## Collision Resolution

When two or more files have the same name:
1. The first file encountered keeps its original name
2. Subsequent files with the same name are renamed with a sequential number
3. Pattern: `filename~1.extension`, `filename~2.extension`, etc.
4. All links pointing to renamed files are updated accordingly

## Link Processing

- Supports both wikilinks: `[[filename]]` or `[[filename|display]]`
- Supports markdown links: `[text](filename.md)` or `[text](path/filename.md)`
- Creates a link mapping file showing all internal references
- Updates links in files when target files are renamed

## Deduplication

When enabled with `--deduplicate`, the tool identifies files with identical content based on hash values and consolidates them:

### Process
1. Groups files with identical hashes into "sibling groups"
2. Selects a "survivor" for each group (the file with the shortest filename)
3. Updates all internal links in the entire vault to point to survivors instead of duplicates
4. Renames non-surviving duplicates with a "dup-" prefix (or deletes them if `--dedup-no-rename` is used)

### Link Updates
The tool automatically updates both types of Obsidian links:
- **Wikilinks**: `[[duplicate-file]]` → `[[survivor-file]]`
- **Markdown links**: `[text](duplicate-file.md)` → `[text](survivor-file.md)`

### Example
- File 1: `my-notes.md` and File 2: `my-notes-2024.md` have identical content (same hash)
- `my-notes.md` becomes the survivor (shorter filename)
- All wikilinks and markdown links to `my-notes-2024.md` are updated to point to `my-notes.md`
- `my-notes-2024.md` is renamed to `dup-my-notes-2024.md`

**Note:** The tool must be run with `--hash-all-files` to generate hash values required for deduplication.

## Output

The tool generates several output files in the destination vault:

- Merged vault with preserved folder structures
- Link mapping file showing all internal references
- Comprehensive HTML log file for each merge
- Log of all file renames due to collisions
- Error report for any unresolved links

## Requirements

- Python 3.13 or higher
- uv package manager

## License

MIT

## Main Script: `main.py`

The `main.py` script is the entry point for the Obsidian Vault Merger tool. It orchestrates the merging of multiple Obsidian vaults into a single vault by calling various modules.

### Modules

-   `config_manager`: Manages the configuration of the merging process, including parsing command-line arguments and validating paths.
-   `file_scanner`: Scans the source vaults to identify files and folder structures.
-   `collision_resolver`: Resolves filename collisions across all vaults.
-   `file_copier`: Copies files from source to destination, resolving collisions as needed.
-   `link_processor`: Processes and updates internal links within the vaults.
-   `report_generator`: Generates a comprehensive merge report.
-   `logger`: Handles logging of events during the merging process.

### Functions

-   `main()`: The main function that orchestrates the vault merging process. It performs the following steps:
    1.  Parses command-line arguments using `config_manager`.
    2.  Validates paths using `config_manager`.
    3.  Scans vaults using `file_scanner`.
    4.  Resolves collisions using `collision_resolver`.
    5.  Copies files using `file_copier`.
    6.  Processes links using `link_processor`.
    7.  Generates a merge report using `report_generator`.

### Classes

This script does not define any classes. It primarily uses functions from other modules to perform the vault merging process.
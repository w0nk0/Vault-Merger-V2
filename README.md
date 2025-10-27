# Obsidian Vault Merger

A tool to merge multiple Obsidian vaults into a single vault while preserving file integrity and maintaining internal link consistency.

## Features

- Merge multiple Obsidian vaults into a single destination vault
- Preserve original folder structures from source vaults
- Handle filename collisions by appending sequential numbers (#1, #2, etc.)
- Map and update all internal links to reflect renamed files
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

## Usage

```
python main.py [source_paths]... -d [destination_path] [options]
```

### Arguments

- `source_paths`: Paths to source Obsidian vaults (one or more)
- `-d, --destination`: Path to destination vault (required)

### Options

- `-f, --file-types`: File types to include (default: .md)
- `--flatten`: Flatten directory structure instead of preserving it
- `--include-dot-folders`: Include dot-prefixed folders (default: exclude)

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

## How It Works

1. **Configuration**: Set up source and destination paths
2. **Analysis**: Scan source vaults and identify files and folder structures
3. **Collision Detection**: Identify filename collisions across all vaults
4. **File Processing**: Copy files from source to destination with collision resolution
5. **Link Updating**: Update all internal links to reflect file renames
6. **Reporting**: Generate comprehensive reports of the merge operation

## Collision Resolution

When two or more files have the same name:
1. The first file encountered keeps its original name
2. Subsequent files with the same name are renamed with a sequential number
3. Pattern: `filename#1.extension`, `filename#2.extension`, etc.
4. All links pointing to renamed files are updated accordingly

## Link Processing

- Supports both wikilinks: `[[filename]]` or `[[filename|display]]`
- Supports markdown links: `[text](filename.md)` or `[text](path/filename.md)`
- Creates a link mapping file showing all internal references
- Updates links in files when target files are renamed

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
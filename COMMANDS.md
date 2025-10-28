# Command Reference

This document explains all available commands for the Obsidian Vault Merger tool.

## Basic Commands

### Merge Multiple Vaults

Merge two or more vaults into a single destination vault:

```bash
python main.py <source1> <source2> ... -d <destination> [options]
```

**Example:**
```bash
python main.py /path/to/vault1 /path/to/vault2 -d /path/to/merged_vault
```

### Analyze-Only Mode

Analyze an existing vault for links and hashes without merging:

```bash
python main.py <vault_path> --analyze-only [options]
```

**Example:**
```bash
python main.py /path/to/vault --analyze-only
```

### Generate Link Mapping Only

Generate the link mapping file without merging or analyzing:

```bash
python main.py <vault_path> --linkmap-only
```

**Example:**
```bash
python main.py /path/to/vault --linkmap-only
```

## Command-Line Options

### Basic Options

#### `-d, --destination <path>`
Path to the destination vault (required for merging)

#### `-f, --file-types <types>`
File types to include (default: all files)

**Example:**
```bash
--file-types .md .png .jpg
```

#### `--flatten, -l`
Flatten directory structure instead of preserving it

#### `--include-dot-folders, -i`
Include dot-prefixed folders (default: excluded)

### Hash Options

#### `--no-hash-files`
Disable hash calculation (hash calculation is ON by default)

**Note:** Hash calculation is enabled by default. Disable only if you don't need deduplication.

**Example:**
```bash
python main.py vault1 vault2 -d merged --no-hash-files
```

### Deduplication Options

#### `--deduplicate, -D`
Enable deduplication of files with identical content based on hash values

**Example:**
```bash
python main.py vault1 vault2 -d merged --hash-all-files --deduplicate
```

#### `--dedup-test`
Run deduplication in test mode (process only first few groups for safety)

**Example:**
```bash
python main.py vault --analyze-only --deduplicate --dedup-test
```

#### `--dedup-max-groups N`
Maximum number of duplicate groups to process in test mode (default: 3)

**Example:**
```bash
python main.py vault --analyze-only --deduplicate --dedup-test --dedup-max-groups 5
```

#### `--dedup-no-rename`
Disable renaming of non-surviving duplicates (they remain as-is, links still updated)

**Example:**
```bash
python main.py vault --analyze-only --deduplicate --dedup-no-rename
```

## Common Workflows

### 1. Basic Merge

Merge two vaults without deduplication:

```bash
python main.py /path/to/vault1 /path/to/vault2 -d /path/to/merged
```

### 2. Merge with Deduplication

Merge vaults and deduplicate files with identical content:

```bash
python main.py /path/to/vault1 /path/to/vault2 -d /path/to/merged \
    --deduplicate
```

**What happens:**
1. Vaults are merged
2. Hashes are calculated for all files (enabled by default)
3. Duplicate files are identified
4. Survivors are selected (shortest filename)
5. All links are updated to point to survivors
6. Duplicates are renamed with `dup-` prefix

**Note:** Hash calculation is enabled by default. You don't need `--hash-all-files` anymore.

### 3. Analyze Existing Vault

Analyze an existing vault for links and hashes:

```bash
python main.py /path/to/vault --analyze-only
```

### 4. Deduplicate Existing Merged Vault

After merging, deduplicate the result:

```bash
# Step 1: Merge (hashes calculated by default)
python main.py vault1 vault2 -d merged

# Step 2: Deduplicate
python main.py merged --analyze-only --deduplicate
```

### 5. Test Deduplication Safely

Test deduplication on a merged vault with limited groups:

```bash
python main.py /path/to/merged --analyze-only --deduplicate \
    --dedup-test --dedup-max-groups 5
```

### 6. Merge with Collision Resolution

Merge vaults with specific file types and flatten structure:

```bash
python main.py vault1 vault2 -d merged \
    --file-types .md .txt \
    --flatten
```

## Understanding Deduplication

### What is Deduplication?

Deduplication identifies files with **identical content** (same hash value) and consolidates them.

### How it Works

1. **Sibling Groups**: Files with identical hashes are grouped together
2. **Survivor Selection**: The file with the shortest filename becomes the "survivor"
3. **Link Updates**: All links to duplicate files are updated to point to the survivor
4. **File Renaming**: Non-surviving files are renamed with a `dup-` prefix

### Example

**Before deduplication:**
- `company.md` (content: "About us")
- `company-backup-2023.md` (same content)
- `company-backup-2024.md` (same content)

**After deduplication:**
- `company.md` (survivor - kept)
- `dup-company-backup-2023.md` (renamed)
- `dup-company-backup-2024.md` (renamed)

**Links updated:**
- `[[company-backup-2023]]` → `[[company]]`
- `[text](company-backup-2024.md)` → `[text](company.md)`

## Test Commands

Run the test suite to verify functionality:

### Integration Test
```bash
python test_integration.py
```

### Link Update Test
```bash
python test_deduplication_links.py
```

### Full Deduplication Test
```bash
python test_deduplication.py
```

## Troubleshooting

### "linkmap.txt not found"

You need to run with `--hash-all-files` first to generate hash values:

```bash
python main.py vault --analyze-only
python main.py vault --analyze-only --deduplicate
```

### Deduplication not running

Make sure you're using `--deduplicate` flag:

```bash
python main.py vault --analyze-only --deduplicate
```

### Files not being renamed

Check if `--dedup-no-rename` was used. Also ensure there are actual duplicate files (identical content).

### Links not being updated

Verify that:
1. Deduplication actually ran (check logs)
2. Hash values match for duplicate files
3. Survivors were selected correctly

## Output Files

The tool generates several output files:

### In Destination Vault

- `linkmap.txt` - Link mapping file with hash values
  - Format: `SOURCE ; TARGET ; HASH`
- `.merge_logs/` - Log files from operations
- `.merge_reports/` - HTML reports of merge operations

### After Deduplication

- Renamed files: `dup-<original-name>` prefix
- Updated markdown files with corrected links

## Quick Reference

| Command | Purpose |
|---------|---------|
| `python main.py vault1 vault2 -d merged` | Basic merge |
| `python main.py vault -o` | Analyze only |
| `python main.py vault -a` | Generate hashes |
| `python main.py vault -o -D` | Deduplicate |
| `python main.py vault -o -D --dedup-test` | Safe test mode |

## See Also

- `TESTING.md` - Detailed testing guide
- `DEDUPLICATION_ARCHITECTURE.md` - Technical architecture
- `README.md` - Project overview


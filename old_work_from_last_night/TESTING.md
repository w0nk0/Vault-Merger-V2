# Testing Guide

This document explains how to test the deduplication functionality.

## Test Files

Three test scripts are provided:

1. **`test_integration.py`** - Simple end-to-end test
2. **`test_deduplication.py`** - Comprehensive merge and deduplication test
3. **`test_deduplication_links.py`** - Test for link updates

## Quick Start

Run the simple integration test:

```bash
python test_integration.py
```

This will:
1. Create two test vaults with duplicate content
2. Merge them
3. Run deduplication
4. Verify results

## Test Scripts Explained

### test_integration.py

**Purpose:** Simple end-to-end verification that merge + deduplication works.

**What it does:**
- Creates two vaults (A and B)
- Vault A has: `notes/meeting.md` with content "Same meeting notes."
- Vault B has: `notes/meeting-backup.md` with IDENTICAL content
- Merges the vaults
- Runs deduplication
- Verifies that:
  - Survivor (`meeting.md`) exists
  - Duplicate (`meeting-backup.md`) was renamed to `dup-meeting-backup.md`
  - `linkmap.txt` was generated

**Expected Result:**
```
✓ Survivor 'meeting.md' exists
✓ Found 1 renamed duplicate(s):
  - dup-meeting-backup.md
✓ linkmap.txt exists
  - X entries
```

### test_deduplication.py

**Purpose:** Comprehensive test with multiple duplicates and collisions.

**What it does:**
- Creates test vault A and B with:
  - Files with duplicate content (different names, same hash)
  - Files with collisions (same names)
  - Files with links between them
- Runs full merge process
- Runs deduplication
- Verifies:
  - Collision resolution (file~1.md, file~2.md)
  - Duplicate renaming (dup- prefix)
  - Link updates

**Expected Structure:**
```
test_deduplication_vaults/
├── vault_a/
│   ├── notes/
│   │   ├── project-alpha.md
│   │   ├── project-beta.md
│   │   ├── ideas.md
│   │   └── summary.md
└── vault_b/
    ├── notes/
    │   ├── project-alpha-backup.md (SAME as project-alpha.md)
    │   ├── ideas-copy.md (SAME as ideas.md)
    │   └── other-ideas.md
    └── merged_vault/
        └── ...
```

### test_deduplication_links.py

**Purpose:** Verify that links are updated correctly after deduplication.

**What it does:**
- Creates a vault with:
  - Original file: `company.md` (content)
  - Duplicates: `company-backup-2023.md` and `company-backup-2024.md` (SAME content)
  - Files with links to duplicates
- Runs deduplication
- Verifies that all links point to the survivor

**Example:**
```markdown
# index.md - BEFORE
- [[company]]
- [[company-backup-2023]]
- [company info](company-backup-2024.md)

# index.md - AFTER (expected)
- [[company]] 
- [[company]] (was backup-2023)
- [company info](company.md) (was backup-2024)
```

## Running the Tests

### Basic Integration Test
```bash
python test_integration.py
```

### Full Deduplication Test
```bash
python test_deduplication.py
```

### Link Update Test
```bash
python test_deduplication_links.py
```

## What Each Test Verifies

### test_integration.py
- ✅ Merge works
- ✅ Hash calculation works
- ✅ Survivor selection (shortest filename)
- ✅ Duplicate renaming (dup- prefix)
- ✅ linkmap.txt generation

### test_deduplication.py
- ✅ Multiple duplicate groups
- ✅ Collision resolution (~1, ~2 pattern)
- ✅ Deduplication after collision resolution
- ✅ File renaming
- ✅ Structure preservation

### test_deduplication_links.py
- ✅ Wikilink updates: `[[duplicate]]` → `[[survivor]]`
- ✅ Markdown link updates: `[text](duplicate.md)` → `[text](survivor.md)`
- ✅ All links point to survivors
- ✅ No broken links

## Test Output Examples

### Successful Test
```
============================================================
INTEGRATION TEST: Merge + Deduplication
============================================================

✓ Created test vaults:
  - Vault A: test_integration/vault_a
  - Vault B: test_integration/vault_b
  - Destination: test_integration/merged

============================================================
Step 1: Merging vaults
============================================================

Running: python main.py vault_a vault_b -d merged --hash-all-files

✓ Merge completed

============================================================
Step 2: Deduplicating
============================================================

Running: python main.py merged --analyze-only --deduplicate

✓ Deduplication completed

============================================================
Step 3: Verifying Results
============================================================

✓ Survivor 'meeting.md' exists
✓ Found 1 renamed duplicate(s):
  - dup-meeting-backup.md
✓ linkmap.txt exists
  - 8 entries

============================================================
INTEGRATION TEST PASSED
============================================================
```

## Cleanup

Test files are created in:
- `test_integration/`
- `test_deduplication_vaults/`
- `test_link_deduplication/`

To clean up:
```bash
rm -rf test_integration test_deduplication_vaults test_link_deduplication
```

## Troubleshooting

### Test fails: "linkmap.txt not found"
- Run with `--hash-all-files` flag first
- Check that link processing completed successfully

### Test fails: "No duplicate files renamed"
- Check that files actually have identical content
- Verify hash values in linkmap.txt are identical

### Test fails: "Links not updated"
- Check that deduplication actually ran
- Verify link patterns are correct (wikilinks vs markdown links)

## Manual Testing

You can also test manually:

```bash
# 1. Create a test vault
mkdir test_vault
cd test_vault

# 2. Create files with identical content
echo "Content A" > file-a.md
echo "Content A" > file-b.md

# 3. Generate hash values
python ../main.py . --analyze-only

# 4. Run deduplication
python ../main.py . --analyze-only --deduplicate

# 5. Check results
ls -la  # Should see dup- prefix on one file
cat linkmap.txt  # Should show hash values
```

## Next Steps

After tests pass:
1. Use on real vaults
2. Test with `--dedup-test` flag first
3. Limit with `--dedup-max-groups N`
4. Review renamed files before deleting


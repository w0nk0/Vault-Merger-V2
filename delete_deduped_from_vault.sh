#!/bin/bash

# Script to delete all deduplicated files (those starting with "dup-") in a specific vault
# This will remove all files that were renamed during the deduplication process

VAULT_PATH=${1:-"."}

echo "This script will delete all files starting with 'dup-' in $VAULT_PATH and its subdirectories."
echo "These are typically files that were identified as duplicates during the deduplication process."
read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Find and delete all files starting with "dup-" in the specified path
    find "$VAULT_PATH" -type f -name "dup-*" -print -delete
    
    echo
    echo "Files starting with 'dup-' have been deleted from $VAULT_PATH."
    echo "Note: The original surviving files remain intact."
else
    echo "Operation cancelled."
fi
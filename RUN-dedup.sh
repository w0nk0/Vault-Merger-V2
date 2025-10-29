#!/bin/bash

# RUN-dedup.sh - Deduplicate existing merged vault
# Usage: ./RUN-dedup.sh vault_path

if [ $# -ne 1 ]; then
    echo "Usage: $0 vault_path"
    echo "Example: $0 /path/to/merged_vault"
    exit 1
fi

VAULT="$1"

if [ ! -d "$VAULT" ]; then
    echo "Error: Directory '$VAULT' does not exist"
    exit 1
fi

echo "Deduplicating vault: $VAULT"
echo "This will identify duplicate files and update all links."
echo ""

python main.py "$VAULT" --analyze-only --deduplicate


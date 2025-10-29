#!/bin/bash

# RUN-merge-dedup.sh - Merge vaults with deduplication enabled
# Usage: ./RUN-merge-dedup.sh vault1 [vault2 ...] destination

if [ $# -lt 2 ]; then
    echo "Usage: $0 vault1 [vault2 ...] destination"
    echo "Example: $0 /path/to/vault1 /path/to/vault2 /path/to/merged_output"
    exit 1
fi

# Get destination (last argument)
DEST="${@: -1}"

# Get all source vaults (all arguments except the last)
SOURCES="${@:1:$(($#-1))}"

echo "Merging vaults with deduplication:"
for source in $SOURCES; do
    echo "  - $source"
done
echo "Destination: $DEST"
echo ""

python main.py $SOURCES -d "$DEST" --deduplicate


#!/bin/bash

# RUN-merge.sh - Basic merge of multiple Obsidian vaults
# Usage: ./RUN-merge.sh vault1 [vault2 ...] destination

if [ $# -lt 2 ]; then
    echo "Usage: $0 vault1 [vault2 ...] destination"
    echo "Example: $0 /path/to/vault1 /path/to/vault2 /path/to/merged_output"
    exit 1
fi

# Get destination (last argument)
DEST="${@: -1}"

# Get all source vaults (all arguments except the last)
SOURCES="${@:1:$(($#-1))}"

echo "Merging vaults:"
for source in $SOURCES; do
    echo "  - $source"
done
echo "Destination: $DEST"
echo ""

python main.py $SOURCES -d "$DEST"


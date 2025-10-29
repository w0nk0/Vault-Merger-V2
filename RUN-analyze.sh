#!/bin/bash

# RUN-analyze.sh - Analyze existing vault for links and hashes
# Usage: ./RUN-analyze.sh vault_path

if [ $# -ne 1 ]; then
    echo "Usage: $0 vault_path"
    echo "Example: $0 /path/to/existing_vault"
    exit 1
fi

VAULT="$1"

if [ ! -d "$VAULT" ]; then
    echo "Error: Directory '$VAULT' does not exist"
    exit 1
fi

echo "Analyzing vault: $VAULT"
echo "This will scan for links and calculate file hashes."
echo ""

python main.py "$VAULT" --analyze-only


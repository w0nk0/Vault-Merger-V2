"""
CSV Tracker for v0.2 - Track processed images in CSV file.

Per RULES.md specifications: columns are hash, filename, summary.
"""

import csv
import os
from pathlib import Path
from datetime import datetime


class CSVTracker:
    """Tracks OCR processing results in CSV file."""
    
    def __init__(self, csv_path):
        """
        Initialize CSV tracker.
        
        Args:
            csv_path: Path to CSV file (relative to output directory)
        """
        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Ensure CSV file exists with header
        if not self.csv_path.exists():
            self._create_csv()
    
    def _create_csv(self):
        """Create CSV file with headers."""
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['hash', 'filename', 'summary'])
    
    def add_entry(self, hash_value, filename, summary):
        """
        Add entry to CSV.
        
        Args:
            hash_value: 8-character hash
            filename: Original image filename
            summary: Brief summary/description (first 100 chars of text)
        """
        # Truncate summary to reasonable length
        summary_short = summary[:100] if summary else ""
        
        with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([hash_value, filename, summary_short])
    
    def get_all_hashes(self):
        """
        Get all hashes currently in CSV.
        
        Returns:
            set: Set of hash strings
        """
        hashes = set()
        
        if not self.csv_path.exists():
            return hashes
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'hash' in row:
                    hashes.add(row['hash'].lower())
        
        return hashes


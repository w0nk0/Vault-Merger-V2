"""
CSV Tracker for v0.2 - Index of processed OCR documents.

This is an index (not a log) where each OCR'd document appears only once.
Columns: source_filename, results_filename, summary
"""

import csv
import os
from pathlib import Path
from datetime import datetime


class CSVTracker:
    """Tracks OCR processing results in CSV index file."""
    
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
            writer.writerow(['source_filename', 'results_filename', 'summary'])
    
    def add_entry(self, source_filename, results_filename, summary):
        """
        Add or update entry in CSV index.
        
        This ensures each document appears only once (by source filename).
        If entry exists, it updates it; otherwise adds new entry.
        
        Args:
            source_filename: Original source file path/name
            results_filename: Output OCR results file name
            summary: Document summary (extracted from document if available)
        """
        # Read existing entries
        entries = {}
        source_to_row = {}
        
        if self.csv_path.exists():
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    src = row.get('source_filename', '')
                    if src:
                        entries[src] = row
                        source_to_row[src] = len(entries) - 1
        
        # Update or add entry
        source_str = str(source_filename)
        entries[source_str] = {
            'source_filename': source_str,
            'results_filename': str(results_filename),
            'summary': str(summary) if summary else ""
        }
        
        # Write all entries back (this maintains the index - one entry per document)
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['source_filename', 'results_filename', 'summary'])
            # Write entries sorted by source filename for consistency
            for src in sorted(entries.keys()):
                row = entries[src]
                writer.writerow([
                    row['source_filename'],
                    row['results_filename'],
                    row['summary']
                ])
    
    def get_all_hashes(self):
        """
        Get all hashes currently in CSV (for backward compatibility).
        
        Note: This extracts hash from results_filename which follows pattern *_OCR_{hash}.*
        
        Returns:
            set: Set of hash strings
        """
        hashes = set()
        
        if not self.csv_path.exists():
            return hashes
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                results_fn = row.get('results_filename', '')
                # Extract hash from filename pattern: *_OCR_{hash}.{ext}
                if '_OCR_' in results_fn:
                    parts = results_fn.split('_OCR_')
                    if len(parts) >= 2:
                        hash_part = parts[1].split('.')[0]
                        if len(hash_part) == 8:  # 8-character hash
                            hashes.add(hash_part.lower())
        
        return hashes
    
    def entry_exists(self, source_filename):
        """
        Check if an entry exists for the given source filename.
        
        Args:
            source_filename: Source file path/name to check
            
        Returns:
            bool: True if entry exists
        """
        if not self.csv_path.exists():
            return False
        
        source_str = str(source_filename)
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('source_filename', '') == source_str:
                    return True
        
        return False


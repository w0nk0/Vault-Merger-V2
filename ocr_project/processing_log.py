"""
Processing Log for v0.2 - Human-readable markdown log file.

Per RULES.md: Logs all processing activities in ocr_processing_log.md
"""

from pathlib import Path
from datetime import datetime


class ProcessingLog:
    """Manages OCR processing log in markdown format."""
    
    def __init__(self, log_path):
        """
        Initialize processing log.
        
        Args:
            log_path: Path to log file (typically ocr_processing_log.md)
        """
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize log file if it doesn't exist
        if not self.log_path.exists():
            self._initialize_log()
    
    def _initialize_log(self):
        """Create initial log file with header."""
        with open(self.log_path, 'w', encoding='utf-8') as f:
            f.write("# OCR Processing Log\n\n")
            f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
    
    def log_processed(self, image_path, hash_value, output_file):
        """
        Log successfully processed image.
        
        Args:
            image_path: Path to original image
            hash_value: 8-character hash
            output_file: Path to generated markdown file
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(f"## Processed: {Path(image_path).name}\n\n")
            f.write(f"- **Timestamp**: {timestamp}\n")
            f.write(f"- **Hash**: `{hash_value}`\n")
            f.write(f"- **Output**: `{output_file}`\n")
            f.write(f"- **Source**: `{image_path}`\n\n")
            f.write("---\n\n")
    
    def log_skipped(self, image_path, hash_value, reason, existing_file=None):
        """
        Log skipped image (duplicate or error).
        
        Args:
            image_path: Path to image that was skipped
            hash_value: 8-character hash (or None if error)
            reason: Reason for skipping
            existing_file: Existing file that matched (for duplicates)
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(f"## Skipped: {Path(image_path).name}\n\n")
            f.write(f"- **Timestamp**: {timestamp}\n")
            if hash_value:
                f.write(f"- **Hash**: `{hash_value}`\n")
            if existing_file:
                f.write(f"- **Existing File**: `{existing_file}`\n")
            f.write(f"- **Reason**: {reason}\n")
            f.write(f"- **Source**: `{image_path}`\n\n")
            f.write("---\n\n")
    
    def log_error(self, image_path, error_type, error_message):
        """
        Log error during processing.
        
        Args:
            image_path: Path to image that caused error
            error_type: Type of error (e.g., "Corrupted Image", "Model Error")
            error_message: Detailed error message
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(f"## Error: {Path(image_path).name}\n\n")
            f.write(f"- **Timestamp**: {timestamp}\n")
            f.write(f"- **Error Type**: {error_type}\n")
            f.write(f"- **Error Message**: {error_message}\n")
            f.write(f"- **Source**: `{image_path}`\n\n")
            f.write("---\n\n")


"""
PDF processing module for OCR v0.2.

Handles PDF to image conversion for OCR processing.
"""

from pathlib import Path
from typing import List, Tuple
from PIL import Image
import tempfile
import os


def convert_pdf_to_images(pdf_path: str, dpi: int = 200) -> List[Tuple[Image.Image, int]]:
    """
    Convert PDF pages to PIL Images.
    
    Args:
        pdf_path: Path to PDF file
        dpi: Resolution for PDF rendering (default: 200)
        
    Returns:
        List of (PIL.Image, page_number) tuples
        
    Raises:
        Exception: If PDF conversion fails or pdf2image not available
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        raise Exception(
            "pdf2image library not installed. Install it with: "
            "uv pip install pdf2image. "
            "Note: You may also need poppler-utils installed on your system."
        )
    
    try:
        # Convert PDF pages to images
        images = convert_from_path(pdf_path, dpi=dpi)
        
        # Return list of (image, page_number) tuples
        return [(img, page_num + 1) for page_num, img in enumerate(images)]
        
    except Exception as e:
        raise Exception(f"Failed to convert PDF '{pdf_path}' to images: {str(e)}")


def is_pdf_file(file_path: Path) -> bool:
    """
    Check if file is a PDF.
    
    Args:
        file_path: Path to file
        
    Returns:
        bool: True if file is a PDF
    """
    return file_path.suffix.lower() in ['.pdf']


def process_pdf_for_ocr(pdf_path: str, dpi: int = 200) -> List[Tuple[Image.Image, int]]:
    """
    Process PDF file and return images ready for OCR.
    
    This is a convenience wrapper around convert_pdf_to_images.
    
    Args:
        pdf_path: Path to PDF file
        dpi: Resolution for PDF rendering (default: 200)
        
    Returns:
        List of (PIL.Image, page_number) tuples ready for OCR processing
    """
    return convert_pdf_to_images(pdf_path, dpi=dpi)


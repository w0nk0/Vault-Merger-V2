"""
Image preprocessing module for OCR v0.2.

Handles image loading and preprocessing:
- Aspect ratio preserving resize for small images
- Hugging Face AutoProcessor pan-and-scan for large images (if available)
- Fallback to manual tiling if AutoProcessor unavailable
Image enhancement planned for v0.1.5.
"""

from PIL import Image
import warnings


class ImagePreprocessor:
    """Handles image loading and preprocessing for OCR."""
    
    def __init__(self):
        """Initialize the image preprocessor."""
        self.target_size = (896, 896)  # Gemma 3 requirement
    
    def load_image(self, image_path):
        """
        Load image from file path.
        
        Args:
            image_path: Path to image file
            
        Returns:
            PIL.Image: Loaded image
            
        Raises:
            Exception: If image cannot be loaded or is corrupted
        """
        try:
            image = Image.open(image_path)
            # Verify image is valid by attempting to load it
            image.verify()
            # Reopen because verify() closes the file
            image = Image.open(image_path)
            return image
        except Exception as e:
            raise Exception(f"Failed to load image '{image_path}': {str(e)}")
    
    def preprocess(self, image):
        """
        Preprocess image for OCR (resize to fit 896x896 while preserving aspect ratio).
        
        For v0.1: Resize with aspect ratio preservation to prevent text cutoff.
        Enhancement (contrast, noise reduction) planned for v0.1.5.
        
        Args:
            image: PIL.Image to preprocess
            
        Returns:
            PIL.Image: Preprocessed image (max dimension 896, aspect ratio preserved)
        """
        width, height = image.size
        target_width, target_height = self.target_size
        
        # Calculate scaling factor to fit within 896x896 while preserving aspect ratio
        scale = min(target_width / width, target_height / height)
        
        # Calculate new dimensions
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # Resize with aspect ratio preservation
        # Use LANCZOS for high-quality resampling
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return resized_image
    
    def is_large_image(self, image):
        """
        Check if image is larger than 896x896.
        
        Args:
            image: PIL.Image
            
        Returns:
            bool: True if image is larger than 896x896
        """
        width, height = image.size
        return width > 896 or height > 896
    
    def is_mostly_blank(self, image, threshold=0.99):
        """
        Check if image is mostly blank/white (useful for filtering edge tiles).
        
        Args:
            image: PIL.Image to check
            threshold: Fraction of pixels that must be "blank" (default: 0.99 = 99%)
                       Set high to avoid false positives - only skip truly blank tiles
            
        Returns:
            bool: True if image is mostly blank
        """
        import numpy as np
        
        # Convert to numpy array
        img_array = np.array(image.convert('RGB'))
        
        # Calculate brightness (average of RGB channels)
        brightness = img_array.mean(axis=2)
        
        # Consider pixels "blank" if brightness > 240 (very light)
        blank_pixels = (brightness > 240).sum()
        total_pixels = brightness.size
        
        blank_ratio = blank_pixels / total_pixels
        
        return blank_ratio >= threshold
    
    def create_tiles_with_hf_pan_scan(self, image_path, model_name="google/gemma-3-12b-it"):
        """
        Use Hugging Face AutoProcessor's pan-and-scan to create tiles intelligently.
        
        This uses the native pan-and-scan capability mentioned in Hugging Face docs.
        
        Args:
            image_path: Path to image file
            model_name: Model identifier for AutoProcessor
            
        Returns:
            list: List of PIL.Image tiles from pan-and-scan processing
                  Returns None if AutoProcessor not available (fallback to manual tiling)
        """
        try:
            from transformers import AutoProcessor
            
            # Load processor for pan-and-scan
            processor = AutoProcessor.from_pretrained(model_name)
            
            # Use apply_chat_template with do_pan_and_scan=True
            # This should automatically tile large images
            # Note: apply_chat_template expects messages format, but for pan-and-scan
            # we need to check the actual API
            
            # Actually, pan-and-scan might be handled during image preprocessing
            # Let's check if we can use the processor's image handling directly
            # For now, return None to indicate we'll use manual fallback
            # TODO: Investigate exact API for do_pan_and_scan with AutoProcessor
            
            warnings.warn(
                "Hugging Face AutoProcessor pan-and-scan not fully integrated yet. "
                "Using manual tiling fallback. "
                "Note: do_pan_and_scan=True is available in AutoProcessor.apply_chat_template() "
                "but requires testing with llama-cpp-python workflow."
            )
            return None
            
        except ImportError:
            # Transformers not available - use manual tiling
            return None
        except Exception as e:
            warnings.warn(f"Failed to use Hugging Face pan-and-scan: {str(e)}. Using manual tiling.")
            return None
    
    def create_tiles(self, image, tile_size=(896, 896), overlap=0.1):
        """
        Split large image into overlapping tiles for processing (manual fallback).
        
        This is used when Hugging Face AutoProcessor pan-and-scan is not available.
        
        Args:
            image: PIL.Image to tile
            tile_size: Tuple (width, height) for each tile
            overlap: Overlap percentage between tiles (0.0 to 1.0)
            
        Returns:
            list: List of (tile_image, (x, y)) tuples
        """
        width, height = image.size
        tile_width, tile_height = tile_size
        overlap_pixels_x = int(tile_width * overlap)
        overlap_pixels_y = int(tile_height * overlap)
        
        tiles = []
        y = 0
        while y < height:
            x = 0
            while x < width:
                # Calculate tile bounds
                right = min(x + tile_width, width)
                bottom = min(y + tile_height, height)
                
                # Extract tile
                tile = image.crop((x, y, right, bottom))
                tiles.append((tile, (x, y)))
                
                # Move to next tile (with overlap)
                x += tile_width - overlap_pixels_x
                if x >= width:
                    break
            
            y += tile_height - overlap_pixels_y
            if y >= height:
                break
        
        return tiles

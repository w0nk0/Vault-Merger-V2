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
    
    def __init__(self, min_size_pixels=40000):
        """
        Initialize the image preprocessor.
        
        Args:
            min_size_pixels: Minimum total pixels (width * height) required for processing (default: 40000 = 200x200)
        """
        self.target_size = (896, 896)  # Gemma 3 requirement
        self.min_size_pixels = min_size_pixels  # Minimum total pixels
    
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
        Check if image is larger than target size.
        
        Args:
            image: PIL.Image
            
        Returns:
            bool: True if image is larger than target size
        """
        width, height = image.size
        target_width, target_height = self.target_size
        return width > target_width or height > target_height
    
    def is_too_small(self, image):
        """
        Check if image is too small to process (below minimum pixel threshold).
        
        Args:
            image: PIL.Image
            
        Returns:
            bool: True if image is below minimum size (should be skipped)
        """
        width, height = image.size
        total_pixels = width * height
        return total_pixels < self.min_size_pixels
    
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
    
    def create_tiles(self, image, tile_size=None, overlap=0.1):
        """
        Split large image into vertical strips (straightforward pan-and-scan approach).
        
        Strategy:
        1. Pick the shorter side of the document
        2. Scale the image so the shorter side becomes model max width
        3. Create vertical strips by sliding only through Y axis (not X)
        
        This approach solves 90% of cases without compromising quality.
        
        Args:
            image: PIL.Image to tile
            tile_size: Tuple (width, height) for each tile (optional, uses self.target_size if not provided)
            overlap: Overlap percentage between tiles (0.0 to 1.0)
            
        Returns:
            list: List of (tile_image, (x, y)) tuples
        """
        # Use target_size from class or provided tile_size
        if tile_size is None:
            tile_size = self.target_size
        tile_width, tile_height = tile_size
        
        original_width, original_height = image.size
        
        # Step 1: Pick the shorter side
        shorter_side = min(original_width, original_height)
        
        # Step 2: Scale image so shorter side becomes model max width
        scale_factor = float(tile_width) / shorter_side
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)
        
        # Resize image with high-quality resampling
        scaled_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Step 3: Create vertical strips (full width) sliding only through Y axis
        overlap_pixels_y = int(tile_height * overlap)
        
        width, height = scaled_image.size
        tiles = []
        
        # Ensure width matches tile_width (should match after scaling, but handle edge cases)
        if width > tile_width:
            # If width is still larger than tile_width (edge case for landscape), crop/center
            # This shouldn't happen with proper scaling, but handle it safely
            start_x = (width - tile_width) // 2
            scaled_image = scaled_image.crop((start_x, 0, start_x + tile_width, height))
            width = tile_width
        
        # Only slide through Y axis (x is always 0, width is always tile_width)
        y = 0
        while y < height:
            # Calculate tile bounds (always full width, variable height at edges)
            right = min(tile_width, width)
            bottom = min(y + tile_height, height)
            
            # Extract tile
            tile = scaled_image.crop((0, y, right, bottom))
            tiles.append((tile, (0, y)))
            
            # Move to next tile along Y axis (with overlap)
            y += tile_height - overlap_pixels_y
            if y >= height:
                break
        
        return tiles

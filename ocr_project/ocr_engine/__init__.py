"""
OCR Engine for v0.1 - Vision Language Model integration using llama.cpp.

Handles GGUF model loading and text extraction using Gemma 3.
Supports quantized models for efficient local inference.
"""

import os
from pathlib import Path
from llama_cpp import Llama
from llama_cpp.llama_chat_format import Llava15ChatHandler
import sys


class VisionOCREngine:
    """Vision OCR Engine using Gemma 3 VLM with llama.cpp (GGUF)."""
    
    def __init__(self, model_name, device=None, temperature=0.1, max_new_tokens=1024, do_sample=False, verbose=False):
        """
        Initialize OCR engine with GGUF model.
        
        Args:
            model_name: Path to model directory or GGUF file
            device: Device to use (for llama.cpp, typically "cpu" or "cuda", ignored for now)
            temperature: Sampling temperature (default: 0.1)
            max_new_tokens: Maximum tokens to generate (default: 1024)
            do_sample: Whether to use sampling (default: False, ignored for now)
            verbose: Whether to print verbose output (default: False)
        """
        self.model_name = model_name
        self.device_arg = device
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens
        self.do_sample = do_sample
        self.verbose = verbose
        
        # Find GGUF model files
        self.model_path, self.mmproj_path = self._find_model_files()
        
        # Load model
        self._load_model()
    
    def _find_model_files(self):
        """
        Find the main GGUF model and mmproj file.
        
        Returns:
            tuple: (model_path, mmproj_path)
        """
        model_path_str = str(self.model_name)
        
        # If it's a directory, look for GGUF files
        if os.path.isdir(model_path_str):
            files = os.listdir(model_path_str)
            
            # Find main model (usually largest or matches pattern)
            model_files = [f for f in files if f.endswith('.gguf') and 'mmproj' not in f.lower()]
            mmproj_files = [f for f in files if f.endswith('.gguf') and 'mmproj' in f.lower()]
            
            if not model_files:
                raise Exception(
                    f"No GGUF model file found in {model_path_str}. "
                    "Expected a .gguf file (e.g., gemma-3-12b-it-Q4_K_M.gguf)"
                )
            
            # Use largest model file if multiple found
            model_file = max(model_files, key=lambda f: os.path.getsize(os.path.join(model_path_str, f)))
            model_path = os.path.join(model_path_str, model_file)
            
            # Find mmproj file for vision
            mmproj_path = None
            if mmproj_files:
                mmproj_path = os.path.join(model_path_str, mmproj_files[0])
            
            return model_path, mmproj_path
        
        # If it's a single file
        elif os.path.isfile(model_path_str) and model_path_str.endswith('.gguf'):
            # Look for mmproj in same directory
            model_dir = os.path.dirname(model_path_str)
            mmproj_files = [f for f in os.listdir(model_dir) if f.endswith('.gguf') and 'mmproj' in f.lower()]
            
            mmproj_path = os.path.join(model_dir, mmproj_files[0]) if mmproj_files else None
            
            return model_path_str, mmproj_path
        else:
            raise Exception(
                f"Model path not found or invalid: {model_path_str}. "
                "Expected a directory with .gguf files or a .gguf file path."
            )
    
    def _vprint(self, *args, **kwargs):
        """Print only if verbose mode is enabled."""
        if self.verbose:
            print(*args, **kwargs)
    
    def _load_model(self):
        """Load the Vision Language Model using llama.cpp."""
        try:
            self._vprint(f"  Loading GGUF model: {os.path.basename(self.model_path)}")
            
            # Auto-detect GPU usage
            n_gpu_layers = 0
            if self.device_arg == "cuda":
                n_gpu_layers = -1  # Use all GPU layers (-1 = use all available)
                self._vprint("  Using GPU (CUDA) - all layers")
            elif self.device_arg is None or self.device_arg == "auto":
                # Auto-detect: try GPU first
                n_gpu_layers = -1  # Try all GPU layers, llama.cpp will fallback to CPU if GPU unavailable
                self._vprint("  Auto-detecting GPU (will fallback to CPU if unavailable)...")
            else:
                # CPU explicitly requested
                n_gpu_layers = 0
                self._vprint(f"  Using CPU")
            
            # Initialize chat handler for multimodal (LLaVA-style)
            chat_handler = None
            if self.mmproj_path:
                self._vprint(f"  Loading vision projection: {os.path.basename(self.mmproj_path)}")
                chat_handler = Llava15ChatHandler(
                    clip_model_path=self.mmproj_path
                )
            
            # Load the main model with increased context for images
            self.model = Llama(
                model_path=self.model_path,
                chat_handler=chat_handler,
                n_ctx=8192,  # Increased context window for image embeddings
                n_gpu_layers=n_gpu_layers,
                verbose=self.verbose  # Use verbose flag
            )
            
            self._vprint("  Model loaded successfully")
            
            # Verify GPU usage
            if n_gpu_layers > 0:
                # Check if actually using GPU by looking at verbose output
                # (This is a simple check - llama.cpp doesn't expose GPU status easily)
                self._vprint("  ⚠️  Note: Verify GPU usage - if processing is slow, GPU may not be enabled")
                self._vprint("  💡 Tip: Ensure llama-cpp-python was built with CUDA support")
            
        except Exception as e:
            raise Exception(f"FATAL: Model loading failed - {str(e)}. Aborting process.")
    
    def extract_text(self, image, prompt):
        """
        Extract text from image using VLM, or generate text from prompt only.
        
        Args:
            image: PIL.Image (preprocessed) or None for text-only inference
            prompt: Text prompt for OCR or text generation
            
        Returns:
            str: Extracted text or generated text
        """
        try:
            self._vprint("  Running inference...")
            
            # Build the full prompt
            full_prompt = prompt
            
            # Use create_chat_completion for multimodal or text-only
            # llama-cpp-python with Llava15ChatHandler expects image as base64 data URI
            
            # If image is None, do text-only inference
            if image is None:
                # Text-only mode (for summaries, etc.)
                messages = [
                    {
                        "role": "system",
                        "content": "You are a text analysis tool. Generate clear, concise summaries and analysis."
                    },
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ]
            elif self.mmproj_path:
                # Convert PIL Image to base64
                import base64
                from io import BytesIO
                
                # Convert image to base64
                buffer = BytesIO()
                image.save(buffer, format='PNG')
                image_bytes = buffer.getvalue()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                image_url = f"data:image/png;base64,{image_base64}"
                
                # Vision model - use chat format with base64 image
                # System message to suppress conversational formatting
                messages = [
                    {
                        "role": "system",
                        "content": "You are a text extraction tool. Output only the extracted text, no explanations or conversational formatting."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": image_url}},
                            {"type": "text", "text": full_prompt}
                        ]
                    }
                ]
                self._vprint(f"  Image encoded: {len(image_base64)} characters")
            else:
                # Text-only model (no vision)
                messages = [
                    {
                        "role": "system",
                        "content": "You are a text analysis tool. Generate clear, concise summaries and analysis."
                    },
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ]
            
            # Generate response using llama.cpp chat API
            self._vprint("  Generating response...")
            response = self.model.create_chat_completion(
                messages=messages,
                max_tokens=self.max_new_tokens,
                temperature=self.temperature if self.do_sample else 0.0,
            )
            
            # Extract text from response
            extracted_text = response['choices'][0]['message']['content'].strip()
            
            return extracted_text
            
        except Exception as e:
            raise Exception(f"Text extraction failed: {str(e)}")

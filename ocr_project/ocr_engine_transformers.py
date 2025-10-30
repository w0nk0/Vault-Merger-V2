"""
OCR Engine for Transformers-based models (safetensors).

Handles loading and inference for Transformers-based Vision Language Models.
Supports safetensors format models.
"""

import os
from pathlib import Path
import warnings


class TransformersOCREngine:
    """Vision OCR Engine using Transformers library (safetensors)."""
    
    def __init__(self, model_name, device=None, temperature=0.1, max_new_tokens=1024, do_sample=False):
        """
        Initialize OCR engine with Transformers model.
        
        Args:
            model_name: Path to model directory or Hugging Face model ID
            device: Device to use ("cuda", "cpu", "auto", etc.)
            temperature: Sampling temperature (default: 0.1)
            max_new_tokens: Maximum tokens to generate (default: 1024)
            do_sample: Whether to use sampling (default: False)
        """
        try:
            from transformers import AutoProcessor, AutoConfig
            import torch
        except ImportError as e:
            raise ImportError(
                "Transformers dependencies not installed. "
                "Please install: transformers, torch, accelerate, safetensors"
            ) from e
        
        self.model_name = model_name
        self.device_arg = device
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens
        self.do_sample = do_sample
        self.model = None
        self.processor = None
        self.torch = torch
        
        # Load model and processor
        self._load_model()
    
    def _load_model(self):
        """Load the Vision Language Model using Transformers."""
        try:
            # Import model loading functions
            from transformers import AutoProcessor, AutoConfig
            import sys
            
            model_path_str = str(self.model_name)
            
            print(f"  Loading Transformers model from: {model_path_str}")
            
            # Check if it's a local path and has custom modeling files
            is_local = os.path.isdir(model_path_str) or os.path.isfile(model_path_str)
            
            if is_local and os.path.exists(os.path.join(model_path_str, "modeling_deepseekocr.py")):
                # Custom model - load directly
                print(f"  Detected custom DeepSeek OCR model")
                sys.path.insert(0, model_path_str)
                try:
                    from modeling_deepseekocr import DeepseekOCRForCausalLM
                    config = AutoConfig.from_pretrained(model_path_str, trust_remote_code=True)
                    self.model = DeepseekOCRForCausalLM.from_pretrained(
                        model_path_str,
                        config=config,
                        dtype=self.torch.bfloat16 if self.device_arg == "cuda" else self.torch.float32,
                        device_map="auto" if self.device_arg == "auto" else self.device_arg,
                        trust_remote_code=True
                    )
                except ImportError as e:
                    raise Exception(f"Failed to load custom model: {str(e)}")
            else:
                # Standard model - try AutoModelForVision2Seq
                try:
                    from transformers import AutoModelForVision2Seq
                    self.model = AutoModelForVision2Seq.from_pretrained(
                        model_path_str,
                        torch_dtype=self.torch.bfloat16 if self.device_arg == "cuda" else self.torch.float32,
                        device_map="auto" if self.device_arg == "auto" else self.device_arg,
                        trust_remote_code=True
                    )
                except Exception as e:
                    warnings.warn(f"Failed to load with AutoModelForVision2Seq: {e}")
                    # Try AutoModelForCausalLM as fallback
                    from transformers import AutoModelForCausalLM
                    self.model = AutoModelForCausalLM.from_pretrained(
                        model_path_str,
                        torch_dtype=self.torch.bfloat16 if self.device_arg == "cuda" else self.torch.float32,
                        device_map="auto" if self.device_arg == "auto" else self.device_arg,
                        trust_remote_code=True
                    )
            
            # Load processor
            self.processor = AutoProcessor.from_pretrained(model_path_str, trust_remote_code=True)
            
            print("  Model loaded successfully")
            
            # Verify device
            if hasattr(self.model, 'device'):
                print(f"  Model on device: {self.model.device}")
            elif hasattr(self.model, 'hf_device_map'):
                print(f"  Model device map: {self.model.hf_device_map}")
            
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
            print("  Running inference...")
            
            if image is None:
                # Text-only mode (for summaries, etc.)
                # For DeepSeek OCR, we need to handle this differently
                # For now, skip text-only inference with Transformers
                raise Exception("Text-only inference not supported with Transformers engine")
            
            # Prepare inputs using processor
            from transformers.image_utils import load_image
            
            # Convert PIL Image if needed
            if hasattr(image, 'save'):
                inputs = self.processor(images=image, text=prompt, return_tensors="pt")
            else:
                inputs = self.processor(images=[image], text=prompt, return_tensors="pt")
            
            # Move inputs to model device
            if hasattr(self.model, 'device'):
                inputs = {k: v.to(self.model.device) for k, v in inputs.items() if hasattr(v, 'to')}
            
            # Generate
            print("  Generating response...")
            with self.torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=self.max_new_tokens,
                    temperature=self.temperature if self.do_sample else 0.0,
                    do_sample=self.do_sample,
                )
            
            # Decode output
            extracted_text = self.processor.decode(outputs[0], skip_special_tokens=True)
            
            # Remove the input prompt from the output if it's there
            if prompt in extracted_text:
                extracted_text = extracted_text.replace(prompt, "").strip()
            
            return extracted_text.strip()
            
        except Exception as e:
            raise Exception(f"Text extraction failed: {str(e)}")


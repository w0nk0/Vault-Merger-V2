"""
Main entry point for OCR v0.2 - Single file OCR processing with duplicate detection and tracking.

Command-line interface:
    uv run python -m ocr_project.main --model "google/gemma-3-12b-it" --input "document.jpg" --output "./output" [--device cuda]

Features:
- Hash-based duplicate detection
- CSV tracking
- Processing log
- Enhanced error handling
"""

import argparse
import sys
import os
import json
from pathlib import Path

# Hardcoded defaults per v0.1 spec
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_NEW_TOKENS = 1024
DEFAULT_DO_SAMPLE = False
DEFAULT_PROMPT = "Extract and transcribe all visible text from this image."

# Global verbose flag
VERBOSE = False


def vprint(*args, **kwargs):
    """Print only if verbose mode is enabled."""
    if VERBOSE:
        print(*args, **kwargs)


def parse_arguments():
    """Parse command-line arguments for v0.2."""
    parser = argparse.ArgumentParser(
        description="OCR v0.2: Single file OCR processing with duplicate detection and tracking"
    )
    global VERBOSE
    parser.add_argument(
        "--model",
        required=True,
        help="Model identifier (e.g., 'google/gemma-3-12b-it')"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input image file path"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output directory path"
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Device (cuda, cpu, mps). If not provided, auto-detect."
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help=f"Custom OCR prompt (default: '{DEFAULT_PROMPT}')"
    )
    parser.add_argument(
        "--template",
        type=str,
        default=None,
        help="Path to JSON schema template file for structured extraction"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output (model details, inference info, etc.)"
    )
    
    args = parser.parse_args()
    global VERBOSE
    VERBOSE = args.verbose
    return args


def _detect_model_format(model_path):
    """
    Detect if model is GGUF or Transformers format.
    
    Returns:
        str: "gguf" or "transformers"
    """
    model_path_str = str(model_path)
    
    # Check if it's a directory
    if os.path.isdir(model_path_str):
        files = os.listdir(model_path_str)
        
        # Check for GGUF files
        gguf_files = [f for f in files if f.endswith('.gguf')]
        if gguf_files:
            return "gguf"
        
        # Check for Transformers files (safetensors, config.json, tokenizer.json)
        transformers_files = [
            f for f in files 
            if f.endswith('.safetensors') or f == 'config.json' or 'tokenizer.json' in f
        ]
        if len(transformers_files) >= 2:  # At least config + safetensors or tokenizer
            return "transformers"
    
    # Default to GGUF for backward compatibility
    return "gguf"


def main():
    """Main entry point for OCR v0.2."""
    args = parse_arguments()
    
    # Detect model format
    model_format = _detect_model_format(args.model)
    vprint(f"Detected model format: {model_format}")
    
    # Handle JSON template if provided
    json_template = None
    if args.template:
        try:
            from json_template_handler import JSONTemplateHandler
        except ImportError:
            try:
                from ocr_project.json_template_handler import JSONTemplateHandler
            except ImportError:
                raise ImportError("Cannot import JSONTemplateHandler. Make sure json_template_handler.py exists.")
        
        json_template = JSONTemplateHandler(args.template)
        vprint(f"✓ Using JSON template: {args.template}")
    
    # Use custom prompt if provided, otherwise use default
    ocr_prompt = args.prompt if args.prompt else DEFAULT_PROMPT
    
    # Generate structured prompt if template is provided
    if json_template:
        ocr_prompt = json_template.generate_prompt(ocr_prompt)
    
    # Validate inputs
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Import modules
        try:
            # Try relative imports first (when running from parent directory)
            from ocr_project.image_processor import ImagePreprocessor
            from ocr_project.ocr_engine import VisionOCREngine
            from ocr_project.hash_manager import calculate_image_hash, check_duplicate
            from ocr_project.csv_tracker import CSVTracker
            from ocr_project.processing_log import ProcessingLog
        except ImportError:
            # Fall back to relative imports (when running from within ocr_project)
            from image_processor import ImagePreprocessor
            try:
                from ocr_engine import VisionOCREngine
            except ImportError:
                VisionOCREngine = None  # May not be available if using Transformers
            from hash_manager import calculate_image_hash, check_duplicate
            from csv_tracker import CSVTracker
            from processing_log import ProcessingLog
        
        # v0.2: Initialize tracking and logging
        csv_tracker = CSVTracker(output_dir / "ocr_results.csv")
        processing_log = ProcessingLog(output_dir / "ocr_processing_log.md")
        
        # v0.2: Calculate hash for duplicate detection
        vprint(f"Calculating hash for: {args.input}")
        image_hash = calculate_image_hash(str(input_path))
        vprint(f"  Hash: {image_hash}")
        
        # v0.2: Check for duplicates
        duplicate_check = check_duplicate(image_hash, output_dir)
        
        if duplicate_check['action'] == 'skip':
            # Duplicate found in OCR file - skip processing
            existing_file = duplicate_check['existing_files'][0] if duplicate_check['existing_files'] else "unknown"
            reason = f"Hash {image_hash} already exists in OCR file: {existing_file}"
            print(f"\n⚠️  Skipping duplicate image")
            print(f"   {reason}")
            
            processing_log.log_skipped(
                str(input_path),
                image_hash,
                reason,
                existing_file
            )
            
            print(f"   Logged to: {processing_log.log_path}")
            sys.exit(0)
        elif duplicate_check['is_duplicate']:
            # Hash found in non-OCR file - continue but log
            existing_file = duplicate_check['existing_files'][0] if duplicate_check['existing_files'] else "unknown"
            print(f"  Note: Hash found in non-OCR file {existing_file}, continuing...")
            processing_log.log_skipped(
                str(input_path),
                image_hash,
                f"Hash {image_hash} found in non-OCR file {existing_file}, continuing",
                existing_file
            )
        
        # Initialize image processor
        image_processor = ImagePreprocessor()
        
        # Load and preprocess image
        vprint(f"Loading image: {args.input}")
        try:
            image = image_processor.load_image(str(input_path))
            original_size = image.size
            vprint(f"  Original size: {original_size[0]}x{original_size[1]}")
            
            # Check if image needs tiling
            is_large = image_processor.is_large_image(image)
            
            if is_large:
                vprint(f"  Large image detected ({original_size[0]}x{original_size[1]})")
                # Try Hugging Face AutoProcessor pan-and-scan first
                vprint(f"  Attempting to use Hugging Face pan-and-scan...")
                hf_tiles = image_processor.create_tiles_with_hf_pan_scan(str(input_path))
                
                if hf_tiles is not None:
                    vprint(f"  ✅ Using Hugging Face pan-and-scan tiles")
                    tiles = [(tile, (0, 0)) for tile in hf_tiles]  # HF provides images, positions handled internally
                else:
                    vprint(f"  Using manual tiling strategy (fallback)")
                    # Fallback to manual tiling
                    tiles = image_processor.create_tiles(image, tile_size=(896, 896), overlap=0.1)
                    
                vprint(f"  Created {len(tiles)} tiles")
            else:
                # For smaller images, just resize with aspect ratio preservation
                preprocessed_image = image_processor.preprocess(image)
                tiles = [(preprocessed_image, (0, 0))]
                
        except Exception as e:
            # Corrupted image - log and skip
            error_msg = f"Failed to load/preprocess image: {str(e)}"
            print(f"\n❌ ERROR: {error_msg}", file=sys.stderr)
            processing_log.log_error(str(input_path), "Corrupted Image", error_msg)
            sys.exit(1)
        
        # Initialize OCR engine based on detected format
        vprint(f"Loading model: {args.model}")
        try:
            if model_format == "transformers":
                # Import Transformers engine
                try:
                    from ocr_engine_transformers import TransformersOCREngine
                except ImportError:
                    try:
                        from ocr_project.ocr_engine_transformers import TransformersOCREngine
                    except ImportError:
                        raise ImportError("Could not import TransformersOCREngine")
                
                ocr_engine = TransformersOCREngine(
                    model_name=args.model,
                    device=args.device if args.device else "auto",
                    temperature=DEFAULT_TEMPERATURE,
                    max_new_tokens=DEFAULT_MAX_NEW_TOKENS,
                    do_sample=DEFAULT_DO_SAMPLE
                )
            else:
                # GGUF engine
                if VisionOCREngine is None:
                    raise ImportError(
                        "Cannot import VisionOCREngine. "
                        "Make sure ocr_engine/__init__.py exists and llama-cpp-python is installed."
                    )
                
                ocr_engine = VisionOCREngine(
                    model_name=args.model,
                    device=args.device,
                    temperature=DEFAULT_TEMPERATURE,
                    max_new_tokens=DEFAULT_MAX_NEW_TOKENS,
                    do_sample=DEFAULT_DO_SAMPLE
                )
        except Exception as e:
            # Model loading failure - fatal error
            error_msg = f"Model loading failed: {str(e)}"
            print(f"\n❌ FATAL ERROR: {error_msg}", file=sys.stderr)
            processing_log.log_error(str(input_path), "Model Loading Failure", error_msg)
            sys.exit(1)
        
        # Separate extraction prompt from summary request
        # For tiled processing, we extract text first, then summarize if requested
        extraction_prompt = ocr_prompt
        generate_summary = False
        
        # Check if prompt asks for summary (common patterns)
        summary_keywords = ['summary', 'summarize', 'summarise', '## SUMMARY', 'SUMMARY ##']
        if any(keyword.lower() in ocr_prompt.lower() for keyword in summary_keywords):
            # Remove summary request from extraction prompt for tiles
            # Use a clean extraction-only prompt
            extraction_prompt = DEFAULT_PROMPT  # "Extract and transcribe all visible text from this image."
            generate_summary = True
            vprint("  ℹ️  Summary requested - will generate from combined text after extraction")
        
        # Extract text from each tile and combine
        vprint("Extracting text from image...")
        tile_texts = []
        
        for i, (tile_image, (x, y)) in enumerate(tiles):
            if len(tiles) > 1:
                vprint(f"  Processing tile {i+1}/{len(tiles)} (position: {x},{y})...")
            
            # Skip mostly blank tiles (edge tiles with no content)
            if len(tiles) > 1 and image_processor.is_mostly_blank(tile_image):
                vprint(f"  ⏭️  Skipping mostly blank tile {i+1} (position: {x},{y})")
                continue
            
            try:
                # Preprocess each tile (preserves aspect ratio, fits within 896x896)
                # For tiles from manual tiling, they're already cropped to ~896x896, but
                # preprocessing ensures they fit model requirements properly
                tile_to_process = image_processor.preprocess(tile_image)
                
                # Use extraction-only prompt (no summary request for individual tiles)
                tile_text = ocr_engine.extract_text(
                    image=tile_to_process,
                    prompt=extraction_prompt
                )
                
                # Filter out artifacts: sequences of consecutive numbers 1-100 (hallucination pattern)
                # But keep legitimate number sequences (invoice line items, etc.)
                if tile_text.strip():
                    lines = [line.strip() for line in tile_text.strip().split('\n') if line.strip()]
                    
                    # Only filter if it looks like a pure consecutive number sequence
                    if len(lines) > 15:  # Long sequences might be suspicious
                        # Check if lines are mostly single consecutive integers starting from 1
                        consecutive_numbers = 0
                        for idx, line in enumerate(lines[:50]):  # Check first 50 lines
                            if line.isdigit():
                                num = int(line)
                                # Consecutive numbers starting from 1 are suspicious (hallucinations)
                                if num == idx + 1:
                                    consecutive_numbers += 1
                        
                        # If it's a pure consecutive sequence (1, 2, 3, ...), it's likely an artifact
                        # But allow some breaks (invoice items might have gaps)
                        consecutive_ratio = consecutive_numbers / min(len(lines), 50)
                        if consecutive_ratio > 0.9 and len(lines) > 20:
                            # Also check that there's no other text mixed in
                            non_number_lines = sum(1 for line in lines if not (line.strip().isdigit() and line.strip().isnumeric()))
                            if non_number_lines / len(lines) < 0.1:  # Less than 10% non-number lines
                                print(f"  ⏭️  Filtering consecutive number sequence artifact from tile {i+1}")
                                continue
                    
                    tile_texts.append((x, y, tile_text))
                    
            except Exception as e:
                print(f"  ⚠️  Warning: Failed to process tile {i+1}: {str(e)}")
                # Continue with other tiles
                continue
        
        # Combine tile texts (for now, simple concatenation - could be improved)
        if len(tile_texts) == 0:
            extracted_text = ""
        elif len(tile_texts) == 1:
            extracted_text = tile_texts[0][2]  # Just the text
        else:
            # For multiple tiles, combine with separator
            # TODO: Improve combining logic to handle overlaps intelligently
            combined = []
            for x, y, text in sorted(tile_texts, key=lambda t: (t[1], t[0])):  # Sort by y, then x
                if text.strip():
                    combined.append(f"--- Tile at ({x},{y}) ---\n{text.strip()}\n")
            extracted_text = "\n\n".join(combined)
        
        # Generate summary from combined text if requested
        if generate_summary and extracted_text.strip():
            vprint("\nGenerating summary from combined text...")
            try:
                # Create a text-only summary prompt
                summary_prompt = f"""Based on the following extracted text from a document, create a summary section starting with "## SUMMARY ##" that summarizes the purpose and content of the document in one or two sentences.

Extracted text:
{extracted_text}

## SUMMARY ##"""
                
                # Generate summary using text-only inference (no image)
                # Note: llama-cpp-python can do text-only inference
                summary_text = ocr_engine.extract_text(
                    image=None,  # No image for summary
                    prompt=summary_prompt
                )
                
                # Append summary to extracted text
                extracted_text = f"{extracted_text}\n\n{summary_text}"
                vprint("  ✅ Summary generated")
            except Exception as e:
                print(f"  ⚠️  Warning: Failed to generate summary: {str(e)}")
                # Continue without summary
        
        # Handle JSON template extraction if provided
        is_json_mode = json_template is not None
        json_data = None
        
        if is_json_mode:
            vprint("Extracting JSON from output...")
            json_data = json_template.extract_json(extracted_text)
            
            if json_data:
                vprint("  ✓ JSON extracted successfully")
                
                # Validate JSON against schema
                is_valid, error_msg = json_template.validate(json_data)
                
                if is_valid:
                    vprint("  ✅ JSON validated against schema")
                else:
                    print(f"  ⚠️  JSON validation warning: {error_msg}")
                    print("  Continuing anyway...")
            else:
                print("  ⚠️  Failed to extract JSON, falling back to plain text")
                is_json_mode = False
        
        # Clean up extracted text (only for non-JSON mode)
        if not is_json_mode:
            try:
                # Basic cleanup: Remove trailing garbage patterns
                # Remove long sequences of repeated characters (e.g., "|  |  |  |  |")
                import re
                # Remove lines with only pipes/spaces (garbage patterns)
                lines = extracted_text.split('\n')
                cleaned_lines = []
                for line in lines:
                    # Skip lines that are mostly pipe characters or whitespace
                    if line.strip() and not re.match(r'^[\|\s\|]+$', line.strip()):
                        cleaned_lines.append(line)
                extracted_text = '\n'.join(cleaned_lines).strip()
                
            except Exception as e:
                # Text extraction failure - log and skip
                error_msg = f"Text extraction failed: {str(e)}"
                print(f"\n❌ ERROR: {error_msg}", file=sys.stderr)
                processing_log.log_error(str(input_path), "Text Extraction Error", error_msg)
                sys.exit(1)
        
        # v0.2: Generate output filename with hash
        input_stem = input_path.stem
        if is_json_mode and json_data:
            # Use JSON extension for structured output
            output_filename = f"{input_stem}_OCR_{image_hash}.json"
            output_path = output_dir / output_filename
            
            # Format and save JSON
            output_content = json_template.format_output(json_data)
        else:
            # Use markdown extension for plain text
            output_filename = f"{input_stem}_OCR_{image_hash}.md"
            output_path = output_dir / output_filename
            output_content = extracted_text
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        # v0.2: Track in CSV
        if is_json_mode and json_data:
            # For JSON output, use title or summary field
            summary = json_data.get('title', json_data.get('summary', ''))[:100] if isinstance(json_data, dict) else ""
        else:
            summary = extracted_text[:100].replace('\n', ' ') if extracted_text else ""
        csv_tracker.add_entry(image_hash, str(input_path), summary)
        
        # v0.2: Log successful processing
        processing_log.log_processed(str(input_path), image_hash, str(output_path))
        
        print(f"\n✅ OCR complete!")
        print(f"📄 Output saved to: {output_path}")
        print(f"📊 Tracked in CSV: {csv_tracker.csv_path}")
        print(f"📝 Logged to: {processing_log.log_path}")
        
        if is_json_mode and json_data:
            print(f"\n📋 Extracted JSON:\n{'-' * 60}")
            print(json.dumps(json_data, indent=2, ensure_ascii=False))
            print(f"{'-' * 60}\n")
        else:
            print(f"\n📝 Extracted text:\n{'-' * 60}")
            print(extracted_text)
            print(f"{'-' * 60}\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

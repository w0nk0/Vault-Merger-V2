"""
Main entry point for OCR v0.2 - Single or batch file OCR processing with duplicate detection and tracking.

Command-line interface:
    uv run python -m ocr_project.main --model "google/gemma-3-12b-it" --input "document.jpg" --output "./output" [--device cuda]
    uv run python -m ocr_project.main --model "model.gguf" --input "*.jpg" --output "./output" [--device cuda]

Features:
- Hash-based duplicate detection
- CSV tracking
- Processing log
- Enhanced error handling
- Wildcard/batch support
- Single model initialization for batch processing
"""

import argparse
import sys
import os
import json
import glob
from pathlib import Path

# Import OCR modules at module level
try:
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
        VisionOCREngine = None
    from hash_manager import calculate_image_hash, check_duplicate
    from csv_tracker import CSVTracker
    from processing_log import ProcessingLog

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
        description="OCR v0.2: Single or batch file OCR processing with duplicate detection and tracking"
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
        help="Input image file path or glob pattern (e.g., '*.jpg', 'folder/**/*.png')"
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


def _expand_input_pattern(input_pattern):
    """
    Expand input pattern to list of files.
    
    Args:
        input_pattern: File path or glob pattern
        
    Returns:
        List of file paths
    """
    path = Path(input_pattern)
    
    # If it's a wildcard pattern, expand it
    if '*' in str(input_pattern) or '?' in str(input_pattern) or '[' in str(input_pattern):
        files = sorted(glob.glob(str(input_pattern), recursive='**' in str(input_pattern)))
        return [Path(f) for f in files if Path(f).is_file()]
    # If it's a directory, get all image files
    elif path.is_dir():
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        files = []
        for ext in image_extensions:
            files.extend(path.glob(f'*{ext}'))
            files.extend(path.glob(f'*{ext.upper()}'))
        return sorted(files)
    # Single file
    elif path.is_file():
        return [path]
    else:
        raise FileNotFoundError(f"Input not found: {input_pattern}")


def process_single_image(input_path, ocr_engine, image_processor, csv_tracker, processing_log, 
                         output_dir, ocr_prompt, json_template, model_format, args, model_name):
    """
    Process a single image through the OCR pipeline.
    
    Args:
        input_path: Path to input image
        ocr_engine: Initialized OCR engine
        image_processor: Initialized image processor
        csv_tracker: CSV tracker
        processing_log: Processing log
        output_dir: Output directory
        ocr_prompt: OCR prompt
        json_template: JSON template handler (or None)
        model_format: Model format string
        args: Command-line arguments
        
    Returns:
        True if successful, False if skipped
    """
    try:
        # v0.2: Calculate hash for duplicate detection
        vprint(f"Calculating hash for: {input_path}")
        image_hash = calculate_image_hash(str(input_path))
        vprint(f"  Hash: {image_hash}")
        
        # v0.2: Check for duplicates
        duplicate_check = check_duplicate(image_hash, output_dir)
        
        if duplicate_check['action'] == 'skip':
            # Duplicate found in OCR file - skip processing
            existing_file = duplicate_check['existing_files'][0] if duplicate_check['existing_files'] else "unknown"
            reason = f"Hash {image_hash} already exists in OCR file: {existing_file}"
            print(f"⚠️  Skipping duplicate: {input_path.name}")
            
            processing_log.log_skipped(
                str(input_path),
                image_hash,
                reason,
                existing_file
            )
            return False
        elif duplicate_check['is_duplicate']:
            # Hash found in non-OCR file - continue but log
            existing_file = duplicate_check['existing_files'][0] if duplicate_check['existing_files'] else "unknown"
            vprint(f"  Note: Hash found in non-OCR file {existing_file}, continuing...")
            processing_log.log_skipped(
                str(input_path),
                image_hash,
                f"Hash {image_hash} found in non-OCR file {existing_file}, continuing",
                existing_file
            )
        
        # Load and preprocess image
        vprint(f"Loading image: {input_path}")
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
                hf_tiles = image_processor.create_tiles_with_hf_pan_scan(str(input_path), model_name)
                
                if hf_tiles is not None:
                    vprint(f"  ✅ Using Hugging Face pan-and-scan tiles")
                    tiles = [(tile, (0, 0)) for tile in hf_tiles]
                else:
                    vprint(f"  Using manual tiling strategy (fallback)")
                    tiles = image_processor.create_tiles(image, tile_size=(896, 896), overlap=0.1)
                    
                vprint(f"  Created {len(tiles)} tiles")
            else:
                # For smaller images, just resize with aspect ratio preservation
                preprocessed_image = image_processor.preprocess(image)
                tiles = [(preprocessed_image, (0, 0))]
                
        except Exception as e:
            # Corrupted image - log and skip
            error_msg = f"Failed to load/preprocess image: {str(e)}"
            print(f"❌ ERROR: {error_msg}", file=sys.stderr)
            processing_log.log_error(str(input_path), "Corrupted Image", error_msg)
            return False
        
        # Separate extraction prompt from summary request
        extraction_prompt = ocr_prompt
        generate_summary = False
        
        # Check if prompt asks for summary
        summary_keywords = ['summary', 'summarize', 'summarise', '## SUMMARY', 'SUMMARY ##']
        if any(keyword.lower() in ocr_prompt.lower() for keyword in summary_keywords):
            extraction_prompt = DEFAULT_PROMPT
            generate_summary = True
            vprint("  ℹ️  Summary requested - will generate from combined text after extraction")
        
        # Extract text from each tile and combine
        vprint("Extracting text from image...")
        tile_texts = []
        
        for i, (tile_image, (x, y)) in enumerate(tiles):
            if len(tiles) > 1:
                vprint(f"  Processing tile {i+1}/{len(tiles)} (position: {x},{y})...")
            
            # Skip mostly blank tiles
            if len(tiles) > 1 and image_processor.is_mostly_blank(tile_image):
                vprint(f"  ⏭️  Skipping mostly blank tile {i+1} (position: {x},{y})")
                continue
            
            try:
                tile_to_process = image_processor.preprocess(tile_image)
                tile_text = ocr_engine.extract_text(
                    image=tile_to_process,
                    prompt=extraction_prompt
                )
                
                # Filter artifacts
                if tile_text.strip():
                    lines = [line.strip() for line in tile_text.strip().split('\n') if line.strip()]
                    
                    if len(lines) > 15:
                        consecutive_numbers = 0
                        for idx, line in enumerate(lines[:50]):
                            if line.isdigit():
                                num = int(line)
                                if num == idx + 1:
                                    consecutive_numbers += 1
                        
                        consecutive_ratio = consecutive_numbers / min(len(lines), 50)
                        if consecutive_ratio > 0.9 and len(lines) > 20:
                            non_number_lines = sum(1 for line in lines if not (line.strip().isdigit() and line.strip().isnumeric()))
                            if non_number_lines / len(lines) < 0.1:
                                vprint(f"  ⏭️  Filtering consecutive number sequence artifact from tile {i+1}")
                                continue
                        
                    tile_texts.append((x, y, tile_text))
                        
            except Exception as e:
                vprint(f"  ⚠️  Warning: Failed to process tile {i+1}: {str(e)}")
                continue
        
        # Combine tile texts
        if len(tile_texts) == 0:
            extracted_text = ""
        elif len(tile_texts) == 1:
            extracted_text = tile_texts[0][2]
        else:
            combined = []
            for x, y, text in sorted(tile_texts, key=lambda t: (t[1], t[0])):
                if text.strip():
                    combined.append(f"--- Tile at ({x},{y}) ---\n{text.strip()}\n")
            extracted_text = "\n\n".join(combined)
        
        # Generate summary if requested
        if generate_summary and extracted_text.strip():
            vprint("\nGenerating summary from combined text...")
            try:
                summary_prompt = f"""Based on the following extracted text from a document, create a summary section starting with "## SUMMARY ##" that summarizes the purpose and content of the document in one or two sentences.

Extracted text:
{extracted_text}

## SUMMARY ##"""
                
                summary_text = ocr_engine.extract_text(
                    image=None,
                    prompt=summary_prompt
                )
                
                extracted_text = f"{extracted_text}\n\n{summary_text}"
                vprint("  ✅ Summary generated")
            except Exception as e:
                vprint(f"  ⚠️  Warning: Failed to generate summary: {str(e)}")
        
        # Handle JSON template extraction if provided
        is_json_mode = json_template is not None
        json_data = None
        
        if is_json_mode:
            vprint("Extracting JSON from output...")
            if VERBOSE:
                print(f"  Raw extracted text length: {len(extracted_text)}")
                print(f"  Preview: {extracted_text[:300]}")
            json_data = json_template.extract_json(extracted_text)
            
            if json_data:
                vprint("  ✓ JSON extracted successfully")
                is_valid, error_msg = json_template.validate(json_data)
                
                if is_valid:
                    vprint("  ✅ JSON validated against schema")
                else:
                    vprint(f"  ⚠️  JSON validation warning: {error_msg}")
            else:
                vprint("  ⚠️  Failed to extract JSON, falling back to plain text")
                is_json_mode = False
        
        # Clean up extracted text (only for non-JSON mode)
        if not is_json_mode:
            try:
                import re
                lines = extracted_text.split('\n')
                cleaned_lines = []
                for line in lines:
                    if line.strip() and not re.match(r'^[\|\s\|]+$', line.strip()):
                        cleaned_lines.append(line)
                extracted_text = '\n'.join(cleaned_lines).strip()
                
            except Exception as e:
                error_msg = f"Text extraction failed: {str(e)}"
                print(f"❌ ERROR: {error_msg}", file=sys.stderr)
                processing_log.log_error(str(input_path), "Text Extraction Error", error_msg)
                return False
        
        # Generate output filename with hash
        input_stem = input_path.stem
        if is_json_mode and json_data:
            output_filename = f"{input_stem}_OCR_{image_hash}.json"
            output_path = output_dir / output_filename
            output_content = json_template.format_output(json_data)
        else:
            output_filename = f"{input_stem}_OCR_{image_hash}.md"
            output_path = output_dir / output_filename
            output_content = extracted_text
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        # Track in CSV
        if is_json_mode and json_data:
            summary = json_data.get('title', json_data.get('summary', ''))[:100] if isinstance(json_data, dict) else ""
        else:
            summary = extracted_text[:100].replace('\n', ' ') if extracted_text else ""
        csv_tracker.add_entry(image_hash, str(input_path), summary)
        
        # Log successful processing
        processing_log.log_processed(str(input_path), image_hash, str(output_path))
        
        # Print success for this image
        print(f"✅ Processed: {input_path.name} → {output_filename}")
        if VERBOSE:
            if is_json_mode and json_data:
                print(f"\n📋 Extracted JSON:\n{'-' * 60}")
                print(json.dumps(json_data, indent=2, ensure_ascii=False))
                print(f"{'-' * 60}\n")
            else:
                print(f"\n📝 Extracted text:\n{'-' * 60}")
                print(extracted_text[:200] + ('...' if len(extracted_text) > 200 else ''))
                print(f"{'-' * 60}\n")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR processing {input_path.name}: {str(e)}", file=sys.stderr)
        if VERBOSE:
            import traceback
            traceback.print_exc()
        processing_log.log_error(str(input_path), "Processing Error", str(e))
        return False


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
        # If using template with a custom prompt, prepend it. Otherwise just use template prompt.
        base_prompt = ocr_prompt if args.prompt else None
        ocr_prompt = json_template.generate_prompt(base_prompt)
    
    # Expand input pattern to list of files
    try:
        input_files = _expand_input_pattern(args.input)
        if not input_files:
            print(f"ERROR: No matching files found: {args.input}", file=sys.stderr)
            sys.exit(1)
        print(f"Found {len(input_files)} image(s) to process")
    except FileNotFoundError as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Modules are now imported at module level
        # Initialize tracking and logging
        csv_tracker = CSVTracker(output_dir / "ocr_results.csv")
        processing_log = ProcessingLog(output_dir / "ocr_processing_log.md")
        
        # Initialize image processor
        image_processor = ImagePreprocessor()
        
        # Initialize OCR engine ONCE (expensive operation)
        vprint(f"Loading model: {args.model}")
        print("⏳ Loading OCR model (this may take a moment)...")
        try:
            if model_format == "transformers":
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
                    do_sample=DEFAULT_DO_SAMPLE,
                    verbose=VERBOSE
                )
        except Exception as e:
            error_msg = f"Model loading failed: {str(e)}"
            print(f"\n❌ FATAL ERROR: {error_msg}", file=sys.stderr)
            sys.exit(1)
        
        print("✅ Model loaded successfully")
        
        # Process each image
        print(f"\nProcessing {len(input_files)} image(s)...")
        successful = 0
        skipped = 0
        failed = 0
        
        for i, input_file in enumerate(input_files, 1):
            print(f"\n[{i}/{len(input_files)}] {input_file.name}")
            result = process_single_image(
                input_file, ocr_engine, image_processor, csv_tracker, 
                processing_log, output_dir, ocr_prompt, json_template, 
                model_format, args, args.model
            )
            
            if result:
                successful += 1
            elif result is False:
                skipped += 1
            else:
                failed += 1
        
        # Final summary
        print(f"\n{'=' * 60}")
        print(f"✅ Batch complete!")
        print(f"📊 Successfully processed: {successful}")
        print(f"⏭️  Skipped (duplicates): {skipped}")
        print(f"❌ Failed: {failed}")
        print(f"📁 Output directory: {output_dir}")
        print(f"📄 CSV tracker: {csv_tracker.csv_path}")
        print(f"📝 Processing log: {processing_log.log_path}")
        print(f"{'=' * 60}\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

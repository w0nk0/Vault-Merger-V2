"""
Main entry point for OCR v0.2.5 - Single or batch file OCR processing with duplicate detection and tracking.

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
import re
from pathlib import Path

# Import OCR modules at module level
try:
    from ocr_project.image_processor import ImagePreprocessor
    from ocr_project.ocr_engine import VisionOCREngine
    from ocr_project.hash_manager import calculate_image_hash, check_duplicate
    from ocr_project.csv_tracker import CSVTracker
    from ocr_project.processing_log import ProcessingLog
    from ocr_project.pdf_processor import convert_pdf_to_images, is_pdf_file
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
    from pdf_processor import convert_pdf_to_images, is_pdf_file

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
        help="Input image/PDF file path or glob pattern (e.g., '*.jpg', '*.pdf', 'folder/**/*.png')"
    )
    parser.add_argument(
        "--output",
        required=False,
        default=None,
        help="Output directory path (default: root/OCRoutput if --root provided, else required)"
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
        "--result-template",
        type=str,
        default=None,
        help="Path to markdown template file for formatting JSON results (e.g., json2result.template.md). Uses %fieldname% placeholders."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output (model details, inference info, etc.)"
    )
    parser.add_argument(
        "--csv-json-summary-field",
        type=str,
        default="summary",
        help="JSON field name to use for CSV summary (default: 'summary'). Can also be set via config file."
    )
    parser.add_argument(
        "--csv-path",
        type=str,
        default=None,
        help="Path to CSV index file directory (default: root/.obsidian or output_dir/.obsidian). Can also be set via config file."
    )
    parser.add_argument(
        "--root",
        type=str,
        default=None,
        help="Path to vault root directory (default: uses output_dir). Used for CSV index and result template defaults."
    )
    parser.add_argument(
        "--min-image-size",
        type=int,
        default=40000,
        help="Minimum total pixels (width * height) required to process an image (default: 40000 = 200x200)"
    )
    parser.add_argument(
        "--cfgpath",
        type=str,
        default=None,
        help="Path to configuration file relative to root (default: .obsidian/OCRconfig.yaml). Omit to use default."
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
    Expand input pattern to list of files (images and PDFs).
    
    Args:
        input_pattern: File path or glob pattern
        
    Returns:
        List of file paths (Path objects)
    """
    path = Path(input_pattern)
    
    # Supported file extensions
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    pdf_extensions = ['.pdf']
    supported_extensions = image_extensions + pdf_extensions
    
    # If it's a wildcard pattern, expand it
    if '*' in str(input_pattern) or '?' in str(input_pattern) or '[' in str(input_pattern):
        all_files = sorted(glob.glob(str(input_pattern), recursive='**' in str(input_pattern)))
        files = [Path(f) for f in all_files if Path(f).is_file()]
        # Filter to supported extensions
        files = [f for f in files if f.suffix.lower() in [ext.lower() for ext in supported_extensions]]
        return files
    # If it's a directory, get all image and PDF files
    elif path.is_dir():
        files = []
        for ext in supported_extensions:
            files.extend(path.glob(f'*{ext}'))
            files.extend(path.glob(f'*{ext.upper()}'))
        return sorted(files)
    # Single file
    elif path.is_file():
        # Check if it's a supported format
        if path.suffix.lower() not in [ext.lower() for ext in supported_extensions]:
            raise ValueError(f"Unsupported file type: {path.suffix}. Supported: {', '.join(supported_extensions)}")
        return [path]
    else:
        raise FileNotFoundError(f"Input not found: {input_pattern}")


def process_single_image(input_path, ocr_engine, image_processor, csv_tracker, processing_log, 
                         output_dir, ocr_prompt, json_template, model_format, args, model_name,
                         csv_json_summary_field="summary"):
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
        # Check if source has already been OCR'd using CSV index
        if csv_tracker.entry_exists(str(input_path)):
            print(f"⚠️  Skip: {input_path.name}")
            processing_log.log_skipped(
                str(input_path),
                "",
                "Source already processed (found in CSV index)",
                ""
            )
            return False
        
        # Calculate hash for filename
        vprint(f"Calculating hash for: {input_path}")
        image_hash = calculate_image_hash(str(input_path))
        vprint(f"  Hash: {image_hash}")
        
        # Load and preprocess image
        vprint(f"Loading image: {input_path}")
        try:
            image = image_processor.load_image(str(input_path))
            original_size = image.size
            vprint(f"  Original size: {original_size[0]}x{original_size[1]}")
            
            # Check if image is too small
            if image_processor.is_too_small(image):
                total_pixels = original_size[0] * original_size[1]
                reason = f"Image too small ({original_size[0]}x{original_size[1]} = {total_pixels} pixels, minimum: {image_processor.min_size_pixels})"
                print(f"⚠️  Skip: {input_path.name} ({reason})")
                processing_log.log_skipped(
                    str(input_path),
                    "",
                    reason,
                    ""
                )
                return False
            
            # Check if image needs tiling
            # JSON template mode requires whole image, not tiles
            if json_template is not None:
                vprint(f"  JSON template mode: Processing whole image (no tiling)")
                preprocessed_image = image_processor.preprocess(image)
                tiles = [(preprocessed_image, (0, 0))]
            else:
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
                        tiles = image_processor.create_tiles(image, overlap=0.1)
                        
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
        # Don't trigger summary mode if using JSON template (templates often have "summary" as a field)
        if json_template is None:
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
        
        # Generate output filename: OCR-{first8}-{last8}-{hash}.{ext}
        input_stem = input_path.stem
        # Get first 8 and last 8 characters (pad if name is shorter than 8 chars)
        if len(input_stem) >= 8:
            first8 = input_stem[:8]
            last8 = input_stem[-8:]
        else:
            # Pad with zeros: first8 padded on right, last8 padded on left
            first8 = input_stem.ljust(8, '0')[:8]
            last8 = input_stem.rjust(8, '0')[-8:]
        
        if is_json_mode and json_data:
            # Use appropriate extension based on template
            output_ext = json_template.get_output_extension()
            output_filename = f"OCR-{first8}-{last8}-{image_hash}{output_ext}"
            output_path = output_dir / output_filename
            output_content = json_template.format_output(json_data)
        else:
            output_filename = f"OCR-{first8}-{last8}-{image_hash}.md"
            output_path = output_dir / output_filename
            output_content = extracted_text
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        # Extract summary from document
        summary = ""
        if is_json_mode and json_data:
            # For JSON mode, use configured field (default: "summary")
            # Fallback to "title" if configured field is not available
            summary = json_data.get(csv_json_summary_field, '') or json_data.get('title', '')
        else:
            # Extract summary from markdown text if it has "## SUMMARY ##" section
            summary_match = re.search(r'##\s*SUMMARY\s*##\s*\n(.*?)(?:\n\n|\n##|$)', extracted_text, re.IGNORECASE | re.DOTALL)
            if summary_match:
                summary = summary_match.group(1).strip()
            else:
                # Fallback: use first 200 characters of text if no summary section
                summary = extracted_text[:200].replace('\n', ' ').strip() if extracted_text else ""
        
        # Track in CSV index (source_filename, results_filename, summary)
        csv_tracker.add_entry(str(input_path), output_filename, summary)
        
        # Log successful processing
        processing_log.log_processed(str(input_path), image_hash, str(output_path))
        
        # Print success for this image
        if VERBOSE:
            print(f"✅ Processed: {input_path.name} → {output_filename}")
        else:
            print(f"✅ {input_path.name}")
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
        print(f"❌ {input_path.name}: {str(e)}", file=sys.stderr)
        if VERBOSE:
            import traceback
            traceback.print_exc()
        processing_log.log_error(str(input_path), "Processing Error", str(e))
        return False


def process_pdf(input_path, ocr_engine, image_processor, csv_tracker, processing_log,
                output_dir, ocr_prompt, json_template, model_format, args, model_name,
                csv_json_summary_field="summary"):
    """
    Process a PDF file by converting pages to images and processing each page.
    
    Args:
        input_path: Path to input PDF file
        ocr_engine: Initialized OCR engine
        image_processor: Initialized image processor
        csv_tracker: CSV tracker
        processing_log: Processing log
        output_dir: Output directory
        ocr_prompt: OCR prompt
        json_template: JSON template handler (or None)
        model_format: Model format string
        args: Command-line arguments
        model_name: Model name/path
        
    Returns:
        True if successful, False if failed
    """
    try:
        # Check if source has already been OCR'd using CSV index
        if csv_tracker.entry_exists(str(input_path)):
            print(f"⚠️  Skip: {input_path.name}")
            processing_log.log_skipped(
                str(input_path),
                "",
                "Source already processed (found in CSV index)",
                ""
            )
            return False
        
        # Calculate hash for filename
        vprint(f"Calculating hash for PDF: {input_path}")
        pdf_hash = calculate_image_hash(str(input_path))
        vprint(f"  PDF Hash: {pdf_hash}")
        
        # Convert PDF pages to images
        if VERBOSE:
            print(f"📄 Converting PDF to images...")
        try:
            pdf_pages = convert_pdf_to_images(str(input_path), dpi=200)
            vprint(f"  Converted {len(pdf_pages)} page(s)")
        except Exception as e:
            error_msg = f"Failed to convert PDF to images: {str(e)}"
            print(f"❌ ERROR: {error_msg}", file=sys.stderr)
            processing_log.log_error(str(input_path), "PDF Conversion Error", error_msg)
            return False
        
        if len(pdf_pages) == 0:
            error_msg = "PDF has no pages"
            print(f"❌ ERROR: {error_msg}", file=sys.stderr)
            processing_log.log_error(str(input_path), "PDF Error", error_msg)
            return False
        
        # Check if all PDF pages are too small (skip if all pages are below threshold)
        valid_pages = [page for page in pdf_pages if not image_processor.is_too_small(page[0])]
        if len(valid_pages) == 0:
            # All pages are too small - show info about first page
            first_page_image = pdf_pages[0][0]
            first_page_size = first_page_image.size
            total_pixels = first_page_size[0] * first_page_size[1]
            reason = f"All PDF pages too small (example: {first_page_size[0]}x{first_page_size[1]} = {total_pixels} pixels, minimum: {image_processor.min_size_pixels})"
            print(f"⚠️  Skip: {input_path.name} ({reason})")
            processing_log.log_skipped(
                str(input_path),
                "",
                reason,
                ""
            )
            return False
        
        # Use only valid (non-too-small) pages
        if len(valid_pages) < len(pdf_pages):
            skipped_count = len(pdf_pages) - len(valid_pages)
            vprint(f"  ⚠️  Skipping {skipped_count} page(s) that are too small")
            pdf_pages = valid_pages
        
        # Process each page
        page_texts = []
        page_json_data = []
        
        for page_image, page_number in pdf_pages:
            page_num = page_number
            vprint(f"  Processing page {page_num}/{len(pdf_pages)}...")
            
            # Save page as temporary image for processing
            # Use process_single_image logic but with the page image directly
            try:
                # Check if image needs tiling (JSON mode uses whole image)
                if json_template is not None:
                    preprocessed_image = image_processor.preprocess(page_image)
                    tiles = [(preprocessed_image, (0, 0))]
                else:
                    is_large = image_processor.is_large_image(page_image)
                    if is_large:
                        tiles = image_processor.create_tiles(page_image, overlap=0.1)
                    else:
                        preprocessed_image = image_processor.preprocess(page_image)
                        tiles = [(preprocessed_image, (0, 0))]
                
                # Extract text from tiles
                tile_texts = []
                for tile_image, (x, y) in tiles:
                    tile_to_process = image_processor.preprocess(tile_image)
                    tile_text = ocr_engine.extract_text(
                        image=tile_to_process,
                        prompt=ocr_prompt
                    )
                    if tile_text.strip():
                        tile_texts.append((x, y, tile_text))
                
                # Combine tile texts
                if len(tile_texts) == 0:
                    page_text = ""
                elif len(tile_texts) == 1:
                    page_text = tile_texts[0][2]
                else:
                    combined = []
                    for x, y, text in sorted(tile_texts, key=lambda t: (t[1], t[0])):
                        if text.strip():
                            combined.append(f"--- Tile at ({x},{y}) ---\n{text.strip()}\n")
                    page_text = "\n\n".join(combined)
                
                # Handle JSON extraction if template provided
                page_json = None
                if json_template:
                    page_json = json_template.extract_json(page_text)
                    if page_json:
                        is_valid, error_msg = json_template.validate(page_json)
                        if not is_valid:
                            vprint(f"  ⚠️  JSON validation warning on page {page_num}: {error_msg}")
                            page_json = None  # Don't use invalid JSON
                
                page_texts.append(page_text)
                if page_json:
                    page_json_data.append(page_json)
                
            except Exception as e:
                error_msg = f"Failed to process page {page_num}: {str(e)}"
                print(f"  ⚠️  Warning: {error_msg}")
                page_texts.append(f"[Error processing page {page_num}]")
                continue
        
        # Combine all pages
        if json_template and page_json_data:
            # For JSON mode, we need to combine JSON objects
            # Strategy: Merge fullText fields, combine tags, keep most recent title/summary/date
            combined_json = {}
            
            # Combine fullText from all pages
            full_texts = []
            for json_data in page_json_data:
                if 'fullText' in json_data:
                    full_texts.append(json_data['fullText'])
                # Collect other fields from first valid page
                if not combined_json:
                    for key in ['tags', 'title', 'date', 'summary', 'conclusion']:
                        if key in json_data:
                            combined_json[key] = json_data[key]
            
            # Combine all fullText fields
            combined_json['fullText'] = '\n\n--- Page Break ---\n\n'.join(full_texts)
            
            # Combine tags (unique)
            if 'tags' in combined_json:
                all_tags = []
                for json_data in page_json_data:
                    if 'tags' in json_data and isinstance(json_data['tags'], list):
                        all_tags.extend(json_data['tags'])
                combined_json['tags'] = list(set(all_tags))  # Remove duplicates
            
            # Use most recent non-empty summary/conclusion
            for json_data in reversed(page_json_data):
                if 'summary' in json_data and json_data.get('summary') and 'summary' in combined_json and not combined_json.get('summary'):
                    combined_json['summary'] = json_data['summary']
                if 'conclusion' in json_data and json_data.get('conclusion') and 'conclusion' in combined_json and not combined_json.get('conclusion'):
                    combined_json['conclusion'] = json_data['conclusion']
            
            json_data = combined_json
            is_json_mode = True
        else:
            # For non-JSON mode, combine text with page markers
            combined_text = []
            for page_num, page_text in enumerate(page_texts, 1):
                if page_text.strip():
                    combined_text.append(f"--- Page {page_num} ---\n{page_text}")
            extracted_text = "\n\n".join(combined_text)
            json_data = None
            is_json_mode = False
        
        # Generate output filename: OCR-{first8}-{last8}-{hash}.{ext}
        input_stem = input_path.stem
        # Get first 8 and last 8 characters (pad if name is shorter than 8 chars)
        if len(input_stem) >= 8:
            first8 = input_stem[:8]
            last8 = input_stem[-8:]
        else:
            # Pad with zeros: first8 padded on right, last8 padded on left
            first8 = input_stem.ljust(8, '0')[:8]
            last8 = input_stem.rjust(8, '0')[-8:]
        
        if is_json_mode and json_data:
            # Use appropriate extension based on template
            output_ext = json_template.get_output_extension()
            output_filename = f"OCR-{first8}-{last8}-{pdf_hash}{output_ext}"
            output_path = output_dir / output_filename
            output_content = json_template.format_output(json_data)
        else:
            output_filename = f"OCR-{first8}-{last8}-{pdf_hash}.md"
            output_path = output_dir / output_filename
            output_content = extracted_text
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        # Extract summary from document
        summary = ""
        if is_json_mode and json_data:
            # For JSON mode, use configured field (default: "summary")
            # Fallback to "title" if configured field is not available
            summary = json_data.get(csv_json_summary_field, '') or json_data.get('title', '')
        else:
            # Extract summary from markdown text if it has "## SUMMARY ##" section
            summary_match = re.search(r'##\s*SUMMARY\s*##\s*\n(.*?)(?:\n\n|\n##|$)', extracted_text, re.IGNORECASE | re.DOTALL)
            if summary_match:
                summary = summary_match.group(1).strip()
            else:
                # Fallback: use first 200 characters of text if no summary section
                summary = extracted_text[:200].replace('\n', ' ').strip() if extracted_text else ""
        
        # Track in CSV index (source_filename, results_filename, summary)
        csv_tracker.add_entry(str(input_path), output_filename, summary)
        
        # Log successful processing
        processing_log.log_processed(str(input_path), pdf_hash, str(output_path))
        
        # Print success
        if VERBOSE:
            print(f"✅ Processed PDF ({len(pdf_pages)} pages): {input_path.name} → {output_filename}")
        else:
            print(f"✅ {input_path.name}")
        
        return True
        
    except Exception as e:
        error_msg = f"An unexpected error occurred while processing PDF {input_path.name}: {str(e)}"
        print(f"❌ FATAL ERROR: {error_msg}", file=sys.stderr)
        processing_log.log_error(str(input_path), "PDF Processing Error", error_msg)
        return False


def main():
    """Main entry point for OCR v0.2."""
    args = parse_arguments()
    
    # Determine vault root early (needed for config loading and template detection)
    # Priority: 1) --root flag, 2) cwd if .obsidian exists, 3) require --root if neither available
    vault_root_path = None
    if args.root:
        vault_root_path = Path(args.root)
    else:
        # Check if current directory has .obsidian
        cwd = Path.cwd()
        if (cwd / ".obsidian").exists():
            vault_root_path = cwd
            vprint(f"✓ Auto-detected vault root: {cwd} (found .obsidian directory)")
        else:
            # Require --root if no .obsidian found in current directory
            print("ERROR: --root is required when .obsidian directory not found in current directory", file=sys.stderr)
            print(f"       Current directory: {cwd}", file=sys.stderr)
            print(f"       Either: 1) Run from vault root (where .obsidian exists), or 2) Use --root to specify vault root", file=sys.stderr)
            sys.exit(1)
    
    # Load configuration from file (if available)
    config = {}
    try:
        from ocr_project.config_loader import load_config, get_config_path, apply_config_to_args
        
        # Determine config file path
        if args.cfgpath:
            # Explicit config path provided (relative to root)
            config_path = vault_root_path / args.cfgpath
        else:
            # Use default: root/.obsidian/OCRconfig.yaml
            config_path = get_config_path(vault_root_path)
        
        if config_path and config_path.exists():
            config = load_config(str(config_path))
            if config:
                vprint(f"✓ Loaded config from: {config_path}")
                # Apply config to args (only if not already set)
                apply_config_to_args(args, config)
    except ImportError:
        # PyYAML not available - continue without config
        pass
    
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
        
        # Determine result template path (default to root/.obsidian/json2result.template.md if root available)
        result_template_path = args.result_template
        if not result_template_path and vault_root_path:
            # Default to root/.obsidian/json2result.template.md
            default_template = vault_root_path / ".obsidian" / "json2result.template.md"
            if default_template.exists():
                result_template_path = str(default_template)
                vprint(f"✓ Auto-detected result template: {result_template_path}")
            else:
                result_template_path = None
        
        json_template = JSONTemplateHandler(args.template, result_template_path=result_template_path)
        vprint(f"✓ Using JSON template: {args.template}")
        if json_template.result_template:
            vprint(f"✓ Using result template: {json_template.result_template_path}")
    
    # Expand input pattern to list of files
    try:
        input_files = _expand_input_pattern(args.input)
        if not input_files:
            print(f"ERROR: No matching files found: {args.input}", file=sys.stderr)
            sys.exit(1)
        if VERBOSE:
            print(f"Found {len(input_files)} image(s) to process")
    except FileNotFoundError as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    # Determine output directory (vault_root_path already determined above)
    if args.output:
        output_dir = Path(args.output)
    elif vault_root_path:
        # Default output to root/OCRoutput
        output_dir = vault_root_path / "OCRoutput"
    else:
        # This shouldn't happen due to earlier check, but safety fallback
        print("ERROR: Cannot determine output directory", file=sys.stderr)
        sys.exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Use the vault_root_path determined earlier
    vault_root = vault_root_path
    
    # Use custom prompt if provided, otherwise use default
    ocr_prompt = args.prompt if args.prompt else DEFAULT_PROMPT
    
    # Generate structured prompt if template is provided
    if json_template:
        # If using template with a custom prompt, prepend it. Otherwise just use template prompt.
        base_prompt = ocr_prompt if args.prompt else None
        ocr_prompt = json_template.generate_prompt(base_prompt)
    
    try:
        # Modules are now imported at module level
        # Determine CSV index path (configurable, default to root/.obsidian)
        csv_path_arg = getattr(args, 'csv_path', None)
        if csv_path_arg:
            csv_index_dir = Path(csv_path_arg)
        else:
            # Default to root/.obsidian (vault root/.obsidian)
            csv_index_dir = vault_root / ".obsidian"
        csv_index_dir.mkdir(parents=True, exist_ok=True)
        csv_tracker = CSVTracker(csv_index_dir / "ocr_results.csv")
        
        # Initialize processing log (default to same directory as CSV index)
        processing_log = ProcessingLog(csv_index_dir / "ocr_processing_log.md")
        
        # Initialize image processor with minimum size
        min_size_pixels = getattr(args, 'min_image_size', 40000)
        image_processor = ImagePreprocessor(min_size_pixels=min_size_pixels)
        
        # Initialize OCR engine ONCE (expensive operation)
        vprint(f"Loading model: {args.model}")
        if VERBOSE:
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
        
        if VERBOSE:
            print("✅ Model loaded successfully")
        
        # Process each file (images and PDFs)
        if VERBOSE:
            print(f"\nProcessing {len(input_files)} file(s)...")
        successful = 0
        skipped = 0
        failed = 0
        
        for i, input_file in enumerate(input_files, 1):
            if VERBOSE:
                print(f"\n[{i}/{len(input_files)}] {input_file.name}")
            else:
                print(f"[{i}/{len(input_files)}] {input_file.name}", end=' ', flush=True)
            
            # Route to appropriate processor based on file type
            # Get CSV JSON summary field from args (defaults to "summary")
            csv_json_summary_field = getattr(args, 'csv_json_summary_field', 'summary')
            
            if is_pdf_file(input_file):
                result = process_pdf(
                    input_file, ocr_engine, image_processor, csv_tracker, 
                    processing_log, output_dir, ocr_prompt, json_template, 
                    model_format, args, args.model, csv_json_summary_field
                )
            else:
                result = process_single_image(
                    input_file, ocr_engine, image_processor, csv_tracker, 
                    processing_log, output_dir, ocr_prompt, json_template, 
                    model_format, args, args.model, csv_json_summary_field
                )
            
            if result:
                successful += 1
            elif result is False:
                skipped += 1
            else:
                failed += 1
        
        # Final summary
        if VERBOSE:
            print(f"\n{'=' * 60}")
            print(f"✅ Batch complete!")
            print(f"📊 Successfully processed: {successful}")
            print(f"⏭️  Skipped (duplicates): {skipped}")
            print(f"❌ Failed: {failed}")
            print(f"📁 Output directory: {output_dir}")
            print(f"📄 CSV tracker: {csv_tracker.csv_path}")
            print(f"📝 Processing log: {processing_log.log_path}")
            print(f"{'=' * 60}\n")
        else:
            print(f"\n✅ {successful} | ⏭️  {skipped} | ❌ {failed}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

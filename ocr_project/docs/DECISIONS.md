# OCR Project - Design Decisions and Resolutions

This document tracks all design decisions, resolved issues, and agreed-upon specifications for the OCR project.

---

## Model Configuration

### ✅ Model Selection
- **Model**: `google/gemma-3-12b-it` (Gemma 3, 12B instruction-tuned)
- **Model Class**: `Gemma3ForConditionalGeneration`
- **Processor**: `AutoProcessor`
- **Transformers Version**: >= 4.50.0 (required for Gemma 3 support)
- **Image Resolution**: 896x896 (as per official model card)
- **Context Window**: 128K tokens (for 12B model)
- **Output Limit**: 8192 tokens

### ✅ Model Specifications
- All model references updated from "13b" to "12b" throughout codebase
- Configuration template updated with correct model name
- Image processing defaults to 896x896 resolution

---

## Dependency Management

### ✅ Single Source of Truth
- **Primary**: `pyproject.toml` is the single source of truth for dependencies
- **Dependencies Harmonized**: All conflicts resolved using highest versions
- **Transformers**: >= 4.50.0 (for Gemma 3 support)
- **Additional Dependencies Added**:
  - accelerate>=0.20.0
  - sentencepiece>=0.1.96
  - tokenizers>=0.14.0
  - huggingface_hub>=0.14.0
  - torchao>=0.1

### ✅ File Status
- `requirements.txt`: Marked as deprecated (points to pyproject.toml)
- `setup.py`: References pyproject.toml for backward compatibility

---

## Error Handling Strategy (Issue #3 - RESOLVED)

### Fatal Errors (Abort Entire Process)
- **Model loading failure**: Abort entire process immediately
  - Log: "FATAL: Model loading failed - {error_details}. Aborting process."
  - Exit with error code
  - Do not attempt to process any images

### Recoverable Errors (Continue Processing)
- **Corrupted image file**: Skip only that image
  - Log: "ERROR: Image {filename} is corrupted - {error_details}. Skipping this image."
  - Continue processing remaining images
  - Record in processing log with reason

### Fallback Strategy
- Inference timeout: Retry with shorter max_tokens or reduced batch size
- Memory exhaustion: Fallback to CPU or reduce image resolution
- Network errors: Retry with exponential backoff
- Partial batch failure: Process successful images, log failures, continue
- Unsupported image format: Try conversion via Pillow, skip if fails

### Error Logging
- All errors logged to `ocr_processing_log.md`
- Include: timestamp, error type, file affected, error details, action taken
- Fatal errors also to console/stderr

---

## Logging Strategy (Issue #4 - RESOLVED)

### Approach
- Use Python `logging` module with structured format (JSON for technical logs)
- Log levels: DEBUG → INFO → WARNING → ERROR → CRITICAL

### Log Files
- **Processing Log**: `ocr_processing_log.md` (markdown format for human readability)
- **Technical Log**: Configurable log file for debugging (if `log_file` specified)
- **Log Rotation**: File size-based rotation for technical logs
- **Structured Format**: JSON for technical logs, markdown for processing log

### Metrics
- Images processed, success rate, average time per image
- Progress bars using `tqdm` (already in dependencies)

---

## Hash-Based Duplicate Detection (Issue #2 - SPECIFIED)

### Logic (for v0.2)
- Calculate SHA-256 hash of image content (first 8 characters)
- Check if hash appears in any existing filename in vault
- **If hash found in OCR-generated file** (pattern `*_OCR_{hash}.md`):
  - Skip OCR processing for this image
  - Log: "Skipped {image_path}: Hash {hash} already exists in OCR file {existing_file}"
- **If hash exists in non-OCR filename**:
  - Continue with OCR processing (hash collision or unrelated file)
  - Log: "Processing {image_path}: Hash {hash} found in non-OCR file {existing_file}, continuing"
- Store all hash detections in processing log

### Implementation Requirements
- Detect OCR file pattern: `{original_name}_OCR_{hash}.md`
- Check filename for hash substring (8 characters per RULES.md)
- Log both scenarios with clear distinction

---

## Configuration Decisions

### Prompt Configuration (Issue #13)
- **Prompt is configurable** in configuration file (`ocr_prompt` field)
- Default prompt: "Extract all text from this image. Transcribe it exactly as it appears."
- Prompt used for each operation logged in processing log
- Added to `config_template.yaml`

### Configuration Template
- File: `config_template.yaml`
- Contains all model, processing, and output parameters
- Will be used starting from v0.3

---

## Testing Strategy (Issue #5 - PROPOSED)

### Test Structure
- `tests/unit/` - Unit tests for individual modules
- `tests/integration/` - Integration tests for full pipeline
- `tests/test_data/` - Sample test images and fixtures
- `tests/fixtures/` - Test configuration files, mock data

### Test Use Cases (10 defined)
1. Single Image OCR (v0.1 core)
2. Model Loading and Initialization
3. Image Preprocessing
4. Hash-Based Duplicate Detection (v0.2)
5. Error Handling
6. CSV Tracking (v0.2)
7. Configuration Management
8. Batch Processing
9. Prompt Customization
10. Output Quality

### Testing Framework
- pytest (already in dependencies)
- Mock model inference for unit tests
- Golden files for regression testing

---

## Integration Decisions

### Vault Merger Integration (Issue #1 & #27)
- **Status**: Deferred to v0.5 per roadmap
- **Strategy**: Implement after core OCR functionality is proven
- Will define API: `process_vault_images(vault_path, config_path=None)`

---

## PDF Processing (Issue #6)

### Decision
- **Status**: Post v0.1 testing
- **Approach**: User will test PDF processing using v0.1 prototype once completed
- Test if Gemma 3-12b-it accepts PDF input natively
- Decision on implementation approach will be made based on test results
- **If VLM handles PDFs natively**: Use directly, no conversion
- **If VLM requires conversion**: Implement PDF → image conversion workflow

---

## Version 0.1 Specifications

### Command-Line Interface
- **Arguments**: `--model`, `--input`, `--output`, `--device` (optional)
- **Example**: `uv run python -m ocr_project.main --model "google/gemma-3-12b-it" --input "document.jpg" --output "./output" [--device cuda]`
- **Device Selection**: Command-line argument `--device` (e.g., `cuda`, `cpu`, `mps`)
  - If not provided, auto-detect using `device_map="auto"`
  - Config file argument for device will be added in later version

### Output Filename Format
- **Format**: `{original_name}_OCR.md` (resembles future structure `{original_name}_OCR_{hash}.md`)
- Example: `document.jpg` → `document_OCR.md`
- Note: Hash will be added in v0.2 when duplicate detection is implemented

### Image Preprocessing (v0.1)
- **Current**: Resize to 896x896 only
- **Planned for v0.1.5**: Add enhancement steps (contrast enhancement, noise reduction)
- Keep enhancement in architecture plan, implement incrementally

### Inference Parameters (v0.1)
- **Hard-coded defaults**:
  - `temperature=0.1`
  - `max_new_tokens=1024`
  - `do_sample=False`
- No CLI arguments for inference parameters in v0.1 (config file support comes later)

### Data Types
- **Auto-select based on device**:
  - CUDA: `bfloat16` or `float16` (auto-detect based on GPU support)
  - CPU: `float32`
  - MPS: `float16` or `bfloat16`
- Support for quantized models (int4/int8) - quantized values need to be possible
- Use `device_map="auto"` for automatic device and dtype selection

### Pan-and-Scan Support
- **Status**: ✅ **TRY NATIVE SUPPORT FIRST WITH FALLBACK**
- **User Requirement**: Expects many files larger than 896x896
- **Implementation Strategy**:
  - **Primary Approach**: Use `do_pan_and_scan=True` in AutoProcessor by default
  - **Fallback Strategy**: If native pan-and-scan fails, implement manual tiling
  - **Error Handling**: Catch any exceptions from pan-and-scan and fall back to manual tiling or simple resize
- **Implementation Plan for v0.1**:
  1. Try `processor.apply_chat_template(..., do_pan_and_scan=True)` for images >896x896
  2. If it works: Use native support (ideal case)
  3. If it fails or raises error: Fall back to manual tiling strategy
  4. Log which method was used for troubleshooting
- **Note**: Model card states "Images normalized to 896 x 896" but we'll test if pan-and-scan parameter actually works

### What's NOT in v0.1
- ❌ Duplicate checking
- ❌ Hash calculation (but filename format prepares for it)
- ❌ CSV tracking
- ❌ Logging system
- ❌ Batch processing
- ❌ Configuration files (CLI args only)
- ❌ Error recovery (basic error handling only)
- ❌ Model caching
- ❌ Image enhancement (planned for v0.1.5)

### What IS in v0.1
- ✅ Single file OCR processing
- ✅ Extract text using VLM
- ✅ Save result as markdown file with `_OCR` suffix
- ✅ Print extracted text to console
- ✅ Basic error handling (model loading abort, corrupted image skip)
- ✅ Device selection via CLI argument (with auto-detect fallback)
- ✅ Auto-selected data types based on device
- ✅ Support for quantized models

---

## Architecture Decisions

### Module Structure
- `main.py`: Main application entry point
- `image_processor/`: Image loading and preprocessing
- `ocr_engine/`: Vision Language Model integration and text extraction
- `config/`: Configuration management (v0.3+)
- `result_processor/`: OCR result post-processing

### Processing Pipeline
1. Load image from file
2. Preprocess image (resize to 896x896)
3. Format image with text prompt using processor.apply_chat_template()
4. Run inference with Gemma3ForConditionalGeneration
5. Extract text from model output
6. Clean and format the extracted text
7. Save to markdown file and print to console

---

## File Naming Conventions

### Output Files (v0.1)
- Simple format: `{input_filename}.md`
- Example: `document.jpg` → `document.md`

### Output Files (v0.2+)
- Format: `{original_name}_OCR_{hash}.md`
- Hash: First 8 characters of SHA-256

---

## Notes

- All resolved issues have been removed from issues.md
- Roadmap serves as the primary to-do list
- See ISSUES.md for open/unresolved items
- See ROADMAP.md for version milestones



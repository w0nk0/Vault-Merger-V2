# OCR Project Roadmap

This document outlines the development roadmap for the OCR project, organized by version milestones.

## Version 0.1 - Early Prototype (Current Target)

**Goal**: Create a minimal working OCR prototype to validate the approach and model integration.

### Features
- **Single file OCR processing**
  - Command-line interface with three arguments:
    - Model identifier/path
    - Input image/document path
    - Output folder path
  - Process one image file at a time
  - Extract text using Vision Language Model
  - Save result as markdown file in output folder
  - Print extracted text to console

### What's NOT included (intentional omissions):
- ❌ Duplicate checking
- ❌ Hash calculation
- ❌ CSV tracking
- ❌ Logging system
- ❌ Batch processing
- ❌ Configuration files
- ❌ Error recovery
- ❌ Model caching

### Implementation Plan
1. Implement basic command-line interface (`main.py`)
2. Implement image loading (`image_processor/`)
3. Implement VLM integration (`ocr_engine/`)
4. Implement basic text extraction
5. Save output as markdown file
6. Print results to console

### Success Criteria
- Can process a single image file from command line
- Successfully extracts text using VLM
- Outputs markdown file with extracted text
- Displays text in console

### Example Usage (v0.1)
```bash
uv run python -m ocr_project.main \
  --model "microsoft/llava-1.5-7b-hf" \
  --input "document.jpg" \
  --output "./output"
```

---

## Version 0.2 - Core Features

**Goal**: Add essential tracking, logging, and duplicate detection capabilities.

### New Features
- ✅ **Hash-based duplicate detection**
  - Calculate SHA-256 hash of image content
  - Check for existing processed files with same hash
  - Skip processing if duplicate found
  - Hash format: First 8 characters (as per RULES.md)

- ✅ **CSV tracking system**
  - Track all processed images in `ocr_results.csv`
  - Columns: `hash`, `filename`, `summary`
  - Append after each successful OCR operation
  - File location relative to output directory

- ✅ **Processing log**
  - Create `ocr_processing_log.md` in output directory
  - Log skipped images (hash, filename, reason)
  - Log processed images (hash, filename, timestamp)
  - Human-readable audit trail

- ✅ **Basic error handling**
  - Handle corrupted images gracefully
  - Handle model loading errors
  - Continue processing other files if one fails
  - Log errors to processing log

### Implementation Plan
1. Add hash calculation module
2. Implement duplicate checking logic
3. Implement CSV tracking with pandas
4. Create markdown log file writer
5. Add error handling wrapper around OCR processing
6. Update filename format: `{original_name}_OCR_{hash}.md`

### Success Criteria
- Detects and skips duplicate images
- Maintains accurate CSV tracking
- Creates readable processing log
- Handles errors without crashing

---

## Version 0.3 - Configuration and Polish

**Goal**: Add configuration management and improve usability.

### New Features
- ✅ **Configuration file support** (`config_template.yaml`)
  - Load configuration from YAML file
  - Command-line overrides for configuration values
  - Default configuration values

- ✅ **Enhanced logging**
  - Configurable log levels
  - Structured logging output
  - Log file support

- ✅ **Batch processing**
  - Process multiple images from directory
  - Progress indicators
  - Batch statistics

- ✅ **Input validation**
  - Validate image formats
  - Validate file paths
  - Validate configuration parameters

### Implementation Plan
1. Create config manager module
2. Implement YAML configuration loading
3. Add batch processing loop
4. Implement progress bars with tqdm
5. Add comprehensive input validation

---

## Future Versions (Planned)

### Version 0.4 - Advanced Features
- Multi-image request support
- Pan-and-scan for high-resolution images
- PDF processing (multi-page)
- Result formatting options (markdown, JSON)

### Version 0.5 - Integration
- Vault merger integration
- Automatic image discovery in vaults
- Link mapping integration

### Version 1.0 - Production Ready
- Comprehensive error handling
- Performance optimization
- Full test coverage
- Complete documentation
- Production-grade logging and monitoring

---

## Development Principles

1. **Incremental Development**: Each version builds on the previous, adding features incrementally.
2. **Working First, Optimize Later**: Get basic functionality working before adding optimizations.
3. **Test as You Go**: Add tests alongside features, not as afterthought.
4. **Document Decisions**: Keep roadmap and optimization documents updated as decisions are made.

---

## Notes

- Model selection will be finalized before v0.1 implementation (currently under review)
- Version numbers follow semantic versioning (MAJOR.MINOR.PATCH)
- Each version should be a shippable increment
- Roadmap is subject to change based on learnings from early versions



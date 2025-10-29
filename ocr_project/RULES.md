# OCR Project Rules

## Hash-Based Duplicate Detection
- Use SHA-256, take first 8 characters
- Filename format: `{original_name}_OCR_{hash}.md`
- Check if hash exists in any existing `.md` file before processing
- Skip if found

## CSV Tracking
- File: `ocr_results.csv` (configurable path relative to vault)
- Columns: `hash,filename,summary`
- Update after each successful OCR

## OCR Processing Log
- File: `ocr_processing_log.md` in output directory
- Log skipped images (hash, filename, reason)
- Log processed images (hash, filename, result)

## Dependency Management
- **UV must be used for Python dependencies**
- Run all Python commands with `uv run`

## Model Format Support
- Supports both Transformers and GGUF format models
- GGUF models use `llama-cpp-python` for inference
- Configure `model_format: "gguf"` and `model_path` for local GGUF files

## Paths
- All paths must be relative to vault main directory
- Configure in `config_template.yaml`

## Configuration Defaults
```yaml
hash_algorithm: "sha256"
model_format: "transformers"  # or "gguf"
model_path: ""  # Path to GGUF file if using GGUF format
hash_length: 8
enable_duplicate_check: true
csv_tracking_enabled: true
csv_filename: "ocr_results.csv"
csv_path: "."
ocr_lock_file: "ocr_processing_log.md"
# OCR Project with Vision Language Models

This project implements OCR functionality using Vision Language Models (VLMs) that are compatible with Hugging Face Transformers library to extract text from image notes (scans of text).

## Important: Project Rules

**Before using or contributing to this project, please read [RULES.md](RULES.md) file** which contains essential guidelines.

## Architecture

- `main.py`: Main application entry point
- `image_processor/`: Image loading and preprocessing
- `ocr_engine/`: Vision Language Model integration and text extraction
- `config/`: Configuration management
- `result_processor/`: OCR result post-processing

## Planned Features

- Extract text from scanned document images using Vision Language Models
- Support for various VLMs compatible with Hugging Face Transformers
- Current model: Google Gemma 3-13b-it (instruction-tuned)
- GGUF format support for efficient local model inference
- Hash-based duplicate detection to avoid reprocessing identical images
- CSV tracking system with hash, filename, and document summary
- OCR processing log for audit trail
- Multimodal processing using chat templates with image/text components
- Pan-and-scan capability for high-resolution images
- Support for multiple images in a single request
- Support for various image formats (JPG, PNG, PDF)
- Batch processing of multiple images
- Configuration management for model parameters
- Result cleaning and formatting
- Integration with existing vault merger system

## Setup

To be implemented.

## Usage

To be implemented.

## Dependency Management

This project uses **UV** for Python dependency management. All Python commands should be run with `uv run` prefix.

## Configuration

All configuration options and defaults are specified in [RULES.md](RULES.md) file.
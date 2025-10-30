# Using JSON Template-Based Extraction

## Overview

The OCR system now supports structured extraction using JSON Schema templates. This allows you to extract consistent, validated data from documents.

## Quick Start

### Basic Usage

```bash
uv run python main.py \
  --model /path/to/model.gguf \
  --input document.jpg \
  --output ./output \
  --template prompt.json
```

### What Happens

1. **Template Loading**: JSON schema is loaded from `prompt.json`
2. **Prompt Generation**: Template generates detailed instructions for the model
3. **Structured Extraction**: Model returns JSON matching your schema
4. **Validation**: Extracted JSON is validated against schema
5. **Output**: Saves as `.json` file with validated data

## Your Existing Template

Your `prompt.json` defines this structure:

```json
{
  "tags": ["array", "of", "3-10", "strings"],
  "title": "string",
  "date": "YYYY-MM-DD",
  "summary": "string",
  "fullText": "complete text",
  "conclusion": "string"
}
```

**Required fields**: `tags`, `title`, `summary`, `fullText`  
**Optional fields**: `date`, `conclusion`

## Example Usage

### Document Analysis
```bash
uv run python main.py \
  --model /home/nico/LMStudio/models/gemma-3-12b-it-GGUF/ \
  --input ../document.png \
  --output ./output \
  --template prompt.json \
  --device cuda
```

### With Custom Prompt
```bash
uv run python main.py \
  --model /path/to/model \
  --input invoice.jpg \
  --output ./output \
  --template prompt.json \
  --prompt "Focus on extracting dates, amounts, and vendor information"
```

## Output

### JSON Output (when using --template)
- **File**: `{filename}_OCR_{hash}.json`
- **Content**: Validated JSON matching your schema
- **Format**: Pretty-printed with indentation

### Markdown Output (without --template)
- **File**: `{filename}_OCR_{hash}.md`
- **Content**: Plain extracted text
- **Format**: Raw markdown

## Validation

The system validates extracted JSON:
- **Required fields**: Must be present
- **Field types**: Must match schema
- **Array constraints**: Min/max items enforced
- **Warnings**: Logged if validation fails (but continues)

## Creating Custom Templates

1. Create a JSON Schema file (see `prompt.json` for example)
2. Use JSON Schema Draft 7 format
3. Specify required fields
4. Add helpful descriptions for each field
5. Use `--template your_template.json`

### Template Example

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Invoice Extraction",
  "type": "object",
  "properties": {
    "invoice_number": {"type": "string", "description": "Invoice number"},
    "date": {"type": "string", "format": "date"},
    "total": {"type": "number", "description": "Total amount"},
    "vendor": {"type": "string", "description": "Vendor name"}
  },
  "required": ["invoice_number", "date", "total"]
}
```

## Features

✅ **Automatic Prompt Generation**: Schema → detailed instructions  
✅ **JSON Extraction**: Handles markdown code blocks  
✅ **Schema Validation**: Type checking, required fields  
✅ **Graceful Fallback**: Falls back to plain text if JSON fails  
✅ **Pretty Output**: Formatted JSON files  
✅ **CSV Integration**: Tracks titles from JSON  

## Tips

1. **Keep temperature low**: Use default (0.1) for consistent JSON
2. **Descriptions matter**: Model uses field descriptions for better extraction
3. **Test iteratively**: Start with simple schemas, add complexity
4. **Required vs optional**: Mark truly required fields carefully
5. **Array constraints**: Use min/max to guide the model

## Troubleshooting

### Model Returns Markdown Instead of JSON
- **Solution**: Template generates instructions to use JSON code blocks
- **Fallback**: System extracts JSON from markdown automatically

### Validation Failures
- **Check**: Required fields are present
- **Check**: Field types match schema
- **Check**: Array items meet constraints
- **Continue**: Processing continues with warning

### No JSON Extracted
- **Fallback**: System saves as plain `.md` file
- **Check logs**: Review validation messages
- **Simpler schema**: Try reducing schema complexity

## Architecture

```
Template → Generate Prompt → OCR Engine → Extract JSON → Validate → Save .json
```

Key Components:
- `json_template_handler.py`: Template management
- `main.py`: Integration with OCR pipeline
- `prompt.json`: Your example schema

## Next Steps

- ✅ Basic template support implemented
- 🔄 Add more template examples
- 🔄 Schema versioning
- 🔄 Template library
- 🔄 Advanced validation rules


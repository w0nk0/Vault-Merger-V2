# JSON Template-Based Structured Extraction

## Overview

Implement JSON schema-based structured extraction for OCR to extract structured data from documents with a consistent format.

## Current State

**File Found**: `ocr_project/prompt.json` contains a JSON Schema for structured extraction:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "OCRing Document",
  "type": "object",
  "properties": {
    "tags": {"type": "array", "items": {"type": "string"}},
    "title": {"type": "string"},
    "date": {"type": "string", "format": "date"},
    "summary": {"type": "string"},
    "fullText": {"type": "string"},
    "conclusion": {"type": "string"}
  },
  "required": ["tags", "title", "summary", "fullText"]
}
```

## Implementation Strategy

### Approach 1: JSON Schema in Prompt (Recommended)

**Method**: Include the JSON schema or a simplified version directly in the OCR prompt.

**Prompt Template**:
```
Extract text from this image and return it as JSON matching this schema:
{
  "tags": ["array", "of", "3-10", "strings"],
  "title": "string",
  "date": "YYYY-MM-DD",
  "summary": "string",
  "fullText": "string",
  "conclusion": "string"
}

Return only valid JSON, no explanations.
```

### Approach 2: JSON Schema File Parameter

**Method**: Pass JSON schema file path to OCR engine and auto-generate prompt.

**CLI**:
```bash
uv run python main.py --model ... --input ... --template prompt.json
```

## Implementation Plan

### Phase 1: Basic JSON Schema Prompt Integration

1. Add `--template` CLI argument
2. Parse JSON schema from file
3. Generate prompt with schema included
4. Extract JSON from model output
5. Validate JSON against schema

### Phase 2: Enhanced JSON Handling

1. Handle malformed JSON in model output
2. Extract JSON from markdown code blocks
3. Schema validation with detailed errors
4. Auto-fix common JSON issues

### Phase 3: Advanced Features

1. Custom field extraction instructions
2. Multiple template support
3. Schema versioning
4. Template library

## Prompt Engineering

**Key Considerations**:
- **Gemma 3**: Good at following structured output instructions
- **Temperature**: Keep at 0.1 (low) for consistent JSON
- **Max tokens**: Increase for complex schemas (2048+)
- **System message**: Emphasize JSON-only output

**Example Enhanced Prompt**:
```
You are a document analysis tool. Extract structured information from this image.

Return valid JSON only matching this schema:
{
  "tags": ["array of 3-10 descriptive tags"],
  "title": "concise document title",
  "date": "ISO date YYYY-MM-DD",
  "summary": "2-3 sentence summary",
  "fullText": "complete extracted text",
  "conclusion": "key takeaways"
}

Requirements:
- Return ONLY valid JSON, no markdown formatting
- No explanations or additional text
- Use null for missing optional fields
- Ensure all required fields are present
```

## Research Findings

Based on web search:
- **DeepSeek OCR**: Supports prompts for specific output formats
- **Gemma 3**: Excellent at structured JSON output
- **Best practice**: Include schema in prompt, keep temperature low
- **Common pattern**: Extract JSON from model output (may be in markdown code blocks)

## Technical Requirements

### Dependencies
- `jsonschema` library for validation
- JSON parsing (built-in Python)
- Prompt template system

### Code Structure
```
ocr_project/
  ├── json_template_handler.py  # New: Template parsing & prompt generation
  ├── prompt.json               # Existing: Example schema
  └── main.py                   # Modified: Add --template argument
```

### Files to Modify
1. `main.py`: Add `--template` argument, parse template
2. `ocr_engine/__init__.py`: Handle JSON output extraction
3. New: `json_template_handler.py`: Template management

## Example Usage

### Basic
```bash
uv run python main.py \
  --model /path/to/model \
  --input document.jpg \
  --output ./output \
  --template prompt.json
```

### Advanced
```bash
uv run python main.py \
  --model /path/to/model \
  --input document.jpg \
  --output ./output \
  --template prompt.json \
  --device cuda \
  --prompt "Extract as JSON with emphasis on dates and numbers"
```

## Output Format

**JSON Mode** (when using template):
- Output file: `{filename}_OCR_{hash}.json`
- Contents: Validated JSON matching schema

**Fallback**:
- If JSON invalid, save raw output to `.md`
- Log validation errors

## Next Steps

1. ✅ Research JSON template extraction patterns
2. ⏳ Implement `json_template_handler.py`
3. ⏳ Add `--template` argument to CLI
4. ⏳ Integrate with existing OCR engine
5. ⏳ Add JSON extraction and validation
6. ⏳ Test with various schemas

## Estimated Effort

- **Phase 1**: 2-3 hours
- **Phase 2**: 1-2 hours  
- **Phase 3**: 2-3 hours
- **Total**: 5-8 hours

## Priority

**Suggestion**: Implement as v0.3 feature (after v0.2 enhancements)

## References

- `prompt.json`: Existing template
- DeepSeek OCR documentation: Prompts guide format
- Gemma 3 model card: Structured output capabilities


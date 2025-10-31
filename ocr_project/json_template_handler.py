"""
JSON Template Handler for Structured OCR Extraction.

Handles parsing JSON schemas, generating prompts, and validating output.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class JSONTemplateHandler:
    """Handles JSON schema templates for structured OCR extraction."""
    
    def __init__(self, template_path: str):
        """
        Initialize with a JSON schema file.
        
        Args:
            template_path: Path to JSON schema file
        """
        self.template_path = Path(template_path)
        self.schema = None
        self._load_schema()
    
    def _load_schema(self):
        """Load JSON schema from file."""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                self.schema = json.load(f)
            # Note: Load confirmation message removed for cleaner output
            # Use --verbose to see it
        except Exception as e:
            raise Exception(f"Failed to load JSON schema: {str(e)}")
    
    def generate_prompt(self, base_prompt: Optional[str] = None) -> str:
        """
        Generate OCR prompt with JSON schema instructions.
        
        Args:
            base_prompt: Optional base prompt to prepend
            
        Returns:
            Complete prompt with JSON schema instructions
        """
        # Extract schema properties for prompt
        properties = self.schema.get('properties', {})
        required = self.schema.get('required', [])
        title = self.schema.get('title', 'Structured Data')
        
        # Build field descriptions
        field_descriptions = []
        for field_name, field_spec in properties.items():
            field_desc = field_spec.get('description', '')
            field_type = field_spec.get('type', '')
            is_required = field_name in required
            
            req_marker = "[REQUIRED]" if is_required else "[optional]"
            field_descriptions.append(f"- {field_name} ({field_type}) {req_marker}: {field_desc}")
        
        # Build JSON example
        json_example = self._build_json_example(properties, required)
        
        # Construct full prompt
        prompt_parts = []
        
        if base_prompt:
            prompt_parts.append(base_prompt)
        
        prompt_parts.append(f"\nExtract information from this image and return it as valid JSON matching this schema:")
        prompt_parts.append(f"\nSchema: {title}")
        prompt_parts.append("\nFields:")
        prompt_parts.extend(field_descriptions)
        
        prompt_parts.append(f"\nReturn ONLY valid JSON in this format:")
        prompt_parts.append(f"```json")
        prompt_parts.append(json.dumps(json_example, indent=2))
        prompt_parts.append("```")
        
        prompt_parts.append("\nRequirements:")
        prompt_parts.append("- Return ONLY valid JSON")
        prompt_parts.append("- No markdown formatting except code block")
        prompt_parts.append("- No explanations or additional text")
        prompt_parts.append("- Use null for missing optional fields")
        prompt_parts.append("- Ensure all required fields are present")
        
        return "\n".join(prompt_parts)
    
    def _build_json_example(self, properties: Dict, required: list) -> Dict[str, Any]:
        """
        Build a JSON example from schema properties.
        
        Args:
            properties: Schema properties dict
            required: List of required field names
            
        Returns:
            Example JSON structure
        """
        example = {}
        
        for field_name, field_spec in properties.items():
            field_type = field_spec.get('type')
            
            # Generate example value based on type
            if field_type == 'string':
                if 'format' in field_spec:
                    # Special format handling
                    if field_spec['format'] == 'date':
                        example[field_name] = "2024-01-15"
                    else:
                        example[field_name] = "example"
                else:
                    example[field_name] = "example"
            elif field_type == 'array':
                example[field_name] = ["example1", "example2"]
            elif field_type == 'object':
                example[field_name] = {}
            elif field_type == 'number':
                example[field_name] = 0
            elif field_type == 'boolean':
                example[field_name] = False
            else:
                example[field_name] = "example"
        
        return example
    
    def extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from model output (may be in markdown code blocks).
        
        Args:
            text: Model output text
            
        Returns:
            Parsed JSON dict or None if extraction fails
        """
        import re
        
        # Remove conversational artifacts (USER:, ASSISTANT:, etc.)
        # Common patterns from model output
        text = re.sub(r'^\s*USER:\s*\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*ASSISTANT:\s*\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'USER:\s*ASSISTANT:', '', text)
        
        # Try to extract JSON from markdown code block
        json_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            # Try to find JSON object in text
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
            else:
                # Assume whole text is JSON
                json_text = text.strip()
        
        # Parse JSON
        try:
            parsed = json.loads(json_text)
            return parsed
        except json.JSONDecodeError as e:
            print(f"⚠️  Failed to parse JSON: {e}")
            return None
    
    def validate(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate extracted JSON against schema.
        
        Args:
            data: Parsed JSON data
            
        Returns:
            (is_valid, error_message)
        """
        # Basic validation (required fields)
        required = self.schema.get('required', [])
        missing_fields = [field for field in required if field not in data]
        
        if missing_fields:
            return False, f"Missing required fields: {missing_fields}"
        
        # Additional validation (types, constraints)
        properties = self.schema.get('properties', {})
        for field_name, value in data.items():
            if field_name in properties:
                field_spec = properties[field_name]
                
                # Type validation
                expected_type = field_spec.get('type')
                if expected_type and not self._check_type(value, expected_type):
                    return False, f"Field '{field_name}' has wrong type. Expected {expected_type}"
                
                # Array constraints
                if expected_type == 'array':
                    items = field_spec.get('items', {})
                    min_items = field_spec.get('minItems')
                    max_items = field_spec.get('maxItems')
                    
                    if min_items and len(value) < min_items:
                        return False, f"Field '{field_name}' has too few items (min: {min_items})"
                    if max_items and len(value) > max_items:
                        return False, f"Field '{field_name}' has too many items (max: {max_items})"
                
                # String items in arrays
                if expected_type == 'array' and 'items' in field_spec:
                    items_type = field_spec['items'].get('type')
                    if items_type and not all(self._check_type(item, items_type) for item in value):
                        return False, f"Field '{field_name}' contains invalid items"
        
        return True, None
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """
        Check if value matches expected JSON type.
        
        Args:
            value: Value to check
            expected_type: Expected JSON schema type
            
        Returns:
            True if type matches
        """
        type_map = {
            'string': str,
            'number': (int, float),
            'integer': int,
            'boolean': bool,
            'array': list,
            'object': dict,
            'null': type(None)
        }
        
        expected = type_map.get(expected_type)
        if expected is None:
            return True  # Unknown type, skip validation
        
        return isinstance(value, expected)
    
    def get_output_extension(self) -> str:
        """Get file extension for structured output."""
        return '.json'
    
    def format_output(self, data: Dict[str, Any]) -> str:
        """
        Format JSON data for output file.
        
        Args:
            data: Validated JSON data
            
        Returns:
            Formatted JSON string
        """
        return json.dumps(data, indent=2, ensure_ascii=False)


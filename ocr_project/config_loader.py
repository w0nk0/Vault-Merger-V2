"""
Configuration loader for OCR project.

Loads settings from YAML configuration file, defaulting to root/.obsidian/OCRconfig.yaml
Command-line arguments override config file values.
"""

from pathlib import Path
from typing import Dict, Any, Optional


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file. If None, tries to auto-detect.
        
    Returns:
        Dictionary with configuration values, or empty dict if config not found/invalid
    """
    config = {}
    
    # Try to load YAML if available
    try:
        import yaml
    except ImportError:
        # PyYAML not installed - return empty config
        return config
    
    config_file = None
    
    # If explicit path provided, use it
    if config_path:
        config_file = Path(config_path)
        if not config_file.exists():
            return config
    
    # Load from file if found
    if config_file and config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"⚠️  Warning: Failed to load config file {config_file}: {e}")
            return {}
    
    return config


def get_config_path(vault_root: Optional[Path] = None) -> Optional[Path]:
    """
    Get default config file path (root/.obsidian/OCRconfig.yaml).
    
    Args:
        vault_root: Vault root directory. If None, returns None.
        
    Returns:
        Path to config file or None if vault_root not provided
    """
    if vault_root:
        config_file = vault_root / ".obsidian" / "OCRconfig.yaml"
        return config_file
    return None


def apply_config_to_args(args, config: Dict[str, Any]) -> None:
    """
    Apply config values to args namespace (only if not already set by CLI).
    
    Args:
        args: Argument namespace (from argparse)
        config: Configuration dictionary from YAML file
    """
    # Map config keys to argument names
    # Only set if CLI arg was not provided (default values don't count)
    config_to_arg_map = {
        'csv_json_summary_field': 'csv_json_summary_field',
        'csv_path': 'csv_path',
        'min_image_size_pixels': 'min_image_size',
        'model_name': 'model',
        'output_directory': 'output',
        'ocr_prompt': 'prompt',
        'device': 'device',
    }
    
    for config_key, arg_name in config_to_arg_map.items():
        if config_key in config:
            # Check if argument was explicitly provided (not just default)
            # For now, we'll check if the value is different from common defaults
            current_value = getattr(args, arg_name, None)
            config_value = config[config_key]
            
            # Apply config if:
            # 1. Current value is None, or
            # 2. Current value matches a common default (so config can override)
            if current_value is None or (current_value == get_default_value(arg_name)):
                if config_value is not None:
                    setattr(args, arg_name, config_value)
    
    # Store additional config values for later use (these aren't CLI args)
    if 'temperature' in config:
        args._config_temperature = config['temperature']
    
    if 'max_new_tokens' in config:
        args._config_max_new_tokens = config['max_new_tokens']
    
    if 'root' in config and not args.root:
        args.root = config['root']


def get_default_value(arg_name: str) -> Any:
    """Get default value for an argument (for comparison)."""
    defaults = {
        'csv_json_summary_field': 'summary',
        'csv_path': None,
        'min_image_size': 40000,
        'output': None,
        'device': None,
    }
    return defaults.get(arg_name, None)


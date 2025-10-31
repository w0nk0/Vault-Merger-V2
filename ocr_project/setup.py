"""
Setup file for the OCR project package.

NOTE: This project uses pyproject.toml as the single source of truth for dependencies.
Dependencies are managed via pyproject.toml for UV compatibility.
This setup.py is kept for backward compatibility but dependencies are defined in pyproject.toml.
"""
from setuptools import setup, find_packages

setup(
    name="ocr_vlm",
    version="0.2.5",
    packages=find_packages(),
    # Dependencies are managed in pyproject.toml
    # Use: uv sync (or: pip install -e .) to install dependencies
    install_requires=[
        # See pyproject.toml for complete dependency list
    ],
    author="OCR Project Team",
    description="OCR project using Vision Language Models with Transformers",
    python_requires=">=3.8",
)
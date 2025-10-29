"""
Setup file for the OCR project package.
"""
from setuptools import setup, find_packages

setup(
    name="ocr_gemma3",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # Dependencies will be filled in during implementation
    ],
    author="Your Name",
    description="OCR project using Google Gemma 3 LLM with Transformers",
    python_requires=">=3.8",
)
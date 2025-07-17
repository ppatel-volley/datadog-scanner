#!/usr/bin/env python3
"""Setup script for DataDog analyser."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README file
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = requirements_path.read_text(encoding="utf-8").strip().split("\n")

setup(
    name="datadog-analyser",
    version="1.0.0",
    description="A tool for analysing DataDog usage across code repositories",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Claude Code",
    author_email="noreply@anthropic.com",
    url="https://github.com/Volley-Inc/datadog-analyser",
    packages=find_packages(exclude=["tests*"]),
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "datadog-analyser=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: System :: Monitoring",
    ],
    keywords="datadog, analysis, monitoring, code-scanning, telemetry",
    project_urls={
        "Bug Reports": "https://github.com/Volley-Inc/datadog-analyser/issues",
        "Source": "https://github.com/Volley-Inc/datadog-analyser",
    },
)
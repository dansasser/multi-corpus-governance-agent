#!/usr/bin/env python3
"""
Multi-Corpus Governance Agent Setup Configuration
"""

from setuptools import setup, find_packages
import os
import sys

# Ensure we can import from src directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def read_requirements(filename):
    """Read requirements from file, filtering out comments and empty lines."""
    requirements = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments, empty lines, and optional dependencies
                if line and not line.startswith('#') and not line.startswith('//'):
                    requirements.append(line)
    except FileNotFoundError:
        print(f"Warning: {filename} not found")
    return requirements

def read_file(filename):
    """Read content from file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ""

# Read README for long description
long_description = read_file('README.md')
if not long_description:
    long_description = "Multi-Corpus Governance Agent with FastAPI integration"

# Core requirements from requirements.txt
install_requires = []
requirements_file = 'requirements.txt'
if os.path.exists(requirements_file):
    with open(requirements_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Include only uncommented, non-optional dependencies
            if (line and 
                not line.startswith('#') and 
                not line.startswith('//') and 
                '# Optional' not in line and
                '# Development' not in line and
                '# AI/ML Dependencies' not in line and
                '# Additional Security' not in line and
                '# Performance' not in line and
                '# Documentation' not in line and
                '# Production Deployment' not in line):
                install_requires.append(line)

# Development dependencies
dev_requires = [
    'jupyter>=1.0.0',
    'notebook>=7.0.0',
    'ipython>=8.0.0',
    'sphinx>=7.0.0',
    'sphinx-rtd-theme>=1.3.0',
    'pre-commit>=3.0.0',
    'bandit>=1.7.0',
    'safety>=2.0.0',
]

# Test dependencies
test_requires = [
    'pytest>=7.4.0',
    'pytest-asyncio>=0.21.0',
    'pytest-mock>=3.12.0',
    'pytest-cov>=4.1.0',
    'pytest-xdist>=3.5.0',
    'pytest-timeout>=2.1.0',
    'pytest-env>=1.0.0',
    'factory-boy>=3.3.0',
    'faker>=20.0.0',
    'httpx>=0.25.0',  # For testing FastAPI endpoints
    'respx>=0.20.0',  # For mocking HTTP requests
]

# Production dependencies
prod_requires = [
    'gunicorn>=21.0.0',
    'docker>=6.0.0',
    'supervisor>=4.2.0',
]

# AI/ML dependencies (optional)
ai_requires = [
    'openai>=1.6.0',
    'anthropic>=0.8.0',
    'langchain>=0.0.300',
    'transformers>=4.30.0',
    'sentence-transformers>=2.2.0',
    'numpy>=1.24.0',
    'pandas>=2.0.0',
]

setup(
    name="mcg-agent",
    version="1.0.0",
    description="Multi-Corpus Governance Agent with FastAPI integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="MCG Agent Development Team",
    author_email="dev@mcg-agent.com",
    url="https://github.com/your-org/mcg-agent",
    
    # Package configuration
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    
    # Dependencies
    install_requires=install_requires,
    extras_require={
        'dev': dev_requires + test_requires,
        'test': test_requires,
        'prod': prod_requires,
        'ai': ai_requires,
        'full': dev_requires + test_requires + prod_requires + ai_requires,
    },
    
    # Entry points for CLI commands
    entry_points={
        'console_scripts': [
            'mcg-agent=mcg_agent.cli.main:app',
            'mcg-setup=mcg_agent.cli.setup:main',
            'mcg-migrate=mcg_agent.database.cli:migrate_cli',
            'mcg-health=mcg_agent.cli.health:health_cli',
        ],
    },
    
    # Package data and resources
    package_data={
        'mcg_agent': [
            'api/templates/*',
            'database/migrations/*',
            'config/schemas/*',
            'governance/policies/*',
        ],
    },
    
    # Metadata
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: FastAPI",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    
    # Additional metadata
    keywords="fastapi governance agent ai multi-corpus authentication",
    project_urls={
        "Bug Reports": "https://github.com/your-org/mcg-agent/issues",
        "Source": "https://github.com/your-org/mcg-agent",
        "Documentation": "https://mcg-agent.readthedocs.io/",
    },
    
    # Development status
    zip_safe=False,
    include_package_data=True,
)
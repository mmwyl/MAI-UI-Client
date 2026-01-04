# Copyright (c) 2025, Alibaba Cloud and its affiliates;
# Licensed under the Apache License, Version 2.0 (the "License")

"""Setup script for MAI Phone Agent Framework."""

from setuptools import setup, find_packages
import os

# Read README for long description
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()
else:
    long_description = "MAI Phone Agent Framework - Autonomous Android control for MAI-UI models"

# Read requirements
requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
with open(requirements_path, "r", encoding="utf-8") as f:
    base_requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

# Additional requirements for phone agent
phone_agent_requirements = [
    "adbutils>=2.3.0",  # Pure Python ADB client
    "click>=8.0.0",     # CLI framework
    "pyyaml>=6.0",      # Configuration file parsing
]

all_requirements = base_requirements + phone_agent_requirements

setup(
    name="mai-ui",
    version="0.1.0",
    author="Alibaba Cloud - Tongyi MAI Team",
    author_email="yue.w@alibaba-inc.com",
    description="MAI-UI: Real-World Centric Foundation GUI Agents with Phone Agent Framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Tongyi-MAI/MAI-UI",
    project_urls={
        "Bug Reports": "https://github.com/Tongyi-MAI/MAI-UI/issues",
        "Source": "https://github.com/Tongyi-MAI/MAI-UI",
        "Documentation": "https://tongyi-mai.github.io/MAI-UI/",
    },
    packages=find_packages(include=["src", "src.*", "phone_agent", "phone_agent.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=all_requirements,
    entry_points={
        "console_scripts": [
            "mai-phone=phone_agent.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)

# -*- coding: utf-8 -*-
"""Setup configuration for microservice chassis package."""
from setuptools import setup, find_packages
import os

# Read README for long description
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as fh:
        long_description = fh.read()
else:
    long_description = "Delivery Chassis - Reusable components for Delivery"

setup(
    name="Delivery-chassis",
    version="1.0.0",
    author="Team 4",
    author_email="team@example.com",
    description="Reusable database components for Delivery following the Chassis pattern",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/your-org/chassis",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "sqlalchemy>=2.0.0,<3.0.0",
        "aiosqlite>=0.19.0",
    ],
    extras_require={
        "postgresql": ["asyncpg>=0.29.0"],
        "mysql": ["aiomysql>=0.2.0"],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "pylint>=2.17.0",
        ],
    },
    keywords="microservice chassis database sqlalchemy async crud",
    project_urls={
        "Bug Reports": "https://gitlab.com/your-org/chassis/-/issues",
        "Source": "https://gitlab.com/your-org/chassis",
        "Documentation": "https://gitlab.com/your-org/chassis/-/blob/main/README.md",
    },
)
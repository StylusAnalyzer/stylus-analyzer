from setuptools import setup, find_packages

setup(
    name="stylus-analyzer",  # Using hyphens in package name is more standard for pip install
    version="0.1.2",
    packages=find_packages(),
    install_requires=[
        "openai>=1.0.0",
         "python-dotenv>=1.0.0",
            "click>=8.0.0",
            "tree-sitter>=0.20.0",
            "reportlab>=3.6.0",  # For PDF generation
    ],
    entry_points={
        "console_scripts": [
            "stylus-analyzer=stylus_analyzer.cli:main",
        ],
    },
    description="AI-powered bug detection tool for Stylus/Rust contracts",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Jay Sojitra",
    author_email="jaysojitra1011@gmail.com",
    url="https://github.com/Jay-Sojitra/stylus-analyzer",
    keywords="stylus, rust, security, smart-contracts, analysis, ai",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Quality Assurance",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.8",
)

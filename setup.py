from setuptools import setup, find_packages
import os
import subprocess
import shutil

def copy_tree_sitter_rust():
    """Copy tree-sitter-rust files to the package"""
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define source and destination paths
    src_dir = os.path.join(current_dir, 'tree-sitter-rust')
    dst_dir = os.path.join(current_dir, 'stylus_analyzer', 'tree-sitter-rust')
    
    # Create destination directory if it doesn't exist
    os.makedirs(dst_dir, exist_ok=True)
    
    # Copy all files from source to destination
    if os.path.exists(src_dir):
        for item in os.listdir(src_dir):
            src = os.path.join(src_dir, item)
            dst = os.path.join(dst_dir, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

# Copy tree-sitter-rust files before setup
copy_tree_sitter_rust()

setup(
    name="stylus-analyzer",
    version="0.1.7",
    packages=find_packages(),
    package_data={
        'stylus_analyzer': [
            'tree-sitter-rust/src/*',
            'tree-sitter-rust/src/**/*',
            'tree-sitter-rust/grammar.js',
            'tree-sitter-rust/package.json',
            'tree-sitter-rust/README.md',
            'tree-sitter-rust/binding.gyp',
            'tree-sitter-rust/Cargo.toml',
            'build/*',
            'build/**/*',
        ],
    },
    include_package_data=True,
    install_requires=[
        "openai>=1.0.0",
        "python-dotenv>=1.0.0",
        "click>=8.0.0",
        "tree-sitter>=0.20.0",
        "setuptools>=42.0.0",
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
    author_email="jaysojitra@lampros.tech",
    url="https://github.com/StylusAnalyzer/stylus-analyzer",
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

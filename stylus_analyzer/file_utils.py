"""
Utility functions for file operations in the Stylus Analyzer
"""
import os
import glob
from typing import List, Optional, Dict, Any, Tuple


def find_rust_contracts(directory: str) -> List[str]:
    """
    Find all Rust contract files in the given directory
    
    Args:
        directory: The directory to search in
        
    Returns:
        List of file paths to Rust contracts
    """
    contract_files = []
    
    # Common patterns for Rust contract files in Stylus projects
    rust_patterns = [
        os.path.join(directory, "**", "*.rs"),
        os.path.join(directory, "src", "**", "*.rs"),
        os.path.join(directory, "contracts", "**", "*.rs"),
        os.path.join(directory, "lib", "**", "*.rs"),
    ]
    
    for pattern in rust_patterns:
        contract_files.extend(glob.glob(pattern, recursive=True))
    
    # Remove duplicates
    contract_files = list(set(contract_files))
    
    return contract_files


def read_file_content(file_path: str) -> Optional[str]:
    """
    Read the content of a file
    
    Args:
        file_path: Path to the file
        
    Returns:
        File content as string, or None if file can't be read
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return None


def find_readme(directory: str) -> Optional[str]:
    """
    Find and read the README file in the given directory
    
    Args:
        directory: The directory to search in
        
    Returns:
        Content of the README file, or None if not found
    """
    readme_patterns = [
        "README.md",
        "Readme.md",
        "readme.md",
        "README.txt",
        "readme.txt",
    ]
    
    for pattern in readme_patterns:
        readme_path = os.path.join(directory, pattern)
        if os.path.exists(readme_path):
            return read_file_content(readme_path)
    
    return None


def collect_project_files(directory: str) -> Dict[str, Any]:
    """
    Collect all relevant files from the Stylus project
    
    Args:
        directory: The root directory of the project
        
    Returns:
        Dictionary containing contract files and README content
    """
    contract_files = find_rust_contracts(directory)
    readme_content = find_readme(directory)
    
    contract_contents = {}
    for file_path in contract_files:
        content = read_file_content(file_path)
        if content:
            contract_contents[file_path] = content
    
    return {
        "contracts": contract_contents,
        "readme": readme_content,
        "project_dir": directory
    } 

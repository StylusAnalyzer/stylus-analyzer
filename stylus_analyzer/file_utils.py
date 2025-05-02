
"""
Utility functions for file operations in the Stylus Analyzer
"""
import os
import glob
from typing import List, Optional, Dict, Any, Tuple
import tree_sitter
from tree_sitter import Language, Parser
import pkg_resources
import shutil

# Global parser instance to avoid recreating it multiple times
_RUST_PARSER = None

def get_rust_parser():
    """
    Get or initialize the Rust parser (singleton pattern)
    
    Returns:
        Parser instance configured for Rust
    """
    global _RUST_PARSER
    if _RUST_PARSER is None:
        try:
            # Get the package directory
            package_dir = pkg_resources.resource_filename('stylus_analyzer', '')
            
            # Define paths
            build_dir = os.path.join(package_dir, 'build')
            rust_dir = os.path.join(package_dir, 'tree-sitter-rust')
            so_file = os.path.join(build_dir, 'my-languages.so')
            
            # Create build directory if it doesn't exist
            os.makedirs(build_dir, exist_ok=True)
            
            # Only build the library if it doesn't exist
            if not os.path.exists(so_file):
                tree_sitter.Language.build_library(
                    so_file,
                    [rust_dir]
                )
            
            # Load the Rust language
            rust_language = Language(so_file, 'rust')
            
            # Initialize the parser
            _RUST_PARSER = Parser()
            _RUST_PARSER.set_language(rust_language)
        except Exception as e:
            print(f"Error initializing Rust parser: {str(e)}")
            # Return a None parser which will be handled by the callers
    
    return _RUST_PARSER

def generate_rust_ast(code: str):
    """
    Generate AST for Rust code using tree-sitter
    
    Args:
        code: Rust source code as string
        
    Returns:
        Tree object representing the parsed AST
    """
    parser = get_rust_parser()
    if not parser:
        return None
        
    return parser.parse(bytes(code, "utf8"))

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

"""
Utility functions for file operations in the Stylus Analyzer
"""
import os
import glob
from typing import List, Optional, Dict, Any, Tuple
import tree_sitter
from tree_sitter import Language, Parser

# Prepare the Rust parser (downloaded grammar will be required)
RUST_LANGUAGE = None
try:
    # You need to build the language library with the Rust grammar first
    # e.g. tree-sitter build instructions: https://tree-sitter.github.io/tree-sitter/using-parsers#python
    Language.build_library(
        'build/my-languages.so',
        [
            'tree-sitter-rust'
        ]
    )
    RUST_LANGUAGE = Language('build/my-languages.so', 'rust')
except Exception:
    pass  # If already built, or for runtime only

def get_rust_parser():
    global RUST_LANGUAGE
    if RUST_LANGUAGE is None:
        RUST_LANGUAGE = Language('build/my-languages.so', 'rust')
    parser = Parser()
    parser.set_language(RUST_LANGUAGE)
    return parser

def generate_rust_ast(code: str):
    """
    Generate AST for Rust code using tree-sitter
    """
    parser = get_rust_parser()
    tree = parser.parse(bytes(code, "utf8"))
    return tree

def print_rust_ast(tree, code: str, max_depth: int = 10, _node=None, _depth=0):
    """
    Recursively print the AST tree for Rust code
    """
    if _node is None:
        _node = tree.root_node
    indent = '  ' * _depth
    print(f"{indent}{_node.type} [{_node.start_point} - {_node.end_point}]")
    if _depth >= max_depth:
        print(f"{indent}  ... (max depth reached)")
        return
    for child in _node.children:
        print_rust_ast(tree, code, max_depth, child, _depth + 1)

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

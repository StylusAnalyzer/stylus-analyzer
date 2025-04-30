"""
Base detector class for static analysis
"""
import logging
from typing import Tuple
from tree_sitter import Node, Tree

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BaseDetector:
    """Base class for all static analysis detectors"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        
    def detect(self, tree: Tree, code: str, results: 'StaticAnalysisResult') -> None:
        """
        Execute detection logic
        
        Args:
            tree: The AST tree
            code: The source code
            results: The results object to add issues to
        """
        raise NotImplementedError("Detector classes must implement detect()")
    
    def _get_node_text(self, node: Node, code: str) -> str:
        """Get the text of a node from the source code"""
        if node.start_byte >= len(code) or node.end_byte > len(code):
            return ""
        return code[node.start_byte:node.end_byte]
    
    def _get_line_for_node(self, node: Node) -> Tuple[int, int]:
        """Get the start and end line numbers for a node"""
        return node.start_point[0] + 1, node.end_point[0] + 1 

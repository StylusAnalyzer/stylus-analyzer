"""
Detector for panic!() macro calls in Stylus Rust contracts
"""
from tree_sitter import Node, Tree

from stylus_analyzer.detectors.detector_base import BaseDetector


class PanicDetector(BaseDetector):
    """
    Detector for panic!() macro calls in Stylus Rust contracts.
    
    panic!() causes the program to immediately terminate with an error message,
    which is dangerous in blockchain contexts where transactions must be handled gracefully.
    """
    
    def __init__(self):
        super().__init__(
            name="unsafe_panic",
            description="Detects panic!() macro calls that cause immediate termination"
        )
        
    def detect(self, tree: Tree, code: str, results) -> None:
        """Detect panic!() macro calls in the contract"""
        # Track found panic calls by location to avoid duplicates
        self.found_locations = set()
        self._find_panic_calls(tree.root_node, code, results)
    
    def _find_panic_calls(self, node: Node, code: str, results) -> None:
        """Recursively search for panic!() macro calls in the contract"""
        # Check for macro invocations
        if node.type == "macro_invocation":
            node_text = self._get_node_text(node, code)
            
            # Check if this is a panic! macro call
            if node_text.startswith("panic!"):
                # Get the location to avoid duplicates
                location = (node.start_point[0], node.end_point[0])
                
                # Check if we've already reported this panic call
                if location not in self.found_locations:
                    self.found_locations.add(location)
                    
                    line_start, line_end = self._get_line_for_node(node)
                    function_node = self._find_parent_function(node)
                    function_name = self._get_function_name(function_node, code) if function_node else "unknown"
                    
                    results.add_issue(
                        issue_type="unsafe_panic",
                        severity="High",
                        description=f"Unsafe call to panic!() macro in function '{function_name}'. This causes immediate termination and cannot be caught.",
                        line_start=line_start,
                        line_end=line_end,
                        code_snippet=node_text,
                        recommendation="Use Result/Option types with explicit error handling or the ? operator instead of panic!()."
                    )
        
        # Process all children
        for child in node.children:
            self._find_panic_calls(child, code, results)
            
    def _find_parent_function(self, node: Node) -> Node:
        """Find the parent function containing this node"""
        parent = node.parent
        while parent:
            if parent.type in ["function_item", "impl_item", "method_item"]:
                return parent
            parent = parent.parent
        return None
    
    def _get_function_name(self, node: Node, code: str) -> str:
        """Extract the function name from a function node"""
        if not node:
            return "unknown"
            
        # For Rust functions
        for child in node.children:
            if child.type == "identifier":
                return self._get_node_text(child, code)
        
        return "unknown"
        
    def _get_line_for_node(self, node: Node) -> tuple:
        """Get the line number for a node (1-indexed)"""
        return node.start_point[0] + 1, node.end_point[0] + 1
    
    def _get_node_text(self, node: Node, code: str) -> str:
        """Get the text of a node from the code"""
        if node.start_byte < 0 or node.end_byte > len(code) or node.start_byte >= node.end_byte:
            return ""
        return code[node.start_byte:node.end_byte] 

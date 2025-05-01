"""
Detector for potentially unsafe unwrap() calls in Stylus Rust contracts
"""
from tree_sitter import Node, Tree

from stylus_analyzer.detectors.detector_base import BaseDetector


class UnwrapDetector(BaseDetector):
    """
    Detector for .unwrap() calls in Stylus Rust contracts.
    
    These calls can cause runtime panics if the value is None/Err,
    which is dangerous in blockchain contexts where transactions can't be reverted
    after a panic.
    """
    
    def __init__(self):
        super().__init__(
            name="unsafe_unwrap",
            description="Detects potentially unsafe .unwrap() calls that can panic at runtime"
        )
        
    def detect(self, tree: Tree, code: str, results) -> None:
        """Detect unwrap calls in the contract"""
        # Track found unwrap calls by location to avoid duplicates
        self.found_locations = set()
        self._find_unwrap_calls(tree.root_node, code, results)
    
    def _find_unwrap_calls(self, node: Node, code: str, results) -> None:
        """Recursively search for unwrap calls in the contract"""
        # Check for call expressions (method calls)
        if node.type == "call_expression":
            # Check if the method being called is unwrap
            method_name = self._get_method_name(node, code)
            if method_name == "unwrap":
                # Get the location to avoid duplicates
                location = (node.start_point[0], node.end_point[0])
                
                # Check if we've already reported this unwrap call
                if location not in self.found_locations:
                    self.found_locations.add(location)
                    
                    line_start, line_end = self._get_line_for_node(node)
                    function_node = self._find_parent_function(node)
                    function_name = self._get_function_name(function_node, code) if function_node else "unknown"
                    
                    results.add_issue(
                        issue_type="unsafe_unwrap",
                        severity="Medium",
                        description=f"Potentially unsafe call to .unwrap() in function '{function_name}'. This can cause runtime panics if the value is None/Err.",
                        line_start=line_start,
                        line_end=line_end,
                        code_snippet=self._get_node_text(node, code),
                        recommendation="Use pattern matching, if let, or explicit error handling (like ? operator) instead of unwrap()."
                    )
        
        # Process all children
        for child in node.children:
            self._find_unwrap_calls(child, code, results)
    
    def _get_method_name(self, node: Node, code: str) -> str:
        """Extract the method name from a call expression"""
        for child in node.children:
            # Field expressions like obj.method
            if child.type == "field_expression":
                for field_child in child.children:
                    if field_child.type == "field_identifier":
                        return self._get_node_text(field_child, code)
        return ""
    
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

"""
Detector for unchecked transfer calls in Stylus Rust contracts
"""
from tree_sitter import Node, Tree

from stylus_analyzer.detectors.detector_base import BaseDetector


class UncheckedTransferDetector(BaseDetector):
    """Detector for unchecked transfer calls in Stylus contracts"""
    
    def __init__(self):
        super().__init__(
            name="unchecked_transfer",
            description="Detects unchecked transfer calls where the return value is not checked"
        )
        
    def detect(self, tree: Tree, code: str, results) -> None:
        """Detect unchecked transfers in the contract"""
        # Find all function calls
        self._find_unchecked_transfers(tree.root_node, code, results)
    
    def _find_unchecked_transfers(self, node: Node, code: str, results) -> None:
        """Recursively search for unchecked transfer calls"""
        # If this is a transfer-like method call
        if self._is_transfer_call(node, code):
            # Check if it's properly handled
            if not self._is_properly_checked(node, code):
                # Extract info and add issue
                line_start, line_end = self._get_line_for_node(node)
                snippet = self._get_node_text(node, code)
                
                results.add_issue(
                    issue_type="unchecked_transfer",
                    severity="High",
                    description="Transfer call with unchecked return value. This can lead to silent failures when transfers fail.",
                    line_start=line_start,
                    line_end=line_end,
                    code_snippet=snippet,
                    recommendation="Check the return value of transfer calls or use a function that reverts on failure (like transfer_or_revert)."
                )
        
        # Recursively check all children
        for child in node.children:
            self._find_unchecked_transfers(child, code, results)
    
    def _is_transfer_call(self, node: Node, code: str) -> bool:
        """Check if a node represents a transfer-like method call"""
        # Look for method call expressions
        if node.type == "call_expression":
            method_name = ""
            
            # Get the method name
            field_expr = next((child for child in node.children if child.type == "field_expression"), None)
            if field_expr:
                method_id = next((child for child in field_expr.children if child.type == "field_identifier"), None)
                if method_id:
                    method_name = self._get_node_text(method_id, code)
            
            # Function identifier (direct function call)
            identifier = next((child for child in node.children if child.type == "identifier"), None)
            if identifier:
                method_name = self._get_node_text(identifier, code)
            
            # Check for transfer-related method names
            transfer_methods = ["transfer", "send", "transferFrom"]
            return method_name in transfer_methods
        
        return False
    
    def _is_properly_checked(self, node: Node, code: str) -> bool:
        """
        Check if the transfer call result is properly handled
        
        For a transfer to be considered properly checked, it must:
        1. Be used in a condition (if, require, assert)
        2. Be assigned to a variable that is later checked
        3. Be used with a method that reverts on failure
        """
        # Find parent expressions to check how the transfer call is used
        parent = node.parent
        
        # Check if it's in a condition (if, require, assert)
        while parent and parent.type not in ["if_expression", "binary_expression", 
                                             "call_expression", "match_expression",
                                             "let_declaration", "assignment_expression"]:
            parent = parent.parent
        
        if not parent:
            return False
            
        # It's in a condition or assignment
        if parent.type in ["if_expression", "binary_expression", "match_expression"]:
            return True
            
        # It's in a require-like statement
        if parent.type == "call_expression":
            call_name = ""
            first_child = next((child for child in parent.children if child.type == "identifier"), None)
            if first_child:
                call_name = self._get_node_text(first_child, code)
                
            check_functions = ["require", "assert", "ensure"]
            return call_name in check_functions
            
        # It's assigned to a variable - we would need further analysis to check if that variable is checked
        # For now, we'll conservatively assume it's unchecked if we can't prove it's checked
        return False 

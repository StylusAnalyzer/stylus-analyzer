"""
Detector for unsafe encode_packed operations in Stylus Rust contracts
"""
from tree_sitter import Node, Tree

from stylus_analyzer.detectors.detector_base import BaseDetector


class EncodePackedDetector(BaseDetector):
    """
    Detector for unsafe encode_packed operations in Stylus Rust contracts.
    
    encode_packed concatenates values without padding, which can lead to hash collisions
    when used with dynamic types (e.g., encode_packed("a", "bc") == encode_packed("ab", "c")).
    This is especially dangerous when hashing the result for signatures, authentication, etc.
    """
    
    def __init__(self):
        super().__init__(
            name="unsafe_encode_packed",
            description="Detects potentially unsafe encode_packed operations with dynamic types"
        )
        
    def detect(self, tree: Tree, code: str, results) -> None:
        """Detect unsafe encode_packed calls in the contract"""
        # Track found unsafe calls by location to avoid duplicates
        self.found_locations = set()
        self._find_encode_packed_calls(tree.root_node, code, results)
    
    def _find_encode_packed_calls(self, node: Node, code: str, results) -> None:
        """Recursively search for unsafe encode_packed calls in the contract"""
        # Look for method call expressions
        if node.type == "call_expression":
            # Get method name
            method_text = self._get_node_text(node, code)
            
            # Check if it's using the abi_encode_packed method or similar
            if "encode_packed" in method_text or "abi_encode_packed" in method_text:
                # Check if this is potentially unsafe (using with dynamic types)
                if self._is_potentially_unsafe_usage(node, code):
                    # Get the location to avoid duplicates
                    location = (node.start_point[0], node.end_point[0])
                    
                    # Check if we've already reported this call
                    if location not in self.found_locations:
                        self.found_locations.add(location)
                        
                        line_start, line_end = self._get_line_for_node(node)
                        function_node = self._find_parent_function(node)
                        function_name = self._get_function_name(function_node, code) if function_node else "unknown"
                        
                        results.add_issue(
                            issue_type="unsafe_encode_packed",
                            severity="Medium",
                            description=f"Potentially unsafe use of encode_packed in function '{function_name}'. When used with dynamic types like strings, it may lead to hash collisions.",
                            line_start=line_start,
                            line_end=line_end,
                            code_snippet=method_text,
                            recommendation="Use regular abi_encode instead, or ensure you're only using fixed-size types with encode_packed, or add delimiters between dynamic values."
                        )
            
            # Also check for direct concatenation of strings/byte arrays without delimiters
            elif ".concat()" in method_text or ".concat(" in method_text:
                # See if this is directly using string concatenation without delimiters
                if self._is_unsafe_concat(node, code):
                    location = (node.start_point[0], node.end_point[0])
                    
                    if location not in self.found_locations:
                        self.found_locations.add(location)
                        
                        line_start, line_end = self._get_line_for_node(node)
                        function_node = self._find_parent_function(node)
                        function_name = self._get_function_name(function_node, code) if function_node else "unknown"
                        
                        results.add_issue(
                            issue_type="unsafe_encode_packed",
                            severity="Medium",
                            description=f"Potentially unsafe manual byte concatenation in function '{function_name}'. Concatenating dynamic types without delimiters can lead to collisions.",
                            line_start=line_start,
                            line_end=line_end,
                            code_snippet=method_text,
                            recommendation="Add a delimiter (e.g., a zero byte) between concatenated dynamic values."
                        )
        
        # Also look for direct manual packing with array concatenation
        elif node.type == "array_expression" and node.parent and node.parent.type == "field_expression":
            array_text = self._get_node_text(node, code)
            parent_text = self._get_node_text(node.parent, code)
            
            if "concat" in parent_text and "as_bytes" in array_text and ".as_bytes(), " in array_text:
                # This is likely manual concatenation of string-like objects
                location = (node.start_point[0], node.end_point[0])
                
                if location not in self.found_locations:
                    self.found_locations.add(location)
                    
                    line_start, line_end = self._get_line_for_node(node)
                    function_node = self._find_parent_function(node)
                    function_name = self._get_function_name(function_node, code) if function_node else "unknown"
                    
                    results.add_issue(
                        issue_type="unsafe_encode_packed",
                        severity="Medium",
                        description=f"Manual byte packing without delimiters in function '{function_name}'. This can cause hash collisions with different inputs.",
                        line_start=line_start,
                        line_end=line_end,
                        code_snippet=parent_text,
                        recommendation="Add a delimiter (e.g., a zero byte) between concatenated string/byte values."
                    )
        
        # Process all children
        for child in node.children:
            self._find_encode_packed_calls(child, code, results)
    
    def _is_potentially_unsafe_usage(self, node: Node, code: str) -> bool:
        """Check if the encode_packed usage is potentially unsafe (using with dynamic types)"""
        # Get the full expression
        call_text = self._get_node_text(node, code)
        
        # Check if it involves dynamic types like String or dynamic byte arrays
        if "String" in call_text or "string" in call_text or "SOLString" in call_text:
            return True
            
        # If it's using fixed-size types, it's likely safer
        if ("Address" in call_text and "U256" in call_text) and not ("String" in call_text):
            return False
            
        # Look at the types being used in the encode_packed call
        function_node = self._find_parent_function(node)
        if function_node:
            function_text = self._get_node_text(function_node, code)
            # Check for dynamic type definitions near the encode_packed call
            if "SOLString" in function_text and "encode_packed" in function_text:
                # This suggests encoding strings with encode_packed
                return True
                
        return False
    
    def _is_unsafe_concat(self, node: Node, code: str) -> bool:
        """Check if this is an unsafe concatenation of strings/byte arrays"""
        call_text = self._get_node_text(node, code)
        
        # Check if it's concatenating string-like objects without delimiters
        if ("as_bytes" in call_text or "as_bytes()" in call_text) and ".concat" in call_text:
            # Look for delimiters
            if "delimiter" not in call_text and "0u8" not in call_text:
                return True
                
        return False
    
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

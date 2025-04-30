"""
Detector for unsafe transfer patterns in Stylus Rust contracts
"""
from tree_sitter import Node, Tree

from stylus_analyzer.detectors.detector_base import BaseDetector


class UnsafeTransferDetector(BaseDetector):
    """
    Detector for potentially unsafe transfer patterns in Stylus/Rust contracts.
    Identifies cases where transfers are made to untrusted or unvalidated addresses.
    """
    
    def __init__(self):
        super().__init__(
            name="unsafe_transfer",
            description="Detects potentially unsafe transfers to unvalidated addresses"
        )
        
    def detect(self, tree: Tree, code: str, results) -> None:
        """Detect unsafe transfers in the contract"""
        self._find_unsafe_transfers(tree.root_node, code, results)
    
    def _find_unsafe_transfers(self, node: Node, code: str, results) -> None:
        """Recursively search for potentially unsafe transfer calls"""
        # If this is a transfer-like method call
        if self._is_transfer_call(node, code):
            # Check if it's to a potentially unsafe address
            if self._is_potentially_unsafe_transfer(node, code):
                # Extract info and add issue
                line_start, line_end = self._get_line_for_node(node)
                snippet = self._get_node_text(node, code)
                
                results.add_issue(
                    issue_type="unsafe_transfer",
                    severity="Medium",
                    description="Transfer to potentially unsafe or unvalidated address. This can lead to funds being sent to malicious contracts or incorrect addresses.",
                    line_start=line_start,
                    line_end=line_end,
                    code_snippet=snippet,
                    recommendation="Validate recipient addresses before transfers. Consider implementing address whitelisting or validation checks."
                )
        
        # Recursively check all children
        for child in node.children:
            self._find_unsafe_transfers(child, code, results)
    
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
    
    def _is_potentially_unsafe_transfer(self, node: Node, code: str) -> bool:
        """
        Check if a transfer is potentially unsafe
        
        A transfer is considered potentially unsafe if:
        1. The recipient is a parameter passed directly to the function (external control)
        2. The recipient comes from an external source without validation
        3. The recipient is a dynamic calculation without checks
        """
        # Get the arguments to the transfer call
        arg_list = next((child for child in node.children if child.type == "arguments"), None)
        if not arg_list or not arg_list.children:
            return False
        
        # For transfer methods, typically the first argument is the recipient
        # For transferFrom, typically the second argument is the recipient
        recipient_index = 0
        method_name = ""
        
        # Get the method name to determine which argument is the recipient
        field_expr = next((child for child in node.children if child.type == "field_expression"), None)
        if field_expr:
            method_id = next((child for child in field_expr.children if child.type == "field_identifier"), None)
            if method_id:
                method_name = self._get_node_text(method_id, code)
        
        identifier = next((child for child in node.children if child.type == "identifier"), None)
        if identifier:
            method_name = self._get_node_text(identifier, code)
        
        if method_name == "transferFrom":
            recipient_index = 1
        
        # Get all arguments
        arguments = [child for child in arg_list.children if child.type not in ["(", ")", ","]]
        if recipient_index >= len(arguments):
            return False
        
        recipient = arguments[recipient_index]
        
        # Check if the recipient is validated
        # This is a simplified heuristic - in practice, you'd need more context
        if recipient.type == "identifier":
            # If it's a simple variable, we need to track where it comes from
            # For simplicity, we'll just flag any direct parameter use
            recipient_name = self._get_node_text(recipient, code)
            
            # Check if this identifier appears in any require/assert statement above
            # For simplicity, we'll just check if this is a function parameter
            # A more sophisticated analysis would track data flow
            
            # Find the nearest function definition
            function_node = self._find_parent_function(node)
            if function_node:
                # Check if recipient is in the parameters
                parameters = self._get_function_parameters(function_node, code)
                if recipient_name in parameters:
                    # It's a parameter - check if it's validated
                    if not self._is_parameter_validated(function_node, recipient_name, code):
                        return True
        
        # If it's a direct msg.sender reference, that's usually safe
        if recipient.type == "field_expression":
            expr_text = self._get_node_text(recipient, code)
            if "msg.sender" in expr_text:
                return False
        
        # Flag any complex expressions as potentially unsafe
        if recipient.type in ["binary_expression", "call_expression"]:
            # This is a simplified approach - we'd need data flow analysis to be more precise
            return True
            
        return False
    
    def _find_parent_function(self, node: Node) -> Node:
        """Find the parent function definition node"""
        current = node
        while current and current.type not in ["function_item", "function_definition"]:
            current = current.parent
        return current
    
    def _get_function_parameters(self, function_node: Node, code: str) -> list:
        """Extract parameter names from function definition"""
        parameters = []
        
        # Find the parameters list
        params_node = next((child for child in function_node.children if child.type == "parameters"), None)
        if not params_node:
            return parameters
        
        # Extract parameter names
        for child in params_node.children:
            if child.type == "parameter":
                # Find the identifier in the parameter
                param_name = next((subchild for subchild in child.children if subchild.type == "identifier"), None)
                if param_name:
                    parameters.append(self._get_node_text(param_name, code))
        
        return parameters
    
    def _is_parameter_validated(self, function_node: Node, param_name: str, code: str) -> bool:
        """
        Check if a parameter is validated within a function
        
        This is a simplified approach - a real implementation would need data flow analysis
        """
        # Look for require/assert statements in the function body
        body_node = next((child for child in function_node.children if child.type == "block"), None)
        if not body_node:
            return False
        
        # Find all require/assert/if statements in the body
        validation_found = False
        
        def find_validations(node):
            nonlocal validation_found
            
            if validation_found:
                return
                
            # Check for require/assert calls
            if node.type == "call_expression":
                func_name = ""
                
                # Get function name
                first_child = next((child for child in node.children if child.type == "identifier"), None)
                if first_child:
                    func_name = self._get_node_text(first_child, code)
                
                if func_name in ["require", "assert"]:
                    # Check if our parameter is used in the check
                    node_text = self._get_node_text(node, code)
                    if param_name in node_text:
                        validation_found = True
                        return
            
            # Check conditionals
            if node.type == "if_expression":
                condition = next((child for child in node.children if child.type in ["binary_expression", "call_expression"]), None)
                if condition:
                    condition_text = self._get_node_text(condition, code)
                    if param_name in condition_text:
                        validation_found = True
                        return
            
            # Recursively check children
            for child in node.children:
                find_validations(child)
        
        find_validations(body_node)
        return validation_found 

"""
Detector for unsafe transfer patterns in Stylus Rust contracts
"""
from tree_sitter import Node, Tree

from stylus_analyzer.detectors.detector_base import BaseDetector


class UnsafeTransferDetector(BaseDetector):
    """
    Detector for unsafe transfer patterns in Stylus/Rust contracts.
    Identifies cases where transfers might be made to untrusted addresses.
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
        """Recursively search for unsafe transfers in the contract"""
        # Process function definitions for potential unsafe transfers
        if node.type in ["function_item", "function_definition"]:
            self._check_function_for_unsafe_transfers(node, code, results)
        
        # Check for Solidity function in sol! macro
        elif self._is_in_sol_macro(node, code):
            node_text = self._get_node_text(node, code)
            
            if "function " in node_text and "transfer" in node_text:
                # Extract function name and parameters
                func_name = self._extract_solidity_function_name(node_text)
                
                # Check if function has address parameters involved in transfers
                addresses = self._extract_address_params(node_text)
                
                if addresses and not self._has_address_validation(node_text, addresses):
                        line_start, line_end = self._get_line_for_node(node)
                        
                        results.add_issue(
                            issue_type="unsafe_transfer",
                            severity="Medium",
                        description=f"Function '{func_name}' contains transfers to potentially unvalidated addresses.",
                            line_start=line_start,
                            line_end=line_end,
                        code_snippet=self._get_function_signature(node, code),
                            recommendation="Validate address parameters before using them in transfer operations."
                        )
        
        # Process all children
        for child in node.children:
            self._find_unsafe_transfers(child, code, results)
    
    def _check_function_for_unsafe_transfers(self, node: Node, code: str, results) -> None:
        """Check if a function contains unsafe transfer patterns"""
        function_text = self._get_node_text(node, code)
        func_name = self._get_function_name(node, code)
        
        # Skip if this is a constructor, entry point, or internal function
        if any(keyword in func_name.lower() for keyword in ["constructor", "deploy", "main", "internal"]):
            return
        
        # Check if this function uses transfers
        if "transfer" not in function_text and ".call(" not in function_text:
            return
            
        # Get parameters and identify address types
        params = self._extract_function_parameters(node, code)
        address_params = [p for p in params if "Address" in p or "address" in p]
        
        # If we have address parameters used in transfers
        if address_params and self._are_params_used_in_transfers(function_text, address_params):
            # Check if the addresses are validated anywhere
            if not self._has_address_validation(function_text, address_params):
                line_start, line_end = self._get_line_for_node(node)
                
                results.add_issue(
                    issue_type="unsafe_transfer",
                    severity="Medium",
                    description=f"Function '{func_name}' performs transfers to potentially unvalidated address parameters.",
                    line_start=line_start,
                    line_end=line_end,
                    code_snippet=self._get_function_signature(node, code),
                    recommendation="Validate address parameters before using them in transfer operations."
                )
    
    def _extract_solidity_function_name(self, function_text: str) -> str:
        """Extract the name from a Solidity function definition"""
        if "function " in function_text:
            start_idx = function_text.find("function ") + 9
            end_idx = function_text.find("(", start_idx)
            if start_idx < end_idx:
                return function_text[start_idx:end_idx].strip()
        return ""
        
    def _extract_address_params(self, function_text: str) -> list:
        """Extract address parameters from a function definition"""
        address_params = []
        
        # For Solidity style
        if "function " in function_text and "(" in function_text:
            params_start = function_text.find("(")
            params_end = function_text.find(")")
            
            if params_start > 0 and params_end > params_start:
                params_text = function_text[params_start+1:params_end]
                
                for param in params_text.split(","):
                    param = param.strip()
                    if "address" in param:
                        # Extract parameter name (last word in the parameter)
                        name = param.split()[-1].strip()
                        address_params.append(name)
        
        # For Rust style
        elif "fn " in function_text and "Address" in function_text:
            lines = function_text.split("\n")
            for line in lines:
                if ":" in line and "Address" in line:
                    param_name = line.split(":")[0].strip()
                    address_params.append(param_name)
        
        return address_params
    
    def _extract_function_parameters(self, node: Node, code: str) -> list:
        """Extract parameters from a function definition"""
        params = []
        
        # Find the parameter list
        for child in node.children:
            if child.type == "parameters":
                # Process each parameter
                for param_child in child.children:
                    if param_child.type == "parameter":
                        param_text = self._get_node_text(param_child, code)
                        params.append(param_text)
        
        return params
    
    def _are_params_used_in_transfers(self, function_text: str, address_params: list) -> bool:
        """Check if address parameters are used in transfer operations"""
        # Check each parameter
        for param in address_params:
            # Extract the parameter name without type info
            param_name = param.split(":")[-1].strip() if ":" in param else param
            
            # Common transfer patterns
            transfer_patterns = [
                f".transfer({param_name}",
                f".transfer({param_name},",
                f".transferFrom({param_name}",
                f".transferFrom({param_name},",
                f"transfer(address,uint256).*{param_name}",
                f"transferFrom(address,address,uint256).*{param_name}"
            ]
            
            # Check if any parameter is used in a transfer
            if any(pattern in function_text for pattern in transfer_patterns):
                            return True
        
        return False
    
    def _has_address_validation(self, function_text: str, address_params: list) -> bool:
        """Check if address parameters are validated before use"""
                # Common validation patterns
        validation_patterns = [
            "require", "assert", "revert",       # Solidity validation
            "== Address::ZERO", "!= Address::ZERO",   # Rust validation
            "Address::zero()", "is_zero()",           # Zero address checks
            "== 0x0", "!= 0x0"                   # Other common patterns
        ]
        
        # Check if any address parameter is validated
        for param in address_params:
            # Extract parameter name without type info
            param_name = param.split(":")[-1].strip() if ":" in param else param
            
            # Look for validations of this parameter
            param_validated = False
            for pattern in validation_patterns:
                if f"{param_name} {pattern}" in function_text or f"{pattern}({param_name}" in function_text:
                    param_validated = True
                    break
            
            # If this parameter is not validated, return false
            if not param_validated:
                return False
        
        # All parameters are validated
        return True
    
    def _is_in_sol_macro(self, node: Node, code: str) -> bool:
        """Check if this node is within a sol! macro"""
        parent = node
        while parent:
            if parent.type == "macro_invocation":
                macro_text = self._get_node_text(parent, code)
                if "sol!" in macro_text:
                    return True
            parent = parent.parent
                            
        return False
        
    def _get_function_name(self, node: Node, code: str) -> str:
        """Extract the function name from a function definition node"""
        # For Rust functions
        for child in node.children:
            if child.type == "identifier":
                return self._get_node_text(child, code)
        
        # For Solidity functions in sol! macro
        function_text = self._get_node_text(node, code)
        if "function " in function_text:
            return self._extract_solidity_function_name(function_text)
                
        return ""
        
    def _get_function_signature(self, node: Node, code: str) -> str:
        """Get a simplified function signature for display in results"""
        # For Solidity functions in sol! macro
        if self._is_in_sol_macro(node, code):
            function_text = self._get_node_text(node, code)
            
        if "function " in function_text:
            lines = function_text.split("\n")
            for line in lines:
                if "function " in line:
                    end_idx = line.find("{")
                    if end_idx > 0:
                        return line[:end_idx].strip()
                    return line.strip()
                    
        # For Rust functions
        function_name = self._get_function_name(node, code)
        if function_name:
            return f"fn {function_name}(...)"
            
        # Default fallback
        return self._get_node_text(node, code).split("\n")[0]

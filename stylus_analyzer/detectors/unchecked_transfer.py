"""
Detector for unchecked transfer calls in Stylus Rust contracts
"""
from tree_sitter import Node, Tree
from typing import Optional

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
        self._find_unchecked_transfers(tree.root_node, code, results)
        self._check_solidity_unchecked_transfers(code, results)
    
    def _find_unchecked_transfers(self, node: Node, code: str, results) -> None:
        """Recursively search for unchecked transfer calls"""
        # Check for Rust function calls
        if node.type == "call_expression":
            call_text = self._get_node_text(node, code)
            
            # Check for ERC20 transfer/transferFrom calls using the SDK interface
            if any(method in call_text for method in [".transfer(", ".transferFrom("]):
                if self._is_token_interface_call(node, code) and not self._is_return_value_checked(node, code):
                    line_start, line_end = self._get_line_for_node(node)
                    results.add_issue(
                        issue_type="unchecked_transfer",
                        severity="High",
                        description="ERC20 transfer call with unchecked return value. This can lead to silent failures.",
                        line_start=line_start,
                        line_end=line_end,
                        code_snippet=call_text,
                        recommendation="Check the boolean return value of transfer calls (e.g., `if !success { revert }`)."
                    )
            
            # Check for low-level calls in Rust (e.g., evm::call)
            elif ".call(" in call_text and "transfer" in call_text:
                if not self._is_call_result_checked(node, code):
                    line_start, line_end = self._get_line_for_node(node)
                    results.add_issue(
                        issue_type="unchecked_transfer",
                        severity="High",
                        description="Low-level call to transfer function without checking return value.",
                        line_start=line_start,
                        line_end=line_end,
                        code_snippet=call_text,
                        recommendation="Check the return value using `(bool success, bytes memory returnData) = ...` and verify success."
                    )
        
        # Check for match expressions that ignore errors
        elif node.type == "match_expression":
            match_text = self._get_node_text(node, code)
            if "transfer" in match_text and self._is_transfer_error_ignored(node, code):
                line_start, line_end = self._get_line_for_node(node)
                results.add_issue(
                    issue_type="unchecked_transfer",
                    severity="High",
                    description="Transfer errors are explicitly caught and ignored. This can lead to silent failures.",
                    line_start=line_start,
                    line_end=line_end,
                    code_snippet=match_text,
                    recommendation="Handle errors appropriately by propagating them or providing fallback behavior."
                )
        
        # Process all children
        for child in node.children:
            self._find_unchecked_transfers(child, code, results)
    
    def _check_solidity_unchecked_transfers(self, code: str, results) -> None:
        """Check for unchecked transfers in Solidity code within sol! macros"""
        # Look for sol! macro sections
        sol_sections = self._extract_sol_macro_sections(code)
        
        for section in sol_sections:
            section_code = section["code"]
            section_start_line = section["start_line"]
            
            # Check for unchecked transfer calls
            self._find_solidity_unchecked_transfers(section_code, section_start_line, results)
            
            # Also check specifically for predefined unsafe transfer functions
            self._find_predefined_unsafe_transfers(section_code, section_start_line, results)
    
    def _extract_sol_macro_sections(self, code: str) -> list:
        """Extract sections of code within sol! macros"""
        sections = []
        lines = code.split('\n')
        
        in_sol_macro = False
        sol_start_line = 0
        sol_code = ""
        
        for i, line in enumerate(lines):
            if "sol! {" in line:
                in_sol_macro = True
                sol_start_line = i + 1
                sol_code = ""
            elif in_sol_macro:
                sol_code += line + "\n"
                if "}" in line and (line.strip() == "}" or line.strip().endswith("}")):
                    in_sol_macro = False
                    sections.append({
                        "code": sol_code,
                        "start_line": sol_start_line
                    })
        
        return sections
    
    def _find_solidity_unchecked_transfers(self, code: str, start_line: int, results) -> None:
        """Find unchecked transfers in Solidity code"""
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            line_num = start_line + i
            
            # Check for function calls to transfer or transferFrom
            if "function " in line and "transfer" in line:
                # Find the function body bounds
                func_start = i
                func_body = ""
                brace_count = 0
                in_function = False
                function_name = None
                
                # Extract function name
                if "function " in line:
                    parts = line.split("function ")[1].split("(")[0].strip()
                    function_name = parts
                
                # Find the function body
                for j in range(func_start, len(lines)):
                    if "{" in lines[j]:
                        in_function = True
                        brace_count += lines[j].count("{")
                    
                    if in_function:
                        func_body += lines[j] + "\n"
                        
                    if "}" in lines[j]:
                        brace_count -= lines[j].count("}")
                        if brace_count == 0 and in_function:
                            break
                
                # Check for unchecked transfer calls in the function body
                if function_name and ".call(" in func_body and any(x in func_body for x in ["transfer(", "transferFrom("]):
                    # Check if the call result is properly checked
                    if (("(bool success" not in func_body and "(bool" not in func_body and "success" not in func_body) or 
                        ("require(success" not in func_body and "require" not in func_body)):
                        
                        # Find the line with the transfer call
                        transfer_line = None
                        transfer_code = None
                        for j, body_line in enumerate(func_body.split('\n')):
                            if ".call(" in body_line and any(x in body_line for x in ["transfer", "transferFrom"]):
                                transfer_line = line_num + j
                                transfer_code = body_line.strip()
                                break
                        
                        if transfer_line:
                            results.add_issue(
                                issue_type="unchecked_transfer",
                                severity="High",
                                description=f"Solidity function '{function_name}' contains unchecked transfer call. This can lead to silent failures.",
                                line_start=transfer_line,
                                line_end=transfer_line,
                                code_snippet=transfer_code,
                                recommendation="Check the return value using `(bool success, bytes memory returnData) = ...` and verify success with require."
                            )
    
    def _find_predefined_unsafe_transfers(self, code: str, start_line: int, results) -> None:
        """Find predefined unsafe transfer functions in Solidity code"""
        lines = code.split('\n')
        unsafe_functions = ["unsafeTransferERC20", "unsafeTransferFromERC20"]
        
        for i, line in enumerate(lines):
            line_num = start_line + i
            
            # Check for function declaration of known unsafe transfer functions
            for unsafe_func in unsafe_functions:
                if f"function {unsafe_func}" in line:
                    func_line = line_num
                    call_line = None
                    call_text = ""
                    
                    # Find the start of the function body
                    while i < len(lines) and "{" not in lines[i]:
                        i += 1
                    
                    if i < len(lines):
                        # Look for the .call statement in the next few lines
                        brace_count = lines[i].count("{")
                        search_limit = min(i + 15, len(lines))  # Look at most 15 lines ahead
                        
                        for j in range(i, search_limit):
                            if j < len(lines):
                                current_line = lines[j]
                                if ".call(" in current_line and "transfer" in current_line:
                                    call_line = start_line + j
                                    call_text = current_line.strip()
                                    break
                                
                                # Update brace count
                                brace_count += current_line.count("{") - current_line.count("}")
                                if brace_count == 0:
                                    break  # End of function
                    
                    if call_line:
                        results.add_issue(
                            issue_type="unchecked_transfer",
                            severity="High",
                            description=f"Solidity function '{unsafe_func}' (line {func_line}) uses unchecked transfer call. Return value is not checked.",
                            line_start=call_line,
                            line_end=call_line,
                            code_snippet=call_text,
                            recommendation="Check the return value: `(bool success, bytes memory returnData) = token.call(...); require(success, ...)`"
                        )
    
    def _is_token_interface_call(self, node: Node, code: str) -> bool:
        """Check if this is a call to an ERC20 token interface method"""
        call_text = self._get_node_text(node, code)
        erc20_methods = [".transfer(", ".transferFrom(", ".approve("]
        
        if any(method in call_text for method in erc20_methods):
            function_node = self._find_parent_function(node)
            if function_node:
                function_text = self._get_node_text(function_node, code)
                if "IERC20" in function_text:
                    return True
            if "IERC20" in code[:node.start_byte]:
                return True
        return False
    
    def _is_return_value_checked(self, node: Node, code: str) -> bool:
        """Check if the return value of a token transfer call is properly checked"""
        parent = node.parent
        
        # Handle direct statement (e.g., `let _ = token.transfer(...)`)
        if parent.type == "expression_statement":
            expr_text = self._get_node_text(parent, code)
            if "let _ =" in expr_text:
                return False
            if not expr_text.strip().startswith("let"):
                return False
        
        # Check if it's part of a let binding
        while parent and parent.type != "block":
            parent_text = self._get_node_text(parent, code)
            
            if parent.type == "let_declaration" and ".transfer" in parent_text:
                var_name = None
                for child in parent.children:
                    if child.type == "identifier":
                        var_name = self._get_node_text(child, code)
                        break
                
                if var_name and var_name != "_":
                    # Get the full function context
                    function_node = self._find_parent_function(node)
                    if function_node:
                        function_text = self._get_node_text(function_node, code)
                        
                        # Check for commented-out validation code
                        if (f"// if !{var_name}" in function_text or 
                            f"// if {var_name}" in function_text or 
                            f"// require({var_name}" in function_text):
                            
                            # This function has commented-out validation, which indicates
                            # the developer intentionally skipped validation
                            return False
                        
                        # Check for return statements that just pass the value without validation
                        lines = function_text.split('\n')
                        for line in lines:
                            if f"return {var_name}" in line and "if" not in line and "require" not in line:
                                # The variable is returned without validation
                                return False
                        
                        # Look for actual validation code
                        if (f"if !{var_name}" in function_text or 
                            f"if {var_name}" in function_text or 
                            f"require({var_name}" in function_text):
                            return True
                    
                    # Look for validation in following statements
                    sibling = parent.next_sibling 
                    while sibling:
                        sibling_text = self._get_node_text(sibling, code)
                        if var_name in sibling_text:
                            if (f"if !{var_name}" in sibling_text or 
                                f"if {var_name}" in sibling_text or 
                                f"require({var_name}" in sibling_text):
                                return True
                        sibling = sibling.next_sibling
                    
                    # If we get here, the variable exists but is not properly checked
                    return False
                elif var_name == "_":
                    return False
            
            if parent.type == "if_expression" and parent.child_by_field_name("condition") == node:
                return True
            if parent.type == "return_expression":
                # Check if this is a direct return without validation
                return_text = self._get_node_text(parent, code)
                if "if" in return_text or "require" in return_text:
                    return True
                return False
            
            parent = parent.parent
        
        return False
    
    def _is_call_result_checked(self, node: Node, code: str) -> bool:
        """Check if the result of a low-level call is checked"""
        parent = node.parent
        
        if parent.type == "expression_statement":
            return False
        
        while parent and parent.type != "function_item":
            parent_text = self._get_node_text(parent, code)
            if "(bool success," in parent_text or "bool success" in parent_text:
                function_node = self._find_parent_function(node)
                if function_node:
                    function_text = self._get_node_text(function_node, code)
                    if "require(success" in function_text or "if success" in function_text or "if !success" in function_text:
                        return True
            parent = parent.parent
        
        return False
    
    def _is_transfer_error_ignored(self, node: Node, code: str) -> bool:
        """Check if a match expression ignores transfer errors"""
        for child in node.children:
            if child.type == "match_arm" and "Err" in self._get_node_text(child, code):
                arm_text = self._get_node_text(child, code)
                if "=> {}" in arm_text.replace(" ", "") or "=>{}" in arm_text.replace(" ", ""):
                    return True
                if "return" in arm_text or "revert" in arm_text:
                    return False
        return False
    
    def _find_parent_function(self, node: Node) -> Optional[Node]:
        """Find the parent function or method definition"""
        parent = node.parent
        while parent:
            if parent.type in ["function_item", "impl_item"]:
                return parent
            parent = parent.parent
        return None
    
    def _get_function_signature(self, node: Node, code: str) -> str:
        """Get a simplified function signature for display in results"""
        function_node = self._find_parent_function(node)
        if function_node:
            for child in function_node.children:
                if child.type == "identifier":
                    return f"fn {self._get_node_text(child, code)}"
        return self._get_node_text(node, code).split("\n")[0]

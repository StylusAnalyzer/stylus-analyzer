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
        
        # Handle direct statement (e.g., `token.transfer(...)` without assignment)
        if parent.type == "expression_statement":
            expr_text = self._get_node_text(parent, code)
            if "let _ =" in expr_text:
                return False
            if not expr_text.strip().startswith("let"):
                return False
            
            # Look ahead in code to see if the result is checked
            function_node = self._find_parent_function(node)
            if function_node:
                function_text = self._get_node_text(function_node, code)
                function_lines = function_text.splitlines()
                
                # Find the line containing our call
                call_text = self._get_node_text(node, code)
                call_line_idx = -1
                for i, line in enumerate(function_lines):
                    if call_text in line:
                        call_line_idx = i
                        break
                
                if call_line_idx >= 0 and call_line_idx < len(function_lines) - 1:
                    # Look at the next few lines for an if statement checking the result
                    for i in range(call_line_idx + 1, min(call_line_idx + 5, len(function_lines))):
                        if "if" in function_lines[i] and any(x in function_lines[i] for x in ["success", "result", "!"]):
                            return True
        
        # Handle assignment (let success = token.transfer(...))
        elif parent.type == "assignment_expression" or parent.type == "let_declaration":
            let_text = self._get_node_text(parent, code)
            variable_name = let_text.split("=")[0].strip().replace("let", "").strip()
            
            if variable_name == "_":
                return False
            
            # Look ahead for if statement checking the variable
            function_node = self._find_parent_function(node)
            if function_node:
                function_text = self._get_node_text(function_node, code)
                function_lines = function_text.splitlines()
                
                # Find the line containing our assignment
                let_line_idx = -1
                for i, line in enumerate(function_lines):
                    if let_text in line:
                        let_line_idx = i
                        break
                
                if let_line_idx >= 0 and let_line_idx < len(function_lines) - 1:
                    # Look for an if statement checking the variable
                    for i in range(let_line_idx + 1, min(let_line_idx + 10, len(function_lines))):
                        if f"if {variable_name}" in function_lines[i] or f"if !{variable_name}" in function_lines[i]:
                            return True
        
        # Handle question mark operator (e.g., token.transfer(...)?)
        elif parent.type == "try_expression":
            # The ? operator only handles errors, not the boolean success value
            # We need to check if the return value of this expression is used in a condition
            grand_parent = parent.parent
            
            # Check if the try expression is part of an assignment or variable declaration
            if grand_parent.type == "let_declaration" or grand_parent.type == "assignment_expression":
                let_text = self._get_node_text(grand_parent, code)
                variable_name = let_text.split("=")[0].strip().replace("let", "").strip()
                
                if variable_name == "_":
                    return False
                
                # Look for checks using this variable
                function_node = self._find_parent_function(node)
                if function_node:
                    function_text = self._get_node_text(function_node, code)
                    if f"if {variable_name}" in function_text or f"if !{variable_name}" in function_text:
                        return True
                
                return False
            
            # If the try expression isn't assigned to a variable, it's likely unchecked
            # This is for cases like: `token.transfer(self, to, amount)?;`
            return False
        
        # Check for conditional or match
        elif parent.type == "if_expression" or parent.type == "match_expression":
            return True
        
        return False
        
    def _is_call_result_checked(self, node: Node, code: str) -> bool:
        """Check if a function call result is checked"""
        parent = node.parent
        
        # If it's directly in a let binding or assignment
        if parent.type == "let_declaration" or parent.type == "assignment_expression":
            # Check if the variable is used in a condition later
            return self._is_return_value_checked(node, code)
        
        # If it's already in a condition
        elif parent.type == "if_expression" or parent.type == "match_expression":
            return True
        
        # Check for ? operator
        elif parent.type == "try_expression":
            # For low-level calls, the ? only propagates errors but doesn't check success
            return False
        
        return False
    
    def _is_transfer_error_ignored(self, node: Node, code: str) -> bool:
        """Check if transfer errors are explicitly caught and ignored"""
        match_text = self._get_node_text(node, code)
        return "transfer" in match_text and (
            ("Err(_) => {}" in match_text) or 
            ("Err(_) => ()" in match_text) or
            ("Err(_) => Ok(())" in match_text)
        )
    
    def _find_parent_function(self, node: Node) -> Optional[Node]:
        """Find the parent function node"""
        current = node
        while current.parent and current.type != "function_item":
            current = current.parent
        return current if current.type == "function_item" else None
    
    def _get_function_signature(self, node: Node, code: str) -> str:
        """Get the function signature from a function node"""
        if node.type != "function_item":
            return ""
        
        signature = ""
        for child in node.children:
            if child.type == "block":
                break
            signature += self._get_node_text(child, code)
        
        return signature.strip()
    
    def _get_line_for_node(self, node: Node) -> tuple:
        """Get the line number for a node (1-indexed)"""
        return node.start_point[0] + 1, node.end_point[0] + 1
    
    def _get_node_text(self, node: Node, code: str) -> str:
        """Get the text of a node from the code"""
        if node.start_byte < 0 or node.end_byte > len(code) or node.start_byte >= node.end_byte:
            return ""
        return code[node.start_byte:node.end_byte]

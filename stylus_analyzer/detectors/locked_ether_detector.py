"""
Detector for locked Ether vulnerabilities in Stylus Rust contracts
"""
from tree_sitter import Node, Tree
from typing import Set, List, Optional

from stylus_analyzer.detectors.detector_base import BaseDetector


class LockedEtherDetector(BaseDetector):
    """
    Detector for locked Ether vulnerabilities in Stylus contracts.
    
    Flags contracts that can receive Ether but lack withdrawal methods,
    potentially causing funds to become permanently inaccessible.
    """
    
    def __init__(self):
        super().__init__(
            name="locked_ether",
            description="Detects contracts that can receive Ether but lack withdrawal methods"
        )
        
    def detect(self, tree: Tree, code: str, results) -> None:
        """Detect locked Ether vulnerabilities in the contract"""
        self.can_receive_ether = False
        self.has_withdrawal_method = False
        self.payable_functions = []
        self.withdrawal_functions = []
        
        # First pass: find functions that can receive Ether
        self._find_ether_receiving_functions(tree.root_node, code)
        
        # Second pass: find functions that can withdraw Ether
        self._find_ether_withdrawal_functions(tree.root_node, code)
        
        # Report if contract can receive but not withdraw Ether
        if self.can_receive_ether and not self.has_withdrawal_method:
            self._report_locked_ether_vulnerability(code, results)
    
    def _find_ether_receiving_functions(self, node: Node, code: str) -> None:
        """Find functions that can receive Ether"""
        if node.type == "function_item":
            function_text = self._get_node_text(node, code)
            function_name = self._get_function_name(node, code)
            # Check for payable indicators in Stylus contracts
            if self._is_payable_function(node, code, function_text):
                line_start, line_end = self._get_line_for_node(node)
                self.can_receive_ether = True
                self.payable_functions.append({
                    'name': function_name,
                    'line_start': line_start,
                    'line_end': line_end,
                    'text': function_text[:100] + "..." if len(function_text) > 100 else function_text
                })
        
        # Check for fallback/receive functions (constructor with payable)
        elif node.type == "impl_item":
            impl_text = self._get_node_text(node, code)
            if "payable" in impl_text or "msg_value" in impl_text:
                # Check if this impl block has functions that receive Ether
                for child in node.children:
                    if child.type == "function_item":
                        self._find_ether_receiving_functions(child, code)
        
        # Recursively check children
        for child in node.children:
            self._find_ether_receiving_functions(child, code)
    
    def _find_ether_withdrawal_functions(self, node: Node, code: str) -> None:
        """Find functions that can withdraw Ether"""
        if node.type == "function_item":
            function_text = self._get_node_text(node, code)
            function_name = self._get_function_name(node, code)
            
            # Check for withdrawal patterns
            if self._is_withdrawal_function(node, code, function_text):
                line_start, line_end = self._get_line_for_node(node)
                self.has_withdrawal_method = True
                self.withdrawal_functions.append({
                    'name': function_name,
                    'line_start': line_start,
                    'line_end': line_end
                })
        
        # Recursively check children
        for child in node.children:
            self._find_ether_withdrawal_functions(child, code)
    
    def _is_payable_function(self, node: Node, code: str, function_text: str) -> bool:
        """Check if a function can receive Ether"""
        function_name = self._get_function_name(node, code)
        
        # Check for explicit payable attributes
        if "#[payable]" in function_text:
            return True
        
        # Check for evm::msg_value() usage (indicates function expects Ether)
        if "evm::msg_value()" in function_text or "msg_value()" in function_text:
            return True
            
        # Check for receive/fallback function patterns
        if function_name in ["receive", "fallback", "default"]:
            return True
        
        # Check for value parameter in function signature
        if "value:" in function_text and ("U256" in function_text or "u256" in function_text):
            return True
            
        # Check for sol! macro with payable functions
        if "sol! {" in code:
            sol_sections = self._extract_sol_macro_sections(code)
            for section in sol_sections:
                if "payable" in section["code"] and function_name in section["code"]:
                    return True
        
        return False
    
    def _is_withdrawal_function(self, node: Node, code: str, function_text: str) -> bool:
        """
        Check if a function can actually withdraw Ether from the contract.
        This function must actually transfer Ether OUT of the contract, not just manage internal state.
        """
        function_name = self._get_function_name(node, code)
        
        # Remove comments and whitespace to get actual executable code
        # This prevents commented-out transfer code from being detected
        lines = function_text.split('\n')
        active_code_lines = []
        for line in lines:
            # Remove single-line comments
            if '//' in line:
                line = line[:line.index('//')]
            line = line.strip()
            if line:  # Only keep non-empty lines
                active_code_lines.append(line)
        
        active_code = ' '.join(active_code_lines)
        
        # Primary withdrawal indicators - these MUST be in active (non-commented) code
        actual_transfer_patterns = [
            # Stylus/Rust specific transfer methods
            "evm::call(",
            "evm::transfer_eth(",
            "transfer_eth(",
            ".call(",
            "send_value(",
            
            # Low-level calls with value
            "call{value:",
            "call(value:",
            
            # Self-destruct (selfdestruct in Solidity equivalent)
            "selfdestruct(",
            "suicide(",
            
            # External contract calls with value
            "external_call(",
            "call_contract(",
            
            # More specific patterns for actual transfers
            ".transfer(",
            ".send(",
            "payable(",
        ]
        
                 # Only count as withdrawal if there's actual transfer code (not commented out)
        for pattern in actual_transfer_patterns:
            if pattern in active_code:
                # If we find a transfer pattern, this is a withdrawal function
                # Even if it reads balance first, that's normal for withdrawal functions
                return True
        
        # Check for Solidity withdrawal patterns in sol! macros (must be active code)
        if "sol! {" in code:
            sol_sections = self._extract_sol_macro_sections(code)
            for section in sol_sections:
                section_code = section["code"]
                # Remove comments from Solidity code too
                sol_lines = section_code.split('\n')
                active_sol_lines = []
                for line in sol_lines:
                    if '//' in line:
                        line = line[:line.index('//')]
                    if '/*' in line and '*/' in line:
                        # Handle single-line block comments
                        start = line.index('/*')
                        end = line.index('*/') + 2
                        line = line[:start] + line[end:]
                    line = line.strip()
                    if line:
                        active_sol_lines.append(line)
                
                active_sol_code = ' '.join(active_sol_lines)
                
                if function_name in section_code:
                    solidity_transfer_patterns = [".transfer(", ".send(", ".call{value:", "selfdestruct("]
                    if any(pattern in active_sol_code for pattern in solidity_transfer_patterns):
                        return True
        
        return False
    
    def _extract_sol_macro_sections(self, code: str) -> List[dict]:
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
    
    def _report_locked_ether_vulnerability(self, code: str, results) -> None:
        """Report the locked Ether vulnerability"""
        payable_details = ""
        if self.payable_functions:
            payable_names = [f"'{func['name']}' (line {func['line_start']})" for func in self.payable_functions]
            payable_details = f"Payable functions found: {', '.join(payable_names)}. "
        
        # Find a representative line to report (use first payable function if available)
        if self.payable_functions:
            line_start = self.payable_functions[0]['line_start']
            line_end = self.payable_functions[0]['line_end']
            code_snippet = self.payable_functions[0]['text']
        else:
            # Fallback to start of file if no specific payable function found
            line_start = 1
            line_end = 1
            code_snippet = "Contract can receive Ether but lacks withdrawal methods"
        
        results.add_issue(
            issue_type="locked_ether",
            severity="Medium",
            description=f"Contract can receive Ether but lacks withdrawal methods. {payable_details}This may cause funds to become permanently locked.",
            line_start=line_start,
            line_end=line_end,
            code_snippet=code_snippet,
            recommendation="Add withdrawal functions, access controls for fund management, or remove the ability to receive Ether if not needed. Consider implementing functions like 'withdraw()', 'emergency_withdraw()', or 'transfer_funds()'."
        )
    
    def _get_function_name(self, node: Node, code: str) -> str:
        """Extract the function name from a function node"""
        if not node or node.type != "function_item":
            return "unknown"
            
        # Look for the identifier node which contains the function name
        for child in node.children:
            if child.type == "identifier":
                return self._get_node_text(child, code)
        
        return "unknown"
    
    def _find_parent_function(self, node: Node) -> Optional[Node]:
        """Find the parent function containing this node"""
        parent = node.parent
        while parent:
            if parent.type in ["function_item", "impl_item", "method_item"]:
                return parent
            parent = parent.parent
        return None 

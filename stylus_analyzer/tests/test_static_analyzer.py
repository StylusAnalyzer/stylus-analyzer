"""
Tests for the static analyzer
"""
import os
import unittest
from pathlib import Path

from stylus_analyzer.static_analyzer import StaticAnalyzer


class TestStaticAnalyzer(unittest.TestCase):
    """Test cases for the static analyzer"""
    
    def setUp(self):
        """Set up the test environment"""
        self.analyzer = StaticAnalyzer()
        self.test_dir = Path(__file__).parent.parent.parent / "test_contracts"
        
    def test_transfer_detection(self):
        """Test that the analyzer can detect transfer-related issues"""
        contract_path = self.test_dir / "unsafe_transfer_example.rs"
        
        with open(contract_path, 'r') as f:
            code = f.read()
        
        results = self.analyzer.analyze(code)
        
        # Check that we have issues
        self.assertTrue(results.has_issues(), "Should have detected issues in the contract")
        
        # Check for specific issues
        issue_types = [issue["type"] for issue in results.issues]
        print(f'issue_types => {issue_types}')
        
        # There should be unchecked transfer issues
        self.assertIn("unchecked_transfer", issue_types, "Should detect unchecked transfer issues")
        
    def test_safe_code(self):
        """Test that analyzer doesn't flag issues in safe code"""
        # Create a simple safe contract
        safe_code = """
        #![cfg_attr(not(feature = "export-abi"), no_main)]
        
        extern crate alloc;
        
        use stylus_sdk::{
            alloy_primitives::{Address, U256},
            evm, msg,
            prelude::*,
        };
        
        // Safe transfer function
        fn safe_transfer(to: Address, amount: U256) -> bool {
            // Check for zero address
            if to == Address::ZERO {
                return false;
            }
            
            // Perform transfer with return value check
            let success = do_transfer(to, amount);
            if !success {
                return false;
            }
            
            return true;
        }
        
        fn do_transfer(to: Address, amount: U256) -> bool {
            // Implementation details omitted
            return true;
        }
        
        #[no_mangle]
        extern "C" fn main() {
            // Empty main
        }
        """
        
        results = self.analyzer.analyze(safe_code)
        
        # There should be no issues
        self.assertFalse(results.has_issues(), "Should not detect issues in safe code")
        

if __name__ == "__main__":
    unittest.main() 

"""
Tests for the AI analyzer module
"""
import os
import unittest
from unittest import mock

from stylus_analyzer.ai_analyzer import AIAnalyzer


class TestAIAnalyzer(unittest.TestCase):
    """Test cases for AIAnalyzer class"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock environment variable for testing
        self.env_patcher = mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
        self.env_patcher.start()
        
        # Mock the OpenAI client
        self.client_patcher = mock.patch('stylus_analyzer.ai_analyzer.client')
        self.mock_client = self.client_patcher.start()
        
        # Create analyzer instance
        self.analyzer = AIAnalyzer(model="test-model")
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
        self.client_patcher.stop()
    
    def test_prepare_prompt(self):
        """Test prompt preparation"""
        # Test with contract only
        contract_content = "fn main() {}"
        prompt = self.analyzer._prepare_prompt(contract_content)
        
        self.assertIn("analyze this Rust contract", prompt)
        self.assertIn("```rust\nfn main() {}\n```", prompt)
        
        # Test with contract and README
        readme_content = "This is a test contract"
        prompt_with_readme = self.analyzer._prepare_prompt(contract_content, readme_content)
        
        self.assertIn("analyze this Rust contract", prompt_with_readme)
        self.assertIn("```rust\nfn main() {}\n```", prompt_with_readme)
        self.assertIn("additional context from the README", prompt_with_readme)
        self.assertIn("```\nThis is a test contract\n```", prompt_with_readme)
    
    def test_analyze_contract(self):
        """Test contract analysis with mocked OpenAI API"""
        # Mock OpenAI API response
        mock_response = mock.MagicMock()
        mock_response.choices = [
            mock.MagicMock(
                message=mock.MagicMock(content="Analysis result")
            )
        ]
        self.mock_client.chat.completions.create.return_value = mock_response
        
        # Test analysis
        contract_content = "fn main() {}"
        result = self.analyzer.analyze_contract(contract_content)
        
        # Verify OpenAI API was called correctly
        self.mock_client.chat.completions.create.assert_called_once()
        call_args = self.mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_args["model"], "test-model")
        self.assertEqual(len(call_args["messages"]), 2)
        
        # Verify result format
        self.assertTrue(result["success"])
        self.assertEqual(result["raw_analysis"], "Analysis result")
        
    def test_error_handling(self):
        """Test error handling during analysis"""
        # Mock OpenAI API error
        self.mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        # Test analysis with error
        contract_content = "fn main() {}"
        result = self.analyzer.analyze_contract(contract_content)
        
        # Verify error handling
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "API Error")
        self.assertEqual(result["vulnerabilities"], [])
        self.assertEqual(result["suggestions"], [])


if __name__ == "__main__":
    unittest.main() 

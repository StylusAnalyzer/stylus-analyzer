"""
AI-powered analysis of Stylus/Rust contracts
"""
import os
import logging
from typing import Dict, List, Optional, Any
from openai import OpenAI
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AIAnalyzer:
    """
    Class to analyze Rust contracts using OpenAI's GPT models
    """
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize the AI analyzer
        
        Args:
            model: The OpenAI model to use, defaults to gpt-4o-mini
        """
        self.model = model
        self._client = None
        self._ensure_client()
        
    def _ensure_client(self):
        """
        Lazily load .env and initialize OpenAI client only when needed.
        """
        if self._client is not None:
            return
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment variables. Please set it in your .env file or environment.")
            raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in your .env file or environment.")
        self._client = OpenAI(api_key=api_key)

    def analyze_contract(self, contract_content: str, readme_content: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a Rust contract for potential vulnerabilities using GPT
        
        Args:
            contract_content: The content of the Rust contract
            readme_content: Optional README content for additional context
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            self._ensure_client()
            # Prepare prompt for the AI
            prompt = self._prepare_prompt(contract_content, readme_content)
            
            # Call the OpenAI API
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a security expert specialized in analyzing Rust contracts for the Stylus framework. Identify potential bugs, vulnerabilities, and code quality issues."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.2,
            )
            
            # Process the response
            analysis_result = self._process_response(response)
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error during AI analysis: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "vulnerabilities": [],
                "suggestions": []
            }
    
    def _prepare_prompt(self, contract_content: str, readme_content: Optional[str] = None) -> str:
        """
        Prepare the prompt for the AI model
        
        Args:
            contract_content: The Rust contract code
            readme_content: Optional README content for context
            
        Returns:
            Formatted prompt string
        """
        prompt = "Please analyze this Rust contract for Stylus framework and identify potential security vulnerabilities, bugs, and code quality issues:\n\n"
        prompt += f"```rust\n{contract_content}\n```\n\n"
        
        if readme_content:
            prompt += "Here is additional context from the README:\n\n"
            prompt += f"```\n{readme_content}\n```\n\n"
        
        prompt += "Please structure your analysis as follows:\n"
        prompt += "1. List all potential vulnerabilities with severity (Critical, High, Medium, Low)\n"
        prompt += "2. Describe each issue with the relevant code section\n"
        prompt += "3. Provide recommendations to fix each issue\n"
        prompt += "4. Suggest general code improvements\n"
        
        return prompt
    
    def _process_response(self, response: Any) -> Dict[str, Any]:
        """
        Process the AI response into a structured format
        
        Args:
            response: The response from the OpenAI API
            
        Returns:
            Dictionary with structured analysis results
        """
        # Extract the text from the API response
        if hasattr(response, 'choices') and len(response.choices) > 0:
            analysis_text = response.choices[0].message.content
        else:
            return {"success": False, "error": "Invalid API response", "vulnerabilities": [], "suggestions": []}
        
        # For the MVP, we'll just return the raw text
        # In a more advanced version, we would parse this into structured data
        return {
            "success": True,
            "raw_analysis": analysis_text,
            "vulnerabilities": [],  # To be parsed in future versions
            "suggestions": []  # To be parsed in future versions
        } 

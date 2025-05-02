"""
Static analyzer for Stylus Rust contracts
"""
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
import time
import subprocess
import os


from stylus_analyzer.file_utils import generate_rust_ast, read_file_content
from stylus_analyzer.detectors import AVAILABLE_DETECTORS

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StaticAnalysisResult:
    """Class to represent static analysis results"""

    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, str]] = []
        self.analysis_time: float = 0

    def add_issue(self,
                  issue_type: str,
                  severity: str,
                  description: str,
                  line_start: int,
                  line_end: int,
                  code_snippet: str,
                  recommendation: str):
        """Add an issue to the results"""
        self.issues.append({
            "type": issue_type,
            "severity": severity,
            "description": description,
            "line_start": line_start,
            "line_end": line_end,
            "code_snippet": code_snippet,
            "recommendation": recommendation
        })

    def add_error(self, detector_name: str, error_message: str):
        """Add an error that occurred during analysis"""
        self.errors.append({
            "detector": detector_name,
            "message": error_message
        })

    def has_issues(self) -> bool:
        """Check if there are any issues"""
        return len(self.issues) > 0

    def has_errors(self) -> bool:
        """Check if there were any errors during analysis"""
        return len(self.errors) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "issues": self.issues,
            "total_issues": len(self.issues),
            "errors": self.errors,
            "analysis_time_seconds": self.analysis_time
        }


class StaticAnalyzer:
    """Main static analyzer that manages detectors and runs analysis"""

    def __init__(self):
        self.detectors = []

        # Register built-in detectors
        self._register_default_detectors()

    def _preprocess_with_cargo_expand(self, file_path: str) -> Optional[str]:
        """Preprocess the Rust code with cargo expand to handle macros"""
        try:
            result = subprocess.run(
                ['cargo', 'expand', '--file', file_path],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(
                f"Failed to expand macros: {e}. Falling back to original code.")
            return read_file_content(file_path)

    def _register_default_detectors(self):
        """Register the default set of detectors"""
        for detector_class in AVAILABLE_DETECTORS:
            self.detectors.append(detector_class())

    def register_detector(self, detector):
        """Register a new detector"""
        self.detectors.append(detector)

    def analyze(self, code: str, file_path: Optional[str] = None) -> StaticAnalysisResult:
        """
        Analyze the given Rust code

        Args:
            code: The source code to analyze

        Returns:
            StaticAnalysisResult with the analysis findings
        """
        start_time = time.time()
        results = StaticAnalysisResult()

        # Preprocess code with cargo expand if file_path is provided
        if file_path:
            expanded_code = self._preprocess_with_cargo_expand(file_path)
            if expanded_code:
                code = expanded_code
            else:
                results.add_error(
                    "preprocessor", "Failed to preprocess code with cargo expand")

        # Generate AST - only do this once and reuse for all detectors
        tree = generate_rust_ast(code)
        if not tree:
            logger.error("Failed to generate AST")
            results.add_error(
                "parser", "Failed to generate AST for the provided code")
            results.analysis_time = time.time() - start_time
            return results

        # Run all detectors
        for detector in self.detectors:
            try:
                detector.detect(tree, code, results)
            except Exception as e:
                error_msg = f"Error in detector {detector.name}: {str(e)}"
                logger.error(error_msg)
                results.add_error(detector.name, str(e))

        # Record analysis time
        results.analysis_time = time.time() - start_time

        # Check for reentrancy feature
        if self.check_reentrancy_feature(os.path.dirname(file_path)):
            results.add_issue(
                "reentrancy_feature",
                "Warning",
                "Reentrancy feature is disabled for stylus-sdk.",
                0,
                0,
                "",
                "Consider removing the reentrant feature with caution."
            )
        return results

    def check_reentrancy_feature(self, directory: str) -> bool:
        """Check if the stylus-sdk dependency with reentrant feature is present in Cargo.toml."""
        cargo_toml_path = os.path.join(directory, 'Cargo.toml')
        
        if not os.path.exists(cargo_toml_path):
            return False  # No Cargo.toml found
        
        with open(cargo_toml_path, 'r') as file:
            for line in file:
                if 'stylus-sdk' in line and 'features' in line:
                    if 'reentrant' in line:
                        return True  # Found stylus-sdk with reentrant feature
        return False  # Not found

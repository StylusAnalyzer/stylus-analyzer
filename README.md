# Stylus Analyzer

A tool for analyzing Stylus/Rust smart contracts for security issues and bugs.

## Features

- AI-powered contract analysis using OpenAI models
- Static analysis to detect common vulnerabilities
  - Unchecked transfer vulnerabilities
  - Unsafe panic!() and unwrap() calls
  - Unsafe ABI encoding operations
  - Extensible detector system for easily adding new vulnerability checks

## Installation

You can install Stylus Analyzer using pip:

```bash
pip install stylus-analyzer
```

For development or the latest features, you can install from the source:

```bash
# Clone the repository
git clone https://github.com/StylusAnalyzer/stylus-analyzer.git
cd stylus-analyzer

# Install the package in development mode
pip install -e .
```

## Usage

### Static Analysis

To perform static analysis on Rust contracts to detect common issues:

```bash
# Analyze a single file
stylus-analyzer static-analyze test_contracts/unsafe_transfer_example.rs

# Analyze all contracts in a directory
stylus-analyzer static-analyze test_contracts/

# Save results to a JSON file
stylus-analyzer static-analyze test_contracts/ -o analysis_results.json

# Save results to a PDF report
stylus-analyzer static-analyze test_contracts/ -p analysis_report.pdf

# Save results in both JSON and PDF formats
stylus-analyzer static-analyze test_contracts/ -o analysis_results.json -p analysis_report.pdf

# Show detailed output including code snippets
stylus-analyzer static-analyze test_contracts/ --verbose
```

The static analyzer will check for various issues including:
- Unchecked transfer return values that can lead to silent failures
- Unsafe panic!() macro calls that cause immediate termination
- Unsafe unwrap() calls that may cause panics
- Unsafe encode_packed operations with dynamic types that may cause hash collisions
- More detectors can be added by extending the framework

### AI Analysis

To perform AI-powered analysis (requires OpenAI API key):

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key

# Analyze a single file
stylus-analyzer analyze-file test_contracts/test_token.rs

# Analyze all contracts in a project directory
stylus-analyzer analyze path/to/project

# Save results to a file
stylus-analyzer analyze path/to/project -o analysis_results.json
```

## Custom Detectors

You can create custom detectors for the static analyzer by following these steps:

1. Create a new detector file in `stylus_analyzer/detectors/`
2. Extend the `BaseDetector` class
3. Implement the required methods
4. Register your detector in the system

Example detector:

```python
from tree_sitter import Node, Tree
from stylus_analyzer.detectors.detector_base import BaseDetector

class MyCustomDetector(BaseDetector):
    def __init__(self):
        super().__init__(
            name="my_custom_detector",
            description="Description of what this detector looks for"
        )
    
    def detect(self, tree: Tree, code: str, results) -> None:
        # Implement your detection logic here
        pass
```

You can register your detector in two ways:

1. Add it to the `AVAILABLE_DETECTORS` list in `stylus_analyzer/detectors/__init__.py`:

```python
from stylus_analyzer.detectors.my_custom_detector import MyCustomDetector

AVAILABLE_DETECTORS = [
    # Other detectors...
    MyCustomDetector
]
```

2. Or register it programmatically:

```python
from stylus_analyzer.detectors import register_detector
from my_package.my_detector import MyCustomDetector

register_detector(MyCustomDetector)
```

## Performance Optimizations

The analyzer includes several performance optimizations:

1. AST generation is done once per file and reused across all detectors
2. Parser initialization uses a singleton pattern to avoid redundant setup
3. Analysis timing is tracked and reported for benchmarking
4. Error handling tracks and reports issues without crashing

## Contributing

Contributions to Stylus Analyzer are welcome! Here's how you can contribute:

### Adding New Vulnerability Detectors

1. Fork the repository
2. Create a new detector file in the `stylus_analyzer/detectors/` directory
3. Implement your detector by extending the `BaseDetector` class
4. Add tests for your detector in the `stylus_analyzer/tests/` directory
5. Submit a pull request with a description of the vulnerability your detector identifies

### Coding Standards

- Use type hints for all function parameters and return values
- Add docstrings for all classes and functions
- Follow PEP 8 style guidelines
- Write unit tests for new functionality

### Development Setup

```bash
# Clone your fork
git clone https://github.com/StylusAnalyzer/stylus-analyzer.git
cd stylus-analyzer

# Create and activate a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Run tests
pytest
```

## License

This project is licensed under the terms of the MIT license. 

## Detectors

### Unchecked Transfer
Detects unchecked transfer calls where the return value is not properly checked. This can lead to silent failures where token transfers fail but the contract continues execution as if they succeeded.

### Unsafe Unwrap
Detects uses of `.unwrap()` in Rust code, which can cause runtime panics if the value is None or Err. In a blockchain context, panics can cause transactions to fail and may lead to loss of funds or unexpected behavior. Instead, developers should use pattern matching, the `?` operator, or other explicit error handling techniques.

### Unsafe Panic
Detects uses of `panic!()` macro in Rust code, which causes immediate termination that cannot be caught or recovered from. In a blockchain context, this will cause the entire transaction to fail with no way to handle the error gracefully. Developers should use Result/Option types with explicit error handling instead.

### Unsafe Encode Packed
Detects potentially unsafe uses of `encode_packed` with dynamic types like strings. When used with dynamic types without delimiters, different inputs can produce the same packed result (e.g., `encode_packed("a", "bc") == encode_packed("ab", "c")`), which can lead to hash collisions. This is particularly problematic when the packed result is used for signatures, authentication, or as a unique identifier. Developers should use regular `encode` which adds padding, use fixed-size types with `encode_packed`, or add delimiters between dynamic values.

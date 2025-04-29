# Stylus Analyzer

An AI-powered bug detection tool for Stylus/Rust contracts, similar to Slither for Solidity.

## Features

- AI-powered analysis of Stylus/Rust contracts using GPT-4o Mini
- Detect potential vulnerabilities and bugs in your contracts
- Support for analyzing entire projects or individual files
- Consider contextual information from README files (optional)
- Save analysis results to files for later review

## Installation

```bash
pip install stylus-analyzer
```

That's it! The package will be installed with all its dependencies.

## Configuration

1. Create a `.env` file in your project directory:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

### Analyze a Project

To analyze all Rust contracts in a Stylus project:

```bash
stylus-analyzer analyze /path/to/your/project
```

### Analyze a Single File

To analyze a specific Rust contract file:

```bash
stylus-analyzer analyze-file /path/to/your/contract.rs
```

### Optional Arguments

- `--output` or `-o`: Save analysis results to a file
- `--model` or `-m`: Specify the OpenAI model to use (default: gpt-4o-mini)
- `--verbose` or `-v`: Enable verbose output
- `--readme` or `-r`: Specify a README file for additional context (for analyze-file command)

### Examples

```bash
# Analyze current directory project and save results
stylus-analyzer analyze . --output analysis_results.json

# Analyze a specific file with verbose output
stylus-analyzer analyze-file contracts/MyContract.rs --verbose

# Analyze a specific file with README context
stylus-analyzer analyze-file contracts/MyContract.rs --readme README.md
```

## Development

If you want to contribute or modify the code, you can clone the repository:

```bash
git clone https://github.com/Jay-Sojitra/stylus-analyzer.git
cd stylus-analyzer
pip install -e .
```

## Future Extensions

This tool is designed to be extended with additional features in the future:

- Static analysis capabilities
- Custom rule definitions
- Integration with development workflows
- Support for other smart contract languages

## License

MIT 

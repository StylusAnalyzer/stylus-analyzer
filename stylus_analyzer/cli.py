"""
Command-line interface for the Stylus Analyzer
"""
import os
import sys
import json
import click
import logging
from typing import Optional

from stylus_analyzer.ai_analyzer import AIAnalyzer
from stylus_analyzer.file_utils import collect_project_files, read_file_content, generate_rust_ast, print_rust_ast, find_rust_contracts

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Stylus Analyzer - AI-powered bug detection tool for Stylus/Rust contracts"""
    pass


@cli.command()
@click.argument('project_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True), default='.')
@click.option('--output', '-o', type=click.Path(), help='Output file to save the analysis results')
@click.option('--model', '-m', type=str, default='gpt-4o-mini', help='OpenAI model to use for analysis')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def analyze(project_dir: str, output: Optional[str], model: str, verbose: bool):
    """
    Analyze Rust contracts in the specified Stylus project directory
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"Analyzing Stylus project in: {project_dir}")

    # Collect project files
    project_files = collect_project_files(project_dir)

    if not project_files["contracts"]:
        logger.error("No Rust contract files found in the project directory")
        sys.exit(1)

    # Initialize AI analyzer
    analyzer = AIAnalyzer(model=model)

    # Process each contract
    results = {}
    for file_path, content in project_files["contracts"].items():
        relative_path = os.path.relpath(file_path, project_dir)
        logger.info(f"Analyzing contract: {relative_path}")

        # Analyze contract
        analysis_result = analyzer.analyze_contract(
            content, project_files["readme"])

        # Store results
        results[relative_path] = analysis_result

        # Display results for this contract
        if verbose or not output:
            click.echo(f"\n===== Analysis for {relative_path} =====")
            if analysis_result["success"]:
                click.echo(analysis_result["raw_analysis"])
            else:
                click.echo(
                    f"Error: {analysis_result.get('error', 'Unknown error')}")

    # Save results to output file if specified
    if output:
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Analysis results saved to: {output}")


@cli.command()
@click.argument('file_path', type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.option('--readme', '-r', type=click.Path(exists=True), help='Path to README file for additional context')
@click.option('--output', '-o', type=click.Path(), help='Output file to save the analysis results')
@click.option('--model', '-m', type=str, default='gpt-4o-mini', help='OpenAI model to use for analysis')
def analyze_file(file_path: str, readme: Optional[str], output: Optional[str], model: str):
    """
    Analyze a single Rust contract file
    """
    logger.info(f"Analyzing file: {file_path}")

    # Read file content
    contract_content = read_file_content(file_path)
    if not contract_content:
        logger.error(f"Could not read file: {file_path}")
        sys.exit(1)

    # Read README if provided
    readme_content = None
    if readme:
        readme_content = read_file_content(readme)
        if not readme_content:
            logger.warning(f"Could not read README file: {readme}")

    # Initialize AI analyzer
    analyzer = AIAnalyzer(model=model)

    # Analyze contract
    analysis_result = analyzer.analyze_contract(
        contract_content, readme_content)

    # Display results
    if analysis_result["success"]:
        click.echo(analysis_result["raw_analysis"])
    else:
        click.echo(f"Error: {analysis_result.get('error', 'Unknown error')}")

    # Save results to output file if specified
    if output:
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, indent=2)
        logger.info(f"Analysis results saved to: {output}")


@cli.command()
def version():
    """Display the version of Stylus Analyzer"""
    from stylus_analyzer import __version__
    click.echo(f"Stylus Analyzer v{__version__}")


@cli.command()
@click.argument('target', type=click.Path(exists=True))
@click.option('--max-depth', type=int, default=10, help='Maximum depth to print for AST nodes')
def print_ast(target: str, max_depth: int):
    """
    Generate and print the AST for a Rust contract file or all contracts in a directory.
    """
    if os.path.isdir(target):
        contract_files = find_rust_contracts(target)
        if not contract_files:
            click.echo("No Rust contract files found in the directory.")
            return
        for file_path in contract_files:
            click.echo(f"\n===== AST for {file_path} =====")
            code = read_file_content(file_path)
            if code:
                tree = generate_rust_ast(code)
                print_rust_ast(tree, code, max_depth=max_depth)
            else:
                click.echo(f"Could not read file: {file_path}")
    else:
        code = read_file_content(target)
        if not code:
            click.echo(f"Could not read file: {target}")
            return
        tree = generate_rust_ast(code)
        click.echo(f"===== AST for {target} =====")
        print_rust_ast(tree, code, max_depth=max_depth)


def main():
    """Main entry point for the CLI"""
    try:
        cli()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Command-line interface for the Stylus Analyzer
"""
import os
import sys
import json
import click
import logging
from typing import Optional, Dict, Any
import time
import subprocess

from stylus_analyzer.ai_analyzer import AIAnalyzer
from stylus_analyzer.static_analyzer import StaticAnalyzer
from stylus_analyzer.file_utils import collect_project_files, read_file_content, find_rust_contracts
from stylus_analyzer.output_utils import format_analysis_results, generate_pdf_report

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Stylus Analyzer - Bug detection tool for Stylus/Rust contracts"""
    pass


def preprocess_with_cargo_expand(file_path: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ['cargo', 'expand', '--file', file_path],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to expand macros: {e}")
        return read_file_content(file_path)


@cli.command()
@click.argument('project_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True), default='.')
@click.option('--output', '-o', type=click.Path(), help='Output file to save the analysis results as JSON')
@click.option('--model', '-m', type=str, default='gpt-4o-mini', help='OpenAI model to use for analysis')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def analyze(project_dir: str, output: Optional[str], model: str, verbose: bool):
    """
    Analyze Rust contracts in the specified Stylus project directory using AI
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
            click.echo(f"\n===== AI Analysis for {relative_path} =====")
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
    Analyze a single Rust contract file using AI
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
@click.option('--output', '-o', type=click.Path(), help='Output file to save the analysis results as JSON')
@click.option('--pdf', '-p', type=click.Path(), help='Output file to save the analysis results as PDF')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def static_analyze(target: str, output: Optional[str], pdf: Optional[str], verbose: bool):
    """
    Perform static analysis on Rust contracts to detect common issues.
    The target can be a file or a directory.
    """
    analyzer = StaticAnalyzer()

    # Track total issues found across all files
    total_issues = 0

    if os.path.isdir(target):
        contract_files = find_rust_contracts(target)
        if not contract_files:
            click.echo("No Rust contract files found in the directory.")
            return
        if analyzer.check_reentrancy_feature(target):
            click.echo("\nHigh severity issues:")
            click.echo("  [1] Reentrancy feature status")
            click.echo("      Status: NOT enabled for stylus-sdk")
            click.echo('''   [dependencies]
            stylus-sdk = { version = "0.6.0", features = ["reentrant"] }\n''')
            click.echo(
                "      Recommendation: You can remove reentrant from features so it can handle automatically by stylus-sdk.")
            click.echo(
                "      Ensure that your contract logic is designed to handle reentrancy appropriately.")

            # Print summary
            click.echo(f"\n===== Analysis Summary =====")
            click.echo(f"Analyzed {len(contract_files)} files")
            click.echo(f"Found {total_issues} total issues")
        else:
            click.echo("Reentrancy feature is enabled for stylus-sdk.")

        all_results = {}
        for file_path in contract_files:
            relative_path = os.path.relpath(file_path, target)
            click.echo(f"\n===== Static Analysis for {relative_path} =====")

            code = read_file_content(file_path)
            if code:
                analysis_result = analyzer.analyze(code, file_path)
                all_results[relative_path] = analysis_result.to_dict()
                total_issues += len(analysis_result.issues)

                format_analysis_results(
                    relative_path, analysis_result, verbose)

                click.echo(
                    f"Analysis completed in {analysis_result.analysis_time:.2f} seconds")
            else:
                click.echo(f"Could not read file: {file_path}")

        if output:
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2)
            logger.info(f"Static analysis results saved to: {output}")

        if pdf:
            generate_pdf_report(all_results, pdf)

        # if analyzer.check_reentrancy_feature(target):
        #     click.echo("\nHigh severity issues:")
        #     click.echo("  [1] Reentrancy feature status")
        #     click.echo("      Status: NOT enabled for stylus-sdk")
        #     click.echo(
        #         "      Recommendation: The stylus-sdk will automatically handle reentrancy checks.")
        #     click.echo(
        #         "      Ensure that your contract logic is designed to handle reentrancy appropriately.")
        #     click.echo(
        #         "      Consider reviewing your contract for potential reentrancy vulnerabilities.")

        #     # Print summary
        #     click.echo(f"\n===== Analysis Summary =====")
        #     click.echo(f"Analyzed {len(contract_files)} files")
        #     click.echo(f"Found {total_issues} total issues")
        # else:
        #     click.echo("Reentrancy feature is enabled for stylus-sdk.")

    else:
        code = read_file_content(target)
        if not code:
            click.echo(f"Could not read file: {target}")
            return

        analysis_result = analyzer.analyze(code, file_path=target)

        format_analysis_results(target, analysis_result, verbose)
        click.echo(
            f"Analysis completed in {analysis_result.analysis_time:.2f} seconds")

        if output:
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(analysis_result.to_dict(), f, indent=2)
            logger.info(f"Static analysis results saved to: {output}")

        if pdf:
            generate_pdf_report(analysis_result, pdf)

        if analyzer.check_reentrancy_feature(target):
            click.echo("Reentrancy feature is enabled for stylus-sdk.")
        else:
            click.echo(
                "Reentrancy feature is NOT enabled for stylus-sdk. This is a high-severity issue.")
            click.echo(
                "Consider enabling the reentrancy feature in your Cargo.toml:")
            click.echo('''\n[dependencies]
stylus-sdk = { version = "0.6.0", features = ["reentrant"] }\n''')
            click.echo(
                "Disabling this feature may expose your contract to reentrancy attacks. Ensure that you handle reentrancy carefully in your contract logic.")


def main():
    """Main entry point for the CLI"""
    try:
        cli()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

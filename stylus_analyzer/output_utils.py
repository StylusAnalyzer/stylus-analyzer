"""
Output formatting utilities for Stylus Analyzer
"""
import click


def format_analysis_results(file_path: str, analysis_result, verbose: bool) -> None:
    """
    Format and print analysis results
    
    Args:
        file_path: Path to the analyzed file
        analysis_result: The analysis result object
        verbose: Whether to show detailed output
    """
    if analysis_result.has_issues():
        click.echo(f"\nFound {len(analysis_result.issues)} issues:")
        
        # Group issues by type and severity
        issues_by_severity = {}
        for issue in analysis_result.issues:
            severity = issue['severity']
            if severity not in issues_by_severity:
                issues_by_severity[severity] = []
            issues_by_severity[severity].append(issue)
        
        # Print issues by severity (High to Low)
        severities = ['Critical', 'High', 'Medium', 'Low']
        for severity in severities:
            if severity in issues_by_severity:
                click.echo(f"\n{severity} severity issues:")
                for i, issue in enumerate(issues_by_severity[severity], 1):
                    click.echo(f"  [{i}] {issue['type']}")
                    click.echo(f"      Lines {issue['line_start']}-{issue['line_end']}")
                    if verbose:
                        click.echo(f"      Description: {issue['description']}")
                        click.echo(f"      Code: {issue['code_snippet']}")
                    click.echo(f"      Recommendation: {issue['recommendation']}")
    else:
        click.echo("No issues found.")
    
    if analysis_result.has_errors():
        click.echo(f"\nAnalysis encountered {len(analysis_result.errors)} errors:")
        for error in analysis_result.errors:
            click.echo(f"  Error in {error['detector']}: {error['message']}") 

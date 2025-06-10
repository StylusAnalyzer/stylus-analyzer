"""
Output formatting utilities for Stylus Analyzer
"""
import click
import os
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import inch


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


def generate_pdf_report(results, output_file: str) -> None:
    """
    Generate a PDF report from analysis results
    
    Args:
        results: Analysis results dictionary or StaticAnalysisResult object
        output_file: Path to save the PDF file
    """
    # Convert results to dictionary format if it's not already
    if hasattr(results, 'to_dict'):
        results_dict = results.to_dict()
    else:
        results_dict = results
    
    # Create the PDF document
    doc = SimpleDocTemplate(output_file, pagesize=letter)
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading1']
    heading2_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Custom styles
    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=9,
        leftIndent=20,
        spaceAfter=10,
        backColor=colors.lightgrey,
    )
    
    # Report header
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elements.append(Paragraph("Stylus Analyzer Security Report", title_style))
    elements.append(Paragraph(f"Generated on: {timestamp}", normal_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Summary section
    elements.append(Paragraph("Analysis Summary", heading_style))
    
    # If it's a multi-file analysis
    if isinstance(results_dict, dict) and any(isinstance(v, dict) and 'issues' in v for v in results_dict.values()):
        # This is a multiple file analysis
        total_issues = sum(v.get('total_issues', 0) for v in results_dict.values() if isinstance(v, dict))
        num_files = len(results_dict)
        
        summary_text = [
            f"Analyzed {num_files} files",
            f"Found {total_issues} total issues"
        ]
        
        # Group issues by severity across all files
        severity_counts = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0}
        for file_result in results_dict.values():
            if isinstance(file_result, dict) and 'issues' in file_result:
                for issue in file_result.get('issues', []):
                    severity = issue.get('severity', 'Unknown')
                    if severity in severity_counts:
                        severity_counts[severity] += 1
        
        # Add severity counts to summary
        for severity, count in severity_counts.items():
            if count > 0:
                summary_text.append(f"{severity} Severity Issues: {count}")
        
        for line in summary_text:
            elements.append(Paragraph(line, normal_style))
        
        elements.append(Spacer(1, 0.25*inch))
        
        # Process each file separately
        for file_path, file_result in results_dict.items():
            if isinstance(file_result, dict) and 'issues' in file_result:
                elements.append(Paragraph(f"File: {file_path}", heading2_style))
                elements.append(Spacer(1, 0.1*inch))
                
                _add_file_analysis_to_pdf(elements, file_result, normal_style, code_style)
                elements.append(PageBreak())
    
    else:
        # Single file analysis
        total_issues = results_dict.get('total_issues', 0)
        
        summary_text = [f"Found {total_issues} total issues"]
        
        # Group issues by severity
        severity_counts = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0}
        for issue in results_dict.get('issues', []):
            severity = issue.get('severity', 'Unknown')
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        # Add severity counts to summary
        for severity, count in severity_counts.items():
            if count > 0:
                summary_text.append(f"{severity} Severity Issues: {count}")
        
        for line in summary_text:
            elements.append(Paragraph(line, normal_style))
        
        elements.append(Spacer(1, 0.25*inch))
        
        # Add the main analysis results
        _add_file_analysis_to_pdf(elements, results_dict, normal_style, code_style)
    
    # Build the PDF
    doc.build(elements)
    
    click.echo(f"PDF report generated: {output_file}")


def _add_file_analysis_to_pdf(elements, result, normal_style, code_style):
    """Helper function to add a single file's analysis to the PDF"""
    issues = result.get('issues', [])
    
    if not issues:
        elements.append(Paragraph("No issues found in this file.", normal_style))
        return
    
    # Group issues by severity
    issues_by_severity = {}
    for issue in issues:
        severity = issue.get('severity', 'Unknown')
        if severity not in issues_by_severity:
            issues_by_severity[severity] = []
        issues_by_severity[severity].append(issue)
    
    # Add issues by severity (Critical to Low)
    severities = ['Critical', 'High', 'Medium', 'Low']
    for severity in severities:
        if severity in issues_by_severity:
            elements.append(Paragraph(f"{severity} Severity Issues:", normal_style))
            elements.append(Spacer(1, 0.1*inch))
            
            for i, issue in enumerate(issues_by_severity[severity], 1):
                # Issue header
                elements.append(Paragraph(f"Issue {i}: {issue['type']}", normal_style))
                
                # Issue details table
                data = [
                    ["Location", f"Lines {issue.get('line_start', '?')}-{issue.get('line_end', '?')}`"],
                    ["Description", Paragraph(issue.get('description', 'No description provided'), normal_style)],
                    ["Code Snippet", Paragraph(issue.get('code_snippet', ''), code_style) if issue.get('code_snippet') else ''],
                    ["Recommendation", Paragraph(issue.get('recommendation', 'No recommendation provided'), normal_style)]
                ]
                
                # Create the table
                table = Table(data, colWidths=[1.5*inch, 5*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('BACKGROUND', (1, 0), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                
                elements.append(table)
                
                elements.append(Spacer(1, 0.2*inch))
    
    # Add errors if any
    errors = result.get('errors', [])
    if errors:
        elements.append(Paragraph("Analysis Errors:", normal_style))
        elements.append(Spacer(1, 0.1*inch))
        
        for error in errors:
            elements.append(Paragraph(
                f"Error in {error.get('detector', 'Unknown')}: {error.get('message', 'Unknown error')}",
                normal_style
            ))
        
        elements.append(Spacer(1, 0.2*inch))
    
    # Analysis time
    analysis_time = result.get('analysis_time_seconds', 0)
    elements.append(Paragraph(f"Analysis completed in {analysis_time:.2f} seconds", normal_style)) 

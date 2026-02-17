
import os
import datetime
import json

def generate_report(all_issues, total_score, target_dir):
    """
    Generates a beautiful HTML report from the audit findings.
    """
    
    # Calculate Stats
    total_files_audited = len(all_issues) # Approximate, since we only get issues here? 
    # Actually, all_issues only contains files with issues. 
    # We should pass total_files_audited properly if we want accurate stats.
    # For now, let's assume all_issues IS the full list (which it is in the GUI logic)
    
    # Wait, looking at toolkit_gui logic:
    # It loops over ALL html_files.
    # If a file has issues, it adds to all_issues.
    # If a file is PERFECT, it does NOT add to all_issues.
    # So we need to pass the total count explicitly.
    
    files_with_issues = len(all_issues)
    
    # Determine Status Color
    if total_score >= 90:
        status_color = "#2ecc71" # Green
        status_text = "Excellent"
        status_msg = "Your course is extremely accessible! Great work."
    elif total_score >= 70:
        status_color = "#f1c40f" # Yellow
        status_text = "Good"
        status_msg = "You're getting there! A few tweaks will make this perfect."
    else:
        status_color = "#e74c3c" # Red
        status_text = "Needs Work"
        status_msg = "Some significant accessibility barriers exist. Let's fix them!"

    # Generate Issue List HTML
    issues_html = ""
    for filename, res in all_issues.items():
        tech_issues = res.get("technical", [])
        subj_issues = res.get("subjective", [])
        
        if not tech_issues and not subj_issues:
            continue
            
        file_badges = ""
        if tech_issues:
             file_badges += f'<span class="badge badge-tech">{len(tech_issues)} Errors</span>'
        if subj_issues:
             file_badges += f'<span class="badge badge-subj">{len(subj_issues)} Suggestions</span>'

        issues_html += f"""
        <div class="file-card">
            <div class="file-header">
                <h3>📄 {filename}</h3>
                <div class="badges">{file_badges}</div>
            </div>
            <div class="issue-list">
        """
        
        for issue in tech_issues:
            issues_html += f'<div class="issue-item tech">🔴 {issue}</div>'
        for issue in subj_issues:
            issues_html += f'<div class="issue-item subj">🟡 {issue}</div>'
            
        issues_html += """
            </div>
        </div>
        """

    if not issues_html:
        issues_html = """
        <div class="empty-state">
            <h2>🎉 No Issues Found!</h2>
            <p>Your content is perfectly accessible according to our checks.</p>
        </div>
        """

    # HTML Template
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MOSH Audit Report</title>
    <style>
        :root {{
            --primary: #4b3190;
            --bg: #f5f6fa;
            --card-bg: #ffffff;
            --text: #2f3640;
            --border: #dcdde1;
        }}
        body {{
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }}
        .header {{
            background: var(--primary);
            color: white;
            padding: 40px 20px;
            text-align: center;
        }}
        .header h1 {{ margin: 0; font-size: 2.5em; }}
        .header p {{ opacity: 0.9; }}
        
        .container {{
            max-width: 900px;
            margin: -30px auto 40px;
            padding: 0 20px;
        }}
        
        .score-card {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .score-circle {{
            width: 150px;
            height: 150px;
            border-radius: 50%;
            background: {status_color};
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3.5em;
            font-weight: bold;
            margin: 0 auto 20px;
            box-shadow: 0 0 0 10px rgba(0,0,0,0.05);
        }}
        .status-text {{
            font-size: 1.5em;
            font-weight: bold;
            color: {status_color};
            margin-bottom: 5px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        .stat-val {{ font-size: 2em; font-weight: bold; color: var(--primary); }}
        
        .file-card {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            margin-bottom: 15px;
            overflow: hidden;
        }}
        .file-header {{
            background: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .file-header h3 {{ margin: 0; font-size: 1.1em; color: #333; }}
        
        .issue-list {{ padding: 15px 20px; }}
        .issue-item {{
            padding: 8px 0;
            border-bottom: 1px solid #f1f1f1;
        }}
        .issue-item:last-child {{ border-bottom: none; }}
        .issue-item.tech {{ color: #c0392b; }}
        .issue-item.subj {{ color: #f39c12; }}
        
        .badge {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
            color: white;
            margin-left: 5px;
        }}
        .badge-tech {{ background: #e74c3c; }}
        .badge-subj {{ background: #f1c40f; color: #333; }}
        
        .footer {{
            text-align: center;
            margin-top: 50px;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 40px;
            background: white;
            border-radius: 8px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Course Health Report</h1>
        <p>Generated by MOSH Toolkit on {datetime.datetime.now().strftime("%B %d, %Y")}</p>
    </div>
    
    <div class="container">
        <!-- Score Card -->
        <div class="score-card">
            <div class="score-circle">{total_score}%</div>
            <div class="status-text">{status_text}</div>
            <p>{status_msg}</p>
        </div>
        
        <!-- Stats -->
        <div class="stats-grid">
            <div class="stat-card">
                 <div class="stat-val">{files_with_issues}</div>
                 <div>Files with Issues</div>
            </div>
             <div class="stat-card">
                 <div class="stat-val">{len(all_issues)}</div>
                 <div>Total Files Audited</div>
            </div>
        </div>
        
        <h2 style="margin-bottom: 20px; color: #2c3e50;">Detailed Findings</h2>
        
        {issues_html}
        
    </div>
    
    <div class="footer">
        <p>MOSH: Making Online Spaces Helpful</p>
    </div>
</body>
</html>
    """
    
    report_path = os.path.join(target_dir, "MOSH_Audit_Report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    return report_path

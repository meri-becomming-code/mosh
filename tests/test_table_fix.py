import run_fixer
import os
from bs4 import BeautifulSoup

def test_table_structure_fix():
    print("--- Testing Table Structure Fix ---")
    
    # Problematic HTML provided by user (simplified)
    html = """
<table border="1">
    <caption>Programming Standards</caption>
    <tbody></tbody>
    <thead>
        <tr>
            <th scope="row">The Standard</th>
            <th scope="row">What we look for</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Resilience</td>
            <td>Does it stay running?</td>
        </tr>
    </tbody>
</table>
"""
    test_file = "test_table.html"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(html)
        
    print("Running remediation...")
    remediated, fixes = run_fixer.remediate_html_file(test_file)
    
    print(f"Fixes applied: {fixes}")
    
    soup = BeautifulSoup(remediated, 'html.parser')
    table = soup.find('table')
    
    # 1. Check for empty tbody removal
    tbodies = table.find_all('tbody')
    if len(tbodies) == 1:
        print("PASS: Removed empty <tbody>.")
    else:
        print(f"FAIL: Found {len(tbodies)} tbodies.")
        
    # 2. Check for thead ordering (should be after caption and before tbody)
    caption = table.find('caption')
    thead = table.find('thead')
    tbody = table.find('tbody')
    
    if thead and tbody and table.contents.index(thead) < table.contents.index(tbody):
        print("PASS: <thead> is before <tbody>.")
    else:
        print("FAIL: <thead> ordering incorrect.")
        
    # Headers in <thead> must have scope='col' per WCAG.
    # The original test HTML had scope='row' on thead headers — the fixer
    # correctly upgrades them to scope='col'. Verify this is happening.
    ths = thead.find_all('th')
    if all(th.get('scope') == 'col' for th in ths):
        print("PASS: <thead> headers correctly have scope='col' (WCAG compliant).")
    else:
        actual = [th.get('scope') for th in ths]
        print(f"FAIL: <thead> headers have incorrect scope: {actual}")

    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)
    
if __name__ == "__main__":
    test_table_structure_fix()

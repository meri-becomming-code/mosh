from bs4 import BeautifulSoup, Comment
import re

html_v1 = """
<div style="background-color: #4b3190;">
    <h2>Topic 1</h2>
    <p style="color: #e1bee7">Tagline Text</p>
</div>
<div style="width: 600px">Content</div>
"""

def run_fixer_partial(html_content):
    fixes = []
    
    # regex reflow (simulated)
    def width_replacer(match):
        val = int(match.group(1))
        if val > 320:
             return f"width: 100%; max-width: {val}px"
        return match.group(0)

    if re.search(r'(?<!-)width:\s*(\d+)px', html_content, re.IGNORECASE):
        html_content = re.sub(r'(?<!-)width:\s*(\d+)px', width_replacer, html_content, flags=re.IGNORECASE)
        fixes.append("Reflow Fix")

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Tagline Logic
    for h2 in soup.find_all('h2'):
        parent = h2.parent
        if parent.name == 'div' and 'background-color' in parent.get('style', '').lower() and '#4b3190' in parent['style'].lower():
            tagline = h2.find_next_sibling('p')
            if tagline:
                tagline.extract()
                parent.insert_after(tagline)
                tagline['style'] = "margin-top: 10px; margin-left: 15px; font-style: italic; color: #4b3190;"
                tagline.insert_after(Comment("ADA FIX: Refactored tagline"))
                fixes.append("Tagline Fix")

    return str(soup), fixes

print("--- RUN 1 ---")
out_v1, fixes_v1 = run_fixer_partial(html_v1)
print(f"Fixes: {fixes_v1}")
print(out_v1)

print("\n--- RUN 2 (Idempotency Check) ---")
out_v2, fixes_v2 = run_fixer_partial(out_v1)
print(f"Fixes: {fixes_v2}")
if fixes_v2:
    print("FAIL: Fixes reported on second run!")
else:
    print("PASS: No fixes on second run.")

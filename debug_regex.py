import re

# Scenario 1: Audit Check
# Current Logic: r'\bwidth:\s*(\d+)px'
audit_regex = r'\bwidth:\s*(\d+)px'
style = "max-width: 600px; width: 100%;"

print(f"--- Audit Check ---")
print(f"Style: {style}")
match = re.search(audit_regex, style)
if match:
    print(f"MATCH: {match.group(0)} (Group 1: {match.group(1)})")
    if int(match.group(1)) > 320:
        print("RESULT: FAIL (Incorrectly flagged max-width?)")
else:
    print("RESULT: PASS (Correctly ignored)")

# Scenario 2: Fixer Replacement
# Current Logic: r'width:\s*(\d+)px' (No boundary)
fixer_regex = r'width:\s*(\d+)px'
html_fragment = 'style="max-width: 500px;"'

def replacer(match):
    val = int(match.group(1))
    if val > 320:
        return f"width: 100%; max-width: {val}px"
    return match.group(0)

print(f"\n--- Fixer Replacement ---")
print(f"Original: {html_fragment}")
new_html = re.sub(fixer_regex, replacer, html_fragment)
print(f"Fixed:    {new_html}")

if "max-width: 100%" in new_html:
    print("RESULT: MANGLED (Replaced inside max-width)")
else:
    print("RESULT: CLEAN")

# Scenario 3: Proposed Fix
# Logic: r'(?<!-)width:\s*(\d+)px'
proposed_regex = r'(?<!-)width:\s*(\d+)px'
print(f"\n--- Proposed Fix Check ---")
match = re.search(proposed_regex, style)
if match:
     print(f"Audit Match: {match.group(0)}")
else:
     print("Audit Match: None (Correct)")

new_html_fixed = re.sub(proposed_regex, replacer, html_fragment)
print(f"Fixer Output: {new_html_fixed}")

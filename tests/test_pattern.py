import os
import re

# The link in the assignment HTML
link = r'href="$IMS-CC-FILEBASE$/Uploaded%20Media%202/PE_1_4-3_Returning_results_from_a_function.pptx?canvas_=1&amp;canvas_qs_wrap=1"'

# What we're looking for
pptx_filename = "PE_1_4-3_Returning_results_from_a_function.pptx"
pptx_base = os.path.splitext(pptx_filename)[0]  # "PE_1_4-3_Returning_results_from_a_function"
print(f"PPTX base: {pptx_base}")

# The pattern we're using
pattern1 = rf'href="(\$IMS-CC-FILEBASE\$/[^"]*){re.escape(pptx_base)}([^"]*)"'
print(f"\nPattern: {pattern1}")

# Does it match?
match = re.search(pattern1, link)
print(f"\nMatch found: {match}")

if match:
    print(f"Match groups: {match.groups()}")
else:
    print("\nWHY IT DOESN'T MATCH:")
    print(f"  Looking for: {pptx_base}")
    print(f"  In string: {link}")
    print(f"  Problem: URL encoding! '_' vs '%20'")
    
    # The actual path in the URL is URL-encoded
    print(f"\n  'Uploaded Media 2' becomes 'Uploaded%20Media%202'")
    print(f"  Spaces are %20 in URLs")

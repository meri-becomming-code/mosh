from bs4 import BeautifulSoup

# Simulate run 1
html1 = '''<pre>print("hello")</pre>'''
soup1 = BeautifulSoup(html1, 'html.parser')
pre = soup1.find('pre')

# Apply style like run_fixer does
pre['style'] = "background-color: #121212; color: #ffffff; padding: 15px; border-radius: 5px; font-family: 'Courier New', monospace; white-space: pre;"

# Wrap in div
wrapper = soup1.new_tag('div', style="overflow-x: auto; margin-bottom: 20px;")
pre.wrap(wrapper)

output1 = str(soup1)
print("After Run 1:")
print(output1)
print()

# Now simulate run 2 - parse the output from run 1
soup2 = BeautifulSoup(output1, 'html.parser')
pre2 = soup2.find('pre')

print("Run 2 analysis:")
print(f"  pre style: {pre2.get('style', '')}")
print(f"  parent: {pre2.parent.name}")
print(f"  parent style: {pre2.parent.get('style', '')}")

# Check idempotency
COLOR_BG_DARK = "#121212"
current_style = pre2.get('style', '').lower()
print(f"  Check 'background-color' in style: {'background-color' in current_style}")
print(f"  Check COLOR_BG_DARK in style: {COLOR_BG_DARK.lower() in current_style}")
print(f"  Would SKIP (not add to fixes): {'background-color' in current_style and COLOR_BG_DARK.lower() in current_style}")

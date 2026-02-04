import re
COLOR_BG_DARK = '#121212'
test_style = 'background-color: #121212; color: #ffffff; padding: 15px; border-radius: 5px;'
current_style = test_style.lower()
print(f'current_style: {current_style}')
print(f'COLOR_BG_DARK.lower(): {COLOR_BG_DARK.lower()}')
print(f'Check background-color in style: {"background-color" in current_style}')
print(f'Check color match: {COLOR_BG_DARK.lower() in current_style}')
print(f'Would skip: {"background-color" in current_style and COLOR_BG_DARK.lower() in current_style}')

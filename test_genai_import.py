"""
Quick smoke-test: simulate the import path the EXE will take.
This runs *outside* PyInstaller, so it can't fully test _MEIPASS,
but it confirms the import chain in math_converter.py works.
"""
import sys
print(f"Python: {sys.executable}")

# Test 1: direct import
try:
    import google.genai as genai
    print(f"OK: google.genai imported from {genai.__file__}")
except Exception as e:
    print(f"FAIL: {e}")

# Test 2: what math_converter sees
try:
    import math_converter
    if math_converter.genai is not None:
        print(f"OK: math_converter.genai = {math_converter.genai}")
    else:
        print("FAIL: math_converter.genai is None")
except Exception as e:
    print(f"FAIL importing math_converter: {e}")

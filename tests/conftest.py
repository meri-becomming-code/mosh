"""
pytest configuration file for the MOSH Toolkit test suite.
Adds the project root to sys.path so test modules can import
project code (canvas_utils, converter_utils, run_fixer, etc.).
"""
import sys
import os

# Insert the project root (parent of the tests/ directory) at the front of sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

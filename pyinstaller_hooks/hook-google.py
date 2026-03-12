# PyInstaller hook for the 'google' namespace package.
#
# google is a namespace package (PEP 420) with no __init__.py.
# We must tell PyInstaller to treat it as a package with subpackages
# and provide a proper __init__.py that sets up __path__.

from PyInstaller.utils.hooks import collect_submodules, get_package_paths
import os, site

# Collect every google.* submodule that's importable
hiddenimports = collect_submodules('google')

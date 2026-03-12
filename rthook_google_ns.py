# Runtime hook for PyInstaller: fix the 'google' namespace package.
#
# Problem: 'google' is a namespace package (no __init__.py on disk).
# PyInstaller bundles it as an empty PYMODULE stub.  The data files for
# google/genai, google/auth, google/oauth2 are extracted to _MEIPASS but
# the frozen 'google' module has no __path__ pointing there, so
# 'import google.genai' fails.
#
# Solution: patch google.__path__ so that the subpackages become importable.

import sys
import os

_meipass = getattr(sys, '_MEIPASS', None)
if _meipass:
    _google_dir = os.path.join(_meipass, 'google')
    if os.path.isdir(_google_dir):
        # Ensure _MEIPASS itself is on sys.path
        if _meipass not in sys.path:
            sys.path.insert(0, _meipass)

        # Force-import google and set its __path__ to the _MEIPASS copy.
        # This must happen before anything tries 'import google.genai'.
        try:
            import google
        except ImportError:
            import types
            google = types.ModuleType('google')
            sys.modules['google'] = google

        # Ensure __path__ exists and includes _MEIPASS/google
        if not hasattr(google, '__path__'):
            google.__path__ = []
        if _google_dir not in list(google.__path__):
            google.__path__ = [_google_dir] + list(google.__path__)
        google.__package__ = 'google'

        # Also set __file__ if missing (some import machinery checks this)
        init_file = os.path.join(_google_dir, '__init__.py')
        if os.path.isfile(init_file) and not getattr(google, '__file__', None):
            google.__file__ = init_file

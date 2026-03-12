# PyInstaller hook for google.genai
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules('google.genai')
datas = collect_data_files('google.genai')

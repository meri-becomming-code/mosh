# MOSH - Development Roadmap & Next Steps

**Last Updated:** February 26, 2026

---

## 🎯 Phase 1: Immediate Actions (This Week)

### 1. **Security: Handle Exposed API Key** ⚠️ CRITICAL
```bash
# Step 1: Delete the file
rm check_models.py
git rm check_models.py

# Step 2: Check git history for leaks
git log --all -S "AIzaSyBmi28or6Mcw1NUq1A2tm2Cv-jsg3U3cBc" --oneline

# Step 3: If found in history, use BFG Repo-Cleaner
brew install bfg
bfg --delete-files check_models.py --no-blob-protection

# Step 4: Force push
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push origin --force --all
```

**Estimated Time:** 30 minutes

### 2. **Code Cleanup: Delete Unused Files**
See `CLEANUP_CHECKLIST.md` for full list. Start with:
```bash
# Old spec files (save space)
rm MOSH_ADA_Toolkit_v*.spec
git keep MOSH_ADA_Toolkit.spec

# Dev/test scripts
rm quick_test.py verify_*.py reconvert.py compare_conversion.py
rm process_canvas_export.py latex_converter.py fix_pptx_links.py make_transparent.py

# Test data
rm test.html test.pdf test_img.txt test_source.png verification_test.html

git add -A && git commit -m "refactor: remove 60+ unused development files"
```

**Estimated Time:** 15 minutes  
**Result:** ~70% smaller repository (less clutter, easier to navigate)

### 3. **Add Security Safeguards**
Update `.gitignore`:
```gitignore
# API Keys & Secrets
.env
.env.local
.env.*.local
*.key
*.secret
api_keys.py
check_models.py
config.local.json
credentials.json
```

Create `config.example.json`:
```json
{
  "canvas_url": "https://your-canvas.instructure.com",
  "canvas_token": "YOUR_TOKEN_HERE",
  "gemini_api_key": "YOUR_GEMINI_KEY_HERE",
  "target_dir": "~/Desktop",
  "theme": "light"
}
```

Update `toolkit_gui.py`:
```python
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ToolkitGUI:
    def _load_config(self):
        # Try environment variables first
        config = {
            "canvas_url": os.getenv("CANVAS_URL", ""),
            "canvas_token": os.getenv("CANVAS_TOKEN", ""),
            "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
        }
        
        # Fall back to saved config file
        config_file = Path.home() / ".mosh" / "config.json"
        if config_file.exists():
            import json
            with open(config_file) as f:
                saved = json.load(f)
            config.update(saved)
        
        return config
```

Add to `requirements.txt`:
```
python-dotenv==1.0.0
```

**Estimated Time:** 45 minutes

---

## 📊 Phase 2: Code Quality (Weeks 2-3)

### 1. **Add Type Hints to Core Modules**

Priority order:
1. `converter_utils.py` - Most important
2. `math_converter.py` - AI integration
3. `run_fixer.py` - Core remediation
4. `canvas_utils.py` - API wrapper

Example refactoring for `converter_utils.py`:
```python
from typing import Optional, Tuple, List, Callable, Dict, Any
from pathlib import Path
from dataclasses import dataclass

@dataclass
class ConversionResult:
    """Result of file conversion."""
    success: bool
    output_path: Optional[str]
    error_message: str = ""
    fixes_applied: List[str] = None
    
    def __post_init__(self):
        if self.fixes_applied is None:
            self.fixes_applied = []

# Before
def convert_pdf_to_html(pdf_path):
    ...

# After
def convert_pdf_to_html(
    pdf_path: str,
    log_func: Optional[Callable[[str], None]] = None,
    poppler_path: Optional[str] = None
) -> ConversionResult:
    """Convert PDF to HTML with proper type hints."""
    ...
    return ConversionResult(
        success=True,
        output_path=output_file,
        fixes_applied=fixes
    )
```

**Estimated Time:** 20-30 hours

### 2. **Create pytest Test Suite**

Structure:
```
tests/
├── __init__.py
├── conftest.py                    # Fixtures & shared setup
├── unit/
│   ├── test_contrast_ratio.py
│   ├── test_heading_detection.py
│   ├── test_color_adjustment.py
│   └── test_html_cleanup.py
├── integration/
│   ├── test_pdf_conversion.py
│   ├── test_word_conversion.py
│   └── test_canvas_api.py
└── fixtures/
    ├── sample.pdf
    ├── sample.docx
    └── expected_output.html
```

Example test:
```python
# tests/unit/test_contrast_ratio.py
import pytest
from run_fixer import get_contrast_ratio

class TestContrastRatio:
    """Test WCAG contrast ratio calculations."""
    
    def test_white_on_black(self):
        """Pure white on black should return 21.0."""
        ratio = get_contrast_ratio("#ffffff", "#000000")
        assert ratio == 21.0
    
    def test_black_on_white(self):
        """Black on white should return 21.0."""
        ratio = get_contrast_ratio("#000000", "#ffffff")
        assert ratio == 21.0
    
    def test_same_color_returns_one(self):
        """Same foreground and background = 1.0 contrast."""
        ratio = get_contrast_ratio("#808080", "#808080")
        assert ratio == 1.0
    
    def test_wcag_aa_threshold(self):
        """Verify that ratio meets WCAG AA (4.5:1)."""
        ratio = get_contrast_ratio("#595959", "#ffffff")
        assert ratio >= 4.5
    
    @pytest.mark.parametrize("fg,bg,min_ratio", [
        ("#000000", "#ffffff", 21.0),
        ("#ffffff", "#000000", 21.0),
        ("#0000ff", "#ffff00", 19.56),
    ])
    def test_known_values(self, fg, bg, min_ratio):
        """Test against known WCAG values."""
        ratio = get_contrast_ratio(fg, bg)
        assert ratio >= min_ratio * 0.99  # Allow 1% float error
```

Configure `pytest.ini`:
```ini
[pytest]
minversion = 7.0
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --tb=short
    --cov=converter_utils
    --cov=run_fixer
    --cov=math_converter
    --cov-report=html
    --cov-report=term-missing
```

**Estimated Time:** 30-40 hours

### 3. **Set Up Code Quality Tools**

Create `pyproject.toml`:
```toml
[tool.black]
line-length = 100
target-version = ['py39']

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
strict_equality = true

[tool.pylint]
max-line-length = 100
disable = [
    "missing-module-docstring",
    "too-many-arguments",
]
```

Create `requirements-dev.txt`:
```
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
black==23.12.0
isort==5.13.2
mypy==1.7.1
pylint==3.0.3
flake8==6.1.0
pre-commit==3.5.0
```

Set up pre-commit hooks (`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.0
    hooks:
      - id: black
        language_version: python3.9

  - repo: https://github.com/PyCQA/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: detect-private-key

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: ['types-requests', 'types-PyYAML']
```

Install & run:
```bash
pip install -r requirements-dev.txt
pre-commit install
pre-commit run --all-files
```

**Estimated Time:** 3-4 hours

---

## 🏗️ Phase 3: Architecture (Weeks 4-5)

### 1. **Refactor toolkit_gui.py**

Current structure: Single 3,800-line class  
Target structure: Multi-view architecture

```
gui/
├── __init__.py
├── main.py                    # App launcher
├── base.py                    # Common components
│   ├── BaseView (abstract)
│   ├── CommonDialogs
│   └── ThemeManager
├── views/
│   ├── dashboard_view.py
│   ├── setup_view.py
│   ├── course_view.py
│   ├── math_view.py
│   └── files_view.py
├── dialogs/
│   ├── image_dialog.py        # Alt text editor
│   ├── manifest_dialog.py     # Visual manifest
│   ├── math_board.py          # LaTeX editor
│   └── preflight_dialog.py    # Course check
└── components/
    ├── custom_widgets.py
    ├── tooltips.py
    └── logging_panel.py
```

Benefits:
- Each view is ~300-400 lines (easier to test/maintain)
- Components are reusable
- Clear separation of concerns
- Easier for new contributors

**Estimated Time:** 40-60 hours

### 2. **Create Core Task System**

```python
# core/tasks.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable

class Task(ABC):
    """Base class for long-running operations."""
    
    def __init__(self, name: str):
        self.name = name
        self.progress = 0
        self.total_steps = 0
        self.status = "Pending"
    
    @abstractmethod
    def execute(self, log_func: Optional[Callable] = None) -> Dict[str, Any]:
        """Execute the task."""
        pass
    
    def on_progress(self, current: int, total: int):
        """Called to update progress."""
        self.progress = current
        self.total_steps = total

class RemediationTask(Task):
    """Remediate an HTML file."""
    
    def __init__(self, html_path: str):
        super().__init__("HTML Remediation")
        self.html_path = html_path
    
    def execute(self, log_func: Optional[Callable] = None) -> Dict[str, Any]:
        if log_func:
            log_func(f"Remediating {self.html_path}...")
        
        result = run_fixer.remediate_html_file(self.html_path)
        
        return {
            "success": True,
            "output": result,
            "html_path": self.html_path
        }
```

**Estimated Time:** 15-20 hours

---

## 🚀 Phase 4: CI/CD & Deployment (Week 6)

### 1. **GitHub Actions Workflow**

Create `.github/workflows/test.yml`:
```yaml
name: Tests & Code Quality

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run tests
        run: pytest --cov=. --cov-report=xml
      
      - name: Check type hints
        run: mypy converter_utils.py run_fixer.py math_converter.py
      
      - name: Code formatting
        run: black --check .
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

Create `.github/workflows/build.yml`:
```yaml
name: Build Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pyinstaller
      
      - name: Build executable
        run: python build_app.py
      
      - name: Create release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/MOSH_ADA_Toolkit.exe
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Estimated Time:** 2-3 hours

### 2. **Version Bump & Release**

Update `__init__.py`:
```python
__version__ = "1.1.0"
__author__ = "Dr. Meri Kasprak"
__license__ = "GPL-3.0"
```

Use semantic versioning:
- MAJOR: Breaking changes
- MINOR: New features
- PATCH: Bug fixes

**Current Status:** v1.0.0 (RC17 should be released as 1.0.0)

**Estimated Time:** 1-2 hours

---

## 📈 Maintenance Schedule

### Weekly
- [ ] Review GitHub issues and discussions
- [ ] Check for new Gemini API updates
- [ ] Monitor Canvas API changes

### Monthly
- [ ] Update dependencies
- [ ] Review security advisories
- [ ] Check test coverage trends

### Quarterly
- [ ] Feature planning review
- [ ] Performance optimization pass
- [ ] User feedback analysis

---

## 🎓 Documentation Updates Needed

After refactoring, update/create:

1. **Architecture Documentation** (`docs/architecture.md`)
   - System overview diagram
   - Module interactions
   - Data flow

2. **API Reference** (`docs/api/`)
   - `converter_utils.md`
   - `run_fixer.md`
   - `math_converter.md`

3. **Developer Guide** (`docs/developer-guide.md`)
   - Setup for contributors
   - Code style guide
   - Testing procedures
   - Git workflow

4. **User Manual** (`docs/user-manual.md`)
   - Step-by-step guides
   - Screenshots
   - FAQ

---

## 💰 Time & Resource Estimate

| Phase | Timeline | Hours | Status |
|-------|----------|-------|--------|
| Phase 1: Security & Cleanup | This week | 90 min | 🔴 Urgent |
| Phase 2: Code Quality | Weeks 2-3 | 55 hours | 🟡 Important |
| Phase 3: Architecture | Weeks 4-5 | 75 hours | 🟡 Important |
| Phase 4: CI/CD | Week 6 | 10 hours | 🟢 Nice-to-have |
| **Total** | **6 weeks** | **~141 hours** | |

---

## 🤝 Contributing Guidelines

For anyone helping with this project:

1. **Create a branch**: `git checkout -b feature/my-feature`
2. **Run tests locally**: `pytest`
3. **Check code quality**: `black . && mypy . && pylint **/*.py`
4. **Commit with message**: `git commit -m "feat: add new feature"`
5. **Create pull request** with description
6. **Wait for CI/CD** to pass

Use conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code refactoring
- `docs:` Documentation
- `test:` Test additions
- `chore:` Maintenance

---

**Last reviewed:** February 26, 2026  
**Next review:** March 26, 2026

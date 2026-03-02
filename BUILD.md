# Build Guide for MOSH ADA Toolkit

This guide provides step-by-step instructions for setting up your development environment and building the executable/application on Windows and macOS.

## 📦 Prerequisites

### Windows
1.  **Python 3.10+**: Download and install from [python.org](https://www.python.org/downloads/).
    *   **IMPORTANT**: During installation, check the box that says **"Add Python to PATH"**.
2.  **Git** (Optional but recommended): Download from [git-scm.com](https://git-scm.com/downloads).

### macOS
1.  **Python 3.9+**: Check with `python3 --version`.
2.  **Homebrew**: Install from [brew.sh](https://brew.sh/).
3.  **Poppler** (CRITICAL for PDF conversion):
    ```bash
    brew install poppler
    ```

---

## 🛠️ Step 1: Setting Up the Environment

1.  **Get the Code**:
    ```bash
    git clone https://github.com/meri-becomming-code/mosh.git
    cd mosh
    ```
    *Or download and extract the ZIP from GitHub.*

2.  **Create a Virtual Environment**:
    *   **Windows**:
        ```powershell
        python -m venv venv
        .\venv\Scripts\activate
        ```
    *   **macOS**:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    pip install pyinstaller
    ```

---

## 🚀 Step 2: Building the Application

### Option A: Using the Build Script (Recommended)
Run the specialized build script which handles assets and spec configurations:
*   **Windows**: `python build_app.py`
*   **macOS**: `python3 build_app.py`

### Option B: Windows Quick-Build (Batch File)
1.  Double-click `BUILD_WINDOWS.bat` in the project folder.

### Option C: Manual PyInstaller
```bash
pyinstaller MOSH_ADA_Toolkit.spec --clean --noconfirm
```

---

## 📂 Step 3: Where is my App?

*   Go to the `dist` folder inside your project directory.
*   **Windows**: `MOSH_ADA_Toolkit.exe`
*   **macOS**: `MOSH_ADA_Toolkit.app`

---

## 🍎 macOS Specific Notes (App Signing)

Since the Mac app is unsigned, users will need to:
1.  **Right-click** (or Control-click) on `MOSH_ADA_Toolkit.app`.
2.  Select **"Open"** from the menu.
3.  Click **"Open"** in the security dialog.

Alternatively, run:
```bash
xattr -cr /path/to/MOSH_ADA_Toolkit.app
```

---

## 🔧 Troubleshooting

*   **"Python not recognized"**: Ensure Python is added to your PATH.
*   **"No module named..."**: Ensure the virtual environment is active and `pip install -r requirements.txt` was run.
*   **Poppler Errors**: Ensure Poppler is installed and reachable in your PATH.
    *   **Windows**: Use the `Auto-Setup` button in the Connect tab or follow the `POPPLER_GUIDE.md`.
    *   **macOS**: `brew install poppler`.

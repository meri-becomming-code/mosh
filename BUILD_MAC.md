# Building MOSH ADA Toolkit on Mac

This guide will help you build the Mac version of the MOSH ADA Toolkit.

## Prerequisites

1. **macOS** (any recent version)
2. **Python 3.9 or higher** (check with `python3 --version`)
3. **Git** (should be pre-installed)

## Step-by-Step Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/meri-becomming-code/mosh.git
cd mosh
```

### 2. Create a Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip3 install -r requirements.txt
pip3 install pyinstaller
```

**Note**: If you encounter any permission errors, use:
```bash
pip3 install --user -r requirements.txt
pip3 install --user pyinstaller
```

### 4. Build the Application

```bash
python3 build_app.py
```

This will take a few minutes. You'll see PyInstaller processing all the modules.

### 5. Find Your Application

When the build completes, you'll find:
- **Location**: `dist/MOSH_ADA_Toolkit.app`
- **Size**: ~50-60 MB

### 6. Test the Application

```bash
open dist/MOSH_ADA_Toolkit.app
```

The toolkit GUI should launch!

## Distribution Notes

### For Users (Unsigned App)

Since the Mac app is unsigned, users will need to:

1. Download the `.app` file
2. **Right-click** (or Control-click) on `MOSH_ADA_Toolkit.app`
3. Select **"Open"** from the menu
4. Click **"Open"** in the security dialog

After the first launch, they can open it normally from then on.

### Alternative: Command Line Bypass

Users can also run this command to allow the app:
```bash
xattr -cr /path/to/MOSH_ADA_Toolkit.app
```

## Uploading to GitHub

To create a release with the Mac version:

### Option 1: GitHub Web Interface

1. Go to https://github.com/meri-becomming-code/mosh/releases
2. Click **"Create a new release"** or **"Draft a new release"**
3. Create a new tag (e.g., `v2026.1.3-mac`)
4. Drag and drop `MOSH_ADA_Toolkit.app` (you may want to zip it first)
5. Add release notes describing Mac compatibility
6. Publish!

### Option 2: Compress and Upload

```bash
# Create a zip file for easier distribution
cd dist
zip -r MOSH_ADA_Toolkit_Mac.zip MOSH_ADA_Toolkit.app
```

Then upload `MOSH_ADA_Toolkit_Mac.zip` to the GitHub release.

## Troubleshooting

### "Command not found: python3"

Try `python` instead of `python3`:
```bash
python build_app.py
```

### "No module named 'tkinter'"

macOS should include tkinter by default. If missing:
```bash
brew install python-tk
```

### Build Fails with "Permission Denied"

Make sure you have write permissions:
```bash
chmod -R u+w .
```

### "ImportError" during build

Make sure all dependencies are installed:
```bash
pip3 install --upgrade -r requirements.txt
```

## File Size Comparison

- **Windows .exe**: ~56 MB
- **Mac .app**: ~50-60 MB (similar)

Both include all Python libraries and dependencies for offline use.

## What's Included

The Mac build includes all the same features as Windows:
- ✅ HTML remediation
- ✅ PDF processing
- ✅ Word/PowerPoint conversion
- ✅ Canvas integration
- ✅ Jeanie AI features (with API key)
- ✅ Audit tools
- ✅ All guides and documentation

## License

This toolkit is distributed under the GNU General Public License v3.0.
See LICENSE file for details.

## Questions?

If you encounter any issues building on Mac:
1. Check that all prerequisites are installed
2. Make sure you're in the `mosh` directory
3. Try running in a fresh virtual environment
4. Check the GitHub Issues page

---

**Happy Building!** 🚀🍎

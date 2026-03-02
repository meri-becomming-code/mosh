# How to Install Poppler for Math PDF Conversion

The MOSH Toolkit uses a tool called **Poppler** to read your PDF files and turn them into images that our AI can understand. We've made this incredibly easy to set up.

## Option 1: The One-Click Way (Recommended)
1. Open the **Connect & Setup** tab in MOSH.
2. Click the **"Auto-Setup Poppler"** button.
3. MOSH will automatically download, extract, and link everything for you.
4. **Done!** You'll see a green checkmark once it's ready.

## Option 2: The "Portable" Way (Best for Work Computers)
If you are at a school or office that blocks downloads or installations:
1. Create a folder named `mosh_helpers` in the **same folder** as your MOSH program.
2. Inside that folder, create another folder named `poppler`.
3. Put the Poppler "bin" folder inside there.
4. MOSH will automatically detect it on startup — no settings required!

## Option 3: The Manual Way
If you prefer to manage it yourself:
1. Download Poppler for Windows [here](https://github.com/oschwartz10612/poppler-windows/releases/).
2. Extract the ZIP file.
3. In MOSH **Settings**, click "Browse" for Poppler Path and select the **bin** folder inside your extracted files.

---
> **Why do I need this?**
> Standard computers don't have the "eyes" to read math equations inside a PDF. Poppler provides those eyes so our AI can read the math and make it accessible for your students!

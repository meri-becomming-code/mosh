# How to Install Poppler for Math PDF Conversion

The MOSH Toolkit uses a tool called **Poppler** to read your PDF files and turn them into images that our AI can understand. If you're seeing a "Poppler not found" error, follow these simple steps:

## 1. Download Poppler
- Go to the [Poppler for Windows download page](https://github.com/oschwartz10612/poppler-windows/releases/).
- Download the latest ZIP file (usually named something like `Release-x.x.x.zip`).

## 2. Extract the Folder
- Right-click the downloaded ZIP file and select **Extract All...**
- Move the extracted folder somewhere safe on your computer (for example, into your **Documents** or **C:\Program Files**).

## 3. Link it to MOSH
- Open **MOSH Toolkit**.
- Go to **Advanced** > **Settings** (or look for the Poppler Path button in Expert Mode).
- Click **Browse** next to "Poppler Bin Path".
- Navigate to the folder you extracted and find the **bin** folder inside it. 
- Click **Select Folder**.

## 4. Test it!
- Try converting a Math PDF again. It should work now!

> **Why do I need this?**
> Standard Windows doesn't come with the ability to "see" inside PDFs the way mathematicians need. Poppler is the industry standard tool that bridges that gap!

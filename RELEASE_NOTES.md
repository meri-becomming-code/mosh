# MOSH ADA Toolkit - Release Notes

## Latest Updates (February 6, 2026)

### 🎯 PDF to HTML Conversion - Major Improvements

**Problem Solved:** PDF conversions were creating fragmented output with each text span becoming a separate paragraph, making content difficult to read and causing accessibility issues.

**What's Fixed:**
- **Text Aggregation**: Text spans are now combined into complete lines before processing
- **Smart Paragraph Grouping**: Related lines are grouped into coherent paragraphs using vertical spacing analysis
- **Bullet List Detection**: Bullet points (•, -, *, ◦, ▪, ⚬) are now properly detected and formatted as `<ul>` and `<li>` tags
- **Priority Logic**: List detection takes priority over font-based header detection to prevent bullets from being misclassified as headers

**Impact:**
- ✅ Screen readers can now properly announce list structures
- ✅ Content flows naturally with proper paragraph breaks
- ✅ Document semantic structure is preserved
- ✅ No more fragmented text with dozens of tiny paragraphs

**Technical Details:**
- Modified `converter_utils.py` lines 655-738
- Three-stage processing: span aggregation → line grouping → semantic unit detection
- Vertical spacing threshold of 24px determines paragraph breaks
- Supports both bulleted and numbered list patterns

---

### 🖼️ PowerPoint Image Sizing Fix

**Problem Solved:** Images from PowerPoint files were being converted too large, dominating the page width.

**What's Fixed:**
- Images are now limited to 50% of page width when text content is present
- Better image-to-text ratio for improved readability
- Maintains visual balance in converted content

---

### 💬 "Spread the Word" Message Update

**What's Changed:**
- Updated the post-conversion message with current information
- Encourages users to share the toolkit with colleagues
- Helps build the alpha testing community

---

## How to Use These Improvements

### PDF Conversion
Simply convert any PDF file using:
- **Single file**: Click the PDF button and select a file
- **Batch conversion**: Use "Roll the Dice" to process entire folders
- **Canvas import**: Import `.imscc` files - PDFs are automatically processed

All three methods use the same improved conversion engine.

### Verification
To verify the improvements:
1. Convert a PDF with lists or paragraphs
2. Open the generated HTML file
3. Look for `<ul>` and `<li>` tags (lists)
4. Check that paragraphs contain complete thoughts, not single lines

---

## Alpha Testing

These improvements are ready for real-world testing with educators. Please report:
- PDFs that don't convert well
- Missing list or paragraph detection
- Any regressions in table or image extraction

---

## Files Modified

- `converter_utils.py` - Core PDF conversion logic enhanced
- PowerPoint converter - Image sizing corrections
- GUI message dialogs - Updated "Spread the Word" content

---

**Version**: Alpha (Pre-Release)  
**Date**: February 6, 2026  
**Build**: Use `build_app.py` to create the latest executable

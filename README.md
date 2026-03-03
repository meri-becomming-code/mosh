# MOSH ADA Toolkit 🤖♿
**"Making Online Spaces Helpful" — The Intelligent Accessibility Suite for Educators**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Website](https://img.shields.io/badge/Website-Live-green.svg)](https://meri-becomming-code.github.io/mosh/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![YouTube](https://img.shields.io/badge/YouTube-Tutorial%20Videos-red.svg)](https://www.youtube.com/@mccmeri)

MOSH is a mission-driven, professional-grade accessibility suite designed to solve the massive "remediation gap" facing K-12 and Higher Education as the **April 2026 ADA compliance deadline** approaches. Unlike generic tools, MOSH is a specialized engine that understands the nuances of Canvas LMS exports, complex math notation, and semantic document structure.

## 🚀 Key Innovations

### 🧠 Intelligent Remediation
- **AI-Powered Vision**: Leverage Gemini 2.0 Flash to automatically generate alt-text for complex diagrams, solve handwritten math, and even OCR images of tables into fully accessible HTML code.
- **Visual Review Dashboard**: A high-speed interface that lets humans verify and "nudge" AI-generated crops, ensuring that complex scientific content stays accurate.
- **Long Description Generator**: Automatically generates linked HTML pages for complex graphics (Calculus graphs, intricate schematics) to meet WCAG best practices without bloating alt-text fields.

### 🎨 Design & Structure
- **AI Mobile Design**: A one-click tool that uses Gemini to intelligently wrap legacy HTML content in modern, responsive, mobile-first design patterns for the Canvas App.
- **Structural Auto-Fixer**: Batch-corrects hierarchical headings, color contrast ratios, duplicate links, and invalid table structures across thousands of files in minutes.
- **Smart List Reflow**: Detects and converts "visual lists" (paragraphs starting with symbols) into semantic `<ul>`/`<li>` tags for screen reader compatibility.

### 📐 Specialized Math Workflows
- **PDF-to-Math**: Converts "locked" PDF equations into editable, accessible LaTeX.
- **Handwriting OCR**: High-accuracy recognition of teacher handwritten notes and whiteboard captures.

## 🛠️ Under the Hood (Technical Profile)
*This project serves as a demonstration of robust software engineering and complex problem-solving:*

- **Asynchronous Architecture**: Implements Python `threading` and `queue` systems to perform heavy AI analysis and file processing without freezing the Tkinter GUI.
- **DOM Orchestration**: Uses `BeautifulSoup4` for complex HTML parsing, sanitization, and restructuring of Canvas LMS export packages.
- **Portable Dependencies**: Features a custom "One-Click Setup" and **Portable Mode** for Poppler binaries, managing binary dependencies across disparate user environments.
- **Cross-Platform Compatibility**: Supports Windows and macOS (via Homebrew integration) with persistent configuration management via JSON.
- **Idempotent Logic**: Smart-hashing ensures that files aren't repeatedly processed, saving AI tokens and computational time.

---

## 🎯 Project Mission & Dedication
MOSH was born from a personal journey. Dedicated to **Michael Joshua (MOSH) Albright**, who battles Diabetic Retinopathy, this project is a gift back to the education community. 

I believe that accessibility is a foundational human right. This tool is released **freely and open-source** to ensure that no teacher is left behind by the digital transition.

*— Developed by Dr. Meri Kasprak*

## 🏁 Getting Started
1. **Visit our [Live Site](https://meri-becomming-code.github.io/mosh/)** to see the vision.
2. **Watch the [Tutorial Video Series](https://www.youtube.com/@mccmeri)** on YouTube for a full walkthrough.
3. Download the latest `MOSH_ADA_Toolkit_RCxx.exe` from the [Releases](https://github.com/meri-becomming-code/mosh/releases) page.
4. **No Setup required**: Use the *Auto-Setup* button in the app to grab everything you need in one click.

## ⚖️ License
Released under the **GNU General Public License v3.0**. Built with love, AI, and a commitment to inclusive education.

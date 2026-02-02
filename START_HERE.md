# MCC Faculty ADA Toolkit (2026 Edition)

This toolkit helps you audit and fix accessibility (ADA) issues in your HTML course content.

## 📦 What's Inside?

### Quick Start (For Instructors)
*   **`LAUNCH_TOOLKIT.bat`**: **Double-click this file** to start. It opens a menu to run any of the tools below without using commands.

### Tools (Run these)
*   **`interactive_fixer.py`**: **(Recommended)** Walks you through files and asks you to type missing Alt Text.
*   **`run_fixer.py`**: Automatically fixes common code issues (headings, contrast, tables).
*   **`run_scanner.py`**: Scans for specific bad assets (read-only mode).
*   **`run_audit.py`**: Creates a full report (`audit_report.json`) of all issues.

### Guides (Read these)
*   **`GUIDE_MANUAL_FIXES.md`**: Explains how to fix the "subjective" things the robot can't (like writing meaningful alt text).
*   **`GUIDE_COMMON_MISTAKES.md`**: A quick list of "Gotchas" to avoid.
*   **`GUIDE_STYLES.md`**: The official style guide for colors, fonts, and layout.

---

## 🚀 Getting Started

### 1. Install & Setup
**Option A: Using the Launcher (Easiest)**
1.  Double-click `LAUNCH_TOOLKIT.bat`.
2.  Type `4` and press Enter to "Install Requirements".
3.  You're ready!

**Option B: Manual Setup**
Open a terminal in this folder and run:
```bash
pip install -r requirements.txt
```

### 2. Fix Your Content
**Recommended Workflow:**
1.  Double-click `LAUNCH_TOOLKIT.bat`.
2.  Select **Option 1 (Run Toolkit)**.
3.  **Step 1:** It will ask if you want to auto-fix headings/tables. Type `Y`.
4.  **Step 2:** It will then find any images missing descriptions and ask you to type them.

### 3. Final Check
Run **Option 2 (Audit Report)** if you want a final pass summary.

## ❓ Need Help?
Refer to `GUIDE_MANUAL_FIXES.md` for issues labeled "Subjective" or "Remediation Tag Found".

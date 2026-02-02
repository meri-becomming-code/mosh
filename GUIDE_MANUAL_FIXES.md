# 🧠 Human Remediation Guide: The "Subjective" Stuff
**For things strictly code cannot fix.**

## 1. Alt Text (Images)
The auditor flags images as "Generic Alt Text" or "Filename used". You must describe the *meaning*.
*   **Bad:** `image.png`, `chart`, `photo of dog`
*   **Good:** `Bar chart showing 50% increase in sales in Q3`, `Golden retriever sitting on grass`
*   **Decorative:** If an image is purely for decoration (borders, flourishes), you can set `alt=""` (empty string).

## 2. Descriptive Links
Panorama hates "Click Here".
*   **Bad:** "Click here to read the report."
*   **Good:** "Read the [2026 ADA Compliance Report]."

## 3. Video Captions
If the auditor flags a `<video>` missing tracks:
1.  **Canvas Studio / YouTube:** Ensure captions are enabled on the platform itself.
2.  **Raw Video Files:** You must generate a `.vtt` file and link it.
    *   *Tip: It is almost always better to host videos on Canvas Studio or YouTube than embedding raw MP4 files.*

## 4. Complex Data (Tables & Charts)
*   **Tables:** The script fixes the *headers*, but you must check the *caption*. Does "Information Table" describe it well? Change it to "Schedule of Classes" or "Grading Rubric".
*   **Charts:** Accessibility checkers cannot see inside a PNG chart. You **MUST** provide a data table or a long text description below the chart.

## 5. Math
*   **Old Way:** Images of equations.
*   **New Way:** Use the Canvas Equation Editor (Insert -> Equation). It acts like a calculator and makes it accessible automatically.

---
*Use this guide alongside `audit_report_v3.json` to finish the job.*

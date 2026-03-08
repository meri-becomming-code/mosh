# Non-Math Usability Persona Test Report

Date: 2026-03-08
Scope: Non-math workflows only (Connect/Setup, file conversion, Guided Review for links/images, Auto-Fix, Audit, Pre-Flight, Canvas push prep).
Method: Code walkthrough + workflow simulation + existing automated test run.

## Validation Performed
- Automated tests: `10 passed, 2 skipped` using `pytest -q tests`.
- UI/workflow reviewed in:
  - `toolkit_gui.py` (setup, course flow, review dialogs, pre-flight)
  - `converter_utils.py` (non-math output behavior)
  - quick-start documentation for user expectation alignment.

## 8 Personas (K-12 + College/University)

### 1) K-2 Classroom Teacher (low technical comfort)
- Goal: Convert one class newsletter and 2 worksheets.
- Non-math flow used: Setup → Select folder → Word convert → Auto-Fix → Guided Review.
- Sticking points:
  - Setup screen is dense before first success.
  - Token/Course ID wording is still technical.
- Improve:
  - Add “Simple Mode” that hides advanced sections by default.
  - First-run checklist with 3 buttons only: Load, Convert, Fix.

### 2) Grade 5 Science Teacher (moderate technical comfort)
- Goal: Convert PPT + PDF reading packet, fix links, upload.
- Sticking points:
  - Conversion wizard pre-selects all files; easy to include unwanted files.
  - Copyright warning exists but selection UX still risky.
- Improve:
  - Add file-type chips + “Exclude publisher-like files” toggle.
  - Start wizard with no files selected, with explicit “Select all my authored files.”

### 3) Grade 8 ELA Teacher (time constrained)
- Goal: Weekly remediation in <20 minutes.
- Sticking points:
  - Many similarly weighted buttons in Step 3.
  - Recommended order is not strongly enforced.
- Improve:
  - Add “Run Recommended Workflow” button (Auto-Fix → Guided Review → Link Repair → Quick Report).
  - Show live progress checklist with completion badges.

### 4) High School CTE Teacher (mixed media heavy)
- Goal: Convert slides/manuals with many screenshots.
- Sticking points:
  - Image dialog includes math/table controls even when non-math workflow is active.
  - Cognitive load during repetitive alt-text review.
- Improve:
  - Context-aware dialog: non-math mode hides math-only controls.
  - Add bulk actions: “Use AI for all remaining screenshots with edit queue.”

### 5) High School Special Education Teacher (accessibility-focused)
- Goal: Ensure all pages are screen-reader friendly.
- Sticking points:
  - “Trust AI” toggle can skip manual checks without clarity of confidence threshold.
  - Link review asks replacement text but does not preview current anchor text prominently.
- Improve:
  - Require confidence badge + reason before auto-accept.
  - In link dialog, show old text/new text side-by-side and suggested rewrite.

### 6) Community College Adjunct (teaches evenings)
- Goal: Fast setup every term on different machines.
- Sticking points:
  - Setup mixes permanent config + per-course state in one long page.
  - Section numbering is inconsistent (duplicate “4”).
- Improve:
  - Split setup into tabs: Account, Course, Output, Advanced.
  - Fix section numbering and add sticky “Save/Validated” status chip.

### 7) University Instructional Designer (supports many faculty)
- Goal: Remediate multiple course exports consistently.
- Sticking points:
  - Batch conversion and final upload readiness can feel ambiguous.
  - Pre-Flight has “Upload anyway” path that may bypass unresolved issues.
- Improve:
  - Add policy profile (strict/standard/expedite) controlling upload gating.
  - Export machine-readable report (`json/csv`) for ticketing handoff.

### 8) University Accessibility Coordinator (compliance oversight)
- Goal: Audit + evidence package for ADA readiness.
- Sticking points:
  - Existing tests are useful but not deep on UI behavior and edge-case regression.
  - Non-math compliance evidence not centralized in one artifact.
- Improve:
  - Add regression suite for workflow-level scenarios (wizard selections, link dialog decisions, pre-flight gating).
  - Generate one-click “Compliance Evidence Bundle” (audit report + change log + unresolved issues).

## Cross-Persona Top Sticking Points (Ranked)

1. **Setup cognitive overload for first-time users**
2. **Action hierarchy unclear in Step 3 (too many equal-priority buttons)**
3. **Review dialogs are powerful but too busy for non-math-only tasks**
4. **Pre-Flight allows risky continuation without strong guardrails**
5. **Selection safety in conversion wizard can improve**
6. **Test coverage is passing but thin on end-to-end UX regressions**

## Recommended Improvements

### P0 (Immediate)
- Add **Simple Mode** default and hide advanced controls until expanded.
- Add **Recommended Workflow** single-button orchestration in Course view.
- Make image/link dialogs **context-aware** (non-math-first controls only).

### P1 (Next)
- Strengthen Pre-Flight with policy gates and clearer risk language.
- Improve conversion wizard defaults (start unselected, safer filters).
- Clarify “Trust AI” with confidence indicator and per-item override.

### P2 (Then)
- Add role-based templates (Teacher, Designer, Accessibility Lead).
- Add exportable compliance evidence bundle.
- Add workflow-level regression tests for non-math journeys.

## Concrete Areas in Code to Prioritize
- Setup complexity and sectioning: `toolkit_gui.py` (`_build_setup_view`)
- Action ordering and labels: `toolkit_gui.py` (`_build_course_view`)
- Review dialog simplification: `toolkit_gui.py` (`_show_image_dialog`, `_show_link_dialog`)
- Upload safeguards/readiness logic: `toolkit_gui.py` (`_show_preflight_dialog`)

## Test Outcome Summary (Non-Math)
- Automated tests currently available completed successfully: **10 passed, 2 skipped**.
- Main risks are **UX and workflow safety**, not immediate converter crashes.

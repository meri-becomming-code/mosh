# MOSH Pilot Test Plan: Two Paths

## Scope
Use two independent tester tracks:
1. **Math Track** (equations, OCR, LaTeX workflows)
2. **Non-Math Track** (structure, layout, links, media, accessibility)

---

## Track A: Math Testers

### Tester Profile
- STEM faculty, math-heavy Canvas pages, PDF equation content
- Comfortable validating equation accuracy

### Required Scenarios
1. **Single-file math conversion**
   - Input: 1 PDF with equations, 1 DOCX with equations
   - Validate: equation detection, conversion success, readable output
2. **Bulk math conversion**
   - Input: mixed folder (math + non-math)
   - Validate: non-math files are skipped and reported correctly
3. **Image/OCR math checks**
   - Validate: equation images flagged correctly, false positives manageable
4. **Canvas-ready HTML output**
   - Validate: no broken rendering, equation sizing acceptable

### Pass Criteria
- No blocker crashes
- Equation meaning preserved in >95% of sampled items
- Skip/report behavior works for non-math files
- Exported files open and render in Canvas without ratio/layout breakage

---

## Track B: Non-Math Testers

### Tester Profile
- General education faculty, content-heavy pages, PPT/Word exports
- Focus on structure, readability, and workflow speed

### Required Scenarios
1. **PPT conversion + fixer**
   - Validate: image/text side-by-side where possible, no horizontal scroll
2. **General page remediation**
   - Validate: headings, lists, table wrappers, link clarity
3. **Media embeds**
   - Validate: iframes keep original aspect ratio when resized
4. **Upload-ready output**
   - Validate: link checks run before publish path

### Pass Criteria
- No blocker crashes
- Layout is stable on desktop/mobile
- No major spacing defects from floats
- Output is upload-ready with minimal manual cleanup

---

## Shared Defect Severity
- **S0**: crash/data loss/blocker
- **S1**: incorrect accessibility or broken content
- **S2**: major UX friction, recoverable
- **S3**: minor visual/wording issue

## Required Bug Report Fields
- Track: Math or Non-Math
- Source file type(s): PPT/PDF/DOCX/HTML
- Steps to reproduce
- Expected vs actual result
- Screenshot/snippet
- Severity (S0-S3)

---

## Pilot Cadence (Recommended)
- Day 1: onboarding + scripted run
- Days 2–5: real course content testing
- Day 6: issue triage
- Day 7: stabilization patch list

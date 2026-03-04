# Teacher Personas & Simulated User Testing
## MOSH ADA Toolkit v1.0.0-RC17

---

## 8 Teacher Personas

### 1. 👩‍🏫 Maria Santos — 1st Grade Math
**Demographics:** 28, first-generation college grad, Title I school in Texas  
**Tech Comfort:** Low-Medium (uses iPad apps, struggles with "backend" stuff)  
**Content:** Counting, addition/subtraction with pictures, number lines  
**Tools Used:** Worksheets from TeachersPayTeachers, hand-drawn number bonds  
**Accessibility Need:** Student with visual impairment uses screen reader  

**Quote:** *"I just need something that works. I don't have time to learn complicated software."*

---

### 2. 👨‍🏫 David Chen — 4th Grade Math
**Demographics:** 42, 15 years teaching, suburban California  
**Tech Comfort:** Medium (comfortable with Google Classroom, basic Canvas)  
**Content:** Fractions, area models, multi-digit multiplication  
**Tools Used:** PowerPoints with colorful visuals, PDF worksheets  
**Accessibility Need:** Two students with IEPs, one uses ZoomText  

**Quote:** *"I make my own materials. They're colorful and engaging. I just need them accessible."*

---

### 3. 👩‍🏫 Patricia "Pat" Williams — 6th Grade Pre-Algebra  
**Demographics:** 55, 30 years experience, rural Georgia  
**Tech Comfort:** Low (prefers paper, forced onto Canvas by district)  
**Content:** Integer operations, coordinate planes, basic equations  
**Tools Used:** Scanned handwritten notes, textbook publisher PDFs  
**Accessibility Need:** Mandated by district accessibility audit  

**Quote:** *"I've been teaching longer than these computers have existed. Why do I need to change?"*

---

### 4. 👨‍🏫 Marcus Johnson — 8th Grade Algebra I
**Demographics:** 35, former software developer turned teacher  
**Tech Comfort:** High (writes Python scripts, builds custom tools)  
**Content:** Linear equations, graphing, systems of equations  
**Tools Used:** Desmos, self-made LaTeX documents, Jupyter notebooks  
**Accessibility Need:** Wants to model inclusive practices for students  

**Quote:** *"I want to understand exactly what the AI is doing. Give me the logs."*

---

### 5. 👩‍🏫 Sarah Mitchell — High School Geometry
**Demographics:** 31, 5 years teaching, urban Chicago  
**Tech Comfort:** Medium-High (early adopter, loves new ed-tech)  
**Content:** Proofs, constructions, transformations, lots of diagrams  
**Tools Used:** GeoGebra exports, PowerPoints with complex figures  
**Accessibility Need:** Blind student joining class next semester  

**Quote:** *"The diagrams ARE the lesson. If those aren't accessible, nothing is."*

---

### 6. 👨‍🏫 Robert "Bob" Kowalski — High School Pre-Calculus
**Demographics:** 48, department chair, suburban Ohio  
**Tech Comfort:** Medium (uses what district provides, no more)  
**Content:** Trigonometry, function transformations, limits intro  
**Tools Used:** Publisher textbook PDFs, TI calculator screenshots  
**Accessibility Need:** Evaluating tools for district-wide adoption  

**Quote:** *"If my least tech-savvy colleague can't use it, it's not ready for our department."*

---

### 7. 👩‍🏫 Dr. Aisha Patel — AP Calculus BC / Dual Enrollment
**Demographics:** 38, PhD in Math Education, magnet school  
**Tech Comfort:** High (uses Overleaf, custom LaTeX templates)  
**Content:** Integration techniques, series, differential equations  
**Tools Used:** Hand-typed LaTeX, Mathematica exports, custom PDFs  
**Accessibility Need:** College Board accommodation requirements  

**Quote:** *"My students take the AP exam. The alt-text needs to be mathematically precise."*

---

### 8. 👨‍🏫 Dr. James Morrison — University Calculus III / Linear Algebra
**Demographics:** 62, tenured professor, state university  
**Tech Comfort:** Medium (knows LaTeX well, hates GUIs)  
**Content:** Multivariable calculus, vector fields, matrix operations  
**Tools Used:** LaTeX beamer slides, hand-drawn 3D diagrams scanned  
**Accessibility Need:** Disability services requiring all materials in accessible format  

**Quote:** *"I've been writing LaTeX since 1989. Just give me a command-line tool."*

---

---

## Simulated User Testing Sessions

### Test Scenario: Convert a PDF with handwritten math and graphs to accessible HTML

---

## 🔴 Persona 1: Maria Santos (1st Grade)

### Task: Convert a worksheet with counting bears and number bonds

**Step 1: Opening the Toolkit**
- ✅ Double-clicks MOSH_ADA_Toolkit.exe
- ✅ Sees friendly dashboard with big buttons

**Step 2: Finding the right mode**
- ❌ **STUCK** — Clicks "File Conversion Suite" first (Word/PPT)
- ❌ Doesn't see PDF option there
- 😤 *"Where do I put my PDF?"*
- ⏱️ Wanders for 2 minutes before finding "Math Magic"

**Step 3: Uploading the PDF**
- ✅ Drag-and-drop works
- ✅ Sees progress bar

**Step 4: Visual Review Dialog Appears**
- ❌ **CONFUSED** — Dialog says "Review AI-Detected Images"
- ❌ Doesn't understand "bounding boxes"
- ❓ *"What are these green rectangles? Did I do something wrong?"*
- ❌ **FRUSTRATED** — Clicks X to close dialog (cancels everything)

**Step 5: Retry**
- ✅ Opens again, this time clicks "Use AI Boxes As-Is"
- ✅ Conversion completes

**Step 6: Reviewing Output**
- ❌ **STUCK** — Output folder opens, but she doesn't know which file is the "answer"
- ❓ *"There's a .html and a _graphs folder... which one do I upload?"*

### Pain Points Identified:
1. **Navigation confusion** — PDF conversion hidden under "Math Magic" not obvious
2. **Jargon** — "Bounding boxes", "AI-detected" scary for low-tech users
3. **Dialog intimidation** — Visual review looks like an error screen
4. **Output confusion** — Unclear what to do with multiple output files

---

## 🟡 Persona 2: David Chen (4th Grade)

### Task: Convert colorful fraction PowerPoint with area models

**Step 1-3: Getting Started**
- ✅ Finds "File Conversion Suite" for PowerPoint
- ✅ Uploads file successfully

**Step 4: Image Alt-Text Prompts**
- ❌ **SLOW** — Gets prompted for 14 images one by one
- 😤 *"I have 30 slides! This will take forever!"*
- ❌ Starts clicking "Skip" on everything

**Step 5: Output Quality**
- ⚠️ Reviews HTML — half the images say "Visual Element"
- 😤 *"These descriptions are useless for my blind student!"*

**Step 6: Trying to Fix**
- ❌ **STUCK** — Can't find how to go back and add descriptions
- ❓ *"Do I have to convert the whole thing again?"*

### Pain Points Identified:
1. **Alt-text fatigue** — Too many prompts for image-heavy presentations
2. **No batch mode** — Can't "describe all similar images at once"
3. **Generic fallbacks** — "Visual Element" is useless but too easy to accept
4. **No post-edit workflow** — Once converted, hard to fix mistakes

---

## 🔴 Persona 3: Pat Williams (6th Grade)

### Task: Convert scanned handwritten notes to accessible format

**Step 1: Finding Poppler**
- ❌ **BLOCKED** — Error: "Poppler not found"
- ❓ *"What is Poppler? Is that a virus?"*
- ❌ Closes application

**Step 2: Reading Error Message**
- ⚠️ Error says "See POPPLER_GUIDE.md"
- ❌ **LOST** — Doesn't know what .md files are or how to open them

**Step 3: Calling IT**
- 😤 *"This is exactly why I don't use technology."*
- ❌ **ABANDONS TASK** — Waits for IT to install Poppler (3 days later)

**Step 4: Finally Converting**
- ✅ Poppler installed, conversion starts
- ⚠️ Visual review appears with messy handwriting detection
- ❌ **OVERWHELMED** — AI detected 23 "images" including random marks
- ❓ *"Why is it highlighting my margin notes?"*
- ❌ Clicks "Use AI Boxes As-Is" without reviewing

**Step 5: Output**
- ❌ HTML has cropped images of random scribbles
- 😤 *"This is worse than what I started with!"*

### Pain Points Identified:
1. **Poppler dependency** — Massive barrier for non-technical users
2. **Error messages assume tech literacy** — "See .md file" unhelpful
3. **Handwriting chaos** — AI detects too much on messy scans
4. **No "this is text, not an image" option** — Can't tell AI what's what
5. **Garbage in, garbage out** — Low-quality scans produce low-quality output

---

## 🟢 Persona 4: Marcus Johnson (8th Grade)

### Task: Convert LaTeX-generated PDF with graphs

**Step 1-3: Setup**
- ✅ Already has Poppler installed
- ✅ Finds Math Magic immediately
- ✅ Uploads PDF

**Step 4: Visual Review**
- ✅ **LOVES IT** — "Oh cool, I can see what the AI detected!"
- ✅ Adjusts one bounding box that was too tight
- ✅ Deletes a false positive (page number detected as "icon")

**Step 5: Output Review**
- ⚠️ Notices LaTeX equations are being re-OCR'd instead of preserved
- ❓ *"Wait, my original had perfect LaTeX. Why is it re-scanning?"*
- 😤 *"It introduced errors in my integral notation!"*

**Step 6: Looking for Options**
- ❌ **STUCK** — No "preserve original LaTeX" option
- ❓ *"Can I just mark regions as 'already accessible'?"*

### Pain Points Identified:
1. **No source format detection** — Treats clean LaTeX PDFs same as handwritten
2. **Unnecessary re-conversion** — OCR introduces errors in already-clean math
3. **No "pass-through" option** — Can't mark content as already accessible
4. **Power user wants more control** — Would like to see raw AI responses

---

## 🟡 Persona 5: Sarah Mitchell (Geometry)

### Task: Convert PowerPoint with complex geometric constructions

**Step 1-4: Conversion**
- ✅ Upload successful
- ✅ Uses visual review to verify diagram detection

**Step 5: Alt-Text Quality**
- ❌ **DISAPPOINTED** — AI descriptions are vague
- AI says: *"A triangle with some lines"*
- She needs: *"Triangle ABC with altitude from C to AB, meeting at point D, with right angle marked at D"*
- 😤 *"This doesn't help a blind student understand the proof!"*

**Step 6: Manual Editing**
- ⚠️ Starts typing detailed descriptions in the review dialog
- ❌ **FRUSTRATED** — Text box is tiny (4 lines)
- ❌ Can't copy/paste her prepared descriptions easily
- ⏱️ Takes 45 minutes to describe 12 figures

**Step 7: Saving Work**
- ❓ *"What if I need to edit these later?"*
- ❌ Descriptions are embedded in HTML — no easy edit path

### Pain Points Identified:
1. **Geometry descriptions need precision** — Generic AI fails here
2. **Small text entry boxes** — Can't write detailed descriptions comfortably
3. **No import from file** — Can't paste pre-written descriptions
4. **No description template library** — Common shapes could have templates
5. **Locked after conversion** — Hard to revise descriptions later

---

## 🟡 Persona 6: Bob Kowalski (Pre-Calc Department Chair)

### Task: Evaluate tool for 12 teachers with varying tech skills

**Step 1: Installation Test**
- ✅ Runs on his machine
- ❌ **BLOCKED** — Won't run on teacher's Chromebook
- ❌ **BLOCKED** — IT won't install .exe without review (2 weeks)

**Step 2: Documentation Review**
- ✅ Finds README.md
- ⚠️ *"This assumes I know what LaTeX is. Half my department doesn't."*
- ❓ *"Where's the video tutorial?"*

**Step 3: Training Consideration**
- 😤 *"I'd need to train everyone. There's no in-app guidance."*
- ❓ *"Is there a simpler 'just make it accessible' mode?"*

**Step 4: Batch Processing Test**
- ❌ **STUCK** — Can only process one file at a time via GUI
- 😤 *"We have 200 PDFs to convert. This will take months!"*

**Step 5: Output Consistency**
- ⚠️ Converts same file twice, gets slightly different results
- ❓ *"Which version is 'correct'? My teachers will be confused."*

### Pain Points Identified:
1. **Platform limitations** — Windows-only excludes Chromebook teachers
2. **IT approval barriers** — .exe files flagged by school security
3. **No video tutorials** — Text docs insufficient for training
4. **No batch GUI** — Power users need bulk processing
5. **Non-deterministic output** — AI variations cause confusion
6. **No "simple mode"** — Too many options for basic users

---

## 🟡 Persona 7: Dr. Aisha Patel (AP Calculus)

### Task: Convert calculus notes with precise mathematical notation

**Step 1-4: Conversion**
- ✅ Experienced enough to navigate tool
- ✅ Uses visual review effectively

**Step 5: Mathematical Precision Check**
- ❌ **CRITICAL ERROR** — AI converted ∫₀^∞ as ∫₀^8
- ❌ Misread lim_{x→0} as lim_{x→0} (lost subscript)
- 😤 *"This would cost my student points on the AP exam!"*

**Step 6: Manual Correction**
- ⚠️ Can edit in HTML, but needs LaTeX source
- ❓ *"Can I see the LaTeX it generated so I can fix it?"*
- ❌ Only sees rendered MathJax, not source

**Step 7: Validation**
- ❓ *"How do I verify all equations are correct without reading every one?"*
- ❌ No "equation validation" or "compare to original" feature

### Pain Points Identified:
1. **OCR errors in complex notation** — Infinity vs 8, subscripts lost
2. **No LaTeX source view** — Can't debug equation errors
3. **No validation tool** — Can't compare converted vs original
4. **High stakes context** — Errors have real consequences (AP scores)
5. **No confidence scoring** — Doesn't flag "uncertain" conversions

---

## 🔴 Persona 8: Dr. James Morrison (University)

### Task: Convert multivariable calculus lecture slides (vector fields, 3D plots)

**Step 1: Looking for CLI**
- ❌ **FRUSTRATED** — Only GUI option
- 😤 *"I have 15 courses × 30 lectures. I'm not clicking through a GUI."*
- ❓ *"Where's the command-line interface?"*

**Step 2: Reluctantly Using GUI**
- ✅ Uploads first PDF
- ⚠️ Takes 8 minutes for 25-page document

**Step 3: 3D Visualization Problem**
- ❌ **CRITICAL** — AI cannot describe 3D vector fields meaningfully
- AI says: *"A colorful plot with arrows"*
- He needs: *"Vector field F(x,y,z) = (y, -x, z) shown in the region -2 ≤ x,y,z ≤ 2, with vectors colored by magnitude, demonstrating rotational flow around the z-axis"*

**Step 4: Giving Up on Auto-Description**
- 😤 *"I'll have to write all descriptions myself anyway."*
- ⚠️ Converts just to get structure, plans to edit HTML manually

**Step 5: LaTeX Integration**
- ❓ *"Can I just point it at my .tex source files instead of PDF?"*
- ❌ No LaTeX source input option

### Pain Points Identified:
1. **No CLI** — Unusable for batch academic workflows
2. **3D visualization failure** — AI can't describe complex mathematical plots
3. **Scale problem** — GUI doesn't scale to university course load
4. **No .tex input** — Forcing PDF conversion loses source fidelity
5. **Academic use case ignored** — Tool designed for K-12, not higher ed

---

---

## 📊 Summary: Top Friction Points by Frequency

| Pain Point | Personas Affected | Severity |
|------------|-------------------|----------|
| **Poppler dependency/installation** | 1, 3, 6 | 🔴 BLOCKER |
| **No batch/CLI processing** | 4, 6, 8 | 🔴 BLOCKER |
| **AI description quality for complex visuals** | 5, 7, 8 | 🔴 CRITICAL |
| **Jargon/intimidating UI for low-tech users** | 1, 3 | 🟡 HIGH |
| **Alt-text entry UX (small boxes, no import)** | 2, 5 | 🟡 HIGH |
| **No LaTeX source preservation/view** | 4, 7 | 🟡 HIGH |
| **Output file confusion** | 1, 2 | 🟡 MEDIUM |
| **No post-conversion editing workflow** | 2, 5, 7 | 🟡 MEDIUM |
| **Platform limitations (Windows-only)** | 6 | 🟡 MEDIUM |
| **Non-deterministic AI output** | 6 | 🟠 LOW |

---

## 🛠️ Recommended Fixes by Priority

### P0 — Blockers (Fix Before Release)
1. **Bundle Poppler** — Include in Windows installer, no separate download
2. **Simplify first-run** — Wizard that auto-configures dependencies
3. **Friendly error messages** — "Click here to fix" not "see .md file"

### P1 — Critical (Fix in v1.1)
1. **Add "Simple Mode"** — One-click "Make Accessible" hides all options
2. **Batch processing GUI** — Drag folder, process all files
3. **AI confidence indicators** — Flag equations/descriptions that need review
4. **Larger description text boxes** — Full editor with paste support

### P2 — High Priority (Fix in v1.2)
1. **CLI interface** — `mosh convert --input folder --output folder`
2. **LaTeX source view** — Toggle to see/edit raw LaTeX
3. **Description templates** — Pre-built templates for common shapes
4. **Post-conversion editor** — Dedicated UI for editing completed files

### P3 — Medium Priority (Future)
1. **Web version** — Cross-platform, no installation
2. **Video tutorials** — Embedded in-app guidance
3. **.tex file input** — Direct LaTeX processing
4. **Equation validator** — Side-by-side original vs converted

---

## 💡 Quick Wins (< 1 Day Each)

1. ✅ Rename "Math Magic" → "PDF & Math Converter" (clearer)
2. ✅ Change "Use AI Boxes As-Is" → "Accept & Continue"  
3. ✅ Add "What is this?" tooltips to visual review dialog
4. ✅ Show "Upload this file to Canvas →" with arrow pointing to .html
5. ✅ Add progress message: "Converting page 3 of 12..."
6. ✅ Make visual review dialog title friendlier: "Review Detected Images"

---

*Document generated from simulated user testing - March 2026*

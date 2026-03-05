# RC62 Synthetic Persona UI Test Report

Date: 2026-03-04  
Scope: Teacher workflow in the MOSH ADA Toolkit (math conversion, visual box review, setup toggles, mirror mode)

## Method
This is a **simulated user test** using 8 realistic teacher personas (no live participants).  
Each persona ran the same core tasks:
1. Open setup and choose workflow options.
2. Run math conversion from PDF/canvas export.
3. Use visual selection review (add/select/resize/delete boxes).
4. Regenerate alt text after a box adjustment.
5. Continue page-by-page flow and complete upload.
6. Validate mirror mode persistence on restart.

Severity scale: Critical / High / Medium / Low

---

## Persona Set (8)

1. **Ms. Rivera** — Grade 3 math intervention
   - Device/context: 13" laptop, non-technical, time-constrained pull-out sessions.
   - Priority: speed and simple wording.

2. **Mr. Patel** — Grade 5 general math
   - Device/context: classroom desktop, frequent interruptions, tab-switching.
   - Priority: resilience to context switching.

3. **Ms. Johnson** — Grade 6 pre-algebra
   - Device/context: district-issued Windows laptop, moderate technical comfort.
   - Priority: predictable next-step flow.

4. **Mr. Nguyen** — Grade 8 algebra
   - Device/context: dual-monitor setup, high volume worksheets.
   - Priority: keyboard efficiency and batch throughput.

5. **Ms. Chen** — Geometry (grade 9)
   - Device/context: many diagrams and nested labels.
   - Priority: accurate region selection and overlap handling.

6. **Mr. Alvarez** — Algebra II (grade 10)
   - Device/context: advanced symbolic expressions, arrows, multi-column pages.
   - Priority: transcription continuity and correctness.

7. **Ms. O’Connor** — AP Precalculus (grade 11)
   - Device/context: fine-grained formatting expectations.
   - Priority: confidence checks before publishing.

8. **Dr. Shah** — Calculus (grade 12)
   - Device/context: power user, strict ADA standards.
   - Priority: auditability and explicit status signals.

---

## Simulated Walkthrough Findings

### 1) Ambiguous action ordering in visual review
- Observed by: Personas 1, 3, 6
- Issue: Users hesitated between “Process Next Page” and other controls because they expected a stronger “primary next” visual cue.
- Severity: **High**
- Recommendation:
  - Make one dominant primary CTA (color/placement).
  - Keep secondary actions grouped in a separate panel section.

### 2) Add Box mode state can be forgotten
- Observed by: Personas 1, 2, 5
- Issue: Users entered Add Box mode, then tried selecting existing boxes and were confused when behavior differed.
- Severity: **High**
- Recommendation:
  - Persistent mode badge near cursor or title (e.g., “ADD BOX MODE ON”).
  - Auto-timeout back to Select mode after one box creation (optional toggle).

### 3) Discoverability gap for AI alt refresh
- Observed by: Personas 2, 4, 7
- Issue: Users resized boxes but did not immediately notice the “Refresh Alt (AI)” action.
- Severity: **High**
- Recommendation:
  - Trigger inline prompt after resize: “Region changed. Refresh description?”
  - Add changed-state indicator on selected box details.

### 4) Confidence/status messaging during long AI actions
- Observed by: Personas 1, 4, 8
- Issue: Temporary uncertainty (“Did it freeze?”) when regeneration/conversion takes several seconds.
- Severity: **Medium**
- Recommendation:
  - Show explicit progress state (“Analyzing selected region…”) with spinner and cancellable option.

### 5) Keyboard-only usage friction
- Observed by: Personas 4, 8
- Issue: Power users looked for shortcuts (next page, delete box, refresh alt) and lost time with mouse-only flow.
- Severity: **Medium**
- Recommendation:
  - Add hotkeys: `N` (next page), `Del` (delete box), `R` (refresh alt), `A` (add mode), `Esc` (exit add mode).

### 6) Setup toggles need stronger plain-language help
- Observed by: Personas 1, 3
- Issue: “Responsive” and “Final ADA check” meanings were partly unclear without hover/help text.
- Severity: **Medium**
- Recommendation:
  - Add one-line helper text below each toggle with expected time/quality tradeoff.

### 7) Mirror mode start state confirmation could be clearer
- Observed by: Personas 2, 8
- Issue: Users wanted immediate startup confirmation that mirror restored successfully.
- Severity: **Medium**
- Recommendation:
  - Show startup toast: “Mirror mode restored: ON (watching folder …)”.

### 8) Multi-column/arrow continuation trust remains fragile
- Observed by: Personas 6, 7
- Issue: Users still expect occasional continuity misses in complex pages and want a fast correction loop.
- Severity: **Medium**
- Recommendation:
  - Add optional “continuation confidence” marker on generated segments requiring review.

### 9) Error recovery language for failed uploads
- Observed by: Personas 2, 3
- Issue: If upload fails, users need explicit “what next” steps and retry context.
- Severity: **High**
- Recommendation:
  - Structured error panel: cause, last successful step, retry button, and safe fallback export path.

### 10) Dense controls on smaller displays
- Observed by: Personas 1, 3
- Issue: On smaller screens, users reported cognitive load from many controls in one panel.
- Severity: **Medium**
- Recommendation:
  - Progressive disclosure: basic controls first, advanced controls collapsible.

---

## Prioritized UI Backlog (Top 8)

1. **Primary CTA hierarchy cleanup** (High)
2. **Add Box mode persistent status + optional auto-exit** (High)
3. **Post-resize AI refresh prompt** (High)
4. **Upload error recovery panel with retry** (High)
5. **Long-action progress feedback + cancel affordance** (Medium)
6. **Keyboard shortcuts for review operations** (Medium)
7. **Plain-language helper text for setup toggles** (Medium)
8. **Mirror startup restored-state toast** (Medium)

---

## Suggested Validation Script for Next Round
Use this short script with real users (10–12 minutes each):
1. Turn on manual visual selection and run a 2-page sample.
2. Add one missing box.
3. Resize one existing box.
4. Refresh AI alt text.
5. Process next page and complete upload.
6. Close/reopen app and confirm mirror state.

Success criteria:
- No task needs facilitator intervention.
- Users can describe what each primary button does.
- Users can complete full flow in <= 8 minutes for 2 pages.

---

## Conclusion
The current RC62 workflow is substantially improved for teacher-led control, but the next UX gains are mostly in **state visibility**, **action hierarchy**, and **recovery clarity**. The highest-value immediate win is an explicit changed-region prompt that guides users to run AI alt refresh after box edits.
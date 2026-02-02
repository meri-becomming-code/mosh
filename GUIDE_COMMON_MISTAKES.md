# 🚨 April 2026 ADA Compliance: "Gotchas" & Solutions
**Unanticipated Challenges for Higher Education**

Research into university discussions and legal analysis reveals several common pitfalls ("gotchas") that institutions often miss until it's too late.

## 1. The "Third-Party" Trap
**Gotcha:** Many assume *all* external content is exempt.
**Reality:** The exception is NARROW.
*   **Exempt:** A student posting a link to a random article in a forum.
*   **NOT Exempt:** A professor posting a link to a YouTube video as required coursework. If you assign it, YOU own the accessibility.
*   **The Fix:** You must provide captions/transcripts for *any* third-party media you assign, or choose accessible alternatives.

## 2. The "Archived" Content Confusion
**Gotcha:** "I'll just move my old courses to an 'Archive' folder."
**Reality:** To be legally "archived" and exempt, content must meet 4 strict criteria:
1.  Created before April 2026.
2.  Retained *exclusively* for recordkeeping (not used for active class reference).
3.  Stored in a designated "Archive" area.
4.  **NEVER MODIFIED** after archiving.
*   **The Fix:** If you copy an old course to teach it again, it is **ACTIVE**, not archived. It must be fully remediated.

## 3. The "Decentralized" Nightmare
**Gotcha:** "The LMS (Canvas) is accessible, so we are fine."
**Reality:** The *platform* is accessible, but the *content* (your PDFs, Word docs, PPT slides, Images) often is not.
*   **Risk:** Faculty-created syllabus PDFs are the #1 target for lawsuits.
*   **The Fix:** 
    *   Stop using PDFs for syllabi; use Canvas Pages (HTML).
    *   Stop uploading Word docs; copy the text into Canvas Pages.

## 4. Social Media & Passwords
*   **Social Media:** Any post by a department (e.g., "Math Dept Facebook") created after the deadline MUST have alt text and captions.
*   **Password Protection:** Putting content behind a login (Canvas) does **NOT** exempt it. If it's for students/employees, it must be accessible.

## 5. STEM & Math (The Hardest Part)
**Gotcha:** "Math engines can't be made accessible."
**Reality:** They can, and legal precedent (Title II) demands it.
*   **The Fix:** As planned, moving from PDF Images -> Native Canvas LaTeX (`$$...$$`) is the best defense.

---
**Does this align with your current strategy?**
Our toolkit (`remediate_master_v3.py`) solves #3 and #5 by fixing HTML/Canvas content. Issue #1 (Third Party) requires policy changes, not just code.

# 🎨 Universal High-Contrast Design Framework (2026 Edition)
**Standardized CSS for ADA-Compliant (WCAG 2.1 AA) Canvas Courses**

This guide ensures your course meets the **April 2026 Federal Mandate**.

---

## 📱 1. Mobile Reflow (Critical Update)
**The Law:** Content must fit on a 320px wide screen without horizontal scrolling.
**The Fix:**
*   **NEVER** use pixel widths (`width: 800px`).
*   **ALWAYS** use `max-width` or percentages.
*   The `remediate_master_v3.py` script automatically injects the required `<meta name="viewport">` tag.

---

## 🔠 2. Typography & Readability
*   **No "Justified" Text:** Never use `text-align: justify`. It creates uneven spacing that hurts users with Dyslexia. Use `text-align: left`.
*   **Font Size:** Minimum **16px** for body text.
*   **Line Height:** Minimum **1.5** for readability.

---

## 📐 3. Math & Formulas (Canvas Native)
**Do NOT upload PDFs of math.** They are not accessible.

### Recommended: Native LaTeX
Let Canvas handle the heavy lifting. Use these standard delimiters:
*   **Inline (inside a sentence):** `\( a^2 + b^2 = c^2 \)`
*   **Block (centered equation):** `$$ a^2 + b^2 = c^2 $$`

Canvas will automatically convert these to accessible MathML/MathJax.

---

## 🧱 4. The Global Container
**Why:** Prevents text from stretching across wide monitors and ensures a clean white background.

```html
<div lang="en" style="background-color: #ffffff; border: 1px solid #e0e0e0; max-width: 1100px; margin: auto; border-radius: 10px; overflow: hidden; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
    <!-- All page content goes here -->
</div>
```

---

## 💻 5. The Code Block Standard (Deep Obsidian)
**Why:** Prevents "White-Text-on-White-Background" issues in Dark Mode.

### The Wrapper (Mobile Protection)
Always wrap `<pre>` tags in a scrollable div.
```html
<div style="overflow-x: auto;">
    <pre style="background-color: #121212; color: #ffffff; padding: 15px; border-radius: 5px; font-family: 'Courier New', monospace;">
<span style="color: #8ecafc;"># Comment</span>
print(<span style="color: #a6e22e;">"Hello"</span>)
    </pre>
</div>
```

**Syntax Palette:**
*   **Comments:** `#8ecafc` (Sky Blue)
*   **Strings:** `#a6e22e` (Emerald)
*   **Numbers:** `#fd971f` (Orange)
*   **Booleans:** `#ae81ff` (Purple)

---
*Maintained by the 508 Remediation Team | McHenry County College*

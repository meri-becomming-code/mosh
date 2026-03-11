import os
import re
import colorsys
from bs4 import BeautifulSoup, Comment, NavigableString

# --- Configuration: "Deep Obsidian" Code Theme ---
COLOR_BG_DARK = "#121212"
COLOR_TEXT_WHITE = "#ffffff"
COLOR_COMMENT = "#8ecafc"  # Light Blue
COLOR_STRING = "#a6e22e"  # Green
COLOR_NUMBER = "#fd971f"  # Orange
COLOR_BOOLEAN = "#ae81ff"  # Purple
MCC_PURPLE = "#4b3190"
MCC_DEEP = "#2c1f5c"


# --- WCAG 2.1 Contrast Math ---
def hex_to_rgb(color_str):
    color_str = color_str.lower().strip()
    named_colors = {
        "white": "#ffffff",
        "black": "#000000",
        "red": "#ff0000",
        "blue": "#0000ff",
        "green": "#008000",
        "yellow": "#ffff00",
        "gray": "#808080",
        "grey": "#808080",
        "purple": "#800080",
        "orange": "#ffa500",
        "transparent": "inherit",
    }
    if color_str in named_colors:
        color_str = named_colors[color_str]
    if color_str == "inherit" or not color_str:
        return None

    hex_color = color_str.lstrip("#")
    try:
        if len(hex_color) == 3:
            hex_color = "".join([c * 2 for c in hex_color])
        if len(hex_color) != 6:
            return None
        # [FIX] Robustness: Ensure only hex digits are parsed
        if not all(c in "0123456789abcdef" for c in hex_color):
            return None
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return None


def get_luminance(rgb):
    rgb_linear = []
    for c in rgb:
        c = c / 255.0
        if c <= 0.03928:
            rgb_linear.append(c / 12.92)
        else:
            rgb_linear.append(((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * rgb_linear[0] + 0.7152 * rgb_linear[1] + 0.0722 * rgb_linear[2]


def get_contrast_ratio(hex1, hex2):
    rgb1 = hex_to_rgb(hex1)
    rgb2 = hex_to_rgb(hex2)
    if not rgb1 or not rgb2:
        return None
    lum1 = get_luminance(rgb1)
    lum2 = get_luminance(rgb2)
    return (max(lum1, lum2) + 0.05) / (min(lum1, lum2) + 0.05)


def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


def adjust_color_for_contrast(fg_hex, bg_hex, target_ratio=4.5):
    """Automatically darkens or lightens FG to meet target contrast against BG."""
    fg_rgb = hex_to_rgb(fg_hex)
    bg_rgb = hex_to_rgb(bg_hex)
    if not fg_rgb or not bg_rgb:
        return fg_hex

    bg_lum = get_luminance(bg_rgb)
    curr_fg_rgb = list(fg_rgb)

    # Decide direction: if BG is dark, lighten FG; if BG is light, darken FG
    direction = -5 if bg_lum > 0.5 else 5  # Step size

    for _ in range(51):  # Max 50 steps
        ratio = get_contrast_ratio(rgb_to_hex(curr_fg_rgb), bg_hex)
        if ratio and ratio >= target_ratio:
            return rgb_to_hex(curr_fg_rgb)

        # Move RGB values
        for i in range(3):
            curr_fg_rgb[i] = max(0, min(255, curr_fg_rgb[i] + direction))

    return "#000000" if bg_lum > 0.5 else "#ffffff"


def fix_emoji_accessibility(soup):
    """Wraps emojis in spans with role='img' and aria-label."""
    import unicodedata

    # Emoji regex (broad range)
    emoji_pattern = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)

    fixes = []
    # Find text nodes containing emojis
    for text_node in soup.find_all(string=True):
        # [FIX] Idempotency: skip if parent is already an emoji span or a <title> tag
        # (Canvas uses <title> strings verbatim for Module lists; HTML spans will break the UI).
        if text_node.parent.name in ["script", "style", "title"]:
            continue
        if text_node.parent.name == "span" and text_node.parent.get("role") == "img":
            continue

        matches = list(emoji_pattern.finditer(text_node))
        if matches:
            # We found emojis. We need to replace them with spans.
            # This is tricky with BeautifulSoup strings.
            # We'll build a new content list.
            new_contents = []
            last_idx = 0
            for match in matches:
                # Add preceding text
                new_contents.append(text_node[last_idx : match.start()])
                # Create emoji span
                emoji = match.group()
                try:
                    desc = unicodedata.name(emoji).title()
                except Exception:
                    desc = "Emoji"

                span = soup.new_tag("span", attrs={"role": "img", "aria-label": desc})
                span.string = emoji
                new_contents.append(span)
                last_idx = match.end()

            # Add remaining text
            new_contents.append(text_node[last_idx:])

            # Replace text node with new contents
            for content in reversed(new_contents):
                if content:  # Avoid empty strings
                    text_node.insert_after(content)
            text_node.extract()
            fixes.append(f"Accessible-wrapped {len(matches)} emojis")

    return fixes


def remediate_html_file(filepath):
    """
    MASTER REMEDIATION LOGIC (V3):
    1. Clean Strategy (Toolkit 1): Strips bad tags/styles without forcing layout.
    2. Code Strategy (Toolkit 2): Applies "Deep Obsidian" theme to code blocks.
    3. Structural Fixes: Tables, Headings, Images, Iframes.

    Returns: (remediated_html_str, fix_list)
    """
    fixes = []
    print(f"Processing {os.path.basename(filepath)}...")
    with open(filepath, "r", encoding="utf-8") as f:
        html_content = f.read()

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, "html.parser")

    # --- List Cleanup: Remove empty or fragmentary <li> and collapse empty lists ---
    for lst in soup.find_all(["ul", "ol"]):
        # Remove <li> that are empty or only whitespace/nbsp
        for li in list(lst.find_all("li")):
            txt = li.get_text(" ", strip=True)
            if (
                not txt
                or txt == "\u00a0"
                or txt.lower() in {"", " ", "&nbsp;", "\u00a0"}
            ):
                li.decompose()
        # If after cleanup, the list has no <li>, remove the list
        if not lst.find("li"):
            lst.decompose()

    # --- Encoding cleanup (common mojibake artifacts) ---
    # Example: "Â©" appears when UTF-8 content is mis-decoded as cp1252.
    mojibake_map = {
        "Â©": "©",
        "â€™": "’",
        "â€œ": "“",
        "â€": "”",
        "â€“": "–",
        "â€”": "—",
        "â€¦": "…",
        "ð¹": "🎥",
        "Â": "",
    }
    # Entity-encoded mojibake observed in Canvas editor/source views.
    mojibake_entity_map = {
        "&Acirc;&nbsp;": "&nbsp;",
        "&acirc;&nbsp;": "&nbsp;",
        "&Acirc;&copy;": "&copy;",
        "&acirc;&copy;": "&copy;",
        "&eth;&sup1;": "🎥",
    }
    replaced_any_mojibake = False
    for bad, good in mojibake_map.items():
        if bad in html_content:
            html_content = html_content.replace(bad, good)
            replaced_any_mojibake = True
    for bad, good in mojibake_entity_map.items():
        if bad in html_content:
            html_content = html_content.replace(bad, good)
            replaced_any_mojibake = True

    # Common broken range marker from mis-decoded en-dash (e.g., "15â30").
    html_content = re.sub(r"(\d)â(\d)", r"\1–\2", html_content)
    if replaced_any_mojibake:
        fixes.append("Normalized mis-encoded UTF-8 characters (mojibake)")

    # --- Part 1: Cleanup (Toolkit 1 Logic) ---
    # Strip <font> tags but keep content
    # [REMOVED] Destructive stripping. Handled in Part 8 via BeautifulSoup to preserve info.
    # html_content = re.sub(r'<font[^>]*>(.*?)</font>', r'\1', html_content, flags=re.IGNORECASE | re.DOTALL)

    # REGEX REMOVED: Do not strip inline colors globally.
    # html_content = re.sub(r'(?:background-)?color:\s*#(?:000|fff|333|666|000000|ffffff|333333|666666);?', '', html_content, flags=re.IGNORECASE)

    # Strip Justified Text (Panorama / Dyslexia Fix)
    html_content = re.sub(
        r"text-align:\s*justify;?",
        "text-align: left;",
        html_content,
        flags=re.IGNORECASE,
    )

    # Note: The regex now uses (?<!-) lookbehind to avoid matching max-width/min-width

    # REGEX REMOVED: Do not globally force width: 100%. Handled cleanly in BeautifulSoup.

    # UX Update: Widen containers per user request
    html_content = html_content.replace("max-width: 1100px", "max-width: 1200px")
    html_content = html_content.replace("max-width: 800px", "max-width: 950px")

    # Check for legacy shorthands

    # Check for legacy shorthands (REMOVED: Dangerous collisions with #ffffff)
    # html_content = html_content.replace('background-fff', '').replace('background-f;', '').replace('fff;', '')

    # --- Part 1: Pre-Soup Regex Fixes (Reflow/Mobile) ---
    # [FIX] Track if we actually changed anything
    reflow_fixed = False

    def width_replacer(match):
        nonlocal reflow_fixed
        val = int(match.group(1))
        if val > 320:
            reflow_fixed = True
            return f"width: 100%; max-width: {val}px"
        return match.group(0)

    # Transform
    html_content = re.sub(
        r"(?<!-)width:\s*(\d+)px", width_replacer, html_content, flags=re.IGNORECASE
    )

    if reflow_fixed:
        fixes.append("Converted fixed widths >320px to responsive max-width")

    # Fix 3: Font Size Remediation (align with strict checker thresholds)
    def font_size_bump(match):
        nonlocal reflow_fixed
        val = float(match.group(1))
        unit = match.group(2)
        if unit == "px" and val < 12:
            return "font-size: 14px"
        elif unit == "pt" and val < 9:
            return "font-size: 10.5pt"  # ~14px
        elif unit == "em" and val < 0.9:
            return "font-size: 0.95em"
        elif unit == "rem" and val < 0.9:
            return "font-size: 0.95rem"
        return match.group(0)

    html_content = re.sub(
        r"font-size:\s*([0-9.]+)(px|pt|em|rem)",
        font_size_bump,
        html_content,
        flags=re.IGNORECASE,
    )

    soup = BeautifulSoup(html_content, "html.parser")

    # [FIX] Revert any emoji span wrappers inside <title> tags from previous passes
    # to prevent Canvas UI corruption when imported.
    for title_tag in soup.find_all("title"):
        for span in title_tag.find_all("span", attrs={"role": "img"}):
            span.unwrap()
            fixes.append("Reverted broken HTML from <title> tag")

    # --- Part 2: Document Structure ---
    # Ensure valid html/head/body skeleton for fragments, then enforce viewport.
    if not soup.find("html"):
        html_tag = soup.new_tag("html")
        body_tag = soup.new_tag("body")
        for element in list(soup.contents):
            body_tag.append(element.extract())
        html_tag.append(body_tag)
        soup.append(html_tag)
        fixes.append("Wrapped HTML fragment in <html><body>")

    if not soup.find("body"):
        html_tag = soup.find("html")
        body_tag = soup.new_tag("body")
        for element in list(html_tag.contents):
            if getattr(element, "name", None) != "head":
                body_tag.append(element.extract())
        html_tag.append(body_tag)
        fixes.append("Created missing <body> element")

    head = soup.find("head")
    if not head:
        html_tag = soup.find("html")
        head = soup.new_tag("head")
        html_tag.insert(0, head)
        fixes.append("Created missing <head> element")

    if head:
        meta_charset = head.find("meta", attrs={"charset": True})
        if not meta_charset:
            # Place charset first in head when possible.
            new_charset = soup.new_tag("meta", attrs={"charset": "utf-8"})
            if head.contents:
                head.insert(0, new_charset)
            else:
                head.append(new_charset)
            fixes.append("Added UTF-8 charset meta tag")

        meta_viewport = head.find("meta", attrs={"name": "viewport"})
        if not meta_viewport:
            new_meta = soup.new_tag(
                "meta",
                attrs={
                    "name": "viewport",
                    "content": "width=device-width, initial-scale=1",
                },
            )
            head.append(new_meta)
            fixes.append("Added mobile viewport meta tag")

        # Enforce safe responsive image policy without upscaling.
        css_rule = (
            ".main-content img { width: 50%; max-width: 50%; height: auto !important; }\n"
            ".slide-container img { width: 50%; max-width: 50%; height: auto !important; }\n"
            "@media (max-width: 768px) { .main-content img, .slide-container img { width: 100% !important; max-width: 100% !important; float: none !important; } }"
        )
        existing_css = "\n".join((st.get_text() or "") for st in head.find_all("style"))
        if ".slide-container img" not in existing_css:
            st = soup.new_tag("style")
            st.string = css_rule
            head.append(st)
            fixes.append("Added slide image responsive CSS policy")

    # [NEW] Structural Integrity: Ensure the body contains exactly one main-content div,
    # and all other content is moved inside it.
    main_div = soup.find("div", class_="main-content")
    if not main_div:
        main_div = soup.find("div", attrs={"lang": True})

    if main_div:
        # Move any siblings of main_div into it (to prevent "leaking" outside)
        siblings = [s for s in main_div.parent.contents if s != main_div]
        for s in siblings:
            if hasattr(s, "name") and s.name in [
                "script",
                "style",
                "head",
                "meta",
                "link",
            ]:
                continue
            main_div.append(s.extract())
    else:
        # Create a wrapper if none exists
        new_div = soup.new_tag("div", class_="main-content")
        if soup.body:
            for element in list(soup.body.contents):
                new_div.append(element.extract())
            soup.body.append(new_div)
        else:
            for element in list(soup.contents):
                new_div.append(element.extract())
            soup.append(new_div)
        main_div = new_div

    if main_div and not main_div.has_attr("lang"):
        # Check if <html> has a lang we can copy
        html_lang = soup.html.get("lang") if soup.html else None
        if html_lang:
            main_div["lang"] = html_lang
            fixes.append(f"Applied language '{html_lang}' to main container")
        else:
            main_div["lang"] = "en"
            fixes.append("Applied default language 'en' to main container")

    # --- Part 4: "Deep Obsidian" Code & Standardized Math ---

    # A. Code Blocks
    for pre in soup.find_all("pre"):
        # Move code blocks out of inline/text containers so they stand alone.
        parent = pre.parent
        if parent and parent.name in [
            "p",
            "span",
            "strong",
            "em",
            "a",
            "li",
            "dd",
            "dt",
        ]:
            parent.insert_before(pre.extract())
            if not parent.get_text(strip=True) and not parent.find(
                ["img", "iframe", "table", "ul", "ol"]
            ):
                parent.decompose()
            fixes.append("Moved code block out of inline/text container")

        # Convert old paragraph spacers from prior versions to line breaks.
        if pre.previous_sibling is not None and hasattr(pre.previous_sibling, "name"):
            prev_el = pre.previous_sibling
            if prev_el.name == "p" and "code-spacing" in (prev_el.get("class") or []):
                prev_el.replace_with(soup.new_tag("br"))
                fixes.append(
                    "Replaced old paragraph spacer above code block with line break"
                )

        if pre.next_sibling is not None and hasattr(pre.next_sibling, "name"):
            next_el = pre.next_sibling
            if next_el.name == "p" and "code-spacing" in (next_el.get("class") or []):
                next_el.replace_with(soup.new_tag("br"))
                fixes.append(
                    "Replaced old paragraph spacer below code block with line break"
                )

        # Ensure there is a line break above the code block.
        prev_node = pre.previous_sibling
        while (
            prev_node is not None
            and isinstance(prev_node, NavigableString)
            and not str(prev_node).strip()
        ):
            prev_node = prev_node.previous_sibling
        if not (hasattr(prev_node, "name") and prev_node.name == "br"):
            pre.insert_before(soup.new_tag("br"))
            fixes.append("Added line break above code block")

        # Ensure there is a line break below the code block.
        next_node = pre.next_sibling
        while (
            next_node is not None
            and isinstance(next_node, NavigableString)
            and not str(next_node).strip()
        ):
            next_node = next_node.next_sibling
        if not (hasattr(next_node, "name") and next_node.name == "br"):
            pre.insert_after(soup.new_tag("br"))
            fixes.append("Added line break below code block")

        parent = pre.parent
        if parent.name != "div" or "overflow" not in parent.get("style", "").lower():
            new_wrapper = soup.new_tag(
                "div", style="overflow-x: auto; margin-bottom: 20px;"
            )
            pre.wrap(new_wrapper)

        # Apply Deep Obsidian theme - but check if already styled (idempotency)
        current_style = pre.get("style", "").lower()
        already_styled = COLOR_BG_DARK.lower() in current_style

        if not already_styled:
            pre["style"] = (
                f"background-color: {COLOR_BG_DARK}; "
                f"color: {COLOR_TEXT_WHITE}; "
                "padding: 15px; "
                "border-radius: 5px; "
                "font-family: 'Courier New', monospace; "
                "white-space: pre;"
            )
            fixes.append("Applied 'Deep Obsidian' theme to code block")

        for span in pre.find_all("span"):
            text = span.get_text().strip()

            is_docstring = text.startswith('"""') or text.startswith("'''")
            is_comment = text.startswith("#") or (
                span.get("style") and "italic" in span["style"]
            )
            is_string = (
                text.startswith('"') or text.startswith("'")
            ) and not is_docstring
            is_number = text.replace(".", "", 1).isdigit()
            is_bool = text in ["True", "False", "None"]

            new_color = None
            if is_docstring:
                new_color = COLOR_STRING
            elif is_comment:
                new_color = COLOR_COMMENT
            elif is_string:
                new_color = COLOR_STRING
            elif is_number:
                new_color = COLOR_NUMBER
            elif is_bool:
                new_color = COLOR_BOOLEAN

            if new_color:
                span["style"] = f"color: {new_color};"
            else:
                # Ensure no other colors interfere
                if "color" in span.get("style", ""):
                    del span["style"]

    # B. Math Standardization (Canvas Native)
    # Note: Regex replacements for LaTeX delimiters are safer done on strings BEFORE soup parsing,
    # OR we just assume if they exist, Canvas catches them.
    # We will just ensure that standard LaTeX is not mangled.
    # The current script doesn't mangle brackets, so we are good.

    # C. PPT text-box handling
    # Only force dark styling for code-like boxes. Normal instructional text boxes
    # should remain light/background-neutral.
    for box in soup.find_all("div", class_="text-box"):
        # Determine if this box is code-like.
        box_text = box.get_text(" ", strip=True).lower()
        has_code_tag = bool(box.find(["pre", "code"]))
        has_monospace = False
        for node in box.find_all(True):
            s = (node.get("style", "") or "").lower()
            if "font-family" in s and any(
                ff in s for ff in ["consolas", "courier", "monospace", "lucida console"]
            ):
                has_monospace = True
                break

        code_tokens = [
            "print(",
            "def ",
            "import ",
            "return ",
            "while ",
            "for ",
            "if ",
            "==",
            "!=",
            "\\n",
            "{",
            "}",
            "()",
        ]
        token_hits = sum(1 for tok in code_tokens if tok in box_text)
        is_code_box = has_code_tag or has_monospace or token_hits >= 2

        box_style = box.get("style", "")
        box_style_low = box_style.lower()

        if is_code_box:
            # Code panels: dark, brighter text, larger and bolder for readability.
            if "background-color" not in box_style_low:
                box_style = (
                    box_style.rstrip("; ") + f"; background-color: {COLOR_BG_DARK};"
                )
            else:
                box_style = re.sub(
                    r"background-color\s*:\s*[^;]+",
                    f"background-color: {COLOR_BG_DARK}",
                    box_style,
                    flags=re.IGNORECASE,
                )

            if "color" not in box_style_low:
                box_style = box_style.rstrip("; ") + f"; color: {COLOR_TEXT_WHITE};"
            else:
                # Important: only replace foreground color, not background-color.
                box_style = re.sub(
                    r"(?<!-)color\s*:\s*[^;]+",
                    f"color: {COLOR_TEXT_WHITE}",
                    box_style,
                    flags=re.IGNORECASE,
                )

            if "padding" not in box_style_low:
                box_style = box_style.rstrip("; ") + "; padding: 12px;"
            if "border-radius" not in box_style_low:
                box_style = box_style.rstrip("; ") + "; border-radius: 6px;"
            if "overflow-x" not in box_style_low:
                box_style = box_style.rstrip("; ") + "; overflow-x: auto;"
            if "font-size" not in box_style_low:
                box_style = box_style.rstrip("; ") + "; font-size: 1.05em;"
            if "line-height" not in box_style_low:
                box_style = box_style.rstrip("; ") + "; line-height: 1.6;"
            if "font-weight" not in box_style_low:
                box_style = box_style.rstrip("; ") + "; font-weight: 600;"

            box["style"] = box_style.strip().rstrip(";") + ";"
            fixes.append("Applied accessible dark theme to code-like text-box")

            # Ensure child text is readable on dark background.
            for child in box.find_all(["p", "span", "li", "code"]):
                child_style = child.get("style", "")
                low = child_style.lower()
                if "color" not in low:
                    child["style"] = (
                        child_style.rstrip("; ")
                        + f"; color: {COLOR_TEXT_WHITE}; font-weight: 600;"
                    ).strip().rstrip(";") + ";"
                else:
                    # Brighten dim grays often exported from PPT themes.
                    child["style"] = re.sub(
                        r"(?<!-)color\s*:\s*(#7d7d7d|#7e7e7e|#737373)",
                        "color: #d4d4d4",
                        child_style,
                        flags=re.IGNORECASE,
                    )
        else:
            # Normal text boxes: keep light and readable.
            # Remove accidental dark code background and white text carryover.
            if (
                "background-color" in box_style_low
                and COLOR_BG_DARK.lower() in box_style_low
            ):
                box_style = re.sub(
                    r"background-color\s*:\s*[^;]+",
                    "background-color: #ffffff",
                    box_style,
                    flags=re.IGNORECASE,
                )
            if re.search(
                r"(?<!-)color\s*:\s*(#fff|#ffffff|white)",
                box_style,
                flags=re.IGNORECASE,
            ):
                box_style = re.sub(
                    r"(?<!-)color\s*:\s*[^;]+",
                    "color: #1f2937",
                    box_style,
                    flags=re.IGNORECASE,
                )

            box["style"] = (
                box_style.strip().rstrip(";") + ";" if box_style.strip() else box_style
            )
            fixes.append("Preserved light styling for non-code text-box")

            # If descendants are forced white, bring them back to dark text on light bg.
            for child in box.find_all(["p", "span", "li"]):
                child_style = child.get("style", "")
                if re.search(
                    r"(?<!-)color\s*:\s*(#fff|#ffffff|white)",
                    child_style,
                    flags=re.IGNORECASE,
                ):
                    child["style"] = re.sub(
                        r"(?<!-)color\s*:\s*[^;]+",
                        "color: #1f2937",
                        child_style,
                        flags=re.IGNORECASE,
                    )

    # --- Part 5: Tables (AGGRESSIVE REMEDIATION) ---
    for table in soup.find_all("table"):
        # 0. [NEW] Remove completely empty tables (Accessibility & UI Cleanup)
        # Check if the table has any meaningful text content or images
        has_content = False
        for cell in table.find_all(["td", "th"]):
            if cell.get_text(strip=True) or cell.find("img"):
                has_content = True
                break

        if not has_content:
            fixes.append("Removed empty data table (no text or images found)")
            table.extract()
            continue

        # 1. Cleanup empty TBODYs
        for tb in table.find_all("tbody"):
            if not tb.find("tr"):
                fixes.append("Removed empty <tbody> tag")
                tb.extract()

        # 2. Caption (Mandatory for screen readers)
        if not table.find("caption"):
            caption = soup.new_tag("caption")
            caption["style"] = (
                "text-align: left; font-weight: bold; margin-bottom: 10px;"
            )
            caption.string = "Data Table"
            table.insert(0, caption)
            fixes.append("Added 'Data Table' caption to table")

        # 3. FORCE HEADERS (The most common error)
        thead = table.find("thead")
        if not thead:
            first_row = table.find("tr")
            if first_row:
                # Convert first row to a header row
                thead = soup.new_tag("thead")

                # [FIX] If the row is in a tbody, extract it first to avoid nesting thead inside tbody
                tbody = first_row.find_parent("tbody")
                if tbody:
                    first_row.extract()
                    tbody.insert_before(thead)
                else:
                    first_row.wrap(thead)

                thead.append(first_row)

                for cell in first_row.find_all("td"):
                    cell.name = "th"
                    cell["scope"] = "col"
                for th in first_row.find_all("th"):
                    th["scope"] = "col"
                fixes.append("Converted first row to proper <thead> header")

        # 4. Standardize Scopes (Canvas requirement)
        for th in table.find_all("th"):
            parent_section = th.find_parent(["thead", "tbody", "tfoot"])
            if parent_section and parent_section.name == "thead":
                # Headers in thead must be scope='col'
                if th.get("scope") != "col":
                    th["scope"] = "col"
                    fixes.append("Assigned WCAG scope='col' to thead header")
            elif not th.has_attr("scope"):
                # First cell of a body row = row header
                th["scope"] = "row"
                fixes.append("Assigned WCAG scope to table header")

        # 4.5 [NEW] Enforce Header Length (< 120 chars)
        for th in table.find_all("th"):
            th_text = th.get_text(strip=True)
            if len(th_text) > 120:
                short_text = th_text[:117] + "..."
                th.string = short_text
                fixes.append(
                    f"Truncated long table header ({len(th_text)} chars) to 120 max"
                )

        # 4.6 [NEW] Ensure TBODY exists and contains all non-thead rows
        all_tr = table.find_all("tr")
        body_rows = [tr for tr in all_tr if not tr.find_parent("thead")]

        tbody = table.find("tbody")
        if not tbody:
            tbody = soup.new_tag("tbody")
            # Insert tbody after thead if thead exists, else at start
            thead = table.find("thead")
            if thead:
                thead.insert_after(tbody)
            else:
                table.append(tbody)
            fixes.append("Created missing <tbody> tag")

        if body_rows:
            # Move all body rows into the tbody if they aren't already
            for tr in body_rows:
                if tr.parent != tbody:
                    tbody.append(tr.extract())
                    fixes.append("Moved stray row into <tbody>")
        else:
            # If there's absolutely no data rows, Panorama complains "missing body content".
            # Some authors create tables with just a single header row.
            empty_tr = soup.new_tag("tr")
            empty_td = soup.new_tag("td")
            empty_tr.append(empty_td)
            tbody.append(empty_tr)
            fixes.append("Added empty row to missing <tbody> to satisfy validator")

        if not table.has_attr("border"):
            table["border"] = "1"
        if "border-collapse" not in table.get("style", ""):
            table["style"] = (
                table.get("style", "") + " border-collapse: collapse; min-width: 50%;"
            )

        # 6. Mobile Reflow Check (UX)
        # If table has more than 5 columns or fixed width, warn or wrap
        col_count = 0
        first_row = table.find("tr")
        if first_row:
            col_count = len(first_row.find_all(["td", "th"]))

        if col_count > 4:
            # Wrap in a scrollable div for mobile
            if not (
                table.parent.name == "div"
                and "overflow-x" in table.parent.get("style", "")
            ):
                wrapper = soup.new_tag(
                    "div",
                    style="overflow-x: auto; -webkit-overflow-scrolling: touch; margin-bottom: 20px; border: 1px solid #eee; padding: 5px;",
                )
                table.wrap(wrapper)
                fixes.append(
                    f"Added horizontal scroll wrapper for wide table ({col_count} columns)"
                )

    # --- Part 6: Heading Hierarchy & Standardization (Toolkit 1 Logic + Style Standard) ---

    # Enforce MCC purple heading bars for PPT slide titles.
    for h2 in soup.find_all("h2"):
        in_slide = bool(h2.find_parent("div", class_="slide-container")) or (
            "slide-title" in (h2.get("class") or [])
        )
        if in_slide:
            h2_style = h2.get("style", "")
            low = h2_style.lower()

            if "background-color" in low:
                h2_style = re.sub(
                    r"background-color\s*:\s*[^;]+",
                    "background-color: #4b3190",
                    h2_style,
                    flags=re.IGNORECASE,
                )
            else:
                h2_style = h2_style.rstrip("; ") + "; background-color: #4b3190;"

            if re.search(r"(?<!-)color\s*:", h2_style, flags=re.IGNORECASE):
                h2_style = re.sub(
                    r"(?<!-)color\s*:\s*[^;]+",
                    "color: #ffffff",
                    h2_style,
                    flags=re.IGNORECASE,
                )
            else:
                h2_style = h2_style.rstrip("; ") + "; color: #ffffff;"

            if "padding" not in h2_style.lower():
                h2_style = h2_style.rstrip("; ") + "; padding: 2%;"
            if "border-radius" not in h2_style.lower():
                h2_style = h2_style.rstrip("; ") + "; border-radius: 6px;"

            h2["style"] = h2_style.strip().rstrip(";") + ";"
            fixes.append("Applied MCC purple heading style to slide H2")

    # Standardize Header Taglines (Style 13A: Tagline Underneath)
    # Target: div[bg=#4b3190] > h2 + p[color=#e1bee7]
    for h2 in soup.find_all("h2"):
        parent = h2.parent
        # Check if parent is the dark purple header container
        # [FIX] Explicitly ignore slide-container to prevent breaking PPT layout
        if (
            parent.name == "div"
            and "slide-container" not in parent.get("class", [])
            and "background-color" in parent.get("style", "").lower()
            and "#4b3190" in parent["style"].lower()
        ):
            # Check if next sibling is a paragraph (the tagline)
            tagline = h2.find_next_sibling("p")
            if tagline:
                # [SAFETY FIX] Don't move tagline if it would exit its slide container
                grandparent = parent.parent
                is_in_slide = grandparent and "slide-container" in grandparent.get(
                    "class", []
                )

                # Move tagline OUT of the small header div, but keep it in the slide
                tagline.extract()
                if is_in_slide:
                    # Insert at the end of the slide container instead of after the parent div
                    grandparent.append(tagline)
                else:
                    parent.insert_after(tagline)

                # Apply 13A Style (Dark Purple, Italic, Margin)
                tagline["style"] = (
                    "margin-top: 10px; margin-left: 15px; font-style: italic; color: #4b3190;"
                )
                fixes.append("Refactored header tagline for better contrast and layout")

    # 1. Clear old warnings
    for comment in soup.find_all(
        string=lambda text: isinstance(text, Comment) and "ADA FIX" in text
    ):
        comment.extract()

    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    if not headings:
        # Insert H2 if missing
        title_tag = soup.find("title")
        title_text = title_tag.get_text() if title_tag else "Course Content"
        new_h2 = soup.new_tag("h2")
        new_h2.string = title_text
        if main_div:
            main_div.insert(0, new_h2)
            fixes.append(f"Inserted H2 header: '{title_text}'")
        headings = [new_h2]

    # 2. Leveling
    if headings:
        # Canvas uses H1 for page title, so content should start at H2
        first_level = int(headings[0].name[1])
        if first_level > 2:
            old_tag = headings[0].name
            headings[0].name = "h2"
            headings[0].insert_before(Comment(f"ADA FIX: Forced {old_tag} to H2"))
            fixes.append(
                f"Forced header '{headings[0].get_text()[:30]}' from {old_tag} to H2"
            )
            last_level = 2
        else:
            last_level = first_level

        for h in headings[1:]:
            current_level = int(h.name[1])
            if current_level > last_level + 1:
                # Skipped a level (e.g., H2 -> H4)
                new_level = last_level + 1
                old_tag = h.name
                h.name = f"h{new_level}"
                fixes.append(
                    f"Fixed heading gap: Demoted '{h.get_text()[:30]}' to H{new_level}"
                )
            last_level = int(h.name[1])

    # 3. Make headings span full row (especially near floated images).
    for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        h_style = h.get("style", "")
        low = h_style.lower()

        if "display:" not in low:
            h_style = h_style.rstrip("; ") + "; display: block;"
        if "width:" not in low:
            h_style = h_style.rstrip("; ") + "; width: 100%;"
        if "clear:" not in low:
            h_style = h_style.rstrip("; ") + "; clear: both;"

        # Prevent right-edge overflow when headings have width:100% + padding.
        # border-box keeps total rendered width inside container.
        if "box-sizing" not in low:
            h_style = h_style.rstrip("; ") + "; box-sizing: border-box;"
        elif "box-sizing:border-box" not in low.replace(" ", ""):
            h_style = re.sub(
                r"box-sizing\s*:\s*[^;]+;?",
                "box-sizing: border-box;",
                h_style,
                flags=re.IGNORECASE,
            )

        h["style"] = h_style.strip().rstrip(";") + ";"

        # If immediately followed by inline content/text, add a break paragraph
        # to force visual line separation.
        nxt = h.next_sibling
        while (
            nxt is not None
            and isinstance(nxt, NavigableString)
            and not str(nxt).strip()
        ):
            nxt = nxt.next_sibling

        if isinstance(nxt, NavigableString) and str(nxt).strip():
            spacer = soup.new_tag("p", attrs={"class": "heading-break"})
            spacer.string = "\u00a0"
            h.insert_after(spacer)
            fixes.append("Added break paragraph after heading")
        elif hasattr(nxt, "name") and nxt.name in ["span", "a", "em", "strong", "code"]:
            spacer = soup.new_tag("p", attrs={"class": "heading-break"})
            spacer.string = "\u00a0"
            h.insert_after(spacer)
            fixes.append("Added break paragraph after heading")

    # --- Part 7: Slide Containers + Images (Visual Markers & Responsiveness) ---
    # Global guardrail: ensure div wrappers can contain floats/media on all pages.
    # Only add when no explicit `overflow:` exists so we avoid clobbering intentional settings.
    for div in soup.find_all("div"):
        div_style = div.get("style", "") or ""
        if not re.search(r"(^|;)\s*overflow\s*:", div_style, flags=re.IGNORECASE):
            div["style"] = div_style.rstrip("; ") + "; overflow: auto;"
            fixes.append("Added overflow:auto to div wrapper")

    # Ensure top-level content wrappers do not overflow due to width:100% + padding.
    for wrapper in soup.find_all("div", class_="main-content"):
        w_style = wrapper.get("style", "") or ""
        w_low = w_style.lower()

        if "box-sizing" not in w_low:
            w_style = w_style.rstrip("; ") + "; box-sizing: border-box;"
            fixes.append("Added box-sizing:border-box to main-content")
        elif "box-sizing:border-box" not in w_low.replace(" ", ""):
            w_style = re.sub(
                r"box-sizing\s*:\s*[^;]+;?",
                "box-sizing: border-box;",
                w_style,
                flags=re.IGNORECASE,
            )
            fixes.append("Normalized main-content box-sizing:border-box")

        if "overflow-x" not in w_low:
            w_style = w_style.rstrip("; ") + "; overflow-x: hidden;"
            fixes.append("Added overflow-x:hidden to main-content")

        wrapper["style"] = w_style.strip().rstrip(";") + ";"

    # 7a. Enforce PPT slide container safety so content wraps and grows correctly.
    for div in soup.find_all("div", class_="slide-container"):
        style = div.get("style", "") or ""
        style_low = style.lower()

        # Ensure containers can grow with floated images/content.
        if "overflow" not in style_low:
            style = style.rstrip(";") + "; overflow: auto;"
            style_low = style.lower()
            fixes.append("Enforced slide-container overflow:auto")
        elif "overflow: auto" not in style_low:
            style = re.sub(
                r"overflow\s*:\s*[^;]+;?", "overflow: auto;", style, flags=re.IGNORECASE
            )
            style_low = style.lower()
            fixes.append("Normalized slide-container overflow:auto")

        if "display:" not in style_low:
            style = style.rstrip(";") + "; display: flow-root;"
            fixes.append("Enforced slide-container display:flow-root")
        elif "display: flow-root" not in style_low.replace("  ", " "):
            style = re.sub(
                r"display\s*:\s*[^;]+;?",
                "display: flow-root;",
                style,
                flags=re.IGNORECASE,
            )
            fixes.append("Normalized slide-container display:flow-root")

        if "clear:" not in style_low:
            style = style.rstrip(";") + "; clear: both;"
            fixes.append("Enforced slide-container clear:both")

        # Prevent width + padding + border from exceeding available width.
        if "box-sizing" not in style_low:
            style = style.rstrip(";") + "; box-sizing: border-box;"
            fixes.append("Enforced slide-container box-sizing:border-box")
        elif "box-sizing:border-box" not in style_low.replace(" ", ""):
            style = re.sub(
                r"box-sizing\s*:\s*[^;]+;?",
                "box-sizing: border-box;",
                style,
                flags=re.IGNORECASE,
            )
            fixes.append("Normalized slide-container box-sizing:border-box")

        # Horizontal overflow should be handled by internal wrappers/text boxes, not outer slide frame.
        if "overflow-x" not in style_low:
            style = style.rstrip(";") + "; overflow-x: hidden;"
            fixes.append("Enforced slide-container overflow-x:hidden")
        elif "overflow-x: hidden" not in style_low.replace("  ", " "):
            style = re.sub(
                r"overflow-x\s*:\s*[^;]+;?",
                "overflow-x: hidden;",
                style,
                flags=re.IGNORECASE,
            )
            fixes.append("Normalized slide-container overflow-x:hidden")

        if "width:" not in style_low:
            style = (
                style.rstrip(";")
                + "; width: 90%; margin-left: auto; margin-right: auto;"
            )
            fixes.append("Enforced slide-container width:90%")
        elif "width: 100%" in style_low or "width:100%" in style_low:
            style = re.sub(
                r"width\s*:\s*100%\s*;?", "width: 90%;", style, flags=re.IGNORECASE
            )
            if "margin-left" not in style.lower():
                style = style.rstrip(";") + "; margin-left: auto;"
            if "margin-right" not in style.lower():
                style = style.rstrip(";") + "; margin-right: auto;"
            fixes.append("Normalized slide-container width from 100% to 90%")

        # Avoid unexpectedly narrow PPT cards introduced by legacy fixed-width conversions.
        m_slide_max = re.search(
            r"max-width\s*:\s*([0-9.]+)px", style, flags=re.IGNORECASE
        )
        if m_slide_max:
            try:
                max_px = float(m_slide_max.group(1))
                if max_px <= 800:
                    style = re.sub(
                        r"max-width\s*:\s*[^;]+;?",
                        "max-width: 1200px;",
                        style,
                        flags=re.IGNORECASE,
                    )
                    fixes.append("Expanded slide-container max-width to 1200px")
            except Exception:
                pass

        div["style"] = style.strip()

        # If a slide contains both text and images, keep images beside text when possible.
        # Heuristic: when no float exists, infer side from content order.
        slide_imgs = div.find_all("img")
        has_text_blocks = bool(
            div.find_all(["p", "ul", "ol", "li", "div"], class_="text-box")
        ) or bool([p for p in div.find_all("p") if p.get_text(strip=True)])

        if has_text_blocks and slide_imgs:
            for img in slide_imgs:
                img_style = img.get("style", "") or ""
                img_style_low = img_style.lower()

                if "float:" in img_style_low:
                    continue

                # Determine nearest meaningful siblings to infer likely side.
                prev_sig = img.find_previous_sibling()
                next_sig = img.find_next_sibling()
                prev_has_text = bool(
                    prev_sig
                    and getattr(prev_sig, "get_text", None)
                    and prev_sig.get_text(strip=True)
                )
                next_has_text = bool(
                    next_sig
                    and getattr(next_sig, "get_text", None)
                    and next_sig.get_text(strip=True)
                )

                # If text is before image, float right; if text after image, float left.
                inferred_float = (
                    "right" if prev_has_text or not next_has_text else "left"
                )
                inferred_margin = (
                    "0 0 15px 20px" if inferred_float == "right" else "0 20px 15px 0"
                )

                # Keep side-by-side footprint bounded while remaining responsive.
                if "max-width" not in img_style_low:
                    img_style = img_style.rstrip("; ") + "; max-width: 40%;"
                img_style = (
                    img_style.rstrip("; ")
                    + f"; float: {inferred_float}; margin: {inferred_margin};"
                )
                img["style"] = img_style.strip().rstrip(";") + ";"
                fixes.append(
                    f"Positioned slide image beside text (float:{inferred_float})"
                )

    # 7a.1 Ensure image-hosting divs contain floats/width safely.
    for host_div in soup.find_all("div"):
        if not host_div.find("img"):
            continue

        h_style = host_div.get("style", "") or ""
        h_low = h_style.lower()
        host_updated = False

        if "overflow" not in h_low:
            h_style = h_style.rstrip("; ") + "; overflow: auto;"
            host_updated = True
        elif "overflow: auto" not in h_low.replace("  ", " "):
            h_style = re.sub(
                r"overflow\s*:\s*[^;]+;?",
                "overflow: auto;",
                h_style,
                flags=re.IGNORECASE,
            )
            host_updated = True

        if "display:" not in h_low:
            h_style = h_style.rstrip("; ") + "; display: flow-root;"
            host_updated = True

        if "box-sizing" not in h_low:
            h_style = h_style.rstrip("; ") + "; box-sizing: border-box;"
            host_updated = True

        if host_updated:
            host_div["style"] = h_style.strip().rstrip(";") + ";"
            fixes.append("Ensured overflow:auto on image-hosting div")

    image_extensions = [".png", ".jpg", ".jpeg", ".gif", ".svg"]

    # Preserve existing float behavior: if a paragraph only wraps one floated image,
    # unwrap the paragraph so surrounding content can flow naturally around the image.
    for p in soup.find_all("p"):
        children = [
            c
            for c in p.contents
            if not (isinstance(c, NavigableString) and not str(c).strip())
        ]
        if len(children) == 1 and getattr(children[0], "name", None) == "img":
            img_only = children[0]
            img_style = (img_only.get("style", "") or "").lower()
            if "float:" in img_style:
                p.insert_before(img_only.extract())
                p.decompose()
                fixes.append(
                    "Preserved floated image flow by removing paragraph wrapper"
                )

    # If a floated image lives inside a text block, contain it only for slide content.
    # For non-slide pages, we promote floated images outside wrapper blocks below so
    # text can flow naturally without oversized parent gaps.
    for img in soup.find_all("img"):
        img_style = (img.get("style", "") or "").lower()
        if "float:" not in img_style:
            continue

        host = img.find_parent(["p", "div", "li"])
        if not host:
            continue

        in_slide_host = bool(host.find_parent("div", class_="slide-container")) or (
            "slide-container" in (host.get("class") or [])
        )
        if not in_slide_host:
            continue

        host_style = host.get("style", "") or ""
        host_low = host_style.lower()
        updated = False

        if "overflow" not in host_low:
            host_style = host_style.rstrip("; ") + "; overflow: auto;"
            updated = True
        elif "overflow: auto" not in host_low.replace("  ", " "):
            host_style = re.sub(
                r"overflow\s*:\s*[^;]+;?",
                "overflow: auto;",
                host_style,
                flags=re.IGNORECASE,
            )
            updated = True

        if "display:" not in host_low:
            host_style = host_style.rstrip("; ") + "; display: flow-root;"
            updated = True
        elif "flow-root" not in host_low:
            # Keep existing display if already intentional; only set when no display is present.
            pass

        if updated:
            host["style"] = host_style.strip().rstrip(";") + ";"
            fixes.append("Contained floated image within parent block (overflow:auto)")

    # Promote floated images out of wrapper blocks in non-slide content.
    # This prevents large empty vertical gaps caused by paragraph/div height expansion.
    for img in soup.find_all("img"):
        img_style = img.get("style", "") or ""
        img_style_low = img_style.lower()
        if "float:" not in img_style_low:
            continue

        # Leave slide layouts as-is; slide logic is handled separately.
        if img.find_parent("div", class_="slide-container"):
            continue

        block_host = img.find_parent(["p", "div"])
        if not block_host:
            continue

        # If image is wrapped by inline tags (<em>/<span>/<strong>/<a>), move it to the block edge first.
        inline_parent = (
            img.parent
            if img.parent and img.parent.name in ["em", "span", "strong", "a"]
            else None
        )
        if inline_parent is not None:
            inline_parent.insert_after(img.extract())

        # Move floated image to be a sibling before its block host.
        block_host.insert_before(img.extract())

        # Normalize aggressive margins that amplify blank space.
        if "margin:" in img_style_low:
            side = (
                "right"
                if "float:right" in img_style_low.replace(" ", "")
                else (
                    "left"
                    if "float:left" in img_style_low.replace(" ", "")
                    else "right"
                )
            )
            norm_margin = "10px 0 15px 20px" if side == "right" else "10px 20px 15px 0"
            img_style = re.sub(
                r"margin\s*:\s*[^;]+;?",
                f"margin: {norm_margin};",
                img_style,
                flags=re.IGNORECASE,
            )
        else:
            side = (
                "right"
                if "float:right" in img_style_low.replace(" ", "")
                else (
                    "left"
                    if "float:left" in img_style_low.replace(" ", "")
                    else "right"
                )
            )
            norm_margin = "10px 0 15px 20px" if side == "right" else "10px 20px 15px 0"
            img_style = img_style.rstrip("; ") + f"; margin: {norm_margin};"

        img["style"] = img_style.strip().rstrip(";") + ";"
        fixes.append("Promoted floated image outside wrapper block to reduce gap")

    for img in soup.find_all("img"):
        needs_fix = False
        reason = ""
        alt_raw = img.get("alt", None)
        alt_val = alt_raw.strip() if isinstance(alt_raw, str) else ""
        in_slide_container = bool(img.find_parent("div", class_="slide-container"))

        # 7b. Responsive Fix (Safe)
        # Ensure image never exceeds container width, but do NOT force it to expand (width: 100%).
        style = img.get("style", "")
        style_low = style.lower()

        # Determine an original intended max pixel width if available.
        intended_px = None
        w_attr = (img.get("width") or "").strip()
        if w_attr.isdigit():
            intended_px = int(w_attr)
        else:
            m_w = re.search(r"(?<!max-)width\s*:\s*([0-9.]+)px", style_low)
            if m_w:
                intended_px = int(float(m_w.group(1)))
            else:
                m_mw = re.search(r"max-width\s*:\s*([0-9.]+)px", style_low)
                if m_mw:
                    intended_px = int(float(m_mw.group(1)))

        if intended_px and intended_px > 0:
            # Responsive, but never larger than original intended size.
            style = re.sub(
                r"(?<!max-)width\s*:\s*[^;]+;?", "", style, flags=re.IGNORECASE
            )
            style = re.sub(r"max-width\s*:\s*[^;]+;?", "", style, flags=re.IGNORECASE)
            style = re.sub(r"height\s*:\s*[^;]+;?", "", style, flags=re.IGNORECASE)
            style = style.rstrip("; ")
            style = (
                style + f"; width: 50%; max-width: {intended_px}px; height: auto;"
            ).strip("; ") + ";"
            img["style"] = style
            fixes.append(
                f"Preserved image max size at {intended_px}px while keeping it responsive: {os.path.basename(img.get('src', 'unknown'))}"
            )
        elif "max-width" not in style_low:
            # Unknown original size: preserve intrinsic sizing, only downscale to container.
            new_style_part = "width: 50%; max-width: 50%; height: auto;"
            if style:
                img["style"] = style.rstrip(";") + "; " + new_style_part
            else:
                img["style"] = new_style_part
            fixes.append(
                f"Made image responsive with intrinsic default sizing: {os.path.basename(img.get('src', 'unknown'))}"
            )
        # 7c. Alt Text Logic
        if "alt" not in img.attrs:
            # Hard requirement: every image must include an alt attribute.
            # Leave empty by default and flag for follow-up description.
            img["alt"] = ""
            if "role" not in img.attrs:
                img["role"] = "presentation"
            img["data-alt-needed"] = "true"
            needs_fix = True
            reason = 'Missing Alt Text (inserted alt="")'
        elif alt_val == "":
            # Explicitly mark as decorative for screen readers (Panorama compliance)
            img["role"] = "presentation"
            img["alt"] = ""
        elif alt_val.lower() in ["image", "picture", "photo"]:
            needs_fix = True
            reason = f"Generic Alt Text '{alt_val}'"
        elif any(alt_val.lower().endswith(ext) for ext in image_extensions):
            needs_fix = True
            reason = "Filename used as Alt Text"

        # Keep alt text concise for LMS/readers; push long detail to long description.
        if img.has_attr("alt") and alt_val and len(alt_val) > 120:
            full_alt = alt_val
            trimmed_alt = full_alt[:117].rstrip()
            if not trimmed_alt.endswith("..."):
                trimmed_alt += "..."
            img["alt"] = trimmed_alt
            img["data-alt-truncated"] = "true"
            img["data-original-alt"] = full_alt
            img["data-longdesc-needed"] = "true"
            fixes.append(
                "Trimmed alt text to 120 chars and flagged for long description"
            )
            alt_val = trimmed_alt

        if needs_fix:
            # Note: Placeholders and markers removed per user request. Fixes are tracked in 'fixes' list only.
            fixes.append(f"Flagged image for review: {reason}")

        # 7d. POTENTIAL EQUATION DETECTION (Math Check)
        # Heuristic: Small images with high contrast, or alt text containing math terms but no LaTeX
        src = img.get("src", "").lower()
        # Clear stale math-review flags on known non-math UI/icon assets.
        icon_like = (
            "icons%20full%20size" in src
            or "icons full size" in src
            or "assignment-full-size" in src
            or "assignment_full_size" in src
            or "icon" in src
        )
        if icon_like and img.has_attr("data-math-check"):
            del img["data-math-check"]
            fixes.append(
                f"Cleared false math-review flag on icon asset: {os.path.basename(src)}"
            )

        # [FIX] Idempotency: skip if already flagged or math'd
        if (
            (not icon_like)
            and (not img.has_attr("data-math"))
            and (not img.has_attr("data-math-check"))
            and (
                any(
                    term in alt_val.lower() or term in src
                    for term in ["eq", "formula", "math", "sigma", "sqrt", "frac"]
                )
            )
        ):
            # Mark for interactive review to suggest LaTeX
            img["data-math-check"] = "true"
            fixes.append(
                f"Flagged potential math equation for accessibility verification: {os.path.basename(src)}"
            )

        # 7e. POTENTIAL TABLE IMAGE DETECTION
        # Heuristic: filename/alt hints that image is actually tabular data.
        table_terms = [
            "table",
            "rows",
            "columns",
            "spreadsheet",
            "data table",
            "tabular",
        ]
        if not img.has_attr("data-table-check") and any(
            term in alt_val.lower() or term in src for term in table_terms
        ):
            img["data-table-check"] = "true"
            fixes.append(
                f"Flagged potential table image for HTML table conversion: {os.path.basename(src)}"
            )

    # 7f. Recover missing image tags in visual blocks (description present, image missing).
    # This can happen after iterative edit/replace flows. Reconcile against local *_graphs assets.
    try:
        html_dir = os.path.dirname(filepath)
        html_stem = os.path.splitext(os.path.basename(filepath))[0]
        graphs_dir = os.path.join(html_dir, f"{html_stem}_graphs")

        if os.path.isdir(graphs_dir):
            all_graph_files = []
            for fn in os.listdir(graphs_dir):
                low = fn.lower()
                if low.startswith("full_p"):
                    continue
                if low.endswith("_longdesc.html"):
                    continue
                if low.endswith(
                    (
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".gif",
                        ".webp",
                        ".bmp",
                        ".tif",
                        ".tiff",
                        ".svg",
                    )
                ):
                    all_graph_files.append(fn)

            referenced_basenames = set()
            for im in soup.find_all("img"):
                src = (im.get("src") or "").strip()
                if src:
                    referenced_basenames.add(os.path.basename(src))

            missing_files = [
                fn for fn in sorted(all_graph_files) if fn not in referenced_basenames
            ]

            if missing_files:
                # Try to restore images inline at their original reference points.
                for fn in list(missing_files):
                    # Heuristic: look for a comment or placeholder span with the filename, or a div with a matching data attribute.
                    inserted = False
                    # 1. Look for a comment node with the filename
                    for comment in soup.find_all(
                        string=lambda t: isinstance(t, Comment)
                    ):
                        if fn in str(comment):
                            # Insert image after the comment
                            src = f"{html_stem}_graphs/{fn}"
                            new_img = soup.new_tag("img")
                            new_img["src"] = src
                            new_img["alt"] = "Visual Element"
                            new_img["style"] = (
                                "width: 50%; max-width: 600px; height: auto; border: 1px solid #ccc; display: block; margin: 15px auto;"
                            )
                            comment.insert_after(new_img)
                            fixes.append(
                                f"Restored missing image inline at comment: {fn}"
                            )
                            inserted = True
                            break
                    if inserted:
                        missing_files.remove(fn)
                        continue
                    # 2. Look for a span or div with a placeholder for this image
                    placeholder = soup.find(
                        lambda tag: tag.name in ["span", "div"]
                        and fn
                        in (
                            tag.get("data-img-placeholder", "")
                            or tag.get("id", "")
                            or ""
                        )
                    )
                    if placeholder:
                        src = f"{html_stem}_graphs/{fn}"
                        new_img = soup.new_tag("img")
                        new_img["src"] = src
                        new_img["alt"] = "Visual Element"
                        new_img["style"] = (
                            "width: 50%; max-width: 600px; height: auto; border: 1px solid #ccc; display: block; margin: 15px auto;"
                        )
                        placeholder.insert_after(new_img)
                        fixes.append(
                            f"Restored missing image inline at placeholder: {fn}"
                        )
                        inserted = True
                        missing_files.remove(fn)
                        continue
                # Fill existing empty visual containers next.
                empty_visuals = [
                    dv
                    for dv in soup.find_all("div", class_="mosh-visual")
                    if not dv.find("img")
                ]
                for dv in empty_visuals:
                    if not missing_files:
                        break
                    fn = missing_files.pop(0)
                    src = f"{html_stem}_graphs/{fn}"
                    detail_div = dv.find("details")
                    alt_text = "Visual Element"
                    if detail_div:
                        detail_text = detail_div.get_text(" ", strip=True)
                        if detail_text:
                            alt_text = detail_text[:120].strip()
                    new_img = soup.new_tag("img")
                    new_img["src"] = src
                    new_img["alt"] = alt_text
                    new_img["style"] = (
                        "width: 50%; max-width: 600px; height: auto; border: 1px solid #ccc; display: block; margin: 15px auto;"
                    )
                    dv.insert(0, new_img)
                    fixes.append(f"Restored missing image in mosh-visual block: {fn}")
                # If assets are still unreferenced, append as standalone visual blocks at the end.
                if missing_files:
                    host = (
                        soup.find("div", class_="content-wrapper")
                        or soup.find("body")
                        or soup
                    )
                    for fn in list(missing_files):
                        src = f"{html_stem}_graphs/{fn}"
                        dv = soup.new_tag("div", attrs={"class": "mosh-visual"})
                        dv["style"] = "text-align: center; margin: 2% 0;"
                        im = soup.new_tag("img", src=src, alt="Visual Element")
                        im["style"] = (
                            "width: 50%; max-width: 600px; height: auto; border: 1px solid #ccc; display: block; margin: 15px auto;"
                        )
                        dv.append(im)
                        host.append(dv)
                        fixes.append(f"Appended unreferenced graph image asset: {fn}")
    except Exception:
        pass

    # --- Part 7f: Horizontal separators ---
    # Some checkers produce false contrast flags on <hr> even when color contrast is valid.
    # Replace with a decorative separator div to avoid noisy failures.
    for hr in soup.find_all("hr"):
        sep = soup.new_tag("div")
        sep["role"] = "separator"
        sep["aria-hidden"] = "true"
        sep["style"] = (
            "display: block; width: 100%; "
            "height: 3px; background-color: #4b3190; "
            "margin: 24px 0; border: 0;"
        )
        hr.insert_before(sep)
        hr.decompose()
        fixes.append("Replaced <hr> with school-color decorative separator")

    # --- Part 8: Typography & Accessibility (Brand Colors / Small Fonts / AUTO-CONTRAST) ---
    import run_audit  # Use get_style_property for robust lookup

    # A. Brand color normalization:
    # If a tag has a non-neutral background color, normalize it to school purple
    # (except intentional code-dark panels).
    allowed_bg = {
        "#ffffff",
        "#fff",
        "#f8f9fa",
        "#f5f6fa",
        "#f9f9f9",
        "#eeeeee",
        "#ddd",
        "#121212",
        MCC_PURPLE.lower(),
        MCC_DEEP.lower(),
        "white",
        "transparent",
        "inherit",
    }

    for tag in soup.find_all(style=True):
        style_original = tag.get("style", "")
        style = style_original
        low = style.lower()

        # Skip explicit code areas.
        if tag.name in ["pre", "code"]:
            continue
        if tag.find_parent("pre") or tag.find_parent("code"):
            continue

        bg_match = re.search(r"background(?:-color)?\s*:\s*([^;]+)", low)
        if not bg_match:
            continue

        bg_val = bg_match.group(1).strip()
        if bg_val in allowed_bg:
            continue

        # Normalize to school purple for non-neutral backgrounds.
        style = re.sub(
            r"background(?:-color)?\s*:\s*[^;]+",
            f"background-color: {MCC_PURPLE}",
            style,
            flags=re.IGNORECASE,
        )

        # Ensure readable foreground on purple backgrounds.
        if re.search(r"(?<!-)color\s*:", style, flags=re.IGNORECASE):
            style = re.sub(
                r"(?<!-)color\s*:\s*[^;]+", "color: #ffffff", style, flags=re.IGNORECASE
            )
        else:
            style = style.rstrip("; ") + "; color: #ffffff;"

        tag["style"] = style.strip().rstrip(";") + ";"
        fixes.append("Normalized non-neutral background to school color")

    # B. Small fonts and contrast checks
    for tag in soup.find_all(style=True):
        style = tag.get("style", "").lower()

        # A. Font Size Fix
        size_match = re.search(r"font-size:\s*([0-9.]+)(px|pt|em|rem)", style)
        if size_match:
            val = float(size_match.group(1))
            unit = size_match.group(2)
            needs_elevation = False
            new_val = 12
            if unit == "px" and val < 12:
                needs_elevation = True
                new_val = 14
            elif unit == "pt" and val < 9:
                needs_elevation = True
                new_val = 10.5
            elif unit in ["em", "rem"] and val < 0.9:
                needs_elevation = True
                new_val = 0.95
            if needs_elevation:
                tag["style"] = re.sub(
                    rf"font-size:\s*[0-9.]+{unit}",
                    f"font-size: {new_val}{unit}",
                    tag["style"],
                    flags=re.IGNORECASE,
                )
                fixes.append(
                    f"Elevated small font size ({val}{unit} -> {new_val}{unit})"
                )

        # B. AUTO-CONTRAST CORRECTION
        if tag.get_text(strip=True):
            fg = run_audit.get_style_property(tag, "color")
            bg = run_audit.get_style_property(tag, "background-color")

            if fg and bg:
                ratio = get_contrast_ratio(fg, bg)
                if ratio and ratio < 4.5:
                    # Calculate target
                    # If it's large text, we only need 3.0, but 4.5 is safer
                    new_fg = adjust_color_for_contrast(fg, bg)

                    # Update the style string
                    if re.search(r"(?<!-)color\s*:", tag["style"], flags=re.IGNORECASE):
                        # Important: only replace foreground color, not background-color.
                        tag["style"] = re.sub(
                            r"(?<!-)color:\s*#[0-9a-fA-F]{3,6}",
                            f"color: {new_fg}",
                            tag["style"],
                            flags=re.IGNORECASE,
                        )
                        tag["style"] = re.sub(
                            r"(?<!-)color:\s*[a-zA-Z]+",
                            f"color: {new_fg}",
                            tag["style"],
                            flags=re.IGNORECASE,
                        )
                    else:
                        tag["style"] = tag["style"].rstrip("; ") + f"; color: {new_fg};"

                    fixes.append(
                        f"Auto-corrected low contrast ({ratio:.1f}:1 -> 4.5:1)"
                    )

    # --- Part 9: Links & Iframes (Vague Text Correction) ---
    # 9a. List structure normalization: ul/ol should only contain <li> children.
    for lst in soup.find_all(["ul", "ol"]):
        children = list(lst.children)
        for child in children:
            # Keep valid list items.
            if getattr(child, "name", None) == "li":
                continue

            # Remove empty text nodes.
            if isinstance(child, NavigableString):
                if not str(child).strip():
                    child.extract()
                else:
                    # Convert meaningful stray text node into a list item.
                    new_li = soup.new_tag("li")
                    new_li.string = str(child).strip()
                    child.replace_with(new_li)
                    fixes.append("Normalized stray list text into <li>")
                continue

            # For non-li tags inside lists, move them outside (after list).
            if getattr(child, "name", None) is not None:
                lst.insert_after(child.extract())
                fixes.append(f"Moved non-list element <{child.name}> outside list")

    vague_terms = [
        "click here",
        "read more",
        "learn more",
        "more",
        "link",
        "here",
        "view",
    ]
    for a in soup.find_all("a"):
        href = a.get("href", "")
        text = a.get_text(strip=True).lower()

        # 1. Remove empty links
        if not text and not a.find_all(True):
            fixes.append(f"Removed empty link to '{href}'")
            a.extract()
            continue

        # Link Text Cleanup (Strip extensions and underscores)
        # Heuristic: If text looks like a filename (ends in extension or has underscores)
        doc_exts = [".pdf", ".docx", ".pptx", ".xlsx", ".zip", ".txt"]
        if any(text.endswith(ext) for ext in doc_exts) or "_" in text:
            new_text = text
            for ext in doc_exts:
                if new_text.endswith(ext):
                    new_text = new_text[: -len(ext)]
                    break
            new_text = new_text.replace("_", " ").strip()
            if new_text and new_text != text:
                a.string = new_text
                fixes.append(f"Cleaned link text: '{text}' -> '{new_text}'")
                text = new_text.lower()  # Update for next check

        # 2. Fix Vague Text (e.g. "Click Here")
        if text in vague_terms:
            # Try to find context (previous text or heading)
            context = "Information"
            prev_tag = a.find_previous(["h2", "h3", "strong", "b", "p"])
            if prev_tag:
                context = prev_tag.get_text(strip=True)[:30]

            # If it's a file link, use the sanitized filename
            if any(ext in href.lower() for ext in doc_exts):
                filename = os.path.basename(href).split("?")[0]
                name_only = (
                    os.path.splitext(filename)[0]
                    .replace("%20", " ")
                    .replace("_", " ")
                    .strip()
                )
                a.string = f"Download {name_only}"
                fixes.append(
                    f"Fixed vague link text '{text}' -> 'Download {name_only}'"
                )
            else:
                a.string = f"View {context}"
                fixes.append(f"Fixed vague link text '{text}' -> 'View {context}'")

        # Ensure every link has a descriptive title attribute.
        link_text_now = a.get_text(" ", strip=True)
        href_now = (a.get("href") or "").strip()
        current_title = (a.get("title") or "").strip()

        # Treat empty/generic titles as missing.
        generic_titles = {
            "link",
            "click here",
            "here",
            "more",
            "read more",
            "learn more",
            "view",
        }
        needs_title = (not current_title) or (current_title.lower() in generic_titles)
        if needs_title:
            desc = link_text_now if link_text_now else "linked resource"
            if href_now and any(href_now.lower().endswith(ext) for ext in doc_exts):
                title_val = f"Download {desc}"
            elif href_now:
                title_val = f"Open {desc}"
            else:
                title_val = desc
            a["title"] = title_val[:180]
            fixes.append("Added descriptive title to link")

    for iframe in soup.find_all("iframe"):
        if not iframe.has_attr("title") or not iframe["title"].strip():
            # Try to guess title from src
            src = iframe.get("src", "").lower()
            if "youtube" in src:
                title = "Embedded YouTube Video"
            elif "panopto" in src:
                title = "Embedded Panopto Video"
            elif "vimeo" in src:
                title = "Embedded Vimeo Video"
            else:
                title = "Embedded Content"

            iframe["title"] = title
            fixes.append(f"Added title '{title}' to iframe")

        # Preserve proportional video/LTI sizing.
        try:

            def _px_from_style(style_text, prop_name):
                m = re.search(
                    rf"{prop_name}\s*:\s*([0-9.]+)px", style_text, flags=re.IGNORECASE
                )
                return int(float(m.group(1))) if m else None

            def _ratio_from_style(style_text):
                # Matches: aspect-ratio: 16 / 9; or aspect-ratio:16/9
                m = re.search(
                    r"aspect-ratio\s*:\s*([0-9.]+)\s*/\s*([0-9.]+)",
                    style_text,
                    flags=re.IGNORECASE,
                )
                if not m:
                    return None
                a = float(m.group(1))
                b = float(m.group(2))
                if a > 0 and b > 0:
                    return (a, b)
                return None

            width_attr = iframe.get("width", "").strip()
            height_attr = iframe.get("height", "").strip()
            w = int(float(width_attr)) if width_attr else None
            h = int(float(height_attr)) if height_attr else None
            st = iframe.get("style", "") or ""

            # Use existing style dimensions when attrs are missing.
            if not w:
                w = _px_from_style(st, "max-width") or _px_from_style(st, "width")
            if not h:
                h = _px_from_style(st, "height")

            # Use existing aspect-ratio when present.
            ratio_pair = _ratio_from_style(st)
            if ratio_pair and not (w and h):
                rw, rh = ratio_pair
                if w and not h:
                    h = int(round(w * (rh / rw)))
                elif h and not w:
                    w = int(round(h * (rw / rh)))

            # Infer counterpart only when one side exists.
            if w and not h:
                h = int(round(w * 9 / 16))
            elif h and not w:
                w = int(round(h * 16 / 9))

            if w and h and h > 0:
                ratio = f"{w} / {h}"
                ratio_pct = (float(h) / float(w)) * 100.0

                # Use a ratio wrapper so Canvas/browser differences don't distort iframe height.
                parent = iframe.parent
                has_ratio_wrapper = (
                    parent
                    and getattr(parent, "name", None) == "div"
                    and (
                        "responsive-iframe-wrap" in (parent.get("class") or [])
                        or parent.get("data-ada-iframe-wrap") == "true"
                    )
                )

                if has_ratio_wrapper:
                    wrapper = parent
                else:
                    wrapper = soup.new_tag("div")
                    wrapper["class"] = ["responsive-iframe-wrap"]
                    wrapper["data-ada-iframe-wrap"] = "true"
                    iframe.insert_before(wrapper)
                    wrapper.append(iframe.extract())

                wrapper["style"] = (
                    f"position: relative; width: 100%; max-width: {w}px; "
                    f"padding-top: {ratio_pct:.6f}%; height: 0; overflow: hidden;"
                )

                # Keep non-size inline styles, but force size/position from wrapper.
                st = re.sub(r"height\s*:\s*[^;]+;?", "", st, flags=re.IGNORECASE)
                st = re.sub(r"width\s*:\s*[^;]+;?", "", st, flags=re.IGNORECASE)
                st = re.sub(r"max-width\s*:\s*[^;]+;?", "", st, flags=re.IGNORECASE)
                st = re.sub(r"aspect-ratio\s*:\s*[^;]+;?", "", st, flags=re.IGNORECASE)
                st = st.rstrip("; ")
                st = (
                    st
                    + "; position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0;"
                ).strip("; ") + ";"
                iframe["style"] = st
                iframe["loading"] = iframe.get("loading", "lazy")
                fixes.append(
                    f"Normalized iframe to fixed-ratio responsive sizing ({ratio})"
                )
            else:
                # Not enough dimension data: do not touch sizing to avoid skewing embeds.
                iframe["loading"] = iframe.get("loading", "lazy")
        except Exception:
            pass

    # --- Part 10: SMART IMAGE ALIGNMENT (For Word/PDF) ---
    for img in soup.find_all("img"):
        parent = img.parent
        # If image is alone in a paragraph, it might benefit from being floated
        if parent.name == "p" and len(parent.contents) == 1:
            # Check image size (heuristic)
            width = img.get("width", "800")
            try:
                w_val = int(width)
                if w_val < 400:
                    # [FIX] Idempotency: skip if float already exists
                    current_style = img.get("style", "").lower()
                    if "float" not in current_style:
                        img["style"] = (
                            img.get("style", "")
                            + " float: right; margin: 10px 0 15px 20px; max-width: 40%;"
                        )
                        fixes.append(
                            f"Applied smart float-right to small image: {os.path.basename(img.get('src',''))}"
                        )
            except Exception:
                pass

    # --- Part 8: Deprecated Tags ---
    # Convert <b> to <strong>
    for tag in soup.find_all("b"):
        tag.name = "strong"
        fixes.append("Converted deprecated <b> to <strong>")

    # Convert <i> to <em>
    for tag in soup.find_all("i"):
        # Skip Font Awesome icons (they use <i class="fa-...">)
        if tag.get("class") and any("fa" in c for c in tag.get("class", [])):
            continue
        tag.name = "em"
        fixes.append("Converted deprecated <i> to <em>")

    # Convert <center> to <div style="text-align: center">
    for tag in soup.find_all("center"):
        tag.name = "div"
        existing_style = tag.get("style", "")
        tag["style"] = f"text-align: center; {existing_style}".strip()
        fixes.append("Converted deprecated <center> to styled <div>")

    # Unwrap <font> (preserve content, remove tag)
    for tag in soup.find_all("font"):
        # Try to preserve color and face as a span with inline style
        color = tag.get("color")
        font = tag.get("face")

        style_parts = []
        if color:
            style_parts.append(f"color: {color};")
        if font:
            style_parts.append(f"font-family: {font}, sans-serif;")

        if style_parts:
            new_span = soup.new_tag("span", style=" ".join(style_parts))
            new_span.extend(tag.contents[:])
            tag.replace_with(new_span)
        else:
            tag.unwrap()
        fixes.append("Replaced deprecated <font> tag with styled <span>")

    # Unwrap <blink> and <marquee> (just remove the tag, keep content)
    for tag_name in ["blink", "marquee"]:
        for tag in soup.find_all(tag_name):
            tag.unwrap()
            fixes.append(f"Removed deprecated <{tag_name}> tag")

    # --- Part 9: Smart List Reflow ---
    # Detect paragraphs starting with list markers (*, -, 1., etc.) and group them into lists
    all_p = soup.find_all("p")
    i = 0
    while i < len(all_p):
        p = all_p[i]
        text = p.get_text(strip=True)
        # Match *, -, or 1. at the start
        bullet_match = re.match(r"^([\*\-•]|\d+[\.\)])\s+", text)
        if bullet_match:
            # We found a potential list item. Look ahead for consecutive ones.
            list_items = []
            current_p = p
            while current_p and current_p.name == "p":
                t = current_p.get_text(strip=True)
                m = re.match(r"^([\*\-•]|\d+[\.\)])\s+", t)
                if not m:
                    break

                # Extract text without marker
                marker_len = len(m.group(0))
                item_text = t[marker_len:].strip()
                list_items.append((current_p, item_text, m.group(1)))

                # Check next sibling paragraph (skipping whitespace/comments)
                next_sib = current_p.next_sibling
                while next_sib and not (
                    hasattr(next_sib, "name") and next_sib.name == "p"
                ):
                    if (
                        hasattr(next_sib, "name")
                        and next_sib.name
                        and next_sib.name not in ["script", "style", "span"]
                    ):
                        # Hit a real tag that isn't a paragraph, stop grouping
                        current_p = None
                        break
                    next_sib = next_sib.next_sibling
                current_p = next_sib

            if len(list_items) > 1:
                # Group them!
                is_ordered = list_items[0][2].replace(".", "").isdigit()
                list_tag = soup.new_tag("ol" if is_ordered else "ul")

                # Use standard styles
                list_tag["style"] = "margin-left: 20px; margin-bottom: 15px;"

                # Insert list before first P
                list_items[0][0].insert_before(list_tag)

                for p_node, txt, marker in list_items:
                    li = soup.new_tag("li")
                    li.string = txt
                    list_tag.append(li)
                    p_node.extract()

                fixes.append(
                    f"Grouped {len(list_items)} paragraphs into accessible {'ordered' if is_ordered else 'unordered'} list"
                )
                # Advance index by how many we removed
                i += len(list_items) - 1
        i += 1

    # 9c. TOC de-smush repair: split long table-of-contents-like paragraphs into list items.
    for p in list(soup.find_all("p")):
        if p.find(["ul", "ol", "table", "img", "pre", "code"]):
            continue

        raw = p.get_text(" ", strip=True)
        if len(raw) < 120:
            continue

        lower = raw.lower()
        page_nums = re.findall(r"\b\d{1,3}\b", raw)
        section_hits = len(re.findall(r"\b(section|chapter)\b", lower))

        # Only trigger on strong TOC signals to avoid false positives.
        toc_like = (
            ("table of contents" in lower)
            or (len(page_nums) >= 6 and section_hits >= 2)
            or (len(page_nums) >= 10)
        )
        if not toc_like:
            continue

        normalized = re.sub(r"\s+", " ", raw).strip()

        # Robust TOC splitting strategy:
        # Treat standalone 1-3 digit numbers (not part of decimals like 2.1) as page numbers,
        # and split entries at each page-number terminus.
        page_token_re = re.compile(r"(?<![\d\.])\d{1,3}(?![\d\.])")
        parts = []
        start_idx = 0
        for m in page_token_re.finditer(normalized):
            chunk = normalized[start_idx : m.end()].strip(" \t-–•")
            if len(chunk) > 8 and len(chunk.split()) >= 2:
                parts.append(chunk)
            start_idx = m.end()

        # If numeric splitting produced nothing useful, use a heading-boundary fallback.
        if len(parts) < 3:
            boundary_re = re.compile(r"\s+(?=(?:Section\s+\d|Chapter\s+\d|[A-Z][a-z]))")
            fallback = []
            current = []
            for tok in boundary_re.split(normalized):
                tok = tok.strip(" \t-–•")
                if not tok:
                    continue
                current.append(tok)
                # Close an item when it ends with a likely page number.
                if re.search(r"(?<![\d\.])\d{1,3}(?![\d\.])$", tok):
                    item = " ".join(current).strip()
                    if len(item) > 8:
                        fallback.append(item)
                    current = []
            if current:
                tail_item = " ".join(current).strip()
                if len(tail_item) > 8:
                    fallback.append(tail_item)
            parts = fallback

        if len(parts) < 3:
            continue

        ul = soup.new_tag("ul")
        ul["style"] = "margin-left: 20px; margin-bottom: 15px;"
        for entry in parts:
            li = soup.new_tag("li")
            li.string = entry
            ul.append(li)

        p.replace_with(ul)
        fixes.append("Repaired smushed table-of-contents paragraph into list")

    # 9d. Remove duplicate "Table of Contents" paragraph directly under TOC summary/details.
    for det in soup.find_all("details"):
        summary = det.find("summary")
        if not summary:
            continue
        summary_text = summary.get_text(" ", strip=True).lower()
        if "table of contents" not in summary_text:
            continue
        for p in list(det.find_all("p", recursive=False)):
            p_text = p.get_text(" ", strip=True).lower()
            if p_text in {"table of contents", "contents", "table of content"}:
                p.decompose()
                fixes.append("Removed duplicate TOC heading paragraph inside details")

    # 9b. Orphan <li> repair: ensure every list item is inside <ul> or <ol>.
    # Some upstream transforms can leave stray <li> nodes under <div>/<p> containers.
    for li in list(soup.find_all("li")):
        parent_name = getattr(li.parent, "name", None)
        if parent_name in ["ul", "ol"]:
            continue

        # Create a list wrapper before the first orphan item.
        new_list = soup.new_tag("ul")
        li.insert_before(new_list)
        new_list.append(li.extract())

        # Move immediately-following orphan <li> siblings into the same wrapper.
        nxt = new_list.next_sibling
        while nxt is not None:
            # Skip pure whitespace nodes between consecutive list items.
            if isinstance(nxt, NavigableString) and not str(nxt).strip():
                to_remove = nxt
                nxt = nxt.next_sibling
                to_remove.extract()
                continue

            if getattr(nxt, "name", None) == "li":
                to_move = nxt
                nxt = nxt.next_sibling
                new_list.append(to_move.extract())
                continue

            break

        fixes.append("Wrapped orphan <li> item(s) in <ul>")

    # --- Part 10: Final Polish & Special Checks ---
    emoji_fixes = fix_emoji_accessibility(soup)
    fixes.extend(emoji_fixes)

    # Deduplicate fixes
    unique_fixes = list(set(fixes))

    # Final serialization cleanup for lingering mojibake/entity artifacts.
    remediated_html = str(soup)
    final_cleanup = {
        "&Acirc;&nbsp;": " ",
        "&acirc;&nbsp;": " ",
        "Â\xa0": " ",
        "Â ": " ",
        "&Acirc;&copy;": "&copy;",
        "&acirc;&copy;": "&copy;",
        "&eth;&sup1;": "🎥",
        "ð¹": "🎥",
    }
    cleaned_any = False
    for bad, good in final_cleanup.items():
        if bad in remediated_html:
            remediated_html = remediated_html.replace(bad, good)
            cleaned_any = True

    remediated_html = re.sub(r"(\d)â(\d)", r"\1–\2", remediated_html)
    if cleaned_any:
        unique_fixes.append("Final output cleanup removed mojibake artifacts")

    return remediated_html, unique_fixes


def batch_remediate_v3(directory):
    """Processes all HTML files in a directory."""
    report = {}
    for root, dirs, files in os.walk(directory):
        if "_ORIGINALS_DO_NOT_UPLOAD_" in root:
            continue
        for file in files:
            if file.endswith(".html"):
                path = os.path.join(root, file)
                remediated, fixes = remediate_html_file(path)
                if fixes:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(remediated)
                    report[file] = fixes
    return report


# [REMOVED] strip_ada_markers and batch_strip_markers per user request.
# Markers are no longer added, so cleanup is unnecessary.

if __name__ == "__main__":
    import sys

    print("--- MASTER REMEDIATOR V3 (Toolkit Merge) ---")
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
    else:
        target_path = input("Enter path to scan: ").strip('"')

    if os.path.isdir(target_path):
        report = batch_remediate_v3(target_path)
        print(f"Done. Remediated {len(report)} files.")
        for file, fixes in report.items():
            print(f"  [{file}]")
            for fix in fixes:
                print(f"    - {fix}")
    elif os.path.isfile(target_path):
        remediated, fixes = remediate_html_file(target_path)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(remediated)
        print(f"Done. Fixes in {os.path.basename(target_path)}:")
        for fix in fixes:
            print(f"  - {fix}")
    else:
        print("Invalid directory.")

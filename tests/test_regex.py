import re
s = 'href="$IMS-CC-FILEBASE$/Uploaded%20Media/Mat%20165%20Classwork%20Sections%202.docx?canvas_=1&amp;canvas_qs_wrap=1"'
old_base = "Mat 165 Classwork Sections 2"
old_ext = ".docx"
old_encoded = old_base.replace(" ", "%20")
e_old_base = re.escape(old_base)
e_old_encoded = re.escape(old_encoded)
e_old_ext = re.escape(old_ext)

pattern1 = rf'href="(\$IMS-CC-FILEBASE\$/[^"]*){e_old_base}{e_old_ext}(\?[^"]*)?"'
pattern2 = rf'href="(\$IMS-CC-FILEBASE\$/[^"]*){e_old_encoded}{e_old_ext}(\?[^"]*)?"'

print("p1:", re.search(pattern1, s, re.IGNORECASE))
print("p2:", re.search(pattern2, s, re.IGNORECASE))

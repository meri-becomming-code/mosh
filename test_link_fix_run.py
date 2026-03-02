import os
import converter_utils

root_dir = os.path.dirname(os.path.abspath(__file__))
# Note: update_doc_links_to_html(root_dir, old_filename, new_filename, log_func=None)

print("--- Testing Syllabus Fix ---")
converter_utils.update_doc_links_to_html(root_dir, "My Syllabus.pptx", "My Syllabus.html", log_func=print)

print("\n--- Testing Lecture Fix ---")
converter_utils.update_doc_links_to_html(root_dir, "Lecture (1).docx", "Lecture_1.html", log_func=print)

with open("test_link_fix.html", "r") as f:
    print("\nResulting HTML:")
    print(f.read())

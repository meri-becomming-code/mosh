import mammoth
from pathlib import Path
import os
import shutil

doc_path = r'c:\Users\mered\Downloads\new-math-export (1)_extracted_remediated_extracted\web_resources\Chapter 3 Note Packet (Key) (4).docx'

def convert_docx_to_html_with_images(doc_file_path):
    output_dir = Path(doc_file_path).parent
    img_counter = [1]
    
    def handle_image(image):
        with image.open() as image_bytes:
            # Generate unique filename
            img_filename = f"{Path(doc_file_path).stem}_img{img_counter[0]}.{image.content_type.split('/')[1]}"
            img_path = output_dir / img_filename
            with open(img_path, 'wb') as f:
                f.write(image_bytes.read())
            img_counter[0] += 1
            return {"src": img_filename}

    with open(doc_file_path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file, convert_image=mammoth.images.img_element(handle_image))
        html = result.value
        messages = result.messages
        print("HTML length:", len(html))
        print("Messages:", messages)
        print("HTML snippet containing images:", [x for x in html.split('<') if x.startswith('img')])
        return html

html = convert_docx_to_html_with_images(doc_path)
with open('mammoth_output.html', 'w', encoding='utf-8') as f:
    f.write(html)

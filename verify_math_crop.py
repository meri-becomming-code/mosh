import os
from pathlib import Path
from PIL import Image
import re

def extract_and_crop_graphs(html_content, image_path, output_dir, base_name, page_num):
    """
    Parses [GRAPH_BBOX] tokens, crops images from the source page, 
    saves them to web_resources, and replaces tokens with <img> tags.
    """
    if '[GRAPH_BBOX:' not in html_content:
        return html_content
        
    try:
        # 1. Ensure web_resources exists
        res_dir = Path(output_dir) / 'web_resources'
        res_dir.mkdir(exist_ok=True)
        
        # 2. Open Source Image
        with Image.open(image_path) as img:
            width, height = img.size
            
            # 3. Find all BBOX tokens
            # Format: [GRAPH_BBOX: ymin, xmin, ymax, xmax] (0-1000 scale)
            # OLD REGEX: r'\[GRAPH_BBOX:\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]'
            # NEW REGEX (More robust):
            matches = re.finditer(r'\[GRAPH_BBOX:\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]', html_content)
            
            for i, match in enumerate(matches):
                try:
                    full_token = match.group(0)
                    ymin_rel, xmin_rel, ymax_rel, xmax_rel = map(int, match.groups())
                    
                    # 4. Convert to Pixels with Padding
                    ymin = int((ymin_rel / 1000) * height)
                    xmin = int((xmin_rel / 1000) * width)
                    ymax = int((ymax_rel / 1000) * height)
                    xmax = int((xmax_rel / 1000) * width)
                    
                    # Add 80px padding (user requested extra 50-100px)
                    ymin = max(0, ymin - 80)
                    xmin = max(0, xmin - 80)
                    ymax = min(height, ymax + 80)
                    xmax = min(width, xmax + 80)
                    
                    if (xmax - xmin) < 50 or (ymax - ymin) < 50:
                        continue # Skip tiny crops
                        
                    # 5. Crop and Save
                    crop = img.crop((xmin, ymin, xmax, ymax))
                    
                    # Unique filename
                    graph_filename = f"{base_name}_p{page_num + 1}_graph{i + 1}.png"
                    save_path = res_dir / graph_filename
                    crop.save(save_path)
                    
                    # 6. Replace Token with Image Tag
                    img_tag = f'<br><img src="web_resources/{graph_filename}" alt="Graph from Page {page_num + 1}" style="max-width: 600px; border: 1px solid #ccc;"><br>'
                    html_content = html_content.replace(full_token, img_tag)
                    print(f"✅ Created crop: {graph_filename}")
                    
                except Exception as e:
                    print(f"Crop Error: {e}")
                    # Remove token on error to clean up
                    html_content = html_content.replace(full_token, "")
                    
    except Exception as e:
        print(f"Graph extraction failed: {e}")
        
    return html_content

def test_cropping():
    # Create a dummy image (1000x1000)
    img = Image.new('RGB', (1000, 1000), color = (73, 109, 137))
    img.save('test_source.png')
    
    # Mock HTML content with various token formats
    mock_html = """
    <p>Here is a graph:</p>
    [GRAPH_BBOX: 100, 100, 400, 400]
    <p>And another with different spacing:</p>
    [GRAPH_BBOX:500 ,500 , 800 , 800 ]
    """
    
    print("Testing extraction...")
    result = extract_and_crop_graphs(mock_html, 'test_source.png', '.', 'test_output', 0)
    
    print("\nResulting HTML:")
    print(result)
    
    # Verify files
    if os.path.exists('web_resources/test_output_p1_graph1.png'):
        print("\n✅ File 1 exists")
    else:
        print("\n❌ File 1 MISSING")
        
    if os.path.exists('web_resources/test_output_p1_graph2.png'):
        print("✅ File 2 exists")
    else:
        print("❌ File 2 MISSING")

    # Cleanup
    # os.remove('test_source.png')
    # if os.path.exists('web_resources'):
    #     import shutil
    #     shutil.rmtree('web_resources')

if __name__ == "__main__":
    test_cropping()

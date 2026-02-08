from PIL import Image
import os

def make_transparent(img_path):
    print(f"Processing {img_path} with Flood Fill...")
    img = Image.open(img_path).convert("RGBA")
    
    # Flood fill from the top-left corner (0,0) with transparency
    # (255, 255, 255, 0) is transparent
    # We use a threshold/tolerance if needed, but for solid white 0,0 is usually perfect.
    
    # 1. Create a mask of the white background starting from 0,0
    from PIL import ImageDraw
    
    # Find the seed color (top-left pixel)
    seed_color = img.getpixel((0, 0))
    
    # We'll use floodfill to turn the background into a specific "key" color first 
    # then make that color transparent, OR just use the alpha channel directly.
    # Actually PIL's floodfill can work on the image in-place.
    
    ImageDraw.floodfill(img, xy=(0, 0), value=(255, 255, 255, 0), thresh=10)
    
    # Also check other corners in case of separated background pockets
    w, h = img.size
    ImageDraw.floodfill(img, xy=(w-1, 0), value=(255, 255, 255, 0), thresh=10)
    ImageDraw.floodfill(img, xy=(0, h-1), value=(255, 255, 255, 0), thresh=10)
    ImageDraw.floodfill(img, xy=(w-1, h-1), value=(255, 255, 255, 0), thresh=10)

    img.save(img_path, "PNG")
    print(f"Saved transparent image to {img_path} (Eyes preserved!)")

if __name__ == "__main__":
    img_path = "c:\\Users\\mered\\OneDrive\\Desktop\\mosh-1\\mosh_pilot.png"
    if os.path.exists(img_path):
        make_transparent(img_path)
    else:
        print(f"Error: {img_path} not found.")

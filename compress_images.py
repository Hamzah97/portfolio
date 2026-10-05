import os
from PIL import Image

def optimize_images(directory, max_width=1200):
    for root, dirs, files in os.walk(directory):
        for file in files:
            ext = file.lower().split('.')[-1]
            if ext in ['jpg', 'jpeg', 'png']:
                filepath = os.path.join(root, file)
                try:
                    with Image.open(filepath) as img:
                        # Skip animated GIFs masquerading as other formats just in case
                        if getattr(img, "is_animated", False):
                            print(f"Skipping animated image: {file}")
                            continue

                        # Convert RGBA PNGs to RGB if saving as JPEG, but we're keeping original format.
                        # Wait, we just keep original format.
                        original_format = img.format
                        
                        # Calculate new size if wider than max_width
                        if img.width > max_width:
                            wpercent = (max_width / float(img.width))
                            hsize = int((float(img.height) * float(wpercent)))
                            img = img.resize((max_width, hsize), Image.Resampling.LANCZOS)
                            print(f"Resized: {file} to {max_width}x{hsize}")

                        # Save optimized
                        if ext in ['jpg', 'jpeg']:
                            # Ensure image is in a mode that can be saved as JPEG
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            img.save(filepath, 'JPEG', optimize=True, quality=80)
                            print(f"Optimized JPG: {file}")
                        elif ext == 'png':
                            img.save(filepath, 'PNG', optimize=True)
                            print(f"Optimized PNG: {file}")
                except Exception as e:
                    print(f"Failed to process {file}: {e}")

if __name__ == '__main__':
    images_dir = r"C:\Users\hamza\OneDrive\Documents\GitHub\portfolio\assets\images"
    print("Starting image optimization...")
    optimize_images(images_dir)
    print("Finished optimization.")

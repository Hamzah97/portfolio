import os
import json
import re
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent
JS_FILE = SITE_DIR / "assets" / "projects.js"

def main():
    print("Reading projects.js...")
    with open(JS_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract JSON string from the JS file
    # It looks for "const projectsData = [ ... ];"
    match = re.search(r'const projectsData = (\[.*\]);', content, re.DOTALL)
    if not match:
        print("Could not find projectsData array in projects.js")
        return

    json_str = re.sub(r",\s*]$", "]", match.group(1))
    try:
        projects = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON in projects.js: {e}")
        return

    print("Scanning directories for media...")
    for p in projects:
        pid = p.get("id")
        if not pid:
            continue

        media_list = []
        
        img_dir = SITE_DIR / "assets" / "images" / pid
        vid_dir = SITE_DIR / "assets" / "videos" / pid
        
        # Scan images
        if img_dir.exists():
            for f in sorted(img_dir.iterdir()):
                if not f.is_file() or f.suffix.lower() not in (
                    '.png', '.jpg', '.jpeg', '.gif', '.webp'
                ):
                    continue

                if f.suffix.lower() == '.webp':
                    if f.stem.endswith('.optimized'):
                        continue
                    source_extensions = ('.png', '.jpg', '.jpeg', '.gif')
                    if any(f.with_suffix(ext).exists() for ext in source_extensions):
                        continue
                    image_file = f
                else:
                    optimized = f.with_name(f"{f.stem}.optimized.webp")
                    image_file = (
                        optimized
                        if optimized.is_file() and optimized.stat().st_size < f.stat().st_size
                        else f
                    )

                src = f"assets/images/{pid}/{image_file.name}"
                media = {"type": "image", "src": src, "caption": f.name}
                if image_file != f:
                    media["fallback"] = f"assets/images/{pid}/{f.name}"
                media_list.append(media)
                    
        # Scan videos
        if vid_dir.exists():
            for f in sorted(vid_dir.iterdir()):
                if (
                    not f.is_file()
                    or f.suffix.lower() not in ('.mp4', '.webm', '.ogg', '.mov', '.m4v')
                    or f.stem.endswith('.optimized')
                ):
                    continue

                optimized = f.with_name(f"{f.stem}.optimized.mp4")
                video_file = (
                    optimized
                    if optimized.is_file() and optimized.stat().st_size < f.stat().st_size
                    else f
                )
                src = f"assets/videos/{pid}/{video_file.name}"
                media = {"type": "video", "src": src, "caption": f.name}
                if video_file != f:
                    media["fallback"] = f"assets/videos/{pid}/{f.name}"
                media_list.append(media)
                    
        # Update media array in the project data
        p["media"] = media_list
        
        # Find the best thumbnail
        # 1. Look for an image containing 'cover' or 'thumbnail' in its name
        thumbnail = None
        for m in media_list:
            if m['type'] == 'image' and ('cover' in m['src'].lower() or 'thumbnail' in m['src'].lower()):
                thumbnail = m['src']
                break
                
        # 2. Fallback to any file with 'cover' or 'thumbnail' (even a video)
        if not thumbnail:
            for m in media_list:
                if 'cover' in m['src'].lower() or 'thumbnail' in m['src'].lower():
                    thumbnail = m['src']
                    break
        
        # 3. Fallback to the first image found
        if not thumbnail:
            for m in media_list:
                if m['type'] == 'image':
                    thumbnail = m['src']
                    break
                    
        # 4. Final fallback to any media (e.g., if there are only videos)
        if not thumbnail and media_list:
            thumbnail = media_list[0]['src']
            
        if thumbnail:
            p["thumbnail"] = thumbnail
            thumbnail_media = next(
                (m for m in media_list if m["type"] == "image" and m["src"] == thumbnail),
                None,
            )
            if thumbnail_media and "fallback" in thumbnail_media:
                p["thumbnailFallback"] = thumbnail_media["fallback"]
            else:
                p.pop("thumbnailFallback", None)
            print(f"[{pid}] Found {len(media_list)} media files. Thumbnail: {os.path.basename(thumbnail)}")
        else:
            print(f"[{pid}] No media found.")

    # Write back to JS file
    print("Saving updates to projects.js...")
    new_json_str = json.dumps(projects, indent=2, ensure_ascii=False)
    
    new_content = content[:match.start(1)] + new_json_str + content[match.end(1):]

    with open(JS_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    print("Done! You can now refresh your page.")

if __name__ == "__main__":
    main()

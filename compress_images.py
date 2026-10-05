import argparse
from pathlib import Path

from PIL import Image, ImageOps


SITE_DIR = Path(__file__).resolve().parent
IMAGES_DIR = SITE_DIR / "assets" / "images"
SOURCE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
STILL_QUALITY = 82
ANIMATED_QUALITY = 72
FALLBACK_MAX_WIDTH = 960
FALLBACK_STILL_QUALITY = 70
FALLBACK_ANIMATED_QUALITY = 62


def _prepare_frame(frame, max_width):
    if frame.width > max_width:
        frame.thumbnail(
            (max_width, frame.height),
            Image.Resampling.LANCZOS,
        )

    has_transparency = "A" in frame.getbands() or "transparency" in frame.info
    return frame.convert("RGBA" if has_transparency else "RGB")


def _save_webp(source, destination, max_width, still_quality, animated_quality):
    with Image.open(source) as image:
        frame_count = getattr(image, "n_frames", 1)
        if frame_count > 1:
            frames = []
            durations = []
            for frame_index in range(frame_count):
                image.seek(frame_index)
                frames.append(_prepare_frame(image.convert("RGBA"), max_width))
                duration = image.info.get("duration", 100)
                durations.append(100 if duration is None else int(duration))

            frames[0].save(
                destination,
                format="WEBP",
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=image.info.get("loop", 0),
                quality=animated_quality,
                method=4,
            )
        else:
            frame = ImageOps.exif_transpose(image)
            frame = _prepare_frame(frame, max_width)
            frame.save(
                destination,
                format="WEBP",
                quality=still_quality,
                method=4,
            )


def optimize_images(directory, max_width=1200, force=False):
    if max_width < 1:
        raise ValueError("max_width must be greater than zero")

    directory = Path(directory)
    if not directory.is_dir():
        raise FileNotFoundError(f"Image directory does not exist: {directory}")

    image_paths = sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS
    )
    total_original_bytes = 0
    total_optimized_bytes = 0
    processed_count = 0
    skipped_count = 0

    for path in image_paths:
        destination = path.with_name(f"{path.stem}.optimized.webp")
        temporary_path = destination.with_name(
            f"{destination.stem}.tmp{destination.suffix}"
        )
        if (
            not force
            and destination.is_file()
            and destination.stat().st_mtime_ns >= path.stat().st_mtime_ns
        ):
            skipped_count += 1
            print(f"Already optimized: {path.name}")
            continue

        try:
            _save_webp(
                path,
                temporary_path,
                max_width,
                STILL_QUALITY,
                ANIMATED_QUALITY,
            )
            if temporary_path.stat().st_size >= path.stat().st_size:
                _save_webp(
                    path,
                    temporary_path,
                    min(max_width, FALLBACK_MAX_WIDTH),
                    FALLBACK_STILL_QUALITY,
                    FALLBACK_ANIMATED_QUALITY,
                )
            if temporary_path.stat().st_size >= path.stat().st_size:
                temporary_path.unlink()
                print(f"Kept original: {path.name} (WebP copy was not smaller)")
                continue

            temporary_path.replace(destination)
        except (OSError, ValueError) as error:
            temporary_path.unlink(missing_ok=True)
            print(f"ERROR: Could not optimize {path}: {error}")
            raise

        source_size = path.stat().st_size
        optimized_size = destination.stat().st_size
        processed_count += 1
        total_original_bytes += source_size
        total_optimized_bytes += optimized_size
        reduction = 1 - optimized_size / source_size if source_size else 0
        print(
            f"{path.name}: {source_size / 1024:.0f} KB -> "
            f"{optimized_size / 1024:.0f} KB ({reduction:.0%} smaller)"
        )

    total_reduction = (
        1 - total_optimized_bytes / total_original_bytes
        if total_original_bytes
        else 0
    )
    print(
        f"Optimized {processed_count} images, skipped {skipped_count}: "
        f"{total_original_bytes / 1048576:.1f} MiB -> "
        f"{total_optimized_bytes / 1048576:.1f} MiB "
        f"({total_reduction:.0%} smaller)"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Create smaller WebP copies of portfolio images."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        type=Path,
        default=IMAGES_DIR,
        help="Image directory (defaults to this site's assets/images folder)",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=1200,
        help="Maximum width for generated images (default: 1200px)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate WebP copies that already exist",
    )
    args = parser.parse_args()
    optimize_images(args.directory, max_width=args.max_width, force=args.force)


if __name__ == "__main__":
    main()

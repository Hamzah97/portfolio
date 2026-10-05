import argparse
import subprocess
from pathlib import Path

import imageio_ffmpeg


SITE_DIR = Path(__file__).resolve().parent
VIDEOS_DIR = SITE_DIR / "assets" / "videos"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v"}
DEFAULT_MAX_WIDTH = 960
DEFAULT_CRF = 30
DEFAULT_PRESET = "medium"


def compress_videos(
    paths,
    max_width=DEFAULT_MAX_WIDTH,
    crf=DEFAULT_CRF,
    preset=DEFAULT_PRESET,
    force=False,
):
    if max_width < 2:
        raise ValueError("max_width must be at least 2 pixels")
    if not 0 <= crf <= 51:
        raise ValueError("crf must be between 0 and 51")

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    total_original_bytes = 0
    total_output_bytes = 0
    compressed_count = 0
    skipped_count = 0

    for source in paths:
        source = Path(source)
        if not source.is_file():
            raise FileNotFoundError(f"Video file does not exist: {source}")
        if source.stem.endswith(".optimized"):
            raise ValueError(f"Refusing to recompress an optimized video: {source}")
        if source.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError(f"Unsupported video format: {source}")

        destination = source.with_name(f"{source.stem}.optimized.mp4")
        temporary = destination.with_name(f"{destination.stem}.tmp.mp4")
        if (
            not force
            and destination.is_file()
            and destination.stat().st_mtime_ns >= source.stat().st_mtime_ns
        ):
            skipped_count += 1
            source_size = source.stat().st_size
            output_size = destination.stat().st_size
            if output_size < source_size:
                total_original_bytes += source_size
                total_output_bytes += output_size
            print(f"Already compressed: {source.name}")
            continue

        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            f"scale='min({max_width},iw)':-2",
            "-c:v",
            "libx264",
            "-preset",
            preset,
            "-crf",
            str(crf),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-movflags",
            "+faststart",
            str(temporary),
        ]

        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            if not temporary.is_file() or temporary.stat().st_size == 0:
                raise RuntimeError(f"FFmpeg produced no output for {source}")
            temporary.replace(destination)
        except (OSError, subprocess.CalledProcessError, RuntimeError) as error:
            temporary.unlink(missing_ok=True)
            if isinstance(error, subprocess.CalledProcessError):
                detail = error.stderr.strip() or str(error)
                raise RuntimeError(f"FFmpeg failed for {source}: {detail}") from error
            raise

        source_size = source.stat().st_size
        output_size = destination.stat().st_size
        if output_size >= source_size:
            destination.unlink()
            print(
                f"Kept original: {source.name} "
                f"(compressed copy was not smaller)"
            )
            skipped_count += 1
            continue

        compressed_count += 1
        total_original_bytes += source_size
        total_output_bytes += output_size
        reduction = 1 - output_size / source_size if source_size else 0
        print(
            f"{source.name}: {source_size / 1048576:.1f} MiB -> "
            f"{output_size / 1048576:.1f} MiB ({reduction:.0%} smaller)"
        )

    total_reduction = (
        1 - total_output_bytes / total_original_bytes
        if total_original_bytes
        else 0
    )
    print(
        f"Compressed {compressed_count} videos, skipped {skipped_count}: "
        f"{total_original_bytes / 1048576:.1f} MiB -> "
        f"{total_output_bytes / 1048576:.1f} MiB "
        f"({total_reduction:.0%} smaller)"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Create web-ready H.264 MP4 copies of portfolio videos."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Specific video files; defaults to all supported videos under assets/videos",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=DEFAULT_MAX_WIDTH,
        help="Maximum output width in pixels (default: 960)",
    )
    parser.add_argument(
        "--crf",
        type=int,
        default=DEFAULT_CRF,
        help="H.264 quality setting; lower means higher quality (default: 30)",
    )
    parser.add_argument(
        "--preset",
        default=DEFAULT_PRESET,
        help="H.264 speed/compression preset (default: medium)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate compressed copies that already exist",
    )
    args = parser.parse_args()

    paths = args.paths or sorted(
        path
        for path in VIDEOS_DIR.rglob("*")
        if (
            path.is_file()
            and path.suffix.lower() in VIDEO_EXTENSIONS
            and not path.stem.endswith(".optimized")
        )
    )
    compress_videos(
        paths,
        max_width=args.max_width,
        crf=args.crf,
        preset=args.preset,
        force=args.force,
    )


if __name__ == "__main__":
    main()

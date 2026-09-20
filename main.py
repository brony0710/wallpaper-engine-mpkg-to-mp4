"""
Wallpaper Engine MPKG to MP4 Converter - Main Entry Point
Licensed under the MIT License.
Copyright (c) 2026 Brony-PC.
"""

import argparse
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from extractor import extract_media_from_we_package


def run_cli(input_files, output_dir):
    print("=" * 60)
    print("Wallpaper Engine MPKG/PKG to MP4 Extractor (CLI Mode)")
    print("MIT License - Copyright (c) 2026 Brony-PC")
    print("=" * 60)

    total_extracted = 0
    for idx, f in enumerate(input_files, 1):
        print(f"\n[{idx}/{len(input_files)}] Processing: {f}")
        try:
            results = extract_media_from_we_package(
                file_path=f,
                output_dir=output_dir,
                log_cb=print,
                progress_cb=lambda p: print(f"Progress: {int(p*100)}%", end="\r")
            )
            total_extracted += len(results)
        except Exception as err:
            print(f"[ERROR] {err}")

    print("\n" + "=" * 60)
    print(f"Finished! Total videos extracted: {total_extracted}")
    print(f"Destination folder: {os.path.abspath(output_dir)}")
    print("=" * 60)


def main():
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--gui"):
        parser = argparse.ArgumentParser(description="Wallpaper Engine MPKG to MP4 Extractor")
        parser.add_argument("files", nargs="+", help="List of .mpkg or .pkg files")
        parser.add_argument("-o", "--output", default="extracted_videos", help="Target output folder")
        args = parser.parse_args()
        run_cli(args.files, args.output)
    else:
        from gui import launch_gui
        launch_gui()


if __name__ == "__main__":
    main()

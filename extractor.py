"""
Wallpaper Engine Package Extractor & Inspector (.mpkg / .pkg to MP4)
Copyright (c) 2026 brony0710 (https://github.com/brony0710).
Licensed under the MIT License.

This module provides:
- Fast package inspection without full extraction (reads project.json, preview thumbnail, file listing)
- Selective extraction (extract only user-selected assets)
- Smart output naming (using wallpaper title, original name, or archive name)
- Clock widget detection in project.json
"""

import io
import json
import os
import re
import struct
import zipfile
from typing import Any, Callable, Dict, List, Optional, Tuple

VIDEO_EXTENSIONS = ('.mp4', '.m4v', '.webm', '.mkv', '.avi', '.mov', '.flv')
AUDIO_EXTENSIONS = ('.mp3', '.ogg', '.wav', '.flac')
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')


class PackageEntry:
    def __init__(self, full_path: str, offset: int, length: int):
        self.full_path = full_path.replace('\\', '/')
        self.offset = offset
        self.length = length

    @property
    def clean_name(self) -> str:
        return os.path.basename(self.full_path)

    @property
    def category(self) -> str:
        low = self.full_path.lower()
        if low.endswith(VIDEO_EXTENSIONS):
            return 'video'
        elif low.endswith(AUDIO_EXTENSIONS):
            return 'audio'
        elif low.endswith(IMAGE_EXTENSIONS):
            return 'image'
        elif low.endswith(('.json', '.xml', '.txt', '.ini')):
            return 'config'
        elif low.endswith(('.pkg', '.mpkg')):
            return 'package'
        return 'other'

    def is_video(self) -> bool:
        return self.category == 'video'

    def is_audio(self) -> bool:
        return self.category == 'audio'


def read_string_i32(stream: io.BufferedReader) -> Optional[str]:
    """Reads a 4-byte uint32 length-prefixed UTF-8 string."""
    raw_len = stream.read(4)
    if len(raw_len) < 4:
        return None
    (length,) = struct.unpack('<I', raw_len)
    if length > 10 * 1024 * 1024:  # 10 MB safety limit
        return None
    data = stream.read(length)
    return data.decode('utf-8', errors='replace')


def is_zip_container(file_path: str) -> bool:
    """Checks whether the file is a standard ZIP container (PK\x03\x04 header)."""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(4)
            return header.startswith(b'PK\x03\x04')
    except Exception:
        return False


def parse_binary_package(stream: io.BufferedReader) -> Tuple[str, List[PackageEntry], int]:
    """
    Parses a Wallpaper Engine binary package structure.
    Returns: (magic_version, entries, data_start_offset)
    """
    magic = read_string_i32(stream)
    if not magic:
        raise ValueError("Invalid package header or empty file.")

    raw_count = stream.read(4)
    if len(raw_count) < 4:
        raise ValueError("Corrupted header: unable to read entry count.")
    (entry_count,) = struct.unpack('<I', raw_count)

    if entry_count < 0 or entry_count > 100000:
        raise ValueError(f"Abnormal file count ({entry_count}). Unsupported package format.")

    entries: List[PackageEntry] = []
    for _ in range(entry_count):
        full_path = read_string_i32(stream)
        if full_path is None:
            raise ValueError("Corrupted directory structure while reading file path.")
        
        meta = stream.read(8)
        if len(meta) < 8:
            raise ValueError("Corrupted directory structure while reading entry metadata.")
        offset, length = struct.unpack('<II', meta)
        entries.append(PackageEntry(full_path, offset, length))

    data_start = stream.tell()
    return magic, entries, data_start


def sanitize_filename(name: str) -> str:
    """Sanitizes illegal Windows characters from a filename."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = clean.strip().replace(" ", "_")
    return clean or "wallpaper"


def inspect_we_package(file_path: str) -> Dict[str, Any]:
    """
    Performs quick package inspection without extracting files to disk.
    Reads project.json metadata and preview thumbnail in-memory.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    archive_name = os.path.splitext(os.path.basename(file_path))[0]
    result: Dict[str, Any] = {
        "file_path": file_path,
        "archive_name": archive_name,
        "file_size": os.path.getsize(file_path),
        "format": "Unknown",
        "title": archive_name,
        "type": "video",
        "description": "",
        "thumbnail_bytes": None,
        "clock_widget_detected": False,
        "clock_details": "",
        "entries": [],
        "video_count": 0,
        "audio_count": 0,
        "image_count": 0,
    }

    # Case A: ZIP Container
    if is_zip_container(file_path):
        result["format"] = "ZIP Container"
        with zipfile.ZipFile(file_path, 'r') as zf:
            namelist = zf.namelist()
            for name in namelist:
                info = zf.getinfo(name)
                if not info.is_dir():
                    entry = PackageEntry(name, 0, info.file_size)
                    result["entries"].append(entry)

            # Find project.json
            for name in namelist:
                if os.path.basename(name).lower() == 'project.json':
                    try:
                        raw_json = zf.read(name).decode('utf-8', errors='ignore')
                        pj = json.loads(raw_json)
                        _populate_project_metadata(pj, result)
                    except Exception:
                        pass
                    break

            # Find preview image
            for name in namelist:
                low = os.path.basename(name).lower()
                if low.startswith('preview') and low.endswith(IMAGE_EXTENSIONS):
                    try:
                        result["thumbnail_bytes"] = zf.read(name)
                    except Exception:
                        pass
                    break

    # Case B: Binary PKG (PKGV0001-0003, PKGM0014, etc.)
    else:
        with open(file_path, 'rb') as f:
            magic, entries, data_start = parse_binary_package(f)
            result["format"] = f"Binary ({magic})"
            result["entries"] = entries

            # Find project.json
            for entry in entries:
                if entry.clean_name.lower() == 'project.json':
                    f.seek(data_start + entry.offset)
                    raw_bytes = f.read(entry.length)
                    try:
                        pj = json.loads(raw_bytes.decode('utf-8', errors='ignore'))
                        _populate_project_metadata(pj, result)
                    except Exception:
                        pass
                    break

            # Find preview image
            for entry in entries:
                low = entry.clean_name.lower()
                if (low.startswith('preview') or 'preview' in low) and low.endswith(IMAGE_EXTENSIONS):
                    f.seek(data_start + entry.offset)
                    result["thumbnail_bytes"] = f.read(entry.length)
                    break

    # Count categories
    for e in result["entries"]:
        if e.is_video():
            result["video_count"] += 1
        elif e.is_audio():
            result["audio_count"] += 1
        elif e.category == 'image':
            result["image_count"] += 1

    return result


def _populate_project_metadata(pj: dict, result: dict):
    """Extracts title, description, wallpaper type, and inspects clock widget properties."""
    if "title" in pj and pj["title"]:
        result["title"] = str(pj["title"])
    if "type" in pj and pj["type"]:
        result["type"] = str(pj["type"])
    if "description" in pj and pj["description"]:
        result["description"] = str(pj["description"])

    # Detect clock / time widget properties
    general = pj.get("general", {})
    props = general.get("properties", {})
    clock_keys = [k for k in props.keys() if any(w in k.lower() for w in ['clock', 'time', 'jam', 'timer', 'date'])]
    if clock_keys:
        result["clock_widget_detected"] = True
        result["clock_details"] = (
            f"Clock widget properties found: {', '.join(clock_keys)}. "
            "Good news: the raw MP4 video stream inside is 100% clean without this overlay!"
        )


def extract_custom_entries(
    file_path: str,
    output_dir: str,
    target_entry_paths: List[str],
    naming_mode: str = "original",
    custom_title: str = "",
    log_cb: Optional[Callable[[str], None]] = None,
    progress_cb: Optional[Callable[[float], None]] = None,
) -> List[str]:
    """
    Extracts specific user-selected files from the package.
    
    naming_mode:
      - 'title': Uses wallpaper title (e.g. 'Wallpaper_Title.mp4')
      - 'original': Uses the internal file name
      - 'archive': Uses the .mpkg archive file name
    """
    def log(msg: str):
        if log_cb:
            log_cb(msg)
        else:
            print(msg)

    def update_progress(val: float):
        if progress_cb:
            progress_cb(val)

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    os.makedirs(output_dir, exist_ok=True)
    extracted_files: List[str] = []

    target_set = set(target_entry_paths)
    if not target_set:
        log("[WARNING] No files selected for extraction.")
        return []

    archive_stem = os.path.splitext(os.path.basename(file_path))[0]
    safe_title = sanitize_filename(custom_title) if custom_title else sanitize_filename(archive_stem)

    total_items = len(target_set)
    processed = 0

    # Case A: ZIP
    if is_zip_container(file_path):
        with zipfile.ZipFile(file_path, 'r') as zf:
            for item_path in target_set:
                try:
                    orig_name = os.path.basename(item_path)
                    _, ext = os.path.splitext(orig_name)

                    if naming_mode == "title" and orig_name.lower().endswith(VIDEO_EXTENSIONS):
                        dest_name = f"{safe_title}{ext}"
                    elif naming_mode == "archive" and orig_name.lower().endswith(VIDEO_EXTENSIONS):
                        dest_name = f"{archive_stem}{ext}"
                    else:
                        dest_name = orig_name

                    dest_path = _get_unique_path(output_dir, dest_name)
                    log(f"[PROCESS] Extracting '{orig_name}' -> '{os.path.basename(dest_path)}'...")

                    with zf.open(item_path) as src, open(dest_path, 'wb') as dst:
                        while chunk := src.read(1024 * 1024):
                            dst.write(chunk)

                    size_mb = os.path.getsize(dest_path) / (1024 * 1024)
                    log(f"[SUCCESS] Saved: {dest_path} ({size_mb:.2f} MB)")
                    extracted_files.append(dest_path)
                except Exception as e:
                    log(f"[ERROR] Failed to extract '{item_path}': {e}")

                processed += 1
                update_progress(processed / total_items)
        return extracted_files

    # Case B: Binary PKG
    with open(file_path, 'rb') as f:
        magic, entries, data_start = parse_binary_package(f)
        matched_entries = [e for e in entries if e.full_path in target_set or e.clean_name in target_set]

        for entry in matched_entries:
            orig_name = entry.clean_name
            _, ext = os.path.splitext(orig_name)

            if naming_mode == "title" and orig_name.lower().endswith(VIDEO_EXTENSIONS):
                dest_name = f"{safe_title}{ext}"
            elif naming_mode == "archive" and orig_name.lower().endswith(VIDEO_EXTENSIONS):
                dest_name = f"{archive_stem}{ext}"
            else:
                dest_name = orig_name

            dest_path = _get_unique_path(output_dir, dest_name)
            log(f"[PROCESS] Extracting '{orig_name}' ({entry.length / (1024*1024):.2f} MB) -> '{os.path.basename(dest_path)}'...")

            f.seek(data_start + entry.offset)
            bytes_left = entry.length
            with open(dest_path, 'wb') as out_f:
                while bytes_left > 0:
                    read_size = min(1024 * 1024, bytes_left)
                    chunk = f.read(read_size)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    bytes_left -= len(chunk)

            size_mb = os.path.getsize(dest_path) / (1024 * 1024)
            log(f"[SUCCESS] Saved: {dest_path} ({size_mb:.2f} MB)")
            extracted_files.append(dest_path)

            processed += 1
            update_progress(processed / total_items)

    return extracted_files


def _get_unique_path(directory: str, filename: str) -> str:
    """Generates a unique destination path to avoid overwriting existing files."""
    base_stem, ext = os.path.splitext(filename)
    dest_path = os.path.join(directory, filename)
    counter = 1
    while os.path.exists(dest_path):
        dest_path = os.path.join(directory, f"{base_stem}_{counter}{ext}")
        counter += 1
    return dest_path


def extract_media_from_we_package(
    file_path: str,
    output_dir: str,
    log_cb: Optional[Callable[[str], None]] = None,
    progress_cb: Optional[Callable[[float], None]] = None,
) -> List[str]:
    """Compatibility function to automatically extract all videos."""
    info = inspect_we_package(file_path)
    video_paths = [e.full_path for e in info["entries"] if e.is_video()]
    if not video_paths:
        if log_cb:
            if info["type"].lower() == "scene" or any(e.clean_name.endswith('.tex') for e in info["entries"]):
                log_cb("[INFO] This wallpaper is a 'Scene' type (real-time script canvas render, not a video recording).")
                log_cb("[TIPS] For Scene wallpapers, using screen recording (e.g. OBS Studio) while playing is recommended.")
            else:
                log_cb("[WARNING] No video files found in this package.")
        return []

    return extract_custom_entries(
        file_path=file_path,
        output_dir=output_dir,
        target_entry_paths=video_paths,
        naming_mode="original",
        log_cb=log_cb,
        progress_cb=progress_cb
    )

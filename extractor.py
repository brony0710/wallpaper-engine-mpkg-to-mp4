"""
Wallpaper Engine Package Extractor & Inspector (.mpkg / .pkg to MP4)
Licensed under the MIT License.
Copyright (c) 2026 Brony-PC.

Modul ini mendukung:
- Inspeksi instan tanpa ekstraksi (membaca project.json, thumbnail preview, daftar berkas)
- Ekstraksi selektif (pengguna memilih berkas apa saja yang ingin dikeluarkan)
- Opsi penamaan cerdas (menggunakan judul asli wallpaper, nama file, dll.)
- Deteksi widget jam (clock overlay) di project.json
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
    """Membaca string berawalan 4-byte uint32 panjang dalam format UTF-8."""
    raw_len = stream.read(4)
    if len(raw_len) < 4:
        return None
    (length,) = struct.unpack('<I', raw_len)
    if length > 10 * 1024 * 1024:  # Batas wajar 10 MB
        return None
    data = stream.read(length)
    return data.decode('utf-8', errors='replace')


def is_zip_container(file_path: str) -> bool:
    """Mengecek apakah berkas merupakan arsip ZIP (header PK\x03\x04)."""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(4)
            return header.startswith(b'PK\x03\x04')
    except Exception:
        return False


def parse_binary_package(stream: io.BufferedReader) -> Tuple[str, List[PackageEntry], int]:
    """
    Mem-parsing struktur biner paket Wallpaper Engine.
    Mengembalikan: (magic_version, entries, data_start_offset)
    """
    magic = read_string_i32(stream)
    if not magic:
        raise ValueError("Header paket tidak valid atau file kosong.")

    raw_count = stream.read(4)
    if len(raw_count) < 4:
        raise ValueError("Header rusak: tidak dapat membaca jumlah entri file.")
    (entry_count,) = struct.unpack('<I', raw_count)

    if entry_count < 0 or entry_count > 100000:
        raise ValueError(f"Jumlah file tidak wajar ({entry_count}). Format mungkin tidak didukung.")

    entries: List[PackageEntry] = []
    for _ in range(entry_count):
        full_path = read_string_i32(stream)
        if full_path is None:
            raise ValueError("Struktur direktori rusak saat membaca nama file.")
        
        meta = stream.read(8)
        if len(meta) < 8:
            raise ValueError("Struktur direktori rusak saat membaca metadata file.")
        offset, length = struct.unpack('<II', meta)
        entries.append(PackageEntry(full_path, offset, length))

    data_start = stream.tell()
    return magic, entries, data_start


def sanitize_filename(name: str) -> str:
    """Membersihkan karakter ilegal dari nama berkas pada Windows."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = clean.strip().replace(" ", "_")
    return clean or "wallpaper"


def inspect_we_package(file_path: str) -> Dict[str, Any]:
    """
    Melakukan inspeksi cepat terhadap isi paket tanpa mengekstrak seluruh file.
    Mengekstrak metadata project.json dan gambar preview langsung dalam memori.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File tidak ditemukan: {file_path}")

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

    # Kasus A: Arsip ZIP / Mobile Package
    if is_zip_container(file_path):
        result["format"] = "ZIP Container"
        with zipfile.ZipFile(file_path, 'r') as zf:
            namelist = zf.namelist()
            for name in namelist:
                info = zf.getinfo(name)
                if not info.is_dir():
                    entry = PackageEntry(name, 0, info.file_size)
                    result["entries"].append(entry)

            # Cari project.json
            for name in namelist:
                if os.path.basename(name).lower() == 'project.json':
                    try:
                        raw_json = zf.read(name).decode('utf-8', errors='ignore')
                        pj = json.loads(raw_json)
                        _populate_project_metadata(pj, result)
                    except Exception:
                        pass
                    break

            # Cari preview image
            for name in namelist:
                low = os.path.basename(name).lower()
                if low.startswith('preview') and low.endswith(IMAGE_EXTENSIONS):
                    try:
                        result["thumbnail_bytes"] = zf.read(name)
                    except Exception:
                        pass
                    break

    # Kasus B: Binary PKG Wallpaper Engine
    else:
        with open(file_path, 'rb') as f:
            magic, entries, data_start = parse_binary_package(f)
            result["format"] = f"Binary ({magic})"
            result["entries"] = entries

            # Cari project.json
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

            # Cari preview image
            for entry in entries:
                low = entry.clean_name.lower()
                if (low.startswith('preview') or 'preview' in low) and low.endswith(IMAGE_EXTENSIONS):
                    f.seek(data_start + entry.offset)
                    result["thumbnail_bytes"] = f.read(entry.length)
                    break

    # Hitung kategori
    for e in result["entries"]:
        if e.is_video():
            result["video_count"] += 1
        elif e.is_audio():
            result["audio_count"] += 1
        elif e.category == 'image':
            result["image_count"] += 1

    return result


def _populate_project_metadata(pj: dict, result: dict):
    """Mengekstrak judul, deskripsi, tipe wallpaper, dan memeriksa properti jam (clock)."""
    if "title" in pj and pj["title"]:
        result["title"] = str(pj["title"])
    if "type" in pj and pj["type"]:
        result["type"] = str(pj["type"])
    if "description" in pj and pj["description"]:
        result["description"] = str(pj["description"])

    # Deteksi properti jam (clock widget / time widget)
    general = pj.get("general", {})
    props = general.get("properties", {})
    clock_keys = [k for k in props.keys() if any(w in k.lower() for w in ['clock', 'time', 'jam', 'timer', 'date'])]
    if clock_keys:
        result["clock_widget_detected"] = True
        result["clock_details"] = f"Ditemukan konfigurasi widget jam: {', '.join(clock_keys)}. Video MP4 di dalam paket adalah video asli tanpa widget ini."


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
    Mengekstrak berkas tertentu yang dipilih pengguna dari paket.
    
    naming_mode:
      - 'title': Menggunakan judul wallpaper (misal: 'Nama_Wallpaper.mp4')
      - 'original': Menggunakan nama asli berkas di dalam arsip
      - 'archive': Menggunakan nama file paket .mpkg itu sendiri
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
        raise FileNotFoundError(f"File tidak ditemukan: {file_path}")

    os.makedirs(output_dir, exist_ok=True)
    extracted_files: List[str] = []

    target_set = set(target_entry_paths)
    if not target_set:
        log("[PERINGATAN] Tidak ada berkas yang dipilih untuk diekstrak.")
        return []

    archive_stem = os.path.splitext(os.path.basename(file_path))[0]
    safe_title = sanitize_filename(custom_title) if custom_title else sanitize_filename(archive_stem)

    total_items = len(target_set)
    processed = 0

    # Kasus A: ZIP
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
                    log(f"[PROSES] Mengekstrak '{orig_name}' -> '{os.path.basename(dest_path)}'...")

                    with zf.open(item_path) as src, open(dest_path, 'wb') as dst:
                        while chunk := src.read(1024 * 1024):
                            dst.write(chunk)

                    size_mb = os.path.getsize(dest_path) / (1024 * 1024)
                    log(f"[SUKSES] Berhasil disimpan: {dest_path} ({size_mb:.2f} MB)")
                    extracted_files.append(dest_path)
                except Exception as e:
                    log(f"[ERROR] Gagal mengekstrak '{item_path}': {e}")

                processed += 1
                update_progress(processed / total_items)
        return extracted_files

    # Kasus B: Binary PKG
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
            log(f"[PROSES] Mengekstrak '{orig_name}' ({entry.length / (1024*1024):.2f} MB) -> '{os.path.basename(dest_path)}'...")

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
            log(f"[SUKSES] Berhasil disimpan: {dest_path} ({size_mb:.2f} MB)")
            extracted_files.append(dest_path)

            processed += 1
            update_progress(processed / total_items)

    return extracted_files


def _get_unique_path(directory: str, filename: str) -> str:
    """Menghasilkan path unik untuk menghindari menimpa file yang sudah ada."""
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
    """Fungsi kompatibilitas ke belakang untuk mengekstrak seluruh video otomatis."""
    info = inspect_we_package(file_path)
    video_paths = [e.full_path for e in info["entries"] if e.is_video()]
    if not video_paths:
        if log_cb:
            if info["type"].lower() == "scene" or any(e.clean_name.endswith('.tex') for e in info["entries"]):
                log_cb("[INFO] Wallpaper ini adalah tipe 'Scene' (render script 2D/3D), bukan rekaman video.")
                log_cb("[TIPS] Untuk tipe Scene, gunakan perekam layar (seperti OBS Studio) saat wallpaper diputar.")
            else:
                log_cb("[PERINGATAN] Tidak ditemukan file video di dalam paket ini.")
        return []

    return extract_custom_entries(
        file_path=file_path,
        output_dir=output_dir,
        target_entry_paths=video_paths,
        naming_mode="original",
        log_cb=log_cb,
        progress_cb=progress_cb
    )

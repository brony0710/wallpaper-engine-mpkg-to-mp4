"""
Wallpaper Engine MPKG to MP4 Converter - Modern CustomTkinter GUI with Preview & Selective Output
Licensed under the MIT License.
Copyright (c) 2026 Brony-PC.
"""

import io
import os
import subprocess
import sys
import threading
from datetime import datetime
from typing import Dict, List, Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image

from extractor import (
    inspect_we_package,
    extract_custom_entries,
    sanitize_filename,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
)


class ConverterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Konfigurasi Tema & Jendela
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.title("Wallpaper Engine MPKG to MP4 Extractor & Preview")
        self.geometry("980x740")
        self.minsize(860, 640)

        # State Data
        self.current_file_path: Optional[str] = None
        self.package_info: Optional[Dict] = None
        self.entry_checkboxes: Dict[str, ctk.CTkCheckBox] = {}
        self.output_dir: str = os.path.join(os.path.expanduser("~"), "Videos", "WallpaperEngine_Extracted")
        self.last_extracted_video: Optional[str] = None
        self.is_processing: bool = False

        self._create_ui()

    def _create_ui(self):
        # 1. Header Frame
        header = ctk.CTkFrame(self, corner_radius=12, fg_color=("#2b2b2b", "#1a1a1a"))
        header.pack(fill="x", padx=16, pady=(14, 8))

        top_row = ctk.CTkFrame(header, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=(10, 4))

        title_lbl = ctk.CTkLabel(
            top_row,
            text="🎬 Wallpaper Engine MPKG to MP4 Inspector & Extractor",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("#3B8ED0", "#38bdf8")
        )
        title_lbl.pack(side="left")

        # Tombol Info Lisensi & Solusi Jam
        btn_about = ctk.CTkButton(
            top_row,
            text="ℹ️ Info Lisensi & Solusi Jam",
            width=180,
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#374151", "#27272a"),
            hover_color=("#4b5563", "#3f3f46"),
            command=self._show_about_dialog
        )
        btn_about.pack(side="right")

        sub_lbl = ctk.CTkLabel(
            header,
            text="Pratinjau isi wallpaper, pilah berkas output, dan dapatkan video MP4 murni tanpa gangguan widget jam.",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        sub_lbl.pack(anchor="w", padx=16, pady=(0, 10))

        # 2. File & Output Path Bar
        path_bar = ctk.CTkFrame(self, corner_radius=10)
        path_bar.pack(fill="x", padx=16, pady=4)

        # Baris Pilih File
        f_row = ctk.CTkFrame(path_bar, fg_color="transparent")
        f_row.pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(f_row, text="File Input:", width=80, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.file_entry = ctk.CTkEntry(f_row, placeholder_text="Pilih berkas .mpkg atau .pkg untuk diinspeksi...", font=ctk.CTkFont(size=11))
        self.file_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        self.btn_browse_file = ctk.CTkButton(
            f_row, text="📂 Buka Berkas", width=120, command=self._choose_and_load_file
        )
        self.btn_browse_file.pack(side="right")

        # Baris Folder Output
        o_row = ctk.CTkFrame(path_bar, fg_color="transparent")
        o_row.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(o_row, text="Simpan ke:", width=80, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.out_entry = ctk.CTkEntry(o_row, font=ctk.CTkFont(size=11))
        self.out_entry.insert(0, self.output_dir)
        self.out_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_browse_out = ctk.CTkButton(
            o_row, text="📁 Ubah Folder", width=120, fg_color=("#475569", "#334155"), command=self._choose_output_dir
        )
        self.btn_browse_out.pack(side="right")

        # 3. Main Body Split Area (Left: Preview & Metadata, Right: File Selector & Output Options)
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=6)

        # LEFT COLUMN: Preview & Info (Lebar tetap ~330px)
        left_col = ctk.CTkFrame(body, width=330, corner_radius=12)
        left_col.pack(side="left", fill="y", padx=(0, 8), pady=0)
        left_col.pack_propagate(False)

        ctk.CTkLabel(left_col, text="🖼️ Pratinjau Wallpaper", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))

        # Thumbnail Image Display
        self.thumb_frame = ctk.CTkFrame(left_col, height=190, fg_color=("#18181b", "#121214"), corner_radius=8)
        self.thumb_frame.pack(fill="x", padx=12, pady=(0, 8))
        self.thumb_frame.pack_propagate(False)

        self.thumb_label = ctk.CTkLabel(self.thumb_frame, text="Tidak ada pratinjau\n(Pilih file terlebih dahulu)", text_color="gray")
        self.thumb_label.pack(expand=True)

        # Metadata Card
        meta_frame = ctk.CTkScrollableFrame(left_col, corner_radius=8, fg_color=("#27272a", "#1e1e24"))
        meta_frame.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        self.lbl_title = ctk.CTkLabel(meta_frame, text="Judul: -", font=ctk.CTkFont(size=13, weight="bold"), anchor="w", wraplength=280)
        self.lbl_title.pack(fill="x", pady=2)

        self.lbl_type = ctk.CTkLabel(meta_frame, text="Tipe: -", font=ctk.CTkFont(size=11), text_color="gray", anchor="w")
        self.lbl_type.pack(fill="x", pady=1)

        self.lbl_format = ctk.CTkLabel(meta_frame, text="Format: -", font=ctk.CTkFont(size=11), text_color="gray", anchor="w")
        self.lbl_format.pack(fill="x", pady=1)

        self.lbl_size = ctk.CTkLabel(meta_frame, text="Ukuran Paket: -", font=ctk.CTkFont(size=11), text_color="gray", anchor="w")
        self.lbl_size.pack(fill="x", pady=1)

        # Alert Box Masalah Jam
        self.clock_alert_box = ctk.CTkFrame(meta_frame, corner_radius=6, fg_color=("#1e3a2f", "#142c22"))
        self.lbl_clock_status = ctk.CTkLabel(
            self.clock_alert_box,
            text="⏱️ Status Jam: Siap diperiksa",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#86efac", "#4ade80"),
            wraplength=270,
            justify="left"
        )
        self.lbl_clock_status.pack(padx=8, pady=6)

        # RIGHT COLUMN: Content Inspector & Output Settings
        right_col = ctk.CTkFrame(body, corner_radius=12)
        right_col.pack(side="right", fill="both", expand=True, pady=0)

        # Header Filter Berkas
        filter_header = ctk.CTkFrame(right_col, fg_color="transparent")
        filter_header.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            filter_header, text="📋 Daftar Berkas di Dalam Paket (Pilih yang ingin diekstrak):",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(side="left")

        # Tombol Filter Cepat
        btn_filter_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        btn_filter_frame.pack(fill="x", padx=12, pady=(0, 6))

        ctk.CTkButton(
            btn_filter_frame, text="🎬 Hanya Video", width=95, height=24, font=ctk.CTkFont(size=11),
            command=lambda: self._apply_filter('video')
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            btn_filter_frame, text="🎵 Video + Audio", width=105, height=24, font=ctk.CTkFont(size=11),
            fg_color=("#475569", "#334155"), command=lambda: self._apply_filter('media')
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            btn_filter_frame, text="Semua", width=65, height=24, font=ctk.CTkFont(size=11),
            fg_color=("#475569", "#334155"), command=lambda: self._apply_filter('all')
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            btn_filter_frame, text="Batal Pilih", width=75, height=24, font=ctk.CTkFont(size=11),
            fg_color="transparent", text_color="gray", command=lambda: self._apply_filter('none')
        ).pack(side="left")

        # Scrollable Frame untuk Daftar File
        self.file_list_frame = ctk.CTkScrollableFrame(right_col, corner_radius=8, fg_color=("#18181b", "#141416"))
        self.file_list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.empty_file_lbl = ctk.CTkLabel(
            self.file_list_frame,
            text="Pilih file .mpkg / .pkg di atas untuk menampilkan daftar berkas.",
            text_color="gray"
        )
        self.empty_file_lbl.pack(expand=True, pady=40)

        # Pengaturan Opsi Penamaan Output
        naming_row = ctk.CTkFrame(right_col, fg_color="transparent")
        naming_row.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(naming_row, text="Penamaan File Output:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))
        self.naming_combo = ctk.CTkComboBox(
            naming_row,
            values=[
                "Gunakan Judul Asli Wallpaper (Rekomendasi)",
                "Gunakan Nama Berkas Asli di Dalam Paket",
                "Gunakan Nama File Arsip .mpkg"
            ],
            width=300,
            font=ctk.CTkFont(size=11)
        )
        self.naming_combo.set("Gunakan Judul Asli Wallpaper (Rekomendasi)")
        self.naming_combo.pack(side="left", fill="x", expand=True)

        # 4. Action & Progress Area
        bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        bottom_bar.pack(fill="x", padx=16, pady=4)

        self.btn_extract = ctk.CTkButton(
            bottom_bar,
            text="🚀 Ekstrak Berkas Terpilih",
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("#16a34a", "#15803d"),
            hover_color=("#15803d", "#166534"),
            command=self._start_extraction_thread
        )
        self.btn_extract.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_open_folder = ctk.CTkButton(
            bottom_bar,
            text="📂 Buka Folder Hasil",
            height=40,
            font=ctk.CTkFont(size=12),
            command=self._open_output_folder
        )
        self.btn_open_folder.pack(side="left", padx=(0, 8))

        self.btn_play_preview = ctk.CTkButton(
            bottom_bar,
            text="▶️ Putar Video",
            height=40,
            width=110,
            font=ctk.CTkFont(size=12),
            fg_color=("#4338ca", "#3730a3"),
            hover_color=("#3730a3", "#312e81"),
            state="disabled",
            command=self._play_extracted_video
        )
        self.btn_play_preview.pack(side="right")

        # Progress bar
        prog_bar_frame = ctk.CTkFrame(self, fg_color="transparent")
        prog_bar_frame.pack(fill="x", padx=16, pady=(0, 2))

        self.progress_bar = ctk.CTkProgressBar(prog_bar_frame)
        self.progress_bar.set(0)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.lbl_progress = ctk.CTkLabel(prog_bar_frame, text="0%", width=45, font=ctk.CTkFont(size=11, weight="bold"))
        self.lbl_progress.pack(side="right")

        # 5. Log Console (Collapsible / Compact)
        log_frame = ctk.CTkFrame(self, height=100, corner_radius=10)
        log_frame.pack(fill="x", padx=16, pady=(2, 12))
        log_frame.pack_propagate(False)

        self.log_box = ctk.CTkTextbox(log_frame, font=ctk.CTkFont(family="Consolas", size=10), wrap="word")
        self.log_box.pack(fill="both", expand=True, padx=6, pady=6)

        self._log("Program siap. Pilih berkas .mpkg atau .pkg untuk melihat pratinjau dan memilih output.")

    def _log(self, text: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{timestamp}] {text}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _choose_and_load_file(self):
        file_path = filedialog.askopenfilename(
            title="Pilih Paket Wallpaper Engine",
            filetypes=[
                ("Wallpaper Engine Package", "*.mpkg;*.pkg"),
                ("Mobile Package (.mpkg)", "*.mpkg"),
                ("Desktop Package (.pkg)", "*.pkg"),
                ("Semua File", "*.*")
            ]
        )
        if file_path:
            self.current_file_path = file_path
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, file_path)
            self._load_package(file_path)

    def _load_package(self, file_path: str):
        self._log(f"Memeriksa paket: {os.path.basename(file_path)}...")
        try:
            info = inspect_we_package(file_path)
            self.package_info = info

            # 1. Tampilkan Thumbnail
            if info["thumbnail_bytes"]:
                try:
                    pil_img = Image.open(io.BytesIO(info["thumbnail_bytes"]))
                    # Resize proporsional max 300x180
                    pil_img.thumbnail((300, 180))
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                    self.thumb_label.configure(image=ctk_img, text="")
                except Exception as e:
                    self.thumb_label.configure(image=None, text="[Gagal memuat gambar preview]")
            else:
                self.thumb_label.configure(image=None, text="[Tidak ada file preview gambar]")

            # 2. Tampilkan Metadata
            self.lbl_title.configure(text=f"Judul: {info['title']}")
            self.lbl_type.configure(text=f"Tipe: {info['type'].capitalize()}")
            self.lbl_format.configure(text=f"Format: {info['format']}")
            self.lbl_size.configure(text=f"Ukuran: {info['file_size'] / (1024*1024):.2f} MB")

            # 3. Status Masalah Jam
            self.clock_alert_box.pack(fill="x", pady=6)
            if info["clock_widget_detected"]:
                self.clock_alert_box.configure(fg_color=("#1e3a2f", "#142c22"))
                self.lbl_clock_status.configure(
                    text="⏱️ Widget Jam Ditemukan di Konfigurasi!\n"
                         "Kabar baik: File video MP4 di dalam paket ini adalah feed asli BERSIH tanpa overlay jam!",
                    text_color=("#86efac", "#4ade80")
                )
                self._log("[INFO] Paket ini memiliki setting widget jam. Video MP4 yang diekstrak akan murni tanpa jam.")
            elif info["type"].lower() == "scene":
                self.clock_alert_box.configure(fg_color=("#3f2d1e", "#312215"))
                self.lbl_clock_status.configure(
                    text="⚠️ Wallpaper Tipe 'Scene' (Interaktif)\n"
                         "Animasi dirender via script canvas, bukan video permanen. Disarankan rekam layar dengan OBS jika ingin MP4.",
                    text_color=("#fde047", "#facc15")
                )
                self._log("[INFO] Tipe Scene terdeteksi.")
            else:
                self.clock_alert_box.configure(fg_color=("#182b3a", "#142330"))
                self.lbl_clock_status.configure(
                    text="✅ Wallpaper Video Bersih\nTidak ada widget jam yang terkonfigurasi.",
                    text_color=("#7dd3fc", "#38bdf8")
                )

            # 4. Tampilkan Daftar File di Checklist
            self._render_file_checklist(info["entries"])
            self._log(f"Paket berhasil dimuat: {len(info['entries'])} berkas ditemukan ({info['video_count']} video).")

        except Exception as err:
            messagebox.showerror("Error Membuka Paket", f"Gagal membaca paket: {err}")
            self._log(f"[ERROR] Gagal membedah paket: {err}")

    def _render_file_checklist(self, entries):
        # Bersihkan widget lama
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()

        self.entry_checkboxes.clear()

        if not entries:
            ctk.CTkLabel(self.file_list_frame, text="Tidak ada file yang ditemukan di dalam arsip.", text_color="gray").pack(pady=20)
            return

        for entry in entries:
            row = ctk.CTkFrame(self.file_list_frame, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=2)

            cb_var = ctk.BooleanVar(value=entry.is_video())
            
            # Badge kategori
            if entry.is_video():
                badge_text, badge_color = "🎬 VIDEO", ("#15803d", "#166534")
            elif entry.is_audio():
                badge_text, badge_color = "🎵 AUDIO", ("#7c3aed", "#6d28d9")
            elif entry.category == 'image':
                badge_text, badge_color = "🖼️ GAMBAR", ("#b45309", "#92400e")
            elif entry.category == 'config':
                badge_text, badge_color = "⚙️ CONFIG", ("#475569", "#334155")
            else:
                badge_text, badge_color = "📦 FILE", ("#3f3f46", "#27272a")

            badge = ctk.CTkLabel(
                row, text=badge_text, font=ctk.CTkFont(size=9, weight="bold"),
                fg_color=badge_color, corner_radius=4, width=70
            )
            badge.pack(side="left", padx=(0, 6))

            size_str = f"{entry.length / (1024*1024):.2f} MB" if entry.length >= 1024*1024 else f"{entry.length / 1024:.1f} KB"
            display_text = f"{entry.clean_name}  ({size_str})"

            cb = ctk.CTkCheckBox(
                row, text=display_text, variable=cb_var, font=ctk.CTkFont(size=12)
            )
            cb.pack(side="left", fill="x", expand=True)

            self.entry_checkboxes[entry.full_path] = cb

    def _apply_filter(self, mode: str):
        if not self.package_info:
            return

        for entry in self.package_info["entries"]:
            cb = self.entry_checkboxes.get(entry.full_path)
            if not cb:
                continue

            if mode == 'video':
                if entry.is_video():
                    cb.select()
                else:
                    cb.deselect()
            elif mode == 'media':
                if entry.is_video() or entry.is_audio():
                    cb.select()
                else:
                    cb.deselect()
            elif mode == 'all':
                cb.select()
            elif mode == 'none':
                cb.deselect()

    def _choose_output_dir(self):
        folder = filedialog.askdirectory(title="Pilih Folder Output", initialdir=self.out_entry.get())
        if folder:
            self.output_dir = folder
            self.out_entry.delete(0, "end")
            self.out_entry.insert(0, folder)
            self._log(f"Folder penyimpanan: {folder}")

    def _open_output_folder(self):
        target = self.out_entry.get().strip()
        if not os.path.exists(target):
            os.makedirs(target, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(target)
        else:
            subprocess.run(["xdg-open", target])

    def _play_extracted_video(self):
        if self.last_extracted_video and os.path.isfile(self.last_extracted_video):
            if sys.platform == "win32":
                os.startfile(self.last_extracted_video)
            else:
                subprocess.run(["xdg-open", self.last_extracted_video])
        else:
            messagebox.showinfo("Info", "Belum ada video yang diekstrak untuk diputar.")

    def _set_ui_state(self, processing: bool):
        self.is_processing = processing
        state = "disabled" if processing else "normal"
        self.btn_extract.configure(state=state)
        self.btn_browse_file.configure(state=state)
        self.btn_browse_out.configure(state=state)
        if processing:
            self.btn_extract.configure(text="⏳ Sedang Mengekstrak...")
        else:
            self.btn_extract.configure(text="🚀 Ekstrak Berkas Terpilih")

    def _start_extraction_thread(self):
        if self.is_processing:
            return

        if not self.current_file_path or not os.path.isfile(self.current_file_path):
            messagebox.showwarning("Peringatan", "Silakan pilih file .mpkg atau .pkg terlebih dahulu!")
            return

        selected_paths = [path for path, cb in self.entry_checkboxes.items() if cb.get() == 1]
        if not selected_paths:
            messagebox.showwarning("Peringatan", "Silakan centang setidaknya satu berkas yang ingin diekstrak!")
            return

        out_path = self.out_entry.get().strip()
        if not out_path:
            messagebox.showwarning("Peringatan", "Silakan tentukan folder output terlebih dahulu!")
            return

        # Naming mode
        combo_val = self.naming_combo.get()
        if "Judul Asli" in combo_val:
            naming_mode = "title"
        elif "Arsip" in combo_val:
            naming_mode = "archive"
        else:
            naming_mode = "original"

        self.output_dir = out_path
        self._set_ui_state(True)
        self.progress_bar.set(0)
        self.lbl_progress.configure(text="0%")

        threading.Thread(
            target=self._worker_custom_extraction,
            args=(selected_paths, naming_mode),
            daemon=True
        ).start()

    def _worker_custom_extraction(self, selected_paths: List[str], naming_mode: str):
        custom_title = self.package_info.get("title", "") if self.package_info else ""
        self._log(f"\n=== Memulai ekstraksi {len(selected_paths)} berkas terpilih ===")

        def progress_cb(fraction: float):
            self.after(0, lambda v=fraction: self._update_progress_ui(v))

        try:
            results = extract_custom_entries(
                file_path=self.current_file_path,
                output_dir=self.output_dir,
                target_entry_paths=selected_paths,
                naming_mode=naming_mode,
                custom_title=custom_title,
                log_cb=lambda msg: self.after(0, lambda m=msg: self._log(m)),
                progress_cb=progress_cb
            )

            # Cek video untuk tombol putar
            vids = [f for f in results if f.lower().endswith(VIDEO_EXTENSIONS)]
            if vids:
                self.last_extracted_video = vids[0]
                self.after(0, lambda: self.btn_play_preview.configure(state="normal"))

            self._log("==========================================")
            self._log(f"Selesai! Berhasil menyimpan {len(results)} berkas di: {self.output_dir}")
            self._log("==========================================")

            if results:
                self.after(0, lambda: messagebox.showinfo(
                    "Ekstraksi Sukses",
                    f"Berhasil mengekstrak {len(results)} berkas!\n\nFolder: {self.output_dir}"
                ))

        except Exception as e:
            self._log(f"[ERROR] Gagal mengekstrak: {e}")
            self.after(0, lambda err=str(e): messagebox.showerror("Gagal", f"Terjadi kesalahan: {err}"))

        self.after(0, lambda: self._set_ui_state(False))

    def _update_progress_ui(self, fraction: float):
        fraction = max(0.0, min(1.0, fraction))
        self.progress_bar.set(fraction)
        self.lbl_progress.configure(text=f"{int(fraction * 100)}%")

    def _show_about_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Tentang, Lisensi & Solusi Jam")
        dialog.geometry("560x480")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        lbl = ctk.CTkLabel(
            dialog, text="Wallpaper Engine MPKG to MP4 Inspector", font=ctk.CTkFont(size=16, weight="bold")
        )
        lbl.pack(pady=(16, 4))

        ctk.CTkLabel(
            dialog,
            text="Versi 2.0 • Open Source MIT License • Author: Brony-PC",
            font=ctk.CTkFont(size=11), text_color="gray"
        ).pack(pady=(0, 10))

        content_box = ctk.CTkTextbox(dialog, font=ctk.CTkFont(size=12), wrap="word")
        content_box.pack(fill="both", expand=True, padx=20, pady=(0, 14))

        info_text = (
            "🛡️ 1. KEAMANAN & LISENSI RESMI MIT:\n"
            "• Program ini 100% open-source dan bebas dari segala bentuk malware/virus.\n"
            "• Menjalankan program langsung dari Python atau run.bat menjamin transparansi penuh dan bebas false-positive.\n\n"
            "⏱️ 2. MASALAH 'JAM' (CLOCK WIDGET):\n"
            "Banyak wallpaper di Wallpaper Engine (khususnya saat diekspor ke Android) memiliki tampilan jam digital/analog.\n"
            "• Bagaimana sistem Wallpaper Engine bekerja:\n"
            "  Jam di Wallpaper Engine adalah WIDGET TERPISAH (lapisan overlay di atas video atau script interaktif), BUKAN menempel permanen pada video aslinya.\n"
            "• Mengapa program ini menyelesaikan masalah jam:\n"
            "  Program ini mengekstrak langsung stream file MP4 mentah di dalam paket .mpkg. Hasilnya adalah VIDEO MURNI yang BERSIH dari overlay jam!\n\n"
            "⚙️ 3. PENGATURAN OUTPUT:\n"
            "• Anda dapat memilih secara spesifik file mana yang ingin diekstrak (Video saja, Audio saja, atau gambar pratinjau).\n"
            "• Opsi penamaan cerdas memungkinkan file dinamai otomatis sesuai judul wallpaper di Steam Workshop."
        )
        content_box.insert("1.0", info_text)
        content_box.configure(state="disabled")

        ctk.CTkButton(dialog, text="Tutup", width=100, command=dialog.destroy).pack(pady=(0, 14))


def launch_gui():
    app = ConverterApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()

# 🎬 Wallpaper Engine MPKG to MP4 Extractor & Inspector

Aplikasi desktop modern berbasis Python & **CustomTkinter** untuk mengekstrak, melihat pratinjau (*preview*), dan menyaring isi paket Wallpaper Engine (`.mpkg` untuk Android/Mobile dan `.pkg` untuk Desktop) secara selektif tanpa proses render ulang (*lossless extraction*).

---

## 🛡️ Lisensi & Jaminan Keamanan (Bebas Virus)

Aplikasi ini dilisensikan secara resmi di bawah **[MIT License](LICENSE.txt)**.
* **100% Open Source:** Seluruh baris kode dapat Anda periksa secara langsung. Tidak ada bagian yang dienkripsi (*obfuscated*) atau disembunyikan.
* **100% Offline & Lokal:** Seluruh proses pembacaan file dan ekstraksi berjalan secara lokal di komputer Anda tanpa mengirim data ke internet.
* **Bebas False Positive:** Dijalankan langsung melalui Python (atau `run.bat`), sehingga tidak akan memicu deteksi virus palsu dari Windows Defender.

---

## ⏱️ Solusi Masalah "Jam" (Clock Widget)

Banyak wallpaper Wallpaper Engine (khususnya saat diekspor ke Android dalam format `.mpkg`) menampilkan jam digital atau analog.
* **Bagaimana Wallpaper Engine Bekerja:** Tampilan jam di Wallpaper Engine adalah **Widget Overlay (lapisan terpisah)** atau skrip interaktif, **BUKAN** video yang menyatu secara permanen.
* **Solusi Program Ini:**
  1. Program membaca paket biner dan mendeteksi konfigurasi jam di dalam `project.json`.
  2. Program mengekstrak berkas `.mp4` asli secara murni dari sumbernya, sehingga video yang Anda dapatkan adalah **VIDEO BERSIH TANPA JAM**.

---

## ✨ Fitur Utama Versi 2.0

1. **🖼️ Pratinjau Visual & Metadata**:
   * Menampilkan gambar thumbnail preview wallpaper (`preview.jpg` / `preview.png`) langsung di dalam antarmuka.
   * Menampilkan judul wallpaper, tipe wallpaper (Video/Scene), ukuran paket, dan status konfigurasi jam.
2. **📋 Pemilihan & Checklist Berkas Output**:
   * Menampilkan seluruh daftar berkas di dalam paket (Video, Audio, Gambar, Config).
   * Tombol filter cepat: **🎬 Hanya Video**, **🎵 Video + Audio**, **Semua**, atau **Batal Pilih**.
   * Anda bebas memilih berkas apa saja yang ingin diekstrak ke disk.
3. **🏷️ Opsi Penamaan Output Fleksibel**:
   * *Gunakan Judul Asli Wallpaper* (misal: `Cyberpunk_Night.mp4` dari metadata `project.json`).
   * *Gunakan Nama Berkas Asli* (misal: `materials_scene.mp4`).
   * *Gunakan Nama File Arsip .mpkg*.
4. **▶️ Tombol Putar Video Langsung**:
   * Setelah selesai diekstrak, Anda bisa langsung memutar video hasil konversi di media player komputer Anda dengan satu klik.

---

## 🚀 Cara Menjalankan

### Cara 1: Launcher Satu-Klik Windows (Paling Mudah)
Cukup **klik ganda (double-click)** pada file:
```text
run.bat
```
Script akan otomatis memeriksa Python dan pustaka yang dibutuhkan (`customtkinter`, `pillow`), lalu membuka jendela aplikasi.

### Cara 2: Menjalankan via Terminal / Command Prompt
```bash
cd "C:\Users\Brony-PC\Documents\ngoding lawak 2\mpkg to mp4"
python main.py
```

---

## 📄 Struktur File Proyek

```text
mpkg to mp4/
├── LICENSE.txt       # Lisensi resmi open-source MIT
├── README.md         # Petunjuk dan dokumentasi lengkap
├── requirements.txt  # Daftar dependensi Python (customtkinter, darkdetect, pillow)
├── run.bat           # Launcher cepat satu-klik Windows
├── extractor.py      # Core engine parser & inspector Wallpaper Engine
├── gui.py            # Antarmuka grafis CustomTkinter modern dengan preview
└── main.py           # Entry point utama
```

---
Dibuat dengan ❤️ untuk kemudahan pengelolaan koleksi Wallpaper Engine Anda.

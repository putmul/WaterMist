# PRD Modul 03 — Recently Released

**Proyek:** WaterMist | **Versi:** 1.0 | **Tanggal:** 18 November 2026 | **Status:** Bot scraping sudah tersedia, integrasi belum
**Dependensi:** Modul 01 | **Dikonsumsi oleh:** Modul 05 (metadata), Modul 06

## 1. Tujuan

Menampilkan game PC yang baru dirilis di Steam. Bot scraping sudah ada, sehingga fokus modul ini adalah **mengintegrasikan bot** ke database dan antarmuka WaterMist.

## 2. Sumber Data

| Sumber | Metode | Status | Frekuensi |
|--------|--------|--------|-----------|
| Steam Store (Steam bot) | Web scraping | Sudah tersedia | 1x/hari |

Patuhi ketentuan penggunaan Steam, terapkan rate limit, dan jangan menghindari mekanisme pembatasan akses.

## 3. Data yang Dikumpulkan

| Data | Tujuan |
|------|--------|
| Nama game, Steam App ID | Identitas dan matching (kunci utama: App ID) |
| Tanggal rilis | Filter periode |
| Harga | Tampilan dan `game_products` |
| Developer, Publisher | Metadata |
| Genre | Dipakai juga oleh Modul 05 |
| Deskripsi singkat | Tampilan dan TF-IDF di Modul 05 |
| URL Steam Store | Link keluar |
| Gambar/cover | Tampilan |

> Genre dan tag dari bot ikut dipakai sebagai fitur rekomendasi. Jika bot belum mengambil **tag**, itu perlu ditambahkan (atau di-enrich terpisah, lihat Modul 01 job nomor 5).

## 4. Definisi Periode

| Label | Definisi MVP |
|-------|-------------|
| Recently Released | Dirilis dalam **30 hari** terakhir |

MVP hanya menggunakan satu rentang, yaitu 30 hari terakhir. Rentang ini
ditetapkan oleh konfigurasi internal dan tidak menyediakan pilihan 90 hari.

## 5. Kebutuhan Fungsional

| ID | Kebutuhan |
|----|-----------|
| FR-08 | Memakai bot scraping Steam yang sudah ada sebagai collector (`steam_release_bot.py`). |
| FR-09 | Menyimpan hasil scraping ke database (`games`, `game_products`, `genres`/`game_genres`, `game_tags`). |
| FR-10 | Menampilkan daftar game yang baru dirilis dalam rentang 30 hari terakhir. |
| FR-11 | Sistem menggunakan rentang 30 hari terakhir secara konsisten. |
| RR-12 | **Adapter:** output bot dibungkus agar mengikuti interface collector Modul 01 (`fetch` → `normalize`) tanpa menulis ulang logika scraping. |
| RR-13 | **Upsert idempoten** berdasarkan `steam_app_id`; game yang sudah ada diperbarui, bukan diduplikasi. |
| RR-14 | Game dari bot yang sama dengan game di modul Deals (Steam App ID sama) harus menjadi satu record `games`. |
| RR-15 | Dijalankan dari scheduler harian (urutan awal, sebelum Deals, agar `games` baru tersedia untuk matching). |
| RR-16 | Logging dan pencatatan `job_runs`; kegagalan bot tidak boleh menghapus data lama. |

## 6. Rencana Integrasi Bot

1. **Audit bot:** cek format output (CSV/JSON/dict?), field yang tersedia, cara menjalankan, dan penanganan rate limit.
2. **Pemetaan field** output bot ke skema `games` dan tabel relasi.
3. **Adapter** + validasi (tanggal rilis valid, App ID wajib).
4. **Penyimpanan** ke MariaDB dengan upsert.
5. **Penjadwalan** harian dan endpoint/halaman tampilan.

## 7. Antarmuka (ringkas, detail di Modul 06)

Halaman **Recently Released:** daftar game terbaru, filter periode, search, tanggal rilis, link ke Steam Store.

## 8. Risiko

| Risiko | Dampak | Mitigasi |
|--------|--------|----------|
| Struktur HTML Steam berubah | Bot gagal | Parser modular dan monitoring |
| Format output bot tidak sesuai skema | Data tidak tersimpan | Audit dan adapter di awal |
| Metadata tidak lengkap (tag/deskripsi) | Rekomendasi kurang akurat | Validasi dan enrichment |
| Rate limiting | Data gagal diambil | Jeda dan retry |

## 9. Tugas Pengembangan

- [x] Membuat bot scraping Steam untuk game terbaru
- [ ] Audit output dan kebutuhan field bot
- [ ] Membuat adapter ke interface collector
- [ ] Mengintegrasikan bot dengan aplikasi Flask
- [ ] Menyimpan hasil scraping ke database
- [ ] Menambahkan ke scheduler harian
- [ ] Membuat halaman Recently Released dan filter periode

## 10. Acceptance Criteria

1. Bot berjalan otomatis sekali sehari dan hasilnya tersimpan di MariaDB.
2. Menjalankan bot dua kali tidak menghasilkan game ganda.
3. Pengguna dapat melihat daftar game yang dirilis dalam 30 hari terakhir.
4. Setiap game punya tanggal rilis dan link Steam Store.

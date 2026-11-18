# WaterVapor — Index PRD per Modul

**Versi:** 1.0 | **Tanggal:** 18 November 2026 | **Status:** Draft | **Platform:** Web App (PC Games)

Dokumen ini adalah hasil pemecahan PRD WaterVapor v1.0 menjadi beberapa PRD per modul. Setiap modul bisa dikerjakan dan di-review terpisah.

## 1. Ringkasan Produk

WaterVapor adalah platform agregasi informasi dan rekomendasi game PC: memantau diskon dari berbagai toko, melacak game baru, dan memberi rekomendasi personal (populer maupun *hidden gems*).

**Visi:** Menjadi platform pencarian dan rekomendasi game PC yang membantu pengguna menemukan game yang tepat dengan harga terbaik.

**Target pengguna:** gamer PC yang mencari harga murah, game terbaru, game sesuai selera, dan game niche/hidden gems.

**Non-goals (tahap awal):** menjual game, distribusi/launcher, game konsol, fitur komunitas/multiplayer, ML kompleks (collaborative filtering) di MVP.

## 2. Daftar Modul

| # | File | Modul | Sumber data | Status |
|---|------|-------|-------------|--------|
| 01 | `01-foundation-data-platform.md` | Foundation & Data Platform (DB inti, normalisasi, scheduler, logging) | — | Belum dikembangkan |
| 02 | `02-game-deals.md` | Game Deals | Steam scraper + CheapShark API | Belum dikembangkan |
| 03 | `03-recently-released.md` | Recently Released | Steam bot | Bot sudah tersedia |
| 04 | `04-steam-integration.md` | Steam Integration & User Data | Steam Web API | Belum dikembangkan |
| 05 | `05-recommendation-engine.md` | Recommendation Engine | Data internal | Belum dikembangkan |
| 06 | `06-dashboard-ui.md` | Dashboard, Halaman & UI | Data internal | Belum dikembangkan |

## 3. Pembagian Sumber Data

| Sumber | Data yang diambil | Metode | Modul | Status |
|--------|-------------------|--------|-------|--------|
| Steam scraper | Game yang sedang diskon | Scraping | 02 | Akan dibuat |
| Steam bot | Recently released | Scraping | 03 | Sudah tersedia |
| CheapShark API | Deal dari berbagai toko PC | REST API | 02 | Akan digunakan |
| Steam Web API | Library, playtime, profil pengguna | REST API | 04 | Akan digunakan |

**Frekuensi pengambilan data:** semua data game (scraping dan API call) diambil **periodik, sekali sehari**, lalu disimpan ke **MariaDB**. Detail jadwal ada di modul 01.

## 4. Ketergantungan Antar Modul

```text
01 Foundation  ──►  02 Deals ──────────┐
      │                                ├──►  06 Dashboard & UI
      ├──────────►  03 Releases ───────┤
      │                                │
      └──►  04 Steam Integration ──►  05 Recommendation ──┘
```

- **01** adalah prasyarat semua modul (skema inti, collector base, scheduler).
- **02** dan **03** independen satu sama lain; keduanya mengisi tabel `games`.
- **05** membutuhkan genre/tag dari **02/03** dan profil pengguna dari **04**.
- **06** mengonsumsi output semua modul; halaman Deals dan Releases bisa dibuat lebih awal sebelum 05 selesai.

## 5. Urutan Pengerjaan (Mapping ke Phase PRD Awal)

| Phase awal | Modul |
|-----------|-------|
| Phase 1 — Foundation | 01 |
| Phase 2 — Game Deals | 02 |
| Phase 3 — Recently Released | 03 |
| Phase 4 — Steam Integration | 04 |
| Phase 5 — Recommendation Engine | 05 |
| Phase 6 — Dashboard & Refinement | 06 |

## 6. Catatan dan Celah yang Ditemukan Saat Memecah PRD

Hal-hal berikut tidak terdefinisi jelas di PRD awal dan perlu diputuskan. Detailnya ada di modul terkait.

1. **Tabel `users` belum didefinisikan.** Banyak tabel punya `user_id` sebagai FK, tapi PRD awal tidak menjelaskan akun/autentikasi. Lihat modul 04.
2. **Tumpang tindih Steam scraper dan CheapShark.** CheapShark juga melacak Steam sebagai salah satu toko, sehingga deal Steam bisa masuk dua kali. Perlu aturan prioritas sumber. Lihat modul 02.
3. **Frekuensi harian vs durasi diskon.** Dengan 1x sehari, diskon flash/singkat bisa terlewat dan riwayat harga hanya per hari. Ini disepakati sebagai batasan MVP. Lihat modul 01 dan 02.
4. **Data popularitas belum punya sumber pasti** untuk Hidden Gems. Lihat modul 05.
5. **Tabel pendukung belum ada:** `job_runs` (log eksekusi job), kolom `is_active`/`last_seen_at` pada `deals`, dan mapping ID toko CheapShark pada `stores`. Diusulkan di modul 01 dan 02.
6. **Kriteria keberhasilan MVP** (PRD awal bagian 14) dipecah ke masing-masing modul sebagai *acceptance criteria*.

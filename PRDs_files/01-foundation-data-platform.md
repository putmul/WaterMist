# PRD Modul 01 — Foundation & Data Platform

**Proyek:** WaterVapor | **Versi:** 1.0 | **Tanggal:** 18 November 2026 | **Status:** Draft
**Dependensi:** tidak ada (modul dasar) | **Dibutuhkan oleh:** semua modul

## 1. Tujuan

Menyediakan fondasi teknis yang dipakai semua modul: struktur proyek, skema database inti, kerangka collector, normalisasi dan validasi data, scheduler harian, serta logging dan error handling.

## 2. Ruang Lingkup

**Termasuk:** project Flask, MariaDB (XAMPP), tabel inti, base class collector, normalisasi, validasi, scheduler, logging, konfigurasi, keamanan dasar.
**Tidak termasuk:** logika spesifik deals (modul 02), releases (03), user dan Steam (04), rekomendasi (05), UI (06).

## 3. Teknologi

| Lapisan | Teknologi |
|---------|-----------|
| Backend | Python, Flask, Flask-SQLAlchemy, Flask-Migrate |
| Database | MariaDB (XAMPP) |
| Data collection | Requests/HTTPX, BeautifulSoup, Playwright (jika perlu render JS) |
| Processing | Pandas, NumPy, Scikit-learn, Joblib |
| Frontend | HTML, CSS, JS, Bootstrap 5, Jinja2, Chart.js (opsional) |
| Background jobs | APScheduler (awal); Celery + Redis jika beban meningkat |

## 4. Struktur Folder

```text
watervapor/
├── app/
│   ├── __init__.py
│   ├── models/        (game.py, store.py, deal.py, user.py)
│   ├── routes/        (main.py, deals.py, releases.py, recommendations.py)
│   ├── services/      (deal_service.py, game_service.py, recommendation_service.py)
│   ├── collectors/    (steam_scraper.py, steam_release_bot.py, cheapshark_client.py)
│   ├── recommendation/(preference_builder.py, similarity.py, ranking.py)
│   ├── templates/
│   └── static/
├── migrations/
├── config.py
├── requirements.txt
└── run.py
```

## 5. Prinsip Arsitektur

- Pisahkan pengambilan data dari business logic.
- Setiap sumber data punya adapter/collector sendiri.
- Simpan sumber data dan waktu pengambilan di setiap record.
- Hindari duplikasi game antar toko.
- Pisahkan identitas game (`games`) dari produk di toko tertentu (`game_products`).
- Simpan riwayat harga terpisah dari harga terbaru.
- Semua scraping dan sinkronisasi berjalan di background job, bukan di request pengguna.

## 6. Alur Data

```text
 Steam Deals     Steam Releases     CheapShark API
     │                 │                  │
     └─────────────────┼──────────────────┘
                       ▼
               Data Normalization
                       ▼
                Data Validation
                       ▼
                    MariaDB
                       ▼
               Flask Application ──► Frontend
```

## 7. Skema Database Inti

Tabel yang dimiliki modul ini. Tabel lain dimiliki modul masing-masing (`deals` di 02, tabel user di 04, `user_preferences`/`recommendations` di 05).

### 7.1. `games`
| Field | Tipe | Keterangan |
|-------|------|-----------|
| id | BIGINT | PK |
| name | VARCHAR | Nama game |
| steam_app_id | VARCHAR | Steam App ID (unique, nullable) |
| description | TEXT | Deskripsi |
| release_date | DATE | Tanggal rilis |
| cover_image | TEXT | URL gambar |
| developer | VARCHAR | Developer |
| publisher | VARCHAR | Publisher |
| created_at / updated_at | TIMESTAMP | Audit |

### 7.2. `stores`
| Field | Tipe | Keterangan |
|-------|------|-----------|
| id | BIGINT | PK |
| name | VARCHAR | Nama toko |
| website_url | TEXT | Website toko |
| *external_store_id* | VARCHAR | **Usulan:** `storeID` dari CheapShark untuk mapping |
| *source* | VARCHAR | **Usulan:** asal data toko (mis. `cheapshark`, `steam`) |

Contoh toko: Steam, GOG, Epic Games Store, Humble Store, Fanatical.

### 7.3. `game_products`
| Field | Tipe | Keterangan |
|-------|------|-----------|
| id | BIGINT | PK |
| game_id | BIGINT | FK → games |
| store_id | BIGINT | FK → stores |
| external_product_id | VARCHAR | ID produk dari sumber |
| product_url | TEXT | URL produk |
| region | VARCHAR | Wilayah harga |
| currency | VARCHAR | Mata uang |

Satu game dapat punya banyak produk di toko berbeda. Unique constraint yang disarankan: (`store_id`, `external_product_id`, `region`).

### 7.4. `price_history`
| Field | Tipe | Keterangan |
|-------|------|-----------|
| id | BIGINT | PK |
| game_product_id | BIGINT | FK |
| price | DECIMAL | Harga saat dicatat |
| regular_price | DECIMAL | Harga normal |
| currency | VARCHAR | Mata uang |
| recorded_at | TIMESTAMP | Waktu pencatatan |
| source | VARCHAR | Sumber data |

Dengan jadwal harian, snapshot dicatat **maksimal 1 baris per `game_product` per hari** (hindari duplikasi jika job dijalankan ulang).

### 7.5. `genres`, `game_genres`, `game_tags`
| Tabel | Field |
|-------|-------|
| genres | id (PK), name |
| game_genres | game_id (FK), genre_id (FK) — many-to-many |
| game_tags | id (PK), game_id (FK), tag |

### 7.6. `job_runs` (usulan baru)
| Field | Tipe | Keterangan |
|-------|------|-----------|
| id | BIGINT | PK |
| job_name | VARCHAR | Mis. `steam_deals`, `cheapshark_deals` |
| started_at / finished_at | TIMESTAMP | Durasi |
| status | VARCHAR | `success` / `partial` / `failed` |
| records_fetched / records_saved | INT | Statistik |
| error_message | TEXT | Ringkasan error |

Tujuan: monitoring, debugging scraper, dan bahan UI "terakhir diperbarui".

## 8. Kebutuhan Fungsional

| ID | Kebutuhan |
|----|-----------|
| FND-01 | Project Flask dengan application factory, konfigurasi via environment variable. |
| FND-02 | Koneksi MariaDB dan migrasi skema dengan Flask-Migrate. |
| FND-03 | Semua tabel inti di bagian 7 tersedia lewat model SQLAlchemy dan migrasi. |
| FND-04 | **Base collector:** setiap collector mengimplementasikan interface seragam (`fetch()` → `normalize()` → data siap simpan). |
| FND-05 | **Normalisasi:** data dari berbagai sumber diseragamkan ke format internal (nama, harga, mata uang, persen diskon, tanggal). |
| FND-06 | **Validasi:** harga ≥ 0, diskon 0–100, mata uang valid, ID wajib ada; record invalid dilog dan dilewati, bukan menggagalkan seluruh job. |
| FND-07 | **Upsert idempoten:** menjalankan job dua kali tidak menghasilkan duplikasi. |
| FND-08 | **Game matching:** urutan pencocokan → `steam_app_id` → `external_product_id` → fallback nama ternormalisasi (lowercase, tanpa tanda baca/edisi). |
| FND-09 | **Scheduler harian** dengan APScheduler (lihat bagian 9). |
| FND-10 | Logging terstruktur untuk setiap job dan pencatatan ke `job_runs`. |
| FND-11 | Error handling: kegagalan satu sumber tidak menghentikan sumber lain; data lama yang masih valid tidak dihapus saat update gagal. |
| FND-12 | Rate limiting dan retry dengan jeda (backoff) untuk semua pemanggilan eksternal. |

## 9. Penjadwalan (Daily Sync)

Semua data game diambil **sekali sehari**. Jam dibuat configurable (default dini hari, WIB) supaya tidak mengganggu pengguna.

| Urutan | Job | Modul | Catatan |
|--------|-----|-------|---------|
| 1 | Sinkron daftar toko (`GET /stores`) | 02 | Ringan, jarang berubah; boleh mingguan |
| 2 | Steam releases bot | 03 | Mengisi `games` baru |
| 3 | Steam discount scraper | 02 | |
| 4 | CheapShark deals | 02 | Memakai data game dari langkah 2–3 untuk matching |
| 5 | Enrichment metadata (genre, tag, popularitas) | 01/05 | Untuk game yang metadatanya belum lengkap |
| 6 | Snapshot `price_history` | 01/02 | Setelah deals terbaru tersimpan |
| 7 | Sinkron library Steam pengguna | 04 | Lihat modul 04 |
| 8 | Hitung ulang rekomendasi | 05 | Setelah semua data baru masuk |

Aturan: job berjalan berurutan atau dengan dependensi eksplisit; tiap job punya timeout; job yang gagal bisa di-retry manual lewat command CLI; *misfire grace time* diatur agar job tetap jalan jika server sempat mati.

**Batasan yang diterima di MVP:** karena sekali sehari, diskon yang muncul dan berakhir di antara dua run tidak akan tercatat, dan riwayat harga bersifat harian.

## 10. Kebutuhan Non-Fungsional

- **Performa:** pengambilan data eksternal tidak boleh menghambat request pengguna; gunakan pagination pada query besar; beri index pada `steam_app_id`, `game_id`, `store_id`, `recorded_at`.
- **Reliability:** setiap pengambilan data punya logging; data lama dipertahankan saat update gagal.
- **Data integrity:** simpan sumber dan timestamp; validasi harga/mata uang/diskon; hindari duplikasi game.
- **Security:** API key (Steam Web API) di environment variable, tidak masuk repository atau frontend; tidak pernah menyimpan password Steam.
- **Compliance:** patuhi ketentuan Steam dan CheapShark; terapkan rate limiting; jangan menghindari mekanisme keamanan situs; periksa ulang kebijakan sumber data sebelum publikasi.

## 11. Risiko

| Risiko | Dampak | Mitigasi |
|--------|--------|----------|
| Data game duplikat | Hasil tidak konsisten | Canonical game ID dan matching bertahap (FND-08) |
| Job gagal diam-diam | Data basi tanpa disadari | `job_runs` + log + indikator "terakhir diperbarui" |
| Server mati saat jadwal | Satu hari data hilang | Misfire grace time + trigger manual |

## 12. Tugas Pengembangan

- [ ] Membuat project Flask dan struktur folder
- [ ] Menyiapkan MariaDB dan konfigurasi koneksi
- [ ] Membuat model dan migrasi tabel inti (termasuk `job_runs`)
- [ ] Membuat base collector dan mekanisme normalisasi
- [ ] Membuat validasi data dan logika game matching
- [ ] Membuat logging dan error handling
- [ ] Menyiapkan APScheduler dan job runner harian

## 13. Acceptance Criteria

1. Aplikasi berjalan dan terkoneksi ke MariaDB; migrasi dapat dijalankan dari nol.
2. Menjalankan collector yang sama dua kali tidak menimbulkan duplikasi data.
3. Satu collector yang gagal tidak menghentikan collector lain dan tercatat di `job_runs`.
4. Scheduler menjalankan seluruh job pengambilan data otomatis sekali sehari tanpa intervensi manual.

# PRD Modul 02 — Game Deals

**Proyek:** WaterMist | **Versi:** 1.0 | **Tanggal:** 18 November 2026 | **Status:** Draft (belum dikembangkan)
**Dependensi:** Modul 01 | **Dikonsumsi oleh:** Modul 06 (Deals page, Best Deals, Game Detail)

## 1. Tujuan

Mengumpulkan informasi game yang sedang diskon dari Steam dan toko PC lain, menyimpannya dalam format seragam, dan menyajikannya agar pengguna bisa menemukan penawaran terbaik.

## 2. Sumber Data

| Sumber | Data | Metode | Frekuensi |
|--------|------|--------|-----------|
| Steam scraper (akan dibuat) | Game yang sedang diskon di Steam Store | HTTP + BeautifulSoup; Playwright jika perlu render JS | 1x/hari |
| CheapShark API (akan digunakan) | Deal dari berbagai toko PC | REST (Requests/HTTPX) | 1x/hari |

### 2.1. Endpoint CheapShark

| Kebutuhan | Endpoint | Pemakaian di WaterMist |
|-----------|----------|-------------------------|
| Daftar deal | `GET /deals` | Sumber utama deal harian (paginasi, urut diskon) |
| Cari game berdasarkan judul | `GET /games?title=...` | Fallback matching jika tidak ada Steam App ID |
| Cari berdasarkan Steam App ID | `GET /games?steamAppID=...` | Mapping game WaterMist ↔ game CheapShark |
| Semua deal suatu game | `GET /games?id=...` | Perbandingan harga antar toko di Game Detail |
| Daftar toko | `GET /stores` | Mengisi/menyinkronkan tabel `stores` |
| Detail satu deal | `GET /deals?id=...` | Verifikasi/refresh satu deal tertentu |

> Nama field dan batas parameter (mis. ukuran halaman, rate limit) harus dicek ke dokumentasi resmi: https://apidocs.cheapshark.com/

### 2.2. Ketentuan Penggunaan CheapShark (wajib)

- Deal dari toko yang dilacak CheapShark **harus diarahkan lewat link CheapShark**.
- Pertahankan URL dan parameter tracking apa adanya; jangan diubah atau dihapus.
- Periksa ketentuan API terbaru sebelum aplikasi dipublikasikan.

### 2.3. Ketentuan Scraping Steam

Patuhi ketentuan penggunaan Steam, terapkan rate limit, dan jangan menghindari mekanisme keamanan atau pembatasan akses.

## 3. Strategi Data (Dua Sumber)

**Tumpang tindih Steam:** CheapShark juga menyertakan Steam sebagai salah satu toko, jadi deal Steam bisa datang dari dua sumber. Aturan yang diusulkan:

| Aspek | Keputusan |
|-------|-----------|
| Sumber utama untuk toko Steam | Steam scraper (lebih lengkap: masa berlaku diskon, gambar, metadata) |
| Sumber untuk toko non-Steam | CheapShark |
| Deal Steam dari CheapShark | Disimpan sebagai pembanding/validasi (`source = cheapshark`), tidak ditampilkan ganda di UI |
| Link keluar | Steam scraper → URL Steam Store; CheapShark → link CheapShark |
| Kunci deduplikasi | (`game_product_id`, `source`); tampilan UI memilih satu deal per produk berdasarkan aturan prioritas di atas |

Keputusan ini perlu dikonfirmasi tim sebelum implementasi.

## 4. Data yang Dikumpulkan

- Nama game, identitas game dan toko (Steam App ID / ID produk eksternal)
- Harga normal, harga diskon, persentase diskon
- Nama toko, URL deal
- Waktu pengambilan data
- Masa berlaku diskon (hanya jika sumber menyediakan; umumnya tersedia dari Steam, tidak dari CheapShark)
- Mata uang dan wilayah harga

## 5. Skema Database

Menggunakan `games`, `stores`, `game_products`, `price_history` dari Modul 01, ditambah tabel berikut.

### `deals`
| Field | Tipe | Keterangan |
|-------|------|-----------|
| id | BIGINT | PK |
| game_product_id | BIGINT | FK → game_products |
| normal_price | DECIMAL | Harga normal |
| sale_price | DECIMAL | Harga diskon |
| discount_percent | DECIMAL | Persentase diskon |
| deal_url | TEXT | URL deal (link CheapShark apa adanya untuk sumber CheapShark) |
| deal_end_date | TIMESTAMP | Berakhir, jika tersedia |
| source | VARCHAR | `steam_scraper` / `cheapshark` |
| fetched_at | TIMESTAMP | Waktu pengambilan |
| *is_active* | BOOLEAN | **Usulan:** false jika tidak muncul di run terbaru |
| *last_seen_at* | TIMESTAMP | **Usulan:** terakhir terlihat di sumber |
| *external_deal_id* | VARCHAR | **Usulan:** mis. `dealID` CheapShark, untuk upsert dan `GET /deals?id=` |

Aturan: satu baris deal aktif per (`game_product_id`, `source`); deal yang hilang dari sumber ditandai `is_active = false`, **bukan dihapus**, supaya data lama tidak hilang jika sumber sedang error.

## 6. Kebutuhan Fungsional

| ID | Kebutuhan |
|----|-----------|
| FR-01 | Mengambil game yang sedang diskon dari Steam Store (scraper). |
| FR-02 | Mengambil deal dari CheapShark API (`GET /deals`, dengan paginasi sampai batas yang ditentukan konfigurasi). |
| FR-03 | Normalisasi data dari kedua sumber ke format seragam (Modul 01 FND-05). |
| FR-04 | Menampilkan: nama game, harga normal, harga diskon, persentase diskon, toko, gambar, link deal. |
| FR-05 | Pengurutan dan filter: persentase diskon, harga, nama, toko, rentang harga. |
| FR-06 | Menyimpan snapshot harga ke `price_history` untuk riwayat harga internal. |
| FR-07 | Pembaruan otomatis lewat background job **1x sehari** (scraper dan API call). |
| DL-08 | Mengaitkan deal dengan game: via Steam App ID (`steamAppID` di data CheapShark) → fallback `GET /games?title=` / nama ternormalisasi. |
| DL-09 | Menyinkronkan daftar toko dari `GET /stores` ke tabel `stores`. |
| DL-10 | Menandai deal yang hilang sebagai tidak aktif dan tidak ditampilkan di UI. |
| DL-11 | Menampilkan mata uang dan wilayah pada harga; tidak membandingkan harga lintas mata uang tanpa konversi atau label yang jelas. |
| DL-12 | Menyediakan daftar deal semua toko untuk satu game (`GET /games?id=`), dipakai di Game Detail. |

## 7. Alur Job Harian

```text
1. Sinkron stores (CheapShark /stores)
2. Steam scraper  → parse diskon → normalisasi → validasi → upsert game_products & deals
3. CheapShark /deals (paginasi) → normalisasi → matching game → upsert deals
4. Tandai deal yang tidak terlihat sebagai is_active = false
5. Tulis snapshot price_history (maks. 1 per produk per hari)
6. Catat hasil ke job_runs
```

## 8. Antarmuka (ringkas, detail di Modul 06)

Halaman **Deals:** search game, filter toko/harga/persentase diskon, sorting, game cards, pagination.

## 9. Risiko

| Risiko | Dampak | Mitigasi |
|--------|--------|----------|
| Struktur HTML Steam berubah | Scraper gagal | Parser modular, monitoring, alert dari `job_runs` |
| Rate limiting | Data gagal diambil | Interval dan retry dengan jeda; 1x/hari menjaga beban rendah |
| CheapShark tidak tersedia | Deal tidak diperbarui | Simpan data terakhir, retry |
| Perbedaan harga regional | Perbandingan tidak akurat | Simpan `region` dan `currency` |
| Duplikasi deal Steam (scraper vs CheapShark) | Tampilan ganda | Aturan prioritas sumber (bagian 3) |
| Diskon singkat terlewat (hanya 1x/hari) | Data tidak lengkap | Diterima di MVP; pertimbangkan frekuensi lebih sering jika dibutuhkan |

## 10. Tugas Pengembangan

- [ ] Membuat Steam discount scraper
- [ ] Mengambil data diskon Steam
- [ ] Membuat CheapShark API client (deals, games, stores)
- [ ] Mengambil data deal CheapShark
- [ ] Menormalisasi data kedua sumber
- [ ] Menghubungkan game dengan toko (`game_products`)
- [ ] Menyimpan data ke database
- [ ] Membuat job harian untuk pembaruan data
- [ ] Mengimplementasikan penanganan deal tidak aktif
- [ ] Membuat halaman Deals, filter, dan sorting (bersama Modul 06)

## 11. Acceptance Criteria

1. Data diskon Steam dapat diambil dan disimpan.
2. Deal CheapShark dapat diambil dan disimpan.
3. Halaman menampilkan deal dari beberapa toko.
4. **Semua deal CheapShark menggunakan link yang disediakan CheapShark** tanpa mengubah parameter.
5. Tidak ada deal ganda untuk produk yang sama pada tampilan.
6. Data diperbarui otomatis sekali sehari tanpa scraping manual.
7. Kegagalan salah satu sumber tidak menghapus atau menghentikan data sumber lain.

# PRD Modul 06 — Dashboard, Halaman & UI

**Proyek:** WaterVapor | **Versi:** 1.0 | **Tanggal:** 18 November 2026 | **Status:** Draft (belum dikembangkan)
**Dependensi:** Modul 01–05 (halaman bisa dikerjakan bertahap sesuai modul yang selesai)

## 1. Tujuan

Menyajikan semua fitur WaterVapor lewat antarmuka web yang cepat dan konsisten: Dashboard, Deals, Recently Released, Recommendations, dan Game Detail.

**Teknologi:** Flask + Jinja2, HTML/CSS/JS, Bootstrap 5, Chart.js (untuk grafik riwayat harga, jika diperlukan).

## 2. Halaman

### 2.1. Dashboard (halaman utama)

Bagian berurutan:
1. **Best Deals** (Modul 02)
2. **Popular Picks For You** (Modul 05)
3. **Hidden Gems For You** (Modul 05)
4. **Recently Released** (Modul 03)

Jika pengguna belum menghubungkan Steam: bagian rekomendasi menampilkan ajakan menghubungkan Steam ID atau memilih favorit, dan/atau game populer umum.

### 2.2. Deals Page
- Search game
- Filter toko, harga, persentase diskon
- Sorting (diskon, harga, nama)
- Game cards (gambar, nama, harga normal → harga diskon, % diskon, toko, tombol ke deal)
- Pagination
- Menampilkan mata uang/wilayah; keterangan "terakhir diperbarui"

### 2.3. Recently Released Page
- Daftar game yang dirilis dalam 30 hari terakhir, search, tanggal rilis
- Link ke Steam Store

### 2.4. Recommendations Page
- Bagian **Popular Picks** dan **Hidden Gems**
- Alasan rekomendasi pada tiap kartu
- Aksi pengguna: favorit, dismiss (tercatat ke `user_interactions`)
- Entri koneksi Steam dan input favorit manual (Modul 04)
- Empty state dan pesan profil privat

### 2.5. Game Detail Page
Nama, cover, deskripsi, developer, publisher, genre, tanggal rilis, daftar toko yang menjual, harga saat ini, riwayat harga (jika tersedia), dan game serupa.

## 3. Kebutuhan Fungsional

| ID | Kebutuhan |
|----|-----------|
| UI-01 | Semua halaman di bagian 2 tersedia dengan navigasi yang konsisten. |
| UI-02 | Daftar panjang memakai pagination; filter dan sorting dilakukan di sisi server. |
| UI-03 | Halaman membaca data dari database; tidak memicu scraping/API call eksternal saat request. |
| UI-04 | Link deal CheapShark memakai `deal_url` apa adanya (Modul 02). |
| UI-05 | Klik deal, view game, favorit, dismiss dicatat sebagai interaksi (Modul 04). |
| UI-06 | Menampilkan waktu "terakhir diperbarui" per bagian (dari `job_runs`/`fetched_at`) karena data diperbarui 1x sehari. |
| UI-07 | Grafik riwayat harga di Game Detail dari `price_history` (titik data harian). |
| UI-08 | Game Detail: perbandingan harga antar toko dari deal aktif (`GET /games?id=` yang sudah disimpan). |
| UI-09 | Empty state, loading, dan pesan error yang jelas di setiap halaman. |
| UI-10 | Responsif (Bootstrap 5) untuk desktop dan mobile. |

## 4. Non-Functional

- Halaman utama dimuat cepat (query ber-index, pagination, bisa memakai cache sederhana).
- Input pencarian dan filter divalidasi; output di-escape oleh Jinja2.
- Tidak ada credential di frontend.
- Teks yang berhubungan dengan harga selalu menyertakan mata uang.

## 5. Risiko

| Risiko | Dampak | Mitigasi |
|--------|--------|----------|
| Query berat pada daftar deal | Halaman lambat | Index, pagination, cache |
| Data kosong saat awal | Dashboard tampak kosong | Empty state dan seed data awal |
| Harga lintas wilayah membingungkan | Salah tafsir | Label mata uang/wilayah |

## 6. Tugas Pengembangan

- [ ] Layout dasar, navigasi, komponen game card (Bootstrap 5)
- [ ] Halaman Deals + filter dan sorting
- [ ] Halaman Recently Released + filter periode
- [ ] Halaman Game Detail (+ riwayat harga dan perbandingan toko)
- [ ] Halaman Recommendations (+ koneksi Steam, favorit manual)
- [ ] Dashboard utama (Best Deals, Popular Picks, Hidden Gems, Recently Released)
- [ ] Indikator "terakhir diperbarui"
- [ ] Perbaikan UI/UX, uji performa, perbaikan inkonsistensi data

## 7. Acceptance Criteria

1. Pengguna dapat melihat deal dari beberapa toko, game baru, dan rekomendasi dari Dashboard.
2. Filter, sorting, dan pagination berfungsi di Deals dan Recently Released.
3. Game Detail menampilkan toko, harga saat ini, dan riwayat harga jika tersedia.
4. Tidak ada request halaman yang memicu scraping/API eksternal.
5. Semua link deal CheapShark sesuai ketentuan.

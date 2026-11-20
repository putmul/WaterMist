# Implementation Plan: Perbaikan Parser `deal_end_date` Steam

## Tujuan

Memastikan tanggal berakhir diskon Steam diambil dari halaman Steam ketika tersedia, disimpan ke `deals.deal_end_date`, dan tidak langsung menggunakan fallback 14 hari. Fallback tetap dipertahankan hanya ketika Steam tidak menyediakan tanggal atau halaman detail gagal diambil.

## Temuan saat ini

- `app/collectors/steam_scraper.py::parse_discount_page()` hanya mengambil nama, harga, persentase diskon, URL, dan gambar.
- `SteamDealsCollector.normalize()` sudah meneruskan `record["deal_end_date"]`, tetapi field tersebut tidak pernah diisi oleh parser.
- `app/services/deal_lifecycle.py` kemudian mengisi `first_seen_at + 14 hari` karena `deal_end_date` kosong.
- Tanggal akhir diskon Steam umumnya berada di halaman detail game pada elemen `.discount_expiration`, bukan pada setiap baris hasil pencarian.
- `parse_app_detail()` saat ini digunakan untuk metadata release dan belum mengembalikan tanggal akhir diskon.

## Rencana perubahan

### 1. Tambahkan parser tanggal akhir Steam

File: `app/collectors/steam_release_bot.py`

- Tambahkan helper khusus, misalnya `parse_discount_end_date(text)`.
- Normalisasi whitespace dan hapus label seperti `Offer ends` sebelum parsing.
- Gunakan format tanggal Steam berbahasa Inggris yang sudah didukung `parse_steam_date()`.
- Kembalikan `datetime`, bukan hanya `date`, karena kolom database bertipe `DateTime`.
- Karena Steam biasanya hanya menampilkan tanggal, gunakan akhir hari lokal (`23:59:59`) agar diskon tidak dianggap berakhir pada awal tanggal tersebut.
- Jika teks kosong atau format tidak dikenali, kembalikan `None` tanpa menggagalkan seluruh record.

### 2. Ekstrak tanggal dari halaman detail

File: `app/collectors/steam_release_bot.py`

- Perluas `parse_app_detail()` untuk membaca `.discount_expiration`.
- Tambahkan field `deal_end_date` pada dictionary hasil parser.
- Parser tetap toleran terhadap halaman detail tanpa diskon, age gate, atau markup yang berubah.
- Field tambahan ini tidak mengubah perilaku scraper new releases karena normalisasi release tidak memakainya.

### 3. Ambil detail untuk record diskon

File: `app/collectors/steam_scraper.py`

- Pertahankan ekstraksi dari halaman search sebagai sumber awal yang cepat.
- Jika search row sudah memiliki tanggal akhir, gunakan tanggal tersebut.
- Jika belum, ambil halaman detail menggunakan mekanisme request dan throttle yang sudah ada pada `SteamReleaseBot`.
- Gabungkan `deal_end_date` dari hasil `parse_app_detail()` ke record diskon.
- Jangan membuang record diskon hanya karena halaman detail gagal; record tetap disimpan dan lifecycle memakai fallback 14 hari.
- Pertahankan pencatatan `failed_urls` agar sinkronisasi tidak menonaktifkan snapshot lama ketika sebagian request detail gagal.
- Hindari request detail duplikat untuk `app_id` yang sama.

### 4. Pertahankan aturan lifecycle

File: `app/services/deal_lifecycle.py`

- Tidak menghapus fallback 14 hari.
- Pastikan tanggal dari source selalu diprioritaskan saat `record["deal_end_date"]` tidak `None`.
- Pastikan update berikutnya tidak mengganti tanggal source dengan fallback.
- Pertahankan perilaku expiry berdasarkan `deal_end_date` yang sudah tersimpan.

### 5. Tambahkan pengujian regresi

File yang disarankan: `tests/test_deal_lifecycle.py` dan/atau test baru untuk scraper Steam.

Test yang perlu ditambahkan:

1. `parse_discount_end_date()` mem-parsing teks seperti `Offer ends 30 Nov, 2026` menjadi datetime akhir hari.
2. Parser mengembalikan `None` untuk teks kosong atau tanggal invalid.
3. `parse_app_detail()` mengekstrak `.discount_expiration` dan mengisi `deal_end_date`.
4. `parse_discount_page()` tetap bekerja pada HTML search tanpa expiration.
5. `SteamDealsCollector` menggabungkan tanggal dari halaman detail ke record diskon.
6. Lifecycle memakai tanggal source dan tidak membuat fallback 14 hari ketika tanggal source tersedia.
7. Lifecycle tetap membuat fallback ketika tanggal source tidak tersedia.
8. Kegagalan request detail tidak menghilangkan record diskon dan tidak mematikan seluruh deal lama.
9. Scraper recently released tetap menghasilkan record yang sama seperti sebelumnya.

## Validasi manual

Setelah implementasi:

1. Jalankan test suite.
2. Jalankan sinkronisasi deals dengan satu atau beberapa game yang sedang diskon.
3. Verifikasi nilai `deals.deal_end_date` terhadap tanggal yang ditampilkan Steam.
4. Verifikasi bahwa game tanpa tanggal Steam masih mendapat fallback 14 hari.
5. Verifikasi job tetap sukses/partial secara tepat jika sebagian halaman detail gagal.

## Kriteria selesai

- Record diskon dengan `.discount_expiration` menyimpan tanggal Steam yang sebenarnya.
- Record tersebut tidak lagi mendapat nilai `first_seen_at + 14 hari`.
- Fallback tetap aktif hanya untuk data tanpa tanggal atau request detail yang gagal.
- Tidak ada regresi pada scraper new releases, CheapShark, lifecycle, atau expiry deal.
- Perubahan hanya menyentuh parser, alur pengayaan detail diskon, dan test terkait.

## Catatan risiko

- Mengambil halaman detail untuk setiap diskon menambah jumlah request; throttle dan deduplikasi harus dipertahankan.
- Markup atau bahasa Steam dapat berubah. Selector perlu memiliki fallback yang aman dan test fixture harus mencakup variasi label tanggal.
- Tanggal Steam hanya berupa tanggal, sehingga keputusan penyimpanan sebagai akhir hari harus konsisten dengan timezone aplikasi.

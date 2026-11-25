# PRD Modul 06 — Dashboard, Halaman & UI

**Proyek:** WaterMist  
**Versi:** 1.1  
**Tanggal:** 24 November 2026  
**Status:** Draft revisi — implementasi parsial  
**Dependensi:** Modul 01–05  
**Teknologi target:** Flask, Jinja2, HTML/CSS/JS, Bootstrap 5 atau design system responsif yang setara, Chart.js bila grafik digunakan

## 1. Tujuan

Menyajikan data deals, game baru, rekomendasi personal, dan detail game melalui antarmuka web yang konsisten, cepat, aman, dan mudah digunakan pada desktop maupun mobile.

PRD ini mencakup halaman yang diakses pengguna, alur autentikasi dan personalisasi yang dibutuhkan UI, serta aturan penyajian data dari database. Pengambilan data eksternal tetap menjadi tanggung jawab collector dan background job pada Modul 01–05.

### 1.1 Status implementasi saat revisi

| Area | Status saat ini |
|------|-----------------|
| Layout dasar dan navigasi | Tersedia dengan CSS custom |
| Deals, filter, sorting, dan pagination | Tersedia sebagian besar |
| Recently Released, search, dan pagination | Tersedia |
| Recommendations, alasan, favorite, dan dismiss | Tersedia sebagian besar |
| Login, register, logout, dan quiz preferensi | Tersedia |
| Koneksi Steam dan fallback quiz | Tersedia |
| Game Detail dan perbandingan harga | Tersedia sebagian |
| Dashboard agregat | Belum tersedia; halaman utama masih berupa panel sinkronisasi |
| Price history chart | Belum tersedia |
| Similar games | Belum tersedia |
| Tracking view dan klik deal dari UI | Belum tersedia |
| Timestamp per section | Tersedia sebagian |
| Loading/error state yang konsisten | Belum lengkap |

## 2. Prinsip UI dan batasan

1. Halaman GET hanya membaca data yang sudah tersimpan di database. Request halaman tidak boleh melakukan scraping atau memanggil API eksternal.
2. Sinkronisasi Steam, CheapShark, release, enrichment, price snapshot, dan refresh recommendation dijalankan oleh scheduler/background job.
3. Semua harga harus menampilkan mata uang. Harga lintas wilayah/mata uang tidak boleh dibandingkan tanpa konversi dan label yang jelas.
4. Link deal CheapShark harus menggunakan `deal_url` yang disimpan apa adanya.
5. Output Jinja2 di-escape secara default. URL eksternal dibuka dengan `target="_blank"` dan `rel="noopener"` bila sesuai kebutuhan.
6. UI harus memiliki empty state, loading state, dan error state yang dapat dipahami pengguna.
7. Game yang sudah dimiliki pengguna atau sudah di-dismiss tidak ditampilkan sebagai rekomendasi secara default.

## 3. Shell aplikasi dan navigasi

Layout bersama harus menyediakan navigasi ke:

- Dashboard
- Deals
- Recently Released
- Recommendations
- Preferensi/Quiz, untuk pengguna yang sudah login
- Profile, untuk pengguna yang sudah login
- Login dan Daftar, untuk pengguna anonymous
- Logout, untuk pengguna yang sudah login

Navigasi harus mempertahankan konteks pengguna dan menyediakan penanda halaman aktif. Pada mobile, navigasi boleh berubah menjadi menu yang dapat dibuka/tutup.

## 4. Halaman dan perilaku

### 4.1 Dashboard (`/`)

Dashboard adalah halaman utama dan harus menampilkan bagian berikut secara berurutan:

1. **Best Deals** — deal aktif dengan diskon terbaik.
2. **Popular Picks For You** — rekomendasi tipe `popular`.
3. **Hidden Gems For You** — rekomendasi tipe `hidden_gem`.
4. **Recently Released** — game dalam periode rilis yang dikonfigurasi, default 30 hari.

Setiap bagian harus memiliki batas jumlah item yang dikonfigurasi, link “Lihat semua”, empty state, dan timestamp data.

#### Perilaku berdasarkan status pengguna

| Status | Perilaku rekomendasi |
|--------|----------------------|
| Anonymous | Tampilkan ajakan memilih genre/tag atau gunakan konteks pencarian; jangan menyimpan profil permanen |
| Login tanpa profil | Tampilkan CTA untuk menyelesaikan quiz preferensi |
| Login dengan profil quiz | Gunakan recommendation batch berbasis quiz |
| Steam publik dan berhasil disinkronkan | Gunakan recommendation batch berbasis library/playtime Steam |
| Steam privat/gagal disinkronkan | Tampilkan pesan yang jelas dan gunakan profil quiz sebagai fallback |
| Belum ada data | Tampilkan empty state yang menjelaskan tindakan berikutnya |

Dashboard tidak boleh memiliki tombol scraping untuk pengguna umum. Jika trigger sinkronisasi manual tetap diperlukan, pindahkan ke area operasional/admin atau command terpisah.

### 4.2 Deals (`/deals`)

Fitur:

- Pencarian berdasarkan nama game.
- Pencarian deskriptif/semantic search sebagai hasil tambahan bila tersedia.
- Filter toko.
- Filter diskon minimum dan maksimum.
- Filter harga minimum dan maksimum.
- Filter mata uang/wilayah bila dataset memiliki lebih dari satu konteks harga.
- Sorting berdasarkan relevansi, diskon, harga, nama, toko, dan popularitas.
- Pagination di sisi server.
- Kartu game berisi cover, nama, toko, region, harga normal, harga diskon, mata uang, persentase diskon, link detail, dan link deal.
- Menampilkan waktu terakhir data diperbarui.

Deal Steam dari CheapShark tidak boleh ditampilkan ganda apabila deal Steam dari `steam_scraper` tersedia. Kartu harus memakai URL `deal_url` dari database tanpa mengubah parameter tracking.

### 4.3 Recently Released (`/releases`)

Fitur:

- Menampilkan game yang dirilis dalam 30 hari terakhir secara default.
- Search berdasarkan nama.
- Menampilkan tanggal rilis, cover, dan link Steam Store.
- Pagination di sisi server.
- Mode `latest` dan mode berbasis preferensi untuk pengguna login.
- Menampilkan timestamp sinkronisasi release terakhir.
- Menampilkan empty state jika tidak ada game yang sesuai.

Periode tampilan harus konsisten dengan konfigurasi `RECENTLY_RELEASED_DAYS`. UI tidak perlu menyediakan pilihan 90 hari pada MVP.

### 4.4 Recommendations (`/recommendations`)

Halaman harus memiliki dua bagian:

1. **Popular Picks**
2. **Hidden Gems**

Setiap kartu harus menampilkan cover, nama game, alasan rekomendasi, dan informasi relevansi yang sesuai kebutuhan produk. Halaman harus membaca recommendation batch tersimpan jika tersedia dan tidak menghitung ulang data eksternal pada request.

Untuk pengguna login, kartu menyediakan aksi:

- Favorit.
- Sembunyikan/dismiss.

Aksi tersebut dicatat ke `user_interactions`; aksi favorit juga membuat/mempertahankan record `user_favorites`.

Halaman juga menyediakan:

- Link ke quiz preferensi.
- Link ke Profile untuk menghubungkan atau memutus Steam.
- Input favorit manual melalui pencarian/pemilihan game, atau fallback yang setara pada kartu game.
- Empty state dan CTA ketika profil belum tersedia.
- Pesan khusus saat profil Steam privat atau gagal disinkronkan.

### 4.5 Game Detail (`/games/<game_id>`)

Halaman harus menampilkan:

- Nama game dan cover.
- Deskripsi.
- Developer dan publisher.
- Genre dan tag.
- Tanggal rilis.
- Rating/review metadata jika tersedia.
- Daftar toko yang memiliki deal aktif.
- Harga normal, harga diskon, mata uang, wilayah, diskon, dan masa berlaku bila tersedia.
- Link deal sesuai sumbernya.
- Penanda harga termurah setelah normalisasi mata uang jika konversi tersedia.
- Grafik riwayat harga dari `price_history` dengan titik data harian bila tersedia.
- Empty state jika belum ada price history.
- Game serupa berdasarkan genre/tag/fitur game yang tersimpan.

Perbandingan toko harus menggunakan deal aktif yang tersimpan di database. Halaman tidak boleh memanggil CheapShark atau Steam secara langsung saat request.

### 4.6 Auth, onboarding, dan profile

UI harus mendukung:

- Register dengan email dan password.
- Login dan logout.
- Quiz genre/tag untuk cold start.
- Input SteamID64, URL `/profiles/<id>`, atau URL vanity `/id/<name>`.
- Pesan validasi input dan error Steam yang aman.
- Status koneksi, visibility, sync status, dan waktu sinkronisasi terakhir.
- Disconnect Steam dan penghapusan data library milik pengguna.
- Tampilan preferensi tersimpan dan sumbernya (`quiz`, `steam`, `favorite`, `interaction`).

Password Steam tidak pernah diminta. API key Steam tidak boleh muncul di HTML, JavaScript, atau URL frontend.

## 5. Kebutuhan fungsional

| ID | Kebutuhan |
|----|-----------|
| UI-01 | Semua halaman utama memiliki layout dan navigasi yang konsisten. |
| UI-02 | Dashboard menampilkan Best Deals, Popular Picks, Hidden Gems, dan Recently Released dalam urutan yang ditentukan. |
| UI-03 | Dashboard dan halaman daftar memiliki batas item, link “Lihat semua”, empty state, dan timestamp per bagian. |
| UI-04 | Daftar panjang menggunakan pagination; filter dan sorting utama dilakukan di sisi server. |
| UI-05 | Halaman GET membaca database dan tidak melakukan scraping/API eksternal. |
| UI-06 | Link deal CheapShark menggunakan `deal_url` tersimpan tanpa modifikasi. |
| UI-07 | View game, klik deal, favorite, dan dismiss dicatat sebagai interaksi untuk pengguna login. |
| UI-08 | Data interaksi tidak boleh dibuat untuk pengguna anonymous tanpa sesi akun yang sah. |
| UI-09 | Timestamp Deals, Releases, dan Recommendation ditampilkan dari `fetched_at`, `job_runs`, atau `generated_at` yang relevan. |
| UI-10 | Game Detail menampilkan perbandingan harga antar toko dari deal aktif yang tersimpan. |
| UI-11 | Game Detail menampilkan price history harian bila tersedia. |
| UI-12 | Game Detail menampilkan game serupa bila kandidat tersedia; jika tidak, tampilkan empty state. |
| UI-13 | Recommendations menampilkan alasan, favorite, dismiss, empty state, dan pesan fallback Steam/quiz. |
| UI-14 | Deals mendukung literal search dan semantic search dengan status loading, unavailable, dan no-result yang berbeda. |
| UI-15 | Auth, quiz, koneksi Steam, fallback profil privat, dan disconnect tersedia melalui UI yang aman. |
| UI-16 | Semua input filter divalidasi dan semua output template di-escape. |
| UI-17 | UI responsif pada desktop dan mobile serta dapat digunakan dengan keyboard dasar. |
| UI-18 | Error dari backend ditampilkan sebagai pesan aman tanpa traceback atau credential. |

## 6. Kontrak data per komponen

| Komponen | Sumber data | Data minimal |
|----------|-------------|--------------|
| Best Deals | `deals`, `game_products`, `games`, `stores` | game, cover, harga normal, harga sale, diskon, toko, currency, region, `deal_url` |
| Popular/Hidden Gems | recommendation batch tersimpan | game, rank, fit score, score, reason text, generated time |
| Recently Released | `games` dan relasi produk Steam | nama, cover, release date, Steam URL |
| Deal timestamp | `deals.fetched_at` atau `job_runs` | waktu lokal yang mudah dipahami |
| Release timestamp | `job_runs` job `steam_releases` | waktu selesai dan status job |
| Game Detail | `games`, active `deals`, `game_products`, `stores` | metadata game dan seluruh offer aktif |
| Price chart | `price_history` | tanggal, harga, harga normal, currency, store/product |
| Similar games | metadata game dan similarity service | game, cover, alasan/fit bila tersedia |

Semua query untuk kartu dan daftar harus memiliki batas yang jelas. Query besar tidak boleh mengambil seluruh tabel tanpa pagination atau limit yang sesuai.

## 7. Tracking interaksi

Interaksi berikut menggunakan model `user_interactions`:

| Interaksi | Kapan dicatat |
|-----------|--------------|
| `view` | Saat pengguna membuka Game Detail atau halaman rekomendasi yang relevan |
| `click_deal` | Saat pengguna mengklik link deal |
| `favorite` | Saat pengguna menekan Favorit |
| `dismiss_recommendation` | Saat pengguna menyembunyikan rekomendasi |

Tracking harus dilakukan melalui endpoint internal yang memvalidasi user dan game terlebih dahulu. Redirect ke URL eksternal tidak boleh menerima URL mentah dari request sebagai pengganti validasi record deal.

## 8. State UX wajib

Setiap halaman harus mendefinisikan:

- **Loading:** ditampilkan saat pencarian asynchronous atau komponen menunggu hasil.
- **Empty:** database valid tetapi tidak ada hasil.
- **Unavailable:** data atau fitur sementara tidak tersedia, misalnya semantic model gagal dimuat.
- **Error:** request gagal atau input tidak valid.
- **Stale data:** data ada tetapi timestamp melewati batas kesegaran yang ditentukan produk.

Pesan harus menjelaskan tindakan berikutnya, misalnya menghapus filter, mencoba pencarian lain, mengisi quiz, atau menghubungkan Steam.

## 9. Non-functional requirements

- Halaman utama menggunakan query terindeks, limit, pagination, dan cache sederhana bila dibutuhkan.
- Tidak ada credential atau API key di frontend.
- Teks harga selalu menyertakan mata uang dan, bila relevan, wilayah.
- Filter numerik memiliki batas dan validasi server-side.
- Form POST memakai perlindungan CSRF pada deployment produksi.
- Link eksternal aman dan tidak membuka data sensitif.
- Layout dapat digunakan pada lebar layar mobile tanpa tabel menyebabkan halaman rusak; tabel perbandingan boleh memiliki horizontal scrolling terkontrol.
- Waktu respons halaman tidak bergantung pada latency Steam, CheapShark, atau scraper.
- Error internal dicatat di server, sedangkan pengguna menerima pesan yang aman dan ringkas.

## 10. Pemetaan route saat ini

| Route | Fungsi |
|-------|--------|
| `GET /` | Dashboard utama; targetnya dashboard agregat |
| `GET /deals` | Deals, filter, sorting, pagination |
| `GET /deals/semantic` | Partial/async semantic search result |
| `GET /releases` | Recently Released dan mode preference |
| `GET /recommendations` | Popular Picks dan Hidden Gems |
| `POST /recommendations/interactions` | Favorite dan dismiss saat ini; perlu diperluas untuk tracking UI |
| `GET /games/<game_id>` | Game Detail dan perbandingan harga |
| `GET/POST /auth/login` | Login |
| `GET/POST /auth/register` | Register |
| `POST /auth/logout` | Logout |
| `GET/POST /onboarding/quiz` | Quiz preferensi |
| `GET /profile` | Profile, status Steam, dan preferensi |
| `POST /profile/steam/connect` | Hubungkan/sinkron Steam |
| `POST /profile/steam/disconnect` | Putuskan Steam dan hapus library |

Endpoint `POST /sync/deals` dan `POST /sync/releases` bukan bagian dari alur pengguna umum. Endpoint tersebut harus dibatasi atau dipindahkan ke alur operasional karena menjalankan scraping pada request.

## 11. Rencana pengembangan

### Sudah tersedia atau hampir selesai

- [x] Layout dasar dan navigasi.
- [x] Deals dengan kartu, filter utama, sorting, dan pagination.
- [x] Recently Released dengan search dan pagination.
- [x] Recommendations dengan Popular Picks dan Hidden Gems.
- [x] Alasan rekomendasi, favorite, dan dismiss.
- [x] Login, register, logout, dan quiz preferensi.
- [x] Koneksi Steam, status profil, disconnect, dan fallback quiz.
- [x] Game Detail dengan deal aktif dan perbandingan toko.
- [x] Semantic search sebagai fitur tambahan Deals.

### Belum selesai

- [ ] Dashboard agregat dengan empat section utama.
- [ ] Timestamp per section untuk dashboard dan releases.
- [ ] Filter Deals lengkap untuk min/max harga dan min/max diskon di UI.
- [ ] Genre dan tanggal rilis pada Game Detail.
- [ ] Price history query, endpoint/view model, dan grafik.
- [ ] Similar games.
- [ ] Tracking `view` dan `click_deal`.
- [ ] Input favorit manual berbasis pencarian/pemilihan game.
- [ ] Loading/error/stale state yang konsisten.
- [ ] Migrasi atau penyelarasan ke Bootstrap 5/design system responsif.
- [ ] CSRF dan pembatasan endpoint sinkronisasi manual untuk deployment produksi.

## 12. Acceptance criteria

1. Pengguna anonymous dapat membuka Dashboard, Deals, Recently Released, Recommendations, dan Game Detail tanpa credential eksternal di frontend.
2. Dashboard menampilkan Best Deals, Popular Picks, Hidden Gems, dan Recently Released dalam urutan yang ditentukan.
3. Pengguna dapat memfilter, mengurutkan, mencari, dan melakukan pagination di Deals tanpa request eksternal pada page load.
4. Recently Released menampilkan game dalam 30 hari terakhir, tanggal rilis, search, pagination, dan link Steam Store.
5. Recommendations menampilkan dua kategori, alasan rekomendasi, empty state, dan fallback quiz/Steam yang sesuai status user.
6. Game Detail menampilkan metadata utama, active offers dari beberapa toko, harga dengan currency/region, dan link deal yang benar.
7. Game Detail menampilkan price history harian dan game serupa ketika data tersedia; ketika tidak tersedia, pesan empty state ditampilkan.
8. Favorite, dismiss, view game, dan klik deal pengguna login tercatat sebagai interaksi yang valid.
9. Setiap section yang memakai data periodik menampilkan timestamp dan status data yang relevan.
10. Tidak ada page request normal yang memicu scraping, Steam API, atau CheapShark API.
11. Empty, loading, unavailable, stale, dan error state tersedia pada setiap halaman yang relevan.
12. UI dapat digunakan pada desktop dan mobile, output aman, filter divalidasi server-side, dan tidak ada credential yang dikirim ke frontend.

## 13. Risiko dan mitigasi

| Risiko | Dampak | Mitigasi |
|--------|--------|----------|
| Dashboard menggabungkan query besar | Halaman lambat | Limit per section, query terindeks, cache, dan query terpisah |
| Data kosong saat awal | Dashboard tampak rusak | Empty state, seed data, dan CTA yang jelas |
| Data periodik stale | Pengguna mengira data terbaru | Timestamp, status job, dan label stale |
| Harga lintas mata uang membingungkan | Salah tafsir harga | Label currency/region dan konversi eksplisit |
| Tracking menambah redirect atau latency | Pengalaman klik menurun | Endpoint ringan, validasi server-side, dan fallback aman |
| Semantic model gagal atau lambat | Pencarian tidak responsif | Hasil literal tetap tampil dan semantic state dibuat terpisah |
| Endpoint sync dapat diakses publik | Beban eksternal dan abuse | Auth/admin guard, rate limit, atau pindahkan ke background command |
| Perubahan struktur sumber eksternal | Data UI basi | `job_runs`, error state, dan data lama tetap dipertahankan |

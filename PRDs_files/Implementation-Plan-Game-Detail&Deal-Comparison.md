Implementation Plan — Game Detail & Deal Comparison
Tujuan
Pengguna dapat:
1. Melihat daftar game yang sedang diskon.
2. Klik Detail Game.
3. Melihat informasi game:
- Nama
- Developer
- Publisher
- Tags
- Deskripsi singkat
4. Melihat harga dari beberapa distributor.
5. Mengetahui distributor dengan harga termurah.
6. Membuka link pembelian dari distributor terkait.
1. Alur Pengguna
/deals
  ↓ klik "Detail Game"
/games/<game_id>
  ↓
Game Detail
  ├── Informasi game
  ├── Daftar harga distributor
  └── Highlight harga termurah
Link pembelian harus tetap menggunakan deal_url asli, khususnya link CheapShark.
2. Backend
File baru
- app/routes/games.py
- app/services/game_detail_service.py
- app/templates/game_detail.html
- tests/test_game_detail_comparison.py
File yang diubah
- app/__init__.py
- app/templates/deals.html
- kemungkinan app/services/deal_service.py
Route
Tambahkan:
GET /games/<int:game_id>
Route hanya membaca database dan tidak melakukan request eksternal, sesuai requirement UI-03.
Jika game tidak ditemukan:
404 Not Found
3. Service Perbandingan
Buat service khusus, misalnya:
GameDetailService.get_game_detail(game_id)
Service mengembalikan:
game
tags
description
active_offers
cheapest_offer
comparison_currency
comparison_status
Query deal
Gunakan deal dengan kondisi:
- Game.id == game_id
- Deal.is_active == True
- hanya harga terbaru yang tersimpan
- gunakan DealService.get_active_deals_for_game() untuk mempertahankan aturan deduplikasi Steam
Data offer:
- nama distributor
- harga normal
- harga diskon
- persentase diskon
- mata uang
- region
- tanggal berakhir
- link deal
- harga normalisasi untuk perbandingan
4. Logika Distributor Termurah
Urutan proses:
1. Ambil semua deal aktif untuk game.
2. Hilangkan duplikasi Steam:
- Steam scraper menjadi sumber utama.
- Deal Steam dari CheapShark tidak ditampilkan jika Steam scraper tersedia.
3. Kelompokkan offer berdasarkan distributor.
4. Jika satu distributor memiliki beberapa offer, pilih offer dengan harga perbandingan terendah.
5. Hitung harga termurah.
6. Tandai offer termurah dengan:
- badge Harga Termurah
- highlight visual
7. Jika terdapat harga sama, semua distributor yang seri ditandai sebagai termurah.
Contoh hasil:
Distributor	Harga	Diskon	Status
Steam	Rp150.000	25%	Harga termurah
Epic Games	Rp165.000	20%	—
GOG	Rp180.000	10%	—
5. Penanganan Mata Uang dan Region
Ini merupakan bagian penting karena konfigurasi saat ini menggunakan:
- Steam: IDR, region ID
- CheapShark: default USD, region US
Harga 150000 IDR tidak boleh dibandingkan langsung dengan 15 USD.
Rekomendasi
Tambahkan harga perbandingan yang dinormalisasi:
sale_price       = harga asli distributor
currency         = mata uang asli
comparison_price = harga setelah dikonversi
comparison_currency = IDR
Contoh:
Steam:
  sale_price: 150000 IDR
  comparison_price: 150000 IDR

Epic:
  sale_price: 15 USD
  comparison_price: 240000 IDR
Implementasi nilai tukar
Untuk MVP:
- Tambahkan konfigurasi nilai tukar atau tabel exchange_rates.
- Nilai tukar diperbarui lewat scheduler harian.
- Halaman detail tidak melakukan request nilai tukar langsung.
- Jika nilai tukar tidak tersedia:
- jangan menentukan pemenang global;
- tampilkan perbandingan berdasarkan grup mata uang;
- tampilkan pesan bahwa harga belum dapat dibandingkan langsung.
Harga asli tetap wajib ditampilkan agar pengguna dapat memverifikasi harga distributor.
6. Tampilan Game Detail
Halaman game_detail.html terdiri dari:
Header Game
- Cover game
- Nama game
- Developer
- Publisher
- Tanggal rilis jika tersedia
- Deskripsi singkat
Tags
Tampilkan seluruh GameTag:
Action · RPG · Singleplayer · Adventure
Highlight Harga Termurah
Contoh:
Harga termurah saat ini
Rp150.000 di Steam
Tambahkan tombol:
Beli di Steam
Tabel Perbandingan
Kolom:
- Distributor
- Harga normal
- Harga diskon
- Diskon
- Mata uang/region
- Berakhir pada
- Tombol Lihat Deal
Harga termurah diberi:
- border/highlight hijau
- badge Termurah
- urutan paling atas
Empty State
Jika tidak ada deal aktif:
Saat ini tidak ada diskon aktif untuk game ini.
Informasi game tetap ditampilkan.
7. Perubahan pada Halaman Deals
Pada setiap kartu di app/templates/deals.html, tambahkan:
Detail Game
Tombol diarahkan ke:
/games/<game_id>
Sebaiknya judul game atau cover juga dapat diklik.
Tombol Lihat deal tetap langsung menuju distributor.
8. Data Game
Field berikut sudah tersedia di model Game:
- name
- developer
- publisher
- description
- cover_image
Tags sudah tersedia melalui relasi:
Game.tags
Jika metadata belum tersedia dari hasil deal, halaman harus menggunakan fallback:
Informasi belum tersedia
Tidak boleh memanggil Steam atau CheapShark secara langsung saat halaman dibuka.
9. Testing
Tambahkan tests/test_game_detail_comparison.py.
Test minimum:
 1. Game detail dapat dibuka.
 2. Developer, publisher, description, dan tags tampil.
 3. Tiga distributor aktif tampil.
 4. Deal tidak aktif tidak tampil.
 5. Distributor termurah terdeteksi dengan benar.
 6. Harga sama menghasilkan lebih dari satu distributor termurah.
 7. Deal Steam dari CheapShark tidak menggandakan Steam scraper.
 8. Link CheapShark tidak diubah.
 9. Game tanpa deal tetap menampilkan detail.
10. Game yang tidak ada menghasilkan 404.
11. Harga dengan mata uang berbeda tidak dibandingkan secara nominal mentah.
12. Halaman tidak melakukan request API eksternal.
Saat ini seluruh 40 unit test yang tersedia lulus, tetapi belum ada test khusus compare.
10. Acceptance Criteria
Fitur dianggap selesai jika:
- User dapat membuka /games/<game_id> dari halaman Deals.
- Detail game tampil lengkap jika datanya tersedia.
- Semua distributor dengan deal aktif tampil.
- Harga asli, mata uang, dan region tampil jelas.
- Distributor termurah diberi highlight.
- Perbandingan tidak salah akibat perbedaan mata uang.
- Link pembelian tetap valid dan tidak dimodifikasi.
- Tidak ada duplikasi Steam.
- Tidak ada request eksternal saat membuka Game Detail.
- Test backend dan route berhasil.
Urutan Implementasi
 1. Tambahkan query/service Game Detail.
 2. Tambahkan logika deduplikasi dan pemilihan offer terbaik per distributor.
 3. Tetapkan strategi normalisasi mata uang.
 4. Tambahkan route /games/<game_id>.
 5. Buat template Game Detail.
 6. Tambahkan link dari halaman Deals.
 7. Tambahkan highlight distributor termurah.
 8. Tambahkan test service dan route.
 9. Tambahkan test untuk perbedaan mata uang.
10. Perbarui PRD dengan status UI-08 dan acceptance criteria baru.
Prioritas utama: implementasikan perbandingan harga dan penentuan distributor termurah setelah aturan mata uang ditetapkan. Tanpa aturan tersebut, hasil “termurah” dapat menyesatkan.
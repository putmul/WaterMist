Tujuan
Gunakan desain di web/template/game-detail.html sebagai tampilan detail game yang dibuka lewat /games/<game_id>. Data game dan penawarannya harus berasal dari database, bukan data contoh.
Rencana pengerjaan
1. Tetapkan halaman utama
- Pertahankan route /games/<int:game_id> di app/routes/games.py.
- Ubah template yang dirender route agar memakai web/template/game-detail.html.
- Jadikan halaman lama app/templates/game_detail.html tidak lagi menjadi tampilan utama, setelah semua perilaku yang diperlukan sudah dipindahkan.
2. Ubah prototipe menjadi template dinamis
- Ganti konten contoh seperti Hollow Knight, STORES, HISTORY, dan SIMILAR dengan variabel Jinja yang dikirim route.
- Gunakan url_for('frontend.static', ...) untuk CSS, JavaScript, dan gambar agar URL aset bekerja dari halaman /games/<id>.
- Buat breadcrumb dan tautan kembali menuju route Deals yang benar.
3. Lengkapi data view di GameDetailService
- Pertahankan data game, tag, penawaran aktif, dan harga termurah yang sudah disiapkan service.
- Tambahkan riwayat harga dari PriceHistory jika data historis tersedia; pastikan mata uangnya jelas dan jangan menggabungkan harga dari mata uang berbeda tanpa konversi.
- Tambahkan hanya informasi game yang memang tersedia di model/database. Untuk data yang belum ada—misalnya screenshot atau spesifikasi—tampilkan kondisi “belum tersedia” atau hilangkan bagian tersebut.
4. Render perbandingan harga dari data backend
- Isi harga terbaik dan tabel toko dari offers.
- Tampilkan mata uang asli dan wilayah setiap penawaran, serta harga normal, harga diskon, persentase diskon, dan tautan deal.
- Pertahankan aturan normalisasi mata uang dan jangan menyatakan ada harga termurah global jika nilai tukar untuk salah satu penawaran tidak tersedia.
- Tampilkan pesan yang sesuai jika belum ada deal aktif.
5. Tangani fitur prototipe yang belum didukung
- Tombol “Simpan” dan “Buat Alert” saat ini belum terhubung ke fitur backend. Jangan biarkan tombol tampak berfungsi jika belum ada endpoint: hilangkan atau tampilkan sebagai nonaktif dengan penjelasan.
- Game serupa hanya ditampilkan jika tersedia sumber data dan aturan pemilihannya; jika belum, keluarkan bagian tersebut dari tampilan awal.
6. Perbarui pengujian
- Perbarui tests/test_game_detail_comparison.py untuk memastikan route merender template prototipe yang sudah dinamis.
- Uji data metadata, tag, daftar penawaran, penawaran termurah, dan keadaan tanpa deal atau tanpa nilai tukar.
- Pastikan nama game tidak ditemukan tetap menghasilkan 404.
- Tambahkan pemeriksaan bahwa teks dummy dan data contoh tidak muncul di halaman hasil.
Kriteria selesai
- Tautan game dari Deals membuka halaman desain prototipe pada /games/<id>.
- Konten dan harga halaman berasal dari database.
- Harga termurah hanya ditentukan jika perbandingan mata uang valid.
- Aset dan navigasi bekerja dari URL detail.
- Tombol yang belum didukung tidak memberi kesan bahwa aksinya berhasil.
- Pengujian detail game lulus.
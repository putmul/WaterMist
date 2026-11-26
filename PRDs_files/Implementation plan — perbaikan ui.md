Rencana implementasi perbaikan UI
Rencana ini mengikuti pilihan Anda: semua harga ditampilkan dalam IDR dan pagination rekomendasi dibuat terpisah per tab. Belum ada file yang diubah.
1. Rapikan pagination
- Samakan tampilan dan navigasi pagination di Deals, Recently Released, dan Recommendations.
- Gunakan kontrol yang konsisten: sebelumnya, nomor halaman, berikutnya, dan informasi halaman aktif.
- Pertahankan parameter pencarian, filter, dan mode saat berpindah halaman.
- Pastikan tombol yang tidak tersedia dinonaktifkan dan navigasi tetap bisa digunakan dengan keyboard.
2. Tambahkan pagination rekomendasi per tab
- Tambahkan pagination terpisah untuk Popular Picks dan Hidden Gem.
- Simpan halaman aktif pada parameter berbeda, misalnya popular_page dan gems_page, agar berpindah tab tidak mereset halaman tab lain.
- Pastikan hasil rekomendasi tersedia lebih banyak daripada satu halaman. Saat ini route membatasi rekomendasi pencarian hingga 12 item, sedangkan hasil rekomendasi tersimpan untuk pengguna juga berjumlah terbatas; bagian ini perlu disesuaikan agar pagination benar-benar menampilkan halaman tambahan.
- Tetap pertahankan pilihan genre/tag dan tab aktif ketika berpindah halaman.
3. Rapikan topnav
- Hapus pilihan bahasa dari topnav.
- Hilangkan kolom “Cari game” di halaman Recently Released, Deals, dan Recommendations.
- Detail game juga tidak termasuk halaman tersebut, jadi kolom pencarian tetap mengikuti perilaku topnav yang ada kecuali Anda ingin menghilangkannya di sana juga.
4. Konsistenkan mata uang menjadi IDR
- Hapus pemilih mata uang di topnav.
- Tampilkan harga dalam IDR secara konsisten di Deals dan detail game.
- Di detail game, gunakan nilai konversi IDR untuk harga utama dan tabel perbandingan; hilangkan kontrol atau pilihan mata uang di halaman tersebut.
- Tentukan perilaku untuk harga yang tidak bisa dikonversi: tampilkan keterangan bahwa konversi tidak tersedia, bukan angka yang seolah-olah IDR. Kurs yang tersedia tetap mengikuti konfigurasi proyek.
5. Sederhanakan filter Deals
- Hapus input diskon dan pemilihan toko.
- Hapus opsi pengurutan Nama, Toko, dan Relevansi.
- Pertahankan opsi pengurutan lain yang masih berguna, seperti harga, diskon, dan popularitas.
- Sesuaikan kondisi tombol “Hapus filter” dan parameter pagination agar tidak lagi memakai filter yang dihapus.
6. Hilangkan game duplikat pada Deals
- Pastikan satu game hanya muncul sekali, meskipun memiliki beberapa deal aktif dari toko atau sumber berbeda.
- Pilih deal yang akan ditampilkan secara konsisten—misalnya harga IDR terendah yang dapat dibandingkan—dan pertahankan akses ke seluruh penawaran pada halaman detail game.
- Pastikan deduplikasi tidak mengubah hasil pencarian semantik atau menghilangkan toko dari perbandingan detail.
7. Pengujian
- Tambahkan atau perbarui test untuk pagination per tab, filter Deals, deduplikasi game, pencarian topnav per halaman, dan harga IDR.
- Uji kasus kurs tidak tersedia, hasil kosong, serta perpindahan halaman dengan filter/pencarian aktif.
- Jalankan seluruh test suite setelah perubahan UI dan backend terkait diterapkan.
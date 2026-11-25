Rencana integrasi /app dan /web
Tujuan: menjadikan /web sebagai frontend utama, menggunakan backend dan layanan yang sudah ada di /app, serta menjalankan semuanya melalui run.py. Profil dan login/sign-in belum termasuk cakupan.
1. Petakan fitur yang akan diintegrasikan
Hubungkan halaman prototipe di /web dengan fitur backend yang sudah tersedia:
Halaman frontend	Backend yang digunakan
Beranda (index.html)	Route beranda; tautan menuju fitur utama
Deals (deals.html)	deals_bp dan DealService
Rilis baru (new-releases.html)	releases_bp dan layanan game/rilis
Rekomendasi (recommendations.html)	recommendations_bp dan RecommendationService
Pencarian, filter, pengurutan, dan pagination diintegrasikan sejauh didukung backend. Jangan menampilkan data dummy sebagai hasil nyata.
2. Jadikan Flask menyajikan frontend /web
Konfigurasikan Flask agar menggunakan:
- web/template sebagai sumber halaman HTML.
- web/static sebagai sumber CSS, JavaScript, dan aset.
Perbarui referensi aset agar menggunakan URL Flask yang konsisten, bukan path relatif seperti ../static/.... Dengan begitu, halaman tetap dapat dimuat melalui route aplikasi.
3. Sesuaikan route untuk merender halaman /web
Pertahankan struktur Blueprint dan layanan backend yang sudah ada. Ubah route fitur yang relevan agar merender halaman frontend di /web dan memberikan data yang diperlukan ke halaman tersebut.
Halaman yang belum memiliki route Flask—terutama beranda—perlu diberi route yang sesuai. Tautan navigasi /web harus menuju route aplikasi, bukan file .html secara langsung.
4. Tentukan cara mengirim data ke frontend
Untuk integrasi awal, gunakan rendering template Flask: route mengambil data dari service lalu mengirimkannya ke halaman sebagai konteks template. Ini mengurangi perubahan dan tidak memerlukan frontend framework baru.
Jika nanti dibutuhkan pembaruan halaman tanpa reload atau pemisahan frontend-backend, API JSON dapat ditambahkan sebagai tahap lanjutan.
5. Hubungkan interaksi halaman dengan backend
Ganti data contoh dan interaksi lokal dengan parameter atau data dari backend, termasuk:
- Deals: pencarian, toko, rentang harga, diskon, pengurutan, dan pagination yang tersedia.
- Rilis baru: daftar rilis dari backend dan filter yang memang didukung.
- Rekomendasi: hasil rekomendasi dari backend.
Tombol atau kontrol yang belum punya dukungan backend sebaiknya tidak memberi kesan bahwa aksinya sudah tersimpan atau diterapkan.
6. Pertahankan run.py sebagai entry point
run.py tetap membuat Flask app melalui create_app() dan menjadi cara standar menjalankan proyek. Scheduler tetap dikendalikan oleh konfigurasi yang sudah ada; hindari memulainya lebih dari sekali saat aplikasi dijalankan.
7. Uji integrasi
Periksa bahwa:
- run.py berhasil menjalankan aplikasi.
- Beranda dan tiga halaman fitur dapat dibuka lewat route Flask.
- CSS, JavaScript, dan gambar termuat dengan benar.
- Data halaman berasal dari backend, bukan array contoh.
- Filter dan pencarian mengirim parameter yang sesuai.
- Fungsi backend yang sudah ada tetap lolos pengujian.
Di luar cakupan
Profil, login/sign-in, serta perubahan autentikasi tidak disentuh. Template prototipe di app/templates dapat dibiarkan selama transisi; penghapusan atau pemindahannya dilakukan terpisah setelah semua fitur yang diperlukan sudah menggunakan /web.
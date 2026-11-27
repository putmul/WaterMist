Rencana implementasi integrasi Quiz WaterMist
Dari peninjauan, ketiga file sudah ada di web/template/quiz.html, web/static/css/quiz.css, dan web/static/js/quiz.js. Proyek Flask juga sudah memiliki alur onboarding quiz di app/routes/auth.py, penyimpanan jawaban melalui UserQuizAnswer, preferensi lewat UserPreference, dan generator rekomendasi. Jadi, rencana utamanya adalah menghubungkan UI baru ke alur yang sudah ada, bukan membuat sistem quiz terpisah.
1. Satukan halaman quiz dengan routing Flask
- Sajikan web/template/quiz.html melalui route /onboarding/quiz yang sudah ada; pastikan halaman tetap membutuhkan login.
- Hapus atau gantikan template sederhana di app/templates/onboarding/quiz.html agar tidak ada dua versi quiz yang membingungkan.
- Sesuaikan template untuk memakai URL Flask dan static asset, bukan path relatif seperti css/quiz.css, js/quiz.js, dan recommendations.html.
- Pastikan halaman memakai layout, topbar, dan footer WaterMist yang sesuai. Template saat ini memakai slot serta aset yang mungkin belum cocok dengan struktur halaman Flask.
2. Cocokkan data quiz dengan backend
Quiz baru menyimpan lima kelompok jawaban: genre, activity, mode, session, dan budget. Backend saat ini hanya mengharapkan genres dan tags.
- Tetapkan pemetaan sebelum implementasi:
- genre → preferensi bertipe genre.
- activity → kemungkinan preferensi bertipe tag, setelah label dipetakan ke tag yang konsisten dengan data game.
- mode, session, dan budget → simpan sebagai jawaban quiz; jangan langsung masukkan ke sistem rekomendasi sebelum ada aturan pemetaan yang jelas.
- Gunakan UserQuizAnswer untuk menyimpan jawaban per question_key. Model tersebut sudah mendukung jawaban teks, tetapi penyimpanan saat ini menggabungkan genre/tag menjadi satu nilai; backend perlu diselaraskan dengan bentuk data baru.
- Validasi nilai di server berdasarkan pilihan yang diizinkan. Jangan mengandalkan validasi JavaScript atau menerima nilai bebas dari browser.
- Tentukan apakah jawaban kosong untuk suatu pertanyaan diperbolehkan. JavaScript sekarang mewajibkan setidaknya satu pilihan di setiap langkah.
3. Ubah penyimpanan lokal menjadi pengiriman ke backend
- Pertahankan localStorage sebagai penyimpanan sementara agar jawaban bisa dipulihkan bila pengguna berpindah halaman atau sesi terputus.
- Saat tombol Selesai ditekan, kirim seluruh jawaban ke /onboarding/quiz melalui POST yang kompatibel dengan autentikasi dan proteksi CSRF aplikasi.
- Tampilkan status proses, kegagalan penyimpanan, dan opsi untuk mencoba lagi. Jangan menampilkan layar sukses sampai backend mengonfirmasi penyimpanan.
- Setelah berhasil, arahkan pengguna ke route rekomendasi Flask. Tombol Ulangi Quiz perlu memulai kembali quiz dengan perilaku penyimpanan yang disepakati, bukan hanya mengubah tampilan lokal.
4. Simpan secara konsisten dan perbarui rekomendasi
- Di handler backend, validasi semua jawaban lalu simpan jawaban dan preferensi quiz dalam satu transaksi.
- Saat quiz dikirim ulang, ganti jawaban dan preferensi source="quiz" milik pengguna tanpa menghapus preferensi dari Steam, favorit, atau interaksi.
- Pertahankan pembaruan preference_mode dan onboarding_status.
- Jalankan RecommendationService().generate_for_user(user) setelah commit, dengan penanganan kegagalan agar jawaban yang sudah tersimpan tidak dianggap gagal hanya karena pembuatan rekomendasi bermasalah.
5. Rapikan perilaku UI dan aset
- Perbarui link dan pemuatan CSS/JavaScript menggunakan URL Flask.
- Pastikan gambar peti memiliki aset yang benar; saat ini halaman memakai path relatif assets/images/quiz-chest.png.
- Periksa bahwa style baru tidak bertabrakan dengan CSS global atau layout utama, serta tetap berfungsi untuk layar kecil dan keyboard/screen reader.
- Buat ringkasan hasil dari jawaban yang tersimpan/terkonfirmasi, bukan hanya dari state browser.
6. Verifikasi integrasi
Tambahkan atau sesuaikan pengujian untuk:
- Akses quiz tanpa login dan dengan login.
- Pengiriman nilai valid, jawaban tidak lengkap, nilai tidak dikenal, dan pengiriman ulang.
- Penyimpanan seluruh lima kelompok jawaban dan pembaruan preferensi yang tepat.
- Isolasi data antarpengguna serta tidak terhapusnya sumber preferensi lain.
- Kegagalan generator rekomendasi setelah jawaban tersimpan.
- Perilaku frontend: lanjut/kembali, batas pilihan, pemulihan jawaban, dan feedback saat request gagal.
Keputusan desain yang perlu dikunci sebelum implementasi: apakah activity dipetakan menjadi tag rekomendasi, dan apakah mode, session, serta budget hanya disimpan untuk personalisasi berikutnya atau turut memengaruhi perankingan rekomendasi.
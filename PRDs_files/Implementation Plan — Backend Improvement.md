Rencana implementasi peningkatan performa backend
Rencana ini berfokus pada bottleneck yang terlihat di /app. Terapkan bertahap agar perubahan mudah diuji dan dampaknya bisa dibandingkan. Belum ada file yang diubah.
Fase 1 — Buat baseline dan pastikan perilaku saat ini
1. Catat waktu respons dan jumlah query untuk:
- GET /deals dengan dan tanpa kata pencarian.
- GET /recommendations.
- Halaman detail game.
2. Ukur durasi job sinkronisasi deals dan release, beserta jumlah record yang diproses.
3. Siapkan data uji dengan volume yang mendekati kondisi sebenarnya.
4. Pastikan test yang ada lulus sebelum perubahan dimulai.
Hasil yang diharapkan: angka pembanding awal, sehingga optimasi bisa dinilai berdasarkan pengukuran, bukan perkiraan.
Fase 2 — Optimalkan pencarian dan paginasi deals
1. Tinjau perilaku dan hasil pencarian saat ini di app/services/deal_service.py.
2. Pindahkan filter, urutan relevansi, dan paginasi ke query database agar aplikasi tidak perlu memuat dan mengurutkan semua hasil di Python.
3. Pertahankan aturan relevansi saat ini—kecocokan persis, awalan nama, lalu kecocokan sebagian—serta filter harga, diskon, toko, dan currency.
4. Periksa query untuk pencarian token fallback dan pencarian semantik supaya hasil dan jumlah halaman tetap benar.
5. Tambahkan atau sesuaikan indeks hanya setelah memastikan query yang mendasarinya membutuhkan indeks tersebut.
Verifikasi: uji pencarian persis, sebagian, tanpa hasil, semua filter, urutan, serta perpindahan halaman. Bandingkan waktu respons dan jumlah data yang dibaca.
Fase 3 — Kurangi biaya pencocokan game saat sinkronisasi
1. Hapus pola pemindaian seluruh tabel Game untuk setiap record di _find_game().
2. Pilih strategi pencocokan nama:
- Pilihan utama: kolom nama ternormalisasi yang diindeks dan dijaga konsisten saat nama game berubah.
- Alternatif awal: buat peta nama ternormalisasi sekali di awal batch sinkronisasi dan gunakan ulang selama batch.
3. Pastikan pencocokan berdasarkan Steam App ID dan produk toko tetap didahulukan.
4. Tambahkan test untuk variasi nama, edisi game, dan nama yang menghasilkan kecocokan ambigu.
Verifikasi: bandingkan durasi sinkronisasi pada volume record yang sama dan pastikan jumlah serta identitas game yang tersimpan tidak berubah secara tak terduga.
Fase 4 — Kurangi query berulang pada proses sinkronisasi
1. Profilkan _upsert_record() dan _upsert_release_record() untuk menemukan lookup yang paling sering berulang.
2. Cache store, genre, dan tag yang digunakan selama satu batch.
3. Evaluasi batch insert/update untuk snapshot harga dan relasi genre/tag.
4. Pertahankan batas transaksi dan isolasi kegagalan record agar satu record bermasalah tidak menggagalkan seluruh batch.
5. Pastikan ada perlindungan terhadap record duplikat, termasuk melalui constraint atau indeks unik yang sesuai dengan skema saat ini.
Verifikasi: uji record baru, record yang sudah ada, record invalid, dan kegagalan di tengah batch. Bandingkan waktu job dan jumlah query.
Fase 5 — Optimalkan rekomendasi dan pemuatan relasi
1. Ukur biaya Game.query.all() dan proses ranking di app/services/recommendation_service.py.
2. Tentukan kriteria kandidat yang aman untuk disaring di database tanpa mengubah hasil rekomendasi yang diharapkan.
3. Periksa akses relasi pada halaman deals, rekomendasi, dan detail game.
4. Jika ditemukan pola N+1, tambahkan eager loading pada query yang tepat, lalu pastikan pagination tetap bekerja dengan benar.
Verifikasi: bandingkan jumlah kandidat, jumlah query, waktu endpoint, dan hasil rekomendasi untuk user anonim maupun login.
Fase 6 — Validasi, benchmark, dan rilis bertahap
1. Jalankan seluruh test, termasuk test pencarian, rekomendasi, sinkronisasi, dan migrasi database.
2. Bandingkan baseline dengan hasil setelah tiap fase:
- Waktu respons median dan p95.
- Jumlah query per request.
- Durasi job sinkronisasi.
- Jumlah kandidat yang dimuat dan hasil yang ditampilkan.
3. Tinjau query plan untuk query lambat dan sesuaikan indeks berdasarkan bukti.
4. Rilis per fase dan pantau error, hasil pencarian, serta waktu respons setelah tiap rilis.
Urutan prioritas
1. Pencarian dan paginasi deals di database.
2. Menghindari pemindaian seluruh game saat sinkronisasi.
3. Mengurangi query berulang pada sinkronisasi dan snapshot harga.
4. Memeriksa pemuatan relasi dan optimasi rekomendasi.
5. Menambahkan indeks berdasarkan hasil pengukuran.
Catatan: implementasi kolom baru atau indeks memerlukan migrasi database. Sebaiknya migrasi dirancang setelah database yang digunakan dan aturan deploy proyek dipastikan.
Implementation Plan — List Hidden Gems
1. Definisi Hidden Gem
Game dikategorikan sebagai Hidden Gem jika memenuhi seluruh kriteria berikut:
- Persentase review positif minimal 80%.
- Jumlah review minimal 25 agar game dengan 1–2 review tidak langsung dianggap bagus.
- Jumlah review relatif rendah dibanding kandidat lain.
- popularity_score <= 0.40.
- Memiliki metadata review yang valid.
Konfigurasi awal:
HIDDEN_GEM_MIN_RATING_PERCENT = 80
HIDDEN_GEM_MIN_REVIEWS = 25
HIDDEN_GEM_MAX_REVIEWS = 10000
HIDDEN_GEM_MAX_POPULARITY_SCORE = 0.40
Nilai tersebut sebaiknya diletakkan di config.py, bukan hardcode di ranking.
2. Kondisi Kode Saat Ini
Fondasi fitur sudah tersedia:
- Metadata review berada di Game:
- steam_rating_percent
- steam_rating_count
- steam_rating_text
- Perhitungan kualitas dan popularitas sudah ada di:
- app/recommendation/scoring.py
- Ranking Hidden Gems sudah ada di:
- app/recommendation/ranking.py
- Hasil rekomendasi sudah disimpan melalui:
- RecommendationRun
- Recommendation
- Tampilan Hidden Gems sudah tersedia di:
- app/templates/recommendations.html
Namun, filter saat ini masih menggunakan:
popularity_score <= 0.40
quality_score >= 0.55
Filter tersebut belum memiliki batas minimal jumlah review dan belum menggunakan rating positif mentah secara eksplisit.
3. Perubahan Scoring
File: app/recommendation/scoring.py
Tambahkan fungsi untuk menentukan eligibility:
is_hidden_gem(rating_percent, review_count, popularity_score)
Aturan:
1. Rating harus tersedia.
2. Rating minimal 80%.
3. Jumlah review minimal 25.
4. Jumlah review tidak melebihi batas maksimal.
5. Popularity score maksimal 0.40.
quality_score tetap digunakan untuk ranking, sedangkan rating_percent digunakan sebagai syarat kelayakan. Ini mencegah rating tinggi dengan jumlah review sangat sedikit dianggap valid.
Naikkan ALGORITHM_VERSION, misalnya:
ALGORITHM_VERSION = "personalized-v2-hidden-gem"
4. Perubahan Ranking
File: app/recommendation/ranking.py
Alur baru:
1. Ambil seluruh kandidat sebelum pagination.
2. Hilangkan game yang:
- sudah dimiliki;
- sudah di-dismiss;
- tidak memiliki metadata review valid.
3. Hitung max_reviews dari seluruh kandidat.
4. Hitung:
- popularity_score;
- quality_score;
- novelty_score.
5. Terapkan is_hidden_gem.
6. Urutkan kandidat yang lolos.
Untuk pengguna dengan profil:
HiddenGemScore =
0.70 × Fit
+ 0.20 × Quality
+ 0.10 × Novelty
Untuk anonymous user atau pengguna tanpa profil, gunakan ranking umum yang lebih menekankan kualitas:
GenericHiddenGemScore =
0.70 × Quality
+ 0.30 × Novelty
Dengan begitu, list Hidden Gems tetap dapat muncul meskipun pengguna belum mengisi preferensi.
5. Ketersediaan Metadata Review
Metadata review saat ini terutama diperbarui melalui DealService dari data CheapShark.
Untuk list Hidden Gems yang mencakup seluruh game, perlu memastikan game non-deal juga mempunyai metadata review. Pilihan implementasi:
1. Gunakan data CheapShark jika tersedia.
2. Tambahkan parsing rating review pada detail Steam.
3. Simpan hasil ke kolom review pada games.
4. Gunakan review_updated_at untuk menentukan data yang perlu diperbarui.
Game tanpa rating atau jumlah review tidak dimasukkan ke list Hidden Gems, bukan dianggap memiliki rating nol.
6. Recommendation Service
File: app/services/recommendation_service.py
Perubahan:
- Simpan hanya hasil yang memenuhi kriteria Hidden Gem.
- Tambahkan alasan khusus, misalnya:
"Review positif 92% dengan 180 review, sehingga termasuk game berkualitas yang belum terlalu populer."
- Bedakan reason_code untuk Hidden Gems, misalnya:
hidden_gem_quality_low_popularity
- Tetap gunakan tabel recommendations yang sudah ada. Belum diperlukan migration baru karena kolom skor dan tipe rekomendasi sudah tersedia.
7. Tampilan List
File: app/templates/recommendations.html
Pada setiap kartu Hidden Gem tampilkan:
- nama game;
- cover;
- rating positif;
- jumlah review;
- label Hidden Gem;
- alasan game dipilih;
- skor rekomendasi;
- tombol favorit dan sembunyikan.
Contoh informasi:
92% positif · 180 review
Hidden Gem karena review sangat baik tetapi belum populer.
Jika jumlah hasil kurang dari batas yang diminta, tampilkan hanya game yang benar-benar memenuhi kriteria. Jangan mengisi list dengan game rating rendah.
8. Pengujian
Tambahkan atau ubah test berikut:
Scoring
- Rating 79% tidak lolos.
- Rating 80% lolos jika jumlah review cukup.
- Rating 100% dengan 1 review tidak lolos.
- Rating kosong tidak lolos.
- Jumlah review 0 tidak lolos.
- Popularity score di atas 0.40 tidak lolos.
- Nilai skor tetap berada pada rentang 0–1.
Ranking
- Kandidat dihitung berdasarkan seluruh dataset, bukan hanya halaman pertama.
- Game yang dimiliki tidak muncul.
- Game yang di-dismiss tidak muncul.
- Game dengan rating tinggi dan jumlah review rendah muncul.
- Game populer dengan rating tinggi tidak masuk Hidden Gems.
- Anonymous user tetap mendapatkan list Hidden Gems.
- Jika tidak ada kandidat valid, tampilkan list kosong dengan pesan yang sesuai.
Persistence dan UI
- Recommendation bertipe hidden_gem tersimpan.
- Alasan rekomendasi tersimpan.
- Review dan jumlah review tampil di kartu.
- Perubahan algoritma tercatat melalui algorithm_version.
9. Urutan Implementasi
1. Tambahkan konfigurasi threshold di config.py.
2. Tambahkan fungsi eligibility di scoring.py.
3. Ubah filter dan fallback ranking di ranking.py.
4. Pastikan metadata review game diperbarui dari sumber data.
5. Tambahkan reason khusus di RecommendationService.
6. Perbarui template Hidden Gems.
7. Tambahkan unit test dan integration test.
8. Lakukan evaluasi manual dengan beberapa dataset game.
Acceptance Criteria
Fitur dianggap selesai jika:
- Game dengan review minimal 80% dan jumlah review rendah dapat muncul.
- Game dengan sedikit review tetapi rating tidak terpercaya tidak muncul.
- Game populer tidak diklasifikasikan sebagai Hidden Gem.
- List tetap berfungsi tanpa profil pengguna.
- Game yang sudah dimiliki atau di-dismiss tidak muncul.
- Setiap item menampilkan rating, jumlah review, dan alasan klasifikasinya.
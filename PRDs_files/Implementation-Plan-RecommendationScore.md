Implementation Plan — Data Review, Discount, dan Recommendation Score
1. Kondisi saat ini
- CheapSharkClient.normalize() baru mengambil harga, diskon, toko, dan URL.
- Data yang dibutuhkan belum disimpan:
- steamRatingPercent
- steamRatingCount
- steamRatingText
- releaseDate
- Model Game belum memiliki kolom rating dan jumlah review.
- Modul rekomendasi masih berupa placeholder.
- Rencana lama di PRDs_files/implemetation-plan-popularity.md menggunakan formula berbeda, sehingga perlu disesuaikan dengan formula terbaru.
2. Kontrak data ter-normalisasi
Semua collector sebaiknya menghasilkan field berikut:
{
    "steam_app_id": str | None,
    "name": str,
    "steam_rating_percent": int | None,  # 0–100
    "steam_rating_count": int | None,    # >= 0
    "steam_rating_text": str | None,
    "release_date": date | None,
    "review_source": "cheapshark" | "steam" | None,
    "review_updated_at": datetime | None,
}
Mapping CheapShark:
CheapShark	Internal
steamRatingPercent	steam_rating_percent
steamRatingCount	steam_rating_count
steamRatingText	steam_rating_text
releaseDate	release_date
steamAppID	steam_app_id
Nilai invalid seperti "", "N/A", atau None harus menjadi None, bukan 0.
3. Perubahan CheapShark API client
File
- app/collectors/cheapshark_client.py
Perubahan
1. Tambahkan parser numerik:
- parser persentase rating dengan batas 0–100;
- parser jumlah review dengan batas minimum 0;
- parser tanggal rilis.
2. Perluas normalize() agar mengambil field rating dari respons /deals.
3. Gunakan /deals sebagai sumber utama karena field review biasanya tersedia langsung di respons deal.
4. Tambahkan fallback enrichment untuk data yang tidak tersedia:
- gunakan fetch_deal(deal_id) atau endpoint game yang relevan;
- cache berdasarkan dealID/steamAppID;
- jangan melakukan request berulang untuk game yang sama;
- kegagalan enrichment tidak boleh menggagalkan penyimpanan harga dan diskon.
5. Pertahankan:
- pagination;
- retry dan backoff;
- rate limiting;
- link redirect CheapShark.
6. Tambahkan logging jumlah record:
- rating lengkap;
- rating tidak tersedia;
- enrichment berhasil;
- enrichment gagal.
4. Perubahan Steam discount scraper
File
- app/collectors/steam_scraper.py
- Jika diperlukan: app/collectors/steam_release_bot.py
Perubahan
1. Pertahankan scraping:
- nama game;
- Steam App ID;
- harga normal;
- harga diskon;
- persentase diskon;
- tanggal akhir diskon;
- URL dan gambar.
2. Samakan format output Steam dengan format CheapShark.
3. Tambahkan review extraction dari halaman detail Steam sebagai fallback opsional jika:
- CheapShark tidak memiliki data;
- data CheapShark tidak dapat dipetakan ke game Steam.
4. Jika struktur HTML review Steam tidak stabil, jangan menjadikannya sumber utama. Data CheapShark tetap diprioritaskan.
5. Tambahkan review_source agar sumber data dapat diaudit.
5. Perubahan database
File
- app/models/game.py
- app/models/deal.py
- app/models/__init__.py
- migration baru, misalnya:
- migrations/versions/0005_review_metadata.py
Kolom baru pada games
steam_rating_percent   INTEGER NULL
steam_rating_count     BIGINT NULL
steam_rating_text      VARCHAR NULL
review_source          VARCHAR NULL
review_updated_at      DATETIME NULL
release_date sudah tersedia dan dapat digunakan kembali.
Opsional pada deals
Jika ingin menyimpan metadata tambahan:
deal_rating       DECIMAL NULL
metacritic_score  INTEGER NULL
Namun kedua field tersebut tidak digunakan dalam formula Quality Score yang diminta.
6. Perubahan proses penyimpanan
File
- app/services/deal_service.py
- app/services/game_service.py
Aturan upsert
1. Cari game berdasarkan steam_app_id.
2. Jika tidak ditemukan, gunakan pencocokan nama seperti saat ini.
3. Simpan metadata review pada tabel games, bukan pada setiap deal.
4. Data baru hanya menimpa data lama jika nilainya valid dan tidak None.
5. Jika CheapShark tidak mengirim rating pada suatu run, data rating lama tidak boleh dihapus.
6. CheapShark dan Steam yang merujuk Steam App ID yang sama harus memperbarui record Game yang sama.
7. Update review_updated_at hanya jika ada metadata review baru.
7. Implementasi formula scoring
File baru
- app/recommendation/scoring.py
Popularity Score
P = log(1 + total_reviews) / log(1 + max_reviews)
Aturan:
- max_reviews dihitung dari seluruh kandidat dalam satu batch.
- Tidak dihitung per halaman.
- Jika max_reviews == 0, hasil P = 0.
- Hasil dibatasi pada rentang 0–1.
Mapping:
ReviewScore = steam_rating_percent / 100
TotalReviews = steam_rating_count
Quality Score
Q = ReviewScore - (
    (ReviewScore - 0.5)
    * 2 ** (-log10(TotalReviews + 1))
)
Aturan:
- ReviewScore berada pada rentang 0–1.
- TotalReviews minimal 0.
- Jika TotalReviews == 0, formula menghasilkan nilai netral mendekati 0.5.
- Rating kosong tidak dianggap sebagai rating 0; kandidat ditandai tidak lengkap.
Final Score
FinalScore = 0.5 * P + 0.5 * Q
Semua hasil harus dibatasi pada 0–1.
P dan Q tidak disimpan permanen pada Game karena P bergantung pada max_reviews dari dataset/batch tertentu.
8. Integrasi recommendation service
File
- app/services/recommendation_service.py
- app/recommendation/ranking.py
- app/routes/recommendations.py
- app/templates/recommendations.html
Alur:
1. Ambil kandidat game dari database.
2. Tentukan dataset kandidat.
3. Hitung max_reviews.
4. Hitung P dan Q setiap game.
5. Hitung FinalScore.
6. Urutkan berdasarkan FinalScore secara descending.
7. Simpan hasil scoring beserta:
- popularity_score;
- quality_score;
- final_score;
- generated_at;
- max_reviews atau identitas batch scoring.
Game tanpa data review lengkap dapat:
- dikeluarkan dari ranking utama; atau
- ditampilkan sebagai fallback dengan status data tidak lengkap.
9. Scheduler
File
- app/services/scheduler_service.py
Urutan sinkronisasi harian:
1. Scraping game dan diskon Steam.
2. Sinkronisasi deal CheapShark.
3. Update metadata review pada games.
4. Jalankan proses perhitungan scoring.
5. Simpan hasil rekomendasi.
Jika sinkronisasi CheapShark gagal, data lama tetap dipertahankan dan proses scoring menggunakan snapshot terakhir yang tersedia.
10. Pengujian
File baru/perubahan
- tests/test_cheapshark_client.py
- tests/test_deal_service.py
- tests/test_scoring.py
- tests/test_recommendation_service.py
Skenario wajib
CheapShark
- Parsing steamRatingPercent.
- Parsing steamRatingCount.
- Nilai kosong atau invalid.
- Nilai rating di luar rentang.
- Pagination tetap berjalan.
- Enrichment tidak melakukan request duplikat.
- Metadata lama tidak tertimpa NULL.
Scoring
- total_reviews = 0.
- max_reviews = 0.
- total_reviews == max_reviews.
- Rating positif 0%, 50%, dan 100%.
- Jumlah review besar.
- Data review tidak tersedia.
- Hasil selalu berada pada rentang 0–1.
- Verifikasi bobot 0.5P + 0.5Q.
Integrasi
- Deal CheapShark tersimpan.
- Game berdasarkan Steam App ID berhasil diperbarui.
- Rating Steam dan jumlah review tersimpan.
- Scoring menggunakan seluruh kandidat, bukan hanya satu halaman.
- Scheduler menjalankan scoring setelah sinkronisasi data.
11. Urutan pengerjaan
 1. Tambahkan parser field review pada CheapSharkClient.
 2. Perbarui format normalisasi Steam dan CheapShark.
 3. Tambahkan kolom metadata review pada Game.
 4. Buat migration database.
 5. Perbarui proses upsert agar metadata tidak hilang saat nilai kosong.
 6. Tambahkan fallback enrichment CheapShark dengan cache.
 7. Buat app/recommendation/scoring.py.
 8. Integrasikan scoring ke recommendation service.
 9. Integrasikan proses scoring ke scheduler.
10. Tambahkan route/template rekomendasi.
11. Tambahkan unit test dan integration test.
12. Validasi hasil menggunakan dataset nyata.
Tidak ada file yang diubah pada tahap penyusunan rencana ini.
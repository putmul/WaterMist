# Implementation Plan — Scoring, Ranking, dan Recommendation

## Status

Ditunda. Dokumen ini menjadi rencana fase berikutnya dan tidak termasuk dalam
implementasi metadata review/diskon saat ini.

## Tujuan

Menghitung skor popularitas dan kualitas dari metadata review yang telah
disimpan pada `games`, lalu menggunakannya untuk ranking dan recommendation.

## Formula

### Popularity Score

Untuk setiap batch kandidat:

```text
P = log(1 + TotalReviews) / log(1 + MaxReviews)
```

- `TotalReviews` berasal dari `games.steam_rating_count`.
- `MaxReviews` dihitung sekali dari seluruh kandidat batch, bukan per halaman.
- Jika `MaxReviews == 0`, `P = 0`.
- Hasil dibatasi pada rentang `0–1`.

### Quality Score

```text
ReviewScore = steam_rating_percent / 100

Q = ReviewScore
    - (ReviewScore - 0.5) * 2^(-log10(TotalReviews + 1))
```

- `ReviewScore` berada pada rentang `0–1`.
- `TotalReviews == 0` tetap merupakan nilai valid dan menghasilkan skor netral.
- Metadata review yang tidak tersedia tidak boleh dianggap sebagai rating `0`.

### Final Score

```text
FinalScore = 0.5 * P + 0.5 * Q
```

## Rencana perubahan

### 1. Modul perhitungan

Buat `app/recommendation/scoring.py` dengan fungsi terpisah:

- `calculate_popularity_score(total_reviews, max_reviews)`
- `calculate_quality_score(rating_percent, total_reviews)`
- `calculate_final_score(popularity_score, quality_score)`

Semua fungsi harus menangani nilai kosong, nol, nilai invalid, dan pembatasan
rentang skor.

### 2. Penyimpanan hasil scoring

Buat model/migration recommendation yang menyimpan:

- `game_id`
- `popularity_score`
- `quality_score`
- `final_score`
- `max_reviews`
- `generated_at`
- versi formula atau `score_version`

Skor tidak disimpan sebagai atribut permanen pada `Game` karena `P` bergantung
pada dataset kandidat dan nilai `MaxReviews` pada batch tersebut.

### 3. Ranking service

Implementasikan `app/recommendation/ranking.py` untuk:

1. mengambil kandidat yang valid;
2. menentukan `MaxReviews` dari seluruh kandidat;
3. menghitung `P`, `Q`, dan `FinalScore`;
4. mengurutkan kandidat berdasarkan `FinalScore` descending;
5. menyimpan metadata batch scoring.

Kandidat tanpa data review lengkap harus ditandai atau dikeluarkan dari ranking
utama, bukan diberi nilai `0` secara diam-diam.

### 4. Recommendation service

Implementasikan `app/services/recommendation_service.py` setelah ranking dasar
tersedia. Fase ini mencakup:

- kandidat game dari deal aktif;
- pengecualian game yang telah dimiliki pengguna;
- pengecualian game yang di-dismiss;
- cold-start fallback;
- kategori recommendation;
- alasan rekomendasi;
- penyimpanan hasil batch.

### 5. Scheduler dan route

Setelah scoring dan recommendation selesai diuji:

- jalankan batch setelah sinkronisasi deal harian;
- ubah `app/routes/recommendations.py` agar membaca hasil tersimpan;
- ubah template rekomendasi untuk menampilkan skor dan metadata review.

### 6. Pengujian

Tambahkan test untuk:

- `TotalReviews == 0`;
- `MaxReviews == 0`;
- kandidat dengan jumlah review maksimum;
- rating 0%, 50%, dan 100%;
- metadata review kosong;
- konsistensi hasil `FinalScore`;
- ranking menggunakan seluruh dataset;
- cold start dan filter game yang dimiliki/dismissed.

## Batasan fase ini

Fase ini tidak mengubah collector new releases dan tidak melakukan scraping
popularitas. Fase ini baru boleh dikerjakan setelah metadata review dari alur
discount/game-deals tersedia dan tervalidasi.

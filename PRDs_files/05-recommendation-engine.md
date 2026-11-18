# PRD Modul 05 — Recommendation Engine

**Proyek:** WaterVapor | **Versi:** 1.0 | **Tanggal:** 18 November 2026 | **Status:** Draft (belum dikembangkan)
**Dependensi:** Modul 01 (genre/tag), 03 (metadata game), 04 (profil pengguna) | **Dikonsumsi oleh:** Modul 06

## 1. Tujuan

Memberi rekomendasi game yang dipersonalisasi dalam dua kategori:

- **Popular Picks For You:** game populer yang sesuai preferensi pengguna.
- **Hidden Gems For You:** game kurang populer tetapi sangat sesuai preferensi.

Game niche tidak berarti kualitas rendah; istilah ini hanya merujuk popularitas/jangkauan pemain yang relatif kecil.

**Non-goal MVP:** collaborative filtering dan ML kompleks.

## 2. Input

| Input | Sumber |
|-------|--------|
| Game yang dimiliki dan playtime | `user_owned_games` (Modul 04) |
| Game favorit manual | `user_favorites` (Modul 04) |
| Interaksi pengguna | `user_interactions` (Modul 04) |
| Genre, tag, deskripsi, developer | `games`, `game_genres`, `game_tags` (Modul 01/03) |
| Data popularitas | Lihat bagian 6 |

## 3. Metode: Content-Based Filtering

Sistem menganalisis karakteristik game yang disukai pengguna, lalu mencari game lain dengan karakteristik serupa. Fitur: genre, tag, deskripsi, developer, elemen gameplay.

### 3.1. User Preference Profile

Bobot preferensi per genre/tag dihitung dari playtime, game favorit, dan interaksi.

| Genre | Preference Score (ilustrasi) |
|-------|-----------------------------:|
| RPG | 0.90 |
| Action | 0.80 |
| Adventure | 0.65 |
| Strategy | 0.20 |

Nilai di atas hanya ilustrasi. Disimpan di `user_preferences`. Usulan bobot sinyal awal (diuji dan disesuaikan dengan data nyata):

| Sinyal | Pengaruh |
|--------|----------|
| Playtime (dinormalisasi, mis. skala log agar satu game raksasa tidak mendominasi) | Utama |
| Favorit manual | Kuat |
| Interaksi positif (favorite, click deal) | Sedang |
| `dismiss_recommendation` | Negatif |

### 3.2. Similarity

- **TF-IDF** untuk representasi fitur teks/tag/genre game.
- **Cosine Similarity** antara vektor profil pengguna dan vektor tiap game kandidat.

### 3.3. Popular Picks

```text
PopularScore = (w1 × Similarity) + (w2 × Popularity)
```

### 3.4. Hidden Gems

```text
NicheScore = (w1 × Similarity) + (w2 × Novelty)
```

Hidden Gems memprioritaskan: similarity tinggi, popularitas relatif rendah, dan metadata cukup untuk dinilai. Bobot (w1, w2) dan ambang batas **harus diuji dengan data nyata**; simpan di konfigurasi, bukan hardcode.

## 4. Aturan Rekomendasi

- Game yang sudah dimiliki tidak direkomendasikan ulang secara default.
- Game yang sudah dimainkan dapat dikecualikan atau diberi prioritas lebih rendah.
- Game tanpa metadata yang cukup dikeluarkan dari kandidat.
- Popularitas rendah tidak otomatis berarti kualitas rendah; Hidden Gems sebaiknya punya syarat minimal kualitas (mis. ulasan positif di atas ambang tertentu, jumlah review minimum).
- Game yang di-dismiss tidak muncul lagi.

## 5. Kebutuhan Fungsional

| ID | Kebutuhan |
|----|-----------|
| FR-14 | Membentuk profil preferensi dari genre dan tag game yang dimainkan. |
| FR-15 | Popular Picks: kombinasi kesesuaian preferensi dan popularitas. |
| FR-16 | Hidden Gems: sesuai preferensi tetapi popularitas relatif rendah. |
| FR-18 | Menyertakan alasan singkat tiap rekomendasi, contoh: "Direkomendasikan karena kamu sering memainkan game RPG dengan elemen eksplorasi dan combat." |
| RE-19 | Mengumpulkan dan melengkapi genre/tag untuk game kandidat (enrichment). |
| RE-20 | Menghitung popularity score dan novelty score per game. |
| RE-21 | Menghitung rekomendasi secara batch (setelah sinkron harian) dan menyimpannya ke `recommendations`; halaman hanya membaca hasil tersimpan. |
| RE-22 | **Cold start:** jika profil pengguna kosong atau data terlalu sedikit, minta pengguna memilih favorit manual, dan sementara tampilkan game populer secara umum. |
| RE-23 | Menyimpan model/vektor (Joblib) agar tidak dihitung ulang tiap request. |
| RE-24 | Rekomendasi diperbarui setelah library/favorit pengguna berubah (trigger) dan lewat job harian. |

## 6. Data Popularitas

PRD awal menyebut indikator: jumlah pemain, jumlah review, jumlah ulasan positif, indikator lain yang tersedia. **Sumber data konkret belum ditetapkan.** Kandidat:

| Indikator | Kemungkinan sumber |
|-----------|--------------------|
| Jumlah review dan persentase positif | Data Steam Store (scraper/enrichment); CheapShark `/deals` juga membawa data rating Steam (cek dokumentasi untuk nama field) |
| Jumlah pemain | Steam API (jika tersedia) atau diabaikan di MVP |

Jika data popularitas tidak tersedia untuk sebuah game, gunakan indikator alternatif yang ada atau keluarkan dari klasifikasi Hidden Gems.

## 7. Skema Database

### `user_preferences`
| Field | Tipe | Keterangan |
|-------|------|-----------|
| id | BIGINT | PK |
| user_id | BIGINT | FK |
| genre_id | BIGINT | FK |
| preference_score | FLOAT | Bobot preferensi |

> Pertimbangkan menambah dimensi tag (bukan hanya genre), karena Soulslike atau Roguelike lebih sering berupa tag.

### `recommendations`
| Field | Tipe | Keterangan |
|-------|------|-----------|
| id | BIGINT | PK |
| user_id | BIGINT | FK |
| game_id | BIGINT | FK |
| recommendation_type | VARCHAR | `popular` / `niche` |
| similarity_score | FLOAT | |
| recommendation_score | FLOAT | Skor akhir |
| generated_at | TIMESTAMP | |
| *reason* | TEXT | **Usulan:** alasan rekomendasi (FR-18) |

## 8. Struktur Kode

`app/recommendation/preference_builder.py`, `similarity.py`, `ranking.py`, dan `app/services/recommendation_service.py`.

## 9. Evaluasi Kualitas

- Pengecekan manual (sanity check) untuk beberapa profil uji, misalnya pemain RPG berat, pemain strategi, dan profil kosong.
- Metrik sederhana: proporsi rekomendasi yang di-dismiss vs. di-klik/favorit.
- Tinjau ulang bobot (w1, w2) dan ambang Hidden Gems berdasarkan hasil.

## 10. Risiko

| Risiko | Dampak | Mitigasi |
|--------|--------|----------|
| Metadata tidak lengkap | Rekomendasi kurang akurat | Validasi dan enrichment; kecualikan game tanpa metadata |
| Data popularitas tidak tersedia | Klasifikasi niche kurang akurat | Indikator alternatif |
| Profil privat / data sedikit | Preferensi terbatas | Input manual; cold start |
| Bobot tidak optimal | Hasil kurang relevan | Konfigurasi bobot dan pengujian data nyata |

## 11. Tugas Pengembangan

- [ ] Mengumpulkan genre dan tag game (enrichment)
- [ ] Membuat user preference profile
- [ ] Mengimplementasikan TF-IDF
- [ ] Mengimplementasikan Cosine Similarity
- [ ] Menghitung popularity dan novelty score
- [ ] Membuat Popular Picks
- [ ] Membuat Hidden Gems
- [ ] Menyediakan alasan rekomendasi
- [ ] Batch job rekomendasi dan penanganan cold start
- [ ] Menguji kualitas rekomendasi

## 12. Acceptance Criteria

1. Sistem membentuk profil preferensi sederhana dari data Steam atau favorit manual.
2. Popular Picks dan Hidden Gems dapat ditampilkan, tanpa game yang sudah dimiliki.
3. Setiap rekomendasi punya alasan singkat.
4. Pengguna tanpa data mendapat fallback yang wajar, bukan halaman kosong.
5. Rekomendasi dibaca dari hasil tersimpan sehingga halaman tetap cepat.

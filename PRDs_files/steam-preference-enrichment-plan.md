# Implementation Plan — Steam Library Enrichment dan Preference Profile

## 1. Tujuan

Memperbaiki alur Steam library agar menghasilkan baris persisten di
`user_preferences` dengan `source='steam'`.

```text
Steam library → map App ID → upsert game → enrich metadata
→ hitung profile berbasis playtime → simpan user_preferences
→ generate recommendation
```

## 2. Diagnosis saat ini

Hasil pengecekan database:

- Steam profile berstatus `success`.
- Ada 28 `user_owned_games`.
- Hanya 6 game memiliki `game_id` ter-map.
- 22 App ID belum memiliki record pada `games`.
- 6 game ter-map tidak memiliki genre, tag, maupun developer.
- `user_preferences` hanya memiliki 4 baris dari quiz.
- Rebuild preference Steam menghasilkan 0 baris karena tidak ada feature game.

## 3. Prinsip desain

1. `user_owned_games` menyimpan ownership dan playtime.
2. `games` menjadi canonical metadata game.
3. Enrichment berjalan di background/sinkronisasi, bukan pada request recommendation.
4. Recommendation hanya membaca profile yang sudah tersimpan di database.
5. Preference quiz tidak dihapus ketika Steam terhubung.
6. Mode `steam` memakai `source='steam'`; mode `quiz` memakai `source='quiz'`.
7. Metadata kosong tidak dianggap sebagai preference negatif atau rating nol.

## 4. Perubahan yang diperlukan

### 4.1. Steam library fetch

Perbarui `SteamService`:

1. Gunakan `include_appinfo=1` agar nama game ikut diambil.
2. Upsert game dasar berdasarkan `steam_app_id`.
3. Isi `user_owned_games.game_id` setelah game berhasil dibuat atau ditemukan.
4. Catat game yang belum memiliki genre/tag/developer sebagai kandidat enrichment.
5. Jangan menghapus data lama ketika sync sebagian gagal.

### 4.2. Game metadata enrichment

Buat service terpisah, misalnya `app/services/game_enrichment_service.py`.

Tanggung jawab:

- mengambil detail Steam untuk App ID yang metadata-nya belum lengkap;
- mengisi `games`, `genres`, `game_genres`, dan `game_tags`;
- memperbarui developer, publisher, description, release date, dan cover;
- mempertahankan metadata lama jika response baru kosong;
- menerapkan rate limit, retry, logging, dan pemrosesan per-game.

Statistik enrichment:

```text
requested, created_games, mapped_games, metadata_completed,
metadata_skipped, failed
```

Parser detail Steam yang sudah tersedia dapat digunakan kembali. Jangan membuat
request eksternal dari halaman web recommendation.

### 4.3. Materialisasi preference Steam

Perbarui `PreferenceProfileService.rebuild_steam_preferences()`:

1. Ambil `user_owned_games` yang sudah memiliki `game_id`.
2. Abaikan game tanpa metadata feature.
3. Hitung bobot playtime:

```text
weight = log(1 + playtime) / log(1 + max_playtime)
```

4. Agregasikan genre, tag, dan developer.
5. Normalisasi skor ke `0..1`.
6. Hitung confidence berdasarkan game ter-map dan ber-metadata.
7. Hapus preference lama dengan `source='steam'`.
8. Simpan preference baru dengan `source`, `confidence`, dan `profile_version`.

Jika tidak ada feature yang tersedia, jangan membuat baris kosong. Simpan
status enrichment agar UI dapat menjelaskan penyebabnya.

### 4.4. Recommendation builder

`build_profile_from_user()` harus hanya membaca `user_preferences` dari database:

```text
preference_mode='steam' → source='steam' + behavioral signals
preference_mode='quiz'  → source='quiz' + behavioral signals
```

Playtime tidak lagi dihitung langsung saat ranking. `user_owned_games` hanya
digunakan untuk mengecualikan game yang sudah dimiliki.

## 5. Urutan sinkronisasi

### Linking Steam dari `/profile`

```text
resolve Steam ID
→ fetch owned games
→ upsert games dasar
→ upsert user_owned_games
→ enrich metadata yang missing
→ rebuild user_preferences(source='steam')
→ set preference_mode='steam'
→ generate recommendation batch
→ redirect ke profile
```

Jika enrichment gagal sebagian, data yang berhasil tetap disimpan dan
preference dibentuk dari game yang metadata-nya tersedia.

### Sinkronisasi harian

1. Sync library Steam user aktif.
2. Upsert game baru dari library.
3. Enrich metadata yang masih kosong.
4. Rebuild preference Steam user terkait.
5. Generate ulang recommendation batch.

Kegagalan satu user tidak boleh menghentikan user lain.

## 6. Status profile dan fallback

Halaman profile perlu menampilkan:

- total game Steam;
- total game ter-map;
- total game dengan metadata lengkap;
- jumlah preference Steam;
- waktu sync terakhir;
- error enrichment terakhir.

Perilaku:

| Kondisi | Perilaku |
|---|---|
| Steam public + metadata lengkap | Mode Steam aktif |
| Steam public + metadata sebagian | Mode Steam aktif dengan confidence lebih rendah |
| Steam public + metadata kosong | Warning; gunakan quiz sementara |
| Steam private | Gunakan quiz/favorit manual |
| API gagal | Pertahankan batch dan profile terakhir yang sukses |

## 7. Testing plan

### Enrichment

- App ID baru membuat record `Game`.
- App ID existing di-update secara idempoten.
- Metadata kosong tidak menimpa metadata valid.
- Genre/tag/developer tersimpan dengan benar.
- Satu game gagal tidak membatalkan game lain.
- Rate limit dan retry berjalan.

### Preference

- Game dengan metadata menghasilkan `source='steam'`.
- Game tanpa mapping tidak menghasilkan sinyal.
- Game tanpa genre/tag/developer tidak menghasilkan sinyal kosong.
- Playtime lebih tinggi menghasilkan bobot lebih tinggi.
- Preference Steam lama diganti, bukan diduplikasi.
- Preference quiz tetap ada setelah Steam sync.
- Confidence mencerminkan kelengkapan mapping dan metadata.

### Integration

- Connect Steam dari `/profile` mengisi owned games.
- Connect Steam menghasilkan `user_preferences.source='steam'`.
- Recommendation memakai profile Steam terbaru.
- Disconnect menghapus preference Steam dan kembali ke quiz.
- Daily sync memperbarui preference dan recommendation.
- API failure mempertahankan data terakhir yang sukses.

## 8. Acceptance criteria

1. Owned App ID yang relevan memiliki `game_id` atau status enrichment yang jelas.
2. Game baru dari library dapat dibuat di `games`.
3. Game dengan genre/tag menghasilkan baris `source='steam'`.
4. Skor preference berbeda mengikuti playtime.
5. Recommendation hanya memakai preference tersimpan dari database.
6. Preference quiz tetap tersedia sebagai fallback.
7. Koneksi Steam dilakukan dari `/profile`.
8. Partial failure tidak menghapus data valid sebelumnya.
9. Semua request eksternal memiliki rate limit, retry, dan logging.

## 9. Urutan pengerjaan

1. Tambahkan diagnostic statistics pada Steam sync.
2. Ambil app info dan upsert game dasar.
3. Implementasikan game metadata enrichment.
4. Hubungkan enrichment ke linking dan daily sync.
5. Jalankan rebuild preference setelah enrichment.
6. Pastikan builder hanya membaca preference database.
7. Tambahkan statistik enrichment pada profile.
8. Tambahkan unit dan integration test.
9. Jalankan sync ulang untuk user existing.

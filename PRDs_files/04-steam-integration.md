# PRD Modul 04 — Steam Integration & User Data

**Proyek:** WaterMist | **Versi:** 1.0 | **Tanggal:** 18 November 2026 | **Status:** Draft (belum dikembangkan)
**Dependensi:** Modul 01, 03 (data `games`) | **Dikonsumsi oleh:** Modul 05, 06

## 1. Tujuan

Memungkinkan pengguna menghubungkan akun Steam (via Steam ID / Profile URL) agar WaterMist dapat mengambil library dan playtime sebagai dasar preferensi, serta menyediakan jalur manual (game favorit) jika data Steam tidak dapat diakses.

## 2. Sumber Data

**Steam Web API** (dokumentasi: https://steamcommunity.com/dev)

| Kebutuhan | Keterangan |
|-----------|-----------|
| Profil Steam | Validasi dan resolusi Steam ID |
| Daftar game yang dimiliki | Library pengguna |
| Playtime | Total menit bermain per game |

Catatan:
- Sebagian data hanya tersedia jika **profil dan library publik**.
- **Jangan pernah meminta password Steam.** Cukup Steam ID/Profile URL.
- API key disimpan di environment variable, tidak di frontend atau repository.

## 3. Keputusan Terbuka: Identitas Pengguna

PRD awal memakai `user_id` di banyak tabel, tetapi **tidak mendefinisikan tabel `users` maupun autentikasi**. Perlu keputusan sebelum implementasi:

| Opsi | Deskripsi | Konsekuensi |
|------|-----------|-------------|
| A. Akun WaterMist (email/username + password) | Registrasi dan login sendiri | Perlu hashing password, session, reset password |
| B. Sesi anonim | `user_id` dibuat otomatis per browser (cookie), Steam ID tersimpan di sesi | Paling sederhana untuk MVP; data hilang jika cookie dihapus |
| C. Steam OpenID login | Login lewat Steam tanpa password | Identitas jelas dan tanpa password; kompleksitas integrasi lebih tinggi |

**Rekomendasi MVP:** opsi B atau A. Skema di bawah mengasumsikan ada tabel `users` minimal (`id`, `created_at`, plus kolom auth sesuai opsi). Jika memakai akun, terapkan autentikasi dan otorisasi sesuai NFR keamanan.

## 4. Skema Database

### `users` (usulan, mengikuti opsi di atas)
| Field | Tipe | Keterangan |
|-------|------|-----------|
| id | BIGINT | PK |
| created_at | TIMESTAMP | |
| *(kolom auth)* | — | Sesuai opsi yang dipilih |

### `user_steam_profiles`
| Field | Tipe | Keterangan |
|-------|------|-----------|
| id | BIGINT | PK |
| user_id | BIGINT | FK → users |
| steam_id | VARCHAR | SteamID64 |
| profile_url | TEXT | URL profil |
| last_synced_at | TIMESTAMP | Sinkronisasi terakhir |

### `user_owned_games`
| Field | Tipe | Keterangan |
|-------|------|-----------|
| id | BIGINT | PK |
| user_id | BIGINT | FK |
| game_id | BIGINT | FK → games |
| playtime_minutes | BIGINT | Total playtime |

### `user_favorites`
| Field | Tipe | Keterangan |
|-------|------|-----------|
| id | BIGINT | PK |
| user_id | BIGINT | FK |
| game_id | BIGINT | FK |

### `user_interactions`
| Field | Tipe | Keterangan |
|-------|------|-----------|
| id | BIGINT | PK |
| user_id | BIGINT | FK |
| game_id | BIGINT | FK |
| interaction_type | VARCHAR | `view`, `favorite`, `click_deal`, `dismiss_recommendation` |
| created_at | TIMESTAMP | |

## 5. Kebutuhan Fungsional

| ID | Kebutuhan |
|----|-----------|
| FR-12 | Pengguna dapat memasukkan Steam ID atau Steam Profile URL. |
| FR-13 | Sistem mengambil daftar game dan playtime lewat Steam Web API, jika profil/library mengizinkan. |
| FR-17 | Pengguna dapat memilih game favorit secara manual bila data Steam tidak tersedia atau tidak cukup. |
| ST-18 | Menerima berbagai format input: SteamID64, `/profiles/<id>`, dan `/id/<vanity>` (vanity URL di-resolve lewat API). |
| ST-19 | **Validasi input Steam ID** (format dan panjang) sebelum memanggil API. |
| ST-20 | Menangani profil/library privat: tampilkan pesan jelas dan arahkan ke input favorit manual. |
| ST-21 | Memetakan App ID dari library ke tabel `games`. App ID yang belum ada di database dimasukkan ke antrean enrichment metadata (job harian Modul 01) dan sementara tidak dipakai pada rekomendasi. |
| ST-22 | Sinkronisasi library: saat pertama kali dihubungkan (sekali jalan) dan diperbarui otomatis **harian** lewat scheduler, atau manual dengan cooldown (mis. min. 1 jam) untuk melindungi rate limit. |
| ST-23 | Mencatat interaksi pengguna (view, favorite, click deal, dismiss) ke `user_interactions`. |
| ST-24 | Pengguna dapat memutuskan koneksi Steam dan menghapus data library/profil miliknya. |
| ST-25 | Pengambilan data Steam berjalan asinkron (background job) agar tidak menghambat request. |

## 6. Alur Pengguna

```text
Input Steam ID/URL → validasi → resolve ke SteamID64 → panggil Steam Web API
   ├─ publik  → simpan library + playtime → mapping ke games → siap dipakai rekomendasi
   └─ privat  → pesan jelas → input game favorit manual
```

## 7. Privasi dan Keamanan

- Tidak menyimpan password Steam.
- Hanya menyimpan data yang dibutuhkan (Steam ID, daftar game, playtime).
- API key tidak terekspos ke frontend.
- Terapkan autentikasi/otorisasi bila ada akun; setiap pengguna hanya mengakses datanya sendiri.
- Sediakan cara menghapus data pengguna.

## 8. Risiko

| Risiko | Dampak | Mitigasi |
|--------|--------|----------|
| Steam Profile privat | Data preferensi terbatas | Input favorit manual |
| Game di library belum ada di `games` | Preferensi kurang lengkap | Antrean enrichment metadata |
| Rate limit Steam Web API | Sinkronisasi gagal | Cooldown, retry dengan jeda, sinkron di background |
| Input Steam ID tidak valid/berbahaya | Error atau penyalahgunaan | Validasi ketat |

## 9. Tugas Pengembangan

- [ ] Memutuskan model identitas pengguna (bagian 3) dan membuat tabel `users`
- [ ] Membuat fitur input Steam ID dan validasi
- [ ] Mengintegrasikan Steam Web API (resolve vanity, owned games)
- [ ] Mengambil daftar game pengguna dan playtime
- [ ] Menghubungkan data Steam dengan database WaterMist (mapping App ID)
- [ ] Menyediakan input game favorit manual
- [ ] Mencatat `user_interactions`
- [ ] Menambahkan sinkronisasi harian ke scheduler
- [ ] Fitur putuskan koneksi dan hapus data

## 10. Acceptance Criteria

1. Pengguna dapat menghubungkan Steam ID dan library tampil/tersimpan jika profil publik.
2. Profil privat menghasilkan pesan jelas dan opsi favorit manual.
3. Pengguna dapat memilih dan menyimpan game favorit manual.
4. Playtime tersimpan per game dan siap dipakai Modul 05.
5. Password Steam tidak pernah diminta atau disimpan; API key tidak terekspos.

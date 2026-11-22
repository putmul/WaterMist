# Implementation Plan: Pencarian Literal + Semantic Terpisah

## Tujuan

Memperbaiki pencarian game agar:

1. Query yang berisi judul game, misalnya `Final Fantasy`, menampilkan hasil berdasarkan nama game terlebih dahulu.
2. Hasil semantic search ditampilkan sebagai bagian terpisah di bawah hasil nama.
3. Semantic search dapat dimuat setelah hasil literal tampil, sehingga pencarian nama tidak menunggu proses embedding.
4. Query deskriptif tetap menghasilkan rekomendasi semantic dengan bahasa yang tidak menyatakan game tidak tersedia.
5. Jika tidak ada hasil literal, sistem memberikan saran berdasarkan kandidat semantic.

## Interpretasi istilah

`Query lateral` diinterpretasikan sebagai **query literal/lexical berdasarkan nama game**. Jika maksudnya berbeda, istilah tersebut perlu diklarifikasi sebelum implementasi.

## Kondisi kode saat ini

- `app/routes/deals.py` saat ini memilih semantic search ketika `q` tersedia.
- `app/services/deal_service.py` sudah mendukung filter nama melalui `Game.name.ilike(...)`.
- `app/services/semantic_search_service.py` mengembalikan hasil semantic yang sudah diranking dan memiliki `semantic_score`.
- `app/templates/deals.html` hanya memiliki satu daftar hasil dan satu pesan kosong.
- Karena semantic search saat ini menggantikan pencarian nama, judul langsung seperti `Final Fantasy` dapat menghasilkan ranking yang tidak relevan.

## Desain perilaku

### 1. Query judul/nama

Contoh: `Final Fantasy`

- Jalankan lexical search berdasarkan nama game.
- Urutkan hasil lexical dengan prioritas:
  1. nama persis sama dengan query;
  2. nama diawali query;
  3. nama mengandung query;
  4. nama alfabetis atau harga sesuai sort yang dipilih.
- Tampilkan bagian `Hasil berdasarkan nama`.
- Setelah hasil lexical tersedia, semantic search dimuat terpisah.
- Tampilkan bagian semantic di bawahnya dengan judul `Mungkin Anda juga tertarik`.
- Hasil yang sudah muncul pada bagian literal tidak boleh diulang di bagian semantic.

### 2. Query deskriptif

Contoh: `game horror psikologis dengan cerita kuat`

- Jalankan lexical search terlebih dahulu, tetapi kemungkinan hasilnya kosong.
- Muat semantic search.
- Jika semantic menemukan hasil, tampilkan:
  `Berdasarkan pencarian Anda, mungkin game ini cocok untuk Anda:`
- Jangan menampilkan pesan `Belum ada deal yang sesuai dengan filter` untuk kondisi ini.

### 3. Tidak ada hasil literal dan semantic

- Tampilkan pesan ramah:
  `Kami belum menemukan hasil yang cocok. Coba gunakan judul, genre, atau deskripsi lain.`
- Hindari kalimat yang menyatakan game tersebut pasti tidak ada.

### 4. Filter terstruktur

- Filter toko, harga, diskon, currency, dan sort harus berlaku pada kedua bagian hasil.
- Filter yang berasal dari query natural language juga harus diteruskan ke lexical dan semantic search.
- Hasil semantic tidak boleh mengabaikan filter manual dari form.

## Rencana perubahan file

### A. `app/services/deal_service.py`

1. Tambahkan method khusus untuk lexical search, misalnya `search_by_name(filters)`.
2. Gunakan query `Game.name.ilike(...)`, tetapi tambahkan ranking SQL/Python untuk membedakan exact, prefix, dan contains match.
3. Pertahankan aturan deal aktif dan deduplikasi Steam/CheapShark yang sudah ada.
4. Pastikan filter harga, diskon, toko, currency, dan sort tetap diterapkan.

### B. `app/services/semantic_search_service.py`

1. Pertahankan perhitungan embedding dan cosine similarity yang ada.
2. Tambahkan parameter `exclude_game_ids` atau lakukan filtering hasil berdasarkan ID game yang sudah tampil secara literal.
3. Pastikan hasil semantic menerima semua filter yang sama dengan lexical search.
4. Tambahkan metadata hasil agar route/template dapat membedakan hasil literal, rekomendasi semantic, dan suggestion semantic.
5. Jangan mencampur skor lexical dengan `semantic_score`.

### C. `app/routes/deals.py`

1. Parse query menjadi informasi nama/literal, semantic text, dan filter terstruktur.
2. Jalankan lexical search secara independen dari semantic search.
3. Untuk progressive loading, pertahankan endpoint halaman utama hanya untuk hasil lexical dan tambahkan endpoint JSON/HTML fragment, misalnya `GET /deals/semantic`.
4. Endpoint semantic menerima query, filter toko/harga/diskon/currency, ID game yang sudah tampil, dan parameter page/per-page bila diperlukan.
5. Endpoint mengembalikan fragment HTML atau JSON yang aman untuk dirender di browser.
6. Jika progressive loading tidak diaktifkan, sediakan fallback server-side agar semantic tetap muncul tanpa JavaScript.

### D. `app/templates/deals.html`

1. Pisahkan tampilan menjadi dua section:
   - `Hasil berdasarkan nama`;
   - `Mungkin Anda juga tertarik`.
2. Tambahkan placeholder/loading state untuk semantic result: `Mencari rekomendasi berdasarkan makna...`.
3. Tambahkan elemen target untuk hasil async semantic.
4. Tambahkan pesan khusus untuk query deskriptif.
5. Jangan tampilkan empty-state global sebelum semantic request selesai.
6. Pastikan pagination lexical dan semantic tidak saling membingungkan; rekomendasi semantic dapat dibatasi Top-K tanpa pagination awal.

### E. JavaScript/static asset

1. Tambahkan script kecil untuk memuat endpoint semantic setelah halaman lexical selesai dirender.
2. Kirim parameter query dan filter menggunakan `URLSearchParams`.
3. Tampilkan loading, success, dan error state.
4. Jika request semantic gagal, hasil literal tetap tampil dan halaman tidak berubah menjadi error.
5. Escape/render data dengan aman; lebih baik gunakan fragment server-side atau JSON yang dirender dengan DOM API.

### F. Parser query

1. Pertahankan parsing harga, diskon, currency, dan sort di `app/services/search_query_parser.py`.
2. Tambahkan metadata ringan untuk membedakan query kemungkinan judul dari query deskriptif, bila dibutuhkan.
3. Jangan menjadikan heuristik ini sebagai satu-satunya penentu relevansi; lexical search tetap boleh dijalankan untuk semua query.

## Strategi deteksi query

Gunakan pendekatan hybrid, bukan hanya klasifikasi query:

1. Selalu jalankan lexical search.
2. Jika lexical menghasilkan hasil kuat, tampilkan sebagai hasil utama.
3. Sediakan semantic search sebagai bagian rekomendasi ketika query memiliki semantic text.
4. Jika lexical kosong, ubah label dan pesan semantic menjadi mode suggestion/descriptive.

Dengan pendekatan ini, query seperti `Final Fantasy` tetap akurat tanpa mengorbankan query seperti `game santai untuk dimainkan bersama teman`.

## Testing plan

### Unit test

- Query exact title menempatkan game dengan nama persis di urutan pertama.
- Query prefix dan contains menghasilkan ranking nama yang benar.
- Hasil semantic mengecualikan game yang sudah ada di hasil literal.
- Filter harga/diskon/toko berlaku pada kedua search mode.
- Query deskriptif menghasilkan semantic recommendation.
- Empty lexical result tidak langsung menghasilkan pesan `game tidak ada`.
- Model semantic gagal: hasil lexical tetap dapat ditampilkan.

### Integration test

- `GET /deals?q=Final+Fantasy` mengembalikan section lexical.
- Endpoint semantic mengembalikan hasil recommendation terpisah.
- `GET /deals?q=game+horror` tidak menampilkan empty-state sebelum semantic selesai.
- Request semantic gagal tidak menghilangkan hasil literal.
- Pagination/filter URL tetap dipertahankan saat memuat semantic.

### Manual acceptance test

1. Cari `Final Fantasy`:
   - game Final Fantasy muncul paling atas;
   - rekomendasi semantic berada di bawah;
   - tidak ada duplikasi.
2. Cari `game horror`:
   - jika tidak ada nama literal yang cocok, tampil pesan `Berdasarkan pencarian Anda...`;
   - rekomendasi horror tetap tampil.
3. Cari deskripsi panjang:
   - tidak muncul pesan `Belum ada deal yang sesuai dengan filter` selama semantic masih loading.
4. Matikan/gagalkan model:
   - pencarian nama tetap berfungsi;
   - UI menampilkan fallback yang ramah.

## Risiko dan keputusan teknis

- Progressive loading membutuhkan JavaScript dan endpoint tambahan.
- Jika hanya ingin perubahan minimal, semantic dapat tetap server-side tetapi ditempatkan sebagai section kedua; waktu respons masih dapat lambat pada query pertama.
- Ranking lexical sebaiknya tidak memakai full-text search dulu agar tetap kompatibel dengan SQLite test database dan MySQL yang digunakan project.
- Model semantic sebaiknya tetap lazy-loaded, tetapi kegagalan load tidak boleh membuat proses pencarian literal gagal.

## Kriteria selesai

- Query nama langsung selalu memprioritaskan hasil nama literal.
- Semantic result tampil di section terpisah di bawah hasil literal.
- Query deskriptif menggunakan bahasa rekomendasi, bukan pesan game tidak ada.
- Filter dan deduplikasi konsisten pada kedua bagian.
- Semua unit/integration test baru lulus.
- Pencarian literal tetap berfungsi ketika model semantic tidak tersedia.

# Implementation Plan: Pemilihan Game Semantic Berdasarkan Relevansi Tertinggi

## Tujuan

Memastikan card semantic search yang ditampilkan hanya berisi game dengan relevansi tertinggi dan selalu terurut dari skor semantic terbesar ke terkecil.

Target perilaku:

- Semantic result selalu diurutkan berdasarkan `semantic_score DESC`.
- Sort harga, diskon, nama, dan toko hanya berlaku untuk hasil pencarian literal.
- Hanya 10–20 game semantic yang ditampilkan.
- Default yang direkomendasikan: 12 game.
- Game yang sudah tampil pada hasil literal tetap dikeluarkan dari semantic result.

## Temuan kode saat ini

- `app/services/semantic_search_service.py` sudah menghitung `semantic_score`.
- Service hanya mengurutkan berdasarkan relevansi jika `requested_sort` bernilai `relevance`.
- Endpoint semantic meneruskan sort dari form, sehingga semantic dapat ikut diurutkan berdasarkan harga/diskon/nama.
- `app/routes/deals.py` sudah membatasi fragment semantic dengan `[:12]`, tetapi pembatasan terjadi setelah urutan yang mungkin bukan berdasarkan relevansi.
- `SEMANTIC_SEARCH_TOP_K` saat ini digunakan sebagai batas hasil service, bukan batas tampilan khusus semantic section.

## Desain perubahan

### 1. Ranking semantic independen

Pada endpoint semantic:

- Abaikan sort literal dari form untuk ranking semantic.
- Panggil semantic service dengan mode ranking `relevance`.
- Pastikan hasil akhir diurutkan dengan skor semantic descending.
- Diskon, harga, dan nama hanya menjadi tie-breaker jika skor sama.

### 2. Batas jumlah hasil semantic

Tambahkan konfigurasi baru:

```python
SEMANTIC_SEARCH_DISPLAY_LIMIT = 12
```

- Nilai valid disarankan berada di rentang 10–20.
- Service boleh tetap mengambil kandidat sampai `SEMANTIC_SEARCH_TOP_K`.
- Route/template hanya menampilkan `SEMANTIC_SEARCH_DISPLAY_LIMIT` hasil teratas.
- Jangan gunakan `SEMANTIC_SEARCH_TOP_K` sebagai batas tampilan agar indexing dan UI tetap terpisah.

### 3. Threshold minimum

Pertahankan `SEMANTIC_SEARCH_MIN_SCORE` sebagai filter minimum.

- Default saat ini `0.35` tetap digunakan pada tahap awal.
- Jangan langsung menaikkan threshold hanya karena skor terlihat seperti persentase.
- Setelah hasil top-N dievaluasi, threshold dapat dinaikkan ke `0.40` atau `0.45` jika terlalu banyak hasil lemah.
- Jika tidak ada kandidat di atas threshold, tampilkan pesan ramah dan jangan memaksa menampilkan card dengan skor rendah.

### 4. Interpretasi skor di UI

Skor cosine similarity bukan probabilitas keyakinan. Pertimbangkan mengganti label menjadi:

```text
Skor kemiripan: 53%
```

Jika label `Relevansi` dipertahankan, tambahkan keterangan bahwa skor adalah kemiripan model dan bukan jaminan kecocokan.

## File yang perlu diubah

### `config.py`

1. Tambahkan `SEMANTIC_SEARCH_DISPLAY_LIMIT`.
2. Ambil nilainya dari environment.
3. Clamp nilai ke rentang aman 10–20, atau gunakan default 12 jika konfigurasi invalid.

### `.env.example`

Tambahkan:

```env
SEMANTIC_SEARCH_DISPLAY_LIMIT=12
```

### `app/services/semantic_search_service.py`

1. Tambahkan helper khusus untuk ranking semantic, misalnya `_sort_by_relevance`.
2. Pastikan helper selalu mengurutkan `semantic_score` descending.
3. Pisahkan ranking semantic dari ranking literal.
4. Pertahankan filter `SEMANTIC_SEARCH_MIN_SCORE` sebelum proses limit.
5. Jangan mengubah kompatibilitas pemanggilan service yang digunakan oleh test lama.

### `app/routes/deals.py`

1. Endpoint `/deals/semantic` memanggil service dengan ranking relevansi, terlepas dari `sort` form.
2. Ambil batas dari `SEMANTIC_SEARCH_DISPLAY_LIMIT`.
3. Slice hasil setelah sorting.
4. Gunakan jumlah hasil setelah filtering untuk menentukan pesan kosong.

### `app/templates/deals_semantic.html`

1. Tampilkan hanya hasil yang sudah dibatasi route.
2. Pertahankan semantic section di bawah hasil literal.
3. Tampilkan skor kemiripan secara konsisten.

### `app/templates/_deal_card.html`

1. Ubah label skor bila keputusan UX menggunakan `Skor kemiripan`.
2. Jangan menampilkan skor pada card literal.

## Testing plan

### Unit test service

Gunakan encoder palsu seperti test semantic saat ini untuk memastikan:

- hasil diurutkan dari skor terbesar ke terkecil;
- skor tie memakai discount/price/name sebagai tie-breaker;
- hasil di bawah minimum score tidak masuk;
- exclude game IDs tetap diterapkan.

### Unit test konfigurasi

- Default display limit adalah 12.
- Nilai 10 dan 20 diterima.
- Nilai di bawah 10 atau di atas 20 ditangani sesuai aturan clamp/fallback.

### Integration test endpoint

- `/deals/semantic?sort=price` tetap mengembalikan hasil berdasarkan skor semantic, bukan harga.
- Jumlah card tidak melebihi display limit.
- Hasil literal dan semantic tidak duplikat.
- Jika semua skor di bawah threshold, endpoint mengembalikan pesan ramah tanpa card.

### Manual acceptance test

1. Cari query deskriptif seperti `game horror`.
2. Pastikan semantic card tampil maksimal 12 card.
3. Catat skor setiap card dan pastikan urut menurun.
4. Ubah sort literal ke `harga terendah`.
5. Pastikan urutan hasil literal berubah, tetapi urutan semantic tetap sama.
6. Uji konfigurasi 20 dan pastikan maksimal 20 card tampil.

## Kriteria selesai

- Semantic section selalu diurutkan dari skor kemiripan tertinggi.
- Sort form tidak mengubah urutan semantic section.
- Jumlah semantic card berada pada batas konfigurasi 10–20.
- Threshold minimum tetap berfungsi.
- Tidak ada duplikasi dengan hasil literal.
- Test suite lama dan test baru lulus.

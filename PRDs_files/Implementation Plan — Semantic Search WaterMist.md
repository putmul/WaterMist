Implementation Plan — Semantic Search WaterMist
1. Tujuan
Mengubah pencarian /deals?q=... dari pencocokan nama berbasis ILIKE menjadi pencarian hybrid:
- memahami makna kueri Bahasa Indonesia dan Inggris;
- mengekstrak filter harga dan diskon dari kalimat bebas;
- hanya menampilkan deal aktif;
- menampilkan harga, mata uang, persentase diskon, dan skor relevansi.
Contoh:
“game horor psikologis di bawah 100 ribu”
Menjadi:
semantic_query: "game horor psikologis"
max_price: 100000
currency: IDR
2. Arsitektur yang Digunakan
Model embedding
Gunakan model multilingual lokal:
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
Model mendukung Bahasa Indonesia dan Inggris tanpa memerlukan API eksternal.
Penyimpanan embedding
Tambahkan kolom pada tabel games:
embedding              BLOB / LargeBinary
embedding_model        VARCHAR
embedding_updated_at   DATETIME
Embedding dibuat dari:
nama game
deskripsi
genre
tag
developer
publisher
Untuk tahap awal, similarity dihitung di Python. Ini lebih kompatibel dengan MySQL dan SQLite test database yang sudah digunakan proyek.
3. Perubahan File
File baru
app/services/semantic_search_service.py
app/services/search_query_parser.py
migrations/versions/0007_semantic_search.py
tests/test_search_query_parser.py
tests/test_semantic_search.py
File yang diperbarui
requirements.txt
config.py
app/models/game.py
app/services/deal_service.py
app/routes/deals.py
app/templates/deals.html
app/services/game_service.py
app/services/game_enrichment_service.py
4. Query Parser
Buat SearchQueryParser yang mengubah kalimat bebas menjadi objek intent:
{
    "semantic_text": "game horor psikologis",
    "max_price": Decimal("100000"),
    "min_price": None,
    "currency": "IDR",
    "min_discount": None,
    "max_discount": None,
    "store": None,
    "sort": "relevance"
}
Parser harus mendukung:
di bawah 100 ribu
kurang dari Rp100.000
di bawah 100k
under $10
diskon minimal 50%
at least 50% discount
game dari Steam
Konversi harga Indonesia:
100 ribu  -> 100000
1 juta    -> 1000000
Rp 100.000 -> 100000
Token filter harga/diskon dihapus dari semantic_text agar embedding hanya memproses maksud konseptual.
5. Embedding Service
Buat service dengan tanggung jawab:
class SemanticEmbeddingService:
    def encode_game(game):
        ...

    def encode_query(text):
        ...

    def rebuild_stale_embeddings(limit=None):
        ...

    def cosine_similarity(query_vector, game_vector):
        ...
Fitur penting:
- model di-load secara lazy;
- embedding hanya dibuat jika metadata game tersedia;
- game tanpa embedding tetap dapat dicari dengan fallback keyword;
- error model tidak boleh membuat halaman /deals gagal.
Konfigurasi baru:
SEMANTIC_SEARCH_ENABLED = True
SEMANTIC_EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
SEMANTIC_SEARCH_MIN_SCORE = 0.25
SEMANTIC_SEARCH_TOP_K = 100
6. Pembaruan Embedding
Embedding dibuat ulang ketika:
- game baru dibuat;
- deskripsi berubah;
- genre atau tag berubah;
- developer/publisher berubah.
Agar proses scraping tidak lambat, embedding sebaiknya dibuat melalui proses batch:
scheduler:
    sync game metadata
    rebuild stale embeddings
    sync deals
Tambahkan juga fungsi manual untuk backfill seluruh game yang sudah ada.
7. Semantic Search Service
Alur pencarian:
query pengguna
    ↓
parse filter harga/diskon
    ↓
ambil deal aktif
    ↓
filter mata uang, harga, toko, diskon
    ↓
buat embedding query
    ↓
hitung cosine similarity
    ↓
urutkan hasil berdasarkan relevansi
    ↓
tampilkan harga dan diskon
Struktur hasil:
{
    "deal": deal,
    "semantic_score": 0.87,
    "discount_score": 65,
}
Rekomendasi ranking default:
1. semantic_score terbesar;
2. discount_percent terbesar;
3. sale_price terendah;
4. nama game.
semantic_score dan discount_score harus ditampilkan terpisah. Jangan mencampurnya menjadi satu angka yang membingungkan.
Jika pengguna meminta “diskon terbesar”, gunakan pengurutan diskon sebagai prioritas.
8. Integrasi dengan /deals
Pertahankan endpoint yang sama:
/deals?q=game horor psikologis di bawah 100 ribu
Perubahan pada route:
- jika q kosong: gunakan query SQL lama;
- jika q berisi kueri bebas: gunakan SemanticSearchService;
- jika semantic search gagal atau embedding tidak tersedia: fallback ke ILIKE.
Karena hasil semantic sudah diurutkan di Python, pagination dilakukan setelah hasil diranking.
Template menampilkan:
Game Name
Rp 150.000 → Rp 75.000
Diskon: 50%
Relevansi: 87%
Steam
Tambahkan indikator bahwa hasil berasal dari semantic search.
9. Perbedaan Mata Uang
Harga hanya dibandingkan dalam mata uang yang sama.
Contoh:
- 100 ribu hanya mencocokkan harga IDR;
- $10 hanya mencocokkan harga USD;
- jika mata uang tidak disebutkan, gunakan mata uang default aplikasi atau jangan menerapkan filter harga secara agresif.
Jangan membandingkan IDR dan USD tanpa layanan konversi kurs.
10. Pengujian
Query parser
- di bawah 100 ribu
- di bawah Rp 100.000
- under $10
- diskon minimal 50%
- kueri Bahasa Indonesia dan Inggris
Semantic search
- “horor psikologis” menemukan game dengan tag relevan;
- game tanpa kecocokan keyword langsung tetap dapat ditemukan;
- hasil di bawah batas harga;
- deal tidak aktif tidak muncul;
- mata uang berbeda tidak tercampur;
- fallback keyword berjalan ketika embedding gagal.
Integrasi
- endpoint /deals?q=...;
- pagination;
- filter toko;
- tampilan harga dan diskon;
- kompatibilitas SQLite test database.
11. Kriteria Penerimaan
Fitur dianggap selesai jika:
1. Pengguna dapat memasukkan kueri bebas Bahasa Indonesia atau Inggris.
2. Sistem memahami konsep, bukan hanya nama game.
3. Filter seperti di bawah 100 ribu diterapkan dengan benar.
4. Hasil hanya berisi deal aktif.
5. Setiap hasil menampilkan harga normal, harga diskon, mata uang, persentase diskon, dan skor relevansi.
6. Sistem tetap berjalan jika model embedding gagal.
7. Pencarian lama berbasis nama tetap kompatibel.
8. Seluruh test baru dan test lama berhasil dijalankan.
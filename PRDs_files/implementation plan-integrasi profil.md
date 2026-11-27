Rencana implementasi
Temuan utama: ada dua jalur halaman profil yang berbeda. web/template/profile.html berisi desain baru, tetapi memakai path relatif untuk CSS, gambar, dan JavaScript; backend Flask sudah punya route /profile dan template app/templates/profile.html yang saat ini masih sederhana. Flask memprioritaskan template di web/template, sehingga nama profile.html di sana menutupi template backend.
1. Tetapkan satu jalur rendering
- Jadikan halaman desain baru sebagai template yang dirender melalui route Flask profile.profile di /profile.
- Hindari membuka web/template/profile.html secara langsung/static.
- Pastikan template yang dipakai route adalah yang benar; pilihan paling aman adalah memindahkan atau menggabungkan desain ke app/templates/profile.html, atau menyesuaikan konfigurasi loader supaya template frontend di web/template dapat memakai data backend tanpa konflik nama.
2. Perbaiki path aset
- Di template Jinja, gunakan url_for('static', filename=...) untuk aset Flask.
- Tentukan apakah aset profil akan disajikan dari app/static atau web/static, lalu atur secara konsisten. Saat ini CSS/JS baru berada di web/static, sedangkan base template Flask menunjuk ke app/static.
- Gambar avatar dan cover perlu memakai path yang benar serta fallback bila berkas tidak tersedia.
- Muat layout.js yang memang diselaraskan dengan route Flask; jangan gunakan layout-profil.js tanpa memeriksa kesesuaiannya. layout-profil.js memakai tautan .html dan berbeda dari layout yang dipakai halaman web lainnya.
3. Integrasikan data profil
- Ganti konten dummy di halaman baru dengan data dari route: identitas pengguna, tanggal bergabung bila tersedia, preferensi tersimpan, status/sinkronisasi Steam, dan hitungan library.
- Selaraskan bagian game favorit dengan data yang benar-benar tersedia di model/backend. Jika belum ada sumber data favorit, tampilkan status kosong dan jangan menampilkan data palsu.
- Pertahankan proteksi @login_required pada halaman dan aksi akun.
4. Hubungkan formulir dan aksi
- Hubungkan form Steam ke route yang sudah ada: POST /profile/steam/connect dan POST /profile/steam/disconnect.
- Pertahankan pesan flash untuk hasil sukses/peringatan/error dan tampilkan di desain baru.
- Untuk edit username, preferensi akun, atau pengaturan lain, verifikasi dulu dukungan route/model; implementasikan hanya jika memang termasuk kebutuhan halaman, dengan validasi dan proteksi CSRF yang sesuai.
5. Selaraskan navigasi
- Pastikan tautan akun/topbar mengarah ke /profile dan pengguna yang belum login diarahkan ke login.
- Gunakan pola header/footer dan autentikasi dari layout.js atau layout Flask agar tampilan serta URL tidak terpecah antara versi frontend statis dan Flask.
6. Verifikasi
- Uji akses /profile untuk pengguna login dan tanpa login.
- Uji koneksi/putus koneksi Steam, pesan flash, dan tampilan saat belum ada preferensi atau Steam.
- Periksa aset di desktop/mobile, mode gelap, serta URL stylesheet, script, avatar, dan cover di browser.
- Jalankan tes route/template yang tersedia dan pastikan halaman lain tidak berubah akibat penyesuaian loader atau aset.
Urutan yang disarankan: tetapkan sumber template dan aset → perbaiki path → integrasikan data dan form → selaraskan navigasi → uji alur lengkap.
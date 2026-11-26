/* WaterMist — login & registrasi: sprite ikon, toggle password, validasi dasar. */
(function () {
  'use strict';

  var SPRITE =
    '<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>' +
    '<symbol id="i-user" viewBox="0 0 24 24"><rect x="8" y="3" width="8" height="8"/><path d="M4 21v-4h16v4"/></symbol>' +
    '<symbol id="i-mail" viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14"/><path d="M3 5l9 8 9-8"/></symbol>' +
    '<symbol id="i-lock" viewBox="0 0 24 24"><rect x="5" y="11" width="14" height="10"/><path d="M8 11V6h8v5"/></symbol>' +
    '<symbol id="i-eye" viewBox="0 0 24 24"><path d="M2 12l4-5h12l4 5-4 5H6z"/><rect x="10" y="10" width="4" height="4"/></symbol>' +
    '<symbol id="i-eye-off" viewBox="0 0 24 24"><path d="M2 12l4-5h12l4 5-4 5H6z"/><path d="M4 4l16 16"/></symbol>' +
    '<symbol id="i-steam" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18"/><rect x="13" y="7" width="5" height="5"/><path d="M5 14l5 2"/></symbol>' +
    '</defs></svg>';
  document.body.insertAdjacentHTML('afterbegin', SPRITE);

  // Tampilkan / sembunyikan password
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-toggle-password]');
    if (!b) return;
    var input = b.parentNode.querySelector('input');
    var show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    b.setAttribute('aria-pressed', show);
    b.setAttribute('aria-label', show ? 'Sembunyikan password' : 'Tampilkan password');
    b.querySelector('use').setAttribute('href', show ? '#i-eye-off' : '#i-eye');
  });

  // Validasi dasar (ganti bagian TODO dengan request ke API)
  document.querySelectorAll('form[data-auth]').forEach(function (f) {
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      var el = f.elements, msg = '';
      if (f.dataset.auth === 'register') {
        if (el.username.value.trim().length < 3) msg = 'Username minimal 3 karakter.';
        else if (el.password.value !== el.password2.value) msg = 'Konfirmasi password tidak cocok.';
        else if (!el.terms.checked) msg = 'Setujui Syarat & Ketentuan untuk melanjutkan.';
      }
      var out = f.querySelector('.form-error');
      out.textContent = msg;
      out.hidden = !msg;
      if (!msg) { /* TODO: kirim ke API */ }
    });
  });
})();

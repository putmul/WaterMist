/* WaterMist — shared layout: topbar, footer, tema, pagination, helper kartu game.
   Muat di <head> (tanpa defer) supaya tema gelap langsung terpasang tanpa kedip. */
(function () {
  'use strict';

  var KEY = 'watermist-theme';
  var root = document.documentElement;
  var NAV = [
    ['new-releases', 'Recently Released'],
    ['deals', 'Deals'],
    ['recommendations', 'Recommendations']
  ];

  /* ---------- Tema ---------- */
  function applyTheme(t) {
    if (t === 'dark') root.setAttribute('data-theme', 'dark');
    else root.removeAttribute('data-theme');
  }
  try { applyTheme(localStorage.getItem(KEY)); } catch (e) {}

  /* ---------- Helper data ---------- */
  function idr(n) { return 'Rp ' + n.toLocaleString('id-ID'); }
  function slug(s) { return s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''); }
  function oldPrice(p, off) { return Math.round(p / (1 - off / 100) / 100) * 100; }

  function cover(title) {
    return '<img class="cover" src="assets/images/game-covers/' + slug(title) + '.jpg"' +
      ' alt="Cover ' + title + '" width="320" height="180" loading="lazy">';
  }

  function game(g) {
    return '<article class="game frame">' + cover(g.t) +
      '<h3>' + g.t + '</h3>' +
      (g.d ? '<p class="meta">' + g.d + '</p>' : '') +
      '<div class="price-row">' +
        '<span class="badge">-' + g.off + '%</span>' +
        '<span class="price">' + idr(g.p) + '</span>' +
        '<s class="price-old"><span class="sr-only">Harga normal </span>' + idr(oldPrice(g.p, g.off)) + '</s>' +
      '</div>' +
      '<button class="btn btn-secondary" type="button">Simpan</button>' +
    '</article>';
  }

  /* ---------- Markup bersama ---------- */
  function topbar(page) {
    var links = NAV.map(function (n) {
      return '<a href="' + n[0] + '.html"' + (n[0] === page ? ' aria-current="page"' : '') + '>' + n[1] + '</a>';
    }).join('');
    return '<header class="topbar show">' +
      '<a class="wordmark" href="index.html">WATERMIST</a>' +
      '<nav aria-label="Navigasi utama">' + links + '</nav>' +
      '<div class="tools">' +
        '<form class="search" role="search" onsubmit="return false">' +
          '<input type="search" placeholder="Cari game..." aria-label="Cari game"></form>' +
        '<select aria-label="Mata uang"><option>IDR</option><option>USD</option></select>' +
        '<select aria-label="Bahasa"><option>ID</option><option>EN</option></select>' +
        '<button class="btn btn-secondary theme-toggle" type="button" aria-pressed="false">Gelap</button>' +
        '<button class="btn btn-primary" type="button">Login</button>' +
      '</div></header>';
  }

  var FOOTER = '<footer class="site-footer">© 2026 WaterMist · Temukan game. Bayar pas.</footer>';

  function slot(name, html) {
    var el = document.querySelector('[data-slot="' + name + '"]');
    if (el) el.outerHTML = html;
  }

  /* ---------- Pagination: <nav class="pagination" data-total="11"> ---------- */
  function pagination(nav) {
    var total = +nav.dataset.total || 1, cur = 1;
    function draw() {
      var pages = total <= 4 ? Array.from({ length: total }, function (_, i) { return i + 1; }) : [1, 2, 3, '…', total];
      nav.innerHTML =
        '<button class="page-btn" type="button" data-go="prev" aria-label="Sebelumnya">‹</button>' +
        pages.map(function (p) {
          return p === '…' ? '<span class="page-gap" aria-hidden="true">…</span>' :
            '<button class="page-btn" type="button" data-go="' + p + '"' + (p === cur ? ' aria-current="page"' : '') + '>' + p + '</button>';
        }).join('') +
        '<button class="page-btn" type="button" data-go="next" aria-label="Berikutnya">›</button>';
    }
    nav.addEventListener('click', function (e) {
      var b = e.target.closest('[data-go]');
      if (!b) return;
      var g = b.dataset.go;
      cur = g === 'prev' ? Math.max(1, cur - 1) : g === 'next' ? Math.min(total, cur + 1) : +g;
      draw();
    });
    draw();
  }

  /* ---------- Init ---------- */
  function init() {
    slot('topbar', topbar(document.body.dataset.page));
    slot('footer', FOOTER);

    var btn = document.querySelector('.theme-toggle');
    function sync() {
      if (!btn) return;
      var dark = root.getAttribute('data-theme') === 'dark';
      btn.textContent = dark ? 'Terang' : 'Gelap';
      btn.setAttribute('aria-pressed', dark);
    }
    if (btn) btn.addEventListener('click', function () {
      var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      try { localStorage.setItem(KEY, next); } catch (e) {}
      sync();
    });
    sync();

    document.querySelectorAll('.pagination').forEach(pagination);

    var scene = document.querySelector('.scene');
    function onScroll() { scene.classList.toggle('is-blurred', window.scrollY > 80); }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  document.addEventListener('DOMContentLoaded', init);
  window.WM = { idr: idr, cover: cover, game: game };
})();

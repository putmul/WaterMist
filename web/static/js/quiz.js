/* WaterMist — quiz preferensi.
   Jawaban disimpan di localStorage ('watermist-prefs') setiap kali pindah pertanyaan.
   Tambah / ubah pertanyaan cukup lewat array STEPS. */
(function () {
  'use strict';

  var KEY = 'watermist-prefs';

  // max = batas pilihan (multi). Tanpa max = pilih satu. opts: [nilai, label, deskripsi?]
  var STEPS = [
    { key: 'genre', max: 3, cols: 5, q: 'Genre game apa yang paling kamu sukai?',
      opts: [['RPG','RPG'],['Action','Action'],['Adventure','Adventure'],['Strategy','Strategy'],['Simulation','Simulation'],
             ['Sports','Sports'],['Racing','Racing'],['Puzzle','Puzzle'],['Indie','Indie'],['Others','Others']] },
    { key: 'activity', max: 3, cols: 3, q: 'Aktivitas apa yang paling kamu nikmati ketika bermain game?',
      opts: [['Eksplorasi','Eksplorasi','Menjelajahi dunia dan menemukan tempat baru.'],
             ['Cerita','Cerita','Mengikuti cerita dan perkembangan karakter.'],
             ['Pertarungan','Pertarungan','Bertarung dan mengalahkan musuh.'],
             ['Strategi','Strategi','Menyusun strategi dan mengelola sumber daya.'],
             ['Membangun','Membangun','Membangun, membuat, dan mengembangkan sesuatu.'],
             ['Teka-teki','Teka-teki','Memecahkan teka-teki.']] },
    { key: 'mode', cols: 3, q: 'Bagaimana kamu lebih suka memainkan game?',
      opts: [['Single Player','Single Player','Menikmati permainan sendiri.'],
             ['Multiplayer','Multiplayer','Bermain bersama orang lain.'],
             ['Keduanya','Keduanya','Tidak masalah bermain sendiri maupun bersama.']] },
    { key: 'session', cols: 5, q: 'Berapa lama biasanya kamu bermain dalam satu sesi?',
      opts: [['<1','Kurang dari 1 jam.'],['1-2','1 – 2 jam.'],['2-4','2 – 4 jam.'],['>4','Lebih dari 4 jam.'],['varies','Tidak menentu.']] },
    { key: 'budget', cols: 4, q: 'Berapa budget yang biasanya kamu siapkan untuk membeli game?',
      opts: [['free','Gratis (Free-to-Play)'],['<50','Di bawah Rp50.000.'],['50-100','Rp50.000 – Rp100.000.'],['100-250','Rp100.000 – Rp250.000.'],
             ['250-500','Rp250.000 – Rp500.000.'],['>500','Di atas Rp500.000.'],['any','Tidak ada batasan khusus.']] }
  ];

  var $ = function (id) { return document.getElementById(id); };
  var saved = {};
  try { saved = JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) {}
  try {
    var serverAnswers = JSON.parse(document.body.dataset.quizAnswers || '{}');
    Object.keys(serverAnswers).forEach(function (key) { saved[key] = serverAnswers[key]; });
  } catch (e) {}

  var ans = {};
  STEPS.forEach(function (s) { ans[s.key] = Array.isArray(saved[s.key]) ? saved[s.key] : []; });
  var i = 0, last = STEPS.length - 1;

  var box = $('opts'), next = $('next'), back = $('back');

  function save(done) {
    try { localStorage.setItem(KEY, JSON.stringify(Object.assign({}, ans, { done: !!done }))); } catch (e) {}
  }

  function renderSteps() {
    $('steps').innerHTML = STEPS.map(function (s, n) {
      var cls = n < i ? 'is-done' : n === i ? 'is-current' : '';
      return '<li class="step ' + cls + '"' + (n === i ? ' aria-current="step"' : '') + '>' +
        '<span class="sr-only">Langkah </span>' + (n < i ? '✓' : n + 1) + '</li>';
    }).join('');
  }

  function sync() {
    var s = STEPS[i], n = ans[s.key].length;
    next.disabled = next.dataset.saving === 'true';
    if (s.max) {
      box.querySelectorAll('input:not(:checked)').forEach(function (x) { x.disabled = n >= s.max; });
    }
  }

  function renderQ(focus) {
    var s = STEPS[i], type = s.max ? 'checkbox' : 'radio';
    renderSteps();
    $('q').textContent = s.q;
    $('hint').textContent = s.max ? 'Pilih maksimal ' + s.max + '.' : '';
    $('quiz-error').hidden = true;
    box.style.setProperty('--cols', s.cols);
    box.innerHTML = s.opts.map(function (o, n) {
      var on = ans[s.key].indexOf(o[0]) > -1;
      return '<label class="opt"><input class="sr-only" type="' + type + '" name="' + s.key + '" value="' + n + '"' + (on ? ' checked' : '') + '>' +
        '<strong>' + o[1] + '</strong>' + (o[2] ? '<small>' + o[2] + '</small>' : '') + '</label>';
    }).join('');
    back.disabled = i === 0;
    next.textContent = i === last ? 'Selesai' : 'Selanjutnya →';
    sync();
    if (focus) $('q').focus();
  }

  box.addEventListener('change', function () {
    var s = STEPS[i];
    ans[s.key] = [].slice.call(box.querySelectorAll('input:checked')).map(function (x) { return s.opts[+x.value][0]; });
    $('quiz-error').hidden = true;
    sync();
  });

  back.addEventListener('click', function () { if (i > 0) { i--; renderQ(true); } });

  next.addEventListener('click', function () {
    if (!ans[STEPS[i].key].length) {
      $('quiz-error').textContent = 'Pilih minimal satu jawaban sebelum melanjutkan.';
      $('quiz-error').hidden = false;
      box.querySelector('input')?.focus();
      return;
    }
    save(false);
    if (i < last) { i++; renderQ(true); } else finish();
  });

  function finish() {
    next.dataset.saving = 'true';
    next.disabled = true;
    next.textContent = 'Menyimpan…';
    $('quiz-error').hidden = true;
    fetch(document.body.dataset.quizEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(ans)
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (!response.ok) throw new Error(data.error || 'Quiz gagal disimpan. Coba lagi.');
        return data;
      });
    }).then(function (data) {
      save(true);
      window.localStorage.removeItem(KEY);
      if (data.warning) $('done-title').textContent = data.warning;
      $('summary').innerHTML = ans.genre.concat(ans.mode, ans.activity).map(function (t) {
        var li = document.createElement('li'); li.textContent = t; return li.outerHTML;
      }).join('');
      $('quiz').hidden = true;
      $('done').hidden = false;
      document.body.classList.add('is-done');
      window.scrollTo(0, 0);
      $('done-title').focus();
    }).catch(function (error) {
      $('quiz-error').textContent = error.message;
      $('quiz-error').hidden = false;
      next.dataset.saving = 'false';
      next.textContent = 'Coba simpan lagi';
      next.disabled = false;
    });
  }

  $('restart').addEventListener('click', function () {
    i = 0;
    STEPS.forEach(function (step) { ans[step.key] = []; });
    save(false);
    $('done').hidden = true;
    $('quiz').hidden = false;
    document.body.classList.remove('is-done');
    renderQ(true);
  });

  renderQ(false);
})();

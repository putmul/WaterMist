(function () {
  "use strict";

  var topbar = document.getElementById("topbar");
  var scene = document.querySelector(".scene");

  function updateTopbar() {
    var scrollPosition = window.scrollY;
    topbar.classList.toggle("show", scrollPosition > window.innerHeight * 0.35);
    scene.classList.toggle("is-blurred", scrollPosition > window.innerHeight * 0.25);
  }

  window.addEventListener("scroll", updateTopbar, { passive: true });
  updateTopbar();

  var themeToggles = document.querySelectorAll(".theme-toggle");
  var savedTheme = localStorage.getItem("watermist-theme");

  if (savedTheme === "dark") {
    document.documentElement.setAttribute("data-theme", "dark");
  }

  function updateThemeToggle() {
    var isDark = document.documentElement.getAttribute("data-theme") === "dark";
    themeToggles.forEach(function (toggle) {
      toggle.textContent = isDark ? "☀" : "☾";
      toggle.setAttribute("aria-label", isDark ? "Ganti ke light mode" : "Ganti ke dark mode");
      toggle.setAttribute("aria-pressed", String(isDark));
    });
  }

  themeToggles.forEach(function (themeToggle) {
    themeToggle.addEventListener("click", function () {
    var isDark = document.documentElement.getAttribute("data-theme") === "dark";

    if (isDark) {
      document.documentElement.removeAttribute("data-theme");
      localStorage.setItem("watermist-theme", "light");
    } else {
      document.documentElement.setAttribute("data-theme", "dark");
      localStorage.setItem("watermist-theme", "dark");
    }

    updateThemeToggle();
    });
  });

  updateThemeToggle();

  document.querySelectorAll(".search").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (form.action && form.getAttribute("action")) return;
      event.preventDefault();
    });
  });

  var cards = document.querySelectorAll(".card");

  if (!("IntersectionObserver" in window)) {
    cards.forEach(function (card) {
      card.classList.add("in");
    });
    return;
  }

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;

      var index = Array.prototype.indexOf.call(cards, entry.target);
      entry.target.style.transitionDelay = (index % 2) * 140 + "ms";
      entry.target.classList.add("in");
      observer.unobserve(entry.target);

      setTimeout(function () {
        entry.target.style.transitionDelay = "";
      }, 800);
    });
  }, { threshold: 0.25 });

  cards.forEach(function (card) {
    observer.observe(card);
  });
})();

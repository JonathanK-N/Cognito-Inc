/* Carrousel héros de l'accueil : défilement automatique, onglets, pause, clavier et animations par diapositive. */
(function () {
  const root = document.getElementById('hero-carousel');
  if (!root) return;

  const slides = Array.from(root.querySelectorAll('[data-slide]'));
  const tabs = Array.from(root.querySelectorAll('[data-goto]'));
  const toggle = root.querySelector('[data-toggle]');
  const status = root.querySelector('[data-hero-status]');
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const DELAY = 8000;
  let index = 0;
  let timer = null;
  let subTimers = [];
  let paused = reduced.matches;
  let hovered = false;
  let remaining = DELAY;
  let startedAt = 0;

  root.style.setProperty('--hero-delay', DELAY + 'ms');

  function clearSub() {
    subTimers.forEach(clearTimeout);
    subTimers.forEach(clearInterval);
    subTimers = [];
  }

  /* Galerie (robotique) : fondu enchaîné entre les photos */
  function runGallery(slide) {
    const imgs = Array.from(slide.querySelectorAll('.hero-gallery img'));
    if (!imgs.length) return;
    let i = 0;
    imgs.forEach(function (img, k) { img.classList.toggle('is-on', k === 0); });
    if (reduced.matches) return;
    subTimers.push(setInterval(function () {
      imgs[i].classList.remove('is-on');
      i = (i + 1) % imgs.length;
      imgs[i].classList.add('is-on');
    }, Math.round(DELAY / imgs.length)));
  }

  /* Conception 3D : frappe du prompt puis modèle → plan → rendu */
  function runCad(slide) {
    const typed = slide.querySelector('[data-cad-typed]');
    const frames = Array.from(slide.querySelectorAll('[data-cad-frame]'));
    const steps = Array.from(slide.querySelectorAll('[data-cad-step]'));
    if (!typed || !frames.length) return;
    const text = typed.getAttribute('data-text') || typed.textContent;
    typed.setAttribute('data-text', text);
    function show(k) {
      frames.forEach(function (f, j) { f.classList.toggle('is-on', j === k); });
      steps.forEach(function (s, j) { s.classList.toggle('is-on', j === k); });
    }
    show(0);
    if (reduced.matches) { typed.textContent = text; return; }
    typed.textContent = '';
    let c = 0;
    subTimers.push(setInterval(function () {
      if (c <= text.length) typed.textContent = text.slice(0, c++);
    }, 28));
    const step = Math.round((DELAY - 1600) / frames.length);
    frames.forEach(function (f, k) {
      subTimers.push(setTimeout(function () { show(k); }, 1600 + k * step));
    });
  }

  function playMedia(slide, active) {
    const video = slide.querySelector('[data-slide-video]');
    if (!video) return;
    if (active && !reduced.matches) {
      if (video.preload === 'none') video.preload = 'auto';
      const p = video.play();
      if (p && typeof p.catch === 'function') p.catch(function () {});
    } else {
      video.pause();
    }
  }

  function show(next, announce) {
    index = (next + slides.length) % slides.length;
    clearSub();
    slides.forEach(function (slide, k) {
      const active = k === index;
      slide.classList.toggle('is-active', active);
      slide.setAttribute('aria-hidden', String(!active));
      slide.inert = !active;
      playMedia(slide, active);
    });
    tabs.forEach(function (tab, k) {
      tab.setAttribute('aria-selected', String(k === index));
      tab.tabIndex = k === index ? 0 : -1;
      tab.classList.toggle('is-past', k < index);
      const bar = tab.querySelector('i');
      if (bar) { bar.style.display = 'none'; void bar.offsetWidth; bar.style.display = ''; }
    });
    runGallery(slides[index]);
    runCad(slides[index]);
    if (announce && status) status.textContent = slides[index].getAttribute('aria-label');
    remaining = DELAY;
    schedule();
  }

  function isHeld() { return paused || hovered || document.hidden; }

  function schedule() {
    clearTimeout(timer);
    root.classList.toggle('is-paused', isHeld());
    if (isHeld()) return;
    startedAt = Date.now();
    timer = setTimeout(function () { show(index + 1, false); }, remaining);
  }

  function hold() {
    if (timer) { clearTimeout(timer); timer = null; remaining = Math.max(400, remaining - (Date.now() - startedAt)); }
    root.classList.add('is-paused');
  }

  function setPaused(value) {
    paused = value;
    toggle.setAttribute('aria-label', paused ? 'Reprendre le défilement' : 'Mettre en pause');
    if (paused) hold(); else schedule();
  }

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () { show(Number(tab.getAttribute('data-goto')), true); });
  });
  root.querySelector('[data-prev]').addEventListener('click', function () { show(index - 1, true); });
  root.querySelector('[data-next]').addEventListener('click', function () { show(index + 1, true); });
  toggle.addEventListener('click', function () { setPaused(!paused); });

  root.querySelector('.hero-tabs').addEventListener('keydown', function (event) {
    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      event.preventDefault();
      show(index + (event.key === 'ArrowRight' ? 1 : -1), true);
      tabs[index].focus();
    }
  });

  root.addEventListener('mouseenter', function () { hovered = true; hold(); });
  root.addEventListener('mouseleave', function () { hovered = false; schedule(); });
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) hold(); else schedule();
  });

  if (paused) toggle.setAttribute('aria-label', 'Reprendre le défilement');
  show(0, false);
})();

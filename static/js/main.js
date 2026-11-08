document.addEventListener('DOMContentLoaded', function () {
  const root = document.documentElement;
  const themeToggle = document.getElementById('theme-toggle');
  function syncThemeLabel() {
    if (!themeToggle) return;
    const dark = root.getAttribute('data-theme') !== 'light';
    themeToggle.setAttribute('aria-label', dark ? 'Passer en mode clair' : 'Passer en mode sombre');
    themeToggle.setAttribute('title', dark ? 'Mode clair' : 'Mode sombre');
  }
  syncThemeLabel();
  if (themeToggle) {
    themeToggle.addEventListener('click', function () {
      const next = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('cognito-theme', next); } catch (e) {}
      syncThemeLabel();
    });
  }

  const toggle = document.getElementById('nav-toggle');
  const menu = document.getElementById('nav-menu');

  if (toggle && menu) {
    function closeMenu() {
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', 'Ouvrir le menu');
      menu.classList.remove('active');
    }

    toggle.addEventListener('click', function () {
      const willOpen = toggle.getAttribute('aria-expanded') !== 'true';
      toggle.setAttribute('aria-expanded', String(willOpen));
      toggle.setAttribute('aria-label', willOpen ? 'Fermer le menu' : 'Ouvrir le menu');
      menu.classList.toggle('active', willOpen);
    });

    menu.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', closeMenu);
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') closeMenu();
    });

    document.addEventListener('click', function (event) {
      if (!menu.contains(event.target) && !toggle.contains(event.target)) closeMenu();
    });
  }

  const path = window.location.pathname.replace(/\/$/, '') || '/';
  if (menu) {
    menu.querySelectorAll('.nav-link').forEach(function (link) {
      const target = new URL(link.href).pathname.replace(/\/$/, '') || '/';
      if (target === path || (target !== '/' && path.startsWith(target + '/'))) {
        link.classList.add('active');
        link.setAttribute('aria-current', 'page');
      }
    });
  }

  const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
  const motionVideos = Array.from(document.querySelectorAll('[data-motion-loop]'));
  if (motionVideos.length) {
    function setMotionVideo(video, shouldPlay) {
      if (shouldPlay && !motionPreference.matches && !document.hidden) {
        const playback = video.play();
        if (playback && typeof playback.catch === 'function') playback.catch(function () {});
      } else {
        video.pause();
      }
    }

    if ('IntersectionObserver' in window) {
      const motionObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          setMotionVideo(entry.target, entry.isIntersecting);
        });
      }, { threshold: 0.2 });
      motionVideos.forEach(function (video) { motionObserver.observe(video); });
      document.addEventListener('visibilitychange', function () {
        motionVideos.forEach(function (video) {
          setMotionVideo(video, video.getBoundingClientRect().bottom > 0 && video.getBoundingClientRect().top < window.innerHeight);
        });
      });
    } else {
      motionVideos.forEach(function (video) { setMotionVideo(video, true); });
    }

    motionPreference.addEventListener('change', function (event) {
      motionVideos.forEach(function (video) {
        const inView = video.getBoundingClientRect().bottom > 0 && video.getBoundingClientRect().top < window.innerHeight;
        setMotionVideo(video, inView && !event.matches);
      });
    });
  }

  const revealItems = document.querySelectorAll('[data-reveal]');
  if (revealItems.length) {
    document.documentElement.classList.add('has-scroll-motion');
    if ('IntersectionObserver' in window) {
      const revealObserver = new IntersectionObserver(function (entries, observer) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.14, rootMargin: '0px 0px -32px 0px' });
      revealItems.forEach(function (item) { revealObserver.observe(item); });
    } else {
      revealItems.forEach(function (item) { item.classList.add('is-visible'); });
    }
  }

  const testimonialForm = document.getElementById('testimonialForm');
  const testimonialMessage = document.getElementById('testimonialMessage');
  if (testimonialForm && testimonialMessage) {
    testimonialForm.addEventListener('submit', async function (event) {
      event.preventDefault();
      if (!testimonialForm.reportValidity()) return;
      const submit = document.getElementById('testimonial-submit');
      submit.disabled = true;
      submit.textContent = 'Envoi en cours…';
      testimonialMessage.hidden = true;
      try {
        const response = await fetch('/submit-testimonial', { method: 'POST', body: new FormData(testimonialForm) });
        const result = await response.json();
        testimonialMessage.textContent = result.message || (result.success ? 'Merci, votre avis a été envoyé.' : 'Impossible d’envoyer votre avis. Réessayez.');
        testimonialMessage.className = 'review-form-message ' + (result.success ? 'success' : 'error');
        testimonialMessage.hidden = false;
        if (result.success) testimonialForm.reset();
      } catch (error) {
        testimonialMessage.textContent = 'Une erreur est survenue. Réessayez ou écrivez-nous par courriel.';
        testimonialMessage.className = 'review-form-message error';
        testimonialMessage.hidden = false;
      } finally {
        submit.disabled = false;
        submit.textContent = 'Envoyer mon avis';
      }
    });
  }

  const form = document.getElementById('contactForm');
  const formMessage = document.getElementById('formMessage');
  if (!form || !formMessage) return;

  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    if (!form.reportValidity()) return;

    const submit = form.querySelector('button[type="submit"]');
    const consent = document.getElementById('privacy');
    if (consent && !consent.checked) {
      consent.focus();
      consent.setCustomValidity('Veuillez accepter l’utilisation de ces renseignements pour le suivi de votre demande.');
      consent.reportValidity();
      consent.addEventListener('change', function () {
        consent.setCustomValidity('');
      }, { once: true });
      return;
    }

    if (consent) consent.setCustomValidity('');
    const label = submit.querySelector('.btn-text');
    const loading = submit.querySelector('.btn-loading');
    submit.disabled = true;
    label.hidden = true;
    loading.hidden = false;
    formMessage.hidden = true;

    const data = Object.fromEntries(new FormData(form).entries());
    try {
      const response = await fetch('/send_message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(data)
      });
      const result = await response.json();
      formMessage.textContent = result.message || (result.success ? 'Votre demande a été envoyée.' : 'Impossible d’envoyer votre demande. Veuillez réessayer.');
      formMessage.className = 'form-message ' + (result.success ? 'success' : 'error');
      formMessage.hidden = false;
      if (result.success) form.reset();
    } catch (error) {
      formMessage.textContent = 'Une erreur est survenue. Veuillez réessayer ou nous écrire par courriel.';
      formMessage.className = 'form-message error';
      formMessage.hidden = false;
    } finally {
      submit.disabled = false;
      label.hidden = false;
      loading.hidden = true;
    }
  });
});

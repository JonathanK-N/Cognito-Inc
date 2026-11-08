document.addEventListener('DOMContentLoaded', () => {
  const navToggle = document.getElementById('nav-toggle');
  const navMenu = document.getElementById('nav-menu');
  if (navToggle && navMenu) {
    navToggle.addEventListener('click', () => {
      const expanded = navToggle.getAttribute('aria-expanded') === 'true';
      navToggle.setAttribute('aria-expanded', String(!expanded));
      navToggle.setAttribute('aria-label', expanded ? 'Ouvrir le menu' : 'Fermer le menu');
      navMenu.classList.toggle('active', !expanded);
    });
    navMenu.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
      navToggle.setAttribute('aria-expanded', 'false');
      navToggle.setAttribute('aria-label', 'Ouvrir le menu');
      navMenu.classList.remove('active');
    }));
  }

  const navbar = document.querySelector('.navbar');
  const syncNavbar = () => navbar?.classList.toggle('scrolled', window.scrollY > 24);
  syncNavbar();
  window.addEventListener('scroll', syncNavbar, { passive: true });

  const path = window.location.pathname.replace(/\/$/, '') || '/';
  navMenu?.querySelectorAll('.nav-link').forEach(link => {
    const target = new URL(link.href).pathname.replace(/\/$/, '') || '/';
    if (target === path || (target !== '/' && path.startsWith(`${target}/`))) {
      link.classList.add('active');
      link.setAttribute('aria-current', 'page');
    }
  });

  const revealItems = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const revealObserver = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        revealObserver.unobserve(entry.target);
      }
    }), { threshold: 0.12 });
    revealItems.forEach(item => revealObserver.observe(item));
  } else {
    revealItems.forEach(item => item.classList.add('is-visible'));
  }

  const form = document.getElementById('contactForm');
  const formMessage = document.getElementById('formMessage');
  if (form && formMessage) {
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const submit = form.querySelector('button[type="submit"]');
      const consent = document.getElementById('privacy');
      if (consent && !consent.checked) {
        consent.focus();
        consent.setCustomValidity('Veuillez accepter l’utilisation de ces renseignements pour le suivi de votre demande.');
        consent.reportValidity();
        consent.addEventListener('change', () => consent.setCustomValidity(''), { once: true });
        return;
      }
      consent?.setCustomValidity('');
      const text = submit.querySelector('.btn-text');
      const loading = submit.querySelector('.btn-loading');
      submit.disabled = true;
      text.hidden = true;
      loading.hidden = false;
      formMessage.hidden = true;

      const data = Object.fromEntries(new FormData(form).entries());
      delete data.privacy;
      try {
        const response = await fetch('/send_message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify(data)
        });
        const result = await response.json();
        formMessage.textContent = result.message || (result.success ? 'Votre demande a été envoyée.' : 'Impossible d’envoyer votre demande. Veuillez réessayer.');
        formMessage.className = `form-message ${result.success ? 'success' : 'error'}`;
        formMessage.hidden = false;
        if (result.success) form.reset();
      } catch {
        formMessage.textContent = 'Une erreur est survenue. Veuillez réessayer ou nous écrire par courriel.';
        formMessage.className = 'form-message error';
        formMessage.hidden = false;
      } finally {
        submit.disabled = false;
        text.hidden = false;
        loading.hidden = true;
      }
    });
  }
});

document.addEventListener('DOMContentLoaded', function () {
  const toggle = document.getElementById('nav-toggle');
  const menu = document.getElementById('nav-menu');

  if (toggle && menu) {
    function closeMenu() {
      toggle.setAttribute('aria-expanded', 'false');
      toggle.textContent = 'Menu';
      menu.classList.remove('active');
    }

    toggle.addEventListener('click', function () {
      const willOpen = toggle.getAttribute('aria-expanded') !== 'true';
      toggle.setAttribute('aria-expanded', String(willOpen));
      toggle.textContent = willOpen ? 'Fermer' : 'Menu';
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

/* Animation du pipeline de l'accueil : exécute les étapes en boucle, façon CI/CD. */
(function () {
  const panel = document.querySelector('[data-pipeline]');
  if (!panel) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const steps = Array.from(panel.querySelectorAll('[data-step]'));
  const fill = panel.querySelector('[data-fill]');
  const state = panel.querySelector('[data-state]');
  const runLabel = panel.querySelector('[data-run]');
  const log = panel.querySelector('[data-log]');

  const plan = [
    { ms: 900, start: 'POST /send_message · demande reçue', done: 'formulaire validé · enregistré en base' },
    { ms: 1700, start: 'IA · analyse du besoin…', done: 'brouillon de réponse généré' },
    { ms: 900, start: 'telegram · notification de l’équipe…', done: 'équipe notifiée · validation humaine' },
    { ms: 900, start: 'resend · envoi de la confirmation…', done: 'courriel de confirmation livré' }
  ];

  let run = 127;
  let timers = [];
  let playing = false;
  let visible = false;

  function wait(ms) {
    return new Promise(function (resolve) { timers.push(setTimeout(resolve, ms)); });
  }

  function clock(totalMs) {
    return (totalMs / 1000).toFixed(1).replace('.', ',') + ' s';
  }

  function addLog(text, kind) {
    const line = document.createElement('p');
    const d = new Date();
    const time = [d.getHours(), d.getMinutes(), d.getSeconds()].map(function (n) { return String(n).padStart(2, '0'); }).join(':');
    line.innerHTML = '<span class="log-time"></span><span></span>';
    line.firstChild.textContent = time;
    line.lastChild.textContent = text;
    if (kind) line.lastChild.className = kind;
    log.appendChild(line);
    while (log.children.length > 3) log.removeChild(log.firstChild);
  }

  function reset() {
    steps.forEach(function (li) {
      li.classList.remove('is-running', 'is-done');
      li.querySelector('[data-time]').textContent = '';
    });
    fill.style.width = '0%';
    panel.classList.remove('is-success');
  }

  async function cycle() {
    while (playing) {
      run += 1;
      runLabel.textContent = run;
      reset();
      panel.classList.add('is-running');
      state.textContent = 'en cours · étape 1/' + steps.length;
      addLog('▶ pipeline #' + run + ' démarré', 'log-run');
      let total = 0;
      for (let i = 0; i < steps.length; i += 1) {
        if (!playing) return;
        const li = steps[i];
        state.textContent = 'en cours · étape ' + (i + 1) + '/' + steps.length;
        li.classList.add('is-running');
        addLog('→ ' + plan[i].start);
        const ms = plan[i].ms + Math.round(Math.random() * 300);
        await wait(ms);
        if (!playing) return;
        total += ms;
        li.classList.remove('is-running');
        li.classList.add('is-done');
        li.querySelector('[data-time]').textContent = '✓ ' + clock(ms);
        fill.style.width = ((i + 1) / steps.length * 100) + '%';
        addLog('✓ ' + plan[i].done, 'log-ok');
      }
      panel.classList.remove('is-running');
      panel.classList.add('is-success');
      state.textContent = 'réussi · ' + clock(total);
      await wait(3200);
    }
  }

  function start() {
    if (playing || !visible || document.hidden) return;
    playing = true;
    panel.classList.add('is-animated');
    cycle();
  }

  function stop() {
    playing = false;
    timers.forEach(clearTimeout);
    timers = [];
    panel.classList.remove('is-running');
  }

  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) {
      visible = entries[0].isIntersecting;
      if (visible) start(); else stop();
    }, { threshold: 0.3 }).observe(panel);
  } else {
    visible = true;
    start();
  }

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) stop(); else start();
  });
})();

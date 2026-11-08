/* Pipelines animés (style CI/CD) : chaque bloc [data-pipeline] exécute ses étapes en boucle.
   Chaque étape [data-step] décrit son exécution avec data-start, data-done, data-ms et, au besoin, data-badge. */
(function () {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  function pad(n) { return String(n).padStart(2, '0'); }
  function clock(ms) { return (ms / 1000).toFixed(1).replace('.', ',') + ' s'; }

  function setup(panel) {
    const steps = Array.from(panel.querySelectorAll('[data-step]'));
    const fill = panel.querySelector('[data-fill]');
    const state = panel.querySelector('[data-state]');
    const runLabel = panel.querySelector('[data-run]');
    const log = panel.querySelector('[data-log]');
    const label = panel.getAttribute('data-pipeline') || 'pipeline';
    const doneLabel = panel.getAttribute('data-done-label') || 'réussi';
    let run = runLabel ? parseInt(runLabel.textContent, 10) - 1 : 0;
    let timers = [];
    let playing = false;
    let visible = false;

    function wait(ms) {
      return new Promise(function (resolve) { timers.push(setTimeout(resolve, ms)); });
    }

    function addLog(text, kind) {
      if (!log) return;
      const d = new Date();
      const line = document.createElement('p');
      line.innerHTML = '<span class="log-time"></span><span></span>';
      line.firstChild.textContent = [d.getHours(), d.getMinutes(), d.getSeconds()].map(pad).join(':');
      line.lastChild.textContent = text;
      if (kind) line.lastChild.className = kind;
      log.appendChild(line);
      while (log.children.length > 3) log.removeChild(log.firstChild);
    }

    function reset() {
      steps.forEach(function (li) {
        li.classList.remove('is-running', 'is-done');
        const t = li.querySelector('[data-time]');
        if (t) t.textContent = '';
      });
      if (fill) fill.style.width = '0%';
      panel.classList.remove('is-success');
    }

    async function cycle() {
      while (playing) {
        run += 1;
        if (runLabel) runLabel.textContent = run;
        reset();
        panel.classList.add('is-running');
        addLog('▶ ' + label + ' #' + run + ' démarré', 'log-run');
        let total = 0;
        for (let i = 0; i < steps.length; i += 1) {
          if (!playing) return;
          const li = steps[i];
          state.textContent = 'en cours · étape ' + (i + 1) + '/' + steps.length;
          li.classList.add('is-running');
          addLog('→ ' + li.getAttribute('data-start'));
          const ms = parseInt(li.getAttribute('data-ms') || '1000', 10) + Math.round(Math.random() * 300);
          await wait(ms);
          if (!playing) return;
          total += ms;
          li.classList.remove('is-running');
          li.classList.add('is-done');
          const t = li.querySelector('[data-time]');
          if (t) t.textContent = '✓ ' + (li.getAttribute('data-badge') || clock(ms));
          if (fill) fill.style.width = ((i + 1) / steps.length * 100) + '%';
          addLog('✓ ' + li.getAttribute('data-done'), 'log-ok');
        }
        panel.classList.remove('is-running');
        panel.classList.add('is-success');
        state.textContent = doneLabel === 'réussi' ? 'réussi · ' + clock(total) : doneLabel;
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
  }

  document.querySelectorAll('[data-pipeline]').forEach(setup);
})();

/* Boot loader (frontend only).
   LIVE    — inside Streamlit: a two-way component. Python sends the machine;
             Generator requests go to Python (core.generator / core.minimize)
             and the replies come back as component args.
   OFFLINE — the downloaded single file: data baked in by the same Python code,
             including a set of pre-built machines for the Generator. */
(function () {
  'use strict';
  const root = document.documentElement.style;
  const applyPalette = p => { for (const k in p) root.setProperty('--' + k, p[k]); };
  const keyOf = m => JSON.stringify([m.cfg.coins, m.cfg.products, m.cfg.cap]);

  function start(machine, backend) {
    document.body.classList.toggle('live', backend.live);
    window.VM_BOOT(machine, { onReady: ctx => window.VM_VIEWS.init(ctx, backend) });
  }

  /* ─── offline ─── */
  const D = window.__VM_DATA__;
  if (D) {
    applyPalette(D.palette);
    let machine = D.machine, idx = null;
    try { idx = localStorage.getItem('vm_prebuilt'); } catch (e) { /* storage blocked */ }
    if (idx !== null && D.prebuilt[+idx]) machine = D.prebuilt[+idx].machine;
    const findIdx = cfg => D.prebuilt.findIndex(r => keyOf(r) === keyOf({ cfg }));
    let lastRand = -1;
    start(machine, {
      live: false,
      defaultForm: D.default_form,
      request(op, data) {
        if (op === 'generate') {
          const i = findIdx(data.cfg);
          return Promise.resolve(i >= 0 ? D.prebuilt[i] : { ok: false, offline: true,
            error: 'This offline copy can only show machines pre-built by the Python backend. ' +
                   'Use Randomize, or run the live app (python -m streamlit run app/Simulator.py) to build a custom one.' });
        }
        if (op === 'randomize') {
          let i; do { i = 1 + Math.floor(Math.random() * (D.prebuilt.length - 1)); } while (i === lastRand && D.prebuilt.length > 2);
          lastRand = i; return Promise.resolve(D.prebuilt[i]);
        }
        if (op === 'load') {
          const i = findIdx(data.cfg);
          try { localStorage.setItem('vm_prebuilt', i >= 0 ? String(i) : '0'); sessionStorage.setItem('vm_view', 'sim'); } catch (e) { /* ignore */ }
          location.reload();
          return new Promise(() => {});
        }
        return Promise.resolve({ ok: false, error: 'Unknown request' });
      },
    });
    return;
  }

  /* ─── live (Streamlit component protocol) ─── */
  const send = (type, extra) => window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type }, extra || {}), '*');
  const pending = {};
  let booted = false, bootKey = null;
  const backend = {
    live: true,
    defaultForm: null,
    request(op, data) {
      const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
      return new Promise(res => {
        pending[id] = res;
        send('streamlit:setComponentValue', { value: { id, op, data: data || {} }, dataType: 'json' });
      });
    },
  };
  window.addEventListener('message', ev => {
    const d = ev.data;
    if (!d || d.type !== 'streamlit:render') return;
    const a = d.args || {};
    if (!a.machine) return;
    if (!booted) {
      booted = true; bootKey = keyOf(a.machine);
      backend.defaultForm = a.default_form;
      applyPalette(a.palette);
      start(a.machine, backend);
    } else if (keyOf(a.machine) !== bootKey) {      // a new machine was loaded in Python
      location.reload(); return;
    }
    if (a.reply && pending[a.reply.id]) { pending[a.reply.id](a.reply); delete pending[a.reply.id]; }
  });
  send('streamlit:componentReady', { apiVersion: 1 });
  send('streamlit:setFrameHeight', { height: 900 });
})();

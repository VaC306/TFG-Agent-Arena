// Blocking bootstrap shared by the local application and the offline demo.
// Runs in <head>, before styles and Angular, so the first paint has the right theme.
(() => {
  const key = 'arena.theme.v1';
  const valid = value => ['system', 'light', 'dark'].includes(value);
  const media = window.matchMedia('(prefers-color-scheme: dark)');
  let preference = 'system';
  try { const saved = localStorage.getItem(key); if (valid(saved)) preference = saved; } catch { /* Storage may be disabled. */ }
  function apply() {
    const theme = preference === 'system' ? (media.matches ? 'dark' : 'light') : preference;
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#191a18' : '#f8f8f6');
    window.dispatchEvent(new Event('arena-theme-change'));
  }
  window.arenaTheme = {
    get preference() { return preference; },
    set(value) {
      if (!valid(value)) return false;
      preference = value;
      let saved = true;
      try { if (value === 'system') localStorage.removeItem(key); else localStorage.setItem(key, value); }
      catch { saved = false; }
      apply();
      return saved;
    },
  };
  media.addEventListener('change', () => { if (preference === 'system') apply(); });
  window.addEventListener('storage', event => {
    if (event.key === key || event.key === null) {
      preference = valid(event.newValue) ? event.newValue : 'system';
      apply();
    }
  });
  apply();
})();

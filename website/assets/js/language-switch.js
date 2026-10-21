/* Both language copies are embedded at build time, as on PACE Lab. */
(function () {
  const root = document.documentElement;

  function apply(language) {
    root.lang = language === 'en' ? 'en' : 'zh-CN';
    root.setAttribute('xml:lang', root.lang);
    const title = root.getAttribute('data-wdc-title-' + language);
    if (title) document.title = title;
    try { localStorage.setItem('wdc-language', language); } catch (_) {}

    // Translate accessible labels as well as visible text.
    for (const attribute of ['alt', 'title', 'aria-label']) {
      document.querySelectorAll('[data-wdc-attr-' + language + '-' + attribute + ']').forEach(element => {
        element.setAttribute(attribute, element.getAttribute('data-wdc-attr-' + language + '-' + attribute));
      });
    }
    document.querySelectorAll('[data-wdc-language]').forEach(button => {
      button.disabled = false;
      button.setAttribute('aria-pressed', String(button.dataset.wdcLanguage === language));
    });
    const url = new URL(location.href);
    url.searchParams.set('lang', language);
    history.replaceState(history.state, '', url.pathname + url.search + url.hash);
    document.querySelectorAll('a[href]').forEach(link => {
      const href = link.getAttribute('href');
      if (!href || href.startsWith('#') || link.hasAttribute('download')) return;
      const target = new URL(href, location.href);
      if (target.origin !== location.origin || !(/\/$|\.html$/.test(target.pathname))) return;
      target.searchParams.set('lang', language);
      link.href = target.pathname + target.search + target.hash;
    });
  }

  function initialize() {
    document.querySelectorAll('[data-wdc-language]').forEach(button => {
      button.addEventListener('click', () => apply(button.dataset.wdcLanguage));
    });
    apply(root.lang === 'en' ? 'en' : 'zh');
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, {once: true});
  else initialize();
  window.addEventListener('pageshow', event => {
    if (event.persisted) {
      const requested = new URLSearchParams(location.search).get('lang');
      apply(requested === 'en' ? 'en' : 'zh');
    }
  });
})();

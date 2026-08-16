(() => {
  'use strict';

  function detectSiteRoot() {
    const scripts = [...document.scripts];
    const ownScript = scripts.find((script) =>
      /\/_assets\/script\/header-nav(?:-v\d+)?\.js(?:[?#]|$)/.test(script.src || ''),
    );

    if (ownScript?.src) {
      return new URL('../../', ownScript.src);
    }

    const anyAssetScript = scripts.find((script) =>
      (script.src || '').includes('/_assets/script/'),
    );
    if (anyAssetScript?.src) {
      const marker = '/_assets/script/';
      const index = anyAssetScript.src.indexOf(marker);
      if (index >= 0) return new URL(anyAssetScript.src.slice(0, index + 1));
    }

    return new URL('./', window.location.href);
  }

  const SITE_ROOT = detectSiteRoot();
  const TARGETS = new Map([
    ['Рекомендации', new URL('index.html#osnovnye-razdely', SITE_ROOT).href],
    ['Клинические исследования', new URL('clinical-trials/', SITE_ROOT).href],
    ['Мероприятия', new URL('events/', SITE_ROOT).href],
    ['Новости', new URL('news/', SITE_ROOT).href],
    ['Обновления', new URL('updates.html', SITE_ROOT).href],
    ['О проекте', new URL('about/', SITE_ROOT).href],
  ]);

  function patchNavigation() {
    for (const anchor of document.querySelectorAll('a')) {
      const text = (anchor.textContent || '').replace(/\s+/g, ' ').trim();
      const target = TARGETS.get(text);
      if (!target) continue;

      if (anchor.href !== target) {
        anchor.href = target;
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', patchNavigation, {once: true});
  } else {
    patchNavigation();
  }

  let scheduled = false;
  const observer = new MutationObserver(() => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      patchNavigation();
    });
  });

  observer.observe(document.documentElement, {childList: true, subtree: true});
})();

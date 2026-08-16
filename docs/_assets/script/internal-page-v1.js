(() => {
  'use strict';

  const INDEX = Array.isArray(window.EESG_SEARCH_INDEX) ? window.EESG_SEARCH_INDEX : [];
  const CLINICAL_ROOTS = new Set([
    'general-principles',
    'soft-tissue-sarcomas',
    'bone-sarcomas',
    'specific-tumor-groups',
    'drugs-and-regimens',
    'special-clinical-situations',
  ]);

  function detectSiteRoot() {
    const ownScript = [...document.scripts].find((script) =>
      /\/_assets\/script\/internal-page-v1\.js(?:[?#]|$)/.test(script.src || ''),
    );
    if (ownScript?.src) return new URL('../../', ownScript.src);
    return new URL('./', window.location.href);
  }

  const SITE_ROOT = detectSiteRoot();

  function normalizedUrl(value) {
    let url = String(value || '').replace(/^\.\//, '').replace(/^\//, '');
    if (!url) return 'index.html';
    if (url.endsWith('/')) url += 'index.html';
    return url;
  }

  function currentRelativeUrl() {
    const rootPath = SITE_ROOT.pathname.endsWith('/') ? SITE_ROOT.pathname : `${SITE_ROOT.pathname}/`;
    let path = window.location.pathname;
    if (path.startsWith(rootPath)) path = path.slice(rootPath.length);
    return normalizedUrl(path);
  }

  function currentRecord() {
    const current = currentRelativeUrl();
    return INDEX.find((item) => normalizedUrl(item.url) === current) || null;
  }

  function isClinicalPage(record) {
    if (!record) return false;
    const first = normalizedUrl(record.url).split('/')[0];
    return CLINICAL_ROOTS.has(first);
  }

  function href(url) {
    return new URL(normalizedUrl(url), SITE_ROOT).href;
  }

  function directoryOf(url) {
    const normalized = normalizedUrl(url);
    return normalized.replace(/index\.html$/, '');
  }

  function findAncestorRecord(title, current) {
    const currentPath = normalizedUrl(current.url);
    const candidates = INDEX.filter(
      (item) => item.title === title && currentPath.startsWith(directoryOf(item.url)),
    );
    return candidates.sort((a, b) => normalizedUrl(b.url).length - normalizedUrl(a.url).length)[0] || null;
  }

  function ensureBreadcrumbs(h1, record) {
    if (document.querySelector('.eesg-breadcrumbs')) return;

    const nav = document.createElement('nav');
    nav.className = 'eesg-breadcrumbs';
    nav.setAttribute('aria-label', 'Хлебные крошки');

    const list = document.createElement('ol');
    list.className = 'eesg-breadcrumbs__list';

    const addLink = (label, url) => {
      const li = document.createElement('li');
      li.className = 'eesg-breadcrumbs__item';
      const a = document.createElement('a');
      a.href = url;
      a.textContent = label;
      li.appendChild(a);
      list.appendChild(li);
    };

    addLink('Рекомендации', new URL('index.html#osnovnye-razdely', SITE_ROOT).href);

    for (const title of record.breadcrumbs || []) {
      const ancestor = findAncestorRecord(title, record);
      if (ancestor) addLink(title, href(ancestor.url));
    }

    nav.appendChild(list);
    h1.parentNode?.insertBefore(nav, h1);
  }

  function findSectionList(heading) {
    let node = heading?.nextElementSibling;
    while (node && !/^H[1-6]$/.test(node.tagName)) {
      if (node.tagName === 'UL' || node.tagName === 'OL') return node;
      node = node.nextElementSibling;
    }
    return null;
  }

  function markSpecialSections(scope) {
    scope.querySelectorAll('h2, h3').forEach((heading) => {
      const title = (heading.textContent || '').trim().toLocaleLowerCase('ru-RU');

      if (title === 'структура раздела') {
        heading.classList.add('eesg-section-links-heading');
        const list = findSectionList(heading);
        if (list) list.classList.add('eesg-section-links');
      }

      if (title === 'литература') {
        heading.classList.add('eesg-literature-heading');
        const list = findSectionList(heading);
        if (list) list.classList.add('eesg-literature-list');
      }

      if (title === 'ограничения опубликованных данных') {
        heading.classList.add('eesg-limitations-heading');
      }
    });
  }

  function ensureBackToTop() {
    let button = document.querySelector('.eesg-back-to-top');
    if (!button) {
      button = document.createElement('button');
      button.type = 'button';
      button.className = 'eesg-back-to-top';
      button.setAttribute('aria-label', 'Наверх');
      button.innerHTML = '<span aria-hidden="true">↑</span><span class="eesg-back-to-top__label">Наверх</span>';
      button.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
      document.body.appendChild(button);
    }

    const update = () => button.classList.toggle('is-visible', window.scrollY > 640);
    if (!button.dataset.scrollBound) {
      window.addEventListener('scroll', update, { passive: true });
      button.dataset.scrollBound = '1';
    }
    update();
  }

  function enhance() {
    const record = currentRecord();
    if (!isClinicalPage(record)) return false;

    const h1 = document.querySelector('.dc-doc-page__content h1, main h1, article h1, h1');
    if (!h1) return false;

    const content = h1.closest('.dc-doc-page__content') || h1.parentElement;
    if (!content) return false;

    content.classList.add('eesg-internal-page');
    h1.classList.add('eesg-internal-page__title');
    ensureBreadcrumbs(h1, record);
    markSpecialSections(content);
    content.querySelectorAll('h2, h3').forEach((heading) => heading.classList.add('eesg-scroll-heading'));
    ensureBackToTop();
    return true;
  }

  function run() {
    enhance();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run, { once: true });
  } else {
    run();
  }

  const observer = new MutationObserver(() => run());
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();

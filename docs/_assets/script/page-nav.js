(() => {
  'use strict';

  const INDEX = Array.isArray(window.EESG_SEARCH_INDEX) ? window.EESG_SEARCH_INDEX : [];

  function detectSiteRoot() {
    const ownScript = [...document.scripts].find((script) =>
      /\/_assets\/script\/page-nav\.js(?:[?#]|$)/.test(script.src || ''),
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

  function parentGroup(url) {
    const parts = normalizedUrl(url).split('/');
    if (parts.length < 3) return '';
    parts.pop();
    parts.pop();
    return parts.join('/');
  }

  function href(url) {
    return new URL(normalizedUrl(url), SITE_ROOT).href;
  }

  function navLink(item, direction) {
    if (!item) return null;
    const link = document.createElement('a');
    link.className = `eesg-page-nav__link eesg-page-nav__link_${direction}`;
    link.href = href(item.url);

    const eyebrow = document.createElement('span');
    eyebrow.className = 'eesg-page-nav__eyebrow';
    eyebrow.textContent = direction === 'prev' ? '← Предыдущая' : 'Следующая →';

    const title = document.createElement('span');
    title.className = 'eesg-page-nav__title';
    title.textContent = item.title;
    link.append(eyebrow, title);
    return link;
  }

  function enhance() {
    if (!INDEX.length || document.querySelector('.eesg-page-nav')) return;
    const currentUrl = currentRelativeUrl();
    const current = INDEX.find((item) => normalizedUrl(item.url) === currentUrl);
    if (!current) return;

    const group = parentGroup(current.url);
    if (!group) return;

    const siblings = INDEX
      .filter((item) => parentGroup(item.url) === group)
      .sort((a, b) => a.title.localeCompare(b.title, 'ru-RU'));
    if (siblings.length < 2) return;

    const index = siblings.findIndex((item) => normalizedUrl(item.url) === normalizedUrl(current.url));
    if (index < 0) return;

    const h1 = document.querySelector('main h1, article h1, h1');
    const content = h1?.closest('.yfm') || h1?.parentElement;
    if (!content) return;

    const nav = document.createElement('nav');
    nav.className = 'eesg-page-nav';
    nav.setAttribute('aria-label', 'Навигация по разделу');

    const parentUrl = `${group}/index.html`;
    const parent = INDEX.find((item) => normalizedUrl(item.url) === parentUrl);
    if (parent) {
      const parentLink = document.createElement('a');
      parentLink.className = 'eesg-page-nav__parent';
      parentLink.href = href(parent.url);
      parentLink.textContent = `↑ ${parent.title}`;
      nav.appendChild(parentLink);
    }

    const row = document.createElement('div');
    row.className = 'eesg-page-nav__row';
    const prev = navLink(siblings[index - 1], 'prev');
    const next = navLink(siblings[index + 1], 'next');
    if (prev) row.appendChild(prev);
    else row.appendChild(document.createElement('span'));
    if (next) row.appendChild(next);
    nav.appendChild(row);
    content.appendChild(nav);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', enhance, { once: true });
  } else {
    enhance();
  }
})();
